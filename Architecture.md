# KIẾN TRÚC DỰ ÁN: NỀN TẢNG PHÂN TÍCH & GIAO DỊCH TỰ ĐỘNG (XAU / FOREX / CRYPTO)
## Giai đoạn 1: UI/UX, Data Pipeline & Giả lập Thực thi (Paper Trading Engine)

---

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

Giai đoạn 1 tập trung xây dựng nền tảng thu thập dữ liệu thời gian thực (Multi-asset Data Stream), kết nối Broker MT5, tích hợp trí tuệ nhân tạo (AI) để phân tích bối cảnh thị trường/tin tức, và cung cấp giao diện trực quan hóa dữ liệu (TradingView Charts) kèm động cơ giả lập lệnh (Paper Trading) trên dữ liệu thực tế.

```
+---------------------------------------------------------------------------------------------------+
|                                      FRONTEND (SPA / Vue 3)                                       |
|  +------------------------------+  +-------------------------------+  +------------------------+  |
|  | TradingView Lightweight Chart|  | Real-time Financial News Feed |  | AI Insights & Strategy |  |
|  | (Candlesticks, Orders, SL/TP)|  | & Sentiment Indicator Box     |  | Optimization Panel     |  |
|  +------------------------------+  +-------------------------------+  +------------------------+  |
|  +---------------------------------------------------------------------------------------------+  |
|  | Simulation Cockpit: Live PnL, Order Book, Position Logs, Winrate & Risk Metrics             |  |
|  +---------------------------------------------------------------------------------------------+  |
+--------------------------------------------------▲------------------------------------------------+
                                                   │ WebSocket / REST API
+--------------------------------------------------▼------------------------------------------------+
|                                    BACKEND CORE (FastAPI Monolith)                                |
|                                                                                                   |
|  +----------------------+  +---------------------+  +--------------------+  +------------------+  |
|  |  Data Ingestion Hub  |  |  AI Strategy Engine |  | Paper Execution Eng|  | Telemetry & Log  |  |
|  |  - WebSocket Feeder  |  |  - RAG / Knowledge  |  | - Virtual Fill Sim |  | - PnL Tracking   |  |
|  |  - News Aggregator   |  |  - LLM Strategy Opt |  | - SL/TP Dynamic Mon|  | - Trade Journal  |  |
|  |  - MT5 Tick Bridge   |  |  - Sentiment Score  |  | - Spread & Latency |  | - Performance    |  |
|  +----------▲-----------+  +----------▲----------+  +---------▲----------+  +--------▲---------+  |
+-------------│-------------------------│-----------------------│----------------------│------------+
              │                         │                       │                      │
+-------------▼-------------------------▼-----------------------▼----------------------▼------------+
|                                      DATA & BROKER LAYER                                          |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
|  | Market Data Providers |  | Financial News APIs  |  | MT5 Bridge         |  | Storage Layer  |  |
|  | - MT5 Ticks (XAU, FX) |  | - ForexFactory / RSS |  | - Local IPC / Wine |  | - PostgreSQL   |  |
|  | - Binance WS (Crypto) |  | - NewsAPI / Finnhub  |  | - Account Sync     |  | - Redis Pub/Sub|  |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. STACK CÔNG NGHỆ VÀ MÔI TRƯỜNG DOCKER

Toàn bộ hệ thống được container hóa thông qua Docker Compose, chạy trên cùng mạng nội bộ (`trading-net`) để tối ưu hóa tốc độ giao tiếp IPC/TCP.

| Phân tầng | Công nghệ | Vai trò kỹ thuật |
| :--- | :--- | :--- |
| **Containerization** | Docker, Docker Compose | Chuẩn hóa môi trường triển khai độc lập giữa Frontend, Backend, Database và Broker. |
| **Frontend** | Vue 3 (Vite), Tailwind CSS, Pinia | Single Page Application hiệu năng cao, tối ưu render DOM với dữ liệu tần suất lớn. |
| **Charting Engine** | TradingView Lightweight Charts (v4.x) | Thư viện đồ họa Canvas hiển thị nến real-time, markers vào lệnh, SL/TP mà không tốn tài nguyên GPU. |
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn | Xử lý bất đồng bộ (`asyncio`), phục vụ RESTful API và WebSocket Hub cho luồng nến/tick. |
| **Data Streaming** | Redis 7 (Alpine) | Caching và Message Broker (Pub/Sub) làm trạm trung chuyển tick data và signal event. |
| **Database** | PostgreSQL 16 (Alpine) | Lưu trữ nến lịch sử (OHLCV), nhật ký giao dịch giả định, dữ liệu tin tức và báo cáo PnL. |
| **AI / NLP Engine** | LangChain / LiteLLM, OpenAI / Gemini API | Phân tích cảm xúc tin tức vĩ mô, trích xuất sự kiện và đề xuất tối ưu tham số chiến lược. |
| **Broker Connector** | Python `MetaTrader5` / Wine Headless | Đồng bộ hóa dữ liệu giá thực tế và quản lý trạng thái tài khoản demo/live. |

---

## 3. THIẾT KẾ CẤU HÌNH DOCKER COMPOSE (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: trading_postgres
    restart: always
    environment:
      POSTGRES_DB: trading_system
      POSTGRES_USER: quant_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - trading-net

  redis:
    image: redis:7-alpine
    container_name: trading_redis
    restart: always
    ports:
      - "6379:6379"
    networks:
      - trading-net

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: trading_backend
    restart: always
    depends_on:
      - postgres
      - redis
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    networks:
      - trading-net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: trading_frontend
    restart: always
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - trading-net

  mt5-bridge:
    build:
      context: ./mt5-bridge
      dockerfile: Dockerfile
    container_name: trading_mt5_bridge
    restart: always
    environment:
      MT5_LOGIN: ${MT5_DEMO_LOGIN}
      MT5_PASSWORD: ${MT5_DEMO_PASSWORD}
      MT5_SERVER: ${MT5_DEMO_SERVER}
    ports:
      - "5001:5001"
    networks:
      - trading-net

networks:
  trading-net:
    driver: bridge

volumes:
  pgdata:
```

