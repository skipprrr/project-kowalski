"""
Projects model.

A project groups tasks together under one name and optional deadline.

Bot commands:
    project: Jersey Fiesta Website
    project: Jersey Fiesta Website — due next friday
    task under Jersey Fiesta: fix the checkout button
    list projects
    project done: Jersey Fiesta Website
"""
from __future__ import annotations

from core.db import db, iso, now_utc

TABLE = "projects"


def create(name: str, description: str | None = None,
           due_at=None, entity_id: str | None = None) -> dict:
    res = db().table(TABLE).insert({
        "name": name.strip(),
        "description": description,
        "due_at": iso(due_at) if due_at else None,
        "entity_id": entity_id,
    }).execute()
    return res.data[0]


def list_projects(status: str = "active") -> list[dict]:
    q = db().table(TABLE).select("*").is_("deleted_at", "null")
    if status != "all":
        q = q.eq("status", status)
    return q.order("created_at", desc=True).execute().data or []


def get_by_name(name: str) -> dict | None:
    rows = (
        db().table(TABLE).select("*")
        .ilike("name", f"%{name.strip()}%")
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def get(project_id: str) -> dict | None:
    res = db().table(TABLE).select("*").eq("id", project_id).is_("deleted_at", "null").execute()
    return res.data[0] if res.data else None


def tasks(project_id: str) -> list[dict]:
    return (
        db().table("items").select("*")
        .eq("project_id", project_id)
        .is_("deleted_at", "null")
        .order("priority", desc=True)
        .order("created_at")
        .execute()
        .data or []
    )


def complete(project_id: str) -> dict | None:
    res = db().table(TABLE).update({"status": "done"}).eq("id", project_id).execute()
    return res.data[0] if res.data else None


def soft_delete(project_id: str) -> None:
    db().table(TABLE).update({"deleted_at": iso(now_utc())}).eq("id", project_id).execute()
