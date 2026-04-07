-- PostgreSQL Database Schema for FinancialReportNews
-- Initialize tables and indexes

CREATE TABLE IF NOT EXISTS market_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ticker VARCHAR(10),
    source VARCHAR(50) NOT NULL,
    announcement_date DATE,
    event_date DATE,
    record_date DATE,
    ex_date DATE,
    url TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'IPO', 'DIVIDEND', 'RIGHTS_ISSUE', 'STOCK_SPLIT',
            'BONUS_SHARES', 'BUYBACK', 'PRIVATE_PLACEMENT',
            'SUSPENSION', 'AGM', 'EGM', 'DELISTING', 'UNKNOWN'
        )
    ),
    
    CONSTRAINT valid_source CHECK (
        source IN ('IDX', 'EIPO', 'KSEI', 'UNKNOWN')
    ),
    
    CONSTRAINT valid_ticker CHECK (
        ticker IS NULL OR ticker ~ '^[A-Z0-9]{1,6}$'
    )
);

CREATE INDEX idx_market_events_lookup 
    ON market_events(ticker, event_type, announcement_date);

CREATE INDEX idx_market_events_date 
    ON market_events(announcement_date DESC);

CREATE INDEX idx_market_events_type 
    ON market_events(event_type);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    total_collected INT DEFAULT 0,
    total_normalized INT DEFAULT 0,
    total_validated INT DEFAULT 0,
    total_deduplicated INT DEFAULT 0,
    
    errors_count INT DEFAULT 0,
    warnings_count INT DEFAULT 0,
    
    execution_time_ms INT,
    status VARCHAR(50),
    
    CONSTRAINT valid_status CHECK (status IN ('SUCCESS', 'PARTIAL', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS event_classifications (
    id SERIAL PRIMARY KEY,
    raw_title TEXT NOT NULL,
    matched_keywords TEXT,
    classified_type VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_classifications_type 
    ON event_classifications(classified_type);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO n8n;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO n8n;

-- Initial data insert test
INSERT INTO market_events 
    (title, event_type, ticker, source, announcement_date)
VALUES 
    ('Initial setup test', 'UNKNOWN', NULL, 'UNKNOWN', CURRENT_DATE)
ON CONFLICT DO NOTHING;

-- Verify schema creation
SELECT 'market_events' as table_name, COUNT(*) as row_count FROM market_events
UNION ALL
SELECT 'pipeline_runs', COUNT(*) FROM pipeline_runs
UNION ALL
SELECT 'event_classifications', COUNT(*) FROM event_classifications;