---

## 4. DATA LAYER: INGESTION & PIPELINE ARCHITECTURE

Tầng dữ liệu được thiết kế tách biệt theo hai luồng: **Market Data Stream (Định lượng)** và **Financial News Pipeline (Định tính)**.

### 4.1. Real-time Market Data Pipeline
* **Vàng (XAUUSD) & Forex (EURUSD, GBPUSD):**
  * Nguồn chính: Cổng MT5 Client qua tiến trình Python Bridge (`MetaTrader5.copy_ticks_range` / `copy_rates_from_pos`).
  * Nguồn dự phòng: Finnhub / TwelveData WebSocket.
* **Crypto (BTCUSDT, ETHUSDT):**
  * Nguồn: Kết nối trực tiếp WebSocket Stream từ Binance (`wss://stream.binance.com:9443/ws/btcusdt@kline_1m`).
* **Chuẩn hóa dữ liệu (Fan-out Format):**
  Tick thu về từ MT5 và Binance được chuẩn hóa và đẩy vào Redis Stream `market:ticks`:
  ```json
  {
    "symbol": "XAUUSD",
    "timestamp": 1774972800000,
    "bid": 2685.50,
    "ask": 2685.75,
    "spread": 25,
    "volume": 12
  }
  ```

### 4.2. Financial News & Sentiment Pipeline
* **Nguồn dữ liệu:**
  * Lịch kinh tế (High Impact Events): Trích xuất định kỳ từ Forex Factory Calendar JSON API (CPI, NFP, FOMC).
  * Tin tức tức thời (Breaking News): RSS Feeds (Reuters Financial, FXStreet) và NewsAPI/Finnhub.
* **Xử lý sơ bộ:** Lọc tin tức theo từ khóa tài sản (`Gold`, `Federal Reserve`, `Interest Rates`, `Inflation`, `Crypto`).

---

## 5. BACKEND ENGINE ARCHITECTURE

