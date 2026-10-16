-- Migration 0009: Phase 03 - Sprint 03 (Update) - MT5 Data Integration
-- Mục tiêu: Chuẩn bị schema và index để hỗ trợ dữ liệu nến từ MT5 (từ 2026-01-01)
-- Ghi chú: Migration này KHÔNG xóa dữ liệu nến cũ; việc xóa và nạp lại
--           được thực hiện qua API /api/v1/market/mt5/seed sau khi MT5 kết nối.

-- 1. Thêm cột source để theo dõi nguồn gốc dữ liệu nến (mt5 | binance | synthetic)
ALTER TABLE market_candles
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(16) NOT NULL DEFAULT 'binance';

-- Update các nến hiện tại (trước 2026-01-01) được đánh dấu là 'binance'
-- Các nến mới từ MT5 sẽ tự động được đánh dấu 'mt5' qua application layer
-- (không update vì chưa biết chắc nguồn gốc)

-- 2. Tạo index hỗ trợ query theo nguồn dữ liệu
CREATE INDEX IF NOT EXISTS idx_market_candles_source
    ON market_candles(symbol, timeframe, data_source);

-- 3. Tạo index tổng hợp tối ưu cho query lịch sử (500 nến gần nhất)
CREATE INDEX IF NOT EXISTS idx_market_candles_history
    ON market_candles(symbol, timeframe, open_time DESC);

-- 4. Ghi nhận thời điểm migration
COMMENT ON COLUMN market_candles.data_source IS
    'Nguồn gốc dữ liệu: mt5 (từ MetaTrader5 bridge), binance (proxy PAXGUSDT), synthetic (tổng hợp từ M1)';
