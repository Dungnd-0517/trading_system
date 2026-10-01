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
    CHECK (sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1)
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