Backend được xây dựng theo kiến trúc hướng module (Modular Monolith) để chuẩn bị cho việc tích hợp tính năng tự động giao dịch thật ở Giai đoạn 2.

### 5.1. Knowledge & Strategy Ingestion Module
* Cho phép nạp chiến lược dưới 2 hình thức:
  1. **Quy tắc toán học (Rules-based):** Định nghĩa cấu trúc chỉ báo (EMA Cross, RSI Divergence, ATR Breakout, SMC/Order Block) qua cấu hình JSON/YAML.
  2. **Tài liệu chiến lược (Unstructured Text):** Nạp tài liệu PDF/Markdown chứa quy tắc trading, kinh nghiệm, nhật ký mẫu vào hệ thống cơ sở tri thức (Vector DB / ChromaDB nhúng cục bộ).

### 5.2. AI Strategy & Market Context Engine
* **Đánh giá tác động tin tức (News Sentiment Impact):**
  * Khi có tin tức mới, trích xuất thực thể và chấm điểm:
    $$\text{Impact Score} \in [-1.0, +1.0] \quad (\text{Bearish} \rightarrow \text{Bullish})$$
  * Phân loại mức độ biến động dự kiến: `LOW`, `MEDIUM`, `HIGH_RISK_HALT`.
* **Tối ưu hóa chiến lược theo bối cảnh thị trường:**
  * AI Module phân tích bối cảnh nến (ADX, ATR, Khung giờ Á/Âu/Mỹ).
  * Đề xuất tinh chỉnh tham số: Ví dụ, nếu biến động (ATR) tăng mạnh do tin tức, AI khuyến nghị nới rộng Stop Loss từ $2.5 \rightarrow $4.0 USD đối với Vàng và thu nhỏ Lot size để bảo toàn $1\%$ rủi ro vốn.

### 5.3. Paper Trading Execution Engine (Mô phỏng vào/đóng lệnh)
Module chạy độc lập, vận hành trên giá thực nhưng ghi nhận lệnh ảo:
* **Khớp lệnh mô phỏng (Virtual Fill):**
  * Tính toán giá khớp có tính kèm **Spread thực tế** và **Slippage (Trượt giá mô phỏng: 0.5 - 2 points)**.
  * Hỗ trợ các trạng thái lệnh: `PENDING`, `FILLED`, `CANCELLED`, `CLOSED`.
* **Giám sát SL/TP động theo từng Tick:**
  * Mỗi khi có tick mới từ Redis, engine quét danh sách vị thế đang mở.
  * Tự động kích hoạt đóng lệnh khi $\text{High} \ge \text{TP}$ hoặc $\text{Low} \le \text{SL}$ (đối với lệnh BUY).
* **Ghi nhận & Nhật ký hóa (Telemetry & Analytics):**
  * Lưu trữ từng chu kỳ giao dịch vào PostgreSQL: Mã lệnh, Giá vào, Giá ra, Thời gian giữ lệnh, Tỷ lệ R:R đạt được, Lý do vào lệnh theo chiến lược, và bối cảnh tin tức lúc khớp.

---

## 6. FRONTEND & UI/UX ARCHITECTURE

Giao diện được thiết kế theo phong cách Trading Cockpit tối giản, hiện đại và tập trung vào dữ liệu tốc độ cao.

