"""Text-to-Speech using Bark by Suno — supports natural non-verbal expressions.

Bark natively supports: [laughs], [sighs], [clears throat], [gasps], ... for hesitation,
♪ for singing, and CAPITALIZATION for emphasis. Runs locally, no API key needed.

First run downloads models (~5GB). Subsequent runs are fast from cache.
"""

import asyncio
import io
import logging
from pathlib import Path

import numpy as np
import pygame
import pygame.mixer
import scipy.io.wavfile

logger = logging.getLogger(__name__)

# Bark speaker presets — these control the voice character
# Format: "v2/{language}_speaker_{N}" where N is 0-9
# Each number is a different voice. Preview them to find the best fit.
VOICE_MAP = {
    # Trollers
    "elderly_cat_lover": "v2/en_speaker_1",    # Softer female voice → Margaret
    "horoscope_karen": "v2/en_speaker_4",      # Younger female voice → Jayden
    "overly_enthusiastic": "v2/en_speaker_3",  # Energetic male voice → Brad
    # Spammers
    "car_warranty": "v2/en_speaker_6",         # Smooth male → Kevin
    "tech_support": "v2/en_speaker_7",         # Neutral male → "Steve"
    "crypto_bro": "v2/en_speaker_0",           # Confident male → Jordan
}

SFX_DIR = Path(__file__).resolve().parent.parent / "sfx"

# Background SFX per persona (reuse ElevenLabs-generated ones if available)
SFX_MAP = {
    "elderly_cat_lover": [("cat_meow.mp3", 0.3), ("cup_clink.mp3", 0.15)],
    "horoscope_karen": [("notification.mp3", 0.15)],
    "overly_enthusiastic": [],
    "car_warranty": [("keyboard_typing.mp3", 0.15)],
    "tech_support": [("keyboard_typing.mp3", 0.25)],
    "crypto_bro": [("notification.mp3", 0.1)],
}

_model_loaded = False
_mixer_initialized = False


def _ensure_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
        pygame.mixer.set_num_channels(4)
        _mixer_initialized = True


def _ensure_model():
    """Load Bark models on first use. Downloads ~5GB on first run."""
    global _model_loaded
    if not _model_loaded:
        from bark import preload_models
        logger.info("Loading Bark models (first run downloads ~5GB)...")
        preload_models()
        _model_loaded = True
        logger.info("Bark models loaded!")


def _maybe_play_sfx(persona: str):
    """Randomly play a background sound after speech."""
    import random
    sfx_list = SFX_MAP.get(persona, [])
    for filename, probability in sfx_list:
        if random.random() < probability:
            sfx_path = SFX_DIR / filename
            if sfx_path.exists():
                try:
                    sound = pygame.mixer.Sound(str(sfx_path))
                    sound.set_volume(0.08)
                    channel = pygame.mixer.find_channel()
                    if channel:
                        channel.play(sound)
                except Exception:
                    pass
            break


def _synthesize_and_play(text: str, persona: str) -> None:
    """Generate speech with Bark and play it."""
    if not text.strip():
        return

    _ensure_model()
    from bark import generate_audio, SAMPLE_RATE

    voice_preset = VOICE_MAP.get(persona, "v2/en_speaker_1")

    try:
        # Bark generates float32 audio at 24kHz
        audio_array = generate_audio(
            text,
            history_prompt=voice_preset,
            text_temp=0.7,      # Lower = more consistent voice
            waveform_temp=0.7,  # Lower = cleaner audio
        )

        # Convert to int16 for pygame
        audio_int16 = (audio_array * 32767).clip(-32768, 32767).astype(np.int16)

        _ensure_mixer()

        sound = pygame.mixer.Sound(audio_int16.tobytes())
        channel = pygame.mixer.find_channel(True)
        channel.play(sound)
        while channel.get_busy():
            pygame.time.wait(50)

        # Play ambient SFX after speech
        _maybe_play_sfx(persona)

    except Exception as e:
        logger.error(f"Bark TTS error: {e}")


async def say_text_async(text: str, persona: str) -> None:
    """Async wrapper — runs Bark synthesis in a thread."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _synthesize_and_play, text, persona)
