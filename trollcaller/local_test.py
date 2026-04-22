"""Local test mode — use your microphone and speakers instead of Twilio.

Run with: python -m trollcaller.local_test
"""

import asyncio
import logging
import sys

import numpy as np
import sounddevice as sd

from .pipeline import ConversationPipeline
from .prompts import PERSONAS, DEFAULT_PERSONA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # Record at 16kHz for Whisper
BLOCK_SIZE = 1600  # 100ms chunks


async def main(persona: str = DEFAULT_PERSONA):
    """Run the conversation pipeline locally with mic input and speaker output."""
    print("\n🤙 TrollCaller — Local Test Mode")
    print(f"   Persona: {PERSONAS[persona]['name']} ({PERSONAS[persona]['description']})")
    print("   Speak into your microphone. Press Ctrl+C to quit.\n")

    pipeline = ConversationPipeline(persona=persona)

    # Play greeting
    print("🔊 Playing greeting...")
    greeting_audio, greeting_sr = await pipeline.get_greeting_audio()
    if len(greeting_audio) > 0:
        sd.play(greeting_audio, greeting_sr)
        sd.wait()
    print("🎤 Listening... (speak now)\n")

    # Audio callback feeds chunks to the pipeline
    def audio_callback(indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        audio = indata[:, 0].copy()  # Mono
        # Convert float32 to int16 for the pipeline
        audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        pipeline.feed_caller_audio(audio_int16, sample_rate=SAMPLE_RATE)

    # Start recording
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="float32",
        callback=audio_callback,
    )

    try:
        with stream:
            while True:
                await asyncio.sleep(0.1)

                if pipeline.is_caller_done_speaking(silence_timeout=1.5):
                    # Generate response
                    print("🤖 Thinking...")
                    text, audio, sr = await pipeline.generate_response()
                    if text:
                        print(f"🤖 {PERSONAS[persona]['name']}: {text}")
                        if len(audio) > 0:
                            sd.play(audio, sr)
                            sd.wait()
                        print("🎤 Listening...\n")

    except KeyboardInterrupt:
        print(f"\n\n📞 Call ended. Duration: {pipeline.call_duration:.0f}s")
        print("👋 Bye!")


if __name__ == "__main__":
    persona = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PERSONA
    if persona not in PERSONAS:
        print(f"Unknown persona '{persona}'. Available: {list(PERSONAS.keys())}")
        sys.exit(1)
    asyncio.run(main(persona))
