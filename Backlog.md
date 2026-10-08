# Backlog cập nhật

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