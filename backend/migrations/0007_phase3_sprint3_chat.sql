-- Migration: backend/migrations/0007_phase3_sprint3_chat.sql
-- Phase 3 Sprint 3: Multi-Conversation Real-time Chat System Schema

-- 1. Bảng quản lý danh sách cuộc trò chuyện (Chat Conversations)
CREATE TABLE IF NOT EXISTS chat_conversations (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    agent_target VARCHAR(64) NOT NULL DEFAULT 'GOVERNOR',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_test BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated_at ON chat_conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_is_pinned ON chat_conversations(is_pinned);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_is_test ON chat_conversations(is_test);

-- 2. Nâng cấp bảng agent_trader_dialogue để gắn kết với conversation
ALTER TABLE agent_trader_dialogue
    ADD COLUMN IF NOT EXISTS conversation_id BIGINT REFERENCES chat_conversations(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS client_msg_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS target_agent VARCHAR(64) NOT NULL DEFAULT 'GOVERNOR';

CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_conv_id ON agent_trader_dialogue(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_client_msg_id ON agent_trader_dialogue(client_msg_id);
