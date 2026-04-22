"""LLM vs LLM battle mode — a spammer LLM calls the troller LLM.

No microphone or Twilio needed! Two LLMs talking with real voices.
Run with: python -m trollcaller.battle [--silent] [--record] [troller] [spammer] [turns]
"""

import asyncio
import logging
import sys
from datetime import datetime

from .llm import ConversationLLM
from .tts_hume import say_text_async, synthesize_audio, play_audio_and_record, _clean_text, enable_recording, save_recording
from .prompts import PERSONAS, SPAMMERS, DEFAULT_PERSONA, DEFAULT_SPAMMER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Colors for terminal output
CYAN = "\033[96m"
YELLOW = "\033[93m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"


async def speak(text: str, persona: str, voice_enabled: bool = True):
    """Speak text with the persona's voice if enabled."""
    if voice_enabled:
        await say_text_async(text, persona)


async def battle(
    troller_persona: str = DEFAULT_PERSONA,
    spammer_persona: str = DEFAULT_SPAMMER,
    max_turns: int = 30,
    voice: bool = True,
    record: bool = False,
):
    """Run an LLM-vs-LLM conversation with real voices.

    The spammer initiates the call and tries to scam.
    The troller answers and wastes the spammer's time.
    """
    troller_info = PERSONAS[troller_persona]
    spammer_info = SPAMMERS[spammer_persona]

    print(f"\n{'='*60}")
    print(f"  🤙 TrollCaller — LLM vs LLM Battle Mode")
    print(f"  🔊 Voice: {'ON' if voice else 'OFF (use --silent to toggle)'}")
    print(f"{'='*60}")
    print(f"  📞 Spammer:  {YELLOW}{spammer_info['name']}{RESET} ({spammer_info['description']})")
    print(f"  🛡️  Troller:  {CYAN}{troller_info['name']}{RESET} ({troller_info['description']})")
    print(f"  🔄 Max turns: {max_turns}")
    print(f"{'='*60}\n")

    # Enable recording if requested
    if record:
        enable_recording()
        print(f"  🔴 Recording enabled — audio will be saved after the call\n")

    # Create both LLMs
    troller = ConversationLLM(persona=troller_persona)
    spammer = ConversationLLM.__new__(ConversationLLM)
    # Manually init the spammer with spammer prompt + context about who they're calling
    gender = troller_info.get("gender", "unknown")
    honorific = "ma'am" if gender == "female" else "sir"
    spammer.persona = spammer_persona
    spammer.system_prompt = (
        spammer_info["system_prompt"]
        + f"\nThe person you are calling is a {gender}. Address them as \"{honorific}\" until you learn their name. Once you know their name, use ONLY their first name — never combine it with sir/ma'am/Mr/Ms."
    )
    spammer.history = []
    from .config import settings
    import ollama
    spammer.client = ollama.AsyncClient(host=settings.ollama_host)

    # Spammer opens the call
    spammer_openers = {
        "car_warranty": "Hi! this is Kevin from the Vehicle Department, your car warranty is about to expire today! Do you have a moment to renew it and avoid costly repairs?",
        "tech_support": "Hello, this is Microsoft Technical Support. We've detected unusual activity on your computer. Are you near your PC?",
        "crypto_bro": "Hey, got your number from a mutual friend. I have an investment opportunity you'd be perfect for — got a minute?",
    }
    spammer_text = spammer_openers.get(spammer_persona, "Hello, do you have a moment?")
    print(f"  {YELLOW}{BOLD}📞 {spammer_info['name']}:{RESET} {spammer_text}\n")

    if voice:
        # Pipeline: LLM generates troller response + synthesize spammer audio in parallel
        troller_text_coro = troller.generate_response(spammer_text)
        spammer_audio_coro = synthesize_audio(spammer_text, spammer_persona)
        troller_text, spammer_audio = await asyncio.gather(troller_text_coro, spammer_audio_coro)
        troller_text = _clean_text(troller_text)

        # Play spammer audio, then immediately print troller response
        await play_audio_and_record(spammer_audio)
        print(f"  {CYAN}{BOLD}🛡️  {troller_info['name']}:{RESET} {troller_text}\n")

        # Back-and-forth with full pipelining
        for turn in range(max_turns - 1):
            # Synthesize troller audio + generate spammer LLM in parallel
            troller_audio_coro = synthesize_audio(troller_text, troller_persona)
            spammer_text_coro = spammer.generate_response(troller_text)
            spammer_text, troller_audio = await asyncio.gather(spammer_text_coro, troller_audio_coro)
            spammer_text = _clean_text(spammer_text)

            # Play troller audio, then print spammer response
            await play_audio_and_record(troller_audio)
            print(f"  {YELLOW}{BOLD}📞 {spammer_info['name']}:{RESET} {spammer_text}\n")

            # Synthesize spammer audio + generate troller LLM in parallel
            spammer_audio_coro = synthesize_audio(spammer_text, spammer_persona)
            troller_text_coro = troller.generate_response(spammer_text)
            troller_text, spammer_audio = await asyncio.gather(troller_text_coro, spammer_audio_coro)
            troller_text = _clean_text(troller_text)

            # Play spammer audio, then print troller response
            await play_audio_and_record(spammer_audio)
            print(f"  {CYAN}{BOLD}🛡️  {troller_info['name']}:{RESET} {troller_text}\n")
    else:
        # Silent mode — no TTS
        troller_text = _clean_text(await troller.generate_response(spammer_text))
        print(f"  {CYAN}{BOLD}🛡️  {troller_info['name']}:{RESET} {troller_text}\n")

        for turn in range(max_turns - 1):
            spammer_text = _clean_text(await spammer.generate_response(troller_text))
            print(f"  {YELLOW}{BOLD}📞 {spammer_info['name']}:{RESET} {spammer_text}\n")
            troller_text = _clean_text(await troller.generate_response(spammer_text))
            print(f"  {CYAN}{BOLD}🛡️  {troller_info['name']}:{RESET} {troller_text}\n")

    print(f"\n{'='*60}")
    print(f"  📞 Call ended after {max_turns} turns")
    print(f"  The spammer wasted a LOT of time. Mission accomplished! 🎉")
    print(f"{'='*60}\n")

    if record:
        import os
        os.makedirs("recordings", exist_ok=True)
        filename = f"recordings/battle_{troller_persona}_vs_{spammer_persona}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        save_recording(filename)
        print(f"  💾 Recording saved to {filename}\n")


