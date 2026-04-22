"""Audio format conversion utilities for Twilio Media Streams."""

import base64
import io
import struct
import numpy as np


def mulaw_decode(mulaw_bytes: bytes) -> np.ndarray:
    """Decode μ-law encoded audio to 16-bit PCM numpy array."""
    # μ-law decompression table
    MULAW_BIAS = 33
    MULAW_MAX = 0x1FFF

    samples = []
    for byte in mulaw_bytes:
        byte = ~byte & 0xFF
        sign = byte & 0x80
        exponent = (byte >> 4) & 0x07
        mantissa = byte & 0x0F
        sample = (mantissa << (exponent + 3)) + MULAW_BIAS * ((1 << (exponent + 3)) - 1)
        sample = sample - MULAW_BIAS
        if sign:
            sample = -sample
        samples.append(sample)

    return np.array(samples, dtype=np.int16)


def pcm_to_mulaw(pcm_data: np.ndarray) -> bytes:
    """Encode 16-bit PCM numpy array to μ-law bytes."""
    MULAW_MAX = 0x1FFF
    MULAW_BIAS = 33

    result = bytearray()
    for sample in pcm_data:
        sample = int(sample)
        sign = 0
        if sample < 0:
            sign = 0x80
            sample = -sample
        sample = min(sample, MULAW_MAX)
        sample += MULAW_BIAS

        exponent = 7
        mask = 0x4000
        while exponent > 0 and not (sample & mask):
            exponent -= 1
            mask >>= 1

        mantissa = (sample >> (exponent + 3)) & 0x0F
        mulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
        result.append(mulaw_byte)

    return bytes(result)


def twilio_audio_to_pcm(payload: str) -> np.ndarray:
    """Convert Twilio's base64 μ-law payload to PCM numpy array.

    Twilio sends audio as base64-encoded μ-law at 8kHz mono.
    """
    raw = base64.b64decode(payload)
    return mulaw_decode(raw)


def pcm_to_twilio_audio(pcm_data: np.ndarray) -> str:
    """Convert PCM numpy array to Twilio's base64 μ-law format."""
    mulaw = pcm_to_mulaw(pcm_data)
    return base64.b64encode(mulaw).decode("ascii")


def resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Simple linear resampling between sample rates."""
    if from_rate == to_rate:
        return audio
    ratio = to_rate / from_rate
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio.astype(np.float64)).astype(
        np.int16
    )


def float32_to_int16(audio: np.ndarray) -> np.ndarray:
    """Convert float32 [-1, 1] audio to int16."""
    return (audio * 32767).clip(-32768, 32767).astype(np.int16)


def int16_to_float32(audio: np.ndarray) -> np.ndarray:
    """Convert int16 audio to float32 [-1, 1]."""
    return audio.astype(np.float32) / 32768.0
