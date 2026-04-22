"""Download free sound effects for background ambience."""

import urllib.request
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent / "sfx"

# Free CC0 sound effects from freesound.org / pixabay (short clips)
# We'll generate simple ones with Python if download fails
SOUNDS = {
    "cat_meow": "cat_meow.wav",
    "cat_purr": "cat_purr.wav",
    "keyboard": "keyboard.wav",
    "phone_ring": "phone_ring.wav",
}


def generate_simple_sounds():
    """Generate basic sound effects using numpy (no download needed)."""
    import numpy as np
    import soundfile as sf

    SFX_DIR.mkdir(parents=True, exist_ok=True)

    sr = 22050

    # Cat meow — sine sweep
    t = np.linspace(0, 0.6, int(sr * 0.6))
    freq = 800 - 300 * t  # descending pitch
    meow = 0.3 * np.sin(2 * np.pi * freq * t) * np.exp(-3 * t)
    sf.write(str(SFX_DIR / "cat_meow.wav"), meow.astype(np.float32), sr)

    # Cat purr — low rumble
    t = np.linspace(0, 2.0, int(sr * 2.0))
    purr = 0.1 * np.sin(2 * np.pi * 25 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))
    sf.write(str(SFX_DIR / "cat_purr.wav"), purr.astype(np.float32), sr)

    # Keyboard clicking
    clicks = np.zeros(int(sr * 1.5))
    for i in range(8):
        pos = int(sr * (0.1 + i * 0.15 + np.random.uniform(-0.02, 0.02)))
        if pos < len(clicks) - 200:
            click = 0.2 * np.random.randn(200) * np.exp(-np.linspace(0, 10, 200))
            clicks[pos:pos+200] += click
    sf.write(str(SFX_DIR / "keyboard.wav"), clicks.astype(np.float32), sr)

    # Phone static/hum
    t = np.linspace(0, 2.0, int(sr * 2.0))
    static = 0.02 * np.random.randn(len(t)) + 0.01 * np.sin(2 * np.pi * 60 * t)
    sf.write(str(SFX_DIR / "phone_static.wav"), static.astype(np.float32), sr)

    print(f"✅ Sound effects generated in {SFX_DIR}/")


if __name__ == "__main__":
    generate_simple_sounds()
