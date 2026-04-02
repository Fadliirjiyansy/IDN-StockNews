"""
main.py — IDX Event Tracker Flask API

Endpoints:
  GET  /health              — Health check
  POST /run                 — Trigger full scrape → normalize → store pipeline
  GET  /events/new          — Return events inserted in the last N hours (for n8n alerting)
  GET  /events              — Query stored events (with optional filters)
  GET  /events/ipo          — IPO calendar (upcoming, next 30 days)
  GET  /events/suspensions  — Active suspensions (last 7 days)

Run:
  python main.py
  # or via gunicorn:
  gunicorn -w 2 -b 0.0.0.0:5055 main:app
"""

import json
import logging
import sys
from datetime import date, datetime, timezone, timedelta
from typing import Any

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request
from flask_cors import CORS

from config import config
from scrapers import (
    IDXIPOScraper,
    IDXCorporateActionsScraper,
    IDXSuspensionsScraper,
    IDXMeetingsScraper,
)
from pipeline import normalize_events, validate_events, deduplicate_and_store

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("event-tracker")

# ── Flask App ─────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ── JSON Encoder ───────────────────────────────────────────────

class _DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = _DateEncoder


# ── DB Helper ─────────────────────────────────────────────────

def _get_db():
    return psycopg2.connect(config.dsn(), cursor_factory=psycopg2.extras.RealDictCursor)


def _query_db(sql: str, params: tuple = ()) -> list:
    """Execute a SELECT query and return list of dicts."""
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Routes ────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check — also verifies DB connectivity."""
    try:
        conn = _get_db()
        conn.close()
        db_ok = True
    except Exception as e:
        logger.warning(f"DB health check failed: {e}")
        db_ok = False

    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "db":     "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.2.0",
    })


@app.route("/run", methods=["POST"])
def run_pipeline():
    """
    Trigger the full event pipeline:
      1. Scrape all sources
      2. Normalize
      3. Validate
      4. Deduplicate & store to PostgreSQL

    Returns a summary with insert/skip/error counts.
    """
    run_start = datetime.now(timezone.utc)
    logger.info("Pipeline run triggered")

    try:
        # ── 1. Scrape ──
        raw_events = []
        scraper_stats = {}

        scrapers = {
            "ipo":              IDXIPOScraper(),
            "corporate_action": IDXCorporateActionsScraper(),
            "suspension":       IDXSuspensionsScraper(),
            "meeting":          IDXMeetingsScraper(),
        }

        for name, scraper in scrapers.items():
            try:
                batch = scraper.fetch()
                raw_events.extend(batch)
                scraper_stats[name] = {"fetched": len(batch), "status": "ok"}
                logger.info(f"Scraper '{name}': {len(batch)} raw events")
            except Exception as e:
                logger.error(f"Scraper '{name}' failed: {e}", exc_info=True)
                scraper_stats[name] = {"fetched": 0, "status": "error", "error": str(e)}

        # ── 2. Normalize ──
        normalized = normalize_events(raw_events)

        # ── 3. Validate ──
        valid_events = validate_events(normalized)

        # ── 4. Store ──
        storage_stats = deduplicate_and_store(valid_events)

        duration_ms = int((datetime.now(timezone.utc) - run_start).total_seconds() * 1000)

        return jsonify({
            "status":       "ok",
            "duration_ms":  duration_ms,
            "run_at":       run_start.isoformat(),
            "scrapers":     scraper_stats,
            "total_raw":    len(raw_events),
            "total_valid":  len(valid_events),
            "inserted":     storage_stats["inserted"],
            "skipped":      storage_stats["skipped"],
            "errors":       storage_stats["errors"],
        })

    except Exception as e:
        logger.error(f"Pipeline run failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/events/new", methods=["GET"])
def get_new_events():
    """
    Return events inserted in the last N hours.
    Used by n8n to detect new events and send Telegram alerts.

    Query params:
      hours (int, default=7): look-back window in hours
      types (str, comma-separated): filter by event type e.g. "IPO,DIVIDEND"
    """
    hours = int(request.args.get("hours", config.NEW_EVENTS_WINDOW_HOURS))
    types_filter = request.args.get("types", "")

    sql = """
        SELECT
            event_id::text,
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
            created_at
        FROM market_events
        WHERE created_at >= NOW() - INTERVAL '%s hours'
    """
    params: list = [hours]

    if types_filter:
        types_list = [t.strip().upper() for t in types_filter.split(",") if t.strip()]
        if types_list:
            placeholders = ",".join(["%s"] * len(types_list))
            sql += f" AND event_type IN ({placeholders})"
            params.extend(types_list)

    sql += " ORDER BY event_type, created_at DESC;"

    try:
        rows = _query_db(sql, tuple(params))
        return jsonify({
            "count": len(rows),
            "hours": hours,
            "events": rows,
        })
    except Exception as e:
        logger.error(f"GET /events/new failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/ipo", methods=["GET"])
def get_ipo_calendar():
    """Return upcoming IPOs from the database view (next 30 days)."""
    try:
        rows = _query_db("SELECT * FROM v_upcoming_ipo;")
        return jsonify({"count": len(rows), "events": rows})
    except Exception as e:
        logger.error(f"GET /events/ipo failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/corporate-actions", methods=["GET"])
def get_corporate_actions():
    """Return upcoming corporate actions (next 30 days)."""
    try:
        rows = _query_db("SELECT * FROM v_upcoming_corporate_actions;")
        return jsonify({"count": len(rows), "events": rows})
    except Exception as e:
        logger.error(f"GET /events/corporate-actions failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/suspensions", methods=["GET"])
def get_suspensions():
    """Return active trading suspensions (last 7 days)."""
    try:
        rows = _query_db("SELECT * FROM v_active_suspensions;")
        return jsonify({"count": len(rows), "events": rows})
    except Exception as e:
        logger.error(f"GET /events/suspensions failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/meetings", methods=["GET"])
def get_meetings():
    """Return upcoming AGM/EGM (next 30 days)."""
    try:
        rows = _query_db("SELECT * FROM v_upcoming_meetings;")
        return jsonify({"count": len(rows), "events": rows})
    except Exception as e:
        logger.error(f"GET /events/meetings failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events", methods=["GET"])
def get_events():
    """
    Generic event query with optional filters.
    Query params:
      type (str): event type filter
      ticker (str): ticker filter
      days (int, default=30): how many days ahead/back to look
    """
    event_type = request.args.get("type", "").upper()
    ticker     = request.args.get("ticker", "").upper()
    days       = int(request.args.get("days", 30))

    sql = """
        SELECT
            event_id::text, event_type, source, ticker, company,
            title, event_date, ex_date, listing_date, url, created_at
        FROM market_events
        WHERE created_at >= NOW() - INTERVAL '%s days'
    """
    params: list = [days]

    if event_type:
        sql += " AND event_type = %s"
        params.append(event_type)
    if ticker:
        sql += " AND ticker = %s"
        params.append(ticker)

    sql += " ORDER BY event_date DESC, created_at DESC LIMIT 200;"

    try:
        rows = _query_db(sql, tuple(params))
        return jsonify({"count": len(rows), "events": rows})
    except Exception as e:
        logger.error(f"GET /events failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Starting IDX Event Tracker API on {config.API_HOST}:{config.API_PORT}")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.API_DEBUG,
    )
