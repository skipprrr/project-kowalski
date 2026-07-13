"""
Intent parsing. Rules first, always.

This is Kowalski's philosophy made executable:

    "Python owns the data. AI interprets the data."

Every message hits these rules before it is allowed anywhere near an
LLM. If the rules understand it — and they usually do — we're done in
under a millisecond, for free, with a result that will be identical
tomorrow. Determinism is a feature, not a limitation.

The AI is a *fallback*, not a *dependency*.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from parsers.timeparse import parse_time

Intent = Literal[
    "task", "reminder", "note", "idea", "journal",
    "money", "done", "search", "today", "list", "unknown",
]


@dataclass
class Parsed:
    intent: Intent = "unknown"
    content: str = ""
    raw_input: str = ""

    due_at: object | None = None          # datetime, UTC
    due_text: str | None = None
    recurrence: str | None = None
    notify: bool = False

    # money
    amount: float | None = None
    direction: str | None = None          # they_owe_me | i_owe_them
    person: str | None = None

    entities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: int = 0

    parsed_by: str = "rules"
    confidence: float = 1.0


# ═══════════════════════════════════════════════════════════════
#  PATTERNS
#  Ordered. First match wins. Order matters — "remind" must be
#  tested before "note", or "note: remind Ali" misfires.
# ═══════════════════════════════════════════════════════════════

REMINDER_RE = re.compile(
    r"^(?:remind(?:\s+me)?(?:\s+to)?|reminder|ping\s+me|alert\s+me|wake\s+me)\b[:\s]*(.*)$",
    re.I | re.S,
)

TASK_RE = re.compile(
    r"^(?:task|todo|to-do|add\s+task|new\s+task|t)\b[:\s]+(.*)$",
    re.I | re.S,
)

NOTE_RE = re.compile(
    r"^(?:note|remember|save|store|keep|memo|n)\b[:\s]+(.*)$",
    re.I | re.S,
)

IDEA_RE = re.compile(
    r"^(?:idea|thought|brainstorm)\b[:\s]+(.*)$",
    re.I | re.S,
)

JOURNAL_RE = re.compile(
    r"^(?:journal|diary|log|entry)\b[:\s]+(.*)$",
    re.I | re.S,
)

DONE_RE = re.compile(
    r"^(?:done|complete[d]?|finish(?:ed)?|✅|✔️?)\s*(.*)$",
    re.I | re.S,
)

SEARCH_RE = re.compile(
    r"^(?:search|find|look\s*up|lookup|s)\b[:\s]+(.*)$",
    re.I | re.S,
)

TODAY_RE = re.compile(
    r"^(?:today|/today|what(?:'s|s)?\s+(?:on\s+)?today|agenda|my\s+day)\s*$",
    re.I,
)

LIST_RE = re.compile(
    r"^(?:list|show|all)\s+(tasks?|reminders?|notes?|ideas?|journal)\s*$",
    re.I,
)

# ── MONEY ───────────────────────────────────────────────────────
# The v1 schema stored person + amount with no direction, which made
# "Fatima 500" permanently ambiguous. These patterns exist purely to
# answer: who owes whom?

MONEY_THEY_OWE = [
    re.compile(r"^(.+?)\s+owes?\s+me\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)\s*(.*)$", re.I),
    re.compile(r"^(?:i\s+)?(?:lent|loaned|gave)\s+(.+?)\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)\s*(.*)$", re.I),
]

MONEY_I_OWE = [
    re.compile(r"^i\s+owe\s+(.+?)\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)\s*(.*)$", re.I),
    # NOTE: the person group must be POSSESSIVE about word boundaries.
    # A lazy (.+?) followed by a greedy (.*) matches exactly one char,
    # which turned "from Karim" into person="K", note="arim".
    re.compile(
        r"^(?:i\s+)?(?:borrowed|took)\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)\s+from\s+"
        # Name = 1-2 words, and it STOPS at a connective. Without the
        # negative lookahead, "from Jegreber for the shop" gives you a
        # person literally called "Jegreber for the shop".
        r"([A-Za-z][\w'.-]*(?:\s+(?!for\b|on\b|about\b|as\b|re\b|to\b|because\b)[A-Za-z][\w'.-]*)?)"
        r"\b\s*(.*)$",
        re.I,
    ),
]

# ── ENTITY & TAG EXTRACTION ─────────────────────────────────────
MENTION_RE = re.compile(r"@(\w+)")
TAG_RE = re.compile(r"#(\w+)")
PRIORITY_RE = re.compile(r"(!{1,3})(?:\s|$)")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _tidy(s: str) -> str:
    """Strip dangling connectives from a captured fragment."""
    s = (s or "").strip(" ,.")
    return re.sub(r"^(for|on|about|as|re)\s+", "", s, flags=re.I).strip(" ,.")


def _extract_meta(text: str) -> tuple[str, list[str], list[str], int]:
    """Pull @entities, #tags and ! priority out; return cleaned text."""
    entities = MENTION_RE.findall(text)
    tags = TAG_RE.findall(text)

    pm = PRIORITY_RE.search(text)
    priority = len(pm.group(1)) if pm else 0

    cleaned = MENTION_RE.sub(r"\1", text)      # keep the name, drop the @
    cleaned = TAG_RE.sub("", cleaned)
    cleaned = PRIORITY_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")

    return cleaned, entities, tags, min(priority, 2)


