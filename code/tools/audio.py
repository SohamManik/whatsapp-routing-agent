"""
Audio tool: transcribe_voice(media_id) -> dict

Calls Groq Whisper Large v3 Turbo to transcribe voice notes.
Results are cached for repeated calls.
"""

from __future__ import annotations

import os
import logging
import time
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

from code.data.loader import get_loader

load_dotenv()

logger = logging.getLogger(__name__)

# Groq Whisper API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WHISPER_MODEL = "whisper-large-v3-turbo"
WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Internal cache for transcription results
_audio_cache: Dict[str, Dict[str, Any]] = {}


def transcribe_voice(media_id: str) -> Dict[str, Any]:
    """
    Transcribe voice note using Groq Whisper Large v3 Turbo.

    Args:
        media_id: Voice note media ID to transcribe

    Returns:
        Dict with keys: transcription, language, duration_seconds
    """
    # Check cache first
    if media_id in _audio_cache:
        logger.info(f"Cache hit for voice note {media_id}")
        return _audio_cache[media_id]

    loader = get_loader()
    audio_path = loader.get_voice_note_path(media_id)

    if not audio_path or not os.path.exists(audio_path):
        result = {
            "transcription": "",
            "language": "unknown",
            "duration_seconds": 0,
            "error": f"Audio file not found for {media_id}",
        }
        _audio_cache[media_id] = result
        return result

    try:
        # Prepare file for upload
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
            data = {"model": WHISPER_MODEL}
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

            # Retry with exponential backoff
            max_retries = 3
            base_delay = 2  # seconds
            for attempt in range(max_retries):
                try:
                    response = requests.post(WHISPER_URL, files=files, data=data, headers=headers, timeout=60)
                    if response.status_code in [429, 503]:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Whisper API {response.status_code} for {media_id}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                    response.raise_for_status()
                    break
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Whisper API timeout for {media_id}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Whisper API error for {media_id}: {e}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    raise
            else:
                # Should not reach here, but just in case
                raise Exception(f"Max retries exceeded for Whisper API for {media_id}")

            result_data = response.json()
            transcription = result_data.get("text", "")

            result = {
                "transcription": transcription,
                "language": result_data.get("language", "unknown"),
                "duration_seconds": 0,  # Whisper doesn't return duration by default
            }

    except Exception as e:
        logger.error(f"Whisper API error for {media_id}: {e}")
        result = {
            "transcription": "",
            "language": "error",
            "duration_seconds": 0,
            "error": f"Transcription failed: {str(e)}",
        }

    # Cache the result
    _audio_cache[media_id] = result
    return result