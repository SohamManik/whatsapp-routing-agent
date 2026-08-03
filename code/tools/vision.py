"""
Vision tool: analyze_image(media_id) -> dict

Calls NVIDIA NIM Vision model to analyze image content.
Results are cached for repeated calls.
"""

from __future__ import annotations

import os
import base64
import json
import logging
import time
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

from code.data.loader import get_loader

load_dotenv()

logger = logging.getLogger(__name__)

# NVIDIA NIM Vision API (using working model from Phase 0)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"
VISION_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Internal cache for vision results
_vision_cache: Dict[str, Dict[str, Any]] = {}


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(media_id: str) -> Dict[str, Any]:
    """
    Analyze image content using NVIDIA NIM Vision model.

    Args:
        media_id: Image media ID to analyze

    Returns:
        Dict with keys: content_type, extracted_text, risk_signals, description
    """
    # Check cache first
    if media_id in _vision_cache:
        logger.info(f"Cache hit for image {media_id}")
        return _vision_cache[media_id]

    loader = get_loader()
    image_path = loader.get_image_path(media_id)

    if not image_path or not os.path.exists(image_path):
        result = {
            "content_type": "unknown",
            "extracted_text": "",
            "risk_signals": ["image_not_found"],
            "description": f"Image file not found for {media_id}",
        }
        _vision_cache[media_id] = result
        return result

    try:
        # Encode image
        b64_image = encode_image(image_path)

        # Prepare prompt for vision model
        prompt = """Analyze this WhatsApp image message. Return a JSON object with:
1. content_type: one of ["document", "screenshot", "poster", "personal_photo", "qr_code", "product_image", "meme", "forward_chain", "other"]
2. extracted_text: all readable text from the image (OCR)
3. risk_signals: array of risk indicators like ["scam", "phishing", "payment_request", "otp_request", "urgent_action", "fake_delivery", "suspicious_link", "chain_message", "none"]
4. description: 2-3 sentence summary of the image content and intent"""

        payload = {
            "model": VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }],
            "max_tokens": 512,
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }

        # Enforce base rate limit (40 RPM = 1.5s per call)
        time.sleep(1.5)

        # Retry with exponential backoff
        max_retries = 4
        base_delay = 3  # seconds
        for attempt in range(max_retries):
            try:
                response = requests.post(VISION_URL, json=payload, headers=headers, timeout=60)
                if response.status_code in [429, 503]:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Vision API {response.status_code} for {media_id}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Vision API timeout for {media_id}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Vision API error for {media_id}: {e}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                raise
        else:
            # Should not reach here, but just in case
            raise Exception(f"Max retries exceeded for Vision API for {media_id}")

        result_data = response.json()
        content = result_data["choices"][0]["message"]["content"]

        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
            else:
                parsed = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: return structured default
            parsed = {
                "content_type": "other",
                "extracted_text": content[:500],
                "risk_signals": ["parse_error"],
                "description": "Failed to parse vision model output",
            }

        result = {
            "content_type": parsed.get("content_type", "other"),
            "extracted_text": parsed.get("extracted_text", ""),
            "risk_signals": parsed.get("risk_signals", []),
            "description": parsed.get("description", ""),
        }

    except Exception as e:
        logger.error(f"Vision API error for {media_id}: {e}")
        result = {
            "content_type": "error",
            "extracted_text": "",
            "risk_signals": ["api_error"],
            "description": f"Vision analysis failed: {str(e)}",
        }

    # Cache the result
    _vision_cache[media_id] = result
    return result