"""
Main entry point.

One FastAPI app. Two sets of routes:
  /api/webhook  <- Telegram posts updates here
  /api/*        <- the dashboard calls these

Local dev:   uvicorn main:app --reload --port 8000
Vercel:      this file is the entry point (see vercel.json)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core import config
from core.kowalski import handle as kowalski_handle
from models import entities, items, money

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(levelname)-7s %(name)-20s %(message)s",
)

log = logging.getLogger("kowalski.main")

app = FastAPI(title="Kowalski", version="2.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════
#  TELEGRAM WEBHOOK
# ════════════════════════════════════════════════════════════════
from handlers.bot import build_app as _build_tg_app
_tg_app = _build_tg_app()


@app.post("/api/webhook")
async def webhook(request: Request) -> Response:
    """Telegram POSTs every message here. We process and return 200."""
    import hashlib, hmac, json
    from telegram import Update

    body = await request.body()

    secret = hashlib.sha256(config.TELEGRAM_BOT_TOKEN.encode()).digest()
    sig = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if sig:
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=403, detail="bad signature")

    try:
        data = json.loads(body)
        update = Update.de_json(data, _tg_app.bot)
        await _tg_app.initialize()
        await _tg_app.process_update(update)
    except Exception as e:
        log.error("webhook error: %s", e, exc_info=True)

    return Response(status_code=200)


# ════════════════════════════════════════════════════════════════
#  HEALTH
# ════════════════════════════════════════════════════════════════
@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "timezone": config.TIMEZONE}


# ════════════════════════════════════════════════════════════════
#  HANDLE
# ════════════════════════════════════════════════════════════════
class HandleRequest(BaseModel):
    text: str

@app.post("/api/handle")
def handle(body: HandleRequest) -> dict[str, Any]:
    r = kowalski_handle(body.text.strip(), source="web")
    return {"ok": r.ok, "text": r.text, "data": r.data}


# ════════════════════════════════════════════════════════════════
#  ITEMS
# ════════════════════════════════════════════════════════════════
@app.get("/api/items")
def list_items(
    type: str | None = None,
    status: str = "open",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    rows = items.list_items(type=type, status=status, limit=limit, offset=offset)
    return {"items": rows, "count": len(rows)}


@app.get("/api/items/today")
def today() -> dict:
    return {"items": items.today(), "overdue": items.overdue()}


@app.get("/api/items/counts")
def counts() -> dict:
    return items.counts()


@app.get("/api/items/{item_id}")
def get_item(item_id: str) -> dict:
    item = items.get(item_id)
    if not item:
        raise HTTPException(404, "item not found")
    return item


@app.patch("/api/items/{item_id}/done")
def complete_item(item_id: str) -> dict:
    item = items.complete(item_id)
    if not item:
        raise HTTPException(404, "item not found")
    return item


@app.delete("/api/items/{item_id}")
def delete_item(item_id: str) -> dict:
    items.soft_delete(item_id)
    return {"ok": True}


# ════════════════════════════════════════════════════════════════
#  SEARCH
# ════════════════════════════════════════════════════════════════
@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = 20) -> dict:
    results = items.search(q, limit=limit)
    return {"results": results, "count": len(results), "query": q}


# ════════════════════════════════════════════════════════════════
#  ENTITIES
# ════════════════════════════════════════════════════════════════
@app.get("/api/entities")
def list_entities(kind: str | None = None) -> dict:
    rows = entities.list_entities(kind=kind)
    return {"entities": rows, "count": len(rows)}


@app.get("/api/entities/{entity_id}")
def get_entity(entity_id: str) -> dict:
    ent = entities.get(entity_id)
    if not ent:
        raise HTTPException(404, "entity not found")
    return {"entity": ent, "timeline": entities.timeline(entity_id)}


class CreateEntityRequest(BaseModel):
    name: str
    kind: str = "person"
    meta: dict = {}

@app.post("/api/entities")
def create_entity(body: CreateEntityRequest) -> dict:
    return entities.create(body.name, body.kind, body.meta)


@app.delete("/api/entities/{entity_id}")
def delete_entity(entity_id: str) -> dict:
    entities.soft_delete(entity_id)
    return {"ok": True}


# ════════════════════════════════════════════════════════════════
#  MONEY
# ════════════════════════════════════════════════════════════════
@app.get("/api/money")
def list_money(direction: str | None = None) -> dict:
    rows = money.list_pending(direction=direction)
    return {"money": rows, "summary": money.summary()}


@app.patch("/api/money/{money_id}/settle")
def settle_money(money_id: str) -> dict:
    rec = money.settle(money_id)
    if not rec:
        raise HTTPException(404, "not found")
    return rec