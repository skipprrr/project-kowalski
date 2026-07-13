"""
Entities. People, businesses, projects.

Your idea, with one change: entities are a *dimension*, not a *root*.
Items exist on their own; entities link to them, many-to-many. So a
task can involve Fatima AND Jersey Fiesta, and — crucially — most
items have no entity at all, and that's fine.

The hard part here is resolution. "fatima", "Fatima", "fatma",
"fati", "my sister" should all land on one row. That's what aliases
and trigram matching are for.

THE SAFETY RULE (see link_by_name):
    Auto-linking only ever matches EXISTING entities.
    Creating a new entity requires an explicit act.

Without that rule you wake up one morning and your contact list
contains "Tomorrow", "Ugh", and "Bank".
"""
from __future__ import annotations

from core.db import db, iso, now_utc

TABLE = "entities"


def create(name: str, kind: str = "person", meta: dict | None = None) -> dict:
    res = db().table(TABLE).insert({
        "name": name.strip(),
        "kind": kind,
        "meta": meta or {},
    }).execute()
    ent = res.data[0]
    add_alias(ent["id"], name.strip().lower())
    return ent


def get(entity_id: str) -> dict | None:
    res = (
        db().table(TABLE).select("*")
        .eq("id", entity_id).is_("deleted_at", "null").limit(1).execute()
    )
    return res.data[0] if res.data else None


def list_entities(kind: str | None = None) -> list[dict]:
    q = db().table(TABLE).select("*").is_("deleted_at", "null")
    if kind:
        q = q.eq("kind", kind)
    return q.order("name").execute().data or []


def add_alias(entity_id: str, alias: str) -> None:
    try:
        db().table("entity_aliases").insert({
            "entity_id": entity_id,
            "alias": alias.strip().lower(),
        }).execute()
    except Exception:          # noqa: BLE001 — duplicate alias is fine
        pass


def resolve(name: str) -> dict | None:
    """
    Name -> entity, or None.

    Exact match, then alias, then fuzzy (trigram). Returns None rather
    than guessing wildly — a wrong link is worse than no link.
    """
    if not name or not name.strip():
        return None
    res = db().rpc("resolve_entity", {"q": name.strip()}).execute()
    return res.data[0] if res.data else None


def resolve_or_create(name: str, kind: str = "person") -> dict:
    """Only call this when the user has EXPLICITLY named someone."""
    found = resolve(name)
    return found or create(name, kind)


def link(item_id: str, entity_id: str, role: str = "about") -> None:
    try:
        db().table("item_entities").insert({
            "item_id": item_id,
            "entity_id": entity_id,
            "role": role,
        }).execute()
    except Exception:          # noqa: BLE001 — already linked
        pass


def link_by_name(item_id: str, names: list[str]) -> list[str]:
    """
    Link an item to entities by name — but ONLY ones that already exist.

    This is the guardrail. Auto-extraction from free text is noisy;
    letting it create rows would pollute your entity list within a week.
    Returns the names it successfully linked.
    """
    linked: list[str] = []
    for n in names:
        ent = resolve(n)
        if ent:
            link(item_id, ent["id"])
            linked.append(ent["name"])
    return linked


def timeline(entity_id: str, limit: int = 100) -> list[dict]:
    """
    Everything about Fatima. One join.

    This is the query the whole entity design exists to make cheap.
    """
    res = (
        db().table("item_entities")
        .select("role, items(*)")
        .eq("entity_id", entity_id)
        .limit(limit)
        .execute()
    )
    items = [r["items"] for r in (res.data or []) if r.get("items")]
    items = [i for i in items if not i.get("deleted_at")]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    return items


def soft_delete(entity_id: str) -> None:
    db().table(TABLE).update({"deleted_at": iso(now_utc())}).eq("id", entity_id).execute()
