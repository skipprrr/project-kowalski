"""
Time. Deliberately separate from db.py.

The parser needs time helpers. The parser must NOT need a database
connection — otherwise you can't unit-test parsing without Supabase
credentials, and a test suite you can't run offline is a test suite
you stop running.

═══════════════════════════════════════════════════════════════
  THE ONLY THREE RULES THAT MATTER

    1. The database stores UTC. Always.
    2. The user thinks in Dhaka time. Always.
    3. Conversion happens ONLY here, at the boundary.

  Every timezone bug you will ever have is one of these, broken.
═══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import datetime, timezone

from core import config


def now_local() -> datetime:
    """Now, in the user's timezone. Use for PARSING."""
    return datetime.now(config.TZ)


def now_utc() -> datetime:
    """Now, UTC. Use for STORING."""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Local -> UTC. Call before writing to the database."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TZ)
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime | str) -> datetime:
    """UTC (or an ISO string from Postgres) -> local. Call before displaying."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(config.TZ)


def iso(dt: datetime | None) -> str | None:
    """Datetime -> UTC ISO string, ready for Postgres."""
    return to_utc(dt).isoformat() if dt else None


def fmt(dt: datetime | str | None) -> str:
    """
    Human-readable local time: 'Tue 14 Jul, 9:00 PM'

    Hand-rolled rather than strftime('%-I') — that directive does not
    exist on Windows, and this project lives on a Windows machine.
    """
    if not dt:
        return ""
    local = to_local(dt)
    hour_12 = local.hour % 12 or 12
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{local:%a %d %b}, {hour_12}:{local:%M} {ampm}"


def time_only(dt: datetime | str | None) -> str:
    """Just the clock: '9:00 PM'"""
    if not dt:
        return ""
    local = to_local(dt)
    hour_12 = local.hour % 12 or 12
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{hour_12}:{local:%M} {ampm}"
