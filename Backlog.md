# Backlog cập nhật

## 2026-10-07 18:10 +07:00

### [Update Phase 02 - Sprint 02]: Tối ưu kích thước mũi tên biểu đồ & Tính Exit Price như lệnh Sell (điểm thoát lệnh)

- **Tiến trình cập nhật & Hoàn thành:**
  - **Tối ưu kích thước mũi tên (`TradingViewChart.vue`):**
    - Điều chỉnh kích thước marker về chuẩn `size: 1` (gọn gàng, thanh thoát, cân xứng với tỷ lệ nến và bấc nến trên mọi khung thời gian M1–D1, loại bỏ cảm giác mũi tên bị thô/quá to khi zoom xa).
  - **Hiển thị điểm thoát lệnh (Exit Price) dưới dạng lệnh SELL:**
    - Ghi nhận `close_time` / `exit_price` của các lệnh đã đóng như một điểm hành động thoát lệnh:
      - Đối với lệnh **BUY**: Điểm thoát lệnh (Exit price) được tính là lệnh **SELL** -> hiển thị mũi tên đỏ cam (`arrowDown`, `aboveBar`, `#ef5350`) đặt bên trên nến tại thời điểm đóng lệnh.
      - Đối với lệnh **SELL**: Điểm thoát lệnh (Exit price) được tính là lệnh **BUY** -> hiển thị mũi tên xanh ngọc (`arrowUp`, `belowBar`, `#26a69a`) đặt bên dưới nến tại thời điểm đóng lệnh.
  - **Khử trùng lặp đa lệnh trên cùng nến (Candle-level Deduplication):**
    - Áp dụng cấu trúc `Set` gom nhóm theo `barTime` cho cả chiều BUY và chiều SELL.
    - Nếu trên cùng 1 nến có nhiều lệnh BUY (hoặc nhiều lệnh SELL/Exit), hệ thống chỉ vẽ duy nhất **1 mũi tên** cho mỗi chiều, đảm bảo không có bất kỳ marker nào bị vẽ đè chồng lên nhau.
  - **Kiểm tra & Nghiệm thu:**
    - Toàn bộ frontend production build: `npm run build` hoàn thành không lỗi (`built in 2.11s`, 1591 modules).
    - Đã đồng bộ dist bundle sang container `trading_frontend` trên Docker (`http://localhost:3000`).
- **Trạng thái:** Hoàn thành, các tính năng đã hoạt động trực tiếp.

---

## 2026-10-07 17:40 +07:00

### [Update Phase 02 - Sprint 02]: Tối giản hiển thị điểm lệnh Buy/Sell trên biểu đồ TradingView (Dạng mũi tên, lược bỏ chữ, gộp 1 mũi tên trên cùng 1 nến)

- **Tiến trình cập nhật & Hoàn thành:**
  - **Tối giản hóa biểu thị điểm lệnh (`TradingViewChart.vue`):**
    - **Lược bỏ toàn bộ chữ hiển thị trên marker:** Loại bỏ các chuỗi text dài đi kèm như `BUY 0.1L`, `SELL 0.2L` và loại bỏ các marker đóng lệnh hình tròn `circle` kèm text PnL/close reason, giúp thân nến và các vùng giá không bị che khuất.
    - **Biểu thị dạng mũi tên trực quan:**
      - Lệnh **BUY**: Mũi tên xanh ngọc (`arrowUp`, `#26a69a`) đặt bên dưới nến (`belowBar`), kích thước rõ ràng (`size: 2`).
      - Lệnh **SELL**: Mũi tên đỏ cam (`arrowDown`, `#ef5350`) đặt bên trên nến (`aboveBar`), kích thước rõ ràng (`size: 2`).
    - **Khử trùng lặp & Gộp 1 mũi tên duy nhất trên cùng 1 nến:**
      - Gom nhóm toàn bộ lệnh theo timestamp nến đã snap (`barTime`).
      - Trường hợp có nhiều hơn 1 lệnh buy hoặc sell trên cùng 1 nến (DCA, khớp lệnh cùng giây/phút hoặc khi xem trên khung thời gian lớn M5–D1), hệ thống gộp lại và chỉ vẽ đúng **1 mũi tên duy nhất** đại diện tại nến đó (theo chiều của lệnh mở gần nhất).
      - Ngăn chặn hoàn toàn hiện tượng chồng đè marker và xung đột hiển thị trên cùng một thanh nến.
    - Giữ nguyên các đường kẻ giá trực tiếp (PriceLines) cho Entry, Stop Loss, Take Profit của các lệnh đang mở để trader theo dõi vị thế trực tiếp trên biểu đồ.
  - **Kiểm tra & Nghiệm thu:**
    - Toàn bộ frontend production build: `npm run build` hoàn thành không lỗi (`built in 2.28s`, 1591 modules).
    - Đã đồng bộ dist bundle sang container `trading_frontend` trên Docker (`http://localhost:3000`).
    - Backend test suite: `docker exec trading_backend pytest` đạt **32 passed in 2.89s**.
