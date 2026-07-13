"""
Items. Tasks, reminders, notes, ideas, journal entries — one table.

Every function here is deterministic Python talking to Postgres.
No AI reaches this layer. It never should.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core.db import db, iso, now_utc

TABLE = "items"


def create(
    *,
    type: str,
    content: str,
    raw_input: str | None = None,
    due_at: datetime | None = None,
    due_text: str | None = None,
    notify: bool = False,
    recurrence: str | None = None,
    priority: int = 0,
    tags: list[str] | None = None,
    source: str = "telegram",
    parsed_by: str | None = None,
) -> dict:
    row = {
        "type": type,
        "content": content,
        "raw_input": raw_input,
        "due_at": iso(due_at),
        "due_text": due_text,
        "notify": notify,
        "recurrence": recurrence,
        "priority": priority,
        "tags": tags or [],
        "source": source,
        "parsed_by": parsed_by,
    }
    res = db().table(TABLE).insert(row).execute()
    return res.data[0]


def get(item_id: str) -> dict | None:
    res = (
        db().table(TABLE).select("*")
        .eq("id", item_id).is_("deleted_at", "null")
        .limit(1).execute()
    )
    return res.data[0] if res.data else None


def list_items(
    *,
    type: str | None = None,
    status: str = "open",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    q = db().table(TABLE).select("*").is_("deleted_at", "null")
    if type:
        q = q.eq("type", type)
    if status != "all":
        q = q.eq("status", status)
    res = (
        q.order("priority", desc=True)
         .order("due_at", desc=False, nullsfirst=False)
         .order("created_at", desc=True)
         .range(offset, offset + limit - 1)
         .execute()
    )
    return res.data or []


def complete(item_id: str) -> dict | None:
    res = (
        db().table(TABLE)
        .update({
            "status": "done",
            "completed_at": iso(now_utc()),
            "notify": False,          # a finished task must never ping you
        })
        .eq("id", item_id).execute()
    )
    return res.data[0] if res.data else None


def complete_latest(type: str = "task") -> dict | None:
    """`done` with no argument — finish the most recent open task."""
    res = (
        db().table(TABLE).select("*")
        .eq("type", type).eq("status", "open").is_("deleted_at", "null")
        .order("created_at", desc=True).limit(1).execute()
    )
    if not res.data:
        return None
    return complete(res.data[0]["id"])


def soft_delete(item_id: str) -> None:
    db().table(TABLE).update({"deleted_at": iso(now_utc())}).eq("id", item_id).execute()


def update(item_id: str, **fields: Any) -> dict | None:
    if "due_at" in fields and isinstance(fields["due_at"], datetime):
        fields["due_at"] = iso(fields["due_at"])
    res = db().table(TABLE).update(fields).eq("id", item_id).execute()
    return res.data[0] if res.data else None


def today() -> list[dict]:
    """Due today, Dhaka time. Reads the v_today view — the DB does the TZ math."""
    res = db().table("v_today").select("*").execute()
    return res.data or []


def overdue() -> list[dict]:
    res = db().table("v_overdue").select("*").execute()
    return res.data or []


def search(query: str, limit: int = 20) -> list[dict]:
    """
    Full-text + fuzzy. Calls the search_items() SQL function, which
    uses the GIN indexes. "fatma" still finds Fatima.
    """
    res = db().rpc("search_items", {"q": query, "limit_n": limit}).execute()
    return res.data or []


def counts() -> dict[str, int]:
    """Dashboard tiles."""
    out: dict[str, int] = {}
    for t in ("task", "reminder", "note", "idea", "journal"):
        res = (
            db().table(TABLE)
            .select("id", count="exact")
            .eq("type", t).eq("status", "open").is_("deleted_at", "null")
            .execute()
        )
        out[t] = res.count or 0
    out["overdue"] = len(overdue())
    out["today"] = len(today())
    return out
