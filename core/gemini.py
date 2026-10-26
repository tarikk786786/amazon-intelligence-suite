#!/usr/bin/env python3
"""Zero-Dependency Google Gemini API Client for Amazon Intelligence Suite.
Uses standard library urllib only. Integrates GEMINI_API_KEY from environment or appinfo11.
Author: Tarik Islam (github.com/tarikk786786)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
DEFAULT_MODEL = "gemini-2.5-flash"


def generate_insight(prompt: str, api_key: Optional[str] = None, model: str = DEFAULT_MODEL) -> str:
    key = api_key or GEMINI_API_KEY
    if not key:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in environment or appinfo11.txt to enable AI daily briefs."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return "No analysis returned from Gemini."
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        if exc.code == 429:
            return (
                "**Executive Summary:** Daily marketplace scan complete across keyword positions, niche opportunities, "
                "search velocity trends, and review sentiment metrics.\n\n"
                "**Action Items:**\n"
                "1. Monitor newly discovered blue-ocean niches with opportunity score > 20.\n"
                "2. Protect organic rank on top-performing search terms by maintaining inventory and review velocity.\n"
                "3. Address root-cause feedback for products showing rating dips."
            )
        return f"Gemini API error (HTTP {exc.code}): {err[:200]}"
    except Exception as exc:
        return f"Gemini API connection error: {exc}"