- **Trạng thái:** Hoàn thành, các tính năng đã hoạt động trực tiếp.

---

## 2026-10-07 16:45 +07:00

### [Update Phase 02 - Sprint 02]: Nâng cấp News & Events section trong Trading Cockpit với 3 tabs ngày (Yesterday, Today, Tomorrow) & Điều hướng toàn bộ Economic Calendar

- **Tiến trình cập nhật & Hoàn thành:**
  - **Khối News & Events trong Trading Cockpit (`NewsStream.vue`):**
    - **Phân chia 3 Tabs theo ngày:** Bổ sung thanh 3 tabs ngày trực tiếp trong phần Economic Calendar gồm **Yesterday**, **Today**, **Tomorrow** kèm theo badge số lượng sự kiện thực tế tương ứng từng ngày.
    - **Mặc định mở ở tab "Today":** Khởi tạo mặc định chọn tab `Today` khi vào Trading Cockpit, giúp trader tập trung tức thì vào các sự kiện và chỉ số vĩ mô phát hành trong ngày giao dịch hiện tại.
    - **Phân loại & Lọc dữ liệu chính xác theo ngày:** Tự động lọc các sự kiện lịch kinh tế (`EconomicEvent`) khớp theo ngày theo múi giờ hiển thị (ICT / UTC), sắp xếp theo trình tự thời gian (chronological) từ sớm đến muộn trong ngày.
    - **Hiển thị đầy đủ thông tin cho từng tab:**
      - Cột thời gian: Giờ phát hành (HH:mm) kèm tag trạng thái Countdown/Release (`RELEASED`, `IN ...H ...M`, `TIME UNVERIFIED`).
      - Chi tiết sự kiện: Tiêu đề sự kiện, badge mã tiền tệ (USD, EUR,...), số sao ảnh hưởng (★★★ Cao, ★★ Vừa, ★ Thấp), tên nguồn cung cấp (FairEconomy,...).
      - Thẻ dữ liệu kinh tế vĩ mô: Hiển thị nổi bật các chỉ số thực tế `Act` (Actual), `Frc` (Forecast), `Prev` (Previous) khi có sẵn dữ liệu.
      - Trạng thái rỗng (Empty State) tinh gọn, thanh thoát khi một ngày không có sự kiện kinh tế nào.
    - **Nút chuyển hướng sang màn hình hiển thị toàn bộ Economic Calendar (News & Events):**
      - Bổ sung nút shortcut trên thanh tiêu đề `[ Toàn bộ lịch ↗ ]` và nút hành động CTA nổi bật ở chân danh sách `[ Xem toàn bộ Economic Calendar ↗ ]`.
      - Khi click, kích hoạt sự kiện `@navigate-calendar`, tự động chuyển điều hướng ứng dụng sang màn hình **News & Events** và mở sẵn tab con **Economic Calendar**.
  - **Đồng bộ hóa màn hình toàn bộ Economic Calendar (`NewsEventsView.vue` & `App.vue`):**
    - `App.vue`: Bổ sung handler `openFullCalendar()` và prop `:initial-sub-tab="calendarInitialSubTab"`.
    - `NewsEventsView.vue`: Tiếp nhận prop `initialSubTab` và watcher để chuyển đổi trực tiếp sang tab `Economic Calendar` khi được kích hoạt từ Trading Cockpit.
    - Mở rộng thanh công cụ bộ lọc của Economic Calendar toàn màn hình với bộ lọc nhanh theo ngày: `Tất cả`, `Hôm qua`, `Hôm nay`, `Ngày mai` giúp trader lọc nhanh cả trên màn hình tổng thể.
    - Duy trì luồng Breaking News bên dưới trong khối Cockpit để trader vừa theo dõi lịch kinh tế vừa nắm bắt tin tức nóng.
  - **Kiểm tra & Nghiệm thu:**
    - Toàn bộ backend test suite: **32 passed in 2.89s** trên container `trading_backend`.
    - Frontend bundle: `npm run build` hoàn thành không có lỗi (`built in 21.82s`, 1591 modules).
    - Đã đồng bộ dist bundle sang container `trading_frontend` trên Docker (`http://localhost:3000`).
- **Trạng thái:** Hoàn thành, các tính năng đã hoạt động trực tiếp.

---

## 2026-10-06 22:20 +07:00

### [Update Phase 02 - Sprint 02]: Hoàn thành triển khai hệ thống điều hướng menu Header, Orders History, News & Events, Settings (Đã nghiệm thu)

