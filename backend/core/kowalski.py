"""
KOWALSKI CORE — v2.1

Added in chunk 2:
- edit: [search] → [new content]
- delete last
- delete: [search term]
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.db import fmt
from models import entities, items, money
from parsers.router import understand

log = logging.getLogger("kowalski")


@dataclass
class Response:
    text: str
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)


ICON = {
    "task": "📋", "reminder": "🔔", "note": "📝",
    "idea": "💡", "journal": "📔", "money": "💰",
}

_FORGET_RE = re.compile(r"^(don'?t|do not)\s+forget\s+", re.I)

# ── Edit pattern: "edit: printer → fix the printer urgently"
EDIT_RE = re.compile(
    r"^edit\s*:\s*(.+?)\s*[→\->]+\s*(.+)$",
    re.I | re.S,
)

# ── Delete patterns
DELETE_LAST_RE = re.compile(r"^delete\s+last$", re.I)
DELETE_RE = re.compile(r"^delete\s*:\s*(.+)$", re.I)


def handle(text: str, source: str = "telegram") -> Response:
    raw = text.strip()

    # ── Edit ────────────────────────────────────────────────────
    m = EDIT_RE.match(raw)
    if m:
        return _edit(m.group(1).strip(), m.group(2).strip())

    # ── Delete last ─────────────────────────────────────────────
    if DELETE_LAST_RE.match(raw):
        return _delete_last()

    # ── Delete by search ────────────────────────────────────────
    m = DELETE_RE.match(raw)
    if m:
        return _delete_search(m.group(1).strip())

    # ── Normal flow ─────────────────────────────────────────────
    p = understand(raw)
    log.info("intent=%s parsed_by=%s conf=%.1f", p.intent, p.parsed_by, p.confidence)

    if p.intent == "today":   return _today()
    if p.intent == "done":    return _done(p)
    if p.intent == "search":  return _search(p)
    if p.intent == "list":    return _list(p)
    if p.intent == "money":   return _money(p, source)

    if p.intent in ("task", "reminder", "note", "idea", "journal"):
        return _capture(p, source)

    item = items.create(
        type="note", content=raw, raw_input=raw,
        source=source, parsed_by="fallback",
    )
    return Response("📝 Saved as a note (couldn't parse it).", data={"item": item})


# ═══════════════════════════════════════════════════════════════
#  EDIT
# ═══════════════════════════════════════════════════════════════
def _edit(search: str, new_content: str) -> Response:
    hits = items.search(search, limit=1)
    open_hits = [h for h in hits if h["status"] == "open"]
    if not open_hits:
        return Response(f'Couldn\'t find an open item matching "{search}".', ok=False)
    item = items.update(open_hits[0]["id"], content=new_content)
    return Response(f"✏️ Updated — {new_content}", data={"item": item})


# ═══════════════════════════════════════════════════════════════
#  DELETE
# ═══════════════════════════════════════════════════════════════
def _delete_last() -> Response:
    res = (
        __import__("core.db", fromlist=["db"]).db()
        .table("items").select("*")
        .is_("deleted_at", "null")
        .order("created_at", desc=True).limit(1).execute()
    )
    if not res.data:
        return Response("Nothing to delete.", ok=False)
    item = res.data[0]
    items.soft_delete(item["id"])
    return Response(f"🗑 Deleted — {item['content']}")


def _delete_search(search: str) -> Response:
    hits = items.search(search, limit=1)
    if not hits:
        return Response(f'Nothing found matching "{search}".', ok=False)
    item = hits[0]
    items.soft_delete(item["id"])
    return Response(f"🗑 Deleted — {item['content']}")


# ═══════════════════════════════════════════════════════════════
#  CAPTURE
# ═══════════════════════════════════════════════════════════════
def _capture(p, source: str) -> Response:
    item = items.create(
        type=p.intent,
        content=p.content,
        raw_input=p.raw_input,
        due_at=p.due_at,
        due_text=p.due_text,
        notify=p.notify,
        recurrence=p.recurrence,
        priority=p.priority,
        tags=p.tags,
        source=source,
        parsed_by=p.parsed_by,
    )

    linked = entities.link_by_name(item["id"], p.entities) if p.entities else []

    icon = ICON.get(p.intent, "✅")
    content_clean = _FORGET_RE.sub("", p.content).strip()
    lines = [f"{icon} {content_clean}"]

    if item.get("due_at"):
        when = fmt(item["due_at"])
        if p.recurrence:
            lines.append(f"🔁 {p.recurrence} — next: {when}")
        else:
            lines.append(f"🕐 {when}")

    if linked:
        lines.append(f"👤 {', '.join(linked)}")
    if p.tags:
        lines.append("🏷 " + " ".join(f"#{t}" for t in p.tags))
    if p.priority:
        lines.append("❗" * p.priority)

    if p.intent == "reminder" and not item.get("due_at"):
        lines.append("⚠️ No time found — saved, but it won't ping you.")

    return Response("\n".join(lines), data={"item": item})


# ═══════════════════════════════════════════════════════════════
#  TODAY
# ═══════════════════════════════════════════════════════════════
def _today() -> Response:
    due = items.today()
    late = items.overdue()
    tasks = items.list_items(type="task", limit=10)
    tasks = [t for t in tasks if not t.get("due_at")]

    if not (due or late or tasks):
        return Response("Nothing today. Clear head. 🧘")

    out: list[str] = []

    if late:
        out.append("⚠️ *Overdue*")
        out += [f"  • {i['content']} — {fmt(i['due_at'])}" for i in late[:5]]
        out.append("")

    if due:
        out.append("📅 *Today*")
        out += [f"  • {fmt(i['due_at'])[-8:].strip()} — {i['content']}" for i in due]
        out.append("")

    if tasks:
        out.append("📋 *Open tasks*")
        out += [f"  • {t['content']}" for t in tasks[:7]]

    return Response("\n".join(out).strip(),
                    data={"today": due, "overdue": late, "tasks": tasks})


# ═══════════════════════════════════════════════════════════════
#  DONE
# ═══════════════════════════════════════════════════════════════
def _done(p) -> Response:
    if p.content:
        hits = items.search(p.content, limit=1)
        open_hits = [h for h in hits if h["status"] == "open"]
        if not open_hits:
            return Response(f'Couldn\'t find an open item matching "{p.content}".', ok=False)
        item = items.complete(open_hits[0]["id"])
    else:
        item = items.complete_latest("task")
        if not item:
            item = items.complete_latest("reminder")

    if not item:
        return Response("Nothing open to complete.", ok=False)

    return Response(f"✅ Done — {item['content']}", data={"item": item})


# ═══════════════════════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════════════════════
def _search(p) -> Response:
    hits = items.search(p.content, limit=10)
    if not hits:
        return Response(f'Nothing found for "{p.content}".', ok=False)

    lines = [f"🔍 *{p.content}* — {len(hits)} result(s)\n"]
    for h in hits:
        icon = ICON.get(h["type"], "•")
        mark = "" if h["status"] == "open" else " ✓"
        when = f" — {fmt(h['due_at'])}" if h.get("due_at") else ""
        lines.append(f"{icon} {h['content']}{when}{mark}")

    return Response("\n".join(lines), data={"results": hits})


# ═══════════════════════════════════════════════════════════════
#  LIST
# ═══════════════════════════════════════════════════════════════
def _list(p) -> Response:
    rows = items.list_items(type=p.content, limit=20)
    if not rows:
        return Response(f"No open {p.content}s.")

    icon = ICON.get(p.content, "•")
    lines = [f"{icon} *{p.content.title()}s* — {len(rows)}\n"]
    for r in rows:
        when = f" — {fmt(r['due_at'])}" if r.get("due_at") else ""
        lines.append(f"• {r['content']}{when}")

    return Response("\n".join(lines), data={"items": rows})


# ═══════════════════════════════════════════════════════════════
#  MONEY
# ═══════════════════════════════════════════════════════════════
def _money(p, source: str) -> Response:
    rec = money.create(
        person=p.person,
        amount=p.amount,
        direction=p.direction,
        note=p.content,
        raw_input=p.raw_input,
    )

    if p.direction == "they_owe_me":
        msg = f"💰 {p.person} owes you ৳{p.amount:,.0f}  (→ you)"
    else:
        msg = f"💰 You owe {p.person} ৳{p.amount:,.0f}  (you →)"

    return Response(msg, data={"money": rec})
