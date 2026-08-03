#!/usr/bin/env python
"""Phase 0: API Connectivity Check for all required APIs."""

import os
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("=" * 60)
print("PHASE 0: API CONNECTIVITY CHECK")
print("=" * 60)

# ============================================================
# Test 1: Nemotron Chat Completion
# ============================================================
print("\n[1/5] Testing Nemotron Chat Completion...")
print(f"    Model: nvidia/nemotron-3-ultra-550b-a55b")
print(f"    Endpoint: https://integrate.api.nvidia.com/v1/chat/completions")

headers = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "nvidia/nemotron-3-ultra-550b-a55b",
    "messages": [{"role": "user", "content": "Reply with just the word hello."}],
    "max_tokens": 10,
    "temperature": 0.1,
}

try:
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=30
    )
    print(f"    Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"    Response: {content.strip()}")
        print("    [OK] Nemotron chat completion WORKS")
    else:
        print(f"    Response: {response.text[:300]}")
        print("    [FAIL] Nemotron chat completion FAILED")
except Exception as e:
    print(f"    Error: {e}")
    print("    [FAIL] Nemotron chat completion FAILED")

# ============================================================
# Test 2: Nemotron Function Calling Support
# ============================================================
print("\n[2/5] Testing Nemotron Function Calling Support...")

dummy_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        }
    }
}

payload = {
    "model": "nvidia/nemotron-3-ultra-550b-a55b",
    "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}],
    "tools": [dummy_tool],
    "tool_choice": "auto",
    "max_tokens": 100,
    "temperature": 0.1,
}

try:
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=30
    )
    print(f"    Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls")
        if tool_calls:
            print(f"    Tool calls returned: {json.dumps(tool_calls, indent=2)}")
            print("    [OK] Nemotron SUPPORTS function calling")
        else:
            print(f"    Content: {message.get('content', '')[:200]}")
            print("    [WARN] Nemotron does NOT return tool_calls (may not support function calling)")
    else:
        print(f"    Response: {response.text[:300]}")
        print("    [FAIL] Nemotron function calling test FAILED")
except Exception as e:
    print(f"    Error: {e}")
    print("    [FAIL] Nemotron function calling test FAILED")

# ============================================================
# Test 3: NIM Vision (Llama 3.2 Vision 11B)
# ============================================================
print("\n[3/5] Testing NIM Vision (Llama 3.2 Vision 11B)...")
print(f"    Model: nvidia/llama-3.2-11b-vision-instruct")

image_path = "dataset/media/images/img_001.jpg"
if os.path.exists(image_path):
    with open(image_path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "nvidia/llama-3.2-11b-vision-instruct",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in one sentence."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
            ]
        }],
        "max_tokens": 100,
        "temperature": 0.1,
    }

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60
        )
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"    Response: {content.strip()[:200]}")
            print("    [OK] NIM Vision WORKS")
        else:
            print(f"    Response: {response.text[:300]}")
            print("    [FAIL] NIM Vision FAILED - trying fallback models...")

            # Try fallback models
            fallback_models = [
                "nvidia/llama-3.2-11b-vision-instruct",
                "nvidia/phi-3.5-vision-instruct",
                "nvidia/nv-vision-llama3-11b",
                "meta/llama-3.2-11b-vision-instruct",
            ]
            for model in fallback_models:
                if model == "nvidia/llama-3.2-11b-vision-instruct":
                    continue
                print(f"    Trying fallback: {model}")
                payload["model"] = model
                try:
                    r = requests.post(
                        "https://integrate.api.nvidia.com/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=60
                    )
                    if r.status_code == 200:
                        d = r.json()
                        c = d["choices"][0]["message"]["content"]
                        print(f"    [OK] Fallback {model} WORKS: {c.strip()[:100]}")
                        break
                except:
                    pass
            else:
                print("    [FAIL] All vision models FAILED")
    except Exception as e:
        print(f"    Error: {e}")
        print("    [FAIL] NIM Vision FAILED")
else:
    print(f"    Image not found: {image_path}")

# ============================================================
# Test 4: NIM Reranker
# ============================================================
print("\n[4/5] Testing NIM Reranker (nvidia/nv-rerankqa-mistral-4b-v3)...")

rerank_payload = {
    "model": "nvidia/nv-rerankqa-mistral-4b-v3",
    "query": "What is the capital of France?",
    "passages": [
        "Paris is the capital city of France.",
        "London is the capital of the United Kingdom.",
        "Berlin is the capital of Germany."
    ],
    "top_k": 3,
}

try:
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/rerank",
        json=rerank_payload,
        headers=headers,
        timeout=30
    )
    print(f"    Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"    Response: {json.dumps(data, indent=2)[:300]}")
        print("    [OK] NIM Reranker WORKS")
    else:
        print(f"    Response: {response.text[:300]}")
        print("    [FAIL] NIM Reranker FAILED - checking available models...")

        # Try alternative reranker endpoints/models
        alt_models = [
            "nvidia/nv-rerankqa-mistral-4b-v3",
            "nvidia/rerank-qa-mistral-4b",
            "nvidia/nv-rerank-mistral-4b",
        ]
        for model in alt_models:
            if model == "nvidia/nv-rerankqa-mistral-4b-v3":
                continue
            print(f"    Trying fallback: {model}")
            rerank_payload["model"] = model
            try:
                r = requests.post(
                    "https://integrate.api.nvidia.com/v1/rerank",
                    json=rerank_payload,
                    headers=headers,
                    timeout=30
                )
                if r.status_code == 200:
                    d = r.json()
                    print(f"    [OK] Fallback {model} WORKS")
                    break
            except:
                pass
        else:
            print("    [WARN] No reranker available - will use BM25 only")
except Exception as e:
    print(f"    Error: {e}")
    print("    [WARN] Reranker endpoint may not exist - will use BM25 only")

# ============================================================
# Test 5: Groq Whisper Large v3 Turbo
# ============================================================
print("\n[5/5] Testing Groq Whisper Large v3 Turbo...")

audio_path = "dataset/media/audio/vn_001.mp3"
if os.path.exists(audio_path):
    groq_headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
        data = {"model": "whisper-large-v3-turbo"}

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                files=files,
                data=data,
                headers=groq_headers,
                timeout=60
            )
            print(f"    Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                transcription = data.get("text", "")
                print(f"    Transcription: {transcription[:200]}")
                print("    [OK] Groq Whisper WORKS")
            else:
                print(f"    Response: {response.text[:300]}")
                print("    [FAIL] Groq Whisper FAILED")
        except Exception as e:
            print(f"    Error: {e}")
            print("    [FAIL] Groq Whisper FAILED")
else:
    print(f"    Audio not found: {audio_path}")

print("\n" + "=" * 60)
print("PHASE 0 COMPLETE")
print("=" * 60)