"""
pipeline/validator.py — Validate normalized event records before storage.

Validation rules:
  - title must not be empty (required field)
  - event_type must be a known enum value
  - ticker, if present, must already be normalized (1–6 alphanumeric)
  - at least one meaningful date must be present
  - source must be a known enum value

Invalid records are logged and discarded (not stored).
"""

import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Valid enum values (must match PostgreSQL enums in schema.sql) ──

VALID_EVENT_TYPES = {
    "IPO", "DIVIDEND", "RIGHTS_ISSUE", "STOCK_SPLIT", "BONUS_SHARES",
    "BUYBACK", "PRIVATE_PLACEMENT", "SUSPENSION", "AGM", "EGM",
    "DELISTING", "UNKNOWN",
}

VALID_SOURCES = {"IDX", "EIPO", "KSEI", "UNKNOWN"}


# ── Individual field validators ────────────────────────────────

def _validate_title(event: Dict[str, Any]) -> Optional[str]:
    title = event.get("title")
    if not title or not str(title).strip():
        return "title is empty or missing"
    return None


def _validate_event_type(event: Dict[str, Any]) -> Optional[str]:
    et = event.get("event_type")
    if et not in VALID_EVENT_TYPES:
        return f"invalid event_type '{et}'"
    return None


def _validate_source(event: Dict[str, Any]) -> Optional[str]:
    src = event.get("source")
    if src not in VALID_SOURCES:
        # Correct silently rather than reject — source is not critical
        event["source"] = "UNKNOWN"
    return None


def _validate_ticker(event: Dict[str, Any]) -> Optional[str]:
    ticker = event.get("ticker")
    if ticker is None:
        return None  # ticker is optional (some announcements are market-wide)
    if not re.match(r'^[A-Z0-9]{1,6}$', str(ticker)):
        # Silently clear invalid ticker rather than discard the whole record
        logger.debug(f"Invalid ticker '{ticker}' cleared from event: {event.get('title')}")
        event["ticker"] = None
    return None


def _validate_dates(event: Dict[str, Any]) -> Optional[str]:
    date_fields = [
        "event_date", "announcement_date", "record_date", "ex_date",
        "book_build_start", "book_build_end", "listing_date",
    ]
    has_any_date = any(
        isinstance(event.get(f), date) for f in date_fields
    )
    if not has_any_date:
        return "no valid date found in any date field"
    return None


def _validate_url(event: Dict[str, Any]) -> Optional[str]:
    url = event.get("url")
    if url and not str(url).startswith(("http://", "https://")):
        logger.debug(f"Malformed URL cleared: '{url}'")
        event["url"] = None
    return None


# ── Entry point ───────────────────────────────────────────────

_VALIDATORS = [
    _validate_title,
    _validate_event_type,
    _validate_source,
    _validate_ticker,
    _validate_dates,
    _validate_url,
]


def validate_event(event: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Run all validations on a single event dict.
    Returns (is_valid: bool, reason: str | None).
    """
    for validator in _VALIDATORS:
        error = validator(event)
        if error:
            return False, error
    return True, None


def validate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate a list of normalized events.
    Returns only valid events, discards invalid ones with logging.
    """
    valid = []
    discarded = 0

    for event in events:
        is_valid, reason = validate_event(event)
        if is_valid:
            valid.append(event)
        else:
            discarded += 1
            logger.warning(
                f"Discarded invalid event — reason: {reason} | "
                f"title='{event.get('title', '')}' ticker='{event.get('ticker', '')}'"
            )

    logger.info(
        f"Validation complete: {len(valid)} valid, {discarded} discarded "
        f"(total={len(events)})"
    )
    return valid
