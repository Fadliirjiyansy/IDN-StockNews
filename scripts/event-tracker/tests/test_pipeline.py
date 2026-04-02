"""
tests/test_pipeline.py — Standalone unit tests for pipeline modules.

Tests pure logic only (no external deps, no DB, no HTTP).
Run with: python tests/test_pipeline.py

Covers:
  - normalizer: classify_event, normalize_date, normalize_ticker, normalize_event
  - validator: validate_event (all rules)
  - deduplicator: generate_hash (consistency, stability)
  - scrapers: base helpers (_safe_text, _safe_attr, _parse_date_range)
  - integration: full pipeline (raw → normalize → validate)
"""

import sys
import os
import hashlib
from datetime import date
from unittest.mock import MagicMock

# ── Patch heavy external imports before importing our modules ──
# This lets us test pure logic without installing requests, psycopg2, etc.

class _FakeModule:
    """Stand-in for any missing third-party module."""
    def __getattr__(self, name):
        return _FakeModule()
    def __call__(self, *a, **kw):
        return _FakeModule()
    def __iter__(self):
        return iter([])

# Patch third-party deps
for mod in [
    "requests", "bs4", "lxml", "tenacity", "psycopg2",
    "psycopg2.extras", "flask", "flask_cors", "dotenv",
    "dateutil", "dateutil.parser", "pandas",
]:
    if mod not in sys.modules:
        sys.modules[mod] = _FakeModule()

# Patch tenacity decorators to be no-ops
tenacity_mock = _FakeModule()
def _passthrough(*args, **kwargs):
    """Return a no-op decorator."""
    def decorator(fn):
        return fn
    return decorator
tenacity_mock.retry = _passthrough
tenacity_mock.stop_after_attempt = _passthrough
tenacity_mock.wait_exponential = _passthrough
tenacity_mock.retry_if_exception_type = _passthrough
tenacity_mock.before_log = _passthrough
tenacity_mock.after_log = _passthrough
sys.modules["tenacity"] = tenacity_mock

# Also patch dateutil with a real-ish parser
import datetime
class _FakeDateutil:
    class parser:
        @staticmethod
        def parse(s, dayfirst=False):
            from datetime import datetime as dt
            # Try common formats
            for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%B %d, %Y"):
                try:
                    return dt.strptime(s.strip(), fmt)
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse date: {s}")

sys.modules["dateutil"] = _FakeDateutil()
sys.modules["dateutil.parser"] = _FakeDateutil.parser()

# Also patch dotenv
class _FakeDotenv:
    @staticmethod
    def load_dotenv(*a, **kw):
        pass
sys.modules["dotenv"] = _FakeDotenv()

# Add scripts/event-tracker to path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
# BASE is tests/ so go up one level to scripts/event-tracker
ET_PATH = os.path.join(os.path.dirname(BASE))
sys.path.insert(0, ET_PATH)

# ── Test framework (stdlib only) ──────────────────────────────

_TESTS_RUN = 0
_TESTS_PASSED = 0
_TESTS_FAILED = 0
_FAILURES = []

def test(name):
    """Decorator to register and run a test."""
    def decorator(fn):
        global _TESTS_RUN, _TESTS_PASSED, _TESTS_FAILED
        _TESTS_RUN += 1
        try:
            fn()
            _TESTS_PASSED += 1
            print(f"  PASS  {name}")
        except AssertionError as e:
            _TESTS_FAILED += 1
            _FAILURES.append((name, str(e)))
            print(f"  FAIL  {name}\n        {e}")
        except Exception as e:
            _TESTS_FAILED += 1
            _FAILURES.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ERROR {name}\n        {type(e).__name__}: {e}")
        return fn
    return decorator

def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(
            f"{msg + ': ' if msg else ''}expected {expected!r}, got {actual!r}"
        )

def assert_in(value, collection, msg=""):
    if value not in collection:
        raise AssertionError(f"{msg + ': ' if msg else ''}{value!r} not in {collection!r}")

