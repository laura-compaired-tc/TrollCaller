"""LLM integration using Ollama for generating conversation responses."""

import logging
import re
import time
from typing import AsyncIterator

import httpx
import ollama

from .config import settings
from .prompts import get_system_prompt, DEFAULT_PERSONA

logger = logging.getLogger(__name__)


def _truncate_to_sentence(text: str) -> str:
    """Keep only the first 1-2 complete sentences, dropping cut-off fragments."""
    # Find sentence endings: . ! ? followed by space or end
    ends = list(re.finditer(r'[.!?](?:\s|$)', text))
    if not ends:
        return text  # no sentence boundary, return as-is
    # Keep up to 2 sentences max
    cut = ends[min(1, len(ends) - 1)].end()
    result = text[:cut].strip()
    # Drop suspiciously short final sentences (likely cut-off fragments)
    # e.g. "I think it's a." or "Well it."
    sentences = re.split(r'(?<=[.!?])\s+', result)
    if len(sentences) > 1 and len(sentences[-1].split()) <= 4:
        result = " ".join(sentences[:-1])
    elif len(sentences) == 1 and len(sentences[0].split()) <= 3:
        pass  # keep very short single sentences like "Oh my!" or "Sure thing."
    return result


class ConversationLLM:
    """Manages conversation state and generates responses via Ollama."""

    def __init__(self, persona: str = DEFAULT_PERSONA):
        self.persona = persona
        self.system_prompt = get_system_prompt(persona)
        self.history: list[dict[str, str]] = []
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        logger.info(f"LLM initialized with persona '{persona}', model '{settings.ollama_model}'")

    def _build_messages(self, user_text: str) -> list[dict[str, str]]:
        """Build the message list for the LLM."""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_text})
        return messages

    async def generate_response(self, user_text: str) -> str:
        """Generate a complete response to the user's speech.

        Args:
            user_text: What the caller said (transcribed).

        Returns:
            The bot's response text.
        """
        if not user_text.strip():
            return ""

        messages = self._build_messages(user_text)
        start = time.monotonic()

        try:
            response = await self.client.chat(
                model=settings.ollama_model,
                messages=messages,
                options={
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 80,
                },
            )
            text = response["message"]["content"].strip()
            # Truncate to last complete sentence to avoid mid-thought cutoffs
            text = _truncate_to_sentence(text)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            # Fallback responses that still waste time
            text = "Oh sorry dear, I dropped the phone. What were you saying?"

        elapsed = time.monotonic() - start
        logger.info(f"LLM response ({elapsed:.0f}ms): '{text}'")

        # Update conversation history
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": text})

        # Keep history manageable (last 20 turns)
        if len(self.history) > 40:
            self.history = self.history[-40:]

        return text

    async def generate_response_stream(self, user_text: str) -> AsyncIterator[str]:
        """Stream response tokens for lower time-to-first-token.

        Yields sentence fragments as they become available,
        so TTS can start speaking sooner.
        """
        if not user_text.strip():
            return

        messages = self._build_messages(user_text)
        start = time.monotonic()
        full_response = ""
        current_sentence = ""

        try:
            stream = await self.client.chat(
                model=settings.ollama_model,
                messages=messages,
                stream=True,
                options={
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 50,
                },
            )

            async for chunk in stream:
                token = chunk["message"]["content"]
                full_response += token
                current_sentence += token

                # Yield on sentence boundaries for natural TTS
                if any(current_sentence.rstrip().endswith(p) for p in ".!?,;:"):
                    sentence = current_sentence.strip()
                    if sentence:
                        yield sentence
                    current_sentence = ""

            # Yield any remaining text
            if current_sentence.strip():
                yield current_sentence.strip()

        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield "Oh sorry dear, I dropped the phone. What were you saying?"
            full_response = "Oh sorry dear, I dropped the phone. What were you saying?"

        elapsed = time.monotonic() - start
        logger.info(f"LLM streamed ({elapsed:.0f}ms): '{full_response}'")

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": full_response})
        if len(self.history) > 40:
            self.history = self.history[-40:]

    def get_greeting(self) -> str:
        """Get an initial greeting when answering the call."""
        greetings = {
            "elderly_cat_lover": "Hello? Oh hello dear! I was just feeding Mittens. Who is this?",
            "horoscope_karen": "Hellooo? Oh my god, my tarot cards literally said someone would call me today. What's your sign?",
            "overly_enthusiastic": "OH MY GOD HI! I was JUST hoping someone would call! What's up?!",
        }
        return greetings.get(self.persona, "Hello?")

    def reset(self) -> None:
        """Reset conversation history."""
        self.history.clear()
