"""STT → LLM → TTS pipeline orchestration."""

import asyncio
import logging
import time
from typing import AsyncIterator, Optional

import numpy as np

from .stt import SpeechToText
from .llm import ConversationLLM
from .tts import TextToSpeech
from .audio_utils import resample, pcm_to_twilio_audio, int16_to_float32
from .prompts import DEFAULT_PERSONA

logger = logging.getLogger(__name__)


class ConversationPipeline:
    """Orchestrates the full STT → LLM → TTS pipeline for a single call."""

    def __init__(self, persona: str = DEFAULT_PERSONA):
        self.stt = SpeechToText()
        self.llm = ConversationLLM(persona=persona)
        self.tts = TextToSpeech()
        self.is_speaking = False
        self._call_start = time.monotonic()
        logger.info(f"Pipeline initialized for persona '{persona}'")

    async def get_greeting_audio(self) -> tuple[np.ndarray, int]:
        """Generate the initial greeting audio.

        Returns:
            Tuple of (audio_data, sample_rate).
        """
        greeting = self.llm.get_greeting()
        logger.info(f"Greeting: '{greeting}'")
        audio, sr = self.tts.synthesize(greeting)
        return audio, sr

    def feed_caller_audio(self, audio_chunk: np.ndarray, sample_rate: int = 8000) -> None:
        """Feed incoming caller audio to the STT engine.

        Args:
            audio_chunk: Raw audio from the caller.
            sample_rate: Sample rate (Twilio sends 8kHz).
        """
        if self.is_speaking:
            # Don't transcribe while we're speaking (echo cancellation)
            return
        self.stt.feed_audio(audio_chunk, sample_rate)

    def is_caller_done_speaking(self, silence_timeout: float = 1.5) -> bool:
        """Check if the caller has stopped talking."""
        return self.stt.is_speech_complete(silence_timeout)

    async def generate_response(self) -> tuple[str, np.ndarray, int]:
        """Transcribe → generate LLM response → synthesize speech.

        Returns:
            Tuple of (response_text, audio_data, sample_rate).
        """
        # Step 1: Transcribe
        start = time.monotonic()
        caller_text = self.stt.transcribe()
        stt_time = time.monotonic() - start

        if not caller_text:
            return "", np.array([], dtype=np.int16), 22050

        logger.info(f"Caller said: '{caller_text}' (STT: {stt_time*1000:.0f}ms)")

        # Step 2: Generate response
        start = time.monotonic()
        response_text = await self.llm.generate_response(caller_text)
        llm_time = time.monotonic() - start

        if not response_text:
            return "", np.array([], dtype=np.int16), 22050

        # Step 3: Synthesize speech
        start = time.monotonic()
        audio, sr = self.tts.synthesize(response_text)
        tts_time = time.monotonic() - start

        total = stt_time + llm_time + tts_time
        logger.info(
            f"Pipeline total: {total*1000:.0f}ms "
            f"(STT={stt_time*1000:.0f}ms, LLM={llm_time*1000:.0f}ms, TTS={tts_time*1000:.0f}ms)"
        )

        return response_text, audio, sr

    async def generate_response_streaming(self) -> AsyncIterator[tuple[str, np.ndarray, int]]:
        """Streaming version: yields audio chunks as sentences complete.

        This reduces perceived latency by starting TTS as soon as
        the first sentence from the LLM is ready.
        """
        caller_text = self.stt.transcribe()
        if not caller_text:
            return

        logger.info(f"Caller said: '{caller_text}'")
        self.is_speaking = True

        try:
            async for sentence in self.llm.generate_response_stream(caller_text):
                audio, sr = self.tts.synthesize(sentence)
                if len(audio) > 0:
                    yield sentence, audio, sr
        finally:
            self.is_speaking = False

    def reset(self) -> None:
        """Reset the pipeline for a new call."""
        self.stt.reset()
        self.llm.reset()
        self.is_speaking = False
        self._call_start = time.monotonic()

    @property
    def call_duration(self) -> float:
        """Duration of the current call in seconds."""
        return time.monotonic() - self._call_start