def parse(text: str) -> Parsed:
    """
    Message in, Parsed out.

    intent == "unknown" is the ONLY signal that the AI fallback
    should run. Everything else was handled here, for free.
    """
    raw = text.strip()
    p = Parsed(raw_input=raw)

    if not raw:
        return p

    # ── ZERO-ARG COMMANDS ───────────────────────────────────────
    if TODAY_RE.match(raw):
        p.intent = "today"
        return p

    m = LIST_RE.match(raw)
    if m:
        p.intent = "list"
        p.content = m.group(1).rstrip("s")
        return p

    # ── DONE ────────────────────────────────────────────────────
    m = DONE_RE.match(raw)
    if m:
        p.intent = "done"
        p.content = m.group(1).strip()   # empty = complete the latest task
        return p

    # ── SEARCH ──────────────────────────────────────────────────
    m = SEARCH_RE.match(raw)
    if m:
        p.intent = "search"
        p.content = m.group(1).strip()
        return p

    # ── MONEY ───────────────────────────────────────────────────
    for rx in MONEY_THEY_OWE:
        m = rx.match(raw)
        if m:
            p.intent = "money"
            p.direction = "they_owe_me"
            p.person = m.group(1).strip()
            p.amount = _num(m.group(2))
            p.content = _tidy(m.group(3)) or f"{p.person} owes {p.amount:,.0f}"
            return p

    for rx in MONEY_I_OWE:
        m = rx.match(raw)
        if m:
            p.intent = "money"
            p.direction = "i_owe_them"
            groups = m.groups()
            # "borrowed 500 from Ali" reverses the capture order
            if groups[0].replace(",", "").replace(".", "").isdigit():
                p.amount, p.person = _num(groups[0]), groups[1].strip()
            else:
                p.person, p.amount = groups[0].strip(), _num(groups[1])
            p.content = _tidy(groups[2]) or f"I owe {p.person} {p.amount:,.0f}"
            return p

    # ── TYPED CAPTURES ──────────────────────────────────────────
    body: str | None = None
    intent: Intent | None = None
    notify = False

    if (m := REMINDER_RE.match(raw)):
        intent, body, notify = "reminder", m.group(1), True
    elif (m := TASK_RE.match(raw)):
        intent, body = "task", m.group(1)
    elif (m := NOTE_RE.match(raw)):
        intent, body = "note", m.group(1)
    elif (m := IDEA_RE.match(raw)):
        intent, body = "idea", m.group(1)
    elif (m := JOURNAL_RE.match(raw)):
        intent, body = "journal", m.group(1)

    if intent and body is not None:
        body = body.strip()
        t = parse_time(body)

        content = t.remainder if t.matched else body
        content, ents, tags, prio = _extract_meta(content)

        p.intent = intent
        p.content = content
        p.entities = ents
        p.tags = tags
        p.priority = prio

        if t.matched:
            p.due_at = t.due_at
            p.due_text = t.due_text
            p.recurrence = t.recurrence
            # a task with a time on it is a task that should ping you
            p.notify = notify or intent == "task"

        # "remind me to call Ali" with no time is not actionable
        if intent == "reminder" and not t.matched:
            p.confidence = 0.5

        return p

    # ── IMPLICIT: bare text with a clear time in it ─────────────
    # "call ali tomorrow 5pm" — no keyword, but obviously a reminder.
    t = parse_time(raw)
    if t.matched and t.remainder:
        content, ents, tags, prio = _extract_meta(t.remainder)
        p.intent = "reminder"
        p.content = content
        p.due_at = t.due_at
        p.due_text = t.due_text
        p.recurrence = t.recurrence
        p.notify = True
        p.entities = ents
        p.tags = tags
        p.priority = prio
        p.confidence = 0.8
        return p

    # ── GIVE UP → the AI gets its turn ──────────────────────────
    p.intent = "unknown"
    p.content = raw
    p.confidence = 0.0
    return p
