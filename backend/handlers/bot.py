"""
Telegram handler — v2.2 (chunk 3)

Added:
- remove person/business: Name — delete an entity
- Partial money settlement: "Fatima paid back 200"
"""
from __future__ import annotations

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core import config
from core.db import db, iso, now_utc
from core.kowalski import handle
from models import entities, items

log = logging.getLogger("kowalski.telegram")


def _authorised(update: Update) -> bool:
    uid = str(update.effective_user.id) if update.effective_user else ""
    return uid == config.TELEGRAM_CHAT_ID


async def _reply(update: Update, text: str, reply_markup=None) -> None:
    try:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    except Exception:                          # noqa: BLE001
        await update.message.reply_text(text, reply_markup=reply_markup)


# ── Patterns ────────────────────────────────────────────────────
SNOOZE_RE = re.compile(
    r"^snooze\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$",
    re.I,
)

ENTITY_CREATE_RE = re.compile(
    r"^(?:add|create|new)\s+(person|contact|business|client|friend|family|project|place)\s*[:\-]?\s*(.+)$",
    re.I | re.S,
)

ENTITY_REMOVE_RE = re.compile(
    r"^(?:remove|delete)\s+(person|business|contact|client|entity)\s*[:\-]?\s*(.+)$",
    re.I | re.S,
)

# "Fatima paid back 200" / "Fatima paid 200"
PARTIAL_SETTLE_RE = re.compile(
    r"^(.+?)\s+paid(?:\s+back)?\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)$",
    re.I,
)

KIND_MAP = {
    "person": "person", "contact": "person", "friend": "person",
    "family": "person", "client": "person",
    "business": "business", "company": "business",
    "project": "project", "place": "place",
}


def _parse_snooze(text: str):
    from datetime import timedelta
    m = SNOOZE_RE.match(text.strip())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("m"):
        return timedelta(minutes=n)
    if unit.startswith("h"):
        return timedelta(hours=n)
    return timedelta(days=n)


