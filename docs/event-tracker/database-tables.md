# Database Table Documentation

## Scope

This document describes the custom PostgreSQL tables defined in this repository for the event-tracker feature.

Schema sources reviewed:

- `scripts/event-tracker/db/schema.sql`: current event-tracker schema used by the Flask API and deduplication pipeline.
- `schema.sql`: older bootstrap schema that still defines additional tables not used by the current Flask service.

This project also uses PostgreSQL for n8n, but n8n system tables are created by n8n itself and are not documented here because they are not declared in this repository.

## Table Summary

| Table | Status | Primary role | Main use case |
|---|---|---|---|
| `market_events` | Active | Stores normalized market event records | Serve event APIs, alerting, and event history |
| `pipeline_runs` | Legacy/bootstrap | Stores pipeline execution metrics | Audit or monitor scraper run quality |
| `event_classifications` | Legacy/bootstrap | Stores title classification results | Analyze or improve keyword-based classification |

## 1. `market_events`

### Purpose

`market_events` is the core business table of the event-tracker subsystem. It stores normalized market event data collected from IDX, e-IPO, and KSEI sources.

The table is designed to support:

- event ingestion from multiple scrapers
- normalization into one common schema
- validation before storage
- deduplication across repeated runs
- downstream API queries for alerting and reporting

### How the application uses it

Writers:

- `scripts/event-tracker/pipeline/deduplicator.py`
- legacy helper in `scripts/event-tracker/database.py`

Readers:

- `scripts/event-tracker/main.py`
- database views defined in `scripts/event-tracker/db/schema.sql`

Typical workflow:

1. Scrapers collect raw announcements.
2. `normalizer.py` maps them into a canonical event structure.
3. `validator.py` checks required fields, enums, dates, ticker format, and URL format.
4. `deduplicator.py` generates a SHA-256 `hash` and inserts into `market_events`.
5. API endpoints query this table directly or through views such as `v_upcoming_ipo`.

### Functional role

This table acts as:

- the source of truth for market event history
- the alert queue source for newly inserted events
- the calendar source for IPOs, meetings, and corporate actions
- the deduplication boundary for repeated scrape runs
- the audit container for raw scraped payloads

### Main use cases

- Show new events from the last few hours through `GET /events/new`
- Show upcoming IPOs through `GET /events/ipo`
- Show upcoming corporate actions through `GET /events/corporate-actions`
- Show recent suspensions through `GET /events/suspensions`
- Show upcoming AGM or EGM events through `GET /events/meetings`
- Run filtered searches by ticker or event type through `GET /events`
- Retain original source payload for debugging parser or normalization issues

### Column reference

| Column | Type | Functionality | Example use case |
|---|---|---|---|
| `event_id` | `UUID` | Primary key for each stored event row | Safely reference one event from an API response |
| `event_type` | `event_type_enum` | Normalized business category such as `IPO`, `DIVIDEND`, `AGM`, or `SUSPENSION` | Filter only dividend or IPO records |
| `source` | `event_source_enum` | Identifies origin system such as `IDX`, `EIPO`, or `KSEI` | Compare data quality by source |
| `ticker` | `VARCHAR(10)` | Stock code if available | Query all events for `BBCA` |
| `company` | `VARCHAR(255)` | Company name when scraper can extract it | Build user-facing Telegram messages |
| `title` | `TEXT` | Main announcement title, required for every record | Present the event headline in APIs and alerts |
| `description` | `TEXT` | Additional event details or parsed summary text | Show more context for corporate actions |
| `event_date` | `DATE` | Primary business date for the event | Sort upcoming meetings or suspensions |
| `announcement_date` | `DATE` | Date the source published or announced the item | Track announcement timing separately from event timing |
| `record_date` | `DATE` | Record date for events like dividends or rights issues | Determine shareholder eligibility deadlines |
| `ex_date` | `DATE` | Ex-date for relevant corporate actions | Build dividend and rights calendars |
| `book_build_start` | `DATE` | IPO book-building start date | Show IPO subscription windows |
| `book_build_end` | `DATE` | IPO book-building end date | Show when the IPO order window closes |
| `listing_date` | `DATE` | IPO listing date on IDX | Build the IPO listing calendar |
| `url` | `TEXT` | Link to the source announcement | Let users drill into the original disclosure |
| `hash` | `VARCHAR(64)` | Unique SHA-256 deduplication key | Prevent duplicate inserts when the scraper reruns |
| `raw_payload` | `JSONB` | Original scraper output before or during normalization | Debug parser mismatches without re-scraping |
| `created_at` | `TIMESTAMPTZ` | Insert timestamp | Find newly inserted events for alert delivery |
| `updated_at` | `TIMESTAMPTZ` | Last update timestamp, managed by trigger | Track when a row was last changed |

### Constraints and behavior

- `event_type` is limited to known enum values.
- `source` is limited to known enum values.
- `hash` must be unique and is the main duplicate-prevention mechanism.
- `updated_at` is refreshed automatically by the `trg_market_events_updated_at` trigger.
- Validation logic rejects rows with no meaningful date or no title before insert.
- Invalid source, ticker, or URL values may be corrected or cleared during validation instead of causing a hard failure.

### Indexes

