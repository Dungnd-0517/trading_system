-- Migration: backend/migrations/0008_phase3_sprint3_knowledge_strategies.sql
-- Phase 3 Sprint 3: Standardized Trading Strategies & Knowledge Ingestion Engine

-- 1. Bảng lưu trữ cấu trúc giao dịch tiêu chuẩn hóa cho từng phương pháp (Standardized Trading Strategies)
CREATE TABLE IF NOT EXISTS standardized_trading_strategies (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(128) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    school_of_thought VARCHAR(64) NOT NULL,
    timeframe_focus VARCHAR(32) NOT NULL DEFAULT 'M15',
    target_risk_reward NUMERIC(4, 2) NOT NULL DEFAULT 2.00,
    philosophy TEXT NOT NULL,
    setup_checklist JSONB NOT NULL DEFAULT '[]'::jsonb,
    entry_rules TEXT NOT NULL,
    stop_loss_rules TEXT NOT NULL,
    take_profit_rules TEXT NOT NULL,
    invalidation_conditions TEXT NOT NULL,
    risk_guardrails JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    system_file_path VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_test BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_std_strategies_school ON standardized_trading_strategies(school_of_thought);
CREATE INDEX IF NOT EXISTS idx_std_strategies_is_test ON standardized_trading_strategies(is_test);
CREATE INDEX IF NOT EXISTS idx_std_strategies_updated_at ON standardized_trading_strategies(updated_at DESC);

-- 2. Mở rộng bảng trading_knowledge với các trường nguồn gốc và chuẩn phân lập D18
ALTER TABLE trading_knowledge
    ADD COLUMN IF NOT EXISTS source_file VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_trading_knowledge_is_test ON trading_knowledge(is_test);
CREATE INDEX IF NOT EXISTS idx_trading_knowledge_source_file ON trading_knowledge(source_file);
