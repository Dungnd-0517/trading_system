# Backlog cập nhật

## 2026-10-09 21:55 +07:00

### [Update Phase 02 - Sprint 03]: Hoàn thiện Động cơ Phân tích Cảm xúc Tin tức (News Sentiment Engine & AI Context)

- **Tiến trình cập nhật & Hoàn thành:**
  - **Động cơ Phân tích Cảm xúc Chuyên sâu cho Vàng XAUUSD (`backend/ai_engine/sentiment.py`):**
    - Xây dựng thuật toán NLP phân tích cảm xúc thị trường tài chính chuyên biệt cho cặp tỷ giá XAUUSD và dữ liệu kinh tế vĩ mô toàn cầu.
    - Nhận diện đa chiều: phân biệt tác động trực tiếp lên Vàng (đà bứt phá, lực mua gom, nhu cầu phòng hộ rủi ro, căng thẳng địa chính trị) và tác động nghịch chiều từ chỉ số USD (DXY), lợi suất trái phiếu (Treasury yields) cùng chính sách lãi suất Fed (hawkish/dovish).
    - Xử lý ngữ cảnh đảo ngược (negation handling): tự động nhận biết các từ phủ định/thất bại (`fails to rally`, `struggles to`, `unlikely to`) trong cụm từ ngữ.
    - Phân cấp mức độ biến động rủi ro (`LOW`, `MEDIUM`, `HIGH_RISK_HALT`) dựa trên biên độ cảm xúc và sự kiện đặc biệt (CPI, NFP, FOMC, địa chính trị).
    - Tự động sinh tóm tắt phân tích AI (`ai_analysis_summary`) chi tiết, giải thích cụ thể lý do tích cực/tiêu cực/trung lập đối với giá Vàng.
  - **Tích hợp Ingestion Thời gian thực & Tự động Backfill (`backend/data_ingestion/news_worker.py`):**
    - Tích hợp hàm `analyze_sentiment` vào chu trình xử lý tin tức định kỳ của `NewsCollector`: mọi tin tức mới từ Kitco News, FXStreet News và Finnhub đều được tự động chấm điểm và sinh tóm tắt AI ngay khi lưu DB.
    - Phát sự kiện `news.upsert` qua Redis kênh `news:events` kèm theo trường `sentiment_score` và `ai_analysis_summary` phục vụ hiển thị trực tiếp trên UI.
    - Xây dựng cơ chế tự động quét nạp bổ sung (`backfill_news_sentiment`) khi backend khởi động: đã hoàn tất chấm điểm toàn bộ hơn 500 bản ghi tin tức lịch sử trong DB PostgreSQL.
  - **Mở rộng API Backend (`backend/api/v1/news.py`):**
    - Bổ sung endpoint `GET /api/v1/news/sentiment` trả về các chỉ số thống kê cảm xúc tổng hợp: điểm số trung bình, xu hướng (BULLISH/BEARISH/NEUTRAL), số lượng tin tức tích cực, tiêu cực và trung tính.
    - Bổ sung endpoint `POST /api/v1/news/analyze` cho phép kích hoạt quy trình phân tích và cập nhật lại điểm số theo yêu cầu.
  - **Nâng cấp Giao diện Đo Cảm xúc (`SentimentGauge.vue` & `NewsEventsView.vue`):**
    - `SentimentGauge.vue`:
      - Kim đo động (animated pointer) mượt mà với hiệu ứng cubic-bezier bám sát trục dải màu từ Bearish (-1.0) đến Bullish (+1.0).
      - Hiển thị điểm số định dạng tài chính có dấu (`+0.35`, `-0.20`, `0.00`).
      - Huy hiệu trạng thái xu hướng động: `BULLISH` (xanh), `BEARISH` (đỏ), `NEUTRAL` (xám) với icon trực quan.
      - Dòng giải thích bối cảnh vĩ mô tương ứng cho Vàng (XAUUSD).
      - Bộ đếm phân loại số lượng tin tức theo từng trạng thái (Bullish ↑ / Neutral – / Bearish ↓).
    - `NewsEventsView.vue`:
      - Hiển thị chuẩn xác huy hiệu Sentiment Pill trên từng thẻ tin tức kèm icon `TrendingUp`, `TrendingDown`, `Minus`.
      - Hộp thông tin `AI INSIGHT` hiển thị sinh động phân tích giải thích lý do tác động.
      - Bộ lọc tin tức theo cảm xúc (Tất cả, Bullish, Bearish, Neutral) hoạt động chính xác 100%.
  - **Kiểm thử & Triển khai:**
    - Toàn bộ backend test suite: **50 passed in 3.62s** trên container `trading_backend` (bao gồm 7 tests mới cho `test_sentiment.py`).
    - Frontend build: `npm run build` hoàn thành không có lỗi (`built in 2.63s`, 1598 modules).
    - Các dịch vụ Docker (`trading_backend`, `trading_frontend`, `trading_postgres`, `trading_redis`) hoạt động ổn định và đồng bộ dữ liệu.