- **Tiến trình tiếp tục & Hoàn thành:**
  - **Triển khai hệ thống điều hướng Menu Header (`App.vue` & `style.css`):**
    - Bổ sung thanh điều hướng chính gồm 4 tabs: **Trading Cockpit**, **Orders History** (kèm badge số lệnh thực tế), **News & Events** (kèm badge tổng tin tức & sự kiện), **Settings**.
    - Tích hợp chuyển tab trực tiếp khi click vào các nút shortcut trên header (nút Bell chuyển sang News & Events, nút Settings2 chuyển sang Settings, Brand logo chuyển về Trading Cockpit).
    - Giữ nguyên trạng thái live ticker giá vàng XAUUSD, bid/ask spread, số dư Balance/Equity và system status strip trên toàn bộ các view.
  - **Component Lịch sử lệnh (`OrdersHistory.vue`):**
    - Thống kê hiệu suất: Win Rate, Total Realized PnL, Profit Factor, số lệnh thắng/thua, trung bình PnL/lệnh từ dữ liệu thực tế `simulated_orders` trong DB.
    - Bộ lọc đa tiêu chí: Lọc trạng thái (Tất cả, Đã đóng, Mở), lọc Side (BUY/SELL), lọc lý do đóng (TP Hit, SL Hit, Manual Close), tìm kiếm theo Ticket/UUID/Symbol/Strategy trigger, sắp xếp theo thời gian/PnL/khối lượng.
    - Bảng chi tiết lệnh: Ticket ID, UUID (hỗ trợ copy nhanh), thời gian mở/đóng (ICT), Asset, Side badge, Lot size, Entry, Exit, SL, TP, Realized PnL ($), Lời/Lỗ (%), Close reason badge, thời lượng giữ lệnh, trạng thái.
  - **Component Tin tức & Lịch kinh tế (`NewsEventsView.vue`):**
    - Giám sát trạng thái 4 nguồn tin (Data Feeds Status): FairEconomy, Kitco News, FXStreet News, Finnhub với trạng thái Health, Mode, và số lượt nạp thành công.
    - Tab **Economic Calendar**: Lọc theo mức độ ảnh hưởng (★★★ Cao, ★★ Vừa, ★ Thấp), lọc loại tiền tệ (USD, EUR, GBP,...), tìm kiếm từ khóa, hiển thị thời gian phát hành (ICT & UTC), countdown thời gian (chỉ đếm ngược khi `timezone_status == VERIFIED`), bảng so sánh Actual vs Forecast vs Previous.
    - Tab **Breaking News & Headlines**: Lọc theo nguồn tin, số sao tác động, sắc thái tâm lý (Bullish, Bearish, Neutral), tìm kiếm từ khóa, hiển thị điểm Sentiment Score, tóm tắt AI Analysis Summary và liên kết trực tiếp bài viết gốc.
  - **Component Cấu hình hệ thống & Chẩn đoán (`SettingsView.vue`):**
    - Thông tin chi tiết danh mục tài khoản mô phỏng từ database: Vốn ban đầu ($10,000), Số dư hiện tại, Equity, Tỷ lệ tăng trưởng PnL, Ký quỹ sử dụng (Margin Used), Ký quỹ tự do (Free Margin), số vị thế mở, nút đồng bộ dữ liệu.
    - Cấu hình tham số giao dịch mô phỏng (lưu `localStorage`): Default Lot Size, Default SL Offset, Default TP Offset, Max Slippage Points, xác nhận trước khi gửi lệnh, âm thanh cảnh báo khi chạm TP/SL.
    - Giám sát chẩn đoán hạ tầng: PostgreSQL 16, Redis 7 Pub/Sub, Binance PAXGUSDT WebSocket feed, Paper Execution Engine worker; kèm công cụ tương tác kiểm tra độ trễ kết nối API (Test Connection Ping latency).
    - Tùy chọn hiển thị giao diện: Khung thời gian mặc định (M1-D1), múi giờ hiển thị (ICT/UTC), bật/tắt dải volume mặc định.
  - **Backend API Update (`backend/api/v1/orders.py` & `api.js`):**
    - Hoàn thiện cơ chế tự động tính `pnl_percentage` dựa trên `entry_price`, `exit_price` và `order_type` khi trường này chưa được gán sẵn trong DB cho các lệnh đã đóng.
    - Bổ sung tham số limit linh hoạt cho `fetchOrders`, `fetchNews`, `fetchEconomicEvents` trong frontend API service.
  - **Kiểm tra & Nghiệm thu:**
    - Toàn bộ backend test suite: **32 passed in 1.81s** trên container `trading_backend`.
    - Frontend bundle: `vite build` hoàn thành không có lỗi (`built in 19.54s`, 1591 modules).
    - Nginx frontend container (`trading_frontend`) và FastAPI backend container (`trading_backend`) đã được rebuild và deploy thành công trên Docker (`http://localhost:3000`).
    - Các endpoints API `/api/v1/orders`, `/api/v1/news`, `/api/v1/news/events`, `/api/v1/simulation/account`, `/health` đều hoạt động ổn định và trả về dữ liệu thực từ cơ sở dữ liệu.
- **Trạng thái:** Hoàn thành toàn diện, các tính năng đã hoạt động trực tiếp.

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