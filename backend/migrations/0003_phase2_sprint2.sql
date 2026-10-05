-- Migration: backend/migrations/0003_phase2_sprint2.sql

-- 1. Bổ sung các cột nâng cao cho simulated_orders
ALTER TABLE simulated_orders 
    ADD COLUMN IF NOT EXISTS ticket_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS slippage NUMERIC(8, 4) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS commission NUMERIC(8, 2) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS swap NUMERIC(8, 2) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS close_reason VARCHAR(32);

-- Tạo index cho ticket_uuid
CREATE UNIQUE INDEX IF NOT EXISTS uq_simulated_orders_ticket_uuid 
    ON simulated_orders(ticket_uuid);

-- 2. Tạo bảng quản lý tài khoản giả định
CREATE TABLE IF NOT EXISTS simulation_account (
    id SERIAL PRIMARY KEY,
    initial_balance NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    current_balance NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    equity NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    margin_used NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Khởi tạo tài khoản mặc định nếu chưa tồn tại
INSERT INTO simulation_account (id, initial_balance, current_balance, equity)
VALUES (1, 10000.00, 10000.00, 10000.00)
ON CONFLICT (id) DO NOTHING;