- **Trạng thái:** Hoàn thành toàn diện.

---

### [Update Phase 02 - Sprint 03]: Làm Mới Biểu Đồ Nến Liên Tục (Chống Khoảng Trống Nhảy Giá) & Quy Đổi Khung Thời Gian về Giờ Việt Nam (ICT, UTC+7)

- **Tiến trình cập nhật & Hoàn thành:**
  - **Cơ chế Làm Mới Liên Tục & Đồng Bộ Nến Thời Gian Thực (`marketStore.js`):**
    - Thiết lập cơ chế chạy ngầm `syncHistory()` định kỳ 2.5 giây (`startPolling(2500)`): tự động so khớp và đồng bộ chuỗi nến lịch sử từ cơ sở dữ liệu backend, lấp kín hoàn toàn các khoảng trống (gaps) nếu có độ trễ mạng hoặc gói tin WebSocket bị gián đoạn.
    - Duy trì nến đang hình thành (forming candle) và nạp tức thì các nến mới mở (`new bar opened`) trực tiếp vào mảng nến trong bộ nhớ `marketStore.candles` khi nhận sự kiện tick `chart.update`, ngăn chặn triệt để tình trạng nhảy lùi thời gian hoặc mất nến gần nhất khi vẽ lại.
    - Nâng cấp `connectMarketStream` (`websocket.js`) với cơ chế tự động kết nối lại (Auto-reconnect sau 2 giây) khi kết nối mạng chập chờn hoặc đứt quãng, bảo đảm luồng dữ liệu biểu đồ không bị ngắt quãng.
  - **Tối ưu Cơ chế Render Tránh Nhảy Zoom / Khung Hình (`TradingViewChart.vue`):**
    - Quản lý cờ trạng thái `hasInitialFit`: chỉ kích hoạt `chart.timeScale().fitContent()` một lần duy nhất khi lần đầu tải biểu đồ hoặc khi người dùng chuyển đổi cặp tiền / khung thời gian (`timeframe`).
    - Trong các chu kỳ làm mới liên tục ngầm tiếp theo, hệ thống cập nhật dữ liệu mượt mà qua `setData` mà không làm reset góc nhìn, giữ nguyên 100% tọa độ phóng to/thu nhỏ (zoom/pan) của trader.
  - **Quy Đổi Khung Timeframe và Trục Thời Gian về Giờ Việt Nam (ICT, UTC+7):**
    - **Trục hoành thời gian (Horizontal TimeScale):** Thiết lập `timeScale.tickMarkFormatter` quy đổi chuẩn xác toàn bộ nhãn thời gian trên trục biểu đồ về múi giờ Việt Nam (UTC+7, không phụ thuộc vào cài đặt múi giờ máy khách), định dạng linh hoạt theo cấp độ thời gian (Năm, Tháng, Ngày, Giờ:Phút).
    - **Nhãn Crosshair trục thời gian:** Tích hợp `localization.timeFormatter` hiển thị chi tiết `DD/MM/YYYY HH:mm (ICT)` ngay dưới con trỏ định vị.
    - **Thanh Legend Bar & Tooltip nổi:** Hàm `formatBarTime` quy đổi và hiển thị thời gian nến chuẩn xác `YYYY-MM-DD HH:mm (ICT)` cả khi hover và ở trạng thái nến mới nhất.
    - **Chân biểu đồ (Chart Footer):** Cập nhật nhãn tham chiếu `ICT (UTC+7, Vietnam) · {timeframe}` tại `App.vue`.
  - **Kiểm thử & Triển khai Hệ thống:**
    - Biên dịch production build frontend (`npm run build`) thành công 100% không lỗi cú pháp.
    - Hệ thống Nginx container `trading_frontend` tự động nhận bản build mới và đồng bộ tức thời trên cả Localhost, LAN và Cloudflare Tunnel.
