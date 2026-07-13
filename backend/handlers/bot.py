"""
Telegram handler.

This file's only job: translate between Telegram and Kowalski.

Receive message → call handle() → send reply.

No business logic lives here. If you find yourself writing an if/else
about what a message means, you're in the wrong file — that belongs in
core/kowalski.py or the parser.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core import config
from core.kowalski import handle

log = logging.getLogger("kowalski.telegram")


# ── SECURITY ────────────────────────────────────────────────────
# Kowalski is personal. One user. Reject everyone else silently.
# Without this, anyone who finds your bot can write to your database.
def _authorised(update: Update) -> bool:
    uid = str(update.effective_user.id) if update.effective_user else ""
    return uid == config.TELEGRAM_CHAT_ID


async def _reject(update: Update) -> None:
    log.warning("unauthorised user %s", update.effective_user)
    # Say nothing. Don't confirm the bot exists to strangers.


# ── HELPERS ─────────────────────────────────────────────────────
async def _reply(update: Update, text: str) -> None:
    """Send a message. Try Markdown, fall back to plain text."""
    try:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception:                          # noqa: BLE001
        await update.message.reply_text(text)


# ── HANDLERS ────────────────────────────────────────────────────
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return await _reject(update)
    await _reply(update, (
        "👋 Kowalski is alive.\n\n"
        "Just talk to me naturally:\n"
        "• `remind me tomorrow 9pm to call Ali`\n"
        "• `task: fix the printer`\n"
        "• `note: passport in top drawer`\n"
        "• `Fatima owes me 500`\n"
        "• `today` — see what's on\n"
        "• `search Ali` — find anything\n"
        "• `done` — complete latest task"
    ))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return await _reject(update)

    text = (update.message.text or "").strip()
    if not text:
        return

    log.info("← %s", text[:80])

    response = handle(text, source="telegram")
    log.info("→ %s", response.text[:80])

    await _reply(update, response.text)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("telegram error: %s", context.error, exc_info=context.error)


# ── ENTRY POINTS ────────────────────────────────────────────────
def build_app() -> Application:
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)
    return app


def run_polling() -> None:
    """
    Local development mode.

    Your PC talks directly to Telegram. No webhook, no public URL needed.
    Use this while developing — it hot-reloads on save.
    Run with: python -m handlers.bot
    """
    log.info("starting in polling mode (local dev)")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(levelname)-7s %(name)-20s %(message)s",
    )
    run_polling()
