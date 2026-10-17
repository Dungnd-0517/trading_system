-- Migration 0009: Phase 03 - Sprint 03 (Update) - MT5 Data Integration
-- Muc tieu: Chuan bi schema va index de ho tro du lieu nen tu MT5 (tu 2026-01-01)

-- 1. Them cot data_source de theo doi nguon goc du lieu nen (mt5 | binance | synthetic)
ALTER TABLE market_candles
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(16) NOT NULL DEFAULT 'binance';

-- 2. Tao index ho tro query theo nguon du lieu
CREATE INDEX IF NOT EXISTS idx_market_candles_source
    ON market_candles(symbol, timeframe, data_source);

-- 3. Tao index tong hop toi uu cho query lich su (500 nen gan nhat)
CREATE INDEX IF NOT EXISTS idx_market_candles_history
    ON market_candles(symbol, timeframe, open_time DESC);

-- 4. Ghi chu cot data_source
COMMENT ON COLUMN market_candles.data_source IS
    'Nguon goc du lieu: mt5, binance, synthetic';
