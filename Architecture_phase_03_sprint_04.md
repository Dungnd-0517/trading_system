# KIẾN TRÚC KỸ THUẬT: GIAI ĐOẠN 3 - SPRINT 4 (PHASE 03 - SPRINT 04)
## BÀN ĐIỀU HÀNH 4 AGENT (AGENT COUNCIL DECK) & LUỒNG THÔNG TIN TRỰC THỜI
### (REAL-TIME 4-AGENT COUNCIL DECK, COLLAPSIBLE UI & STREAMING INTELLIGENCE)

> **Trạng thái:** ARCHITECTURE SPECIFICATION & SPRINT BACKLOG PLAN  
> **Tài liệu nền:** [Architecture.md](Architecture.md), [technical_system.md](technical_system.md)  
> **Tài liệu Sprint trước:** [Architecture_phase_03_sprint_01.md](Architecture_phase_03_sprint_01.md), [Architecture_phase_03_sprint_02.md](Architecture_phase_03_sprint_02.md), [Architecture_phase_03_sprint_03.md](Architecture_phase_03_sprint_03.md), [Backlog.md](Backlog.md)  
> **Hồ sơ Cá nhân hóa Agent:** [Agents_Profile.md](Agents_Profile.md) (Arbiter, Sentinel, Vector, Scribe, Council)  
> **Framework tham chiếu:** Tauric Research TradingAgents, Fieldnote Markets Design System, Vue 3 Reactivity, Redis Pub/Sub, FastAPI WebSocket Hub, PostgreSQL + pgvector.  
> **Phạm vi (Scope):**  
> 1. **Bàn Điều Hành 4 Agent (Agent Council Deck):** Xây dựng component `AgentCouncilDeck.vue` dạng Card Deck / Accordion thu gọn thông minh (Collapsible) tích hợp trực tiếp vào cột bên phải (`aside.right-column`) của Trading Cockpit, thay thế và hợp nhất các panel rời rạc trước đây.  
> 2. **Minh Bạch Hóa 4 Chiều (4-Agent XAI Visualization):** Trực quan hóa toàn bộ nhận định, dữ liệu phân tích và chuỗi suy luận của 4 Agent AI:  
>    - **Arbiter Panel:** Báo cáo đồng thuận, tỷ lệ rủi ro/lệnh, hệ số SL ATR, Daily Drawdown Gauge và nút can thiệp khẩn cấp (Emergency Halt HITL).  
>    - **Sentinel Panel:** Thước đo cảm xúc thị trường (Macro Sentiment Gauge), cờ Circuit Breaker, đồng hồ đếm ngược tin tức đỏ, tương quan DXY và breaking news feed.  
>    - **Vector Panel:** Chế độ thị trường (Regime), xu hướng cấu trúc (Bias), độ tự tin (Confidence), độ tương đồng RAG và gợi ý Trade Setup (Entry/SL/TP/RR).  
>    - **Scribe Panel:** Thẻ Post-Mortem lệnh đóng gần nhất, phân loại nguyên nhân lỗi (Taxonomy), bài học rút ra và danh sách Active Memory Rules.  
> 3. **Cơ Chế Nạp Dữ Liệu Kép (Dual-Channel Hydration & Streaming):** REST API snapshot nạp trạng thái khởi tạo ngay khi mở trang (`GET /api/v1/agents/council/state`) kết hợp với luồng WebSocket thời gian thực (`/api/v1/ws/market` & channel `agent:state`) đảm bảo zero-lag và không bị rỗng giao diện.  
> 4. **Can Thiệp Con Người (HITL Control Integration):** Tích hợp nút khóa giao dịch khẩn cấp (Emergency Halt) gọi trực tiếp endpoint `POST /api/v1/agents/governor/override`, kết nối nghiêm ngặt với bộ rào chắn an toàn Hard Guardrails (Max Daily Drawdown 3%).  
> **Ngoài phạm vi (Out of Scope):** Khớp lệnh trên tài khoản MT5 Live bằng tiền thật (thuộc Phase 04); Fine-tuning lại model weights của LLM nền tảng.  
> **Ngày lập:** 2026-10-24  

---

