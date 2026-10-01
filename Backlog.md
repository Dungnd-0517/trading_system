# Backlog cập nhật

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