```
+---------------------------------------------------------------------------------------------------+
| HEADER: System Health | MT5 Connection: ACTIVE | Real-time Clock (EST/VN) | Account Balance: $10,000|
+----------------------------------------------------------------+----------------------------------+
| VÙNG BIỂU ĐỒ TRỰC QUAN (70% WIDTH)                              | CỘT PHÂN TÍCH & TIN TỨC (30% W)  |
| +------------------------------------------------------------+ | +------------------------------+ |
| | Symbol Selector: [ XAUUSD v ] [ M1 | M5 | M15 | H1 ]       | | | BẢNG ĐIỀU HÀNH AI TỔNG QUAN  | |
| +------------------------------------------------------------+ | | - Thị trường: Trending Up    | |
| |                                                            | | | - Khuyến nghị: Ưu tiên BUY   | |
| |   TradingView Lightweight Chart Canvas                     | | | - Winrate đề xuất: 64%       | |
| |   - Nến thời gian thực (OHLCV)                             | | +------------------------------+ |
| |   - Lớp chỉ báo: EMA(21, 50), ATR Bands                    | | | DÒNG SỰ KIỆN & TIN TỨC REAL  | |
| |   - Markers đồ họa:                                        | | | [14:30] CPI Tăng 0.3% (HIGH) | |
| |     ▲ BUY Entry (2685.20)                                  | | |  -> Tác động: Tiêu cực XAU   | |
| |     ─ Đường SL (2680.00) / ─ Đường TP (2695.00)            | | | [15:10] FED Phát biểu...     | |
| |     ▼ Closed Trade Marker (+2.1R / +$210)                  | | +------------------------------+ |
| +------------------------------------------------------------+ | | THÔNG SỐ ĐỀ XUẤT HIỆN TẠI    | |
| | BẢNG QUẢN LÝ VỊ THẾ & LỆNH GIẢ LẬP (PAPER ORDERS)           | | | - Lot Size tối đa: 0.15      | |
| | Ticket | Asset | Type | Entry | SL   | TP   | Current| PnL | | | - SL Khuyến nghị: 35 points  | |
| | #1001  | XAU   | BUY  | 2685  | 2682 | 2692 | 2689   |+$40 | | | - Trạng thái: CHO PHÉP TRADE | |
+----------------------------------------------------------------+----------------------------------+
```

### 6.1. Triển khai TradingView Lightweight Charts
* **Quản lý dữ liệu:**
  * Khởi tạo: Nạp 500 cây nến lịch sử gần nhất qua REST API (`/api/v1/market/history`).
  * Cập nhật thời gian thực: Nhận tick qua WebSocket, hàm `series.update()` xử lý tạo nến mới hoặc cập nhật nến hiện tại mà không render lại toàn bộ màn hình.
* **Hiển thị giao dịch trực quan (Visual Execution Overlay):**
  * Vẽ vị thế mở bằng đường giá nằm ngang: Màu xanh lá (TP), Màu đỏ (SL), Màu xanh lam (Entry).
  * Điểm vào lệnh / đóng lệnh hiển thị bằng `series.setMarkers()` (Hình mũi tên và nhãn PnL tương ứng).

---

## 7. MÔ HÌNH DỮ LIỆU CỐT LÕI (DATABASE SCHEMA)

```sql
-- 1. Bảng lưu trữ nến thị trường
CREATE TABLE market_candles (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    timeframe VARCHAR(8) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume NUMERIC(16, 2) NOT NULL,
    UNIQUE(symbol, timeframe, open_time)
);

-- 2. Bảng tin tức tài chính và phân tích AI
CREATE TABLE financial_news (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    impact_level VARCHAR(16) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH
    sentiment_score NUMERIC(4, 2), -- Biên độ từ -1.00 đến +1.00
    ai_analysis_summary TEXT
);

-- 3. Bảng lệnh giao dịch giả định (Paper Trading Orders)
CREATE TABLE simulated_orders (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    order_type VARCHAR(8) NOT NULL, -- BUY / SELL
    status VARCHAR(16) NOT NULL,     -- OPEN, CLOSED, CANCELLED
    lot_size NUMERIC(8, 2) NOT NULL,
    entry_price NUMERIC(12, 4) NOT NULL,
    exit_price NUMERIC(12, 4),
    stop_loss NUMERIC(12, 4) NOT NULL,
    take_profit NUMERIC(12, 4) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    close_time TIMESTAMPTZ,
    realized_pnl NUMERIC(12, 2),
    pnl_percentage NUMERIC(6, 2),
    strategy_trigger VARCHAR(64),
    ai_market_context_id BIGINT REFERENCES financial_news(id)
);

-- 4. Bảng tổng hợp số liệu hiệu suất (Daily/Weekly Metrics)
CREATE TABLE simulation_metrics (
    date DATE PRIMARY KEY,
    total_trades INT DEFAULT 0,
    win_trades INT DEFAULT 0,
    loss_trades INT DEFAULT 0,
    winrate NUMERIC(5, 2) DEFAULT 0.0,
    profit_factor NUMERIC(6, 2) DEFAULT 0.0,
    total_pnl NUMERIC(12, 2) DEFAULT 0.0,
    max_drawdown NUMERIC(5, 2) DEFAULT 0.0
);
```

