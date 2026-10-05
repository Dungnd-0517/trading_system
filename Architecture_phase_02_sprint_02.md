# KIẾN TRÚC KỸ THUẬT: GIAI ĐOẠN 2 - SPRINT 2

> **Trạng thái:** SPEC READY FOR IMPLEMENTATION. Quyết định D7–D11 đã chốt.  
> **Tài liệu nền:** [Architecture.md](Architecture.md)  
> **Tài liệu trước:** [Architecture_phase_02_sprint_01.md](Architecture_phase_02_sprint_01.md)  
> **Phạm vi (Scope):** Tích hợp Binance PAXGUSDT làm Data Feed 24/7 cho XAUUSD; Động cơ khớp lệnh giả lập nội bộ (Paper Execution Engine Worker); Trực quan hóa SL/TP/Markers trên TradingView; Bảng điều khiển Trading Cockpit.  
> **Ngoài phạm vi (Out of Scope):** Kết nối MT5 Live Execution thật (để dành Giai đoạn 3); Phân tích AI tự động phát tín hiệu vào lệnh (Sprint 3); Tự động hóa quản lý vốn danh mục nhiều tài sản.  
> **Ngày cập nhật:** 2026-10-02  

---

## MỤC LỤC
1. [Mục tiêu và Phạm vi](#1-mục-tiêu-và-phạm-vi-sprint-objectives)
2. [Quyết định Kiến trúc (Decision Log D7–D11)](#2-quyết-định-kiến-trúc-decision-log)
3. [Kiến trúc Tổng thể & Luồng Dữ liệu (Architecture & Data Flow)](#3-kiến-trúc-tổng-thể--luồng-dữ-liệu)
4. [Data Pipeline: Binance PAXG/USDT Feed & Symbol Mapping](#4-data-pipeline-binance-paxgusdt-feed--symbol-mapping)
5. [Động cơ Khớp lệnh Giả lập (Paper Execution Engine & Worker)](#5-động-cơ-khớp-lệnh-giả-lập-paper-execution-engine)
6. [Hợp đồng API & WebSocket (API & WebSocket Contracts)](#6-hợp-đồng-api--websocket-contracts)
7. [Mô hình Dữ liệu & Migration Additive](#7-mô-hình-dữ-liệu--migration-additive)
8. [Kiến trúc Frontend & Trực quan hóa Trading Cockpit](#8-kiến-trúc-frontend--trực-quan-hóa-trading-cockpit)
9. [Kế hoạch Triển khai theo Task (Task Breakdown)](#9-kế-hoạch-triển-khai-theo-task)
10. [Kiểm thử, SLO & Tiêu chuẩn Nghiệm thu (DoD)](#10-kiểm-thử-slo--tiêu-chuẩn-nghiệm-thu)

---

## 1. MỤC TIÊU VÀ PHẠM VI (SPRINT OBJECTIVES)

1. **Khắc phục nút thắt Broker MT5:** Tích hợp trực tiếp WebSocket cặp `PAXGUSDT` từ Binance Spot (neo giá vàng 1:1 bằng ounce vàng thật, thanh khoản 24/7, không cần API key) để cấp dữ liệu nến, volume và giá nhảy sub-second cho symbol `XAUUSD`, giúp hệ thống vận hành hoàn toàn độc lập với môi trường MT5/Wine.
2. **Hoàn thiện Paper Execution Engine:** Nâng cấp module khớp lệnh giả lập nội bộ chạy nền (background worker) trên giá tick thực tế, tự động quét kiểm tra SL/TP từng tick, tính toán trượt giá (slippage) và phát sinh sự kiện khớp/đóng lệnh theo thời gian thực.
3. **Trực quan hóa toàn diện trên TradingView Lightweight Charts:** Vẽ trực tiếp trên biểu đồ nến các đường giá Entry, Stop Loss (đỏ), Take Profit (xanh lục) và các điểm đánh dấu (Markers) vào lệnh/đóng lệnh.
4. **Bảng điều khiển Cockpit tương tác:** Hiển thị giá live nhảy xanh/đỏ trên Header, cho phép người dùng đóng vị thế thủ công bằng 1 click, và theo dõi số dư/Equity/PnL tức thời.

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC (DECISION LOG)

| ID | Quyết định | Trạng thái | Tác động kỹ thuật |
|---|---|---|---|
| **D7** | **Tích hợp Binance PAXGUSDT vào `ChartStreamer` có sẵn; Symbol Alias sang `XAUUSD`** | `ACCEPTED` | Tái sử dụng `CandleAggregator` của Sprint 1 để tự động tổng hợp nến M1, M5, M15, H1, lưu DB `market_candles` và phát `chart.update` chuẩn; không phân mảnh sang service riêng. |
| **D8** | **Mở rộng Schema Additive qua Migration `0003_phase2_sprint2.sql`** | `ACCEPTED` | Giữ nguyên 100% các cột và khóa ngoại `ai_market_context_id` của `simulated_orders` Phase 1. Bổ sung `ticket_uuid`, `slippage`, `commission`, `swap`, `close_reason`. Thêm bảng `simulation_account`. |
| **D9** | **Chuẩn hóa Paper Engine Worker & Quét SL/TP theo Tick Bid/Ask** | `ACCEPTED` | Kế thừa logic tính toán chính xác của `backend/simulation/paper_engine.py` (khớp BUY theo Ask, SELL theo Bid); worker chạy nền lắng nghe Redis `market:ticks`, cập nhật trạng thái lệnh và ghi DB bất đồng bộ. |
| **D10** | **Giữ nguyên Endpoint `/api/v1/ws/market` & Bổ sung Event `order.update`** | `ACCEPTED` | Không chia tách thành các endpoint WS mới. Phát event `order.update` trên kênh Redis `paper:orders` đã có sẵn; frontend nhận diện qua `event.type === 'order.update'`. Thêm REST API `POST /api/v1/orders/{id}/close`. |
| **D11** | **Mở rộng trực tiếp các Component hiện có (`TradingViewChart.vue`, `OrderBookTable.vue`)** | `ACCEPTED` | Không tạo component song song. Dùng API `createPriceLine` và `setMarkers` trên chart hiện tại; bổ sung action `closeOrder` vào `orderStore` và nút Close trên bảng lệnh. |

---

## 3. KIẾN TRÚC TỔNG THỂ & LUỒNG DỮ LIỆU

```
+───────────────────────────────────────────────────────────────────────────────+
|                               DATA INGESTION HUB                              |
|                                                                               |
|  [ Binance WebSocket ] ─────────► [ ChartStreamer ]                           |
|  - paxgusdt@kline_1m              - CandleAggregator (M1, M5, M15, H1)        |
|  - Symbol Mapping:                - Synthetic ECN Spread (Bid/Ask)            |
|    PAXGUSDT -> XAUUSD             - Upsert PostgreSQL (market_candles)        |
+──────────────────────────────────────────┬────────────────────────────────────+
                                           │ Redis PUBLISH "market:ticks"
                                           ▼
+───────────────────────────────────────────────────────────────────────────────+
|                               REDIS PUB/SUB HUB                               |
|                                                                               |
|   Channel "market:ticks"   ──────► Lắng nghe: FastAPI WS + Paper Engine       |
|   Channel "paper:orders"   ──────► Lắng nghe: FastAPI WS                      |
|   Channel "news:events"    ──────► Lắng nghe: FastAPI WS (từ Sprint 1)        |
+─────────────────────┬────────────────────────────────────┬────────────────────+
                      │                                    │
                      ▼                                    ▼
+──────────────────────────────────────+  +─────────────────────────────────────+
|    FASTAPI WEBSOCKET HUB             |  |      PAPER EXECUTION WORKER         |
|    (backend/api/v1/websocket.py)     |  |      (simulation/paper_worker.py)   |
|                                      |  |                                     |
| Single Endpoint:                     |  |  1. Nhận tick giá (Bid / Ask)       |
| GET /api/v1/ws/market                |  |  2. Quét SL/TP danh sách OPEN       |
|                                      |  |  3. Khớp đóng lệnh & tính Real PnL  |
| Multiplexed Events:                  |  |  4. Cập nhật PostgreSQL             |
| - type: "chart.update" (Nến & Ticks) |  |  5. Publish "paper:orders"          |
| - type: "order.update" (Lệnh & PnL)  |  +─────────────────────────────────────+
| - type: "news.upsert"  (Tin tức)     |
+─────────────────────┬────────────────+
                      │ WebSocket Frames (JSON)
                      ▼
+───────────────────────────────────────────────────────────────────────────────+
|                         FRONTEND TRADING COCKPIT (Vue 3)                      |
|                                                                               |
|  [ Header / Topbar ]           - Hiển thị Live Price, Spread, Clock, Balance  |
|  [ TradingViewChart.vue ]      - Candlesticks + Volume + PriceLine (SL/TP)    |
|                                - Markers (Vào lệnh / Đóng lệnh kèm PnL)       |
|  [ OrderBookTable.vue ]        - Vị thế mở, PnL live, Nút [ Close Order ]     |
|  [ MetricsCards.vue ]          - Realized PnL, Winrate %, Closed Trades       |
|  [ NewsStream.vue ]            - Tin tức gắn sao (⭐, ⭐⭐, ⭐⭐⭐) từ Sprint 1    |
+───────────────────────────────────────────────────────────────────────────────+
```

---

## 4. DATA PIPELINE: BINANCE PAXG/USDT FEED & SYMBOL MAPPING

### 4.1. Cơ chế Mapping & Đơn vị tính
* **Tài sản cơ sở:** PAX Gold (PAXG) là token ERC-20 được chứng thực 100% bằng vàng vật chất tại hầm lưu trữ Brink's (Luân Đôn), với tỷ lệ quy đổi $1 \text{ PAXG} = 1 \text{ Troy Ounce Vàng}$.
* **Mapping quy ước (D7):** Cặp `PAXGUSDT` từ Binance được chuẩn hóa và ánh xạ sang mã giao dịch nội bộ `XAUUSD`.
* **Khối lượng (Volume):** Khối lượng giao dịch từ Binance là số lượng ounce vàng (`base_asset_quantity`). Giữ nguyên quy ước của Sprint 1: `volume.unit = "base_asset_quantity"`.

### 4.2. Giả lập Spread ECN (Synthetic Spread Injector)
Để phản ánh đúng điều kiện giao dịch tài khoản Forex/ECN Gold truyền thống (thường có spread khoảng 20 points $\approx$ $0.20/oz$), `ChartStreamer` sinh giá 2 chiều từ giá khớp `close`:
$$\text{Synthetic Bid} = \text{Close Price} - 0.10$$
$$\text{Synthetic Ask} = \text{Close Price} + 0.10$$
$$\text{Spread} = \text{Ask} - \text{Bid} = 0.20 \text{ USD (20 points)}$$

### 4.3. Tích hợp trực tiếp vào `ChartStreamer`
Không tạo service riêng biệt. Module [`backend/data_ingestion/chart_streamer.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/data_ingestion/chart_streamer.py) mở rộng hàm `_run_binance()`:
1. Kết nối stream `paxgusdt@kline_1m`.
2. Truyền payload vào `self.aggregator.ingest_kline()` với symbol `XAUUSD`.
3. Tự động tính nến M1, M5, M15, H1, ghi vào DB `market_candles` và phát event `chart.update` ra Redis `market:ticks`.
4. Khi khởi tạo: gọi REST API `https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=1m&limit=500` để nạp sẵn nến lịch sử nếu DB chưa có dữ liệu.

---

## 5. ĐỘNG CƠ KHỚP LỆNH GIẢ LẬP (PAPER EXECUTION ENGINE)

Hệ thống kế thừa và đóng gói [`backend/simulation/paper_engine.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/simulation/paper_engine.py) thành kiến trúc chuẩn Broker Provider.

### 5.1. Interface Lõi (`core/interfaces/executor.py`)

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseOrderExecutor(ABC):
    @abstractmethod
    async def open_order(
        self, symbol: str, side: str, lots: float, 
        stop_loss: float, take_profit: float, strategy_trigger: str | None = None
    ) -> dict[str, Any]:
        """Tạo và khớp một vị thế mới với giá thị trường kèm slippage"""
        pass

    @abstractmethod
    async def close_order(self, order_id: int, reason: str = "MANUAL_CLOSE") -> dict[str, Any]:
        """Đóng vị thế theo yêu cầu thủ công hoặc khẩn cấp"""
        pass

    @abstractmethod
    async def on_tick(self, symbol: str, bid: float, ask: float) -> list[dict[str, Any]]:
        """Quét và xử lý tự động SL/TP theo từng tick thị trường"""
        pass
```

### 5.2. Logic Khớp lệnh & Quét SL/TP (D9)

1. **Khớp lệnh thị trường (Market Order Execution):**
   * Giả lập độ trượt giá ngẫu nhiên (Slippage): từ $0.00$ đến $0.05$ USD ($0 - 5$ points).
   * Lệnh `BUY`: Khớp tại $\text{Entry Price} = \text{Ask} + \text{Slippage}$.
   * Lệnh `SELL`: Khớp tại $\text{Entry Price} = \text{Bid} - \text{Slippage}$.
   * Ràng buộc giá hợp lệ:
     * `BUY`: $\text{Stop Loss} < \text{Entry Price} < \text{Take Profit}$.
     * `SELL`: $\text{Take Profit} < \text{Entry Price} < \text{Stop Loss}$.

2. **Quy chuẩn tính PnL Vàng quốc tế (1 Lot = 100 oz):**
   * Lệnh `BUY`:
     $$\text{Realized PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Lot Size} \times 100$$
   * Lệnh `SELL`:
     $$\text{Realized PnL} = (\text{Entry Price} - \text{Exit Price}) \times \text{Lot Size} \times 100$$

3. **Thuật toán quét SL/TP theo Tick (Chuẩn xác theo giá 2 chiều Bid/Ask):**
   * Mỗi khi có tick mới từ Redis `market:ticks`:
     * Lệnh **BUY**:
       * Đóng khi $\text{Bid} \le \text{Stop Loss} \implies \text{Exit Price} = \text{Bid}, \text{close\_reason} = \text{'SL\_HIT'}$.
       * Đóng khi $\text{Bid} \ge \text{Take Profit} \implies \text{Exit Price} = \text{Bid}, \text{close\_reason} = \text{'TP\_HIT'}$.
     * Lệnh **SELL**:
       * Đóng khi $\text{Ask} \ge \text{Stop Loss} \implies \text{Exit Price} = \text{Ask}, \text{close\_reason} = \text{'SL\_HIT'}$.
       * Đóng khi $\text{Ask} \le \text{Take Profit} \implies \text{Exit Price} = \text{Ask}, \text{close\_reason} = \text{'TP\_HIT'}$.
   * Đóng lệnh ngay trong chu kỳ tick; cập nhật DB trạng thái `CLOSED`, gán `close_time`, tính toán `realized_pnl` và phát event `order.update` sang Redis `paper:orders`.

---

## 6. HỢP ĐỒNG API & WEBSOCKET (API & WEBSOCKET CONTRACTS)

### 6.1. Hợp đồng WebSocket (D10 — ACCEPTED)
Tất cả client kết nối vào một endpoint duy nhất: `GET /api/v1/ws/market`.

#### Event 1: Nến và Giá Live (`chart.update` — Giữ nguyên D4)
```json
{
  "type": "chart.update",
  "symbol": "XAUUSD",
  "timeframe": "M1",
  "timestamp": 1774972800,
  "candle": {
    "time": 1774972800,
    "open": 2685.00,
    "high": 2686.50,
    "low": 2684.20,
    "close": 2685.80
  },
  "volume": {
    "time": 1774972800,
    "value": 14.5,
    "unit": "base_asset_quantity",
    "color": "up"
  },
  "price": {
    "value": 2685.80,
    "bid": 2685.70,
    "ask": 2685.90
  }
}
```

#### Event 2: Trạng thái Vị thế Lệnh (`order.update` — Mới trong Sprint 2)
```json
{
  "type": "order.update",
  "event": "ORDER_FILLED",
  "data": {
    "id": 1001,
    "ticket_uuid": "c4b8b6e2-5c7a-4d2b-9e4a-9b4f2c0d1e5a",
    "symbol": "XAUUSD",
    "order_type": "BUY",
    "status": "FILLED",
    "lot_size": 0.10,
    "entry_price": 2685.90,
    "exit_price": null,
    "stop_loss": 2680.00,
    "take_profit": 2695.00,
    "open_time": "2026-10-02T05:40:00Z",
    "close_time": null,
    "realized_pnl": null,
    "close_reason": null
  }
}
```
Khi lệnh đóng do SL/TP hoặc đóng tay:
```json
{
  "type": "order.update",
  "event": "ORDER_CLOSED",
  "data": {
    "id": 1001,
    "ticket_uuid": "c4b8b6e2-5c7a-4d2b-9e4a-9b4f2c0d1e5a",
    "symbol": "XAUUSD",
    "order_type": "BUY",
    "status": "CLOSED",
    "lot_size": 0.10,
    "entry_price": 2685.90,
    "exit_price": 2695.00,
    "stop_loss": 2680.00,
    "take_profit": 2695.00,
    "open_time": "2026-10-02T05:40:00Z",
    "close_time": "2026-10-02T05:45:20Z",
    "realized_pnl": 91.00,
    "close_reason": "TP_HIT"
  }
}
```

### 6.2. Hợp đồng REST API
* `GET /api/v1/orders` : Lấy danh sách lệnh gần nhất (đã có từ Phase 1).
* `POST /api/v1/orders` : Mở vị thế mới (đã có từ Phase 1, nâng cấp tính trượt giá).
* `POST /api/v1/orders/{id}/close` **(Mới)**:
  * **Path param:** `id` (int).
  * **Payload (tùy chọn):** `{ "reason": "MANUAL_CLOSE" }`.
  * **Phản hồi 200 OK:** Chi tiết lệnh đã đóng kèm `realized_pnl`.
* `GET /api/v1/simulation/account` **(Mới)**:
  * **Phản hồi 200 OK:**
    ```json
    {
      "initial_balance": 10000.00,
      "current_balance": 10245.50,
      "equity": 10295.50,
      "margin_used": 268.59,
      "free_margin": 10026.91,
      "open_positions_count": 1
    }
    ```

---

## 7. MÔ HÌNH DỮ LIỆU & MIGRATION ADDITIVE

Tuân thủ **D3 (ACCEPTED)**: Sử dụng migration additive `0003_phase2_sprint2.sql`, không thay đổi các cột hiện hữu hay xóa khóa ngoại Phase 1.

```sql
-- Migration: backend/migrations/0003_phase2_sprint2.sql

-- 1. Bổ sung các cột nâng cao cho simulated_orders
ALTER TABLE simulated_orders 
    ADD COLUMN IF NOT EXISTS ticket_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS slippage NUMERIC(8, 4) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS commission NUMERIC(8, 2) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS swap NUMERIC(8, 2) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS close_reason VARCHAR(32);

-- Tạo index cho ticket_uuid
CREATE UNIQUE INDEX IF NOT EXISTS uq_simulated_orders_ticket_uuid 
    ON simulated_orders(ticket_uuid);

-- 2. Tạo bảng quản lý tài khoản giả định
CREATE TABLE IF NOT EXISTS simulation_account (
    id SERIAL PRIMARY KEY,
    initial_balance NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    current_balance NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    equity NUMERIC(12, 2) NOT NULL DEFAULT 10000.00,
    margin_used NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Khởi tạo tài khoản mặc định nếu chưa tồn tại
INSERT INTO simulation_account (id, initial_balance, current_balance, equity)
VALUES (1, 10000.00, 10000.00, 10000.00)
ON CONFLICT (id) DO NOTHING;
```

---

## 8. KIẾN TRÚC FRONTEND & TRỰC QUAN HÓA TRADING COCKPIT

### 8.1. Trực quan hóa Vị thế trên `TradingViewChart.vue` (D11)
Tận dụng các API có sẵn của TradingView Lightweight Charts (v4.x):

1. **Vẽ các đường giá ngang (Price Lines):**
   * Đối với mỗi vị thế `OPEN` thuộc symbol đang xem:
     * **Đường Entry:** `color: '#2196F3'`, `lineStyle: 2` (Đứt nét), `title: 'BUY #1001'`
     * **Đường Stop Loss:** `color: '#F44336'`, `lineStyle: 0` (Nét liền), `title: 'SL'`
     * **Đường Take Profit:** `color: '#4CAF50'`, `lineStyle: 0` (Nét liền), `title: 'TP'`
   * Lưu trữ instance của price lines theo `order_id` trong component; khi nhận event `ORDER_CLOSED`, gọi `candleSeries.removePriceLine(line)` để dọn dẹp.

2. **Đánh dấu điểm vào/đóng lệnh (Markers):**
   * Gọi `candleSeries.setMarkers()`:
     * Vào lệnh BUY: `shape: 'arrowUp'`, `color: '#26a69a'`, `position: 'belowBar'`, `text: 'BUY 0.1'`
     * Vào lệnh SELL: `shape: 'arrowDown'`, `color: '#ef5350'`, `position: 'aboveBar'`, `text: 'SELL 0.1'`
     * Đóng lệnh: `shape: 'circle'`, `color: pnl >= 0 ? '#26a69a' : '#ef5350'`, `position: 'inBar'`, `text: '+$91.00'`

### 8.2. Cập nhật `OrderBookTable.vue` & Store
* Bổ sung cột thao tác **ACTION** với nút bấm `[ Đóng lệnh ]` (Close).
* Khi click: gọi action `orderStore.closeOrder(order.id)`.
* Hiển thị PnL chưa chốt (Unrealized PnL) nhảy theo từng tick thị trường trên từng dòng lệnh.

### 8.3. Cập nhật `App.vue` Header & Live Price
* Thay thế nhãn tĩnh `-- LIVE PRICE` bằng giá Bid/Ask thực tế nhảy động liên tục.
* Tự động chuyển màu xanh lục khi giá tăng so với tick trước, chuyển màu đỏ khi giá giảm.

---

## 9. KẾ HOẠCH TRIỂN KHAI THEO TASK

| Mã Task | Phân tầng | Nội dung triển khai | Kết quả bàn giao (Deliverables) | Phụ thuộc |
| :--- | :--- | :--- | :--- | :--- |
| **T2.1** | **Database** | Viết file migration SQL và cập nhật model `SimulatedOrder`, `SimulationAccount` trong SQLAlchemy. | `backend/migrations/0003_phase2_sprint2.sql`, `backend/core/models.py` | Không |
| **T2.2** | **Ingestion** | Mở rộng `ChartStreamer` nạp klines `PAXGUSDT` từ Binance, sinh spread giả lập, lưu `market_candles` và bắn `chart.update`. | `backend/data_ingestion/chart_streamer.py` | T2.1 |
| **T2.3** | **Paper Engine** | Cài đặt `BaseOrderExecutor`, hoàn thiện `PaperEngineWorker` chạy nền quét SL/TP theo tick từ Redis, cập nhật PnL và broadcast `paper:orders`. | `backend/simulation/paper_worker.py`, `backend/simulation/paper_engine.py` | T2.1, T2.2 |
| **T2.4** | **API Router** | Bổ sung API `POST /api/v1/orders/{id}/close` và `GET /api/v1/simulation/account`. | `backend/api/v1/orders.py` | T2.3 |
| **T2.5** | **Frontend Chart**| Tích hợp `createPriceLine` (Entry, SL, TP) và `setMarkers` (Buy, Sell, PnL) vào `TradingViewChart.vue`. | `frontend/src/components/Chart/TradingViewChart.vue` | T2.2, T2.4 |
| **T2.6** | **Frontend UI** | Thêm nút đóng lệnh vào `OrderBookTable.vue`, cập nhật header live price và liên kết `orderStore`. | `frontend/src/App.vue`, `frontend/src/components/Simulation/OrderBookTable.vue` | T2.4, T2.5 |

---

## 10. KIỂM THỬ, SLO & TIÊU CHUẨN NGHIỆM THU

### 10.1. Ma trận Kiểm thử Bắt buộc (Test Matrix)
1. **Binance PAXG Feed Ingestion:** Kiểm tra kết nối WebSocket, xử lý tự động reconnect khi ngắt mạng, xác minh nến M1 được tính đúng OHLCV và lưu thành công vào `market_candles`.
2. **Spread & Slippage Simulator:** Xác minh mọi lệnh BUY đều có `entry = ask + slippage`, lệnh SELL có `entry = bid - slippage`.
3. **Tick Monitoring & SL/TP Hit:**
   * Test fixture: Lệnh BUY với SL 2680, TP 2700. Khi tick giả lập phát `bid = 2679.5`, lệnh phải được chuyển sang `CLOSED` với `close_reason = 'SL_HIT'`.
   * Test fixture: Lệnh SELL với SL 2710, TP 2690. Khi tick giả lập phát `ask = 2689.0`, lệnh phải được chuyển sang `CLOSED` với `close_reason = 'TP_HIT'`.
4. **WebSocket Integration:** Kết nối 1 client, gửi 5 lệnh giả định; xác minh client nhận đủ các event `order.update` dạng `ORDER_FILLED` và `ORDER_CLOSED` mà không làm gián đoạn luồng `chart.update`.
5. **Database Integrity:** Migration chạy trên DB đã có dữ liệu Phase 1 không làm rơi rụng bản ghi hay mất khóa ngoại `ai_market_context_id`.

### 10.2. Tiêu chuẩn SLO
* **Độ trễ phản hồi SL/TP (Engine Reaction Latency):** Thời gian từ khi tick Redis chạm mốc SL/TP đến khi bản ghi DB chuyển `CLOSED` và event `order.update` được phát ra: **p95 ≤ 30 ms**.
* **WebSocket Rendering Throughput:** Giao diện biểu đồ và bảng lệnh render mượt mà ở tốc độ cập nhật **5 - 10 ticks/giây** mà không bị giật lag (frame rate duy trì $\ge$ 55 fps).

### 10.3. Tiêu chí Hoàn thành Sprint (Definition of Done - DoD)
* [ ] Nến `XAUUSD` hiển thị liên tục trên giao diện từ nguồn Binance `PAXGUSDT`, không còn thông báo `NO HISTORICAL DATA`.
* [ ] Header hiển thị giá nhảy live xanh/đỏ theo từng tick.
* [ ] Tạo lệnh BUY/SELL qua API hoặc UI: Ngay lập tức xuất hiện 3 đường ngang (Entry, SL, TP) và marker mũi tên trên chart.
* [ ] Bấm nút `[ Đóng lệnh ]` trên bảng lệnh: Vị thế lập tức đóng, tính toán đúng PnL và biến mất khỏi danh sách lệnh mở.
* [ ] Giá thị trường chạm SL hoặc TP: Động cơ tự động đóng lệnh, các đường ngang trên chart biến mất và thay thế bằng marker đóng lệnh hiển thị số tiền lãi/lỗ (+/- PnL).
* [ ] Toàn bộ test suite backend và frontend build đều vượt qua (`pytest` và `npm run build` không có lỗi).