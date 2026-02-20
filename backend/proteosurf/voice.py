"""
ElevenLabs voice narration integration.

Converts protein analysis text to natural-sounding speech using ElevenLabs'
streaming TTS API. Supports multiple voices and models.

Track: Best use of ElevenLabs
"""

from __future__ import annotations

import base64
import io
import json
import os
from typing import Any

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Rachel — warm, clear, scientific narrator
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
DEFAULT_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")

_HAS_ELEVENLABS = False
try:
    from elevenlabs.client import ElevenLabs
    _HAS_ELEVENLABS = True
except ImportError:
    pass


def _get_client():
    if not _HAS_ELEVENLABS:
        raise ImportError("elevenlabs package not installed. pip install elevenlabs")
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not set")
    return ElevenLabs(api_key=ELEVENLABS_API_KEY)


def narrate_analysis(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> str:
    """Convert a protein analysis explanation into spoken audio using ElevenLabs.

    Args:
        text: The text to narrate (typically an AI-generated protein analysis).
        voice_id: ElevenLabs voice ID. Default is Rachel (warm, clear narrator).
        model_id: TTS model to use. Default is eleven_multilingual_v2.
        stability: Voice stability (0.0–1.0). Lower = more expressive.
        similarity_boost: Voice similarity boost (0.0–1.0).

    Returns:
        JSON with base64-encoded MP3 audio and metadata.
    """
    try:
        client = _get_client()
    except (ImportError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    # Truncate very long texts to stay within limits
    if len(text) > 5000:
        text = text[:4900] + "... (truncated for narration)"

    try:
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        )

        audio_bytes = b""
        for chunk in audio_stream:
            if isinstance(chunk, bytes):
                audio_bytes += chunk

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

        return json.dumps({
            "status": "ok",
            "text_length": len(text),
            "audio_format": "mp3",
            "audio_size_bytes": len(audio_bytes),
            "audio_base64": audio_b64,
            "voice_id": voice_id,
            "model_id": model_id,
        })

    except Exception as exc:
        return json.dumps({"error": f"ElevenLabs TTS failed: {exc}"})


def narrate_streaming(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL,
):
    """Stream audio chunks for real-time playback.

    Yields raw MP3 byte chunks as they arrive from ElevenLabs.
    """
    client = _get_client()

    audio_stream = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    for chunk in audio_stream:
        if isinstance(chunk, bytes):
            yield chunk


def list_voices() -> str:
    """List available ElevenLabs voices for narration.

    Returns:
        JSON array of available voices with name, voice_id, and description.
    """
    try:
        client = _get_client()
    except (ImportError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    try:
        response = client.voices.get_all()
        voices = []
        for v in response.voices[:20]:
            voices.append({
                "voice_id": v.voice_id,
                "name": v.name,
                "category": getattr(v, "category", "unknown"),
                "description": getattr(v, "description", ""),
            })
        return json.dumps({"voices": voices}, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Failed to list voices: {exc}"})
