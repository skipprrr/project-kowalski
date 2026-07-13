"""
Database access. The ONLY place a Supabase client is constructed.

Time helpers used to live here. They moved to core/timeutil.py so that
the parser can be tested without a database. Re-exported below purely
for import convenience — timeutil remains the source of truth.
"""
from __future__ import annotations

# lru_cache removed — Supabase HTTP/2 connections drop when idle

from supabase import Client, create_client

from core import config
from core.timeutil import fmt, iso, now_local, now_utc, time_only, to_local, to_utc

__all__ = [
    "db",
    "fmt", "iso", "now_local", "now_utc", "time_only", "to_local", "to_utc",
]


def db() -> Client:
    """The Supabase client. Cached — one connection pool, not fifty."""
    config.require("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
