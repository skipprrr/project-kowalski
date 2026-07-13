"""
Skills model.

Skills are things you're learning: Mandarin, Boxing, Python, etc.
Each skill has a progress % (0-100) and a log of sessions.

Bot commands:
    learning: Mandarin
    learning: Boxing — want to fight in a bout
    skill update: Mandarin 65%
    skill log: boxing did 1 hour sparring, worked on jabs
    skill log: mandarin 45 minutes — practiced tones
    skills               — list all skills
"""
from __future__ import annotations

from core.db import db, iso, now_utc

SKILLS  = "skills"
LOGS    = "skill_logs"


def create(name: str, description: str | None = None, goal: str | None = None) -> dict:
    res = db().table(SKILLS).insert({
        "name": name.strip(),
        "description": description,
        "goal": goal,
        "progress": 0,
    }).execute()
    return res.data[0]


def list_skills() -> list[dict]:
    return (
        db().table(SKILLS).select("*")
        .is_("deleted_at", "null")
        .order("name")
        .execute()
        .data or []
    )


def get_by_name(name: str) -> dict | None:
    """Fuzzy-ish match on skill name."""
    rows = (
        db().table(SKILLS).select("*")
        .ilike("name", f"%{name.strip()}%")
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def update_progress(skill_id: str, progress: int) -> dict | None:
    progress = max(0, min(100, progress))
    res = db().table(SKILLS).update({"progress": progress}).eq("id", skill_id).execute()
    return res.data[0] if res.data else None


def add_log(skill_id: str, note: str, duration: int | None = None) -> dict:
    res = db().table(LOGS).insert({
        "skill_id": skill_id,
        "note": note.strip(),
        "duration": duration,
    }).execute()
    return res.data[0]


def recent_logs(skill_id: str, limit: int = 10) -> list[dict]:
    return (
        db().table(LOGS).select("*")
        .eq("skill_id", skill_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data or []
    )


def soft_delete(skill_id: str) -> None:
    db().table(SKILLS).update({"deleted_at": iso(now_utc())}).eq("id", skill_id).execute()
