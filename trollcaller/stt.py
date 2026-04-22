"""Speech-to-Text using faster-whisper for low-latency transcription."""

import logging
import numpy as np
from faster_whisper import WhisperModel

from .config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    """Whisper-based speech-to-text with streaming-friendly interface."""

    def __init__(self):
        logger.info(f"Loading Whisper model: {settings.whisper_model}")
        self.model = WhisperModel(
            settings.whisper_model,
            device="cpu",  # Use "cuda" if you have a GPU
            compute_type="int8",  # Faster on CPU
        )
        self._buffer = np.array([], dtype=np.float32)
        self._sample_rate = 16000  # Whisper expects 16kHz
        # Minimum audio length to attempt transcription (in seconds)
        self._min_duration = 0.5
        # Silence detection
        self._silence_threshold = 0.01
        self._silence_duration = 0.0
        self._speech_detected = False
        logger.info("Whisper model loaded")

    def feed_audio(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> None:
        """Feed an audio chunk into the buffer.

        Args:
            audio_chunk: float32 audio data normalized to [-1, 1]
            sample_rate: sample rate of the input (will be resampled to 16kHz)
        """
        if sample_rate != self._sample_rate:
            from .audio_utils import resample, int16_to_float32

            if audio_chunk.dtype == np.int16:
                audio_chunk = int16_to_float32(audio_chunk)
            ratio = self._sample_rate / sample_rate
            new_len = int(len(audio_chunk) * ratio)
            audio_chunk = np.interp(
                np.linspace(0, len(audio_chunk) - 1, new_len),
                np.arange(len(audio_chunk)),
                audio_chunk,
            ).astype(np.float32)
        elif audio_chunk.dtype == np.int16:
            audio_chunk = audio_chunk.astype(np.float32) / 32768.0

        self._buffer = np.concatenate([self._buffer, audio_chunk])

        # Track silence for end-of-speech detection
        rms = np.sqrt(np.mean(audio_chunk**2))
        if rms < self._silence_threshold:
            self._silence_duration += len(audio_chunk) / self._sample_rate
        else:
            self._silence_duration = 0.0
            self._speech_detected = True

    def is_speech_complete(self, silence_timeout: float = 1.5) -> bool:
        """Check if the speaker has stopped talking.

        Returns True if speech was detected and then silence lasted
        longer than silence_timeout seconds.
        """
        if not self._speech_detected:
            return False
        return self._silence_duration >= silence_timeout

    def transcribe(self) -> str:
        """Transcribe the current buffer and reset.

        Returns:
            Transcribed text, or empty string if not enough audio.
        """
        duration = len(self._buffer) / self._sample_rate
        if duration < self._min_duration:
            return ""

        logger.debug(f"Transcribing {duration:.1f}s of audio")
        segments, info = self.model.transcribe(
            self._buffer,
            beam_size=1,  # Faster, slightly less accurate
            language="en",
            vad_filter=True,  # Filter out non-speech
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()
        logger.info(f"Transcribed: '{text}'")

        # Reset buffer
        self.reset()
        return text

    def reset(self) -> None:
        """Clear the audio buffer and state."""
        self._buffer = np.array([], dtype=np.float32)
        self._silence_duration = 0.0
        self._speech_detected = False

    @property
    def buffer_duration(self) -> float:
        """Duration of audio currently in the buffer (seconds)."""
        return len(self._buffer) / self._sample_rate
