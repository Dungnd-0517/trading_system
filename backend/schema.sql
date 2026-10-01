CREATE TABLE IF NOT EXISTS market_candles (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    timeframe VARCHAR(8) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume NUMERIC(16, 2) NOT NULL,
    UNIQUE (symbol, timeframe, open_time)
);

CREATE TABLE IF NOT EXISTS financial_news (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    impact_level VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    sentiment_score NUMERIC(4, 2),
    ai_analysis_summary TEXT,
    external_id VARCHAR(128),
    dedupe_key CHAR(64),
    content_hash CHAR(64),
    revision_no INT NOT NULL DEFAULT 1 CHECK (revision_no >= 1),
    last_seen_at TIMESTAMPTZ,
    source_url TEXT,
    impact_stars SMALLINT CHECK (impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3),
    classification_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (
            (classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL)
            OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)
        ),
    keywords_matched TEXT[],
    CHECK (sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_news_source_external_id
    ON financial_news(source, external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_news_dedupe_key
    ON financial_news(dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS economic_events (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    external_id VARCHAR(128),
    dedupe_key CHAR(64),
    title TEXT NOT NULL,
    description TEXT,
    provider_time_raw TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ,
    timezone_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    previous_value VARCHAR(32),
    forecast_value VARCHAR(32),
    actual_value VARCHAR(32),
    impact_stars SMALLINT CHECK (impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3),
    classification_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (
            (classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL)
            OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)
        ),
    keywords_matched TEXT[],
    content_hash CHAR(64),
    revision_no INT NOT NULL DEFAULT 1 CHECK (revision_no >= 1),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (timezone_status = 'VERIFIED' AND event_timestamp IS NOT NULL)
        OR (timezone_status = 'UNKNOWN' AND event_timestamp IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_economic_events_time ON economic_events(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_economic_events_stars ON economic_events(impact_stars);
CREATE UNIQUE INDEX IF NOT EXISTS uq_economic_events_source_external_id
    ON economic_events(source, external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_economic_events_dedupe_key
    ON economic_events(dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS economic_event_revisions (
    id BIGSERIAL PRIMARY KEY,
    economic_event_id BIGINT NOT NULL REFERENCES economic_events(id) ON DELETE CASCADE,
    revision_no INT NOT NULL CHECK (revision_no >= 1),
    snapshot JSONB NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (economic_event_id, revision_no)
);

CREATE TABLE IF NOT EXISTS simulated_orders (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    order_type VARCHAR(8) NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    status VARCHAR(16) NOT NULL CHECK (status IN ('PENDING', 'FILLED', 'CANCELLED', 'CLOSED')),
    lot_size NUMERIC(8, 2) NOT NULL CHECK (lot_size > 0),
    entry_price NUMERIC(12, 4) NOT NULL,
    exit_price NUMERIC(12, 4),
    stop_loss NUMERIC(12, 4) NOT NULL,
    take_profit NUMERIC(12, 4) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    close_time TIMESTAMPTZ,
    realized_pnl NUMERIC(12, 2),
    pnl_percentage NUMERIC(6, 2),
    strategy_trigger VARCHAR(64),
    ai_market_context_id BIGINT REFERENCES financial_news(id)
);

CREATE TABLE IF NOT EXISTS simulation_metrics (
    date DATE PRIMARY KEY,
    total_trades INT NOT NULL DEFAULT 0,
    win_trades INT NOT NULL DEFAULT 0,
    loss_trades INT NOT NULL DEFAULT 0,
    winrate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(6, 2) NOT NULL DEFAULT 0,
    total_pnl NUMERIC(12, 2) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(5, 2) NOT NULL DEFAULT 0
);