"""Twilio Media Stream WebSocket handler."""

import asyncio
import base64
import json
import logging
from typing import Optional

import numpy as np
from starlette.websockets import WebSocket

from .pipeline import ConversationPipeline
from .audio_utils import twilio_audio_to_pcm, pcm_to_twilio_audio, resample
from .prompts import DEFAULT_PERSONA
from .config import settings

logger = logging.getLogger(__name__)


class MediaStreamHandler:
    """Handles a single Twilio Media Stream WebSocket connection."""

    def __init__(self, websocket: WebSocket, persona: str = DEFAULT_PERSONA):
        self.ws = websocket
        self.pipeline = ConversationPipeline(persona=persona)
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self._running = False
        self._response_task: Optional[asyncio.Task] = None

    async def handle(self) -> None:
        """Main handler for the WebSocket connection."""
        await self.ws.accept()
        self._running = True
        logger.info("WebSocket connected")

        try:
            # Send greeting after a short delay
            asyncio.create_task(self._send_greeting())

            # Start the response checking loop
            self._response_task = asyncio.create_task(self._response_loop())

            # Process incoming messages
            async for message in self.ws.iter_text():
                if not self._running:
                    break
                await self._handle_message(json.loads(message))

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self._running = False
            if self._response_task:
                self._response_task.cancel()
            logger.info(
                f"Call ended. Duration: {self.pipeline.call_duration:.0f}s"
            )

    async def _handle_message(self, msg: dict) -> None:
        """Process a single Twilio Media Stream message."""
        event = msg.get("event")

        if event == "start":
            self.stream_sid = msg["start"]["streamSid"]
            self.call_sid = msg["start"].get("callSid", "unknown")
            logger.info(f"Stream started: {self.stream_sid} (call: {self.call_sid})")

        elif event == "media":
            # Decode incoming audio and feed to STT
            payload = msg["media"]["payload"]
            pcm = twilio_audio_to_pcm(payload)
            self.pipeline.feed_caller_audio(pcm, sample_rate=8000)

        elif event == "stop":
            logger.info("Stream stopped by Twilio")
            self._running = False

    async def _response_loop(self) -> None:
        """Periodically check if caller is done speaking and respond."""
        while self._running:
            await asyncio.sleep(0.1)  # Check every 100ms

            if self.pipeline.is_caller_done_speaking(silence_timeout=1.5):
                await self._generate_and_send_response()

    async def _generate_and_send_response(self) -> None:
        """Generate a response and stream it back via WebSocket."""
        try:
            # Use streaming for lower latency
            async for sentence, audio, sr in self.pipeline.generate_response_streaming():
                if not self._running:
                    break
                # Convert to Twilio format (8kHz μ-law)
                audio_8k = resample(audio, sr, 8000)
                payload = pcm_to_twilio_audio(audio_8k)
                await self._send_audio(payload)

        except Exception as e:
            logger.error(f"Response generation error: {e}")

    async def _send_greeting(self) -> None:
        """Send initial greeting after connection is established."""
        await asyncio.sleep(1.0)  # Wait for stream to be ready
        if not self._running or not self.stream_sid:
            return

        try:
            audio, sr = await self.pipeline.get_greeting_audio()
            if len(audio) > 0:
                audio_8k = resample(audio, sr, 8000)
                payload = pcm_to_twilio_audio(audio_8k)
                await self._send_audio(payload)
        except Exception as e:
            logger.error(f"Greeting error: {e}")

    async def _send_audio(self, base64_payload: str) -> None:
        """Send audio back to Twilio via the WebSocket."""
        if not self.stream_sid:
            return

        # Twilio expects audio in chunks of ~20ms
        # At 8kHz μ-law, that's 160 bytes per chunk
        CHUNK_SIZE = 160
        raw = base64.b64decode(base64_payload)

        for i in range(0, len(raw), CHUNK_SIZE):
            if not self._running:
                break
            chunk = raw[i : i + CHUNK_SIZE]
            chunk_b64 = base64.b64encode(chunk).decode("ascii")

            msg = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": chunk_b64},
            }
            await self.ws.send_json(msg)
            # Pace the audio output (~20ms per chunk at 8kHz)
            await asyncio.sleep(0.02)

    async def _send_clear(self) -> None:
        """Tell Twilio to clear its audio buffer (for interruptions)."""
        if not self.stream_sid:
            return
        msg = {"event": "clear", "streamSid": self.stream_sid}
        await self.ws.send_json(msg)
