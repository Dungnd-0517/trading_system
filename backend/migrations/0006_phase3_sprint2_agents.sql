-- Migration: backend/migrations/0006_phase3_sprint2_agents.sql
-- Phase 3 Sprint 2: Multi-Agent System Infrastructure & Decision Memory Schema

-- 1. Bảng lưu trữ nhật ký quyết định đồng thuận của Strategy Governor
CREATE TABLE IF NOT EXISTS agent_decision_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_regime VARCHAR(64) NOT NULL,
    suggested_bias VARCHAR(32) NOT NULL,
    consensus_score NUMERIC(4, 2) NOT NULL,
    technical_confidence NUMERIC(4, 2) NOT NULL,
    macro_sentiment_score NUMERIC(4, 2) NOT NULL,
    active_circuit_breaker BOOLEAN NOT NULL DEFAULT FALSE,
    applied_risk_pct NUMERIC(4, 2) NOT NULL,
    applied_sl_mult NUMERIC(4, 2) NOT NULL,
    applied_min_rr NUMERIC(4, 2) NOT NULL,
    trading_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    halt_reason TEXT,
    rationale_summary TEXT NOT NULL,
    agent_votes JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_test BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_agent_decision_logs_timestamp ON agent_decision_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_decision_logs_is_test ON agent_decision_logs(is_test);

-- 2. Bảng lưu trữ lịch sử đối thoại giữa Chủ thể (Trader) và Strategy Governor
CREATE TABLE IF NOT EXISTS agent_trader_dialogue (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sender VARCHAR(32) NOT NULL,
    message_type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    approval_status VARCHAR(32),
    is_test BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_timestamp ON agent_trader_dialogue(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_is_test ON agent_trader_dialogue(is_test);

-- 3. Mở rộng bảng trading_knowledge với nguồn gốc, trường phái và độ tin cậy tri thức
ALTER TABLE trading_knowledge
    ADD COLUMN IF NOT EXISTS school_of_thought VARCHAR(64) NOT NULL DEFAULT 'GENERAL',
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(64) NOT NULL DEFAULT 'SYSTEM_CORE',
    ADD COLUMN IF NOT EXISTS verified_by_trader BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(4, 2) NOT NULL DEFAULT 1.00;

CREATE INDEX IF NOT EXISTS idx_trading_knowledge_school ON trading_knowledge(school_of_thought);
CREATE INDEX IF NOT EXISTS idx_trading_knowledge_source_type ON trading_knowledge(source_type);
CREATE INDEX IF NOT EXISTS idx_trading_knowledge_metadata ON trading_knowledge USING gin (metadata);
