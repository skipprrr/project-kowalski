"""
Webhook entry point.

Telegram calls this URL every time you send a message.
Vercel wakes this function, we process the update, Vercel sleeps.
No always-on server. No cost.

URL Telegram will POST to:
    https://your-project.vercel.app/api/webhook
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import FastAPI, HTTPException, Request, Response

from core import config
from handlers.bot import build_app

log = logging.getLogger("kowalski.webhook")

# Build once per cold start, reused across warm invocations.
# python-telegram-bot's Application handles its own async internals.
_tg_app = build_app()


async def _process(body: bytes) -> None:
    from telegram import Update
    data = json.loads(body)
    update = Update.de_json(data, _tg_app.bot)
    await _tg_app.initialize()
    await _tg_app.process_update(update)


app = FastAPI(title="Kowalski Webhook", docs_url=None, redoc_url=None)


@app.post("/api/webhook")
async def webhook(request: Request) -> Response:
    """Telegram calls this. We process and return 200 immediately."""
    body = await request.body()

    # Verify the request is genuinely from Telegram.
    # Without this, anyone can POST fake updates to your bot.
    secret = hashlib.sha256(config.TELEGRAM_BOT_TOKEN.encode()).digest()
    sig = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()

    # Telegram doesn't send this header for all update types, so we
    # only reject if the header IS present but wrong.
    if sig and not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="bad signature")

    try:
        await _process(body)
    except Exception as e:                     # noqa: BLE001
        # Never return a non-200 to Telegram — it will retry forever.
        log.error("update processing failed: %s", e, exc_info=True)

    return Response(status_code=200)