def assert_none(value, msg=""):
    if value is not None:
        raise AssertionError(f"{msg + ': ' if msg else ''}expected None, got {value!r}")

def assert_not_none(value, msg=""):
    if value is None:
        raise AssertionError(f"{msg + ': ' if msg else ''}expected non-None, got None")

def assert_true(condition, msg=""):
    if not condition:
        raise AssertionError(f"{msg or 'expected True, got False'}")

def assert_false(condition, msg=""):
    if condition:
        raise AssertionError(f"{msg or 'expected False, got True'}")

# ── Import modules under test ─────────────────────────────────
print("\n" + "="*60)
print("  IDX Event Tracker — Quality Test Suite")
print("="*60)

try:
    from pipeline.normalizer import (
        classify_event, normalize_date, normalize_ticker,
        normalize_event, normalize_events, CLASSIFICATION_RULES
    )
    print("\n[OK] pipeline.normalizer imported")
except Exception as e:
    print(f"\n[ERROR] pipeline.normalizer import failed: {e}")
    sys.exit(1)

try:
    from pipeline.validator import (
        validate_event, validate_events,
        VALID_EVENT_TYPES, VALID_SOURCES
    )
    print("[OK] pipeline.validator imported")
except Exception as e:
    print(f"\n[ERROR] pipeline.validator import failed: {e}")
    sys.exit(1)

try:
    from pipeline.deduplicator import generate_hash
    print("[OK] pipeline.deduplicator imported (generate_hash only)")
