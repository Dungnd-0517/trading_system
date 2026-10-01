ALTER TABLE financial_news
    ADD COLUMN IF NOT EXISTS external_id VARCHAR(128),
    ADD COLUMN IF NOT EXISTS dedupe_key CHAR(64),
    ADD COLUMN IF NOT EXISTS content_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS revision_no INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS impact_stars SMALLINT,
    ADD COLUMN IF NOT EXISTS classification_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN IF NOT EXISTS keywords_matched TEXT[];

ALTER TABLE financial_news
    DROP CONSTRAINT IF EXISTS ck_financial_news_impact_stars,
    DROP CONSTRAINT IF EXISTS ck_financial_news_classification,
    DROP CONSTRAINT IF EXISTS ck_financial_news_revision_no;

ALTER TABLE financial_news
    ADD CONSTRAINT ck_financial_news_impact_stars
        CHECK (impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3),
    ADD CONSTRAINT ck_financial_news_classification
        CHECK (
            (classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL)
            OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)
        ),
    ADD CONSTRAINT ck_financial_news_revision_no CHECK (revision_no >= 1);

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
    impact_stars SMALLINT,
    classification_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    keywords_matched TEXT[],
    content_hash CHAR(64),
    revision_no INT NOT NULL DEFAULT 1,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_economic_events_impact_stars
        CHECK (impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3),
    CONSTRAINT ck_economic_events_classification
        CHECK (
            (classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL)
            OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)
        ),
    CONSTRAINT ck_economic_events_timezone
        CHECK (
            (timezone_status = 'VERIFIED' AND event_timestamp IS NOT NULL)
            OR (timezone_status = 'UNKNOWN' AND event_timestamp IS NULL)
        ),
    CONSTRAINT ck_economic_events_revision_no CHECK (revision_no >= 1)
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