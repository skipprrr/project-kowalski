"""
Telegram handler — v2.3 (chunk 4)

New commands:
    learning: Mandarin [— want to hold a conversation]
    skill update: Mandarin 65%
    skill log: boxing 45 minutes — did sparring
    skills                          — list all skills
    remove skill: Mandarin

    project: Jersey Fiesta Website [— due next friday]
    task under [project]: fix checkout
    list projects
    project done: name

    health: weight 72kg
    health: slept 7 hours
    health: ran 5km

    read: Atomic Habits
    read: https://someurl.com

    met [person] [today/yesterday] — [note about the meeting]
"""
from __future__ import annotations

import logging
import re

from telegram import Update
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
from core.timeutil import fmt
from models import entities, items, skills as skills_model, projects as projects_model

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
    r"^snooze\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$", re.I)

ENTITY_CREATE_RE = re.compile(
    r"^(?:add|create|new)\s+(person|contact|business|client|friend|family|project|place)\s*[:\-]?\s*(.+)$",
    re.I | re.S)

ENTITY_REMOVE_RE = re.compile(
    r"^(?:remove|delete)\s+(person|business|contact|client|entity)\s*[:\-]?\s*(.+)$",
    re.I | re.S)

PARTIAL_SETTLE_RE = re.compile(
    r"^(.+?)\s+paid(?:\s+back)?\s+(?:tk\.?|bdt|৳|\$)?\s*([\d,]+(?:\.\d+)?)$", re.I)

# Skills
LEARNING_RE = re.compile(
    r"^(?:learning|learn|studying|study|practicing|practice)\s*[:\-]?\s*(.+)$", re.I | re.S)

SKILL_UPDATE_RE = re.compile(
    r"^skill\s+(?:update|progress)\s*[:\-]?\s*(.+?)\s+(\d{1,3})\s*%$", re.I)

SKILL_LOG_RE = re.compile(
    r"^skill\s+(?:log|session|did)\s*[:\-]?\s*(.+?)(?:\s+(\d+)\s*(?:min|mins|minutes|hr|hrs|hours))?\s*(?:[—\-]+\s*(.+))?$",
    re.I)

SKILL_LIST_RE = re.compile(r"^skills?\s*$", re.I)
SKILL_REMOVE_RE = re.compile(r"^remove\s+skill\s*[:\-]?\s*(.+)$", re.I)

# Projects
PROJECT_CREATE_RE = re.compile(
    r"^project\s*[:\-]\s*(.+?)(?:\s*[—\-]+\s*due\s+(.+))?$", re.I | re.S)

PROJECT_TASK_RE = re.compile(
    r"^task\s+(?:under|for|in)\s+(.+?)\s*[:\-]\s*(.+)$", re.I | re.S)

PROJECT_LIST_RE = re.compile(r"^list\s+projects?\s*$", re.I)

PROJECT_DONE_RE = re.compile(r"^project\s+done\s*[:\-]?\s*(.+)$", re.I)

# Health
HEALTH_RE = re.compile(r"^health\s*[:\-]\s*(.+)$", re.I | re.S)

# Reading list
READ_RE = re.compile(r"^(?:read|reading|book)\s*[:\-]\s*(.+)$", re.I | re.S)

# Contact note
MET_RE = re.compile(
    r"^met\s+(.+?)\s+(?:today|yesterday|just\s+now|earlier)?\s*(?:[—\-]+\s*(.+))?$",
    re.I | re.S)

KIND_MAP = {
    "person": "person", "contact": "person", "friend": "person",
    "family": "person", "client": "person",
    "business": "business", "project": "project", "place": "place",
}


def _parse_snooze(text: str):
    from datetime import timedelta
    m = SNOOZE_RE.match(text.strip())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("m"):   return timedelta(minutes=n)
    if unit.startswith("h"):   return timedelta(hours=n)
    return timedelta(days=n)