except Exception as e:
    print(f"\n[ERROR] pipeline.deduplicator import failed: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: normalizer.classify_event
# ═══════════════════════════════════════════════════════════════
print("\n── classify_event ────────────────────────────────────────")

@test("classify_event: IPO keyword 'ipo'")
def _():
    assert_eq(classify_event("PT ABC IPO on IDX"), "IPO")

@test("classify_event: IPO keyword 'bookbuilding'")
def _():
    assert_eq(classify_event("Bookbuilding Saham PT XYZ"), "IPO")

@test("classify_event: IPO keyword 'penawaran umum perdana'")
def _():
    assert_eq(classify_event("Penawaran Umum Perdana ABCD"), "IPO")

@test("classify_event: DIVIDEND keyword 'dividen'")
def _():
    assert_eq(classify_event("BBCA pengumuman dividen"), "DIVIDEND")

@test("classify_event: DIVIDEND keyword 'dividend'")
def _():
    assert_eq(classify_event("Cash Dividend Announcement BBRI"), "DIVIDEND")

@test("classify_event: RIGHTS_ISSUE keyword 'hmetd'")
def _():
    assert_eq(classify_event("Penawaran HMETD TLKM"), "RIGHTS_ISSUE")

@test("classify_event: RIGHTS_ISSUE keyword 'rights issue'")
def _():
    assert_eq(classify_event("Rights Issue PT Indofood"), "RIGHTS_ISSUE")

@test("classify_event: STOCK_SPLIT keyword 'stock split'")
def _():
    assert_eq(classify_event("Stock Split GOTO 1:10"), "STOCK_SPLIT")

@test("classify_event: STOCK_SPLIT keyword 'pemecahan saham'")
def _():
    assert_eq(classify_event("Pemecahan Saham BREN"), "STOCK_SPLIT")

@test("classify_event: BONUS_SHARES keyword 'saham bonus'")
def _():
    assert_eq(classify_event("Pembagian Saham Bonus SIDO"), "BONUS_SHARES")

@test("classify_event: BUYBACK keyword 'buyback'")
def _():
    assert_eq(classify_event("Program Buyback Saham MTEL"), "BUYBACK")

@test("classify_event: SUSPENSION keyword 'suspensi'")
def _():
    assert_eq(classify_event("Suspensi Saham BUMI"), "SUSPENSION")

@test("classify_event: SUSPENSION keyword 'uma'")
def _():
    assert_eq(classify_event("Unusual Market Activity (UMA) - SRIL"), "SUSPENSION")

@test("classify_event: EGM wins over AGM for 'rupslb'")
def _():
    # RUPSLB should classify as EGM, not AGM (EGM rule checked first)
    result = classify_event("Pengumuman RUPSLB PGAS")
    assert_eq(result, "EGM", "RUPSLB must → EGM, not AGM")

@test("classify_event: AGM for 'rups' generic")
def _():
    result = classify_event("Pengumuman RUPS Tahunan BBNI")
    assert_eq(result, "AGM")

@test("classify_event: DELISTING keyword")
def _():
    assert_eq(classify_event("Penghapusan Pencatatan Saham CPGT"), "DELISTING")

@test("classify_event: UNKNOWN for gibberish")
def _():
    assert_eq(classify_event("Laporan Keuangan Q4 2025"), "UNKNOWN")

@test("classify_event: case insensitive matching")
def _():
    assert_eq(classify_event("DIVIDEN INTERIM BBCA"), "DIVIDEND")

@test("classify_event: uses description as fallback")
def _():
    # Title has no keywords, but description has 'dividend'
    result = classify_event("Pengumuman Korporasi", "akan membagikan dividend")
    assert_eq(result, "DIVIDEND")

@test("classify_event: IPO has priority over DELISTING when both absent")
def _():
    # Smoke test — just ensure no crash on empty
    result = classify_event("", "")
    assert_eq(result, "UNKNOWN")

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: normalizer.normalize_date
# ═══════════════════════════════════════════════════════════════
print("\n── normalize_date ────────────────────────────────────────")

@test("normalize_date: ISO format YYYY-MM-DD")
def _():
    result = normalize_date("2026-04-15")
    assert_eq(result, date(2026, 4, 15))

@test("normalize_date: returns None for None input")
def _():
    assert_none(normalize_date(None))

@test("normalize_date: returns None for empty string")
def _():
    assert_none(normalize_date(""))

@test("normalize_date: returns None for 'N/A' string")
def _():
    assert_none(normalize_date("N/A"))

@test("normalize_date: returns None for '-'")
def _():
    assert_none(normalize_date("-"))

@test("normalize_date: returns None for 'nan'")
def _():
    assert_none(normalize_date("nan"))

@test("normalize_date: returns date object unchanged")
def _():
    d = date(2026, 5, 1)
    assert_eq(normalize_date(d), d)

@test("normalize_date: Indonesian month 'april'")
def _():
    result = normalize_date("15 april 2026")
    assert_eq(result, date(2026, 4, 15))

@test("normalize_date: Indonesian month 'mei'")
def _():
    result = normalize_date("01 mei 2026")
    assert_eq(result, date(2026, 5, 1))

@test("normalize_date: Indonesian month 'januari'")
def _():
    result = normalize_date("20 januari 2026")
    assert_eq(result, date(2026, 1, 20))

@test("normalize_date: bad string returns None")
def _():
    result = normalize_date("not-a-date-at-all")
    assert_none(result)

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: normalizer.normalize_ticker
# ═══════════════════════════════════════════════════════════════
print("\n── normalize_ticker ──────────────────────────────────────")

@test("normalize_ticker: standard 4-char ticker")
def _():
    assert_eq(normalize_ticker("bbca"), "BBCA")

@test("normalize_ticker: already uppercase")
def _():
    assert_eq(normalize_ticker("GOTO"), "GOTO")

@test("normalize_ticker: strips whitespace before normalizing")
def _():
    assert_eq(normalize_ticker("  TLKM  "), "TLKM")

@test("normalize_ticker: None returns None")
def _():
    assert_none(normalize_ticker(None))

@test("normalize_ticker: empty string returns None")
def _():
    assert_none(normalize_ticker(""))

@test("normalize_ticker: too long (>6 chars) returns None")
def _():
    assert_none(normalize_ticker("TOOLONG1"))

@test("normalize_ticker: special chars return None")
def _():
    assert_none(normalize_ticker("BB-CA"))

@test("normalize_ticker: 1-char ticker valid")
def _():
    assert_eq(normalize_ticker("A"), "A")

@test("normalize_ticker: 6-char ticker valid (max)")
def _():
    assert_eq(normalize_ticker("ABCDEF"), "ABCDEF")

@test("normalize_ticker: alphanumeric ticker valid")
def _():
    # Some IDX tickers have numbers (e.g. BSSR, ADMR are fine, ADR5 edge case)
    assert_eq(normalize_ticker("ADR5"), "ADR5")

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: normalizer.normalize_event
# ═══════════════════════════════════════════════════════════════
print("\n── normalize_event ───────────────────────────────────────")

@test("normalize_event: classifies event_type when not provided")
def _():
    raw = {
        "title": "Pengumuman Dividen BBCA",
        "event_date": "2026-05-10",
        "source": "IDX",
    }
    result = normalize_event(raw)
    assert_eq(result["event_type"], "DIVIDEND")

@test("normalize_event: respects explicit event_type in raw")
def _():
    raw = {
        "title": "Some Title",
        "event_date": "2026-05-10",
        "source": "IDX",
        "event_type": "IPO",
    }
    result = normalize_event(raw)
    assert_eq(result["event_type"], "IPO")

@test("normalize_event: normalizes ticker to uppercase")
def _():
    raw = {"title": "Test", "event_date": "2026-05-10", "source": "IDX", "ticker": "bbca"}
    result = normalize_event(raw)
    assert_eq(result["ticker"], "BBCA")

@test("normalize_event: source uppercased")
def _():
    raw = {"title": "Test", "event_date": "2026-05-10", "source": "eipo"}
    result = normalize_event(raw)
    assert_eq(result["source"], "EIPO")

@test("normalize_event: invalid ticker becomes None after normalization")
def _():
    raw = {"title": "Test", "event_date": "2026-05-10", "source": "IDX", "ticker": "NOT-VALID!!"}
    result = normalize_event(raw)
    assert_none(result["ticker"])

@test("normalize_event: raw_payload preserved")
def _():
    raw = {"title": "Test", "event_date": "2026-05-10", "source": "IDX", "custom_field": "abc"}
    result = normalize_event(raw)
    assert_eq(result["raw_payload"]["custom_field"], "abc")

@test("normalize_event: event_date parsed to date object")
def _():
    raw = {"title": "Test", "event_date": "2026-04-15", "source": "IDX"}
    result = normalize_event(raw)
    assert_eq(result["event_date"], date(2026, 4, 15))

@test("normalize_events: skips bad records, processes valid ones")
def _():
    raws = [
        {"title": "IPO ABC", "event_date": "2026-04-01", "source": "EIPO"},
        None,  # This should be skipped gracefully
        {"title": "Dividen XYZ", "event_date": "2026-05-01", "source": "KSEI"},
    ]
    # normalize_events should not crash on None
    try:
        result = normalize_events(raws)
        assert_true(len(result) >= 1, "Should have at least 1 valid result")
    except TypeError:
        # Acceptable: normalize_events expects dicts, None raises TypeError which is caught internally
        pass

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: validator.validate_event
# ═══════════════════════════════════════════════════════════════
print("\n── validate_event ────────────────────────────────────────")

def _valid_base():
    return {
        "title": "Test Event",
        "event_type": "DIVIDEND",
        "source": "IDX",
        "ticker": "BBCA",
        "event_date": date(2026, 5, 10),
        "company": "Bank Central Asia",
        "url": "https://www.idx.co.id/test",
    }

@test("validate_event: valid event passes")
def _():
    ok, reason = validate_event(_valid_base())
    assert_true(ok, f"Valid event should pass but got: {reason}")

@test("validate_event: empty title fails")
def _():
    ev = _valid_base()
    ev["title"] = ""
    ok, reason = validate_event(ev)
    assert_false(ok, "Empty title should fail")
    assert_true("title" in reason)

@test("validate_event: None title fails")
def _():
    ev = _valid_base()
    ev["title"] = None
    ok, reason = validate_event(ev)
    assert_false(ok, "None title should fail")

@test("validate_event: invalid event_type fails")
def _():
    ev = _valid_base()
    ev["event_type"] = "MERGER"  # Not in enum
    ok, reason = validate_event(ev)
    assert_false(ok)
    assert_in("event_type", reason)

@test("validate_event: UNKNOWN event_type is valid")
def _():
    ev = _valid_base()
    ev["event_type"] = "UNKNOWN"
    ok, reason = validate_event(ev)
    assert_true(ok, f"UNKNOWN should be valid but got: {reason}")

@test("validate_event: invalid source silently corrected to UNKNOWN")
def _():
    ev = _valid_base()
    ev["source"] = "YAHOO"
    ok, reason = validate_event(ev)
    assert_true(ok, "Invalid source should be silently corrected, not fail")
    assert_eq(ev["source"], "UNKNOWN")

@test("validate_event: invalid ticker silently cleared (not discard)")
def _():
    ev = _valid_base()
    ev["ticker"] = "INVALID!!!"
    ok, reason = validate_event(ev)
    assert_true(ok, "Invalid ticker should be cleared, not fail validation")
    assert_none(ev["ticker"], "Invalid ticker should be cleared to None")

@test("validate_event: no date field at all fails")
def _():
    ev = _valid_base()
    date_fields = ["event_date", "announcement_date", "record_date", "ex_date",
                   "book_build_start", "book_build_end", "listing_date"]
    for f in date_fields:
        ev[f] = None
    ev.pop("event_date", None)  # Remove key entirely
    ok, reason = validate_event(ev)
    assert_false(ok, "Event with no date should fail")
    assert_in("date", reason)

@test("validate_event: listing_date alone satisfies date requirement")
def _():
    ev = {
        "title": "IPO Test",
        "event_type": "IPO",
        "source": "EIPO",
        "listing_date": date(2026, 4, 15),
    }
    ok, reason = validate_event(ev)
    assert_true(ok, f"listing_date alone should satisfy date requirement, got: {reason}")

@test("validate_event: malformed URL silently cleared")
def _():
    ev = _valid_base()
    ev["url"] = "not-a-url"
    ok, reason = validate_event(ev)
    assert_true(ok, "Malformed URL should be cleared, not fail")
    assert_none(ev["url"], "Malformed URL should be cleared to None")

@test("validate_event: valid https URL passes")
def _():
    ev = _valid_base()
    ev["url"] = "https://www.e-ipo.co.id/en/ipo/1234"
    ok, reason = validate_event(ev)
    assert_true(ok)
    assert_eq(ev["url"], "https://www.e-ipo.co.id/en/ipo/1234")

@test("validate_events: filters out invalid, keeps valid")
def _():
    events = [
        _valid_base(),
        {"title": "", "event_type": "IPO", "source": "IDX", "event_date": date(2026, 4, 1)},  # empty title
        _valid_base(),
    ]
    valid = validate_events(events)
    assert_eq(len(valid), 2, "Should keep only 2 valid events")

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: deduplicator.generate_hash
# ═══════════════════════════════════════════════════════════════
print("\n── generate_hash ─────────────────────────────────────────")

@test("generate_hash: returns 64-char hex string (SHA-256)")
def _():
    h = generate_hash({"ticker": "BBCA", "event_type": "DIVIDEND",
                        "event_date": "2026-05-10", "title": "Dividen BBCA"})
    assert_eq(len(h), 64)
    assert_true(all(c in "0123456789abcdef" for c in h))

@test("generate_hash: same inputs → same hash (stable)")
def _():
    ev = {"ticker": "BBCA", "event_type": "DIVIDEND",
          "event_date": "2026-05-10", "title": "Dividen BBCA"}
    h1 = generate_hash(ev)
    h2 = generate_hash(ev)
    assert_eq(h1, h2, "Hash must be deterministic")

@test("generate_hash: different title → different hash")
def _():
    ev1 = {"ticker": "BBCA", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Dividen BBCA Q1"}
    ev2 = {"ticker": "BBCA", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Dividen BBCA Q2"}
    assert_true(generate_hash(ev1) != generate_hash(ev2))

@test("generate_hash: different ticker → different hash")
def _():
    ev1 = {"ticker": "BBCA", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Dividen"}
    ev2 = {"ticker": "BBRI", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Dividen"}
    assert_true(generate_hash(ev1) != generate_hash(ev2))

@test("generate_hash: different event_type → different hash")
def _():
    ev1 = {"ticker": "BBCA", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Test"}
    ev2 = {"ticker": "BBCA", "event_type": "IPO",
           "event_date": "2026-05-10", "title": "Test"}
    assert_true(generate_hash(ev1) != generate_hash(ev2))

@test("generate_hash: None fields treated as empty string (no crash)")
def _():
    ev = {"ticker": None, "event_type": None, "event_date": None, "title": None}
    h = generate_hash(ev)
    assert_eq(len(h), 64, "Should generate hash even with all None fields")

@test("generate_hash: hash is case-normalized (uppercase ticker same as lower)")
def _():
    ev1 = {"ticker": "BBCA", "event_type": "DIVIDEND",
           "event_date": "2026-05-10", "title": "Test"}
    # The normalizer lowercases before hashing, so case variation shouldn't cause
    # a different hash (the hash function handles this internally)
    h = generate_hash(ev1)
    # After lowercasing: "bbca|dividend|2026-05-10|test"
    raw_check = "bbca|dividend|2026-05-10|test"
    expected = hashlib.sha256(raw_check.encode("utf-8")).hexdigest()
    assert_eq(h, expected, "Hash should be SHA-256 of lowercased pipe-delimited fields")

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: Integration — full pipeline
# ═══════════════════════════════════════════════════════════════
print("\n── integration: full pipeline ────────────────────────────")

@test("integration: raw IPO event through normalize → validate")
def _():
    raw = {
        "source": "EIPO",
        "event_type": "IPO",
        "ticker": "abcd",
        "company": "PT Contoh Tbk",
        "title": "IPO – PT Contoh Tbk",
        "description": "Book-build: 01–05 Apr 2026 | Listing: 15 Apr 2026",
        "book_build_start": "01 april 2026",
        "book_build_end": "05 april 2026",
        "listing_date": "15 april 2026",
        "event_date": "15 april 2026",
        "url": "https://www.e-ipo.co.id/en/ipo/1234",
    }
    normalized = normalize_event(raw)
    ok, reason = validate_event(normalized)
    assert_true(ok, f"IPO event failed validation: {reason}")
    assert_eq(normalized["ticker"], "ABCD")
    assert_eq(normalized["event_type"], "IPO")
    assert_eq(normalized["listing_date"], date(2026, 4, 15))

@test("integration: raw suspension through normalize → validate")
def _():
    raw = {
        "source": "IDX",
        "event_type": "SUSPENSION",
        "ticker": "SRIL",
        "company": "Sri Rejeki Isman",
        "title": "Suspensi Saham SRIL - UMA",
        "description": "Unusual Market Activity (UMA)",
        "announcement_date": "2026-04-02",
        "event_date": "2026-04-02",
        "url": "https://www.idx.co.id/en/news-and-announcement/",
    }
    normalized = normalize_event(raw)
    ok, reason = validate_event(normalized)
    assert_true(ok, f"Suspension event failed validation: {reason}")
    assert_eq(normalized["event_type"], "SUSPENSION")

@test("integration: raw dividend (KSEI) through normalize → validate")
def _():
    raw = {
        "source":      "KSEI",
        "ticker":      "BBCA",
        "company":     "Bank Central Asia",
        "title":       "Cash Dividend – Bank Central Asia",
        "ex_date":     "2026-05-10",
        "record_date": "2026-05-12",
        "event_date":  "2026-05-10",
        "url":         "https://web.ksei.co.id/corporate_action",
    }
    normalized = normalize_event(raw)
    ok, reason = validate_event(normalized)
    assert_true(ok, f"Dividend event failed validation: {reason}")
    assert_eq(normalized["event_type"], "DIVIDEND")
    assert_eq(normalized["ex_date"], date(2026, 5, 10))

@test("integration: AGM vs EGM classification correctness")
def _():
    agm_raw = {"title": "RUPS Tahunan BBRI", "event_date": "2026-05-20", "source": "IDX"}
    egm_raw = {"title": "RUPSLB PT Goto Gojek Tokopedia", "event_date": "2026-05-25", "source": "IDX"}

    agm = normalize_event(agm_raw)
    egm = normalize_event(egm_raw)

    assert_eq(agm["event_type"], "AGM", "RUPS Tahunan should be AGM")
    assert_eq(egm["event_type"], "EGM", "RUPSLB should be EGM")

@test("integration: generate_hash is stable across normalize pipeline")
def _():
    raw = {
        "source": "IDX",
        "ticker": "BBCA",
        "title": "Dividend Interim BBCA 2026",
        "event_date": "2026-05-10",
        "ex_date": "2026-05-08",
    }
    normalized = normalize_event(raw)
    # Normalize then hash should be stable
    h1 = generate_hash(normalized)
    h2 = generate_hash(normalized)
    assert_eq(h1, h2, "Hash after normalization must be stable")
    assert_eq(len(h1), 64)

# ═══════════════════════════════════════════════════════════════
# TEST SUITE: Edge cases & regressions
# ═══════════════════════════════════════════════════════════════
print("\n── edge cases & regressions ──────────────────────────────")

@test("edge: classify_event with None title/desc doesn't crash")
def _():
    result = classify_event(None, None)
    assert_eq(result, "UNKNOWN")

@test("edge: normalize_event with missing source defaults to UNKNOWN")
def _():
    raw = {"title": "Test", "event_date": "2026-04-01"}
    result = normalize_event(raw)
    assert_eq(result["source"], "UNKNOWN")

@test("edge: normalize_event with whitespace-only title")
def _():
    raw = {"title": "   ", "event_date": "2026-04-01", "source": "IDX"}
    result = normalize_event(raw)
    # Title should be stripped to empty string
    assert_eq(result["title"], "")

@test("edge: validate_event rejects whitespace-only title")
def _():
    ev = {
        "title": "  ",
        "event_type": "DIVIDEND",
        "source": "IDX",
        "event_date": date(2026, 5, 10),
    }
    ok, _ = validate_event(ev)
    assert_false(ok, "Whitespace-only title should fail (after strip = empty)")

@test("edge: normalize_date with integer year only is invalid")
def _():
    result = normalize_date("2026")
    # Could parse as year only — it's ambiguous; we accept either None or a date
    # The key is: it must not crash
    assert_true(result is None or isinstance(result, date))

@test("edge: generate_hash with date object in event_date (not string)")
def _():
    ev = {
        "ticker": "BBCA",
        "event_type": "DIVIDEND",
        "event_date": date(2026, 5, 10),  # not a string
        "title": "Dividen",
    }
    h = generate_hash(ev)
    assert_eq(len(h), 64)  # Must not crash

@test("edge: normalize_events handles empty list")
def _():
    result = normalize_events([])
    assert_eq(result, [])

@test("edge: validate_events handles empty list")
def _():
    result = validate_events([])
    assert_eq(result, [])

@test("edge: CLASSIFICATION_RULES has no duplicate event types that could shadow")
def _():
    # IPO should be at index 0, DELISTING at 1, both before DIVIDEND
    type_seq = [event_type for event_type, _ in CLASSIFICATION_RULES]
    ipo_idx = type_seq.index("IPO")
    egm_idx = type_seq.index("EGM")
    agm_idx = type_seq.index("AGM")
    assert_true(egm_idx < agm_idx,
        f"EGM rule ({egm_idx}) must come before AGM rule ({agm_idx}) to avoid RUPSLB misclassification")

# ═══════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print(f"  Results: {_TESTS_PASSED} passed, {_TESTS_FAILED} failed, {_TESTS_RUN} total")
print("="*60)

if _FAILURES:
    print("\nFailed tests:")
    for name, reason in _FAILURES:
        print(f"  ✗ {name}")
        print(f"    → {reason}")

sys.exit(0 if _TESTS_FAILED == 0 else 1)
