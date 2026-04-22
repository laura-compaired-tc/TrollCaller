"""Text-to-Speech using Hume Octave — emotionally intelligent TTS.

Voices are pre-created in the Hume dashboard and referenced by name.
Get a free API key at: https://app.hume.ai/keys
"""

import asyncio
import base64
import io
import logging
import re

import pygame
import pygame.mixer
from hume import AsyncHumeClient
from hume.tts import PostedUtterance, PostedUtteranceVoiceWithName

logger = logging.getLogger(__name__)

# Pre-created custom voices in Hume (locked — same voice every time)
VOICE_NAMES = {
    "elderly_cat_lover": "trollcaller_margaret",
    "horoscope_karen": "trollcaller_jayden",
    "overly_enthusiastic": "trollcaller_brad",
    "car_warranty": "trollcaller_kevin",
    "tech_support": "trollcaller_steve",
    "crypto_bro": "trollcaller_jordan",
}

_mixer_initialized = False
_client = None


def _ensure_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.set_num_channels(4)
        _mixer_initialized = True


def _get_client() -> AsyncHumeClient:
    global _client
    if _client is None:
        import os
        from .config import settings
        api_key = getattr(settings, 'hume_api_key', '') or os.getenv("HUME_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "HUME_API_KEY not set! Add it to your .env file.\n"
                "Get a free key at: https://app.hume.ai/keys"
            )
        _client = AsyncHumeClient(api_key=api_key)
    return _client


def _clean_text(text: str) -> str:
    """Remove stage directions like *pauses*, (laughs), [sighs], ...pauses..."""
    text = re.sub(r"\*[^*]+\*", "", text)        # *action*
    text = re.sub(r"\([^)]+\)", "", text)         # (action)
    text = re.sub(r"\[[^\]]+\]", "", text)        # [action]
    text = re.sub(r"\.\.\.?\s*\w+\s*\.\.\.?", "", text)  # ...pauses...
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Clean trailing artifacts that cause weird TTS noises
    text = re.sub(r"[.!?]{2,}", ".", text)          # multiple punctuation → single
    text = re.sub(r"\.{3,}", ".", text)              # ellipsis → period
    text = re.sub(r"\s*[—–\-]+\s*$", ".", text)     # trailing dashes → period
    text = re.sub(r"\s*\.{2,}\s*$", ".", text)       # trailing dots → period
    text = text.rstrip(" ,;:-—–")                    # strip trailing partial punctuation
    if text and text[-1] not in ".!?":
        text += "."                                   # ensure clean sentence ending
    return text


async def synthesize_audio(text: str, persona: str) -> bytes | None:
    """Synthesize speech audio, returning raw bytes (or None on failure)."""
    if not text.strip():
        return None

    text = _clean_text(text)
    if not text:
        return None

    voice_name = VOICE_NAMES.get(persona, "trollcaller_margaret")
    client = _get_client()

    try:
        utterance = PostedUtterance(
            text=text,
            voice=PostedUtteranceVoiceWithName(
                name=voice_name,
                provider="CUSTOM_VOICE",
            ),
        )

        result = await client.tts.synthesize_json(
            utterances=[utterance],
        )

        if not result.generations:
            logger.warning("No generations received from Hume")
            return None

        return base64.b64decode(result.generations[0].audio)

    except Exception as e:
        logger.error(f"Hume TTS error: {e}", exc_info=True)
        return None


async def play_audio(audio_bytes: bytes | None) -> None:
    """Play pre-synthesized audio bytes."""
    if not audio_bytes:
        return
    _ensure_mixer()
    sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
    channel = pygame.mixer.find_channel(True)
    channel.play(sound)
    while channel.get_busy():
        await asyncio.sleep(0.05)


# Recording buffer — collects all audio clips in order
_recording: list[bytes] = []
_recording_enabled = False


def enable_recording():
    """Start collecting audio for later export."""
    global _recording_enabled
    _recording_enabled = True
    _recording.clear()


def save_recording(filepath: str):
    """Save all collected audio clips to a single MP3 file."""
    if not _recording:
        logger.warning("No audio to save")
        return
    combined = b"".join(_recording)
    with open(filepath, "wb") as f:
        f.write(combined)
    logger.info(f"Recording saved to {filepath} ({len(_recording)} clips, {len(combined)} bytes)")


async def play_audio_and_record(audio_bytes: bytes | None) -> None:
    """Play audio and optionally add to recording buffer."""
    if not audio_bytes:
        return
    if _recording_enabled:
        _recording.append(audio_bytes)
    _ensure_mixer()
    sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
    channel = pygame.mixer.find_channel(True)
    channel.play(sound)
    while channel.get_busy():
        await asyncio.sleep(0.05)


async def say_text_async(text: str, persona: str) -> None:
    """Synthesize and play speech (convenience wrapper)."""
    audio = await synthesize_audio(text, persona)
    await play_audio_and_record(audio)