| Index | Why it exists | Helps which use case |
|---|---|---|
| `idx_market_events_ticker` | Fast lookup by stock code | Event history per ticker |
| `idx_market_events_event_date` | Fast ordering and filtering by main event date | Upcoming event calendars |
| `idx_market_events_event_type` | Fast filtering by event category | API queries by event type |
| `idx_market_events_created_at` | Fast retrieval of newest rows | `/events/new` alerting flow |
| `idx_market_events_source` | Fast filtering by source | Source-level analysis |
| `idx_market_events_ipo_calendar` | Optimized lookup for IPO rows by listing date | `/events/ipo` |
| `idx_market_events_corp_action` | Optimized lookup for corporate actions by ex-date | Corporate action calendar |

### Data lifecycle

- Inserted by the deduplication pipeline after validation.
- Queried repeatedly by the Flask API and n8n automations.
- Safe to reprocess because duplicates are skipped using `ON CONFLICT (hash) DO NOTHING`.

## 2. `pipeline_runs`

### Status

Legacy/bootstrap table. It exists in the root `schema.sql` and is referenced by the older helper `scripts/event-tracker/database.py`, but it is not used by the current Flask event-tracker pipeline in `scripts/event-tracker/main.py`.

### Purpose

`pipeline_runs` is intended to store one summary row per pipeline execution. It is an operational monitoring table rather than a business data table.

### Functional role

This table is meant to answer questions such as:

- How many raw events were collected in a run?
- How many events survived normalization and validation?
- How many were dropped as duplicates?
- Did the run finish successfully, partially, or fail?
- How long did the run take?

### Main use cases

- Build a simple pipeline health dashboard
- Investigate sudden drops in collected event volume
- Track repeated failures in scraper jobs
- Compare run durations over time

### Column reference

| Column | Type | Functionality | Example use case |
|---|---|---|---|
| `id` | `SERIAL` | Primary key for the run log row | Reference a specific execution summary |
| `run_timestamp` | `TIMESTAMP` | When the pipeline run was logged | Review runs by time |
| `total_collected` | `INT` | Count of raw events scraped | Detect scraper outages |
| `total_normalized` | `INT` | Count after normalization | Measure normalization coverage |
| `total_validated` | `INT` | Count after validation | Spot validation-related drop-off |
| `total_deduplicated` | `INT` | Count after duplicate filtering | Measure fresh vs repeated data |
| `errors_count` | `INT` | Number of errors in the run | Identify unstable runs |
| `warnings_count` | `INT` | Number of warnings in the run | Monitor soft data quality issues |
| `execution_time_ms` | `INT` | Runtime in milliseconds | Watch for performance regressions |
| `status` | `VARCHAR(50)` | Run result such as `SUCCESS`, `PARTIAL`, or `FAILED` | Power a run-status dashboard |

### Notes

- Good fit if the team wants historical observability for the event pipeline.
- Currently appears to be a planned or older design, not an actively queried table.

## 3. `event_classifications`

### Status

Legacy/bootstrap table. It exists in the root `schema.sql` but is not used by the current Flask event-tracker runtime.

### Purpose

`event_classifications` is intended to store classification results for raw announcement titles, probably to support keyword-based categorization analysis.

### Functional role

This table would be useful for:

- recording how a raw title was classified
- storing matched keywords for auditability
- keeping confidence scores for tuning the classifier
- reviewing false positives and false negatives

### Main use cases

- Analyze whether the title classifier is assigning the correct event type
- Improve keyword dictionaries over time
- Build a manual review queue for low-confidence classifications
- Compare classification confidence across different sources

### Column reference

| Column | Type | Functionality | Example use case |
|---|---|---|---|
| `id` | `SERIAL` | Primary key for each classification record | Track one classification decision |
| `raw_title` | `TEXT` | Original title before classification | Review ambiguous source headlines |
| `matched_keywords` | `TEXT` | Keywords that caused the category match | Explain why a title became `DIVIDEND` |
| `classified_type` | `VARCHAR(50)` | Resulting event category | Evaluate classification output distribution |
| `confidence_score` | `DECIMAL(3,2)` | Confidence estimate for the assigned type | Flag low-confidence rows for manual review |
| `created_at` | `TIMESTAMP` | When the classification row was stored | Audit classifier behavior over time |

### Notes

- Useful for analytics and model-rule improvement.
- Not currently connected to the production event-tracker API flow.

## Related Database Views

These are not tables, but they are important because the active API uses them directly.

| View | Built from | Purpose | Used by |
|---|---|---|---|
| `v_upcoming_ipo` | `market_events` | IPO calendar for the next 30 days | `GET /events/ipo` |
| `v_upcoming_corporate_actions` | `market_events` | Upcoming dividends, rights issues, splits, bonus shares, buybacks, and private placements | `GET /events/corporate-actions` |
| `v_active_suspensions` | `market_events` | Suspensions from the last 7 days | `GET /events/suspensions` |
| `v_upcoming_meetings` | `market_events` | Upcoming AGM and EGM events | `GET /events/meetings` |

## Implementation Notes

- The repository currently contains two schema versions with different maturity levels.
- The current Flask event-tracker code aligns with `scripts/event-tracker/db/schema.sql`.
- The root-level `schema.sql` includes extra monitoring and classification tables that are not wired into the active Flask service.
- If the team wants one canonical schema, the next cleanup step should be to decide whether `pipeline_runs` and `event_classifications` are still needed and then either migrate them into the active schema or remove the older definition.
