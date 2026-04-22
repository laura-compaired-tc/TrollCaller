"""Text-to-Speech using Piper TTS for local, fast voice synthesis."""

import io
import logging
import subprocess
import wave
from pathlib import Path
from typing import Optional

import numpy as np

from .config import settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Piper TTS wrapper for fast local speech synthesis."""

    def __init__(self):
        self.voice = settings.piper_voice
        self.voices_dir = settings.voices_dir
        self.model_path = self.voices_dir / f"{self.voice}.onnx"
        self.config_path = self.voices_dir / f"{self.voice}.onnx.json"
        self._sample_rate = 22050  # Piper's default output rate

        if not self.model_path.exists():
            logger.warning(
                f"Piper voice model not found at {self.model_path}. "
                "Run: python scripts/download_piper_voice.py"
            )
        else:
            logger.info(f"Piper TTS ready with voice: {self.voice}")

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """Synthesize text to audio.

        Args:
            text: Text to speak.

        Returns:
            Tuple of (audio_data as int16 numpy array, sample_rate).
        """
        if not text.strip():
            return np.array([], dtype=np.int16), self._sample_rate

        if not self.model_path.exists():
            logger.error("Piper model not found!")
            return np.array([], dtype=np.int16), self._sample_rate

        try:
            # Run piper as subprocess for simplicity
            # Piper reads from stdin and writes WAV to stdout
            cmd = [
                "piper",
                "--model", str(self.model_path),
                "--output-raw",
                "--length_scale", "1.1",  # Slightly slower = more natural
            ]

            process = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )

            if process.returncode != 0:
                logger.error(f"Piper error: {process.stderr.decode()}")
                return np.array([], dtype=np.int16), self._sample_rate

            # Piper --output-raw gives raw 16-bit signed PCM at 22050Hz
            audio = np.frombuffer(process.stdout, dtype=np.int16)
            logger.debug(f"Synthesized {len(audio)/self._sample_rate:.1f}s of audio for: '{text[:50]}...'")
            return audio, self._sample_rate

        except FileNotFoundError:
            logger.error(
                "Piper not found. Install with: pip install piper-tts"
            )
            return np.array([], dtype=np.int16), self._sample_rate
        except subprocess.TimeoutExpired:
            logger.error("Piper TTS timed out")
            return np.array([], dtype=np.int16), self._sample_rate

    def synthesize_for_twilio(self, text: str) -> Optional[bytes]:
        """Synthesize text and convert to Twilio-compatible μ-law 8kHz format.

        Returns:
            Base64-encoded μ-law audio, or None on failure.
        """
        from .audio_utils import resample, pcm_to_mulaw

        audio, sr = self.synthesize(text)
        if len(audio) == 0:
            return None

        # Resample from 22050Hz to 8000Hz (Twilio's rate)
        audio_8k = resample(audio, sr, 8000)
        # Convert to μ-law
        return pcm_to_mulaw(audio_8k)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate
