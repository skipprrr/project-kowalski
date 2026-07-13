"""
Time parsing. Deterministic. Zero AI. Zero network. ~0.2ms.

This module is the reason Kowalski is cheap and fast. Roughly 85% of
the things you say to a second brain are time expressions a regex can
handle perfectly:

    "tomorrow 9pm"      "in 2 hours"      "next friday"
    "tonight"           "every day 7am"   "monday morning"

An LLM can do this too. It just costs money, takes 800ms, needs a
network, and occasionally invents a date. So we only call it when
these rules genuinely fail.

Returns UTC. Always UTC. See core/db.py for why.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from core import config
from core.timeutil import now_local, to_utc

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

# Everything a tired person types at midnight
DAY_WORDS = {
    "today": 0, "tdy": 0,
    "tonight": 0,
    "tomorrow": 1, "tmrw": 1, "tmr": 1, "tmw": 1, "tom": 1,
    "overmorrow": 2,
    "yesterday": -1,   # parsed, then rejected — see below
}

PART_OF_DAY = {
    "morning": config.DEFAULT_HOURS["morning"],
    "afternoon": config.DEFAULT_HOURS["afternoon"],
    "evening": config.DEFAULT_HOURS["evening"],
    "night": config.DEFAULT_HOURS["night"],
    "tonight": config.DEFAULT_HOURS["tonight"],
    "noon": config.DEFAULT_HOURS["noon"],
    "midnight": config.DEFAULT_HOURS["midnight"],
}


@dataclass
class TimeResult:
    due_at: datetime | None = None      # UTC, for the database
    due_text: str | None = None         # the phrase you actually said
    recurrence: str | None = None       # daily | weekly | monthly
    remainder: str = ""                 # the message with the time stripped out
    matched: bool = False


def _clean(text: str, *spans: tuple[int, int]) -> str:
    """Remove matched spans from the text, tidy up the leftovers."""
    out = list(text)
    for start, end in spans:
        for i in range(start, end):
            out[i] = "\x00"
    result = "".join(c for c in out if c != "\x00")
    # collapse whitespace and strip dangling connective words
    result = re.sub(r"\s+", " ", result).strip(" ,.")

    # Loop, don't sub once. Stripping the time out of
    #   "tomorrow at 9pm to call Fatima"
    # leaves "at to call Fatima" — two connectives back to back.
    # A single sub removes "at" and leaves the "to" behind.
    while True:
        new = re.sub(r"^(to|at|on|by|for|about|that|and)\s+", "", result, flags=re.I)
        new = re.sub(r"\s+(at|on|by|to)$", "", new, flags=re.I)
        if new == result:
            break
        result = new

    return result.strip(" ,.")


def parse_time(text: str, now: datetime | None = None) -> TimeResult:
    """
    Pull a datetime out of natural language.

    Returns TimeResult(matched=False) when nothing time-like is found,
    which is the signal for the caller to escalate to AI.
    """
    now = now or now_local()
    low = text.lower()
    spans: list[tuple[int, int]] = []

    recurrence: str | None = None
    day_offset: int | None = None
    target_weekday: int | None = None
    hour: int | None = None
    minute: int = 0
    relative: timedelta | None = None
    explicit_date: tuple[int, int] | None = None   # (day, month)

    # ── RECURRENCE ──────────────────────────────────────────────
    m = re.search(r"\b(every\s?day|everyday|daily)\b", low)
    if m:
        recurrence = "daily"
        spans.append(m.span())

    if not recurrence:
        m = re.search(r"\b(every\s?week|weekly)\b", low)
        if m:
            recurrence = "weekly"
            spans.append(m.span())

    if not recurrence:
        m = re.search(r"\b(every\s?month|monthly)\b", low)
        if m:
            recurrence = "monthly"
            spans.append(m.span())

    # "every monday" -> weekly, anchored to Monday
    if not recurrence:
        m = re.search(r"\bevery\s+(" + "|".join(WEEKDAYS) + r")\b", low)
        if m:
            recurrence = "weekly"
            target_weekday = WEEKDAYS[m.group(1)]
            spans.append(m.span())

    # ── RELATIVE: "in 30 minutes" / "in 2 hours" / "in 3 days" ───
    m = re.search(
        r"\bin\s+(\d+)\s*(min|mins|minute|minutes|hr|hrs|hour|hours|day|days|week|weeks)\b",
        low,
    )
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if unit.startswith("min"):
            relative = timedelta(minutes=n)
        elif unit.startswith(("hr", "hour")):
            relative = timedelta(hours=n)
        elif unit.startswith("day"):
            relative = timedelta(days=n)
        else:
            relative = timedelta(weeks=n)
        spans.append(m.span())

    # ── EXPLICIT DATE: "on 25 dec" / "25/12" / "dec 25" ──────────
    if relative is None:
        months = ("jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec")
        m = re.search(rf"\b(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({months})[a-z]*\b", low)
        if not m:
            m2 = re.search(rf"\b({months})[a-z]*\s+(\d{{1,2}})\b", low)
            if m2:
                mon_i = ["jan","feb","mar","apr","may","jun",
                         "jul","aug","sep","oct","nov","dec"].index(m2.group(1)) + 1
                explicit_date = (int(m2.group(2)), mon_i)
                spans.append(m2.span())
        else:
            mon_i = ["jan","feb","mar","apr","may","jun",
                     "jul","aug","sep","oct","nov","dec"].index(m.group(2)) + 1
            explicit_date = (int(m.group(1)), mon_i)
            spans.append(m.span())

    # ── DAY WORDS: today / tomorrow / tmrw ──────────────────────
    if relative is None and explicit_date is None:
        for word, offset in DAY_WORDS.items():
            m = re.search(rf"\b{re.escape(word)}\b", low)
            if m:
                day_offset = offset
                spans.append(m.span())
                break

    # ── WEEKDAYS: "friday" / "next monday" ──────────────────────
    if relative is None and explicit_date is None and day_offset is None and target_weekday is None:
        m = re.search(r"\b(next\s+)?(" + "|".join(WEEKDAYS) + r")\b", low)
        if m:
            target_weekday = WEEKDAYS[m.group(2)]
            force_next = bool(m.group(1))
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 or force_next:
                days_ahead = days_ahead or 7
                if force_next and days_ahead < 7:
                    days_ahead += 0
            day_offset = days_ahead
            spans.append(m.span())
            target_weekday = None

    # ── CLOCK TIME: "9pm" / "9:30 pm" / "21:00" / "at 9" ─────────
    m = re.search(r"\b(\d{1,2})\s*[:.]\s*(\d{2})\s*(am|pm)?\b", low)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        ap = m.group(3)
        if ap == "pm" and hour < 12:
            hour += 12
        elif ap == "am" and hour == 12:
            hour = 0
        spans.append(m.span())
    else:
        m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", low)
        if m:
            hour = int(m.group(1))
            if m.group(2) == "pm" and hour < 12:
                hour += 12
            elif m.group(2) == "am" and hour == 12:
                hour = 0
            spans.append(m.span())
        else:
            # "at 9" — bare hour, only valid after an explicit "at"
            m = re.search(r"\bat\s+(\d{1,2})\b(?!\s*(min|hour|day))", low)
            if m:
                hour = int(m.group(1))
                # 1-7 with no am/pm almost always means evening
                if 1 <= hour <= 7:
                    hour += 12
                spans.append(m.span())

    # ── PART OF DAY: "morning" / "tonight" / "evening" ───────────
    if hour is None:
        for word, h in PART_OF_DAY.items():
            m = re.search(rf"\b{word}\b", low)
            if m:
                hour = h
                if (m.start(), m.end()) not in spans:
                    spans.append(m.span())
                if word == "tonight" and day_offset is None:
                    day_offset = 0
                break

    # ── NOTHING FOUND ───────────────────────────────────────────
    if (
        relative is None
        and day_offset is None
        and target_weekday is None
        and hour is None
        and explicit_date is None
        and recurrence is None
    ):
        return TimeResult(matched=False, remainder=text.strip())

    # ── ASSEMBLE ────────────────────────────────────────────────
    if relative is not None:
        due_local = now + relative
    else:
        base = now

        if explicit_date is not None:
            day, month = explicit_date
            year = now.year
            candidate = base.replace(month=month, day=day)
            if candidate.date() < now.date():
                year += 1                      # "25 dec" in January = next year
            base = base.replace(year=year, month=month, day=day)

        elif day_offset is not None:
            base = base + timedelta(days=day_offset)

        elif target_weekday is not None:       # recurring weekday
            days_ahead = (target_weekday - now.weekday()) % 7 or 7
            base = base + timedelta(days=days_ahead)

        h = hour if hour is not None else config.DEFAULT_HOURS["default"]
        due_local = base.replace(hour=h, minute=minute, second=0, microsecond=0)

        # "remind me at 9pm" said at 10pm means TOMORROW at 9pm.
        # Without this, the reminder fires instantly. Silent, maddening bug.
        if day_offset is None and explicit_date is None and due_local <= now:
            if recurrence == "weekly":
                due_local += timedelta(days=7)
            elif recurrence == "monthly":
                due_local += timedelta(days=30)
            else:
                due_local += timedelta(days=1)

    due_local = due_local.replace(second=0, microsecond=0)

    # A reminder in the past is always a parse failure, never an intention.
    if due_local < now and recurrence is None:
        return TimeResult(matched=False, remainder=text.strip())

    spans.sort()
    remainder = _clean(text, *spans)
    due_text = " ".join(text[s:e] for s, e in spans).strip()

    return TimeResult(
        due_at=to_utc(due_local),
        due_text=due_text or None,
        recurrence=recurrence,
        remainder=remainder,
        matched=True,
    )
