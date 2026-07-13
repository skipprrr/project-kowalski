"""
Register the Telegram webhook.

Run this ONCE after deploying to Vercel:
    python set_webhook.py https://your-project.vercel.app

Run with no args to check the current webhook:
    python set_webhook.py
"""
from __future__ import annotations

import sys
import httpx

from core import config


def check() -> None:
    r = httpx.get(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    )
    info = r.json().get("result", {})
    url = info.get("url", "(none)")
    pending = info.get("pending_update_count", 0)
    last_err = info.get("last_error_message", "")
    print(f"  url:     {url}")
    print(f"  pending: {pending}")
    if last_err:
        print(f"  error:   {last_err}")


def set_webhook(vercel_url: str) -> None:
    url = vercel_url.rstrip("/") + "/api/webhook"
    r = httpx.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/setWebhook",
        json={"url": url, "drop_pending_updates": True},
    )
    result = r.json()
    if result.get("ok"):
        print(f"✅ Webhook set to: {url}")
    else:
        print(f"❌ Failed: {result}")


def delete_webhook() -> None:
    r = httpx.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/deleteWebhook",
        json={"drop_pending_updates": True},
    )
    print("✅ Webhook deleted (polling mode)" if r.json().get("ok") else "❌ Failed")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("\n── Current webhook ──")
        check()
    elif args[0] == "delete":
        delete_webhook()
    else:
        set_webhook(args[0])