- **Trạng thái:** Hoàn thành.

---

## 2026-10-09 17:15 +07:00

### [Update Phase 02 - Sprint 03]: Hiển thị Đường EMA, Giá trị Chỉ báo trên Biểu đồ & Tùy biến Tham số trong Cài đặt

- **Tiến trình cập nhật & Hoàn thành:**
  - **Tích hợp Thuật toán & Vẽ Đường EMA (`TradingViewChart.vue`):**
    - Hiện thực hàm tính toán chỉ số Trung bình Động Lũy thừa `computeEMA(candles, period)` theo công thức chuẩn kỹ thuật:
      $$\text{Multiplier} = \frac{2}{\text{Period} + 1}, \quad \text{EMA}_t = (\text{Close}_t - \text{EMA}_{t-1}) \times \text{Multiplier} + \text{EMA}_{t-1}$$
    - Tạo `addLineSeries` trong TradingView `lightweight-charts` với các tùy chọn nét vẽ mượt mà, độ dày nét, màu sắc cấu hình linh hoạt.
    - Xử lý cập nhật động thời gian thực (`applyLiveEvent`): tính toán và đẩy giá trị EMA tick mới nhất vào chuỗi line series khi có nến mới hoặc tick giá biến động.
    - Tự động phản ứng (reactive watchers) khi người dùng thay đổi bật/tắt EMA, thay đổi chu kỳ (period) hoặc đổi màu sắc đường.
  - **Hiển thị Giá trị Đường EMA Động trên Legend Bar & Floating Tooltip:**
    - **Candle Legend Bar:** Hiển thị thẻ chỉ số `EMA({period}): {value}` với màu sắc đồng bộ của đường EMA. Giá trị tự động cập nhật theo nến đang hover hoặc nến mới nhất khi không hover.
    - **Floating Hover Tooltip:** Thêm dòng hiển thị giá trị đường EMA tại đúng tọa độ thời gian của nến mà con trỏ chuột đang chỉ tới.
    - Lưu trữ bộ chỉ mục `emaMap` tối ưu truy xuất $O(1)$ theo timestamp giúp thao tác rê chuột mượt mà 60fps.
  - **Thiết lập Tham số Chỉ số EMA trong Cài đặt (`SettingsView.vue`):**
    - Thêm Section 5: **Chỉ báo kỹ thuật & Đường EMA (Technical Indicators)** trong trang Settings.
    - Tùy chọn Bật/Tắt hiển thị EMA với công tắc chuyển đổi trực quan.
    - Ô nhập chu kỳ EMA (`Period`) dạng số tùy ý, đi kèm các nút chọn nhanh (Quick Presets) cho các chu kỳ kinh điển: `EMA 9`, `EMA 20`, `EMA 50`, `EMA 100`, `EMA 200`.
    - Bảng chọn màu sắc trực quan (Vàng kim, Cam, Xanh dương, Xanh ngọc, Tím, Đỏ hồng) và bảng mã màu HTML tùy ý (`color input`).
    - Thẻ xem trước trực quan (Badge Preview) phản chiếu tức thì chu kỳ và màu sắc cấu hình.
    - Lưu trữ bền vững vào `localStorage` (`fieldnote_user_settings`) và đồng bộ tức thì trên toàn bộ ứng dụng qua `settingsStore`.
  - **Nút Bật/Tắt Nhanh trên Khung Biểu đồ (`ChartOverlayControls.vue`):**
    - Bổ sung nút chuyển đổi nhanh `EMA ({period})` ngay tại thanh công cụ góc trên biểu đồ nến giúp trader bật/tắt nhanh mà không cần rời màn hình giao dịch.
    - Hiển thị chấm màu sắc tương ứng chỉ báo và nhãn trạng thái kích hoạt.
  - **Kiểm thử & Triển khai Hệ thống:**
    - Biên dịch production build frontend (`npm run build`) thành công 100% không cảnh báo/lỗi cú pháp.
    - Volume mount Docker tự động cập nhật mã nguồn phân phối qua Nginx `trading_frontend` trên cả cổng localhost, mạng nội bộ (LAN) và Cloudflare Tunnel.
- **Trạng thái:** Hoàn thành.

---

## 2026-10-09 15:35 +07:00

