"""
Config. Every environment variable enters the system here and nowhere else.

If you find yourself typing os.getenv() anywhere else in this codebase,
stop and add it to this file instead.
"""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


# ── Supabase ────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── Telegram ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def require(*keys: str) -> None:
    """
    Assert that these config values exist. Called by whoever actually
    needs them — db() needs Supabase, the bot needs Telegram.

    NOT called at import time, deliberately. If config raised on import,
    you could not unit-test the regex parser without a database
    password, which is absurd. Fail fast, but fail at the right layer.
    """
    missing = [k for k in keys if not globals().get(k)]
    if missing:
        raise RuntimeError(
            "Missing environment variable(s): " + ", ".join(missing) +
            "\nAdd them to backend/.env"
        )

# ── Time ────────────────────────────────────────────────────────
# THE RULE: store UTC, display local. Convert only at the edges.
TIMEZONE = os.getenv("TIMEZONE", "Asia/Dhaka")
TZ = ZoneInfo(TIMEZONE)

# ── AI ──────────────────────────────────────────────────────────
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"

# Providers are tried top to bottom. First one with a key wins.
# Model names live HERE, never in code — providers retire models
# without warning and you want that to be a one-line fix.
AI_PROVIDERS = [
    {
        "name": "groq",
        "key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    },
    {
        "name": "cerebras",
        "key": os.getenv("CEREBRAS_API_KEY"),
        "base_url": "https://api.cerebras.ai/v1",
        "model": os.getenv("CEREBRAS_MODEL", "llama-3.3-70b"),
    },
    {
        "name": "gemini",
        "key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    },
]

# ── Defaults for vague times ────────────────────────────────────
# "remind me tomorrow" — tomorrow WHEN? These are the answers.
DEFAULT_HOURS = {
    "morning": 9,
    "afternoon": 15,
    "evening": 19,
    "night": 21,
    "tonight": 20,
    "noon": 12,
    "midnight": 0,
    "default": 9,   # bare "tomorrow" with no time
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
