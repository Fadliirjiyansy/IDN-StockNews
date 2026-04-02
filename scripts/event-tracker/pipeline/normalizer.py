"""
pipeline/normalizer.py — Normalize raw scraped records into unified event schema.

Two responsibilities:
  1. Classify event_type via keyword matching (rule-based, no ML needed).
  2. Map raw fields (varying per scraper) → canonical market_events schema.
"""

import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional

from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

# ── Event Classification Rules ──────────────────────────────
# Order matters: more specific patterns checked first.
# Each entry: (event_type, [keyword_patterns_lowercased])

CLASSIFICATION_RULES: List[tuple] = [
    # IPO
    ("IPO", [
        "ipo", "initial public offering", "penawaran umum perdana", "penawaran saham perdana",
        "bookbuilding", "book building", "new listing", "pencatatan saham baru",
        "listing date", "tanggal pencatatan",
    ]),
    # Delisting
    ("DELISTING", [
        "delisting", "penghapusan pencatatan", "penghapusan saham",
    ]),
    # Dividend
    ("DIVIDEND", [
        "dividend", "dividen", "cash dividend", "dividen tunai",
        "interim dividend", "dividen interim", "distribution",
    ]),
    # Rights Issue
    ("RIGHTS_ISSUE", [
        "rights issue", "right issue", "hmetd", "hak memesan efek terlebih dahulu",
        "penawaran umum terbatas", "put", "penerbitan saham baru dengan hak memesan",
    ]),
    # Stock Split
    ("STOCK_SPLIT", [
        "stock split", "split saham", "pemecahan saham", "pemecahan nilai nominal",
        "share split",
    ]),
    # Bonus Shares
    ("BONUS_SHARES", [
        "bonus share", "saham bonus", "saham dividen", "share dividend",
        "kapitalisasi agio",
    ]),
    # Buyback
    ("BUYBACK", [
        "buyback", "buy back", "pembelian kembali", "pembelian kembali saham",
        "share repurchase",
    ]),
    # Private Placement
    ("PRIVATE_PLACEMENT", [
        "private placement", "penawaran terbatas", "pp tanpa hmetd",
        "penerbitan saham tanpa hmetd",
    ]),
    # Suspension
    ("SUSPENSION", [
        "suspend", "suspensi", "penghentian perdagangan", "trading halt",
        "dihentikan sementara", "unusual market activity",
        "unusual market activity (uma)",  # full phrase only — 'uma' alone is too short
        "trading suspension",              # and matches 'pengumuman' (Indonesian: announcement)
    ]),
    # EGM (check before AGM — more specific)
    ("EGM", [
        "rupslb", "rups luar biasa", "egm", "extraordinary general meeting",
        "rapat umum pemegang saham luar biasa",
    ]),
    # AGM
    ("AGM", [
        "rups", "agm", "annual general meeting",
        "rapat umum pemegang saham tahunan", "rupst",
    ]),
]


def classify_event(title: str, description: str = "") -> str:
    """
    Classify event type by matching keywords in title + description.
    Returns event_type string (e.g. 'IPO', 'DIVIDEND', 'UNKNOWN').
    Handles None inputs gracefully.
    """
    # Guard against None inputs (can happen with partial raw records)
    safe_title = str(title) if title is not None else ""
    safe_desc = str(description) if description is not None else ""
    search_text = (safe_title + " " + safe_desc).lower()

    for event_type, keywords in CLASSIFICATION_RULES:
        for kw in keywords:
            if kw in search_text:
                return event_type

    return "UNKNOWN"


# ── Date Normalization ───────────────────────────────────────

_ID_MONTH_MAP = {
    "januari": "january", "februari": "february", "maret": "march",
    "april": "april", "mei": "may", "juni": "june",
    "juli": "july", "agustus": "august", "september": "september",
    "oktober": "october", "november": "november", "desember": "december",
    # Abbreviations
    "jan": "jan", "feb": "feb", "mar": "mar", "apr": "apr",
    "mei": "may", "jun": "jun", "jul": "jul", "agt": "aug",
    "sep": "sep", "okt": "oct", "nov": "nov", "des": "dec",
}


def normalize_date(raw: Any) -> Optional[date]:
    """
    Parse a date from any common format (ISO, Indonesian, English).
    Returns datetime.date or None if unparseable.
    """
    if raw is None:
        return None

    if isinstance(raw, date):
        return raw

    raw_str = str(raw).strip()
    if not raw_str or raw_str.lower() in ("n/a", "nan", "-", ""):
        return None

    # Translate Indonesian month names → English
    lower = raw_str.lower()
    for id_month, en_month in _ID_MONTH_MAP.items():
        lower = lower.replace(id_month, en_month)

    try:
        return dateutil_parser.parse(lower, dayfirst=True).date()
    except Exception:
        logger.debug(f"Could not parse date: '{raw_str}'")
        return None


# ── Ticker Normalization ──────────────────────────────────────

def normalize_ticker(raw: Any) -> Optional[str]:
    """
    Normalize IDX ticker: uppercase, strip whitespace, validate 1–6 chars.
    Returns None for invalid tickers.
    """
    if raw is None:
        return None
    ticker = str(raw).strip().upper()
    # IDX tickers: 1–6 uppercase letters, no digits (except some like ADR5, B74, etc.)
    if re.match(r'^[A-Z0-9]{1,6}$', ticker):
        return ticker
    return None


# ── Canonical Field Map ───────────────────────────────────────

def normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a raw scraper record into the canonical event schema.
    Unknown fields are preserved in raw_payload.
    """
    title = str(raw.get("title", "")).strip()
    description = str(raw.get("description", "")).strip()
    event_type = raw.get("event_type") or classify_event(title, description)

    return {
        "event_type":        event_type,
        "source":            str(raw.get("source", "UNKNOWN")).upper(),
        "ticker":            normalize_ticker(raw.get("ticker")),
        "company":           str(raw.get("company", "")).strip() or None,
        "title":             title,
        "description":       description or None,
        "event_date":        normalize_date(raw.get("event_date")),
        "announcement_date": normalize_date(raw.get("announcement_date")),
        "record_date":       normalize_date(raw.get("record_date")),
        "ex_date":           normalize_date(raw.get("ex_date")),
        "book_build_start":  normalize_date(raw.get("book_build_start")),
        "book_build_end":    normalize_date(raw.get("book_build_end")),
        "listing_date":      normalize_date(raw.get("listing_date")),
        "url":               str(raw.get("url", "")).strip() or None,
        "raw_payload":       raw,
    }


def normalize_events(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a list of raw event records. Skips records that raise."""
    normalized = []
    for i, raw in enumerate(raw_events):
        try:
            normalized.append(normalize_event(raw))
        except Exception as e:
            logger.warning(f"Failed to normalize event[{i}]: {e} | raw={raw}")
    logger.info(f"Normalized {len(normalized)}/{len(raw_events)} events")
    return normalized
