"""Generate background sound effects using ElevenLabs Sound Effects API."""

from dotenv import load_dotenv; load_dotenv()
from elevenlabs import ElevenLabs
from pathlib import Path
import os

SFX_DIR = Path(__file__).parent.parent / "sfx"
SFX_DIR.mkdir(exist_ok=True)

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

SOUNDS = {
    "cat_meow.mp3": ("cat meowing softly, single meow, indoor", 1.5),
    "cat_purr.mp3": ("cat purring contentedly, close up", 3.0),
    "keyboard_typing.mp3": ("keyboard typing, a few keystrokes on a laptop", 2.0),
    "phone_static.mp3": ("subtle phone line static and crackle, telephone", 2.0),
    "doorbell.mp3": ("doorbell ringing once, ding dong", 2.0),
    "cup_clink.mp3": ("tea cup being set on a saucer, ceramic clink", 1.0),
    "paper_rustling.mp3": ("paper rustling and shuffling on a desk", 2.0),
    "notification.mp3": ("phone notification ping sound", 1.0),
}

for filename, (description, duration) in SOUNDS.items():
    path = SFX_DIR / filename
    if path.exists():
        print(f"  ✓ {filename} already exists, skipping")
        continue
    print(f"  ⬇ Generating: {filename} ({description})...")
    try:
        result = client.text_to_sound_effects.convert(
            text=description,
            duration_seconds=duration,
        )
        audio = b"".join(result)
        path.write_bytes(audio)
        print(f"  ✓ Saved {filename} ({len(audio)//1024}KB)")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

print("\n✅ Done! Sound effects saved to sfx/")
