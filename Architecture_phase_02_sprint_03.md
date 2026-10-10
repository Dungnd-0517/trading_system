# KIẾN TRÚC KỸ THUẬT: GIAI ĐOẠN 2 - SPRINT 3

> **Trạng thái:** DRAFT ARCHITECTURE SPECIFICATION FOR REVIEW.  
> **Tài liệu nền:** [Architecture.md](Architecture.md)  
> **Tài liệu Sprint trước:** [Architecture_phase_02_sprint_01.md](Architecture_phase_02_sprint_01.md), [Architecture_phase_02_sprint_02.md](Architecture_phase_02_sprint_02.md)  
> **Thông số kỹ thuật hiện tại:** [technical_system.md](technical_system.md)  
> **Phạm vi (Scope):** Động cơ Tự động Kích hoạt Tín hiệu SMC (Autonomous Signal Trigger Engine); Bộ điều phối Tự động Mở lệnh (Auto-Trading Controller); Quản trị Vị thế Nâng cao (Break-Even Move, Partial Take Profit, Trailing Stop); Tích hợp Bộ ngắt mạch Tin tức Đỏ (Macro News Circuit Breaker); Màn hình Thử nghiệm Chiến lược & Backtest Lab.  
> **Ngoài phạm vi (Out of Scope):** Kết nối MT5 Live Broker bằng tiền thật (thuộc Giai đoạn 3); Huấn luyện mô hình Deep Learning Reinforcement Learning (RL) tự học (thuộc Giai đoạn 4).  
> **Ngày lập:** 2026-10-08  

---