### [Update Phase 02 - Sprint 03]: Hiển thị Chi tiết Thông tin Nến (OHLCV & Price Change) khi Hover trên Biểu đồ TradingView

- **Tiến trình cập nhật & Hoàn thành:**
  - **Tích hợp Bắt sự kiện Crosshair Hover (`TradingViewChart.vue`):**
    - Sử dụng `chart.subscribeCrosshairMove` từ thư viện `lightweight-charts` để theo dõi tọa độ di chuột và dữ liệu nến chính xác theo thời gian thực.
    - Phân giải và tính toán dữ liệu: Open, High, Low, Close, Volume, Biên độ thay đổi giá (Change = Close - Open) và tỷ lệ % biến động.
    - Xây dựng cơ chế tra cứu nến nhanh (Candle Map lookup) và hủy đăng ký sự kiện (`unsubscribeCrosshairMove`) khi component unmounted để tối ưu hóa bộ nhớ và hiệu năng render.
  - **Thanh Thông tin Trạng thái Nến (Candle Legend Bar):**
    - Đặt cố định góc trên bên trái khung biểu đồ (`top: 8px, left: 10px`), thiết kế kính mờ (Glassmorphism) hiện đại, đồng bộ hệ màu DM Mono của hệ thống.
    - Hiển thị đầy đủ thông số: Mã cặp tiền (`XAUUSD`), Thời gian nến, O, H, L, C, Chênh lệch giá & % (phân biệt màu xanh Bullish / đỏ Bearish), và Volume.
    - Chế độ hiển thị kép thông minh: Tự động cập nhật thông số của nến đang hover kèm tag `[HOVER]`; khi chuột rời biểu đồ, tự động chuyển về hiển thị thông số của nến mới nhất (`latest candle`) tránh để trống giao diện.
  - **Thẻ Tooltip Nổi Thông minh (Floating Hover Tooltip Card):**
    - Hiển thị thẻ tooltip bám sát con trỏ chuột khi hover qua từng nến trên biểu đồ.
    - Cung cấp đầy đủ: Thời gian nến, Badge xu hướng nến (`BULLISH ▲` / `BEARISH ▼`), bảng chi tiết Open / High / Low / Close, Biên độ giá ($ & %), và Khối lượng giao dịch.
    - Tự động giới hạn vị trí (Bounding Box Clamping) chống tràn viền phải và viền dưới biểu đồ, thiết lập `pointer-events: none` giúp thao tác chuột trên canvas mượt mà 100%.
  - **Cập nhật & Kiểm thử Hệ thống:**
    - Truyền prop `:symbol="marketStore.symbol"` từ `App.vue` sang `TradingViewChart.vue`.
    - Kiểm thử build production frontend (`npm run build`) hoàn thành 100% không lỗi (`1597 modules transformed`).
    - Nginx Docker container `trading_frontend` tự động nhận và phân phối ngay lập tức bản build mới nhất thông qua volume mount `./frontend/dist`.
- **Trạng thái:** Hoàn thành.

---

## 2026-10-09 11:30 +07:00

### [Update Phase 02 - Sprint 03]: Hoàn thành Động cơ Tự động Kích hoạt SMC, Quản trị Vị thế Động (BE Move / Partial TP) & Màn hình Backtest Lab

