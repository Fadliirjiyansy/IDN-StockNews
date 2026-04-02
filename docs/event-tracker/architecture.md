# IDX Event Tracker — Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n Automation Layer                        │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ Schedule    │  │ HTTP Request    │  │ HTTP Request     │   │
│  │ Trigger     │→ │ POST /run       │→ │ GET /events/new  │   │
│  │ (every 6h)  │  │ (trigger scrape)│  │ (fetch alerts)   │   │
│  └─────────────┘  └─────────────────┘  └────────┬─────────┘   │
│                                                  │             │
│  ┌───────────────────────────────────────────────▼──────────┐  │
│  │  IF: Has New Events?                                     │  │
│  │  ├─ YES → Split Events → Format Alert → Telegram Send   │  │
│  │  └─ NO  → NoOp (silent pass)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────┘
                                       │ HTTP (internal Docker network)
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Python Event Tracker Service (Flask)               │
│                    http://event-tracker:5055                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. SCRAPER LAYER                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ IDXIPOScraper│  │CorpActions  │  │Suspensions   │  │  │
│  │  │ (e-ipo.co.id │  │ Scraper     │  │ Scraper      │  │  │
│  │  │  + IDX API)  │  │(KSEI + IDX) │  │ (IDX API)    │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  │         │                 │                  │          │  │
│  │         └─────────────────┴───────────┬──────┘          │  │
│  │                                       ▼                  │  │
│  │  ┌─────────────────────────────────────────────────┐    │  │
│  │  │  MeetingsScraper (IDX announcements — RUPS)     │    │  │
│  │  └────────────────────────┬────────────────────────┘    │  │
│  │                           ▼                              │  │
│  │  2. NORMALIZATION LAYER                                  │  │
│  │  ┌────────────────────────────────────────────────┐     │  │
│  │  │  normalizer.py                                  │     │  │
│  │  │  • Keyword-based event_type classification     │     │  │
│  │  │  • Indonesian date parsing (Bahasa month names) │     │  │
│  │  │  • Ticker normalization (uppercase, 1–6 chars) │     │  │
│  │  │  • Canonical field mapping                     │     │  │
│  │  └────────────────────────┬───────────────────────┘     │  │
│  │                           ▼                              │  │
│  │  3. VALIDATION LAYER                                     │  │
│  │  ┌────────────────────────────────────────────────┐     │  │
│  │  │  validator.py                                   │     │  │
│  │  │  • Required field checks (title, event_type)   │     │  │
│  │  │  • Enum validation (event_type, source)        │     │  │
│  │  │  • Date presence validation                    │     │  │
│  │  │  • URL format validation                       │     │  │
│  │  └────────────────────────┬───────────────────────┘     │  │
│  │                           ▼                              │  │
│  │  4. DEDUPLICATION + STORAGE LAYER                        │  │
│  │  ┌────────────────────────────────────────────────┐     │  │
│  │  │  deduplicator.py                                │     │  │
│  │  │  • SHA-256 hash (ticker+type+date+title)       │     │  │
│  │  │  • INSERT ... ON CONFLICT (hash) DO NOTHING    │     │  │
│  │  │  • Batched commits (50 rows/batch)             │     │  │
│  │  └────────────────────────┬───────────────────────┘     │  │
│  └──────────────────────────┼───────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │ psycopg2
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PostgreSQL — market_events table                │
│                                                                 │
│  Indexes: ticker, event_date, event_type, created_at           │
│  Views: v_upcoming_ipo, v_upcoming_corporate_actions,          │
│         v_active_suspensions, v_upcoming_meetings              │
│                                                                 │
│  UNIQUE constraint on: hash (SHA-256 dedup key)               │
└─────────────────────────────────────────────────────────────────┘
```

## Event Flow

```
Schedule (6h)
      │
      ▼
POST /run ──► Scrape ──► Normalize ──► Validate ──► Deduplicate ──► DB
      │
      ▼
GET /events/new ──► Filter new events (last 7h) ──► n8n
      │
      ▼
