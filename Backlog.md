# Backlog cập nhật

## 2026-10-06 15:38 +07:00

### [Update Phase 02 - Sprint 02]: Thêm menu Settings, Orders History, News & Events (Tạm ngưng / Đã lưu trạng thái)

- **Mục tiêu & Yêu cầu:**
  - Bổ sung hệ thống điều hướng menu trên Header: **Trading Cockpit**, **Orders History**, **News & Events**, **Settings**.
  - Hiển thị dữ liệu thực tế từ các bảng demo đã có sẵn trong cơ sở dữ liệu (`simulated_orders`: 15 lệnh, `financial_news`: 214 bài viết, `economic_events`: 87 sự kiện, `simulation_account`: tài khoản demo #1).
  - Không tự ý sinh hoặc chèn dữ liệu giả lập (mock data); nếu bảng dữ liệu trống thì giữ trạng thái rỗng (empty state) rõ ràng.
- **Hiện trạng & Công việc đã chuẩn bị:**
  - Khảo sát và xác nhận dữ liệu demo trong DB: `simulated_orders` (15 bản ghi), `financial_news` (214 bản ghi), `economic_events` (87 bản ghi), `simulation_account` (1 bản ghi).
  - Cập nhật backend `backend/api/v1/orders.py`: bổ sung trường `pnl_percentage` trong response của endpoint `GET /api/v1/orders` để hỗ trợ hiển thị tỷ lệ lời/lỗ chi tiết trong lịch sử lệnh.
  - Kiểm tra backend test suite: **32 passed in 3.70s** trên container `trading_backend`.
  - Thiết kế kiến trúc các component frontend chuẩn bị triển khai:
    - `OrdersHistory.vue`: Thống kê tổng quan (Win Rate, Total PnL, Total Trades), bộ lọc đa tiêu chí (Status, Side, Close Reason) và bảng lịch sử lệnh chi tiết.
    - `NewsEventsView.vue`: Lịch sự kiện kinh tế với bộ lọc sao/loại tiền tệ/thời gian countdown, luồng tin tức thị trường và giám sát trạng thái các nguồn tin (FairEconomy, Kitco, FXStreet, Finnhub).
    - `SettingsView.vue`: Thông tin tài khoản mô phỏng từ DB, cấu hình tham số lệnh (lot size, SL, TP, slippage), trạng thái kết nối hạ tầng (Postgres, Redis, WebSocket, Binance feed) và tùy chọn hiển thị.
    - `App.vue`: Tích hợp thanh điều hướng chuyển đổi tab mượt mà.
- **Trạng thái:** Tạm ngưng theo yêu cầu người dùng, đã lưu toàn bộ hiện trạng và tài liệu hóa chi tiết trong backlog.

---

## 2026-10-06 00:45 +07:00

### [Update Phase 02 - Sprint 02]: Cập nhật hiển thị chính xác biểu đồ cho từng khung thời gian M1, M5, M15, H1; Bổ sung 2 khung thời gian H4, D1

- **Mở rộng khung thời gian & Ingestion đa khung (T2.2 Update):**
  - Mở rộng `TIMEFRAMES` và `TIMEFRAME_TO_BINANCE_INTERVAL` trong `chart_streamer.py` hỗ trợ đầy đủ 6 khung thời gian: `M1` (60s), `M5` (300s), `M15` (900s), `H1` (3600s), `H4` (14400s), `D1` (86400s).
  - Cập nhật `CandleAggregator.ingest_kline` và `ingest_tick` tự động tổng hợp nến realtime OHLCV và tính toán tích lũy volume chính xác cho cả 6 khung thời gian từ feed Binance PAXGUSDT và MT5. Áp dụng wrapper `KlineEventList` tương thích ngược 100% với các test trước.
  - Cài đặt `seed_history_for_timeframe` và nâng cấp `seed_binance_history_if_needed` tự động nạp 500 nến lịch sử từ Binance REST cho từng khung thời gian, kèm cơ chế fallback tổng hợp từ nến M1 nội bộ nếu offline.
- **API Router Auto-Seed (T2.4 Update):**
  - Cập nhật endpoint `GET /api/v1/market/history` tự động kích hoạt nạp nến lịch sử theo yêu cầu (on-demand seeding) nếu DB chưa có dữ liệu cho khung thời gian đó, đảm bảo không bao giờ bị nến rỗng khi chuyển khung.
- **Tối ưu hóa Paper Worker (T2.3 Update):**
  - Lọc sự kiện tick theo `timeframe == "M1"` trong `PaperEngineWorker.run()` để tránh quét lặp lại SL/TP 6 lần cho cùng một tick thị trường.
- **Frontend Multi-Timeframe Charting (T2.5 & T2.6 Update):**
  - Bổ sung 2 nút chọn khung thời gian `H4` và `D1` trong thanh điều khiển biểu đồ tại `App.vue` (`['M1', 'M5', 'M15', 'H1', 'H4', 'D1']`).
  - Cập nhật `marketStore.applyChartUpdate`: tách biệt cập nhật giá live (`lastPrice`, `quote` BID/ASK/SPD) liên tục theo mọi tick với sự kiện vẽ nến của khung thời gian đang kích hoạt (`chartEvent`), giúp thanh header luôn nhấp nháy giá live ngay cả khi chuyển khung thời gian cao hơn.
  - Nâng cấp `TradingViewChart.vue`:
    - Cài đặt thuật toán binary search `findMatchingBarTime` để snap thời gian của Order Markers (vào lệnh, đóng lệnh) khớp chính xác với thanh nến của từng khung thời gian, loại bỏ hoàn toàn lỗi `Assertion failed` của lightweight-charts.
    - Bổ sung watcher và đồng bộ `livePriceLine` khi chuyển đổi khung thời gian hoặc khi nhận tick mới.
- **Kiểm tra & Nghiệm thu:**
  - Toàn bộ backend test suite: **32 passed in 2.09s** trên container `trading_backend`.
  - Frontend build: `npm run build` hoàn thành không có lỗi (`built in 1.96s`, 1585 modules).
  - Docker services (`trading_backend`, `trading_frontend`, `trading_postgres`, `trading_redis`) đã rebuild và khởi động thành công.
  - Đã xác thực API `GET /api/v1/market/history` trả về đầy đủ 500 nến cho cả 6 khung thời gian: M1, M5, M15, H1, H4, D1.

---

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