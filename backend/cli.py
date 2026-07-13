"""
Kowalski CLI.

    python cli.py              interactive shell
    python cli.py "note: hi"   one-shot
    python cli.py --test       run the parser test suite (no DB writes)
    python cli.py --health     check DB + AI providers

Why this exists before the Telegram bot:

Debugging through a chat app is miserable. You lose the traceback, you
can't rerun the last input, and every test costs you a message. Here,
the whole brain is one function call away and errors land in your face
where they belong.
"""
from __future__ import annotations

import logging
import sys

from core import config

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(levelname)-7s %(name)-16s %(message)s",
)

from core.kowalski import handle          # noqa: E402
from parsers import rules                 # noqa: E402
from parsers.router import understand     # noqa: E402


BANNER = """
╔══════════════════════════════════════╗
║   PROJECT KOWALSKI  ·  core v2       ║
║   Python owns the data.              ║
║   AI interprets the data.            ║
╚══════════════════════════════════════╝
type a message, or /quit
"""


def test_parser() -> None:
    """Parser only. No database. Instant. Run this after any rules change."""
    cases = [
        "remind me tomorrow at 9pm to call Fatima",
        "remind me in 30 minutes to check the oven",
        "remind me every day at 7am to take medicine",
        "task: fix the printer",
        "task buy milk tomorrow morning !!",
        "note: my passport expires in March",
        "idea: add loyalty cards to Jersey Fiesta",
        "journal: good day today",
        "Fatima owes me 500",
        "i owe Rahim 1200 for lunch",
        "borrowed 300 from Karim",
        "lent Fatima 2000",
        "done",
        "done printer",
        "search fatima",
        "today",
        "list tasks",
        "call ali friday 5pm",
        "meeting next monday 3pm #work",
        "remind me tonight",
    ]

    print("\n── RULES ENGINE ──────────────────────────────────────\n")
    ai_needed = 0

    for c in cases:
        p = rules.parse(c)
        if p.intent == "unknown":
            ai_needed += 1
            print(f"  ❓ AI NEEDED   {c!r}")
            continue

        bits = [f"{p.intent:9}"]
        if p.content:
            bits.append(f"“{p.content}”")
        if p.due_at:
            from core.db import fmt
            bits.append(f"@ {fmt(p.due_at)}")
        if p.recurrence:
            bits.append(f"🔁{p.recurrence}")
        if p.amount:
            bits.append(f"৳{p.amount:,.0f} {p.direction}")
        if p.person:
            bits.append(f"[{p.person}]")
        if p.tags:
            bits.append(" ".join(f"#{t}" for t in p.tags))
        if p.priority:
            bits.append("!" * p.priority)

        print(f"  ✓ {'  '.join(bits)}")
        print(f"      ← {c!r}")

    total = len(cases)
    handled = total - ai_needed
    pct = 100 * handled / total
    print(f"\n  {handled}/{total} handled by rules ({pct:.0f}%) — {ai_needed} would call AI")
    print("  Every one of those is $0.00 and ~0.2ms.\n")


def health() -> None:
    from ai import provider
    from core.db import db, now_local, now_utc

    print("\n── HEALTH ────────────────────────────────────────────\n")
    print(f"  local  {now_local():%Y-%m-%d %H:%M %Z}")
    print(f"  utc    {now_utc():%Y-%m-%d %H:%M}")

    try:
        n = db().table("items").select("id", count="exact").execute().count
        print(f"  db     ✓ connected — {n} items")
    except Exception as e:                     # noqa: BLE001
        print(f"  db     ✗ {e}")

    print()
    for name, status in provider.health().items():
        mark = "✓" if status.startswith("ok") else "✗"
        print(f"  {name:10} {mark} {status}")
    print()


def repl() -> None:
    print(BANNER)
    while True:
        try:
            text = input("› ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text in ("/quit", "/exit", "/q"):
            break

        if text == "/parse":
            test_parser()
            continue

        try:
            r = handle(text, source="api")
            print(f"\n{r.text}\n")
        except Exception as e:                 # noqa: BLE001
            import traceback
            traceback.print_exc()
            print(f"\n💥 {e}\n")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        repl()
    elif args[0] == "--test":
        test_parser()
    elif args[0] == "--health":
        health()
    else:
        r = handle(" ".join(args), source="api")
        print(r.text)