---

## 8. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
trading-system/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── core/
│   │   ├── config.py           # Quản lý biến môi trường
│   │   ├── database.py         # Kết nối SQLAlchemy / asyncpg
│   │   └── redis_client.py     # Quản lý Pub/Sub & Caching
│   ├── data_ingestion/
│   │   ├── mt5_feed.py         # Lấy tick từ MT5 Bridge
│   │   ├── binance_feed.py     # WebSocket Client Binance
│   │   └── news_collector.py   # Lấy tin ForexFactory/RSS
│   ├── ai_engine/
│   │   ├── sentiment.py        # Đánh giá tin tức qua LLM
│   │   ├── strategy_advisor.py # Phân tích bối cảnh & tối ưu tham số
│   │   └── prompts.py          # System prompt mẫu cho AI
│   ├── simulation/
│   │   ├── paper_engine.py     # Xử lý khớp lệnh ảo, tính trượt giá
│   │   ├── risk_checker.py     # Giám sát SL/TP từng tick
│   │   └── statistics.py       # Tính toán Winrate, Drawdown, PnL
│   └── api/
│       ├── v1/
│       │   ├── market.py       # REST endpoints nến lịch sử
│       │   ├── orders.py       # CRUD lệnh giả định
│       │   ├── news.py         # Danh sách tin và kết quả phân tích
│       │   └── websocket.py    # Kênh truyền dữ liệu nến + lệnh live
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chart/
│   │   │   │   ├── TradingViewChart.vue  # Wrapper Lightweight Charts
│   │   │   │   └── ChartOverlayControls.vue
│   │   │   ├── News/
│   │   │   │   ├── NewsStream.vue        # Bảng tin tức thời gian thực
│   │   │   │   └── SentimentGauge.vue    # Đồng hồ đo cảm xúc AI
│   │   │   ├── Simulation/
│   │   │   │   ├── OrderBookTable.vue    # Danh sách lệnh mở/đóng
│   │   │   │   └── MetricsCards.vue      # Thống kê Winrate, Profit
│   │   │   └── AIAnalysis/
│   │   │       └── InsightsPanel.vue     # Đề xuất tối ưu chiến lược
│   │   ├── stores/
│   │   │   ├── marketStore.js
│   │   │   └── orderStore.js
│   │   └── services/
│   │       ├── api.js
│   │       └── websocket.js
└── mt5-bridge/
    ├── Dockerfile              # Cấu hình Wine + Python MT5
    └── server.py               # Expose API lấy tick nội bộ cho backend
```

---

## 9. TIÊU CHÍ NGHIỆM THU GIAI ĐOẠN 1

1. **Dữ liệu thời gian thực thông suốt:** Biểu đồ TradingView Lightweight Charts cập nhật nến M1/M5/M15 mượt mà cho XAUUSD, Forex và BTCUSDT mà không bị gián đoạn hay rò rỉ bộ nhớ (memory leak).
2. **Khớp lệnh giả lập chính xác:** Động cơ Paper Trading ghi nhận lệnh, tự động quét nến đóng lệnh qua SL/TP và trừ spread/slippage thực tế.
3. **Phân tích bối cảnh AI hoạt động:** Đưa ra điểm sentiment tin tức và gợi ý điều chỉnh tham số (SL/TP, Lot) theo biến động thị trường.
4. **Sẵn sàng chuyển giao Giai đoạn 2:** Cấu trúc module và cơ sở dữ liệu đã chuẩn hóa, sẵn sàng mở rộng sang Auto-Execution với MT5 Live và Backtesting Engine.