# ── Handlers ────────────────────────────────────────────────────
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update): return
    await _reply(update, (
        "👋 *Kowalski v2*\n\n"
        "*Capture:*\n"
        "• `remind me tomorrow 9pm to call Ali`\n"
        "• `task: fix the printer !!`\n"
        "• `note: passport in top drawer`\n"
        "• `Fatima owes me 500` / `Fatima paid back 200`\n\n"
        "*People:*\n"
        "• `add person: Rahim` / `remove person: Rahim`\n"
        "• `met Fatima today — discussed the collab`\n\n"
        "*Skills:*\n"
        "• `learning: Mandarin`\n"
        "• `skill update: Mandarin 65%`\n"
        "• `skill log: boxing 45 minutes — sparring`\n"
        "• `skills` — list all\n\n"
        "*Projects:*\n"
        "• `project: Jersey Fiesta Website`\n"
        "• `task under Jersey Fiesta: fix checkout`\n"
        "• `list projects`\n\n"
        "*Health & Reading:*\n"
        "• `health: weight 72kg`\n"
        "• `read: Atomic Habits`\n\n"
        "*Manage:*\n"
        "• `edit: old → new` / `delete last`\n"
        "• `snooze 1h` / `done` / `today` / `search X`"
    ))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update): return
    text = (update.message.text or "").strip()
    if not text: return
    log.info("← %s", text[:80])

    # ── Snooze ───────────────────────────────────────────────────
    delta = _parse_snooze(text)
    if delta:
        res = (db().table("items").select("*")
               .eq("type", "reminder").eq("status", "open")
               .is_("deleted_at", "null")
               .order("created_at", desc=True).limit(1).execute())
        if res.data:
            new_due = now_utc() + delta
            db().table("items").update({"due_at": iso(new_due), "notified_at": None}
                                       ).eq("id", res.data[0]["id"]).execute()
            h = int(delta.total_seconds() // 3600)
            m_mins = int((delta.total_seconds() % 3600) // 60)
            await _reply(update, f"⏰ Snoozed — in {'{}h'.format(h) if h else '{}m'.format(m_mins)}.")
        else:
            await _reply(update, "No recent reminder to snooze.")
        return

    # ── Skills: list ─────────────────────────────────────────────
    if SKILL_LIST_RE.match(text):
        all_skills = skills_model.list_skills()
        if not all_skills:
            await _reply(update, "No skills tracked yet. Say `learning: Something` to add one.")
            return
        lines = ["🎯 *Your skills*\n"]
        for s in all_skills:
            bar = "█" * (s["progress"] // 10) + "░" * (10 - s["progress"] // 10)
            lines.append(f"*{s['name']}* — {s['progress']}%\n`{bar}`")
            if s.get("goal"):
                lines.append(f"_Goal: {s['goal']}_")
        await _reply(update, "\n".join(lines))
        return

    # ── Skills: add ──────────────────────────────────────────────
    m = LEARNING_RE.match(text)
    if m:
        body = m.group(1).strip()
        # Split on dash for optional goal
        parts = re.split(r"\s*[—\-]{1,2}\s*", body, maxsplit=1)
        name = parts[0].strip()
        goal = parts[1].strip() if len(parts) > 1 else None
        existing = skills_model.get_by_name(name)
        if existing:
            await _reply(update, f"🎯 Already tracking *{existing['name']}* ({existing['progress']}%).")
        else:
            s = skills_model.create(name, goal=goal)
            await _reply(update, f"🎯 Added *{s['name']}* to your skills." +
                         (f"\n_Goal: {goal}_" if goal else ""))
        return

    # ── Skills: update progress ──────────────────────────────────
    m = SKILL_UPDATE_RE.match(text)
    if m:
        name, pct = m.group(1).strip(), int(m.group(2))
        s = skills_model.get_by_name(name)
        if not s:
            await _reply(update, f'No skill matching "{name}". Say `learning: {name}` to add it.')
            return
        skills_model.update_progress(s["id"], pct)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        await _reply(update, f"📈 *{s['name']}* → {pct}%\n`{bar}`")
        return

    # ── Skills: log session ──────────────────────────────────────
    m = SKILL_LOG_RE.match(text)
    if m:
        name = m.group(1).strip()
        duration = int(m.group(2)) if m.group(2) else None
        note = (m.group(3) or "").strip() or f"session logged"
        s = skills_model.get_by_name(name)
        if not s:
            await _reply(update, f'No skill matching "{name}". Say `learning: {name}` to add it.')
            return
        skills_model.add_log(s["id"], note, duration)
        dur_txt = f" ({duration} min)" if duration else ""
        await _reply(update, f"✍️ Logged *{s['name']}*{dur_txt} — {note}")
        return

    # ── Skills: remove ───────────────────────────────────────────
    m = SKILL_REMOVE_RE.match(text)
    if m:
        s = skills_model.get_by_name(m.group(1).strip())
        if not s:
            await _reply(update, f'No skill matching "{m.group(1)}".')
        else:
            skills_model.soft_delete(s["id"])
            await _reply(update, f"🗑 Removed *{s['name']}* from your skills.")
        return

    # ── Projects: create ─────────────────────────────────────────
    m = PROJECT_CREATE_RE.match(text)
    if m:
        name = m.group(1).strip()
        due_text = m.group(2)
        due_at = None
        if due_text:
            from parsers.timeparse import parse_time
            t = parse_time(due_text)
            if t.matched:
                due_at = t.due_at
        existing = projects_model.get_by_name(name)
        if existing:
            await _reply(update, f"📁 *{existing['name']}* already exists.")
        else:
            p = projects_model.create(name, due_at=due_at)
            due_str = f"\n📅 Due: {fmt(p['due_at'])}" if p.get("due_at") else ""
            await _reply(update, f"📁 Project *{p['name']}* created.{due_str}")
        return

    # ── Projects: add task ───────────────────────────────────────
    m = PROJECT_TASK_RE.match(text)
    if m:
        proj_name, task_content = m.group(1).strip(), m.group(2).strip()
        proj = projects_model.get_by_name(proj_name)
        if not proj:
            await _reply(update, f'No project matching "{proj_name}". Say `project: {proj_name}` first.')
            return
        item = items.create(
            type="task", content=task_content,
            raw_input=text, source="telegram", parsed_by="rules",
        )
        db().table("items").update({"project_id": proj["id"]}).eq("id", item["id"]).execute()
        await _reply(update, f"📋 Task added to *{proj['name']}*:\n{task_content}")
        return

    # ── Projects: list ───────────────────────────────────────────
    if PROJECT_LIST_RE.match(text):
        all_proj = projects_model.list_projects()
        if not all_proj:
            await _reply(update, "No active projects. Say `project: Name` to create one.")
            return
        lines = ["📁 *Active projects*\n"]
        for p in all_proj:
            due = f" — due {fmt(p['due_at'])}" if p.get("due_at") else ""
            lines.append(f"• *{p['name']}*{due}")
        await _reply(update, "\n".join(lines))
        return

    # ── Projects: done ───────────────────────────────────────────
    m = PROJECT_DONE_RE.match(text)
    if m:
        proj = projects_model.get_by_name(m.group(1).strip())
        if not proj:
            await _reply(update, f'No project matching "{m.group(1)}".')
        else:
            projects_model.complete(proj["id"])
            await _reply(update, f"✅ Project *{proj['name']}* marked done.")
        return

    # ── Health ───────────────────────────────────────────────────
    m = HEALTH_RE.match(text)
    if m:
        content = m.group(1).strip()
        item = items.create(
            type="health", content=content,
            raw_input=text, source="telegram", parsed_by="rules",
        )
        await _reply(update, f"💪 Health logged — {content}")
        return

    # ── Reading list ─────────────────────────────────────────────
    m = READ_RE.match(text)
    if m:
        content = m.group(1).strip()
        item = items.create(
            type="read", content=content,
            raw_input=text, source="telegram", parsed_by="rules",
        )
        await _reply(update, f"📚 Added to reading list — {content}")
        return

    # ── Contact note ─────────────────────────────────────────────
    m = MET_RE.match(text)
    if m:
        person_name = m.group(1).strip()
        note_text = (m.group(2) or "").strip() or f"met {person_name}"
        ent = entities.resolve(person_name)
        if not ent:
            ent = entities.create(person_name, kind="person")
        item = items.create(
            type="note",
            content=f"Met {ent['name']}" + (f" — {note_text}" if note_text != f"met {person_name}" else ""),
            raw_input=text, source="telegram", parsed_by="rules",
        )
        entities.link(item["id"], ent["id"], role="about")
        await _reply(update, f"👤 Contact note saved — *{ent['name']}*" +
                     (f"\n_{note_text}_" if note_text and note_text != f"met {person_name}" else ""))
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
        ent = entities.resolve(rm.group(2).strip())
        if not ent:
            await _reply(update, f'Couldn\'t find anyone matching "{rm.group(2)}".')
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
            await _reply(update, f'No entity found for "{person_name}". Try `add person: {person_name}` first.')
            return
        res = (db().table("money").select("*")
               .eq("entity_id", ent["id"]).eq("direction", "they_owe_me")
               .eq("status", "pending").is_("deleted_at", "null")
               .order("created_at", desc=True).execute())
        if not res.data:
            await _reply(update, f"{ent['name']} has no pending money owed to you.")
            return
        remaining = amount
        for rec in res.data:
            if remaining <= 0: break
            rec_amount = float(rec["amount"])
            if remaining >= rec_amount:
                db().table("money").update({"status": "settled", "settled_at": iso(now_utc())}
                                           ).eq("id", rec["id"]).execute()
                remaining -= rec_amount
            else:
                db().table("money").update({"amount": rec_amount - remaining}).eq("id", rec["id"]).execute()
                db().table("money").insert({
                    "entity_id": ent["id"], "person_text": ent["name"],
                    "direction": "they_owe_me", "amount": remaining,
                    "currency": rec.get("currency", "BDT"),
                    "note": "partial payment", "status": "settled",
                    "settled_at": iso(now_utc()),
                }).execute()
                remaining = 0
        bal_res = (db().table("money").select("amount")
                   .eq("entity_id", ent["id"]).eq("direction", "they_owe_me")
                   .eq("status", "pending").is_("deleted_at", "null").execute())
        new_balance = sum(float(r["amount"]) for r in (bal_res.data or []))
        if new_balance > 0:
            await _reply(update, f"💰 {ent['name']} paid ৳{amount:,.0f}.\nStill owes: ৳{new_balance:,.0f}")
        else:
            await _reply(update, f"✅ {ent['name']} is fully settled. All clear!")
        return

    # ── Everything else → core ───────────────────────────────────
    response = handle(text, source="telegram")
    log.info("→ %s", response.text[:80])
    await _reply(update, response.text)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from models import items as items_model
    query = update.callback_query
    await query.answer()
    if not query.data: return

    if query.data.startswith("done:"):
        item = items_model.complete(query.data[5:])
        await query.edit_message_text(f"✅ Done — {item['content']}" if item else "Already done.")

    elif query.data.startswith("snooze1h:"):
        from datetime import timedelta
        item_id = query.data[9:]
        new_due = now_utc() + timedelta(hours=1)
        db().table("items").update({"due_at": iso(new_due), "notified_at": None}
                                   ).eq("id", item_id).execute()
        row = db().table("items").select("content").eq("id", item_id).execute()
        content = row.data[0]["content"] if row.data else "reminder"
        await query.edit_message_text(f"⏰ Snoozed 1h — {content}")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("telegram error: %s", context.error, exc_info=context.error)


def build_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help",  on_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)
    return app


def run_polling() -> None:
    log.info("polling mode")
    build_app().run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import logging as _l
    _l.basicConfig(level=config.LOG_LEVEL, format="%(levelname)-7s %(name)-20s %(message)s")
    run_polling()