def _resolve_persona(name: str) -> str | None:
    """Resolve a persona by key or character name (case-insensitive)."""
    if name in PERSONAS:
        return name
    if name in SPAMMERS:
        return name
    # Try matching by character name
    lower = name.lower()
    for key, info in {**PERSONAS, **SPAMMERS}.items():
        if info["name"].lower() == lower:
            return key
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    voice = "--silent" not in flags
    record = "--record" in flags

    troller_names = {v["name"]: k for k, v in PERSONAS.items()}
    spammer_names = {v["name"]: k for k, v in SPAMMERS.items()}

    troller_input = args[0] if len(args) > 0 else DEFAULT_PERSONA
    spammer_input = args[1] if len(args) > 1 else DEFAULT_SPAMMER
    turns = int(args[2]) if len(args) > 2 else 20

    troller = _resolve_persona(troller_input)
    if troller not in PERSONAS:
        print(f"Unknown troller '{troller_input}'. Available: {list(troller_names.keys())}")
        sys.exit(1)
    spammer = _resolve_persona(spammer_input)
    if spammer not in SPAMMERS:
        print(f"Unknown spammer '{spammer_input}'. Available: {list(spammer_names.keys())}")
        sys.exit(1)

    print(f"\nUsage: python -m trollcaller.battle [--silent] [--record] [troller] [spammer] [turns]")
    print(f"  Trollers: {list(troller_names.keys())}")
    print(f"  Spammers: {list(spammer_names.keys())}")

    asyncio.run(battle(troller, spammer, turns, voice, record))


if __name__ == "__main__":
    main()
