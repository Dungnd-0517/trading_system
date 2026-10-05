# Backlog cập nhật

## 2026-10-02 15:15 +07:00

### Phase 2 - Sprint 2 implementation (PAXGUSDT Feed, Paper Execution Engine & Cockpit)

- **Database Migration & Models (T2.1):** Tạo migration additive `0003_phase2_sprint2.sql` bổ sung `ticket_uuid`, `slippage`, `commission`, `swap`, `close_reason` cho `simulated_orders` và tạo bảng `simulation_account`. Cập nhật `run_migrations()` duyệt tự động tất cả các file migration `.sql` theo thứ tự và cập nhật SQLAlchemy models.
- **Binance PAXG Feed Ingestion (T2.2):** Tích hợp luồng WebSocket Binance `paxgusdt@kline_1m` trực tiếp vào `ChartStreamer` với symbol alias sang `XAUUSD`, sinh synthetic spread ECN 20 points ($0.20/oz: Bid = Close - 0.10, Ask = Close + 0.10), tự động seed nến lịch sử từ Binance REST nếu DB trống và phát sự kiện `chart.update` theo chuẩn D4/D7.
- **Paper Execution Engine & Worker (T2.3):** Cài đặt interface `BaseOrderExecutor` (`core/interfaces/executor.py`), hoàn thiện `PaperEngine` và `PaperEngineWorker` chạy nền trong FastAPI lifespan, lắng nghe Redis `market:ticks`, tự động quét kiểm tra đóng lệnh theo SL/TP từng tick, tính Realized PnL và phát event `order.update` (`ORDER_FILLED`, `ORDER_CLOSED`) qua Redis channel `paper:orders`.
- **API Router (T2.4):** Bổ sung API `POST /api/v1/orders/{id}/close` (đóng lệnh thủ công) và `GET /api/v1/simulation/account` (thông tin số dư, equity, free margin).
- **Frontend Charting & UI Cockpit (T2.5 & T2.6):**
  - Tích hợp `TradingViewChart.vue` vẽ các đường giá Entry (xanh dương đứt nét), Stop Loss (đỏ), Take Profit (xanh lá) bằng `createPriceLine()` và các markers mua/bán/chấm PnL đóng lệnh bằng `setMarkers()`.
  - Cập nhật `OrderBookTable.vue` hiển thị Unrealized PnL theo giá live và nút `[ Close ]` đóng vị thế tức thì.
  - Cập nhật `App.vue` header hiển thị số dư Balance / Equity, live price nhấp nháy xanh/đỏ theo tick, và lắng nghe sự kiện `order.update` từ WebSocket.

### Kiểm tra & Nghiệm thu
- Toàn bộ backend test suite: **31 passed in 1.65s** trên container `trading_backend`.
- Frontend build `npm run build`: hoàn thành không có lỗi (`built in 1.84s`).
- Docker services (`trading_backend`, `trading_frontend`, `trading_postgres`, `trading_redis`) đều khởi động thành công, healthy và đã kiểm tra thực tế khớp lệnh tự động / đóng lệnh thủ công.

---

## 2026-10-01 21:33 +07:00

### Phase 2 - Sprint 1 implementation

- Thêm SQLAlchemy models và migration additive `0002_phase2_sprint1` cho sao/phân loại/revisions của breaking news, `economic_events` và `economic_event_revisions`; giữ nguyên bảng/lệnh Phase 1.
- Thêm provider parsers cho FairEconomy JSON, Kitco RSS, FXStreet RSS và Finnhub Market News; chuẩn hóa timestamp, relevance, dedupe keys và classifier 1–3 sao/`UNKNOWN`.
- Thêm collector worker với polling, retries/backoff, `Retry-After`, circuit breaker, fallback, stale/source status, revision snapshots và Redis `news.upsert` events.
- Thêm API `GET /api/v1/news/events` và `GET /api/v1/news/status`; mở rộng breaking-news response mà không đổi paper-order events.
- Thêm MT5 ticks-since bridge endpoint và candle aggregator cho MT5/Binance; upsert OHLCV vào PostgreSQL và phát `chart.update` với volume unit riêng.
- Cập nhật frontend stores, WebSocket routing, candlestick/volume/live-price series, news stars/source links, event countdown chỉ khi timezone đã xác minh, và source status badges.
- Thêm `.env.example`/Compose flags cho Finnhub; calendar fallback mặc định tắt.

### Kiểm tra

- Pylance diagnostics cho các Python modules đã sửa: không có lỗi.
- Frontend `npm run build`: đạt.
- Provider/chart/worker tests: 16 passed ở lần chạy gần nhất; full backend suite: 24 passed, 1 deselected.
- Test nền `backend/tests/test_paper_engine.py::PaperEngineTests::test_trade_statistics` vẫn fail do so sánh float tuyệt đối (`66.66666666666666` so với `66.66666666666667`); lỗi đã tồn tại trước thay đổi này.
- Migration `0002_phase2_sprint1` đã chạy thành công hai lần trên DB thử theo schema Phase 1 và đã được áp dụng vào DB phát triển. `simulated_orders` cùng khóa ngoại Phase 1 được giữ nguyên.
- `docker compose up -d --build backend frontend` build thành công; frontend đang chạy tại `http://localhost:3000`.

### Còn chờ trước khi bật live sources

- Backend container chưa khởi động được trên DB phát triển: password của PostgreSQL user trong volume đã khởi tạo không khớp cấu hình hiện tại. Backend đã được dừng để tránh restart loop; không reset volume hoặc đổi password. Cần đồng bộ credential hiện có trước khi chạy backend.
- MT5 bridge image không có package/runtime MetaTrader5; live XAUUSD cần bridge chạy trong môi trường Windows có terminal MT5 đã kết nối.
- Finnhub Market News cần API key; Finnhub Economic Calendar cần Premium entitlement và xác minh timezone của trường `time`. Hai điều kiện này chưa được cấu hình/bật.
- Xác nhận quyền lưu/phân phối feed FairEconomy, Kitco và FXStreet trước production.