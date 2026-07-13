"""
Telegram handler — with inline buttons and snooze.

Changes from v1:
- Reminders now arrive with ✅ Done and ⏰ Snooze 1h buttons
- Tapping a button completes or snoozes the reminder
- "snooze 1h" / "snooze 2h" etc. work as text commands too
- "add person: X" / "add business: X" create entities
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

# ── Auth ────────────────────────────────────────────────────────
def _authorised(update: Update) -> bool:
    uid = str(update.effective_user.id) if update.effective_user else ""
    return uid == config.TELEGRAM_CHAT_ID

# ── Helpers ─────────────────────────────────────────────────────
async def _reply(update: Update, text: str, reply_markup=None) -> None:
    try:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    except Exception:                          # noqa: BLE001
        await update.message.reply_text(text, reply_markup=reply_markup)

# ── Snooze parser ────────────────────────────────────────────────
SNOOZE_RE = re.compile(
    r"^snooze\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$",
    re.I,
)

def _parse_snooze(text: str):
    """Return timedelta or None."""
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

# ── Entity creation shortcut ─────────────────────────────────────
ENTITY_RE = re.compile(
    r"^(?:add|create|new)\s+(person|contact|business|client|friend|family|project|place)\s*[:\-]?\s*(.+)$",
    re.I | re.S,
)

KIND_MAP = {
    "person": "person", "contact": "person", "friend": "person",
    "family": "person", "client": "person",
    "business": "business", "company": "business",
    "project": "project", "place": "place",
}

# ── Handlers ─────────────────────────────────────────────────────
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
        "• `add person: Rahim`\n"
        "• `add business: Corner Cafe`\n"
        "• `snooze 1h` — after a reminder fires\n"
        "• `done` — complete latest task\n"
        "• `today` / `search X`"
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
        # Find the most recent open reminder
        res = (
            db().table("items").select("*")
            .eq("type", "reminder").eq("status", "open")
            .is_("deleted_at", "null")
            .order("created_at", desc=True).limit(1).execute()
        )
        if res.data:
            item = res.data[0]
            from core.timeutil import now_utc, to_utc
            from datetime import timezone
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

    # ── Entity creation ──────────────────────────────────────────
    em = ENTITY_RE.match(text)
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

    # ── Everything else → core handler ──────────────────────────
    response = handle(text, source="telegram")
    log.info("→ %s", response.text[:80])
    await _reply(update, response.text)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button taps (✅ Done, ⏰ Snooze)."""
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
        item_id = query.data[9:]
        from datetime import timedelta
        from core.timeutil import now_utc
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


# ── App builder ──────────────────────────────────────────────────
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