# ── Handlers ────────────────────────────────────────────────────
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    await _reply(update, (
        "👋 *Kowalski is alive.*\n\n"
        "Just talk naturally:\n"
        "• `remind me tomorrow 9pm to call Ali`\n"
        "• `task: fix the printer`\n"
        "• `note: passport in top drawer`\n"
        "• `Fatima owes me 500`\n"
        "• `Fatima paid back 200` — partial settlement\n"
        "• `add person: Rahim`\n"
        "• `remove person: Rahim`\n"
        "• `edit: old text → new text`\n"
        "• `delete last` / `delete: item name`\n"
        "• `snooze 1h` — after a reminder fires\n"
        "• `done` / `today` / `search X`"
    ))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    log.info("← %s", text[:80])

    # ── Snooze ───────────────────────────────────────────────────
    delta = _parse_snooze(text)
    if delta:
        res = (
            db().table("items").select("*")
            .eq("type", "reminder").eq("status", "open")
            .is_("deleted_at", "null")
            .order("created_at", desc=True).limit(1).execute()
        )
        if res.data:
            item = res.data[0]
            new_due = now_utc() + delta
            db().table("items").update({
                "due_at": iso(new_due),
                "notified_at": None,
            }).eq("id", item["id"]).execute()
            h = int(delta.total_seconds() // 3600)
            m_mins = int((delta.total_seconds() % 3600) // 60)
            when = f"{h}h" if h else f"{m_mins}m"
            await _reply(update, f"⏰ Snoozed — will remind you in {when}.")
        else:
            await _reply(update, "No recent reminder to snooze.")
        return

    # ── Entity create ────────────────────────────────────────────
    em = ENTITY_CREATE_RE.match(text)
    if em:
        raw_kind, name = em.group(1).lower(), em.group(2).strip()
        kind = KIND_MAP.get(raw_kind, "person")
        existing = entities.resolve(name)
        if existing:
            await _reply(update, f"👤 *{existing['name']}* already exists ({existing['kind']}).")
        else:
            ent = entities.create(name, kind)
            await _reply(update, f"✅ Created *{ent['name']}* as a {kind}.")
        return

    # ── Entity remove ────────────────────────────────────────────
    rm = ENTITY_REMOVE_RE.match(text)
    if rm:
        name = rm.group(2).strip()
        ent = entities.resolve(name)
        if not ent:
            await _reply(update, f'Couldn\'t find anyone matching "{name}".')
        else:
            entities.soft_delete(ent["id"])
            await _reply(update, f"🗑 Removed *{ent['name']}* from your people.")
        return

    # ── Partial money settlement ─────────────────────────────────
    pm = PARTIAL_SETTLE_RE.match(text)
    if pm:
        person_name = pm.group(1).strip()
        amount = float(pm.group(2).replace(",", ""))
        ent = entities.resolve(person_name)
        if not ent:
            await _reply(update, f'No entity found matching "{person_name}". Try "add person: {person_name}" first.')
            return

        # Find pending they_owe_me records for this entity
        res = (
            db().table("money").select("*")
            .eq("entity_id", ent["id"])
            .eq("direction", "they_owe_me")
            .eq("status", "pending")
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        if not res.data:
            await _reply(update, f"{ent['name']} has no pending money owed to you.")
            return

        # Apply partial payment — reduce oldest record first
        remaining = amount
        settled = []
        partially_reduced = []

        for rec in res.data:
            if remaining <= 0:
                break
            rec_amount = float(rec["amount"])
            if remaining >= rec_amount:
                # Fully settle this record
                db().table("money").update({
                    "status": "settled",
                    "settled_at": iso(now_utc()),
                }).eq("id", rec["id"]).execute()
                settled.append(rec_amount)
                remaining -= rec_amount
            else:
                # Partially reduce
                db().table("money").update({
                    "amount": rec_amount - remaining,
                }).eq("id", rec["id"]).execute()
                # Log the partial payment as a new settled record
                db().table("money").insert({
                    "entity_id": ent["id"],
                    "person_text": ent["name"],
                    "direction": "they_owe_me",
                    "amount": remaining,
                    "currency": rec.get("currency", "BDT"),
                    "note": f"partial payment",
                    "status": "settled",
                    "settled_at": iso(now_utc()),
                }).execute()
                partially_reduced.append(remaining)
                remaining = 0

        # Check new balance
        bal_res = (
            db().table("money").select("amount")
            .eq("entity_id", ent["id"])
            .eq("direction", "they_owe_me")
            .eq("status", "pending")
            .is_("deleted_at", "null")
            .execute()
        )
        new_balance = sum(float(r["amount"]) for r in (bal_res.data or []))

        if new_balance > 0:
            await _reply(update,
                f"💰 {ent['name']} paid ৳{amount:,.0f}.\n"
                f"Still owes: ৳{new_balance:,.0f}")
        else:
            await _reply(update,
                f"✅ {ent['name']} is fully settled. All clear!")
        return

    # ── Everything else → core ───────────────────────────────────
    response = handle(text, source="telegram")
    log.info("→ %s", response.text[:80])
    await _reply(update, response.text)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not query.data:
        return

    if query.data.startswith("done:"):
        item_id = query.data[5:]
        item = items.complete(item_id)
        if item:
            await query.edit_message_text(f"✅ Done — {item['content']}")
        else:
            await query.edit_message_text("Already marked done.")

    elif query.data.startswith("snooze1h:"):
        from datetime import timedelta
        item_id = query.data[9:]
        new_due = now_utc() + timedelta(hours=1)
        db().table("items").update({
            "due_at": iso(new_due),
            "notified_at": None,
        }).eq("id", item_id).execute()
        row = db().table("items").select("content").eq("id", item_id).execute()
        content = row.data[0]["content"] if row.data else "reminder"
        await query.edit_message_text(f"⏰ Snoozed 1h — {content}")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("telegram error: %s", context.error, exc_info=context.error)


def build_app() -> Application:
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help",  on_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)
    return app


def run_polling() -> None:
    log.info("polling mode (local dev)")
    build_app().run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import logging as _l
    _l.basicConfig(level=config.LOG_LEVEL,
                   format="%(levelname)-7s %(name)-20s %(message)s")
    run_polling()
