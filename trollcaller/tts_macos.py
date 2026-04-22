"""Text-to-Speech using macOS built-in `say` command.

Zero dependencies — works on any Mac out of the box.
Each persona gets a distinct voice for easy identification.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Map personas to macOS voices that fit their character
VOICE_MAP = {
    # Trollers
    "elderly_cat_lover": "Samantha",       # Warm, mature female voice → Margaret
    "horoscope_karen": "Junior",           # Young, slightly nasal → Jayden
    "overly_enthusiastic": "Fred",         # Energetic male → Brad
    # Spammers
    "car_warranty": "Daniel",              # British, authoritative → Kevin
    "tech_support": "Ralph",               # Flat, robotic-ish → "Steve"
    "crypto_bro": "Albert",               # Fast, slightly nerdy → Jordan
}

# Speaking rates (words per minute) — tuned per persona
RATE_MAP = {
    "elderly_cat_lover": 160,    # Slower, elderly
    "horoscope_karen": 200,      # Normal-fast, young
    "overly_enthusiastic": 220,  # Fast, excited
    "car_warranty": 190,         # Telemarketer pace
    "tech_support": 170,         # Measured, "professional"
    "crypto_bro": 210,           # Fast, salesy
}


def say_text(text: str, persona: str, wait: bool = True) -> Optional[subprocess.Popen]:
    """Speak text using macOS `say` with the persona's voice.

    Args:
        text: Text to speak.
        persona: Persona key to select voice.
        wait: If True, block until speech finishes.

    Returns:
        The Popen process if wait=False, else None.
    """
    voice = VOICE_MAP.get(persona, "Samantha")
    rate = RATE_MAP.get(persona, 180)

    cmd = ["say", "-v", voice, "-r", str(rate), text]

    if wait:
        subprocess.run(cmd, check=False)
        return None
    else:
        return subprocess.Popen(cmd)


async def say_text_async(text: str, persona: str) -> None:
    """Async version — speaks without blocking the event loop."""
    voice = VOICE_MAP.get(persona, "Samantha")
    rate = RATE_MAP.get(persona, 180)

    proc = await asyncio.create_subprocess_exec(
        "say", "-v", voice, "-r", str(rate), text,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


def say_to_audio(text: str, persona: str) -> tuple[np.ndarray, int]:
    """Synthesize text to a numpy audio array using macOS `say`.

    Useful for piping into Twilio or recording.

    Returns:
        Tuple of (audio_data as int16 numpy array, sample_rate).
    """
    voice = VOICE_MAP.get(persona, "Samantha")
    rate = RATE_MAP.get(persona, 180)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
        tmpfile = f.name

    cmd = ["say", "-v", voice, "-r", str(rate), "-o", tmpfile, "--data-format=LEI16@22050", text]
    subprocess.run(cmd, check=True)

    audio, sr = sf.read(tmpfile, dtype="int16")
    Path(tmpfile).unlink(missing_ok=True)
    return audio, sr


def list_available_voices() -> list[str]:
    """List all English voices available on this Mac."""
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    voices = []
    for line in result.stdout.splitlines():
        if "en_US" in line or "en_GB" in line:
            name = line.split()[0]
            voices.append(name)
    return voices
