"""
The router. One function. The single entry point for understanding text.

    understand("remind me tomorrow 9pm to call Ali")
        -> rules handle it, 0.2ms, $0.00

    understand("ugh dont let me forget the fatima thing tmrw")
        -> rules shrug, AI steps in, ~600ms, still $0.00 (free tier)

    understand(...) with every provider down
        -> falls back to a plain note. NEVER loses your input.

That last line is the important one. A second brain that drops a
thought because an API was down is not a second brain. Worst case,
we save the raw text as a note and tell you honestly that we couldn't
parse it — because a note you have to re-file yourself still beats a
thought that vanished.
"""
from __future__ import annotations

import logging
from datetime import datetime

from ai import provider
from core.timeutil import now_local, to_utc
from parsers import rules
from parsers.rules import Parsed

log = logging.getLogger("kowalski.parse")


SYSTEM_PROMPT = """You extract structured intent from a personal assistant message.

Return ONLY a JSON object. No prose, no markdown.

{
  "intent":     "task" | "reminder" | "note" | "idea" | "journal" | "money" | "done" | "search" | "today",
  "content":    "the core content, cleaned of time words and command words",
  "due_at":     "YYYY-MM-DD HH:MM" in the user's LOCAL time, or null,
  "recurrence": "daily" | "weekly" | "monthly" | null,
  "notify":     true | false,
  "entities":   ["names of people or businesses mentioned"],
  "tags":       [],
  "priority":   0 | 1 | 2,
  "amount":     number or null,
  "direction":  "they_owe_me" | "i_owe_them" | null,
  "person":     "name" or null
}

RULES
- Anything with a time the user wants to be pinged about -> "reminder", notify true.
- Something to do, no specific time -> "task".
- A fact to store -> "note".
- Money owed in either direction -> "money", and get the direction right.
- Ambiguous or unclear -> "note". Never invent a due date you are not sure about.
- Never set due_at in the past.
"""


def _ai_parse(text: str) -> Parsed:
    now = now_local()
    user = (
        f"Current local time: {now:%Y-%m-%d %H:%M} ({now:%A})\n"
        f"Timezone: Asia/Dhaka\n\n"
        f"Message: {text}"
    )

    data = provider.complete_json(SYSTEM_PROMPT, user)

    p = Parsed(raw_input=text, parsed_by="ai", confidence=0.7)
    p.intent = data.get("intent") or "note"
    p.content = (data.get("content") or text).strip()
    p.recurrence = data.get("recurrence")
    p.notify = bool(data.get("notify"))
    p.entities = data.get("entities") or []
    p.tags = data.get("tags") or []
    p.priority = int(data.get("priority") or 0)
    p.amount = data.get("amount")
    p.direction = data.get("direction")
    p.person = data.get("person")

    due = data.get("due_at")
    if due:
        try:
            local = datetime.fromisoformat(due)
            # Trust, but verify. Models hallucinate dates in the past.
            if local.replace(tzinfo=now.tzinfo) > now:
                p.due_at = to_utc(local)
                p.due_text = due
        except (ValueError, TypeError):
            log.warning("ai returned unparseable due_at: %r", due)

    return p


def understand(text: str) -> Parsed:
    """Text in, Parsed out. Rules first. AI only if they fail."""
    p = rules.parse(text)

    if p.intent != "unknown":
        log.debug("rules: %s (%.1f)", p.intent, p.confidence)
        return p

    # ── rules gave up ───────────────────────────────────────────
    try:
        ai = _ai_parse(text)
        log.info("ai: %s", ai.intent)
        return ai

    except provider.AIUnavailable as e:
        log.error("ai unavailable, degrading to note: %s", e)

        # THE SAFETY NET.
        # Everything is down. We still do not lose the thought.
        fallback = Parsed(raw_input=text, parsed_by="fallback", confidence=0.0)
        fallback.intent = "note"
        fallback.content = text
        return fallback