- **Tiến trình cập nhật & Hoàn thành:**
  - **D12. Database Schema & Migration Sprint 3 (`0004_phase2_sprint3.sql` - `backend/migrations/`):**
    - Tạo bảng `system_trading_config`: lưu trữ cấu hình chế độ thực thi (`MANUAL`, `SEMI_AUTO`, `FULL_AUTO`), tỷ lệ rủi ro (`risk_percent_per_trade: 1.0%`), giới hạn vị thế mở (`max_open_positions: 2`), giới hạn lỗ tối đa trong ngày (`max_daily_drawdown_percent: 5.0%`), cờ tin tức (`circuit_breaker_enabled: true`), cấu hình dời SL (`be_trigger_r_multiple: 1.5R`), tỷ lệ chốt lời từng phần (`partial_tp_ratio: 0.5`).
    - Tạo bảng `strategy_signals`: lưu trữ tín hiệu phân tích SMC theo thời gian thực (`symbol`, `timeframe`, `signal_type`, `entry_price`, `stop_loss`, `take_profit`, `confidence_score`, `reasons`, `status`, `execution_ticket_id`).
    - Mở rộng bảng `simulated_orders`: bổ sung các trường vị thế động: `parent_ticket_id`, `is_breakeven_moved`, `is_partial_closed`, `trailing_stop_price`.
    - Cập nhật SQLAlchemy ORM models (`backend/core/models.py`) và nạp seed config mặc định vào cơ sở dữ liệu PostgreSQL.

  - **D13. News Circuit Breaker Guard (`backend/ai_engine/news_guard.py`):**
    - Module `NewsCircuitBreaker` tự động quét các sự kiện kinh tế USD có độ ảnh hưởng cao (High Impact - 3 sao đỏ như CPI, NFP, FOMC Interest Rate).
    - Cửa sổ bảo vệ: Tự động kích hoạt trạng thái cấm mở lệnh trước 30 phút và sau 30 phút (`cooldown_minutes=30`) so với thời điểm công bố tin.
    - Phát broadcast sự kiện `circuit_breaker.update` qua WebSocket đến toàn bộ client kết nối khi trạng thái ngắt mạch thay đổi.
    - Bộ test unit `test_news_guard.py` kiểm thử đầy đủ các tình huống: tin tức đang trong vùng cấm, tin ngoài vùng cấm, và cấu hình bypass khi tắt circuit breaker.

  - **D14. Signal Generation Engine (`backend/ai_engine/signal_worker.py`):**
    - Worker chạy ngầm theo chu kỳ nến M15 (tự động khởi động và quản lý vòng đời trong FastAPI lifespan).
    - Tích hợp toàn diện pipeline phân tích SMC 3 tầng: HTF Alignment D1/H4 -> POI Discount/Premium H1 -> M15 Trigger CHoCH / Kill Zone.
    - Kiểm tra bộ lọc News Circuit Breaker trước khi phê duyệt tín hiệu.
    - Lưu tín hiệu đủ điều kiện vào bảng `strategy_signals` và phát thông báo tức thời `market:signals` (`signal.new`).
    - Bổ sung test unit `test_signal_worker.py` giả lập nến và luồng xử lý tín hiệu.

  - **D15. Dynamic Position Management & Auto Executor (`backend/simulation/`):**
    - **Tự động Dời SL về Hòa Vốn (Break-Even Move):** Khi giá đi đúng hướng và tỷ lệ lợi nhuận chạm $\ge 1.5R$, `paper_worker.py` / `paper_engine.py` tự động nâng/hạ Stop Loss về đúng giá Entry ban đầu (`entry_price`), bảo toàn 100% vốn cho lệnh.
    - **Chốt Lời Từng Phần (Partial Take-Profit 50% TP1):** Khi giá chạm vùng TP1 hoặc trader click nút `[ 50% TP ]`, hệ thống chốt 50% volume vị thế hiện tại vào Realized PnL, đồng thời tự động dời SL của 50% volume còn lại về điểm hòa vốn (`is_breakeven_moved=True`).
    - **Động cơ Auto Executor (`auto_executor.py`):** Xử lý thực thi tự động theo 3 chế độ:
      - `MANUAL`: Chỉ phát tín hiệu và âm thanh cảnh báo, người dùng tự duyệt vào lệnh.
      - `SEMI_AUTO`: Tự động điền thông số và hiển thị popup cho trader xác nhận bằng 1 click.
      - `FULL_AUTO`: Tự động tính Lot size theo 1% rủi ro tài khoản và mở lệnh ngay lập tức khi tín hiệu xuất hiện.
    - Tích hợp kiểm tra giới hạn an toàn: `max_open_positions`, `max_daily_drawdown_percent`, và `circuit_breaker`.

  - **D16. API Router `/api/v1/strategy` & WebSocket Multiplexing:**
    - `GET /api/v1/strategy/signals`: Danh sách tín hiệu kèm phân trang và lọc trạng thái.
    - `POST /api/v1/strategy/evaluate`: Quét và đánh giá tín hiệu SMC tức thời cho cặp tiền.
    - `POST /api/v1/strategy/execute`: Kích hoạt khớp lệnh từ tín hiệu chiến lược.
    - `GET/PUT /api/v1/strategy/config`: Đọc và cập nhật cấu hình chế độ giao dịch thời gian thực.
    - `POST /api/v1/strategy/backtest`: Mô phỏng chiến lược trên chuỗi nến lịch sử, tính toán tỷ lệ Winrate, Profit Factor, Max Drawdown, Sharpe Ratio, và đường cong vốn Equity Curve.
    - `POST /api/v1/orders/{id}/partial-close`: API chốt lời từng phần vị thế mô phỏng.
    - Mở rộng kênh WebSocket `market:signals` và `market:circuit_breaker` trên cùng endpoint `/api/v1/ws/market`.

  - **D17. Giao diện Frontend - Điều khiển Chế độ & Quản trị Lệnh (`frontend/`):**
    - **Thanh Topbar Controller (`App.vue` & `style.css`):** Bổ sung cụm điều khiển Mode Pill 3 trạng thái (`MANUAL`, `SEMI-AUTO`, `FULL-AUTO`), hiển thị badge cảnh báo Circuit Breaker đỏ nhấp nháy khi có tin tức USD lớn.
    - **Audio Alert (`orderStore.js`):** Sử dụng Web Audio API tổng hợp âm báo tần số kép khi có tín hiệu SMC mới xuất hiện mà không cần phụ thuộc vào file âm thanh ngoài.
    - **Bảng Paper Positions (`OrderBookTable.vue`):** Bổ sung nút thao tác nhanh `[ 50% TP ]` cho từng lệnh đang mở, hiển thị badge `[BE]` khi đã dời hòa vốn và `[50% Banked]` khi đã chốt một phần.
    - **Khối Setup Action (`MarketAnalysisStatus.vue`):** Bổ sung nút `[ Kích hoạt theo Setup ⚡ ]` tự động tính lot size theo rủi ro mở lệnh trực tiếp, nút `[ Quét Tín hiệu M15 🔄 ]`, và cảnh báo Circuit Breaker trực tiếp.
    - **Màn hình Backtest Lab (`BacktestLabView.vue`):** Màn hình kiểm thử chiến lược toàn diện với KPI tóm tắt (Net Profit, Win Rate, Total Trades, Profit Factor, Max DD), biểu đồ SVG Interactive Equity Curve, và bảng danh sách chi tiết các lệnh backtest kèm lọc theo kết quả WIN / LOSS.

  - **Kiểm thử & Nghiệm thu:**
    - Toàn bộ backend test suite: **43/43 tests passed in 2.56s** trên Docker `trading_backend`.
    - Frontend production build: `npm run build` hoàn thành 100% không lỗi (`✓ built in 4.01s`, 1597 modules).
    - Đã deploy dist bundle sang container `trading_frontend` (`http://localhost:3000`) và reload nginx.
