# 🤙 TrollCaller

> LLM vs LLM battle mode — *Why just detect spammers when you can troll them?*

Two AI characters have a phone call: a **spammer** tries to scam, and a **troller** wastes their time with increasingly absurd responses — all with realistic AI voices. Built for Truecaller Lab Days (April 2026).

## Demo

Run a battle and listen live, or use `--record` to save the call as an MP3:

```bash
python -m trollcaller.battle Margaret Kevin 10 --record
```

Recorded demos are in the `recordings/` folder.

## Architecture

```
┌─────────────────┐       ┌─────────────────┐
│  Spammer LLM    │◄─────►│  Troller LLM    │
│  (e.g. Kevin)   │       │  (e.g. Margaret) │
└────────┬────────┘       └────────┬────────┘
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────┐
│         Hume Octave TTS                  │
│   Custom voices per character            │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│         Battle Engine (asyncio)          │
│   Parallel pipeline: LLM + TTS overlap  │
│   --record saves full call as MP3       │
└──────────────────────────────────────────┘
```

**Key trick:** While TTS synthesizes the current line, the LLM generates the next response — cutting latency roughly in half.

## Components

| Component | What | Implementation |
|-----------|------|----------------|
| LLM | Generates dialogue in character | Ollama + gemma2:9b (local, free) |
| TTS | Realistic voice synthesis | Hume Octave (custom voices per persona) |
| Battle Engine | Turn-by-turn orchestration | Python asyncio parallel pipeline |
| Recording | Save calls as MP3 | `--record` flag, saved to `recordings/` |

## Characters

### Trollers 🛡️
| Name | Persona | Style |
|------|---------|-------|
| **Margaret** | Elderly cat lady | Sweet & confused → cat has a law degree |
| **Jayden** | Astrology Karen | Asks your zodiac sign → Yelp reviews your aura |
| **Brad** | Lonely enthusiast | Friendly & eager → names his goldfish after you |

### Spammers 📞
| Name | Scam | Style |
|------|------|-------|
| **Kevin** | Car warranty | Pushy, vague "Vehicle Department" |
| **Maria** | Fake tech support | Concerned, made-up jargon |
| **Jordan** | Crypto investment | Hype, fake testimonials |

All characters use **slow escalation** — they start believable and get progressively absurd.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed
- A [Hume](https://app.hume.ai/) API key (free tier works)

### 1. Install

```bash
cd TrollCaller
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Pull the LLM

```bash
ollama pull gemma2:9b
```

### 3. Configure

```bash
cp .env.example .env
# Add your HUME_API_KEY to .env
```

### 4. Run a battle

```bash
# With voice (default)
python -m trollcaller.battle Margaret Kevin

# Silent mode (text only, fast iteration)
python -m trollcaller.battle Margaret Kevin --silent

# Record the call as MP3
python -m trollcaller.battle Margaret Kevin 10 --record

# Mix and match characters
python -m trollcaller.battle Jayden Jordan 10 --record
python -m trollcaller.battle Brad Maria 10 --record
```

**Usage:** `python -m trollcaller.battle [troller] [spammer] [turns] [--silent] [--record]`

## Project Structure

```
TrollCaller/
├── trollcaller/
│   ├── battle.py          # LLM vs LLM battle engine
│   ├── llm.py             # Ollama async client + sentence truncation
│   ├── tts_hume.py        # Hume Octave TTS + recording
│   ├── prompts.py         # Character personas (the fun part!)
│   └── config.py          # Pydantic settings from .env
├── recordings/            # Saved battle recordings (MP3)
├── sfx/                   # Sound effects
├── requirements.txt
├── .env.example
└── README.md
```

## User Guide

### Running a Battle

```
python -m trollcaller.battle [troller] [spammer] [turns] [--silent] [--record]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `troller` | Margaret | The troll character (Margaret, Jayden, or Brad) |
| `spammer` | Kevin | The scammer character (Kevin, Maria, or Jordan) |
| `turns` | 20 | Number of back-and-forth exchanges |
| `--silent` | off | Text-only mode, no voice (fast for testing prompts) |
| `--record` | off | Save the full call audio as an MP3 in `recordings/` |

### Example Battles

```bash
# Classic: sweet old lady vs car warranty scammer
python -m trollcaller.battle Margaret Kevin

# Astrology Karen vs crypto bro (chaotic)
python -m trollcaller.battle Jayden Jordan 10 --record

# Lonely guy vs fake tech support (heartbreaking + funny)
python -m trollcaller.battle Brad Maria 10 --record

# Quick text-only test (no TTS, instant)
python -m trollcaller.battle Margaret Kevin 5 --silent
```

### Tips

- **10 turns** is a good length for demos — enough for the escalation to kick in
- **`--record`** removes latency gaps, so recordings sound like natural calls
- **`--silent`** is great for tuning prompts without waiting for TTS
- Characters can be passed by name (Margaret) or key (elderly_cat_lover)
- Recordings are saved to `recordings/` with timestamps in the filename

## Prompt Engineering 🎭

The magic is in `trollcaller/prompts.py`:

- **Slow escalation** — Turns 1-3 sound real, turns 4-6 get odd, turns 7+ go fully absurd
- **No repetition** — Each reply must be fresh and different
- **Short bursts** — 1-2 sentences max (it's a phone call)
- **Spammer rules** — Never make up names, never break character, deflect charmingly

## Legal Note ⚖️

This is a hackathon demo. The "calls" are simulated LLM-vs-LLM conversations — no real phone calls are made.