Per event ──► Format alert by event_type ──► Telegram
```

## Resilience Map

| Layer | Mechanism | Why |
|---|---|---|
| HTTP scraping | tenacity (3 retries, exp. backoff 2–30s) | IDX/KSEI servers occasionally time out |
| HTTP scraping | 30s timeout per request | Prevents hung connections |
| HTTP scraping | Random UA rotation | Avoids bot detection on IDX/KSEI |
| HTML parsing | lxml → html.parser fallback | IDX pages sometimes serve malformed HTML |
| Scraper | In-memory URL dedup before DB | Avoids hammering DB with known duplicates |
| Pipeline | Per-event exception handling | One bad record doesn't drop the batch |
| Storage | `ON CONFLICT DO NOTHING` | Idempotent — safe to re-run after failure |
| Storage | Batch commits (50 rows) | Limits transaction size on large runs |
| Validation | Discard vs. correct strategy | Minor issues silently fixed; fatal issues logged + discarded |

## Data Model

```
market_events
├── event_id          UUID PK
├── event_type        ENUM (IPO, DIVIDEND, RIGHTS_ISSUE, ...)
├── source            ENUM (IDX, EIPO, KSEI)
├── ticker            VARCHAR(10)
├── company           VARCHAR(255)
├── title             TEXT
├── description       TEXT
├── event_date        DATE
├── announcement_date DATE
├── record_date       DATE
├── ex_date           DATE
├── book_build_start  DATE   ← IPO only
├── book_build_end    DATE   ← IPO only
├── listing_date      DATE   ← IPO only
├── url               TEXT
├── hash              VARCHAR(64) UNIQUE  ← dedup key
├── raw_payload       JSONB
├── created_at        TIMESTAMPTZ
└── updated_at        TIMESTAMPTZ
```

## Telegram Alert Templates

### IPO
```
📈 Upcoming IPO
Company      : PT Contoh Tbk
Ticker       : ABCD
Book-Build   : 01 Apr 2026 – 05 Apr 2026
Listing Date : 15 Apr 2026

[IDX/e-IPO](https://www.e-ipo.co.id/...)
```

### Dividend
```
💰 Dividend Announcement
Ticker      : BBCA
Company     : Bank Central Asia
Ex-Date     : 10 May 2026
Record Date : 12 May 2026
Detail      : Rp 250/share

[Detail](https://www.idx.co.id/...)
```

### Suspension
```
⚠️ Trading Suspension
Ticker  : XYZ
Company : PT XYZ Tbk
Tanggal : 02 Apr 2026
Alasan  : Unusual Market Activity (UMA)

[Pengumuman](https://www.idx.co.id/...)
```

### AGM/RUPS
```
🏛 RUPS Tahunan (AGM)
Ticker  : BBRI
Company : Bank Rakyat Indonesia
Tanggal : 20 May 2026

[Pengumuman](https://www.idx.co.id/...)
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health + DB connectivity |
| POST | `/run` | Trigger full scrape → store pipeline |
| GET | `/events/new?hours=7` | New events (for n8n alerting) |
| GET | `/events/ipo` | Upcoming IPO calendar (30 days) |
| GET | `/events/corporate-actions` | Corporate actions (30 days) |
| GET | `/events/suspensions` | Active suspensions (7 days) |
| GET | `/events/meetings` | Upcoming AGM/EGM (30 days) |
| GET | `/events?type=IPO&ticker=BBCA` | Generic event query |

## File Structure

```
scripts/event-tracker/
├── main.py                          ← Flask API entry point
├── config.py                        ← Config from env vars
├── requirements.txt
├── scrapers/
│   ├── __init__.py
│   ├── base.py                      ← Base class (retry, UA, HTML parsing)
│   ├── idx_ipo.py                   ← e-ipo.co.id + IDX new listings
│   ├── idx_corporate_actions.py     ← KSEI + IDX announcements
│   ├── idx_suspensions.py           ← IDX announcements (suspend keywords)
│   └── idx_meetings.py              ← IDX announcements (RUPS/AGM/EGM)
├── pipeline/
│   ├── __init__.py
│   ├── normalizer.py                ← Keyword classification + field mapping
│   ├── validator.py                 ← Field validation + discard logic
│   └── deduplicator.py             ← SHA-256 hash + PostgreSQL upsert
└── db/
    └── schema.sql                   ← Full PostgreSQL schema + views
```

## Integration Notes

- The event tracker service runs as a Docker container (`event-tracker`) on the same network as n8n and PostgreSQL.
- n8n workflow `workflow-0.2.0.json` calls the API via `http://event-tracker:5055`.
- The morning briefing formatter (`workflow-0.1.0`) shows IPO calendar as a **static placeholder** until workflow-0.2.0 is active, at which point the `Format Telegram Message` Code node should fetch live IPO data from `GET /events/ipo` and inject it dynamically.