- **Trạng thái:** Hoàn thành toàn diện Sprint 03.

---

## 2026-10-07 22:30 +07:00

### [Update Phase 02 - Sprint 02]: Bổ sung Khối Trạng thái Phân tích & Kịch bản Giao dịch trong Trading Cockpit (Dưới Paper Positions)

- **Tiến trình cập nhật & Hoàn thành:**
  - **Phát triển Backend API Phân tích Thị trường (`/api/v1/market/analysis` - `backend/api/v1/market.py`):**
    - Trích xuất dữ liệu giá thực tế từ cơ sở dữ liệu và công cụ tính toán SMC / Sessions của hệ thống (`ai_engine.sessions`, `ai_engine.smc`).
    - Tính toán động 5 thành phần phân tích trọng tâm:
      1. *Xu hướng dài hạn (HTF Trend Confirmation):* Xác nhận đa khung D1 & H4, trạng thái đồng thuận xu hướng (Alignment), các mốc Swing High và Swing Low gần nhất.
      2. *Xu hướng hiện tại trong ngày (Intraday Trend & Dealing Range):* Đánh giá khung H1 & M15, nhận diện vị thế vùng giá Discount (< 50% Equilibrium) hoặc Premium (> 50% Equilibrium), phát hiện phiên giao dịch và trạng thái cửa sổ thanh khoản Kill Zone (London, NY AM, NY PM, Asia).
      3. *Các kịch bản đề xuất (Proposed Scenarios):* Phân bổ 2 kịch bản chi tiết: Kịch bản chính (Primary - 65% xác suất, Mua theo POI Discount H1 & xác nhận M15 CHoCH) và Kịch bản dự phòng (Alternative - 35% xác suất, theo dõi nhịp phá vỡ & quét thanh khoản Sell-Side).
      4. *Dự đoán điểm vào lệnh (Predicted Setup):* Cung cấp vùng vào lệnh (Entry Zone), điểm kích hoạt chuẩn (Entry Price), điểm cắt lỗ (Stop Loss), điểm chốt lời (Take Profit), tỷ lệ Risk:Reward (R:R &ge; 1:2), trạng thái chờ xác nhận (`WAITING_TRIGGER`).
      5. *Quy tắc bỏ qua chỉ báo & hủy kịch bản (Invalidation Criteria):* 4 tiêu chí bảo vệ vốn nghiêm ngặt (phá vỡ POI, tin tức 3 sao Circuit Breaker, hết phiên Kill Zone, R:R không tối ưu).
  - **Xây dựng Component Giao diện Phân tích Thị trường (`MarketAnalysisStatus.vue`):**
    - Đặt trực tiếp dưới bảng **Paper Positions** (`OrderBookTable.vue`) trong cột biểu đồ chính (`.chart-column`) của Trading Cockpit (`App.vue`).
    - **Header & Ribbon trạng thái tức thời:** Hiển thị mã cặp tiền (`XAUUSD`), giá thị trường thời gian thực, nút làm mới (Refresh) kèm đồng bộ tự động mỗi 30 giây; thanh ribbon tóm tắt nhanh: HTF Bias, Dealing Zone, Kill Zone Status, Setup Engine.
    - **Thẻ 1 &ndash; Xu hướng Dài hạn (HTF Confirmation):** Cấu trúc xác nhận D1/H4 (BULLISH/BEARISH), trạng thái đồng thuận đa khung (`Alignment: Validated`), hiển thị mốc Swing High và Swing Low.
    - **Thẻ 2 &ndash; Xu hướng Trong ngày (Intraday Bias & Dealing Range):** Thanh trực quan hóa khoảng dao động Dealing Range H1 (Low &rarr; Equilibrium 50% &rarr; High) kèm con trỏ chỉ vị trí giá hiện tại; tự động đưa ra khuyến nghị vùng Discount (ưu tiên Mua) hoặc Premium (cảnh báo rủi ro mua đuổi đỉnh).
    - **Thẻ 3 &ndash; Các Kịch bản Đề xuất theo dõi (Scenarios in Monitor):** 2 khối kịch bản Primary (65%) và Alternative (35%) với đầy đủ điều kiện kích hoạt, vùng mục tiêu giá (BSL/SSL) và nhãn trạng thái theo dõi.
    - **Thẻ 4 &ndash; Dự đoán Điểm vào lệnh khi đủ điều kiện (Predicted Setup):** Hiển thị trực quan hướng lệnh (`BUY ON TRIGGER`), vùng Entry, SL, TP, tỷ lệ R:R; tích hợp **công cụ tính Lot size động (Dynamic Lot Size Calculator)** phản ứng theo số dư tài khoản thực tế và bộ chọn mức rủi ro (0.5%, 1.0%, 1.5%, 2.0%).
    - **Thẻ 5 &ndash; Xác nhận Bỏ qua Chỉ báo & Hủy kịch bản (Invalidation Rules):** Thống kê 4 quy tắc kỷ luật SMC giúp trader hủy tín hiệu và đứng ngoài an toàn khi giá không đi đúng kịch bản, đi kèm badge trạng thái kiểm tra.
  - **Tích hợp Kiến trúc & Hệ thống:**
    - Cập nhật `frontend/src/services/api.js` bổ sung hàm `fetchMarketAnalysis`.
    - Kết nối component `MarketAnalysisStatus.vue` vào `frontend/src/App.vue`.
    - Đã build production frontend thành công (`npm run build`, 1595 modules, 0 lỗi) và đồng bộ sang container `trading_frontend`.
    - Đã chạy kiểm thử backend (`pytest`), toàn bộ **32 test cases passed**.
