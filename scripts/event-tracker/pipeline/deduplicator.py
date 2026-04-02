"""
pipeline/deduplicator.py — Hash-based deduplication + PostgreSQL upsert.

Deduplication strategy:
  - Hash is SHA-256 of: ticker + event_type + event_date + title (normalized/lowercased)
  - Hash stored in market_events.hash (UNIQUE constraint)
  - INSERT ... ON CONFLICT (hash) DO NOTHING → idempotent, safe to re-run
  - Returns stats: { inserted, skipped, errors }
"""

import hashlib
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras

from config import config

logger = logging.getLogger(__name__)


# ── Hash Generation ────────────────────────────────────────────

def generate_hash(event: Dict[str, Any]) -> str:
    """
    Generate a stable SHA-256 deduplication hash for an event.
    Components: ticker + event_type + event_date + title (all lowercased/stripped).
    """
    ticker = str(event.get("ticker") or "").strip().lower()
    event_type = str(event.get("event_type") or "").strip().lower()
    event_date = str(event.get("event_date") or "").strip()
    title = str(event.get("title") or "").strip().lower()

    raw = f"{ticker}|{event_type}|{event_date}|{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── JSON serializer for psycopg2 ──────────────────────────────

def _json_serial(obj):
    """JSON serializer for objects not serializable by default encoder."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _to_json(obj: Any) -> str:
    return json.dumps(obj, default=_json_serial, ensure_ascii=False)


# ── Upsert Logic ───────────────────────────────────────────────

_UPSERT_SQL = """
INSERT INTO market_events (
    event_type,
    source,
    ticker,
    company,
    title,
    description,
    event_date,
    announcement_date,
    record_date,
    ex_date,
    book_build_start,
    book_build_end,
    listing_date,
    url,
    hash,
    raw_payload
)
VALUES (
    %(event_type)s,
    %(source)s,
    %(ticker)s,
    %(company)s,
    %(title)s,
    %(description)s,
    %(event_date)s,
    %(announcement_date)s,
    %(record_date)s,
    %(ex_date)s,
    %(book_build_start)s,
    %(book_build_end)s,
    %(listing_date)s,
    %(url)s,
    %(hash)s,
    %(raw_payload)s
)
ON CONFLICT (hash) DO NOTHING
RETURNING event_id;
"""


def deduplicate_and_store(
    events: List[Dict[str, Any]],
    batch_size: int = 50,
) -> Dict[str, int]:
    """
    Generate hashes, deduplicate, and upsert events to PostgreSQL.

    Uses batch commits (every `batch_size` rows) and individual error
    handling so one bad row doesn't block the entire batch.

    Returns:
        { "inserted": int, "skipped": int, "errors": int }
    """
    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    if not events:
        logger.info("No events to store.")
        return stats

    try:
        conn = psycopg2.connect(config.dsn())
        conn.autocommit = False
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        stats["errors"] = len(events)
        return stats

    cur = conn.cursor()

    for i, event in enumerate(events):
        try:
            event_hash = generate_hash(event)

            params = {
                "event_type":        event.get("event_type", "UNKNOWN"),
                "source":            event.get("source", "UNKNOWN"),
                "ticker":            event.get("ticker"),
                "company":           event.get("company"),
                "title":             event.get("title", ""),
                "description":       event.get("description"),
                "event_date":        event.get("event_date"),
                "announcement_date": event.get("announcement_date"),
                "record_date":       event.get("record_date"),
                "ex_date":           event.get("ex_date"),
                "book_build_start":  event.get("book_build_start"),
                "book_build_end":    event.get("book_build_end"),
                "listing_date":      event.get("listing_date"),
                "url":               event.get("url"),
                "hash":              event_hash,
                "raw_payload":       psycopg2.extras.Json(
                    event.get("raw_payload", {}),
                    dumps=lambda x: _to_json(x)
                ),
            }

            cur.execute(_UPSERT_SQL, params)
            result = cur.fetchone()

            if result:
                stats["inserted"] += 1
            else:
                stats["skipped"] += 1
                logger.debug(f"Duplicate skipped: hash={event_hash} title='{event.get('title')}'")

        except Exception as e:
            logger.error(
                f"Failed to upsert event '{event.get('title', '')}': {e}"
            )
            stats["errors"] += 1
            conn.rollback()
            # Re-start transaction for remaining rows
            conn.autocommit = False
            cur = conn.cursor()
            continue

        # Commit in batches to avoid large transactions
        if (i + 1) % batch_size == 0:
            conn.commit()
            logger.debug(f"Committed batch at event {i + 1}")

    # Final commit for remaining rows
    conn.commit()
    cur.close()
    conn.close()

    logger.info(
        f"Storage complete — inserted: {stats['inserted']}, "
        f"skipped (duplicate): {stats['skipped']}, "
        f"errors: {stats['errors']}"
    )
    return stats
