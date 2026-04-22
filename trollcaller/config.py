"""Configuration loaded from environment variables."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8765

    # Whisper
    whisper_model: str = "base"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # Piper TTS
    piper_voice: str = "en_US-lessac-medium"
    voices_dir: Path = BASE_DIR / "voices"

    # ElevenLabs
    elevenlabs_api_key: str = ""

    # Hume
    hume_api_key: str = ""

    # Recording
    record_calls: bool = False
    recordings_dir: Path = BASE_DIR / "recordings"

    class Config:
        env_file = ".env"


settings = Settings()
