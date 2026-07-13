"""
Money.

Kept out of `items` on purpose: a ledger has semantics a note doesn't.
Amounts, direction, settlement, arithmetic that must be exactly right.

v1's fatal flaw was storing `person` and `amount` with no direction.
"Fatima, 500" — does she owe you, or you her? The table could not say.
Everything here exists to make that question always answerable.
"""
from __future__ import annotations

from core.db import db, iso, now_utc
from models import entities

TABLE = "money"


def create(
    *,
    person: str,
    amount: float,
    direction: str,               # they_owe_me | i_owe_them
    note: str | None = None,
    raw_input: str | None = None,
    currency: str = "BDT",
) -> dict:
    if direction not in ("they_owe_me", "i_owe_them"):
        raise ValueError(f"bad direction: {direction}")
    if amount <= 0:
        raise ValueError("amount must be positive")

    # Money always names a real person, so creating the entity is correct here.
    ent = entities.resolve_or_create(person, kind="person")

    res = db().table(TABLE).insert({
        "entity_id": ent["id"],
        "person_text": person,
        "direction": direction,
        "amount": amount,
        "currency": currency,
        "note": note,
        "raw_input": raw_input,
    }).execute()
    return res.data[0]


def list_pending(direction: str | None = None) -> list[dict]:
    q = (
        db().table(TABLE)
        .select("*, entities(name)")
        .eq("status", "pending").is_("deleted_at", "null")
    )
    if direction:
        q = q.eq("direction", direction)
    return q.order("created_at", desc=True).execute().data or []


def settle(money_id: str) -> dict | None:
    res = (
        db().table(TABLE)
        .update({"status": "settled", "settled_at": iso(now_utc())})
        .eq("id", money_id).execute()
    )
    return res.data[0] if res.data else None


def balances() -> list[dict]:
    """Net position per person. Positive = they owe you."""
    return db().table("v_money_balance").select("*").execute().data or []


def summary() -> dict:
    rows = balances()
    owed_to_me = sum(r["net_amount"] for r in rows if r["net_amount"] > 0)
    i_owe = sum(-r["net_amount"] for r in rows if r["net_amount"] < 0)
    return {
        "owed_to_me": float(owed_to_me),
        "i_owe": float(i_owe),
        "net": float(owed_to_me - i_owe),
        "people": rows,
    }
