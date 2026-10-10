-- Migration: backend/migrations/0004_phase2_sprint3.sql

-- 1. Bảng lưu trữ cấu hình giao dịch hệ thống
CREATE TABLE IF NOT EXISTS system_trading_config (
    id INT PRIMARY KEY DEFAULT 1,
    execution_mode VARCHAR(16) NOT NULL DEFAULT 'MANUAL',
    risk_per_trade_percent NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
    breakeven_r_multiple NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    enable_partial_tp BOOLEAN NOT NULL DEFAULT TRUE,
    partial_tp_ratio NUMERIC(4, 2) NOT NULL DEFAULT 0.50,
    partial_tp_r_multiple NUMERIC(4, 2) NOT NULL DEFAULT 2.00,
    news_circuit_breaker_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    news_circuit_breaker_buffer_mins INT NOT NULL DEFAULT 30,
    max_open_positions INT NOT NULL DEFAULT 2,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO system_trading_config (id, execution_mode)
VALUES (1, 'MANUAL')
ON CONFLICT (id) DO NOTHING;

-- 2. Bảng lưu trữ tín hiệu giao dịch SMC tự động
CREATE TABLE IF NOT EXISTS strategy_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    side VARCHAR(8) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    session_name VARCHAR(64) NOT NULL,
    entry_price NUMERIC(12, 4) NOT NULL,
    stop_loss NUMERIC(12, 4) NOT NULL,
    take_profit_1 NUMERIC(12, 4) NOT NULL,
    take_profit_2 NUMERIC(12, 4),
    risk_reward NUMERIC(6, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    invalidated_reason TEXT,
    reason TEXT NOT NULL,
    executed_order_id BIGINT REFERENCES simulated_orders(id) ON DELETE SET NULL,
    is_test BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_signals_status ON strategy_signals(status);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_generated_at ON strategy_signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_is_test ON strategy_signals(is_test);

-- 3. Mở rộng bảng simulated_orders hỗ trợ quản trị vị thế nâng cao & phân lập dữ liệu test
ALTER TABLE simulated_orders
    ADD COLUMN IF NOT EXISTS parent_ticket_id BIGINT,
    ADD COLUMN IF NOT EXISTS is_breakeven_moved BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_partial_closed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS trailing_stop_price NUMERIC(12, 4),
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_simulated_orders_is_test ON simulated_orders(is_test);
