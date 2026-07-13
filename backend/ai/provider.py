"""
AI provider router.

Every provider here speaks the OpenAI chat-completions dialect, so one
HTTP call works for all of them. We walk the list until someone answers.

    Groq        -> primary. absurdly fast, generous free tier
    Cerebras    -> fallback. big daily token budget
    Gemini      -> fallback. different company, different outage

Why bother with three?

Free tiers get cut without notice. Providers silently retire model
names. Rate limits arrive at the worst possible moment. If Kowalski
depends on exactly one endpoint, then Kowalski is exactly as reliable
as that endpoint's worst day.

It should never be possible for a startup's billing decision to break
your second brain.
"""
from __future__ import annotations

import json
import logging

import httpx

from core import config

log = logging.getLogger("kowalski.ai")

TIMEOUT = httpx.Timeout(20.0, connect=5.0)


class AIUnavailable(Exception):
    """Every provider failed. The caller must degrade gracefully."""


def _usable() -> list[dict]:
    return [p for p in config.AI_PROVIDERS if p.get("key")]


def complete(system: str, user: str, json_mode: bool = False) -> str:
    """
    Send a prompt. Try each provider in order. Return the first answer.

    Raises AIUnavailable only if ALL of them fail — which is the case
    the caller must handle, never ignore.
    """
    if not config.AI_ENABLED:
        raise AIUnavailable("AI is disabled (AI_ENABLED=false)")

    providers = _usable()
    if not providers:
        raise AIUnavailable("No AI provider keys configured")

    errors: list[str] = []

    for p in providers:
        try:
            payload = {
                "model": p["model"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,        # parsing, not poetry
                "max_tokens": 500,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            r = httpx.post(
                f"{p['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {p['key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=TIMEOUT,
            )
            r.raise_for_status()

            text = r.json()["choices"][0]["message"]["content"]
            log.info("ai: answered by %s (%s)", p["name"], p["model"])
            return text.strip()

        except Exception as e:                      # noqa: BLE001
            msg = f"{p['name']}: {type(e).__name__}: {e}"
            log.warning("ai: %s — falling through", msg)
            errors.append(msg)
            continue

    raise AIUnavailable("All providers failed:\n  " + "\n  ".join(errors))


def complete_json(system: str, user: str) -> dict:
    """
    Same, but guarantees a dict back.

    Models wrap JSON in markdown fences no matter how firmly you ask
    them not to. So we just strip the fences instead of pretending.
    """
    raw = complete(system, user, json_mode=True)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip().strip("`").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIUnavailable(f"Model returned non-JSON: {raw[:200]}") from e


def health() -> dict[str, str]:
    """Which providers are actually alive right now? Used by /health."""
    out: dict[str, str] = {}
    for p in config.AI_PROVIDERS:
        if not p.get("key"):
            out[p["name"]] = "no key"
            continue
        try:
            complete("Reply with OK.", "ping")
            out[p["name"]] = f"ok ({p['model']})"
        except Exception as e:                      # noqa: BLE001
            out[p["name"]] = f"fail: {type(e).__name__}"
    return out
