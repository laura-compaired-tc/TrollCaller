"""Text-to-Speech using Microsoft Edge TTS — free, natural-sounding voices.

No API key needed. Uses the same neural voices as Microsoft Edge's Read Aloud.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

import edge_tts
import pygame
import pygame.mixer

logger = logging.getLogger(__name__)

# Natural-sounding Edge TTS voices mapped to personas
VOICE_MAP = {
    # Trollers
    "elderly_cat_lover": "en-US-JennyNeural",         # Warm, mature female → Margaret
    "horoscope_karen": "en-US-AriaNeural",             # Young, expressive female → Jayden
    "overly_enthusiastic": "en-US-GuyNeural",          # Energetic male → Brad
    # Spammers
    "car_warranty": "en-US-DavisNeural",               # Smooth male → Kevin
    "tech_support": "en-IN-PrabhatNeural",             # Indian accent male → "Steve"
    "crypto_bro": "en-US-JasonNeural",                 # Confident male → Jordan
}

# Speaking rates per persona (Edge TTS uses percentage offset like "+10%" or "-5%")
RATE_MAP = {
    "elderly_cat_lover": "-10%",     # Slower, elderly
    "horoscope_karen": "+5%",        # Normal-fast, animated
    "overly_enthusiastic": "+15%",   # Fast, excited
    "car_warranty": "+5%",           # Brisk telemarketer
    "tech_support": "-5%",           # Measured, "professional"
    "crypto_bro": "+10%",            # Fast, salesy
}

# Pitch adjustments
PITCH_MAP = {
    "elderly_cat_lover": "-5Hz",
    "horoscope_karen": "+5Hz",
    "overly_enthusiastic": "+3Hz",
    "car_warranty": None,
    "tech_support": None,
    "crypto_bro": "+2Hz",
}

# Initialize pygame mixer once
_mixer_initialized = False


def _ensure_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        pygame.mixer.init()
        _mixer_initialized = True


async def say_text_async(text: str, persona: str) -> None:
    """Speak text using Edge TTS with the persona's voice.

    Generates audio via Edge TTS and plays it with pygame.
    """
    if not text.strip():
        return

    voice = VOICE_MAP.get(persona, "en-US-JennyNeural")
    rate = RATE_MAP.get(persona, "+0%")
    pitch = PITCH_MAP.get(persona, "+0%")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmpfile = f.name

    try:
        kwargs = {"voice": voice}
        if rate:
            kwargs["rate"] = rate
        if pitch:
            kwargs["pitch"] = pitch
        communicate = edge_tts.Communicate(text, **kwargs)
        await communicate.save(tmpfile)

        _ensure_mixer()
        pygame.mixer.music.load(tmpfile)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)
    except Exception as e:
        logger.error(f"Edge TTS error: {e}")
    finally:
        Path(tmpfile).unlink(missing_ok=True)
