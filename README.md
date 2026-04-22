# 🤙 TrollCaller

> Voice-cloned spam-callback bot — *Lenny, but powered by LLMs*

A bot that answers spam calls with a realistic AI-generated voice, engages the scammer in a long pointless conversation, wasting their time. Built for Truecaller Lab Days (April 2026).

## Architecture

```
Incoming Call (Twilio)
        │
        ▼
   WebSocket Media Stream
        │
        ▼
┌──────────────────────┐
│   Python Server      │
│                      │
│  Audio In ──► Whisper (STT)
│                │
│                ▼
│           Ollama/LLM (Brain)
│                │
│                ▼
│           Piper TTS ──► Audio Out
└──────────────────────┘
```

## Components

| Component | What | Implementation |
|-----------|------|----------------|
| Phone number | Receives calls | Twilio (~$1/mo + $0.01/min) |
| STT | Transcribe caller | Whisper (local, free) |
| LLM | Generate stalling responses | Ollama + Llama 3.1 8B (local, free) |
| TTS | Speak back to caller | Piper TTS (local, free) |
| Glue code | Python server | FastAPI + WebSockets |

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed
- A Twilio account with a phone number
- [ngrok](https://ngrok.com/) for local development

### 1. Install dependencies

```bash
cd TrollCaller
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Download models

```bash
# Pull the LLM
ollama pull llama3.1:8b

# Download Piper TTS voice (run once)
python scripts/download_piper_voice.py
```

### 3. Install Whisper model

The first run will auto-download the Whisper model (~1.5GB for "base").

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your Twilio credentials
```

### 5. Run locally (mic → speaker test)

```bash
python -m trollcaller.local_test
```

### 6. Run the Twilio server

```bash
# Terminal 1: Start the server
python -m trollcaller.server

# Terminal 2: Expose via ngrok
ngrok http 8765
```

Then configure your Twilio number's webhook to `https://<ngrok-url>/incoming-call`.

## Project Structure

```
TrollCaller/
├── trollcaller/
│   ├── __init__.py
│   ├── server.py          # FastAPI server + Twilio webhook
│   ├── media_stream.py    # WebSocket handler for Twilio Media Streams
│   ├── stt.py             # Whisper speech-to-text
│   ├── llm.py             # Ollama LLM integration
│   ├── tts.py             # Piper TTS integration
│   ├── pipeline.py        # STT → LLM → TTS orchestration
│   ├── prompts.py         # System prompts (the fun part!)
│   ├── audio_utils.py     # Audio format conversion helpers
│   └── local_test.py      # Test without Twilio (mic → speaker)
├── scripts/
│   └── download_piper_voice.py
├── voices/                # Piper voice models (downloaded)
├── recordings/            # Saved call recordings
├── requirements.txt
├── .env.example
└── README.md
```

## System Prompt Engineering 🎭

The bot's personality is defined in `trollcaller/prompts.py`. Current personas:

- **Elderly Cat Lover** — Goes off on tangents about their cat Mittens
- **Confused Grandpa** — Hard of hearing, keeps asking to repeat everything
- **Overly Enthusiastic** — WAY too excited about whatever they're selling

## Latency Budget

Target: <500ms end-to-end response time

| Stage | Target | Notes |
|-------|--------|-------|
| STT | ~100ms | Whisper base, streaming chunks |
| LLM | ~200ms | Ollama, first token |
| TTS | ~100ms | Piper, streaming |
| Network | ~100ms | Twilio overhead |

## Legal Note ⚖️

Only use on calls you receive. Don't initiate calls to random numbers. Recording laws vary by country — keep it as an internal demo.
