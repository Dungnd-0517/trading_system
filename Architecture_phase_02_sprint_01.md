# KIẾN TRÚC DỰ ÁN: NỀN TẢNG PHÂN TÍCH & GIAO DỊCH TỰ ĐỘNG (XAU / FOREX / CRYPTO)

> **Trạng thái:** SPEC READY FOR IMPLEMENTATION. Quyết định D2–D6 đã chốt.
> **Tài liệu nền:** [Architecture.md](Architecture.md). Các mục 1–9 dưới đây chỉ là tóm tắt tham khảo, không thay thế hay thu hẹp kiến trúc nền.
> **Phạm vi:** Delta của Phase 2, Sprint 1; triển khai theo decision log và tiêu chí nghiệm thu bên dưới.

---

## MỤC LỤC
1. [Tổng quan Hệ thống (System Overview)](#1-tổng-quan-hệ-thống-system-overview)
2. [Stack Công nghệ & Môi trường Docker](#2-stack-công-nghệ--môi-trường-docker)
3. [Thiết kế Cấu hình Docker Compose (`docker-compose.yml`)](#3-thiết-kế-cấu-hình-docker-compose-docker-composeyml)
4. [Data Layer: Pipeline Thu thập & Phân phối](#4-data-layer-pipeline-thu-thập--phân-phối)
5. [Backend Core Engine](#5-backend-core-engine)
6. [Frontend & UI/UX Architecture](#6-frontend--uiux-architecture)
7. [Mô hình Dữ liệu Cốt lõi (Database Schema)](#7-mô-hình-dữ-liệu-cốt-lõi-database-schema)
8. [Cấu trúc Thư mục Dự án](#8-cấu-trúc-thư-mục-dự-án)
9. [Tiêu chí Nghiệm thu Giai đoạn 1](#9-tiêu-chí-nghiệm-thu-giai-đoạn-1)
10. [Giai đoạn 2 - Sprint 1: XAUUSD News Collectors & TradingView Live Data](#10-giai-đoạn-2---sprint-1-xauusd-news-collectors--tradingview-live-data)
    - [10.1. Bộ Thu thập Tin tức & Phân loại Mức độ Ảnh hưởng (3 Cấp sao)](#101-bộ-thu-thập-tin-tức--phân-loại-mức-độ-ảnh-hưởng-3-cấp-sao)
    - [10.2. TradingView Live Data Feed Pipeline (Nến, Volume, Price)](#102-tradingview-live-data-feed-pipeline-nến-volume-price)
    - [10.3. Kiến trúc Component Frontend (Sprint 1)](#103-kiến-trúc-component-frontend-sprint-1)
    - [10.4. Mở rộng Database Schema (Sprint 1)](#104-mở-rộng-database-schema-sprint-1)

---

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

Hệ thống được thiết kế theo mô hình **Event-Driven Modular Monolith**, tối ưu độ trễ thấp và độ tin cậy cao trong thu thập dữ liệu tài chính đa tài sản, trực quan hóa biểu đồ TradingView, phân tích bối cảnh AI và mô phỏng/thực thi lệnh tự động.

```
+---------------------------------------------------------------------------------------------------+
|                                      FRONTEND (SPA / Vue 3)                                       |
|  +------------------------------+  +-------------------------------+  +------------------------+  |
|  | TradingView Lightweight Chart|  | XAUUSD Financial News Feed    |  | AI Insights & Strategy |  |
|  | (Candles, Volume, Live Price)|  | & 3-Star Impact Rating        |  | Optimization Panel     |  |
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
|  |  - Live Chart Feeder |  |  - RAG / Knowledge  |  | - Virtual Fill Sim |  | - PnL Tracking   |  |
|  |  - News Aggregator   |  |  - LLM Strategy Opt |  | - SL/TP Dynamic Mon|  | - Trade Journal  |  |
|  |  - Star Rating Engine|  |  - Sentiment Score  |  | - Spread & Latency |  | - Performance    |  |
|  +----------▲-----------+  +----------▲----------+  +---------▲----------+  +--------▲---------+  |
+-------------│-------------------------│-----------------------│----------------------│------------+
              │                         │                       │                      │
+-------------▼-------------------------▼-----------------------▼----------------------▼------------+
|                                      DATA & BROKER LAYER                                          |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
|  | Market Data Providers |  | Financial News APIs  |  | MT5 Bridge         |  | Storage Layer  |  |
|  | - MT5 Ticks (XAU, FX) |  | - ForexFactory API   |  | - Local IPC / Wine |  | - PostgreSQL   |  |
|  | - Binance WS (Crypto) |  | - NewsAPI / Finnhub  |  | - Account Sync     |  | - Redis Pub/Sub|  |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. STACK CÔNG NGHỆ & MÔI TRƯỜNG DOCKER

| Phân tầng | Công nghệ | Vai trò kỹ thuật |
| :--- | :--- | :--- |
| **Containerization** | Docker, Docker Compose | Chuẩn hóa môi trường triển khai độc lập giữa Frontend, Backend, Database và Broker. |
| **Frontend** | Vue 3 (Vite), Tailwind CSS, Pinia | Single Page Application hiệu năng cao, tối ưu render DOM với dữ liệu tần suất lớn. |
| **Charting Engine** | TradingView Lightweight Charts (v4.x) | Thư viện đồ họa Canvas hiển thị nến real-time, volume histogram, giá live và markers lệnh. |
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn | Xử lý bất đồng bộ (`asyncio`), phục vụ RESTful API và WebSocket Hub. |
| **Data Streaming** | Redis 7 (Alpine) | Caching và Message Broker (Pub/Sub) làm trạm trung chuyển tick data và signal event. |
| **Database** | PostgreSQL 16 (Alpine) | Lưu trữ nến lịch sử (OHLCV), sự kiện kinh tế, tin tức đánh giá sao, và nhật ký lệnh. |
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

## 4. DATA LAYER: PIPELINE THU THẬP & PHÂN PHỐI

### 4.1. Real-time Market Data Pipeline
* **Vàng (XAUUSD) & Forex (EURUSD, GBPUSD):** MT5 Client qua tiến trình Python Bridge (`MetaTrader5.copy_ticks_range` / `copy_rates_from_pos`). Dự phòng: Finnhub / TwelveData WebSocket.
* **Crypto (BTCUSDT, ETHUSDT):** WebSocket Stream từ Binance (`wss://stream.binance.com:9443/ws/btcusdt@kline_1m`).
* **Chuẩn hóa dữ liệu:** Tick đẩy vào Redis Stream `market:ticks` và tổng hợp thành nến OHLCV kèm Volume đẩy tới client.

### 4.2. Financial News & Sentiment Pipeline
* Lịch kinh tế: Forex Factory Calendar API / RSS Feeds.
* Tin tức tức thời: FXStreet, Reuters Financial, Finnhub, NewsAPI.
* Lọc từ khóa chuyên sâu cho Vàng và USD.

---

## 5. BACKEND ENGINE ARCHITECTURE

* **Knowledge & Strategy Ingestion Module:** Nạp chiến lược dạng cấu hình JSON (Rules-based) hoặc tài liệu PDF/Markdown vào Vector DB.
* **AI Strategy & Market Context Engine:** Đánh giá điểm tác động tin tức $\text{Impact Score} \in [-1.0, +1.0]$, tối ưu hóa tham số SL/TP động.
* **Paper Trading Execution Engine:** Khớp lệnh ảo với spread và slippage thực tế, quét SL/TP động theo từng tick giá.

---

## 6. FRONTEND & UI/UX ARCHITECTURE

Thiết kế giao diện Trading Cockpit màn hình rộng:
* **70% Chiều rộng:** Khung biểu đồ TradingView Lightweight Canvas hiển thị Candlesticks, Volume histogram và dải giá trực tiếp.
* **30% Chiều rộng:** Bảng tin tức tài chính (hiển thị sao ⭐⭐⭐), chỉ số cảm xúc AI, và danh sách lệnh đang chạy.

---

## 7. MÔ HÌNH DỮ LIỆU CỐT LÕI (DATABASE SCHEMA)

```sql
-- Nến thị trường
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

-- Lệnh giao dịch giả định
CREATE TABLE simulated_orders (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    order_type VARCHAR(8) NOT NULL,
    status VARCHAR(16) NOT NULL,
    lot_size NUMERIC(8, 2) NOT NULL,
    entry_price NUMERIC(12, 4) NOT NULL,
    exit_price NUMERIC(12, 4),
    stop_loss NUMERIC(12, 4) NOT NULL,
    take_profit NUMERIC(12, 4) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    close_time TIMESTAMPTZ,
    realized_pnl NUMERIC(12, 2),
    strategy_trigger VARCHAR(64)
);
```

---

## 8. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
trading-system/
├── docker-compose.yml
├── README.md
├── Architecture.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── redis_client.py
│   ├── data_ingestion/
│   │   ├── mt5_feed.py
│   │   ├── news_collector.py     # Collectors: Lịch kinh tế & Breaking news
│   │   ├── news_classifier.py    # Phân loại 1, 2, 3 sao cho XAUUSD
│   │   └── chart_streamer.py     # Nén tick thành nến + volume live
│   ├── ai_engine/
│   ├── simulation/
│   └── api/
│       └── v1/
│           ├── chart_router.py
│           ├── news_router.py
│           └── websocket.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── components/
│       │   ├── Chart/
│       │   │   └── TradingViewLiveChart.vue  # Nến, Volume, Price scale
│       │   └── News/
│       │       └── GoldNewsFeed.vue          # Tin tức gắn sao (⭐, ⭐⭐, ⭐⭐⭐)
└── mt5-bridge/
    ├── Dockerfile
    └── server.py
```

---

## 9. TIÊU CHÍ NGHIỆM THU GIAI ĐOẠN 1

1. Dữ liệu nến real-time hiển thị liên tục, không rò rỉ bộ nhớ.
2. Khớp lệnh giả lập chính xác theo spread và slippage thực tế.
3. Module phân tích bối cảnh AI đề xuất SL/TP theo biến động.
4. Môi trường Docker Compose khởi chạy toàn bộ service chỉ với 1 câu lệnh.

---

## 10. GIAI ĐOẠN 2 - SPRINT 1: XAUUSD NEWS COLLECTORS & TRADINGVIEW LIVE DATA

Sprint 1 của Giai đoạn 2 tập trung sâu vào 2 trục tính năng:
1. **Pipeline Tin tức XAUUSD:** Thu thập Lịch kinh tế và Tin tức tức thời, lọc nội dung liên quan trực tiếp đến Vàng và phân loại ảnh hưởng theo 3 cấp độ sao.
2. **Biểu đồ TradingView Live:** Tích hợp engine đồ họa TradingView Lightweight Charts hiển thị đồng thời Nến (OHLC), Khối lượng (Volume) và Giá trực tiếp (Price) với độ trễ thấp.

### Decision log

| ID | Quyết định | Trạng thái | Tác động |
|---|---|---|---|
| D2 | Phân loại sao theo loại sự kiện; tách mức độ quan trọng khỏi hướng sentiment | `ACCEPTED` | Quy tắc classifier và dữ liệu news/event |
| D3 | Mở rộng additive: giữ `financial_news`, thêm `economic_events`; không gộp/xóa schema Phase 1 | `ACCEPTED` | Models, migration, API và tương thích khóa ngoại |
| D4 | Mở rộng `/api/v1/ws/market` với event có `type`; giữ nguyên message paper-order; timestamp chart UTC Unix seconds | `ACCEPTED` | Aggregator, WebSocket và frontend stores/chart |
| D5 | Provider endpoints, polling, retry, quota, dedupe, revisions và stale/failover behavior như mục 10.1.1 | `ACCEPTED` | Collector adapters; production gates ghi tại D5 |
| D6 | Test matrix, latency/freshness SLO và nghiệm thu như mục 12 | `ACCEPTED` | CI/integration tests và sprint sign-off |

### 10.1. Bộ Thu thập Tin tức & Phân loại Mức độ Ảnh hưởng (3 Cấp sao)

**D2 — ACCEPTED: phân loại theo loại sự kiện, không theo biến động giá sau sự kiện.** Số sao biểu thị mức độ quan trọng/rủi ro dự kiến; hướng tác động bullish/bearish là dữ liệu riêng, không suy ra từ số sao.

| Cấp | Quy tắc loại sự kiện | Ví dụ |
|---|---|---|
| 1 sao | Sự kiện thứ cấp, thường ít tác động | Đấu thầu trái phiếu định kỳ, tồn kho bán buôn, Initial Jobless Claims thông thường |
| 2 sao | Sự kiện kinh tế có thể làm biến động đáng kể | PMI, Retail Sales, UoM Consumer Sentiment, ADP |
| 3 sao | Sự kiện trọng yếu hoặc rủi ro thị trường cao | FOMC/quyết định lãi suất, CPI/PPI, NFP, phát biểu Chủ tịch Fed, tin địa chính trị trọng yếu |
| Chưa phân loại | Không khớp quy tắc hoặc thiếu dữ liệu đáng tin cậy | Lưu trạng thái `UNKNOWN`, không tự gán 1 sao |

Quy tắc áp dụng trước tiên cho loại sự kiện/mã sự kiện đã chuẩn hóa; từ khóa `USD`, `GOLD` hoặc `FED` chỉ dùng lọc liên quan, không đủ để tự quyết định số sao. Không dùng ngưỡng biến động giá/points để gán sao. Lưu `impact_stars` riêng với sentiment/hướng tác động; sentiment chưa xác định được thì để trống/unknown.

### 10.1.1. Nguồn dữ liệu, vận hành và revision (D5 — ACCEPTED)

Các endpoint/feed dưới đây đã được kiểm tra trực tiếp ngày 2026-10-01. Finnhub có tài liệu REST chính thức; FairEconomy, Kitco và FXStreet được kiểm tra qua endpoint/feed công khai. Không tìm thấy hợp đồng API/SLA chính thức cho FairEconomy nên đây là phụ thuộc best-effort, không có cam kết độ sẵn sàng.

| Luồng | Vai trò và endpoint | Protocol / dữ liệu đã xác minh |
|---|---|---|
| Economic calendar | Primary: [FairEconomy current-week JSON](https://nfs.faireconomy.media/ff_calendar_thisweek.json) | HTTPS `GET`, JSON array gồm `title`, `country`, `date`, `impact`, `forecast`, `previous`; `date` có UTC offset ISO-8601. Chỉ endpoint `thisweek` được xác minh; `ff_calendar_nextweek.json` trả 404 nên không dùng. |
| Economic calendar | Fallback: [Finnhub Economic Calendar](https://finnhub.io/docs/api/economic-calendar) | HTTPS REST `GET https://finnhub.io/api/v1/calendar/economic?from=YYYY-MM-DD&to=YYYY-MM-DD`; JSON `economicCalendar[]` có `actual`, `country`, `estimate`, `event`, `impact`, `prev`, `time`, `unit`. Tài liệu đánh dấu endpoint **Premium**. |
| Gold news | Primary 1: [Kitco News RSS](https://news.kitco.com/rss/kitconewsfeed.xml) | HTTPS `GET`, RSS 2.0/XML; feed latest precious-metals news; item có `guid`, `link`, `title`, `description`, `pubDate`, `dc:creator`. Mẫu `pubDate` dùng EDT. |
| General/FX news | Primary 2: [FXStreet News RSS](https://www.fxstreet.com/rss/news) | HTTPS `GET`, RSS 2.0/XML; item có UUID `guid`, `link`, `title`, `description`, `pubDate`; mẫu feed ghi GMT. |
| Breaking-news fallback | [Finnhub Market News](https://finnhub.io/docs/api/market-news) | HTTPS REST `GET https://finnhub.io/api/v1/news?category=forex&minId=<id>` và `category=general`; JSON array có `id`, `datetime` (Unix seconds), `headline`, `source`, `summary`, `url`. |

#### Polling và failover

* Poll FairEconomy `thisweek.json` mỗi **5 phút**. Chỉ lưu/hiển thị sự kiện trong feed; không tự suy diễn dữ liệu cho tuần sau khi endpoint không tồn tại.
* Poll Kitco và FXStreet mỗi **2 phút**. Dùng `ETag`/`Last-Modified` và conditional GET nếu server cung cấp; nếu không có validator, dùng hash nội dung feed. Gửi `Accept: application/rss+xml, application/xml`; không crawl trang bài viết, chỉ lưu headline, excerpt từ feed, thời gian, nguồn và URL.
* Bắt đầu fallback riêng cho nguồn sau **2 chu kỳ liên tiếp** có lỗi mạng, timeout, HTTP 5xx hoặc payload không parse/validate được. Finnhub chỉ được gọi khi fallback active: Market News mỗi 2 phút, Economic Calendar mỗi 5 phút. Sau **2 lần poll primary liên tiếp thành công và hợp lệ**, quay lại primary.
* Mỗi lần gọi có connect timeout **3 giây**, read timeout **10 giây**, tối đa **3 attempts tổng cộng** mỗi chu kỳ; khoảng chờ retry là `1s` và `2s` với jitter ±20%. Chỉ retry lỗi mạng, timeout, 408 và 5xx. Với 429, tôn trọng `Retry-After`, không gọi dồn. 401/403/404 không retry; vô hiệu hóa endpoint đó đến lần restart/cấu hình kế tiếp và đánh dấu entitlement/cấu hình/endpoint lỗi.
* Mở circuit breaker sau **5 lỗi liên tiếp**, giữ mở **5 phút**, sau đó cho một probe. Nguồn quá **3 chu kỳ poll** không có fetch hợp lệ thì đánh dấu `STALE`; tiếp tục phục vụ last-good nhưng UI/API phải báo stale, không coi là live.
* Finnhub xác nhận HTTP 429 khi vượt quota và hard ceiling 30 calls/second ngoài quota theo plan. Client phải cấu hình quota theo entitlement thật, giới hạn concurrency/budget; không coi 30 calls/second là quota được cấp. Gửi API key bằng header `X-Finnhub-Token` từ secret/environment; không đưa vào URL, log hay tài liệu. Economic Calendar cần Premium entitlement; nếu không có thì fallback là unavailable và phải báo rõ.

#### Timezone, identity và revisions

* FairEconomy `date` có offset: parse thành aware datetime, chuẩn hóa UTC và giữ raw timestamp. Kitco `pubDate` parse theo timezone ghi trong chuỗi (`EDT`/`EST`); FXStreet `pubDate` theo GMT; Finnhub Market News `datetime` là Unix seconds.
* Finnhub Economic Calendar response mẫu chỉ có `time` dạng chuỗi không kèm timezone/offset. Lưu `provider_time_raw`; đặt `event_timestamp = NULL` và không bật countdown tới khi timezone được xác minh bằng tài liệu hoặc xác nhận bằng văn bản từ Finnhub. Không tự giả định EST/UTC.
* Identity ưu tiên ID nguồn: Finnhub news `id`, RSS `guid`; thiếu `guid` thì dùng canonical article URL. Economic Calendar payload không có event ID đã xác minh: tạo khóa từ source, currency/country, title chuẩn hóa và ngày sự kiện theo thời gian gốc. Đổi giờ trong cùng ngày cập nhật cùng bản ghi; đổi ngày hoặc có nhiều ứng viên trùng title thì không fuzzy-merge, lưu riêng và ghi anomaly.
* Upsert theo identity. Payload không đổi không tạo revision. Nếu field chuẩn hóa đổi, tăng `revision_no`, cập nhật bản hiện hành và `updated_at`. Economic event phải lưu snapshot cũ của thời gian, previous/forecast/actual, impact và raw-time trước update. News cập nhật bản hiện hành, `content_hash`, `revision_no`, `last_seen_at`; không lưu thêm bản sao toàn văn bài báo. Finnhub Market News dùng `minId` theo category và replay overlap **100 ID** gần nhất; dedupe bằng `id`.
* Provider `impact` là input tham khảo; số sao cuối do classifier D2 quyết định. Ghi `source`, `fetched_at`, `published_at/event_timestamp` và `source_status` để phân biệt primary/fallback/stale.

#### Deployment gates D5

* Trước production, xác nhận điều khoản/permission dùng FairEconomy và RSS Kitco/FXStreet; endpoint truy cập được không đồng nghĩa được phép lưu/phân phối lại. UI chỉ hiển thị phần cần thiết và dẫn link nguồn.
* Trước khi bật Finnhub Economic Calendar fallback, xác nhận Premium entitlement và timezone của trường `time`. Cho tới lúc xác nhận, vẫn có thể nhập nội dung nhưng phải giữ raw time và không phát countdown.

---

### 10.2. TradingView Live Data Feed Pipeline (Nến, Volume, Price)

**D4 — ACCEPTED: giữ endpoint WebSocket hiện tại `/api/v1/ws/market` và mở rộng bằng event type mới.** Không đổi hoặc loại bỏ message hiện có cho market/paper orders. Timestamp của chart là UTC Unix seconds, nhất quán với REST `/api/v1/market/history`.

```
MT5/Binance -> chuẩn hóa tick -> aggregator theo symbol/timeframe
            -> Redis -> /api/v1/ws/market -> chart.update -> series.update()
```

Event chart có dạng:

```json
{
  "type": "chart.update",
  "symbol": "XAUUSD",
  "timeframe": "M1",
  "timestamp": 1774972800,
  "candle": { "time": 1774972800, "open": 2685.0, "high": 2686.0, "low": 2684.5, "close": 2685.5 },
  "volume": { "time": 1774972800, "value": 12, "unit": "tick_count", "color": "up" },
  "price": { "value": 2685.5, "bid": 2685.5, "ask": 2685.75 }
}
```

Quy ước:
* `time`/`timestamp` là Unix seconds UTC; timeframe dùng các giá trị chart đang hỗ trợ: `M1`, `M5`, `M15`, `H1`.
* Nến/giá XAUUSD và Forex được tính từ `bid`; payload có thể kèm `ask` để hiển thị spread. Crypto dùng giá và volume từ giao dịch/stream của sàn.
* `volume.value` của MT5 là số tick trong nến (`tick_count`); Binance là traded volume (`base_asset_quantity`). Hai đơn vị không được diễn giải như cùng một đại lượng.
* `volume.color` là `up` khi `close >= open`, nếu không là `down`; frontend ánh xạ màu theo design system hiện tại.
* REST lịch sử khởi tạo chart. WebSocket cập nhật nến đang mở, volume và giá; không gọi tải lại toàn bộ lịch sử theo từng tick. Event mới phải có `type` để không làm thay đổi cách nhận message paper-order hiện tại.

---

### 10.3. Kiến trúc Component Frontend (Sprint 1)

Triển khai trên các component hiện có `TradingViewChart.vue` và `NewsStream.vue`; không tạo component song song `TradingViewLiveChart.vue`/`GoldNewsFeed.vue` trong sprint này. Có thể tách component ở sprint sau nếu độ phức tạp thực tế yêu cầu.

* `TradingViewChart.vue` khởi tạo candlestick, histogram volume và current-price line; nhận dữ liệu lịch sử REST trước rồi áp dụng các event `chart.update` qua `series.update()`.
* `NewsStream.vue` tiếp tục hiển thị breaking news hiện có và thêm sao/trạng thái chưa phân loại. Event lịch kinh tế có thể hiển thị riêng theo nguồn `/news/events`; countdown chỉ hiển thị với event có `event_timestamp` hợp lệ.
* Giữ design system hiện hành của cockpit; không ép chuyển sang dark mode trong Sprint 1.

---

### 10.4. Mở rộng Database Schema (Sprint 1)

**D3 — ACCEPTED: bổ sung schema theo kiểu additive; không tạo bảng gộp `gold_market_news` và không xóa/đổi vai trò các bảng Phase 1.** `financial_news` tiếp tục lưu breaking news và giữ nguyên khóa ngoại từ `simulated_orders`; lịch kinh tế có bảng riêng `economic_events`.

Các cột bổ sung cho `financial_news`:

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `external_id` | `VARCHAR(128)` nullable | ID từ provider để chống trùng; không có ID thì collector dùng khóa dedupe đã chuẩn hóa |
| `dedupe_key` | `CHAR(64)` nullable | SHA-256 của source chuẩn hóa, title chuẩn hóa và timestamp gốc UTC; dùng khi provider không có ID |
| `source_url` | `TEXT` nullable | Link bài gốc, chỉ lưu/hiển thị URL do provider trả về |
| `content_hash` | `CHAR(64)` nullable | Phát hiện thay đổi nội dung của cùng source item |
| `revision_no` | `INT NOT NULL DEFAULT 1` | Số revision hiện hành; chỉ tăng khi payload chuẩn hóa đổi |
| `last_seen_at` | `TIMESTAMPTZ` nullable | Lần gần nhất source item được nhìn thấy |
| `impact_stars` | `SMALLINT` nullable | 1–3; `NULL` khi chưa phân loại |
| `classification_status` | `VARCHAR(16)` | `CLASSIFIED` hoặc `UNKNOWN`; dữ liệu cũ được backfill thành `UNKNOWN` |
| `keywords_matched` | `TEXT[]` nullable | Từ khóa/quy tắc làm bản tin liên quan |

`impact_level` và `sentiment_score` hiện có được giữ tương thích; không dùng chúng thay cho số sao. Ràng buộc sao: `impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3`; `CLASSIFIED` phải có sao, `UNKNOWN` phải để sao `NULL`.

Schema mục tiêu cho lịch kinh tế:

```sql
CREATE TABLE economic_events (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
  external_id VARCHAR(128),
  dedupe_key CHAR(64),
    title TEXT NOT NULL,
    description TEXT,
  provider_time_raw TEXT NOT NULL,
  event_timestamp TIMESTAMPTZ,
  timezone_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'
    CHECK (timezone_status IN ('VERIFIED', 'UNKNOWN')),
    currency VARCHAR(8) DEFAULT 'USD',
    previous_value VARCHAR(32),
    forecast_value VARCHAR(32),
    actual_value VARCHAR(32),
    impact_stars SMALLINT CHECK (impact_stars BETWEEN 1 AND 3),
    classification_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (classification_status IN ('CLASSIFIED', 'UNKNOWN')),
    keywords_matched TEXT[],
    content_hash CHAR(64),
    revision_no INT NOT NULL DEFAULT 1 CHECK (revision_no >= 1),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL)
        OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)
    ),
    CHECK (
      (timezone_status = 'VERIFIED' AND event_timestamp IS NOT NULL)
      OR (timezone_status = 'UNKNOWN' AND event_timestamp IS NULL)
    )
);

CREATE INDEX idx_economic_events_time ON economic_events(event_timestamp DESC);
CREATE INDEX idx_economic_events_stars ON economic_events(impact_stars);
CREATE UNIQUE INDEX uq_economic_events_source_external_id
    ON economic_events(source, external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX uq_economic_events_dedupe_key
    ON economic_events(dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE TABLE economic_event_revisions (
  id BIGSERIAL PRIMARY KEY,
  economic_event_id BIGINT NOT NULL REFERENCES economic_events(id) ON DELETE CASCADE,
  revision_no INT NOT NULL CHECK (revision_no >= 1),
  snapshot JSONB NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (economic_event_id, revision_no)
);
```

Tạo unique partial indexes tương đương cho `financial_news(source, external_id)` và `financial_news(dedupe_key)` sau khi thêm cột. Với calendar không có ID, dedupe key theo source/currency/title/ngày sự kiện gốc, không theo thời điểm collector nhận. `economic_event_revisions` lưu snapshot canonical cũ trước khi update; news chỉ giữ revision number/hash, không lưu thêm bản sao toàn văn. Mọi thay đổi phải đi qua migration triển khai được trên DB đã có dữ liệu; không dựa vào `CREATE TABLE IF NOT EXISTS` để cập nhật schema hiện hữu.

API giữ tương thích: `GET /api/v1/news` tiếp tục trả breaking news và bổ sung các trường phân loại, revision và `source_url`; `GET /api/v1/news/events` trả lịch kinh tế; `GET /api/v1/news/status` trả trạng thái health/fallback/stale theo source. WebSocket dùng event có type `news.upsert`, kèm `kind` (`breaking_news` hoặc `economic_event`) và `data`; message paper-order hiện có không đổi.

---

## 11. TRẠNG THÁI QUYẾT ĐỊNH

* **D2–D6 — ACCEPTED:** hợp đồng Sprint 1 đã chốt; có thể bắt đầu triển khai code.
* **Production gates, không chặn phát triển/test:** xác nhận quyền sử dụng FairEconomy/RSS; Finnhub Premium entitlement và timezone của Economic Calendar; cấu hình API key/quota cho môi trường đích. Nguồn không đủ điều kiện phải được báo `unavailable`, không đánh dấu healthy.

## 12. KIỂM THỬ VÀ TIÊU CHÍ NGHIỆM THU (D6 — ACCEPTED)

### Test matrix bắt buộc

1. **Parser/normalization:** fixture cho FairEconomy JSON, Kitco RSS 2.0, FXStreet RSS 2.0 và Finnhub JSON; kiểm tra field thiếu/sai kiểu, HTML entities, UTC offsets, EDT/EST, GMT, Holiday và timezone unknown.
2. **Classifier:** bao phủ từng nhóm 1/2/3 sao và `UNKNOWN`; verify provider impact không ghi đè D2, số sao không hàm ý sentiment.
3. **Identity/dedupe/revisions:** cùng GUID/ID/key poll lặp không tạo row mới; thay đổi payload cùng identity update row/tăng revision đúng một lần; economic event thay đổi time/previous/forecast/actual có snapshot cũ; event trùng title khác ngày/nguồn không bị ghép nhầm.
4. **Resilience:** test timeout/network, 408, 429 có `Retry-After`, 5xx, 401/403, 404, invalid XML/JSON, circuit open/half-open, stale status, failover sau 2 lỗi và failback sau 2 poll primary hợp lệ. Không retry lỗi cấu hình; không vượt request budget trong fixture test.
5. **Schema/API:** migration từ DB Phase 1 giữ nguyên rows `financial_news`, khóa ngoại `simulated_orders` và metrics. Economic event timezone unknown phải có raw time, `event_timestamp=NULL`, không countdown. REST news/events và WebSocket `news.upsert` giữ attribution; paper-order message cũ không đổi.
6. **Frontend:** REST seed + WebSocket update không tạo duplicate; badge sao/UNKNOWN và nguồn đúng; link nguồn hợp lệ; countdown chỉ hiện với thời gian đã xác minh; stale/fallback có trạng thái rõ; revision cập nhật đúng item.

CI dùng fixtures và HTTP mocks, không phụ thuộc internet, Finnhub key hay provider availability. Live smoke test tách riêng, ghi HTTP status/schema/timezone/quota state và không ghi secrets.

### SLO và acceptance

* **Internal WebSocket latency:** p95 ≤ **50 ms** từ lúc backend publish event đến lúc browser nhận event trong Docker Compose local, 1 browser client, tải cố định **10 events/second trong 5 phút**. Đo trên cùng host với đồng hồ đồng bộ; không gộp độ trễ từ provider bên ngoài vào SLO này.
* **Collector detection bound:** khi test server bắt đầu trả item mới ngay sau poll trước, DB và WebSocket nhận item trong tối đa **10 giây sau fetch thành công**. Detection ceiling tính từ lúc source bắt đầu trả item: **5 phút 10 giây** với calendar, **2 phút 10 giây** với RSS/Finnhub fallback (poll interval + 10 giây processing budget).
* **Failover/staleness:** sau 2 poll primary lỗi, fallback được thử đúng chu kỳ; last-good data vẫn đọc được nhưng có trạng thái stale/provider. Finnhub 429 không retry trước `Retry-After`; lỗi credential/entitlement phải hiện `unavailable`, không báo xanh.
* **Không mất/nhân đôi dữ liệu:** migration không làm mất dữ liệu Phase 1; chạy lại cùng fixtures không tạo thêm rows; revision chỉ tăng khi hash/canonical fields đổi; chart/news/order WebSocket hiện hữu vẫn tương thích.
* **Nghiệm thu Sprint:** toàn bộ test matrix bắt buộc đạt, SLO được đo bằng harness có kết quả lưu lại, không có regression tương thích/migration. Production chỉ bật từng provider sau khi production gate D5 của provider đó được xác nhận.