## MỤC LỤC
1. [Mục tiêu và Phạm vi (Sprint Objectives)](#1-mục-tiêu-và-phạm-vi-sprint-objectives)
2. [Quyết định Kiến trúc (Decision Log D12–D16)](#2-quyết-định-kiến-trúc-decision-log)
3. [Kiến trúc Tổng thể & Luồng Dữ liệu (Architecture & Data Flow)](#3-kiến-trúc-tổng-thể--luồng-dữ-liệu)
4. [Động cơ Tự động Kích hoạt Tín hiệu (Autonomous Signal Engine)](#4-động-cơ-tự-động-kích-hoạt-tín-hiệu)
5. [Bộ Ngắt mạch Tin tức Đỏ Vĩ mô (Macro News Circuit Breaker)](#5-bộ-ngắt-mạch-tin-tức-đỏ-vĩ-mô)
6. [Quản trị Vị thế Động Nâng cao (Advanced Position Management)](#6-quản-trị-vị-thế-động-nâng-cao)
7. [Hợp đồng API & WebSocket (API & WebSocket Contracts)](#7-hợp-đồng-api--websocket-contracts)
8. [Mô hình Dữ liệu & Migration Additive (`0004_phase2_sprint3.sql`)](#8-mô-hình-dữ-liệu--migration-additive)
9. [Kiến trúc Frontend & Màn hình Backtesting Lab](#9-kiến-trúc-frontend--màn-hình-backtesting-lab)
10. [Kế hoạch Triển khai theo Task (Task Breakdown T3.1–T3.6)](#10-kế-hoạch-triển-khai-theo-task)
11. [Kiểm thử, SLO & Tiêu chuẩn Nghiệm thu (DoD)](#11-kiểm-thử-slo--tiêu-chuẩn-nghiệm-thu)

---

## 1. MỤC TIÊU VÀ PHẠM VI (SPRINT OBJECTIVES)

### 1.1. Bối cảnh & Vấn đề Cần giải quyết
Ở Sprint 1 và Sprint 2, hệ thống đã hoàn thiện xuất sắc:
* Dữ liệu nến 24/7 từ Binance PAXGUSDT ánh xạ sang XAUUSD trên 6 khung thời gian (M1 đến D1).
* Động cơ khớp lệnh ảo `PaperEngineWorker` theo dõi SL/TP từng tick, tính Realized PnL và cập nhật số dư.
* Thư viện nguyên thủy SMC / ICT (`ai_engine/smc.py`, `strategy.py`, `sessions.py`) và giao diện hiển thị kịch bản phân tích `MarketAnalysisStatus.vue` trong Cockpit.

**Hạn chế lớn nhất hiện tại:**
1. **Thiếu cơ chế tự động kích hoạt:** Trader vẫn phải quan sát thủ công và bấm tay đặt lệnh. Khi nến M15 đóng tạo CHoCH trong phiên Kill Zone, hệ thống chưa tự động bắt tín hiệu và đẩy lệnh vào động cơ khớp.
2. **Quản trị vị thế còn sơ khai:** Lệnh chỉ có Stop Loss và Take Profit cố định từ lúc vào. Chưa có khả năng tự động dời SL về hòa vốn (Break-Even) khi giá đã chạy được 1.5R, chưa có chốt lời từng phần (Partial TP) hay Trailing Stop theo ATR.
3. **Bộ lọc tin tức chưa kết nối với lệnh:** Tiêu chí bảo vệ vốn `inv_2` (hủy kịch bản khi có tin tức 3 sao) trên giao diện mới chỉ là text tĩnh, chưa có logic tự động ngăn chặn mở lệnh khi tin đỏ sắp ra.
4. **Chưa có công cụ Backtest trực quan:** Trader chưa thể kiểm tra xem nếu chạy chiến lược SMC này trên 2,000 nến quá khứ thì tỷ lệ Win Rate và Profit Factor thực tế đạt bao nhiêu.

### 1.2. Mục tiêu Trọng tâm của Sprint 3
1. **Xây dựng `SignalEngineWorker` tự động phát hiện Setup:** Lắng nghe chu kỳ đóng nến M15, đối chiếu điều kiện D1/H4 Bias $\to$ H1 POI Discount/Premium $\to$ M15 CHoCH trong Kill Zone, tự động sinh tín hiệu chuẩn `strategy_signals`.
2. **Bộ điều khiển Chế độ Thực thi (Trading Mode Controller):** Hỗ trợ 3 chế độ:
   * `MANUAL`: Bắn thông báo lên giao diện kèm âm thanh alert, trader click xác nhận vào lệnh.
   * `SEMI_AUTO`: Hiển thị Quick Modal đếm ngược 10s tự động xác nhận trừ khi bị hủy.
   * `FULL_AUTO`: Tự động tính Lot Size theo 1% rủi ro tài khoản và tự động mở lệnh trực tiếp vào `PaperEngineWorker`.
3. **Nâng cấp Động cơ Khớp lệnh với Quản trị Vị thế Động (Dynamic Position Management):**
   * **Break-Even (BE) Protection:** Tự động dời SL về giá `Entry + 0.10` khi giá di chuyển đạt $+1.5R$.
   * **Partial Take Profit (50% TP1):** Tự động chốt lời một nửa khối lượng ($50\%$ lot) tại mục tiêu $1:2R$, dời SL của $50\%$ lot còn lại về BE và gồng đến $3R$ hoặc BSL/SSL.
   * **Trailing Stop Loss:** Bám sát theo $1.5 \times \text{ATR}(15)$ khi giá bứt phá mạnh.
4. **Hiện thực hóa Circuit Breaker Tin tức Đỏ Vĩ mô:** Tự động khóa mở lệnh mới trong phạm vi $\pm 30$ phút của các sự kiện kinh tế 3 sao (CPI, NFP, FOMC, GDP).
5. **Xây dựng Trung tâm Kiểm thử Chiến lược (Backtest Lab):** Cho phép người dùng chạy kiểm thử lại thuật toán SMC trên dữ liệu lịch sử nạp từ DB, hiển thị bảng số liệu thống kê và biểu đồ đường cong vốn (Equity Curve).

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC (DECISION LOG D12–D17)

| ID | Quyết định Kiến trúc | Trạng thái | Tác động Kỹ thuật |
| :--- | :--- | :---: | :--- |
| **D12** | **Xây dựng `SignalEngineWorker` kích hoạt theo sự kiện nến M15 hoàn tất (Bar Close Trigger)** | `ACCEPTED` | Không quét tín hiệu theo từng tick (tránh lãng phí CPU). Chỉ đánh giá tín hiệu khi nến M15 đóng cửa (`kline.is_closed == True` hoặc phát hiện nến M15 mới) và đang nằm trong Kill Zone. |
| **D13** | **Lưu cấu hình hệ thống giao dịch & Chế độ Auto-Trade vào PostgreSQL `system_trading_config`** | `ACCEPTED` | Cho phép cấu hình linh hoạt (tỷ lệ rủi ro %, ngưỡng BE, bật/tắt Auto-Trade, news buffer phút). Lưu DB kèm bộ đệm cache bộ nhớ/Redis giúp duy trì trạng thái khi khởi động lại container backend. |
| **D14** | **Mở rộng Schema Additive qua Migration `0004_phase2_sprint3.sql`** | `ACCEPTED` | Tạo bảng mới `strategy_signals` (lưu trữ tín hiệu, trạng thái, lý do hủy). Tạo bảng `system_trading_config`. Bổ sung cột `parent_ticket_id`, `is_breakeven_moved`, `is_partial_closed`, `trailing_stop_price` vào `simulated_orders`. Không làm thay đổi schema cũ. |
| **D15** | **Xử lý Partial Take Profit bằng cơ chế Phân tách Lệnh (Order Splitting)** | `ACCEPTED` | Khi chạm TP1, hệ thống thực hiện: Đóng 50% khối lượng ban đầu với lý do `PARTIAL_TP1`, cập nhật `realized_pnl` cho nửa lot đó; cập nhật vị thế còn lại với `lot_size = lot_size * 0.5`, chuyển `stop_loss = entry` (BE) và gắn cờ `is_partial_closed = True`. |
| **D16** | **Tái sử dụng WebSocket Multiplexing Hub (`/api/v1/ws/market`) với Event Type Mới** | `ACCEPTED` | Không mở thêm port hoặc endpoint WebSocket mới. Sử dụng Redis channel `market:signals` để phát `type: "signal.new"`, và `market:circuit_breaker` để phát `type: "circuit_breaker.update"`. WebSocket hub tự động chuyển tiếp đến client. |
| **D17** | **Động cơ Bù đắp Khoảng trống Nến Tự động (`CandleGapHealer` & `CandleIntegrityWorker`)** | `ACCEPTED` | Tự động phát hiện và vá khoảng trống nến lịch sử do server downtime khi chạy local (tắt máy, mất mạng). Tự động chạy ngay khi restart và định kỳ mỗi 60s, bù nến từ Binance REST API cho cả 6 khung thời gian (M1 đến D1). |
| **D18** | **Phân lập Dữ liệu Kiểm thử & Cơ chế Tự động Dọn dẹp với Cờ `is_test` (Test Data Isolation & Auto-Cleanup)** | `ACCEPTED` | Bổ sung cột `is_test BOOLEAN NOT NULL DEFAULT FALSE` vào `simulated_orders` và `strategy_signals`. Tất cả các kịch bản test ghi dữ liệu bắt buộc gắn `is_test = True`. Tự động dọn dẹp sạch toàn bộ dữ liệu test sau mỗi lần chạy test qua autouse fixture (`conftest.py`), khôi phục số dư tài khoản về $10,000.00, loại bỏ hoàn toàn tình trạng rác test làm sai lệch tab Orders History và số dư thật. |

---

## 3. KIẾN TRÚC TỔNG THỂ & LUỒNG DỮ LIỆU

```mermaid
flowchart TB
    subgraph Data_Flow["1. Luồng Dữ Liệu Thời Gian Thực"]
        BinanceWS["Binance WebSocket (PAXGUSDT)"]
        Streamer["ChartStreamer & CandleAggregator"]
        BinanceWS --> Streamer
        Streamer -->|Tick / Candle M1..D1| RedisTicks[("Redis: market:ticks")]
        Streamer -->|M15 Bar Closed Event| SignalWorker
    end

    subgraph Signal_Generation["2. Động cơ Phân tích & Sinh Tín hiệu"]
        SignalWorker["SignalEngineWorker<br/>(ai_engine/signal_worker.py)"]
        SMCLib["SMC Engine (smc.py)<br/>- D1/H4 HTF Bias<br/>- H1 Dealing Range & POI<br/>- M15 CHoCH Trigger"]
        NewsGuard["Macro News Circuit Breaker<br/>(economic_events check)"]
        SignalWorker --> SMCLib
        SignalWorker --> NewsGuard
        SignalWorker -->|Signal Created| DB_Signals[("DB: strategy_signals")]
        SignalWorker -->|Publish 'market:signals'| RedisSignals[("Redis: market:signals")]
    end

    subgraph Auto_Execution["3. Bộ Điều Phối & Khớp Lệnh"]
        ExecController["AutoExecutionController<br/>(simulation/auto_executor.py)"]
        Config["System Config<br/>(MANUAL / SEMI / FULL_AUTO)"]
        PaperWorker["PaperEngineWorker<br/>(simulation/paper_worker.py)"]
        
        RedisSignals --> ExecController
        Config --> ExecController
        NewsGuard -.->|Block if Circuit Active| ExecController
        ExecController -->|If FULL_AUTO: open_order()| PaperWorker
    end

    subgraph Position_Management["4. Quản Trị Vị Thế Nâng Cao (Tick-by-Tick)"]
        RedisTicks --> PaperWorker
        PaperWorker --> TickRules{"Quét từng Tick"}
        TickRules -->|Unrealized R >= 1.5R| BEMove["Dời SL về Breakeven (Entry)"]
        TickRules -->|Price >= TP1 (2R)| PartialClose["Chốt lời 50% Lot & Dời SL về BE"]
        TickRules -->|Price >= TP2 / SL Hit| FullClose["Đóng toàn bộ vị thế & Tính PnL"]
        PaperWorker -->|Publish 'paper:orders'| RedisOrders[("Redis: paper:orders")]
    end

    subgraph Frontend_Cockpit["5. Giao Diện Người Dùng (Trading Cockpit)"]
        WSHub["FastAPI WebSocket Hub<br/>(/api/v1/ws/market)"]
        RedisTicks & RedisSignals & RedisOrders --> WSHub
        WSHub --> ClientUI["Vue 3 Frontend<br/>- Cockpit Auto-Trade Switcher<br/>- Signal Audio Alert & Confirm Modal<br/>- Orders Table with BE/Partial Badges<br/>- Backtesting Lab View"]
    end
```

### 3.1. Cơ chế Tự động Bù đắp Khoảng trống Nến do Server Downtime (Candle Gap Healing Engine)
Do hệ thống vận hành tại máy cục bộ (local host), các sự cố tắt máy, gập máy, mất kết nối mạng hoặc khởi động lại container thường tạo ra các khoảng trống thời gian (gaps) từ hàng chục phút đến nhiều ngày trong chuỗi nến lịch sử. Module `CandleGapHealer` (`backend/data_ingestion/candle_healer.py`) giải quyết triệt để vấn đề này:

1. **Thuật toán Phát hiện Khoảng trống (`detect_gaps`):**
   * **Trailing/Head Gap:** Khoảng trống từ thời điểm nến mới nhất trong DB đến thời điểm hiện tại `now` ($> 1.5 \times \text{Interval}$).
   * **Internal Gaps:** Quét toàn bộ các đoạn đứt gãy giữa 2 nến liên tiếp trong 7 ngày gần nhất ($\Delta t > 1.5 \times \text{Interval}$).
   * **Leading Gap:** Bổ sung nếu số lượng nến lịch sử chưa đạt mức tối thiểu (300 nến).
2. **Cơ chế Bù đắp Nến Phân trang (`heal_range`):**
   * Tự động ánh xạ `XAUUSD` sang `PAXGUSDT` (nguồn Binance giao dịch 24/7 không nghỉ cuối tuần).
   * Phân trang gọi Binance REST API `https://api.binance.com/api/v3/klines` với `limit=1000`, liên tục nạp và ghi đè an toàn qua `ON CONFLICT (symbol, timeframe, open_time) DO UPDATE`.
   * Hỗ trợ đồng bộ chuẩn xác cho cả 6 khung thời gian: `M1`, `M5`, `M15`, `H1`, `H4`, `D1`.
3. **Cơ chế Kích hoạt Kép (Dual Triggering):**
   * **Khi Khởi động lại (Startup Recovery):** Chạy ngay lập tức khi ứng dụng khởi động trong lifespan của FastAPI, phục hồi toàn bộ nến bị mất trong suốt thời gian server tắt.
   * **Định kỳ Chạy ngầm (`CandleIntegrityWorker`):** Chạy ngầm mỗi 60 giây, tự động phát hiện nếu WebSocket bị nghẽn mạng hoặc trễ nến để tự động kích hoạt bù đắp tức thì.
   * **On-Demand API:** Hỗ trợ `GET /api/v1/market/integrity` và `POST /api/v1/market/heal` cho phép giao diện Settings kiểm tra và kích hoạt vá nến thủ công.

---

## 4. ĐỘNG CƠ TỰ ĐỘNG KÍCH HOẠT TÍN HIỆU (AUTONOMOUS SIGNAL ENGINE)

Module `SignalEngineWorker` (`backend/ai_engine/signal_worker.py`) chạy dưới dạng background task độc lập trong FastAPI lifespan.

### 4.1. Điều kiện Kích hoạt Đánh giá (Evaluation Trigger)
Để đảm bảo tín hiệu hoàn toàn không có độ trễ và không bị vẽ lại nến (repainting):
1. **Chu kỳ kích hoạt:** Kích hoạt ngay khi một cây nến **M15** hoàn tất đóng cửa (nghĩa là timestamp chuyển sang thanh nến mới) hoặc nhận được payload nến M15 đóng từ `ChartStreamer`.
2. **Kiểm tra phiên giao dịch:**
   * Sử dụng hàm `sessions.in_kill_zone(now, cfg["kill_zones"])`.
   * Nếu hiện tại **không nằm trong bất kỳ Kill Zone nào** (London, NY AM, NY PM) $\implies$ Bỏ qua, ghi nhận trạng thái `OFF_SESSION`.

### 4.2. Quy trình Đánh giá Đa khung thời gian (3-Tier Evaluation Pipeline)
Worker nạp tối thiểu số lượng nến đã đóng từ PostgreSQL:
* `D1`: 30 nến gần nhất
* `H4`: 40 nến gần nhất
* `H1`: 60 nến gần nhất
* `M15`: 60 nến gần nhất

Quy trình logic thực thi:
1. **Bước 1 (HTF Bias):** Gọi `smc.market_structure()` trên D1 và H4. Xác nhận đồng thuận:
   * Nếu cả D1 và H4 đều là TĂNG $\implies \text{Bias} = +1$ (BULLISH).
   * Nếu cả D1 và H4 đều là GIẢM $\implies \text{Bias} = -1$ (BEARISH).
   * Nếu xung đột xu hướng $\implies \text{Bias} = 0 \implies$ Đứng ngoài, không sinh tín hiệu.
2. **Bước 2 (POI Selection trong Dealing Range H1):**
   * Xác định 50% Equilibrium của H1: $\text{Eq} = \frac{High + Low}{2}$.
   * Nếu $\text{Bias} = +1$: Chỉ lọc các Order Block (OB) hoặc Fair Value Gap (FVG) nằm ở vùng **Discount** ($Mid < Eq$).
   * Nếu $\text{Bias} = -1$: Chỉ lọc các OB hoặc FVG nằm ở vùng **Premium** ($Mid > Eq$).
3. **Bước 3 (M15 Tap & CHoCH Trigger):**
   * Kiểm tra nến M15 trong 5 nến gần nhất đã chạm vào vùng biên của POI H1 (`tap POI`).
   * Cây nến M15 vừa đóng cửa phải tạo **Change of Character (CHoCH)** theo đúng hướng Bias.
4. **Bước 4 (Tính toán Tỷ lệ Rủi ro & Mục tiêu):**
   * $Entry = Close$ của nến M15 vừa đóng.
   * Stop Loss ($SL$): Cạnh xa nhất của POI hoặc Swing Low/High M15 gần nhất trừ/cộng thêm khoảng đệm $0.5 \times ATR(15)$.
   * Take Profit 1 ($TP_1$): Đạt mức tối thiểu $1:2.0R$ ($Entry + 2.0 \times |Entry - SL|$ đối với BUY).
   * Take Profit 2 ($TP_2$): Đỉnh/Đáy thanh khoản Swing H1 đối diện (tối thiểu $\ge 1:3.0R$).
   * Nếu $R:R < 1:2.0 \implies$ Loại bỏ setup vi phạm tiêu chuẩn quản trị rủi ro.

---

## 5. BỘ NGẮT MẠCH TIN TỨC ĐỎ VĨ MÔ (MACRO NEWS CIRCUIT BREAKER)

Module `NewsCircuitBreaker` (`backend/ai_engine/news_guard.py`) bảo vệ hệ thống khỏi các đợt biến động bất thường do tin tức vĩ mô.

### 5.1. Cơ chế Hoạt động & Cấu hình Thời gian
* Trước khi một tín hiệu được phê duyệt vào lệnh, worker truy vấn bảng `economic_events` trong cơ sở dữ liệu:
  $$\text{Query: } \text{impact\_stars} = 3 \quad \text{AND} \quad \text{currency} = \text{'USD'} \quad \text{AND} \quad |\text{event\_timestamp} - \text{now}| \le \text{buffer\_minutes}$$
* **Thông số bộ đệm (Configurable Buffer):**
  * Mặc định: **Trước 30 phút** và **Sau 30 phút** của giờ công bố tin tức 3 sao (ví dụ: Non-Farm Payrolls, Core CPI, FOMC Rate Decision, GDP Advance).
* **Xử lý khi Circuit Breaker kích hoạt:**
  * Trạng thái hệ thống chuyển sang `CIRCUIT_BREAKER_ACTIVE`.
  * Mọi tín hiệu mới phát sinh trong khoảng thời gian này tự động gán trạng thái `INVALIDATED` với lý do: `"CIRCUIT_BREAKER: HIGH_IMPACT_NEWS_IMMIMENT"`.
  * Phát event `circuit_breaker.update` ra Redis để hiển thị cảnh báo đỏ trên UI Cockpit.

### 5.2. Động cơ Phân tích Cảm xúc Tin tức & Bối cảnh AI (News Sentiment & AI Context Engine)
* **Module:** `backend/ai_engine/sentiment.py`
* **Mục tiêu:** Tự động tính toán điểm tác động tin tức tài chính và kinh tế vĩ mô đối với cặp tỷ giá **XAUUSD (Vàng)**:
  $$\text{Sentiment Score} \in [-1.0, +1.0] \quad (\text{Bearish} \rightarrow \text{Neutral} \rightarrow \text{Bullish})$$
* **Cơ chế Phân loại & Chấm điểm:**
  * **Trường phái Tác động Trực tiếp tới Vàng:**
    * Tăng giá (Bullish $\ge +0.15$): Bứt phá giá, lực mua hồi phục (short covering), nhu cầu trú ẩn an toàn (safe haven demand), rủi ro địa chính trị, kỳ vọng cắt giảm lãi suất Fed, USD và lợi suất trái phiếu suy yếu.
    * Giảm giá (Bearish $\le -0.15$): Áp lực bán chốt lời, phá vỡ ngưỡng hỗ trợ, đà tăng mạnh của chỉ số USD và lợi suất trái phiếu, lãi suất duy trì mức cao (higher-for-longer).
    * Trung lập (Neutral $-0.15 < \text{Score} < +0.15$): Dữ liệu thị trường cân bằng hoặc thông tin thông lệ không tạo xu hướng một chiều.
  * **Phân cấp Rủi ro Biến động (Volatility Impact):**
    * `HIGH_RISK_HALT`: Tin tức 3 sao, biên độ cảm xúc mạnh ($|\text{Score}| \ge 0.70$), hoặc xuất hiện từ khóa đặc biệt (CPI, NFP, FOMC, chiến sự).
    * `MEDIUM`: Tin tức 2 sao hoặc điểm cảm xúc từ $0.25$ đến $0.70$.
    * `LOW`: Tin tức 1 sao hoặc thông tin thường lệ.
* **Tích hợp Ingestion & Đồng bộ Cơ sở Dữ liệu:**
  * `NewsCollector` (`backend/data_ingestion/news_worker.py`) tự động chấm điểm `sentiment_score` và sinh `ai_analysis_summary` ngay khi tiếp nhận tin mới từ RSS (Kitco, FXStreet) và Finnhub.
  * Tự động quét và nạp bổ sung (backfill) toàn bộ dữ liệu lịch sử chưa có điểm số trong DB khi khởi động hệ thống.
  * Cung cấp API `GET /api/v1/news/sentiment` trả về tổng hợp điểm số, tỷ lệ Bullish/Bearish/Neutral và endpoint `POST /api/v1/news/analyze` kích hoạt phân tích theo yêu cầu.
* **Giao diện Cockpit (`SentimentGauge.vue` & `NewsEventsView.vue`):**
  * Kim đồng hồ đo động (Animated Pointer) hiển thị trực quan tỷ lệ cảm xúc từ -1.0 đến +1.0 kèm vạch chuẩn Neutral 0.00.
  * Huy hiệu trạng thái động: `BULLISH` (xanh), `BEARISH` (đỏ), `NEUTRAL` (xám).
  * Bộ đếm phân loại số lượng tin tức tích cực, trung tính và tiêu cực.
  * Thẻ tin tức hiển thị chỉ báo xu hướng (`TrendingUp`, `TrendingDown`, `Minus`) cùng hộp thông tin chi tiết `AI INSIGHT`.

---

## 6. QUẢN TRỊ VỊ THẾ ĐỘNG NÂNG CAO (DYNAMIC POSITION MANAGEMENT)

Mở rộng `PaperEngine` (`simulation/paper_engine.py`) và `PaperEngineWorker` (`simulation/paper_worker.py`) để giám sát các điều kiện chốt lời và bảo vệ vốn tự động từng tick:

### 6.1. Tự động Dời Stop Loss về Hòa Vốn (Break-Even Move)
* **Điều kiện:**
  * Lệnh BUY: $\text{Bid} \ge \text{Entry} + 1.5 \times (\text{Entry} - \text{Stop Loss})$
  * Lệnh SELL: $\text{Ask} \le \text{Entry} - 1.5 \times (\text{Stop Loss} - \text{Entry})$
* **Hành động:**
  * Tự động điều chỉnh: $\text{Stop Loss} \leftarrow \text{Entry} \pm 0.10$ (bù trừ thêm phí/spread tượng trưng).
  * Đánh dấu cờ `is_breakeven_moved = True`.
  * Ghi nhật ký vào database và phát event `order.update` cập nhật SL mới lên biểu đồ TradingView.

### 6.2. Chốt Lời Từng Phần 50% (Partial Take Profit at TP1)
* **Điều kiện:** Giá thị trường chạm mốc $TP_1$ (tương đương tỷ lệ $1:2R$).
* **Quy trình Phân tách Lệnh (Order Splitting Logic):**
  1. Khối lượng đóng: $\text{Lots}_{\text{closed}} = \frac{\text{Lots}_{\text{current}}}{2}$
  2. Tính lợi nhuận chốt lời cho nửa lot:
     $$\text{Partial PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Direction} \times \text{Lots}_{\text{closed}} \times 100$$
  3. Cộng $\text{Partial PnL}$ vào `current_balance` của tài khoản `SimulationAccount`.
  4. Cập nhật vị thế hiện tại:
     * $\text{Lots} \leftarrow \text{Lots} - \text{Lots}_{\text{closed}}$
     * $\text{Stop Loss} \leftarrow \text{Entry}$ (Bảo đảm không thể lỗ cho phần vị thế còn lại).
     * $\text{Take Profit} \leftarrow TP_2$ (Mục tiêu đỉnh Swing H1).
     * Đánh dấu `is_partial_closed = True`.
  5. Tạo một bản ghi đóng lệnh phụ trong DB lưu vết lịch sử partial đóng kèm `close_reason = "PARTIAL_TP1"`.

### 6.3. Trailing Stop Loss theo ATR (Tùy chọn Bật/Tắt)
* Khi giá tiếp tục di chuyển vượt qua $TP_1$, hệ thống có thể kích hoạt trailing:
  * Lệnh BUY: $\text{New SL} = \max(\text{Current SL}, \text{Bid} - 1.5 \times \text{ATR}(15))$.
  * Ngăn ngừa việc lùi SL về vùng rủi ro hơn (chỉ dịch chuyển theo chiều nâng cao lợi nhuận).

---

## 7. HỢP ĐỒNG API & WEBSOCKET (API & WEBSOCKET CONTRACTS)

### 7.1. REST Endpoints Mới & Nâng cấp (Base: `/api/v1/strategy`)

| Phương thức | Endpoint | Tham số | Chức năng |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/strategy/signals` | `limit` (int, default 50), `status` (optional) | Lấy danh sách tín hiệu SMC được sinh ra gần nhất kèm trạng thái. |
| `POST` | `/api/v1/strategy/signals/evaluate` | `symbol` (str, default "XAUUSD") | Kích hoạt thủ công quá trình quét nến và sinh tín hiệu tức thì. |
| `POST` | `/api/v1/strategy/signals/{id}/execute` | Không | Trader duyệt thủ công vào lệnh từ tín hiệu (dùng cho chế độ MANUAL). |
| `GET` | `/api/v1/strategy/config` | Không | Lấy cấu hình giao dịch hệ thống (chế độ Auto, Risk %, BE %, News buffer). |
| `PUT` | `/api/v1/strategy/config` | JSON Payload | Cập nhật cấu hình giao dịch và công tắc Auto-Trading. |
| `POST` | `/api/v1/strategy/backtest` | JSON: `start_date`, `end_date`, `symbol`, `risk_pct` | Chạy kiểm thử lại chiến lược trên dữ liệu lịch sử nến và trả về báo cáo PnL. |

### 7.2. Hợp đồng JSON Payload

#### 1. Payload Cấu hình Giao dịch (`PUT /api/v1/strategy/config`)
```json
{
  "execution_mode": "FULL_AUTO",
  "risk_per_trade_percent": 1.0,
  "breakeven_r_multiple": 1.5,
  "enable_partial_tp": true,
  "partial_tp_ratio": 0.5,
  "partial_tp_r_multiple": 2.0,
  "news_circuit_breaker_enabled": true,
  "news_circuit_breaker_buffer_mins": 30,
  "max_open_positions": 2
}
```

#### 2. Payload Kết quả Tín hiệu (`strategy_signals`)
```json
{
  "id": 84,
  "symbol": "XAUUSD",
  "side": "BUY",
  "generated_at": "2026-10-08T14:45:00Z",
  "session": "London Kill Zone",
  "entry_price": 2682.50,
  "stop_loss": 2677.00,
  "take_profit_1": 2693.50,
  "take_profit_2": 2704.00,
  "risk_reward_1": 2.0,
  "risk_reward_2": 3.9,
  "status": "EXECUTED",
  "reason": "long | D1/H4 bias | H1 OB [2678.00-2681.50] | M15 CHoCH | London KZ",
  "executed_order_id": 142
}
```

### 7.3. WebSocket Multiplexing Event Mới (`/api/v1/ws/market`)

#### Frame Tín hiệu Mới (`type: "signal.new"`)
```json
{
  "type": "signal.new",
  "data": {
    "id": 84,
    "symbol": "XAUUSD",
    "side": "BUY",
    "entry_price": 2682.50,
    "stop_loss": 2677.00,
    "take_profit": 2693.50,
    "risk_reward": "1:2.0",
    "status": "WAITING_EXECUTION",
    "reason": "D1/H4 Bullish Bias + H1 POI Discount + M15 CHoCH",
    "timestamp": 1774972800
  }
}
```

#### Frame Cảnh báo Ngắt mạch Tin tức (`type: "circuit_breaker.update"`)
```json
{
  "type": "circuit_breaker.update",
  "active": true,
  "event_title": "US Non-Farm Payrolls",
  "event_time": "2026-10-08T12:30:00Z",
  "time_remaining_minutes": 15,
  "message": "Circuit Breaker kích hoạt: Tạm dừng tự động mở lệnh trong 30 phút."
}
```

---

## 8. MÔ HÌNH DỮ LIỆU & MIGRATION ADDITIVE (`0004_phase2_sprint3.sql`)

Migration mới hoàn toàn **additive**, tuyệt đối không thay đổi hay xóa các bảng/cột đã có từ Phase 1 và Sprint 1–2.

```sql
-- Migration: 0004_phase2_sprint3.sql

-- 1. Bảng lưu trữ cấu hình giao dịch hệ thống
CREATE TABLE IF NOT EXISTS system_trading_config (
    id INT PRIMARY KEY DEFAULT 1,
    execution_mode VARCHAR(16) NOT NULL DEFAULT 'MANUAL', -- 'MANUAL', 'SEMI_AUTO', 'FULL_AUTO'
    risk_per_trade_percent NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
    breakeven_r_multiple NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    enable_partial_tp BOOLEAN NOT NULL DEFAULT TRUE,
    partial_tp_ratio NUMERIC(4, 2) NOT NULL DEFAULT 0.50,
    partial_tp_r_multiple NUMERIC(4, 2) NOT NULL DEFAULT 2.00,
    news_circuit_breaker_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    news_circuit_breaker_buffer_mins INT NOT NULL DEFAULT 30,
    max_open_positions INT NOT NULL DEFAULT 2,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO system_trading_config (id, execution_mode)
VALUES (1, 'MANUAL')
ON CONFLICT (id) DO NOTHING;

-- 2. Bảng lưu trữ tín hiệu giao dịch SMC tự động
CREATE TABLE IF NOT EXISTS strategy_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    side VARCHAR(8) NOT NULL, -- 'BUY', 'SELL'
    generated_at TIMESTAMPTZ NOT NULL,
    session_name VARCHAR(64) NOT NULL,
    entry_price NUMERIC(12, 4) NOT NULL,
    stop_loss NUMERIC(12, 4) NOT NULL,
    take_profit_1 NUMERIC(12, 4) NOT NULL,
    take_profit_2 NUMERIC(12, 4),
    risk_reward NUMERIC(6, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'EXECUTED', 'INVALIDATED', 'EXPIRED'
    invalidated_reason TEXT,
    reason TEXT NOT NULL,
    executed_order_id BIGINT REFERENCES simulated_orders(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_signals_status ON strategy_signals(status);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_generated_at ON strategy_signals(generated_at DESC);

-- 3. Mở rộng bảng simulated_orders hỗ trợ quản trị vị thế nâng cao
ALTER TABLE simulated_orders
    ADD COLUMN IF NOT EXISTS parent_ticket_id BIGINT,
    ADD COLUMN IF NOT EXISTS is_breakeven_moved BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_partial_closed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS trailing_stop_price NUMERIC(12, 4);
```

---

## 9. KIẾN TRÚC FRONTEND & MÀN HÌNH BACKTESTING LAB

### 9.1. Nâng cấp Trading Cockpit
1. **Thanh Header & Ribbon Điều khiển Auto-Trade:**
   * Bổ sung cụm điều khiển: `[ Chế độ: MANUAL | SEMI | AUTO ]` kèm đèn tín hiệu xanh/vàng/xám.
   * Cảnh báo `[ CIRCUIT BREAKER ACTIVE ]` nhấp nháy đỏ khi sắp có tin 3 sao.
2. **Khối Market Analysis Status (`MarketAnalysisStatus.vue`):**
   * Chuyển trạng thái thẻ Predicted Setup từ tĩnh `WAITING_TRIGGER` sang động:
     * `ACTIVE SIGNAL FOUND`: Hiển thị nút bấm nổi bật `[ Xác nhận mở lệnh ngay ]` (ở chế độ Manual).
     * `AUTO-EXECUTING IN 5s...`: Thanh đếm ngược tiến trình (ở chế độ Semi-Auto).
     * `EXECUTED #1042`: Liên kết trực tiếp sang bảng Order Book.
3. **Âm thanh Cảnh báo (Audio Alert Sound):**
   * Sử dụng Web Audio API (âm báo ding-dong nhẹ nhàng) khi nhận được frame `signal.new` mà không cần phụ thuộc vào file MP3 bên ngoài.
4. **Bảng Lệnh Mở (`OrderBookTable.vue`):**
   * Bổ sung các badge trực quan trên từng dòng lệnh:
     * `[BE Protected]`: Khi SL đã được tự động dời về hòa vốn.
     * `[50% TP1 Banked]`: Khi nửa lot đã được chốt lời tại TP1.

### 9.2. Màn hình Trung tâm Backtest Lab (`BacktestLabView.vue`)
Bổ sung một công cụ kiểm thử chiến lược trực quan:
* Bộ chọn tham số: Khung thời gian test (M15, H1), Khoảng ngày kiểm thử (1 tuần, 1 tháng, 3 tháng), Tỷ lệ rủi ro (0.5% - 2.0%).
* Thẻ tóm tắt kết quả:
  * **Win Rate %** (Tỷ lệ thắng)
  * **Profit Factor** (Hệ số lợi nhuận / thua lỗ)
  * **Net Profit ($ & %)**
  * **Max Drawdown %** (Mức sụt giảm tài khoản lớn nhất)
  * **Total Trades** (Tổng số lệnh thực thi)
* Biểu đồ đường cong tài khoản (Equity Curve) tích hợp vẽ canvas nhẹ nhàng so sánh số dư tăng trưởng qua từng giao dịch.
* Danh sách chi tiết từng trade lịch sử trong backtest kèm lý do vào lệnh SMC.

---

## 10. KẾ HOẠCH TRIỂN KHAI THEO TASK (TASK BREAKDOWN T3.1–T3.7)

| Mã Task | Phân tầng | Nội dung Triển khai Cụ thể | Kết quả Bàn giao (Deliverables) | Phụ thuộc |
| :--- | :--- | :--- | :--- | :--- |
| **T3.1** | **Database & Models** | Viết file migration SQL `0004_phase2_sprint3.sql` và khai báo các model SQLAlchemy: `StrategySignal`, `SystemTradingConfig`, mở rộng `SimulatedOrder`. | `backend/migrations/0004_phase2_sprint3.sql`, `backend/core/models.py` | Không |
| **T3.2** | **News Guard & Circuit Breaker** | Cài đặt `NewsCircuitBreaker` kiểm tra lịch tin tức 3 sao USD trong $\pm 30$ phút, phát event `circuit_breaker.update` ra Redis. | `backend/ai_engine/news_guard.py`, `backend/tests/test_news_guard.py` | T3.1 |
| **T3.3** | **Signal Engine Worker** | Xây dựng `SignalEngineWorker` chạy nền kiểm tra nến M15 đóng, gọi pipeline SMC, đối chiếu Circuit Breaker, lưu `strategy_signals` và phát `signal.new`. | `backend/ai_engine/signal_worker.py`, `backend/tests/test_signal_worker.py` | T3.1, T3.2 |
| **T3.4** | **Dynamic Position Mgmt & Auto-Executor** | Cài đặt logic Break-Even Move và Partial TP 50% trong `PaperEngine` và `PaperEngineWorker`. Xây dựng `AutoExecutionController` mở lệnh khi ở chế độ `FULL_AUTO`. | `backend/simulation/paper_engine.py`, `backend/simulation/paper_worker.py`, `backend/simulation/auto_executor.py` | T3.1, T3.3 |
| **T3.5** | **API Routers & Config Controller** | Bổ sung các endpoints `/api/v1/strategy/signals`, `/config`, `/evaluate`, `/execute`, kết nối Redis Pub/Sub channels vào WebSocket hub. | `backend/api/v1/strategy.py`, `backend/main.py` | T3.3, T3.4 |
| **T3.6** | **Frontend Cockpit & Backtest Lab** | Nâng cấp Header với nút Auto-Trade, tích hợp Audio Alert, popup xác nhận lệnh, badge BE/Partial trên Orders Table, và xây dựng màn hình Backtesting Lab. | `frontend/src/components/Simulation/MarketAnalysisStatus.vue`, `BacktestLabView.vue`, `orderStore.js` | T3.5 |
| **T3.7** | **Test Data Isolation & Auto-Cleanup** | Thêm cờ `is_test` cho `simulated_orders` & `strategy_signals`, lọc `include_test=False` trên API, xây dựng autouse cleanup fixture trong `conftest.py`, dọn dẹp sạch toàn bộ 53 demo orders cũ và reset tài khoản về ban đầu $10,000. | `backend/tests/conftest.py`, `backend/tests/test_test_data_isolation.py`, `backend/core/models.py`, `backend/api/v1/orders.py` | T3.1, T3.4 |

---

## 11. KIỂM THỬ, SLO & TIÊU CHUẨN NGHIỆM THU (DoD)

### 11.1. Ma trận Kiểm thử Bắt buộc (Test Matrix)
1. **Signal Generation Accuracy:** Kiểm tra chuỗi nến lịch sử có setup hợp lệ (D1 Bullish + H1 Discount OB + M15 CHoCH), xác minh worker sinh đúng tín hiệu `BUY` với $R:R \ge 1:2.0$.
2. **Circuit Breaker Block:** Giả lập sự kiện tin tức Non-Farm trong 15 phút tới; xác minh tín hiệu phát sinh bị chuyển sang trạng thái `INVALIDATED` và Auto-Executor từ chối mở lệnh.
3. **Break-Even Move Trigger:** Khởi tạo lệnh BUY với Entry 2680, SL 2670 ($1R = 10$). Khi tick giá chạm 2695 ($+1.5R$), xác minh Stop Loss tự động cập nhật lên 2680.10 và gắn cờ `is_breakeven_moved = True`.
4. **Partial Take Profit Trigger:** Khởi tạo lệnh 0.20 lots. Khi giá chạm TP1 ($+2R$), xác minh 0.10 lots được đóng và ghi nhận lợi nhuận, 0.10 lots còn lại tiếp tục chạy với SL tại BE.
5. **Backtest Determinism:** Chạy thuật toán backtest 2 lần trên cùng một tập dữ liệu nến; xác minh kết quả Win Rate, Max Drawdown và Net PnL hoàn toàn trùng khớp (100% deterministic).
6. **Test Data Isolation & Auto-Cleanup:** Kiểm tra việc tạo lệnh với `is_test=True` không xuất hiện trên API real-time `/api/v1/orders` và tự động biến mất hoàn toàn khỏi PostgreSQL sau khi test suite hoàn tất.

### 11.2. Tiêu chuẩn SLO (Service Level Objectives)
* **Thời gian xử lý tín hiệu (Signal Latency):** Từ khi nến M15 đóng đến khi tín hiệu được lưu DB và bắn lên WebSocket: **$\le 150 \text{ ms}$**.
* **Độ trễ kích hoạt Break-Even / Partial TP:** Từ khi tick giá chạm mốc $1.5R$ hoặc $2R$ đến khi lệnh cập nhật trong bộ nhớ: **$\le 20 \text{ ms}$**.
* **Thời gian hoàn tất Backtest:** Backtest trên 2,000 nến hoàn thành trong **$\le 1.5 \text{ giây}$**.

### 11.3. Tiêu chí Hoàn thành Sprint (Definition of Done - DoD)
* [x] Background worker `SignalEngineWorker` chạy ổn định trong backend, không gây crash hoặc nghẽn event loop.
* [x] Khi có tín hiệu nến M15 mới thỏa mãn SMC, giao diện nhận được thông báo ngay lập tức và phát âm thanh alert.
* [x] Bật chế độ `FULL_AUTO`: Khi có tín hiệu, hệ thống tự động mở lệnh trong Paper Positions với khối lượng chuẩn theo 1% rủi ro tài khoản.
* [x] Khi giá chạy được $+1.5R$: Đường Stop Loss trên biểu đồ TradingView tự động nhảy về giá Entry (Break-Even) mà không cần can thiệp thủ công.
* [x] Khi giá chạm $TP_1$: Nửa khối lượng được chốt lãi, tài khoản cộng thêm PnL và vị thế còn lại tiếp tục chạy đến $TP_2$.
* [x] Khi có tin đỏ 3 sao sắp công bố: Banner Circuit Breaker cảnh báo đỏ trên Header và hệ thống không cho phép mở lệnh mới.
* [x] Toàn bộ bộ test suite backend đạt **$\ge 45$ tests passed** (thực tế đạt 54/54 tests passed).
* [x] Frontend build `npm run build` thành công, không có bất kỳ warning nghiêm trọng hay lỗi component.
* [x] Phân lập triệt để dữ liệu test với cờ `is_test`, tự động xóa sạch sau mỗi lần chạy test (`conftest.py`); Orders History không còn bị ô nhiễm bởi dữ liệu demo/test.