## MỤC LỤC
1. [Mục Tiêu và Bối Cảnh Sprint 04](#1-mục-tiêu-và-bối-cảnh-sprint-04)
2. [Quyết Định Kiến Trúc Mới (Decision Log D32–D35)](#2-quyết-định-kiến-trúc-mới-decision-log-d32d35)
3. [Kiến Trúc Tổng Thể & Sơ Đồ Luồng Dữ Liệu](#3-kiến-trúc-tổng-thể--sơ-đồ-luồng-dữ-liệu)
4. [Đặc Tả Chi Tiết 4 Bảng Hiển Thị Agent (Council Deck Panels)](#4-đặc-tả-chi-tiết-4-bảng-hiển-thị-agent-council-deck-panels)
   - [4.1. Arbiter Panel (Risk & Hard Guardrails)](#41-arbiter-panel-quản-trị-rủi-ro--phán-quyết-tối-cao)
   - [4.2. Sentinel Panel (Macro Sentiment & News Guard)](#42-sentinel-panel-tình-báo-vĩ-mô--ngắt-mạch-tin-tức)
   - [4.3. Vector Panel (Technical Regime & RAG Setup)](#43-vector-panel-phân-tích-kỹ-thuật-hợp-lưu--rag-setup)
   - [4.4. Scribe Panel (Post-Mortem & Memory Rules)](#44-scribe-panel-phản-xạ-học-tập--bộ-nhớ-quy-tắc)
5. [Hợp Đồng Dữ Liệu: REST Hydration & WebSocket Protocol](#5-hợp-đồng-dữ-liệu-rest-hydration--websocket-protocol)
   - [5.1. REST Endpoint Nạp Khởi Tạo (`GET /api/v1/agents/council/state`)](#51-rest-endpoint-nạp-khởi-tạo-get-apiv1agentscouncilstate)
   - [5.2. WebSocket Event Schema (`AGENT_STATE_UPDATE`)](#52-websocket-event-schema-agent_state_update)
   - [5.3. Bảng Ánh Xạ Dữ Liệu Backend (Backend Pydantic Mapping)](#53-bảng-ánh-xạ-dữ-liệu-backend-backend-pydantic-mapping)
6. [Cấu Trúc State Management Frontend (`agentStore.js`)](#6-cấu-trúc-state-management-frontend-agentstorejs)
7. [Tích Hợp Giao Diện Vào Trading Cockpit (`App.vue`)](#7-tích-hợp-giao-diện-vào-trading-cockpit-appvue)
8. [Kế Hoạch Triển Khai Theo Task (Task Breakdown T1–T6)](#8-kế-hoạch-triển-khai-theo-task-task-breakdown-t1t6)
9. [Kiểm Thử, Chuẩn D18 & Tiêu Chuẩn Nghiệm Thu (Definition of Done)](#9-kiểm-thử-chuẩn-d18--tiêu-chuẩn-nghiệm-thu-definition-of-done)

---

## 1. MỤC TIÊU VÀ BỐI CẢNH SPRINT 04

### 1.1. Bối Cảnh Kế Thừa Từ Sprint 02 & Sprint 03
- **Sprint 02** đã xây dựng hoàn chỉnh năng lực tính toán của 4 tác tử AI cốt lõi:
  - `NewsEventAgent` (Sentinel): Cảm xúc vĩ mô, Circuit Breaker ngắt mạch tin đỏ USD.
  - `TechnicalRagAgent` (Vector): Nhận diện mô hình SMC/Wyckoff/ICT, truy vấn RAG 1536 chiều từ `pgvector`.
  - `ReflexionAgent` (Scribe): Mổ xẻ post-mortem lệnh đóng, gắn nhãn lỗi (taxonomy) và thăng cấp quy tắc vào bộ nhớ.
  - `StrategyGovernor` (Arbiter): Phán quyết rủi ro, áp đặt rào chắn an toàn Hard Guardrails (Drawdown $\ge 3\%$) và xuất bản Executive Briefing.
- **Sprint 03** đã hoàn thiện hệ thống Chat Real-time đa phiên (Gemini Layout + Floating Widget), quy chuẩn hóa định danh cá nhân [Agents_Profile.md](Agents_Profile.md), hệ thống nạp tri thức đa nguồn và Linux MT5 Bridge.

### 1.2. Thách Thức Đặt Ra Cho Sprint 04
Mặc dù 4 Agent đã hoạt động ổn định ở tầng Backend, giao diện Trading Cockpit hiện tại vẫn còn tồn tại các rào cản:
1. **Phân Mảnh Thị Giác:** Thông tin của các Agent bị rải rác: Governor Consensus ở một sub-tab, Reflexion ở dưới cùng, tin tức ở sub-tab khác, còn Technical RAG và chi tiết Trade Setup lại nằm ẩn trong tab Strategy & Analysis.
2. **Thiếu Khung Nhìn Toàn Cảnh (Council View):** Trader không thể quan sát đồng thời sự tương tác giữa 4 Agent khi thị trường biến động mạnh để ra quyết định giao dịch nhanh.
3. **Độ Trễ Trong Phản Ánh Học Tập:** Khi một lệnh vừa đóng (Paper Execution Fill/Stop), Trader không thấy ngay lập tức bài học rút ra và nguyên nhân gốc rễ trên màn hình chính Cockpit mà phải chuyển qua tab chuyên sâu.
4. **Cơ Chế Can Thiệp Khẩn Cấp (HITL) Cần Nhanh & Trực Quan Hơn:** Nút khóa khẩn cấp cần được đặt ngay tại vị trí trang trọng của Arbiter Panel để Trader có thể can thiệp trong vòng 1 cú click chuột.

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC MỚI (DECISION LOG D32–D35)

| ID | Quyết Định Kiến Trúc | Trạng Thái | Tác Động Kỹ Thuật & Lý Do Thiết Kế |
| :--- | :--- | :---: | :--- |
| **D32** | **Bộ Tổng Hợp Trạng Thái Hội Đồng Agent (Agent Council State Aggregator Service)** | `ACCEPTED` | Xây dựng service `backend/ai_engine/council_aggregator.py` tổng hợp snapshot trạng thái mới nhất từ 4 Agent thành một cấu trúc dữ liệu duy nhất `AgentCouncilState`. Giúp backend có một nguồn sự thật duy nhất (Single Source of Truth) phát sóng đồng thời qua REST API và Redis Pub/Sub channel `agent:state`. |
| **D33** | **Cơ Chế Nạp Kép Khởi Tạo & Phát Sóng (Dual-Channel Hydration: REST Snapshot + WebSocket Stream)** | `ACCEPTED` | Khi Frontend khởi động (`onMounted`), gọi ngay `GET /api/v1/agents/council/state` để hydrate đầy đủ dữ liệu cho 4 Agent (khắc phục hoàn toàn lỗi màn hình rỗng). Sau đó, kết nối WebSocket `/api/v1/ws/market` lắng nghe sự kiện `AGENT_STATE_UPDATE` để cập nhật trạng thái phản ứng thời gian thực với độ trễ $< 100\text{ms}$. |
| **D34** | **Thiết Kế Bàn Điều Hành Dạng Card Deck Thu Gọn (Collapsible Accordion / Card Deck Pattern)** | `ACCEPTED` | Thay vì xếp chồng 4 panel tĩnh gây tràn màn hình vượt quá $2000\text{px}$, triển khai component `AgentCouncilDeck.vue` với 4 card đại diện cho Arbiter, Sentinel, Vector, Scribe có khả năng thu gọn/mở rộng linh hoạt (Collapsible), ghi nhớ trạng thái đóng/mở qua LocalStorage hoặc component state, tích hợp hài hòa vào cột phải `aside.right-column`. |
| **D35** | **Khóa Khẩn Cấp HITL & Ràng Buộc Rào Chắn Cứng (Emergency Halt & Hard Guardrails Enforcement)** | `ACCEPTED` | Tích hợp nút Emergency Halt trực tiếp trên Arbiter Panel, kích hoạt hàm `agentStore.overrideParams()` gửi chỉ thị `POST /api/v1/agents/governor/override` với `trading_allowed = false`. Rào chắn cứng $3\%$ Daily Drawdown vẫn có quyền phủ quyết cao nhất: một khi Drawdown $\ge 3\%$, hệ thống tự động cưỡng chế cấm mở lệnh mới bất kể chỉ thị người dùng. |

---

## 3. KIẾN TRÚC TỔNG THỂ & SƠ ĐỒ LUỒNG DỮ LIỆU

```
+───────────────────────────────────────────────────────────────────────────────────────────────────+
|                                  FRONTEND LAYER (Vue 3 / Vite)                                    |
|                                                                                                   |
|  [ MÀN HÌNH TRADING COCKPIT: App.vue ]                                                            |
|  +---------------------------------------------+  +--------------------------------------------+  |
|  | TradingView Lightweight Chart (65% Width)   |  | ASIDE.RIGHT-COLUMN: AGENT COUNCIL DECK     |  |
|  | - Candlesticks, Volume, EMA, SL/TP Markers  |  | [ Tab: Council Deck ]                      |  |
|  | - Virtual Execution & Price Overlays        |  |  1. Arbiter Panel (Risk & Hard Guardrails) |  |
|  +---------------------------------------------+  |  2. Sentinel Panel (Macro & Circuit Break) |  |
|  | SIMULATION METRICS & ORDER BOOK TABLE       |  |  3. Vector Panel (Technical Regime & RAG)  |  |
|  +---------------------------------------------+  |  4. Scribe Panel (Post-Mortem & Memory)    |  |
|                                                   +--------------------------------------------+  |
|                                                                  ▲                                |
|                                                                  │ Reactive State                 |
|                                                +─────────────────┴─────────────────────────────+  |
|                                                | PINIA/REACTIVE STORE: agentStore.js           |  |
|                                                | - dashboard.arbiter, sentinel, vector, scribe |  |
|                                                | - actions: hydrateCouncilState(),             |  |
|                                                |   updateDashboard(), toggleEmergencyHalt()    |  |
|                                                +─────────────────▲─────────────────────────────+  |
+──────────────────────────────────────────────────────────────────┼────────────────────────────────+
                                                                   │ 
                                ┌──────────────────────────────────┴────────────────────────────────┐
                                │ 1. REST Hydration (onMounted)         2. WebSocket Stream         │
                                │    GET /api/v1/agents/council/state      /api/v1/ws/market        │
                                ▼                                       ▼                           │
+───────────────────────────────────────────────────────────────────────────────────────────────────┼
|                                  BACKEND CORE (FastAPI Service)                                   |
|                                                                                                   |
|  +---------------------------------------+  +--------------------------------------------------+  |
|  | AGENT COUNCIL STATE AGGREGATOR        |  | WEBSOCKET DISPATCHER HUB (websocket.py)          |  |
|  | (backend/ai_engine/council_aggregator)|  | - Subscribes to: market:ticks, paper:orders      |  |
|  | - Pulls from Governor, News, Tech,    |  |   governor:consensus, agent:state                |  |
|  |   Reflexion Services                  |  | - Emits: AGENT_STATE_UPDATE                      |  |
|  | - Generates unified JSON snapshot     |  |                                                  |  |
|  +-------------------▲-------------------+  +------------------------▲-------------------------+  |
|                      │                                               │                            |
+──────────────────────┼───────────────────────────────────────────────┼────────────────────────────+
                       │                                               │ Redis Pub/Sub              |
+──────────────────────▼───────────────────────────────────────────────▼────────────────────────────+
|                                       DATA & STORAGE LAYER                                        |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
|  | PostgreSQL            |  | pgvector (1536 dims) |  | Redis Pub/Sub      |  | Redis Cache    |  |
|  | - system_trading_config| - trading_knowledge    |  | - Channel:         |  | - runtime:     |  |
|  | - simulated_orders    |  - episodic_trade_memory|    agent:state        |    params:XAUUSD  |  |
|  | - agent_decision_logs |  (Cosine Similarity) |  | - Channel:         |  | - breaker:state|  |
|  |                       |                         |    market:ticks    |  |                |  |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 4. ĐẶC TẢ CHI TIẾT 4 BẢNG HIỂN THỊ AGENT (COUNCIL DECK PANELS)

Mỗi Agent đại diện cho một thẻ (Card) trong component `AgentCouncilDeck.vue`. Mỗi thẻ có Header hiển thị ngắn gọn thông tin cốt lõi khi thu gọn, và khu vực nội dung chi tiết khi mở rộng.

### 4.1. ARBITER PANEL (Quản Trị Rủi Ro & Phán Quyết Tối Cao)
Bảng trung tâm phản ánh quyền uy cao nhất trong việc bảo vệ vốn và cấp phép giao dịch.
- **Header Thẻ:**
  - Icon: 🛡️ / `ShieldCheck` (hoặc `ShieldAlert`).
  - Tên: **ARBITER** `(Risk & Hard Guardrails)`.
  - Huy hiệu giấy phép: `ALLOWED` (Xanh lá `#225c43` / `#c9f06b`), `RESTRICTED` (Vàng `#cb9a50`), `BLOCKED` (Đỏ `#c65345`).
- **Nội Dung Mở Rộng:**
  - **Risk Per Trade Meter:** Thanh đo trực quan thể hiện mức rủi ro hiện tại cho mỗi lệnh (Dải từ $0.25\%$ đến $1.50\%$, mặc định $1.00\%$).
  - **Dynamic ATR SL Multiplier:** Chỉ số nhân khoảng Stop Loss theo biến động thực tế ($1.00\text{x}$ đến $3.00\text{x}$ ATR).
  - **Daily Drawdown Gauge:** Thước đo trực quan mức sụt giảm tài khoản trong ngày hiện tại so với rào chắn cứng $3.00\%$. Kèm cảnh báo màu nếu Drawdown $> 2.0\%$.
  - **Reasoning Box:** Đoạn trích xuất ngắn giải thích lý do phán quyết (`rationale` từ `ConsensusReport`).
  - **Nút Khóa Khẩn Cấp (HITL Emergency Halt):**
    - Nếu trạng thái đang `ALLOWED`: Nút đỏ `[ KHÓA GIAO DỊCH KHẨN CẤP ]` $\rightarrow$ Gửi chỉ thị `trading_allowed = false`.
    - Nếu trạng thái đang `BLOCKED`: Nút xanh `[ MỞ LẠI GIAO DỊCH ]` $\rightarrow$ Thẩm định lại điều kiện an toàn và mở lại nếu Drawdown $< 3\%$.

### 4.2. SENTINEL PANEL (Tình Báo Vĩ Mô & Ngắt Mạch Tin Tức)
Bảng giám sát các biến số định tính ngoài thị trường, đo lường tâm lý vĩ mô và phòng ngừa thiên nga đen.
- **Header Thẻ:**
  - Icon: 📰 / `Newspaper` (hoặc `Radar`).
  - Tên: **SENTINEL** `(Macro & Circuit Breaker)`.
  - Huy hiệu Circuit Breaker: `NORMAL` (Xanh nhạt), `APPROACHING` (Cam cảnh báo), `HALT_ACTIVE` (Đỏ nhấp nháy).
- **Nội Dung Mở Rộng:**
  - **Macro Sentiment Gauge:** Thanh trượt ngang trực quan chia làm 3 vùng:
    - Bearish ($-1.00$ đến $-0.20$): Đỏ cam.
    - Neutral ($-0.20$ đến $+0.20$): Xám tro.
    - Bullish ($+0.20$ đến $+1.00$): Xanh lục.
  - **DXY Correlation Bias:** Thẻ xu hướng đồng USD tương quan (`BEARISH_DXY` $\rightarrow$ tích cực cho Vàng, `BULLISH_DXY` $\rightarrow$ tiêu cực cho Vàng).
  - **Next High-Impact Event Clock:** Bộ đếm ngược thời gian thực (Countdown) tới sự kiện kinh tế đỏ USD gần nhất kèm số sao tác động (ví dụ: *"USD Core CPI - còn 28 phút"*).
  - **Breaking News Alert Feed:** Danh sách 2-3 tin nóng gần nhất có gắn nhãn mức độ khẩn cấp (`CRITICAL`, `HIGH`, `MEDIUM`).

### 4.3. VECTOR PANEL (Phân Tích Kỹ Thuật Hợp Lưu & RAG Setup)
Bảng mổ xẻ cấu trúc hành động giá, nến M15 và trích xuất mẫu hình từ cơ sở dữ liệu tri thức Vector.
- **Header Thẻ:**
  - Icon: 📐 / `TrendingUp` (hoặc `Layers`).
  - Tên: **VECTOR** `(Technical Regime & RAG)`.
  - Huy hiệu Market Regime: `TRENDING_EXPANSION`, `HIGH_VOLATILITY`, `COMPRESSION_CHOP`.
- **Nội Dung Mở Rộng:**
  - **Structural Bias & Confidence:** Xu hướng (`BULLISH` / `BEARISH` / `NEUTRAL`) đi kèm thanh tiến trình mức độ tự tin ($0\% - 100\%$).
  - **RAG Knowledge Match Box:** Tên mẫu hình kỹ thuật có độ tương đồng Cosine Similarity cao nhất trong `pgvector` kèm tỷ lệ $\%$ khớp (ví dụ: *"Wyckoff Spring Phase C at Support (92% Match)"*).
  - **Suggested Trade Setup Box:** Khung tóm tắt kịch bản vào lệnh:
    - Hành động: `BUY` / `SELL` / `WAIT`.
    - Vùng giá kích hoạt (Entry Zone): Ví dụ `[4128.50 - 4132.00]`.
    - Stop Loss đề xuất & Take Profit mục tiêu (R:R $\ge 1.5$).

### 4.4. SCRIBE PANEL (Phản Xạ Học Tập & Bộ Nhớ Quy Tắc)
Bảng kiểm toán hiệu quả lệnh, phân tích sai lầm sau khi đóng lệnh và danh sách quy tắc đang áp dụng.
- **Header Thẻ:**
  - Icon: 🧠 / `Brain` (hoặc `BookOpen`).
  - Tên: **SCRIBE** `(Reflexion & Memory Rules)`.
  - Huy hiệu kết quả lệnh gần nhất: `WIN` (Xanh) / `LOSS` (Đỏ) / `NO_TRADES`.
- **Nội Dung Mở Rộng:**
  - **Post-Mortem Trade Card:** Thẻ tóm tắt thông tin lệnh vừa đóng gần nhất:
    - Ticket ID, Hướng lệnh (`BUY`/`SELL`), Lợi nhuận thực tế (`realized_pnl` USD & $\%$, ví dụ: `-$38.50 (-0.38%)`).
    - Nhãn nguyên nhân lỗi (Root Cause Taxonomy): `SL_TOO_TIGHT`, `EARLY_ENTRY`, `CHASED_PRICE`, `VOLATILITY_EXPANSION`.
    - Bài học đúc kết: Chuỗi văn bản phân tích ngắn từ `reflexion_service`.
  - **Active Memory Rules List:** Danh sách các quy tắc rút ra gần đây đã được thăng cấp vào bộ nhớ dài hạn và đang có hiệu lực trong chiến lược giao dịch.

---

## 5. HỢP ĐỒNG DỮ LIỆU: REST HYDRATION & WEBSOCKET PROTOCOL

Nhằm giải quyết dứt điểm vấn đề màn hình rỗng khi tải trang, Sprint 04 áp dụng cơ chế nạp dữ liệu hai lớp:

### 5.1. REST Endpoint Nạp Khởi Tạo (`GET /api/v1/agents/council/state`)
- **Route:** `GET /api/v1/agents/council/state`
- **Mục đích:** Nạp snapshot trạng thái tức thì của cả 4 Agent ngay khi màn hình Cockpit được mount.
- **Mã phản hồi HTTP:** `200 OK`
- **Payload Response:** Hoàn toàn đồng nhất với cấu trúc JSON Payload mục 5.2.

### 5.2. WebSocket Event Schema (`AGENT_STATE_UPDATE`)
- **Kênh lắng nghe:** WebSocket `/api/v1/ws/market` (hoặc alias `/api/v1/ws/agents`).
- **Redis Channel nguồn:** `agent:state`.
- **Event Type:** `AGENT_STATE_UPDATE`.

```json
{
  "type": "AGENT_STATE_UPDATE",
  "timestamp": 1727834400,
  "payload": {
    "arbiter": {
      "permission": "ALLOWED",
      "current_risk_percent": 1.00,
      "sl_multiplier": 1.50,
      "daily_drawdown_pct": 0.45,
      "regime_tag": "COMPRESSION_CHOP",
      "reason_summary": "Thị trường nén biến động nhẹ. Giữ rủi ro 1.0% với SL 1.5x ATR.",
      "hard_breaker_active": false
    },
    "sentinel": {
      "sentiment_score": 0.20,
      "circuit_breaker_active": false,
      "circuit_breaker_status": "NORMAL",
      "dxy_bias": "BEARISH_DXY",
      "next_event": {
        "title": "USD Core CPI YoY",
        "countdown_seconds": 1800,
        "impact_stars": 3
      },
      "recent_news": [
        {
          "id": "news_101",
          "source": "Kitco News",
          "title": "Gold holds steady ahead of US inflation data",
          "urgency": "MEDIUM",
          "time_ago": "2m ago"
        }
      ]
    },
    "vector": {
      "bias": "BULLISH",
      "regime": "COMPRESSION_CHOP",
      "confidence": 85,
      "rag_similarity": 92,
      "pattern_match": "Wyckoff Spring Phase C at Support",
      "primary_school": "WYCKOFF",
      "suggested_trade_setup": {
        "action": "BUY",
        "entry_zone": [4128.50, 4132.00],
        "suggested_sl": 4118.00,
        "suggested_tp": 4155.00,
        "planned_risk_reward": 2.25
      },
      "action_recommendation": "Ưu tiên canh Mua tại vùng kiểm định Spring với SL đặt dưới đáy cú quét."
    },
    "scribe": {
      "last_trade": {
        "id": 1048,
        "order_type": "BUY",
        "realized_pnl": -38.50,
        "outcome": "LOSS",
        "mistake_category": "SL_TOO_TIGHT",
        "root_cause": "Swept liquidity during London open due to tight SL buffer.",
        "lesson_learned": "Expand ATR SL buffer to 1.8x during high-volatility session overlaps."
      },
      "active_memory_rules": [
        "Nới SL thêm 12 points trong phiên London mở cửa.",
        "Khóa lệnh BUY nếu tin CPI công bố cao hơn dự báo 0.2%."
      ]
    }
  }
}
```

### 5.3. Bảng Ánh Xạ Dữ Liệu Backend (Backend Pydantic Mapping)

| Phân Vùng JSON | Trường JSON | Thuộc Tính Model Backend | Nguồn Dữ Liệu / Module |
| :--- | :--- | :--- | :--- |
| **`arbiter`** | `permission` | `"ALLOWED" if active_params.trading_allowed else "BLOCKED"` | `ConsensusReport` / `strategy_governor` |
| | `current_risk_percent`| `active_params.risk_per_trade_percent` | `ConsensusReport` |
| | `sl_multiplier` | `active_params.atr_sl_multiplier` | `ConsensusReport` |
| | `daily_drawdown_pct` | `current_daily_drawdown_pct` | `ConsensusReport` |
| | `regime_tag` | `market_regime` | `ConsensusReport` |
| | `reason_summary` | `rationale` | `ConsensusReport` |
| | `hard_breaker_active` | `current_daily_drawdown_pct >= 3.0` | `strategy_governor` |
| **`sentinel`** | `sentiment_score` | `macro_sentiment_score` ($-1.00$ đến $+1.00$) | `MacroInsightReport` |
| | `circuit_breaker_active`| `active_circuit_breaker` (Boolean) | `MacroInsightReport` |
| | `circuit_breaker_status`| `circuit_breaker_details.status` (`NORMAL`/`APPROACHING`/`HALT_ACTIVE`) | `MacroInsightReport` |
| | `dxy_bias` | `dxy_correlation_bias` | `MacroInsightReport` |
| | `next_event` | Bản ghi đầu tiên trong `high_impact_events_upcoming` | `news_event_agent` |
| | `recent_news` | Mảng trích xuất từ `breaking_news_alerts` & `FinancialNews` | `news_event_agent` |
| **`vector`** | `bias` | `structural_bias` (`BULLISH`/`BEARISH`/`NEUTRAL`) | `TechnicalAnalysisReport` |
| | `regime` | `market_regime` | `TechnicalAnalysisReport` |
| | `confidence` | `confidence_score * 100` | `TechnicalAnalysisReport` |
| | `rag_similarity` | `retrieved_knowledge_chunks[0].similarity_score * 100` | `pgvector` Cosine Similarity |
| | `pattern_match` | `retrieved_knowledge_chunks[0].title` | `technical_rag_agent` |
| | `primary_school` | `primary_school` | `TechnicalAnalysisReport` |
| | `suggested_trade_setup`| `suggested_trade_setup` (Object Entry/SL/TP/RR) | `TechnicalAnalysisReport` |
| **`scribe`** | `last_trade` | Bản ghi gần nhất trong `EpisodicTradeMemory` join `SimulatedOrder` | `reflexion_service` |
| | `mistake_category` | `last_memory.mistake_category` | `EpisodicTradeMemory` |
| | `active_memory_rules`| Mảng quy tắc `rule_to_add` đã được thăng cấp | `trading_knowledge` (source: `REFLEXION_PROMOTED`) |

---

## 6. CẤU TRÚC STATE MANAGEMENT FRONTEND (`agentStore.js`)

Mở rộng `frontend/src/stores/agentStore.js` với cụm state `dashboard` và khớp hoàn toàn các phương thức API hiện hữu:

```javascript
// frontend/src/stores/agentStore.js (Bổ sung State và Actions cho Sprint 04)

export const agentStore = reactive({
  // 1. Nhóm State Bàn điều hành 4 Agent (Council Deck)
  dashboard: {
    arbiter: {
      permission: 'ALLOWED',
      current_risk_percent: 1.0,
      sl_multiplier: 1.5,
      daily_drawdown_pct: 0.0,
      regime_tag: 'COMPRESSION_CHOP',
      reason_summary: '',
      hard_breaker_active: false,
    },
    sentinel: {
      sentiment_score: 0.0,
      circuit_breaker_active: false,
      circuit_breaker_status: 'NORMAL',
      dxy_bias: 'NEUTRAL',
      next_event: null,
      recent_news: [],
    },
    vector: {
      bias: 'NEUTRAL',
      regime: 'COMPRESSION_CHOP',
      confidence: 50,
      rag_similarity: 0,
      pattern_match: '',
      primary_school: 'GENERAL',
      suggested_trade_setup: null,
      action_recommendation: '',
    },
    scribe: {
      last_trade: null,
      active_memory_rules: [],
    },
    lastUpdated: null,
    loading: false,
  },

  // 2. Hydrate trạng thái khởi tạo qua REST API
  async hydrateCouncilState() {
    this.dashboard.loading = true
    try {
      const data = await fetchAgentCouncilStateApi()
      if (data?.payload) {
        this.updateAgentDashboardState(data.payload)
      }
    } catch (err) {
      console.warn('Lỗi khi nạp Council State ban đầu:', err)
    } finally {
      this.dashboard.loading = false
    }
  },

  // 3. Cập nhật trạng thái theo sự kiện WebSocket (AGENT_STATE_UPDATE)
  updateAgentDashboardState(payload) {
    if (!payload) return
    if (payload.arbiter) Object.assign(this.dashboard.arbiter, payload.arbiter)
    if (payload.sentinel) Object.assign(this.dashboard.sentinel, payload.sentinel)
    if (payload.vector) Object.assign(this.dashboard.vector, payload.vector)
    if (payload.scribe) Object.assign(this.dashboard.scribe, payload.scribe)
    this.dashboard.lastUpdated = new Date()
  },

  // 4. Action can thiệp khẩn cấp (Emergency Halt) - Khớp đúng phương thức overrideParams sẵn có
  async toggleEmergencyHalt(reason = 'Khóa khẩn cấp từ Bàn điều hành Trader') {
    const isCurrentlyAllowed = this.dashboard.arbiter.permission === 'ALLOWED'
    const newAllowedState = !isCurrentlyAllowed
    return await this.overrideParams({
      trading_allowed: newAllowedState,
      halt_reason: newAllowedState ? null : reason,
    })
  },
})
```

---

## 7. TÍCH HỢP GIAO DIỆN VÀO TRADING COCKPIT (`App.vue`)

### 7.1. Bố Cục Tích Hợp Tại Cột Phải (`aside.right-column`)
Nhằm loại bỏ sự phân tán và trùng lặp với giao diện cũ, cấu trúc sub-tab tại cột phải được chuẩn hóa như sau:

```html
<!-- Sub-panel Tab Switcher tại aside.right-column -->
<div class="column-switcher" role="tablist" aria-label="Right column sub navigation">
  <button
    class="switch-btn"
    :class="{ active: rightPanelTab === 'council' }"
    @click="rightPanelTab = 'council'"
    title="Bàn điều hành 4 Agent thời gian thực"
  >
    <BrainCircuit :size="12" />
    <span>Council Deck</span>
  </button>
  <button
    class="switch-btn"
    :class="{ active: rightPanelTab === 'dialogue' }"
    @click="rightPanelTab = 'dialogue'"
  >
    <MessageSquare :size="12" />
    <span>Dialogue &amp; HITL</span>
  </button>
  <button
    class="switch-btn"
    :class="{ active: rightPanelTab === 'news' }"
    @click="rightPanelTab = 'news'"
  >
    <Newspaper :size="12" />
    <span>News &amp; Macro</span>
  </button>
</div>

<!-- NỘI DUNG TAB 1: BÀN ĐIỀU HÀNH 4 AGENT -->
<template v-if="rightPanelTab === 'council'">
  <AgentCouncilDeck
    @open-knowledge="showKnowledgeModal = true"
    @open-strategy="activeTab = 'strategy'"
    @open-dialogue="rightPanelTab = 'dialogue'"
  />
</template>
```

### 7.2. Tuân Thủ Hệ Thống Design Tokens Fieldnote Markets
Toàn bộ giao diện của `AgentCouncilDeck.vue` và các sub-panels sử dụng các biến token chuẩn xác từ `style.css`:
- **Màu nền Card & Border:** Nền `var(--paper)` (`#f8faf6`), đường viền `var(--line)` (`#d9e0d9`), góc bo tròn `border-radius: 7px`.
- **Màu chữ & Nhãn:** Chữ chính `var(--ink)` (`#1b2a23`), phụ đề `var(--muted)` (`#77847c`), font monospace cho số liệu tài chính `var(--mono)` (`'DM Mono'`).
- **Màu sắc trạng thái Agent:**
  - Arbiter: Vàng cát `#d0b674` / Nền `#f2e8cb` / Accent `#8b6b23`.
  - Sentinel: Tím than / Badge `badge-purple`.
  - Vector: Xanh dương / Badge `badge-blue`.
  - Scribe: Xanh lục `#225c43` / Lime `#c9f06b` / Badge `badge-green`.
  - Ngắt mạch / Báo động: Đỏ `#c65345`.
- **Khả Năng Thu Gọn (Collapsible Accordion):** Cho phép mở đồng thời nhiều card hoặc chỉ một card (tùy trader cấu hình), hỗ trợ phím tắt thu gọn toàn bộ để quan sát tổng thể.

---

## 8. KẾ HOẠCH TRIỂN KHAI THEO TASK (TASK BREAKDOWN T1–T6)

Kế hoạch thực hiện Phase 03 - Sprint 04 được phân rã thành 6 Task kỹ thuật bài bản, độc lập và bảo toàn nghiêm ngặt chuẩn phân lập kiểm thử D18:

| Mã Task | Tên Task & Trách Nhiệm Kỹ Thuật | Sản Phẩm Bàn Giao Cụ Thể | Tiêu Chuẩn Hoàn Thành (DoD) |
| :--- | :--- | :--- | :--- |
| **Task 1** | **Backend Council State Aggregator Service & REST API Router** | Module `backend/ai_engine/council_aggregator.py`, router endpoint `GET /api/v1/agents/council/state` trong `api/v1/agents_governor.py`. | Snapshot 4 Agent được tạo tức thì $< 50\text{ms}$, trả về chuẩn JSON Schema, unit tests backend pass 100%. |
| **Task 2** | **WebSocket Broadcaster Hub & Redis Channel `agent:state`** | Bổ sung channel `agent:state` vào `_CHANNELS` trong `api/v1/websocket.py`, hook phát sự kiện tự động khi có biến động từ Governor / Reflexion / News. | Phát sóng `AGENT_STATE_UPDATE` qua WebSocket ngay khi có trạng thái mới, độ trễ phát $< 30\text{ms}$. |
| **Task 3** | **Mở Rộng Store Frontend (`agentStore.js`) & API Client Service** | Cập nhật `frontend/src/services/api.js` (`fetchAgentCouncilStateApi`), mở rộng cụm state `dashboard` trong `agentStore.js`, action `hydrateCouncilState()`, `toggleEmergencyHalt()`. | Nạp snapshot thành công khi mount, merge chính xác các gói WebSocket, xử lý an toàn khi mất kết nối mạng. |
| **Task 4** | **Phát Triển Component Bàn Điều Hành `AgentCouncilDeck.vue`** | Component `AgentCouncilDeck.vue` tại `frontend/src/components/AIAnalysis/` với 4 panel thu gọn (Arbiter, Sentinel, Vector, Scribe), thanh đo trực quan, Dark/Fieldnote styling. | Hiển thị sắc nét, accordion đóng mở mượt mà (CSS transition 0.2s), không vỡ layout trên mọi kích thước màn hình $\ge 1366\text{px}$. |
| **Task 5** | **Tích Hợp Trading Cockpit (`App.vue`) & Hook Lệnh Đóng Post-Mortem** | Tích hợp vào `aside.right-column` trong `App.vue`, gắn hook lắng nghe WebSocket `AGENT_STATE_UPDATE` và sự kiện `order.update` để kích hoạt Scribe refresh. | Mở màn hình Cockpit thấy ngay 4 Agent hoạt động, đóng lệnh paper trading lập tức thấy thẻ Post-Mortem của Scribe cập nhật. |
| **Task 6** | **Kiểm Thử Toàn Diện, Phân Lập D18 & Biên Dịch Hệ Thống (Validation & Build)** | Bộ test suite backend `test_council_aggregator_sprint4.py`, kiểm thử dọn dẹp CSDL test, biên dịch frontend `npm run build`. | 100% backend tests pass (134/134 hiện tại + tests mới), frontend build hoàn tất không lỗi cú pháp. |

---

## 9. KIỂM THỬ, CHUẨN D18 & TIÊU CHUẨN NGHIỆM THU (DEFINITION OF DONE)

### 9.1. Rào Chắn An Toàn & Chuẩn Phân Lập D18
- **100% D18 Compliant:** Mọi kiểm thử tự động phát sinh bản ghi trong `agent_decision_logs`, `episodic_trade_memory` hoặc `simulated_orders` phải gắn cờ `is_test = TRUE`. Fixture tự động quét dọn sạch dữ liệu test sau khi hoàn tất test suite.
- **Bảo Vệ Vốn Bất Biến:** Hard Guardrails ($3\%$ Max Daily Drawdown) luôn có quyền phủ quyết tuyệt đối. Nút Emergency Halt trên giao diện chỉ là cơ chế chủ động bổ sung cho Trader.

### 9.2. Tiêu Chí Nghiệm Thu Tổng Thể (Definition of Done - DoD)
- [ ] Endpoint `GET /api/v1/agents/council/state` hoạt động ổn định và trả về đúng schema JSON của 4 Agent.
- [ ] Kênh WebSocket `/api/v1/ws/market` phát sóng sự kiện `AGENT_STATE_UPDATE` thông suốt qua channel Redis `agent:state`.
- [ ] Component `AgentCouncilDeck.vue` hiển thị đầy đủ 4 Agent tại cột phải Cockpit dưới dạng Card Deck / Accordion thu gọn mượt mà.
- [ ] Giao diện tuân thủ 100% hệ thống design tokens trong `style.css`, sắc nét, chuyên nghiệp, không vỡ layout từ độ phân giải $1366\text{x}768$ trở lên.
- [ ] Hydration khởi tạo thành công khi tải trang: Không có khoảnh khắc hiển thị trắng/rỗng hoặc lỗi font số.
- [ ] Thanh đo Sentiment Gauge (Sentinel) và Progress Bar Confidence/RAG (Vector) hiển thị đúng tỉ lệ giá trị thực tế.
- [ ] Khi có lệnh Paper Trading vừa đóng, Scribe Panel hiển thị ngay thẻ Post-Mortem kèm taxonomy lỗi và quy tắc mới.
- [ ] Bấm nút Emergency Halt trên Arbiter Panel khóa ngay lập tức quyền mở lệnh mới và hiển thị badge `BLOCKED`.
- [ ] Toàn bộ Backend Test Suite đạt kết quả **Passed 100%** trong Docker container.
- [ ] Frontend biên dịch thành công xuất sắc qua lệnh `npm run build` không có cảnh báo nghiêm trọng hay lỗi cú pháp.
- [ ] Tiến độ và kết quả bàn giao được cập nhật minh bạch vào [Backlog.md](Backlog.md).