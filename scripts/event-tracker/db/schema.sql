-- ============================================================
-- IDX Market Event Tracker — PostgreSQL Schema
-- Version: 0.2.0
-- Run: psql -U <user> -d <db> -f schema.sql
-- ============================================================

-- ── Extensions ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Enum: Event Types ───────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE event_type_enum AS ENUM (
        'IPO',
        'DIVIDEND',
        'RIGHTS_ISSUE',
        'STOCK_SPLIT',
        'BONUS_SHARES',
        'BUYBACK',
        'PRIVATE_PLACEMENT',
        'SUSPENSION',
        'AGM',
        'EGM',
        'DELISTING',
        'UNKNOWN'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ── Enum: Event Source ──────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE event_source_enum AS ENUM (
        'IDX',
        'EIPO',
        'KSEI',
        'UNKNOWN'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ── Table: market_events ────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_events (
    -- Identity
    event_id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    event_type          event_type_enum NOT NULL DEFAULT 'UNKNOWN',
    source              event_source_enum NOT NULL DEFAULT 'UNKNOWN',

    -- Company info
    ticker              VARCHAR(10),
    company             VARCHAR(255),

    -- Event details
    title               TEXT            NOT NULL,
    description         TEXT,

    -- Key dates
    event_date          DATE,             -- Primary date (listing date, RUPS date, etc.)
    announcement_date   DATE,             -- Date of IDX/KSEI announcement
    record_date         DATE,             -- Record date (dividend, rights issue)
    ex_date             DATE,             -- Ex-date (dividend, rights issue)
    book_build_start    DATE,             -- IPO: start of bookbuilding
    book_build_end      DATE,             -- IPO: end of bookbuilding
    listing_date        DATE,             -- IPO: listing date on IDX

    -- Source link
    url                 TEXT,

    -- Deduplication
    hash                VARCHAR(64)     UNIQUE NOT NULL, -- SHA-256 of (ticker + event_type + event_date + title)

    -- Metadata
    raw_payload         JSONB,           -- Original scraped raw data
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_market_events_ticker
    ON market_events (ticker);

CREATE INDEX IF NOT EXISTS idx_market_events_event_date
    ON market_events (event_date);

CREATE INDEX IF NOT EXISTS idx_market_events_event_type
    ON market_events (event_type);

CREATE INDEX IF NOT EXISTS idx_market_events_created_at
    ON market_events (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_events_source
    ON market_events (source);

-- Composite: fast lookup for IPO calendar queries
CREATE INDEX IF NOT EXISTS idx_market_events_ipo_calendar
    ON market_events (event_type, listing_date)
    WHERE event_type = 'IPO';

-- Composite: fast lookup for corporate action queries
CREATE INDEX IF NOT EXISTS idx_market_events_corp_action
    ON market_events (event_type, ex_date)
    WHERE event_type IN ('DIVIDEND', 'RIGHTS_ISSUE', 'STOCK_SPLIT', 'BONUS_SHARES');

-- ── Trigger: auto-update updated_at ─────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_market_events_updated_at ON market_events;
CREATE TRIGGER trg_market_events_updated_at
    BEFORE UPDATE ON market_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── View: upcoming IPO calendar (next 30 days) ───────────────
CREATE OR REPLACE VIEW v_upcoming_ipo AS
SELECT
    ticker,
    company,
    book_build_start,
    book_build_end,
    listing_date,
    url,
    source,
    created_at
FROM market_events
WHERE
    event_type = 'IPO'
    AND listing_date >= CURRENT_DATE
    AND listing_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY listing_date ASC;

-- ── View: upcoming corporate actions (next 30 days) ──────────
CREATE OR REPLACE VIEW v_upcoming_corporate_actions AS
SELECT
    event_type,
    ticker,
    company,
    title,
    description,
    event_date,
    record_date,
    ex_date,
    url,
    source,
    created_at
FROM market_events
WHERE
    event_type IN ('DIVIDEND', 'RIGHTS_ISSUE', 'STOCK_SPLIT', 'BONUS_SHARES', 'BUYBACK', 'PRIVATE_PLACEMENT')
    AND event_date >= CURRENT_DATE
    AND event_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY event_date ASC;

-- ── View: active suspensions ─────────────────────────────────
CREATE OR REPLACE VIEW v_active_suspensions AS
SELECT
    ticker,
    company,
    title,
    description,
    event_date,
    url,
    source,
    created_at
FROM market_events
WHERE
    event_type = 'SUSPENSION'
    AND event_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY event_date DESC;

-- ── View: upcoming RUPS/AGM/EGM ─────────────────────────────
CREATE OR REPLACE VIEW v_upcoming_meetings AS
SELECT
    event_type,
    ticker,
    company,
    title,
    event_date,
    url,
    source,
    created_at
FROM market_events
WHERE
    event_type IN ('AGM', 'EGM')
    AND event_date >= CURRENT_DATE
    AND event_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY event_date ASC;

-- ── Grant (adjust roles as needed) ──────────────────────────
-- GRANT SELECT, INSERT, UPDATE ON market_events TO n8n;
-- GRANT SELECT ON v_upcoming_ipo TO n8n;
-- GRANT SELECT ON v_upcoming_corporate_actions TO n8n;
-- GRANT SELECT ON v_active_suspensions TO n8n;
-- GRANT SELECT ON v_upcoming_meetings TO n8n;
