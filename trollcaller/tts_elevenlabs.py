"""Text-to-Speech using ElevenLabs with background sound effects.

Uses the best-matching voices and overlays ambient sounds
(cat meowing, keyboard clicks, etc.) for immersion.
"""

import asyncio
import io
import logging
import tempfile
from pathlib import Path

import pygame
import pygame.mixer
from elevenlabs import ElevenLabs

logger = logging.getLogger(__name__)

SFX_DIR = Path(__file__).resolve().parent.parent / "sfx"

# ── Voice mapping (best character fit from your account) ─────────────────────

VOICE_MAP = {
    # Trollers
    "elderly_cat_lover": "pFZP5JQG7iQjIQuC4Bku",   # Lily — velvety, British, middle-aged (slowed down for grandma feel) → Margaret
    "horoscope_karen": "cgSgspJ2msm6clMCkdW9",      # Jessica — playful, bright, young → Jayden
    "overly_enthusiastic": "IKne3meq5aSn9XLyUdCD",   # Charlie — deep, energetic, Australian → Brad
    # Spammers
    "car_warranty": "cjVigY5qzO86Huf0OWal",          # Eric — smooth, trustworthy (perfect scammer) → Kevin
    "tech_support": "onwK4e9ZLuTAKqWW03F9",          # Daniel — steady broadcaster → "Steve"
    "crypto_bro": "N2lVS1w4EtoT3dr4eOWO",            # Callum — husky trickster → Jordan
}

# Lower stability = more expressive/human. Higher style = more dramatic.
VOICE_SETTINGS = {
    "elderly_cat_lover": {"stability": 0.35, "similarity_boost": 0.80, "style": 0.40, "speed": 0.85},
    "horoscope_karen":   {"stability": 0.30, "similarity_boost": 0.80, "style": 0.50, "speed": 1.0},
    "overly_enthusiastic": {"stability": 0.25, "similarity_boost": 0.75, "style": 0.60, "speed": 1.15},
    "car_warranty":      {"stability": 0.50, "similarity_boost": 0.85, "style": 0.30, "speed": 1.05},
    "tech_support":      {"stability": 0.55, "similarity_boost": 0.80, "style": 0.20, "speed": 0.95},
    "crypto_bro":        {"stability": 0.30, "similarity_boost": 0.80, "style": 0.50, "speed": 1.1},
}

# Background SFX per persona: (filename, probability per turn)
SFX_MAP = {
    "elderly_cat_lover": [("cat_meow.mp3", 0.35), ("cat_purr.mp3", 0.15), ("cup_clink.mp3", 0.15)],
    "horoscope_karen": [("notification.mp3", 0.2), ("paper_rustling.mp3", 0.1)],
    "overly_enthusiastic": [("notification.mp3", 0.1)],
    "car_warranty": [("keyboard_typing.mp3", 0.2), ("phone_static.mp3", 0.1)],
    "tech_support": [("keyboard_typing.mp3", 0.3), ("phone_static.mp3", 0.15)],
    "crypto_bro": [("notification.mp3", 0.15)],
}

import random

_mixer_initialized = False
_client = None


def _ensure_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.set_num_channels(4)
        _mixer_initialized = True


def _maybe_play_sfx(persona: str):
    """Randomly play a background sound effect for this persona."""
    sfx_list = SFX_MAP.get(persona, [])
    for filename, probability in sfx_list:
        if random.random() < probability:
            sfx_path = SFX_DIR / filename
            if sfx_path.exists():
                try:
                    sound = pygame.mixer.Sound(str(sfx_path))
                    sound.set_volume(0.08)  # Very quiet, just ambient
                    channel = pygame.mixer.find_channel()
                    if channel:
                        channel.play(sound)
                except Exception as e:
                    pass
            break


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        import os
        from .config import settings
        api_key = settings.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set! Add it to your .env file.\n"
                "Get a free key at: https://elevenlabs.io"
            )
        _client = ElevenLabs(api_key=api_key)
    return _client


def _clean_text(text: str) -> str:
    """Strip non-verbal cues like *laughs*, (sighs), [pauses] etc."""
    import re
    # Remove *action*, (action), [action] markers
    text = re.sub(r'\*[^*]+\*', '', text)
    text = re.sub(r'\([^)]+\)', '', text)
    text = re.sub(r'\[[^\]]+\]', '', text)
    # Remove common written-out stage directions without brackets
    text = re.sub(r'(?i)\b(laughs|sighs|pauses|chuckles|coughs|clears throat|gasps|giggles|snorts|whispers)\b', '', text)
    # Clean up extra whitespace and dangling punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[,;:\s]+', '', text)
    return text


def _synthesize_and_play(text: str, persona: str) -> None:
    """Generate audio with ElevenLabs and play it."""
    text = _clean_text(text)
    if not text:
        return

    voice_id = VOICE_MAP.get(persona, "EXAVITQu4vr4xnSDxMaL")
    vs = VOICE_SETTINGS.get(persona, {})

    client = _get_client()

    try:
        audio_gen = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",  # Best quality model
            output_format="mp3_44100_128",
            voice_settings={
                "stability": vs.get("stability", 0.5),
                "similarity_boost": vs.get("similarity_boost", 0.75),
                "style": vs.get("style", 0.0),
                "use_speaker_boost": True,
                "speed": vs.get("speed", 1.0),
            },
        )

        audio_bytes = b"".join(audio_gen)

        _ensure_mixer()

        sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
        channel = pygame.mixer.find_channel(True)
        channel.play(sound)
        while channel.get_busy():
            pygame.time.wait(50)

        # Play ambient SFX *after* speech, in the pause between turns
        _maybe_play_sfx(persona)

    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")


async def say_text_async(text: str, persona: str) -> None:
    """Async wrapper — runs synthesis in a thread to not block the event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _synthesize_and_play, text, persona)
