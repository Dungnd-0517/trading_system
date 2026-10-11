-- Migration: backend/migrations/0005_phase3_agents_memory.sql
-- Phase 3 Sprint 1: Vector Infrastructure & Agents Memory Schema

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Bảng lưu trữ tri thức giao dịch cho RAG (Trading Knowledge Base)
CREATE TABLE IF NOT EXISTS trading_knowledge (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL, -- 'SMC', 'PRICE_ACTION', 'RISK_MANAGEMENT', 'MACRO', 'TEST'
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_knowledge_category ON trading_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_trading_knowledge_embedding ON trading_knowledge USING hnsw (embedding vector_cosine_ops);

-- 3. Bảng lưu trữ ký ức giao dịch cho Reflexion Engine (Episodic Trade Memory)
CREATE TABLE IF NOT EXISTS episodic_trade_memory (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES simulated_orders(id) ON DELETE CASCADE,
    outcome VARCHAR(16) NOT NULL, -- 'WIN', 'LOSS', 'BREAKEVEN'
    market_context_summary TEXT NOT NULL,
    root_cause TEXT,
    lesson_learned TEXT NOT NULL,
    mistake_category VARCHAR(64), -- 'FOMO', 'COUNTER_TREND', 'EARLY_ENTRY', 'BAD_RR', etc.
    rule_to_add TEXT,
    embedding vector(1536),
    is_test BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_order_id ON episodic_trade_memory(order_id);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_outcome ON episodic_trade_memory(outcome);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_mistake ON episodic_trade_memory(mistake_category);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_is_test ON episodic_trade_memory(is_test);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_embedding ON episodic_trade_memory USING hnsw (embedding vector_cosine_ops);

-- 4. Mở rộng system_trading_config với các tham số thích ứng AI (Dynamic Runtime Parameters)
ALTER TABLE system_trading_config
    ADD COLUMN IF NOT EXISTS atr_sl_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    ADD COLUMN IF NOT EXISTS min_risk_reward_ratio NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    ADD COLUMN IF NOT EXISTS trading_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS halt_reason TEXT,
    ADD COLUMN IF NOT EXISTS updated_by_agent VARCHAR(64) NOT NULL DEFAULT 'SYSTEM_INIT';