- **Trạng thái:** Hoàn thành, các chức năng đã hoạt động trực tiếp trên hệ thống.

---

## 2026-10-07 19:00 +07:00

### [Update Phase 02 - Sprint 02]: Bổ sung Menu Chiến lược & Phân tích (Strategy & Analysis) và Hệ tri thức SMC Trading áp dụng cho hệ thống

- **Tiến trình cập nhật & Hoàn thành:**
  - **Triển khai Menu điều hướng mới (`App.vue` & `style.css`):**
    - Bổ sung tab **Strategy & Analysis** (icon `BrainCircuit`) vào thanh điều hướng Header chính trên toàn hệ thống.
    - Tích hợp nhãn nhận diện màn hình hoạt động `VIEW: STRATEGY & ANALYSIS`.
    - Kết nối nút shortcut từ khối `InsightsPanel` trong Trading Cockpit giúp trader mở trực tiếp trang phân tích chiến lược.
  - **Xây dựng Màn hình Chiến lược & Phân tích (`StrategyAnalysisView.vue`):**
    - **Executive Hero Header:** Tổng quan mô hình giao dịch SMC / ICT đa khung thời gian cho XAUUSD (Gold), triết lý rule-based không look-ahead, thông số tỷ lệ R:R mục tiêu &ge; 1:2 (mục tiêu 1:3), mức rủi ro 0.5% &ndash; 1.0% vốn.
    - **Tab 1 &ndash; Quy trình Đa khung thời gian (Multi-Timeframe Pipeline):** Chi tiết 3 tầng phân tích thực tế trong mã nguồn:
      1. *Tầng 1 (HTF Bias - D1 &amp; H4):* Xác định xu hướng vĩ mô qua Fractal Swing (Left=3, Right=3) và điều kiện đồng thuận bắt buộc (D1/H4 alignment).
      2. *Tầng 2 (POI Selection - H1):* Phân chia Dealing Range theo 50% Equilibrium (chỉ BUY ở Discount, chỉ SELL ở Premium), quét Order Block và Fair Value Gap (FVG &ge; 0.3 &times; ATR).
      3. *Tầng 3 (Trigger &amp; Entry - M15):* Kiểm tra chạm vùng POI H1 (Tap POI), nến M15 đóng cửa tạo CHoCH trong khung giờ Kill Zone.
    - **Tab 2 &ndash; Thư viện Khái niệm SMC Cốt lõi (SMC Mechanics Library):** Định nghĩa toán học chi tiết về BOS (Break of Structure), CHoCH (Change of Character), Order Block (OB), Fair Value Gap (FVG), Dealing Range &amp; Equilibrium, Liquidity Sweeps.
    - **Tab 3 &ndash; Khung giờ vàng giao dịch (Kill Zones &amp; Sessions):** Bảng đối chiếu giờ New York và giờ Việt Nam (ICT) cho London Kill Zone (14:00&ndash;17:00 ICT), New York AM Kill Zone (19:00&ndash;22:00 ICT), New York PM Kill Zone, ICT Silver Bullet và cơ chế tự động bù trừ giờ mùa hè/mùa đông (DST-aware).
    - **Tab 4 &ndash; Ma trận Quản trị Rủi ro &amp; Vốn (Risk Management Matrix):** Công cụ tính Lot Size tự động tương tác trực tiếp theo số dư vốn và khoảng cách SL; quy tắc ngắt giao dịch khẩn cấp khi sụt giảm trong ngày chạm ngưỡng Daily Loss &ge; 5.0% và Stop Loss buffer theo ATR.
    - **Tab 5 &ndash; Bộ lọc Tin tức &amp; Bối cảnh vĩ mô (Macro News Guard):** Cơ chế Circuit Breaker tự động khóa mở lệnh khi có tin đỏ 3 sao (CPI, NFP, FOMC) và bộ điều tiết khối lượng/khoảng cách SL theo tỷ lệ biến động ATR Volatility Ratio.
    - **Tab 6 &ndash; Checklist Vào lệnh Tương tác (Execution Checklist):** 7 tiêu chí vàng giúp trader tự đánh giá điều kiện vào lệnh thực tế, kèm thanh tiến độ phần trăm trực quan.
  - **Nâng cấp Khối Bối cảnh thị trường trong Cockpit (`InsightsPanel.vue`):**
    - Cập nhật hiển thị tóm tắt mô hình chiến lược SMC, chế độ thực thi và phiên Kill Zone hiện hành; bổ sung nút chuyển hướng nhanh sang màn hình Strategy &amp; Analysis.
  - **Kiểm tra &amp; Nghiệm thu:**
    - Toàn bộ frontend production build: `npm run build` hoàn thành không lỗi (`built in 2.30s`, 1593 modules).
    - Đã đồng bộ dist bundle sang container `trading_frontend` trên Docker (`http://localhost:3000`).
    - Backend test suite: `docker exec trading_backend pytest` đạt **32 passed in 1.80s**.
- **Trạng thái:** Hoàn thành, các tính năng đã hoạt động trực tiếp.

---

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