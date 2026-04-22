"""Download Piper TTS voice model."""

import sys
import urllib.request
from pathlib import Path

VOICES_DIR = Path(__file__).parent.parent / "voices"

# Piper voice download URLs
VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
VOICE_FILES = [
    "en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json",
]


def download_voice():
    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    for filename in VOICE_FILES:
        dest = VOICES_DIR / filename
        if dest.exists():
            print(f"✓ {filename} already exists")
            continue

        url = f"{VOICE_BASE_URL}/{filename}"
        print(f"⬇ Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"✓ Saved to {dest}")
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}")
            print(f"  Manual download: {url}")
            sys.exit(1)

    print("\n✅ Piper voice model ready!")


if __name__ == "__main__":
    download_voice()
