# KIẾN TRÚC KỸ THUẬT: PHASE 03 - SPRINT 04
## UI/UX Agent Dashboard Panels & Real-Time Intelligence Stream

---

## 1. TỔNG QUAN KIẾN TRÚC (SYSTEM OVERVIEW)

Sprint 04 tập trung triển khai **Bàn điều hành 4 Agent (Agent Dashboard Panels / Agent Council Deck)** trên giao diện Trading Cockpit (Vue 3 / Vanilla CSS Tokens kế thừa `style.css`). Mục tiêu kỹ thuật cốt lõi là minh bạch hóa toàn bộ chuỗi suy luận (Chain of Thought), nhận định thị trường và nhật ký học tập (Reflexion) của 4 Agent AI thời gian thực, đồng thời cung cấp cơ chế can thiệp con người (Human-in-the-Loop - HITL) đối với động cơ thực thi lệnh.

```
+---------------------------------------------------------------------------------------------------+
|                                 FRONTEND (Vue 3 / Reactive Stores)                                |
|  +-------------------------------------+  +----------------------------------------------------+  |
|  | TradingView Lightweight Chart (65%) |  | AGENT COUNCIL DECK (35% Right Column)              |  |
|  | - Candlesticks, Volume, SL/TP       |  | 1. Arbiter Panel (Risk & Hard Guardrails Core)     |  |
|  | - Order Markers & Execution Overlay |  | 2. Sentinel Panel (Macro Sentiment & News Stream)  |  |
|  +-------------------------------------+  | 3. Vector Panel (Technical Regime & RAG Pattern)   |  |
|  | SIMULATION ORDER BOOK & PNL TABLE   |  | 4. Scribe Panel (Reflexion & Memory Rules)         |  |
|  +-------------------------------------+  +----------------------------------------------------+  |
+--------------------------------------------------▲------------------------------------------------+
                                                   │ WebSocket (/api/v1/ws/agents hoặc /api/v1/ws/market)
+--------------------------------------------------▼------------------------------------------------+
|                                    BACKEND CORE (FastAPI Monolith)                                |
|                                                                                                   |
|  +----------------------+  +---------------------+  +--------------------+  +------------------+  |
|  |  Data Ingestion Hub  |  |  TradingAgents      |  | Paper Execution Eng|  | WebSocket Hub    |  |
|  |  - Tick & News Stream|  |  - 4-Agent Pipeline |  | - Virtual Fill     |  | - Realtime State |  |
|  |  - MT5 / Twelve Data |  |  - RAG Search (pgv) |  | - SL/TP Trigger    |  | - Agent Broad-   |  |
|  |                      |  |  - Hard Guardrails  |  |                    |  |   caster Worker  |  |
|  +----------▲-----------+  +----------▲----------+  +---------▲----------+  +--------▲---------+  |
+-------------│-------------------------│-----------------------│----------------------│------------+
              │                         │                       │                      │
+-------------▼-------------------------▼-----------------------▼----------------------▼------------+
|                                      DATA & STORAGE LAYER                                         |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
|  | PostgreSQL            |  | pgvector             |  | Redis Pub/Sub      |  | Redis Key/Value|  |
|  | - Simulated Orders    |  | - RAG Knowledge Base |  | - Channel:         |  | - Runtime      |  |
|  | - Daily Metrics       |  | - Episodic Memory    |  |   agent:state      |  |   Params Cache |  |
|  | - Trading Config      |  |   (1536 dims)        |  | - Channel:         |  | - Circuit      |  |
|  |                       |  |                      |  |   market:ticks     |  |   Breaker State|  |
|  +-----------------------+  +----------------------+  +--------------------+  +----------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. NGUYÊN TẮC KỸ THUẬT & MỤC TIÊU SPRINT 04

1. **Explainable AI (XAI) & Structured Output:** Toàn bộ phản hồi từ LLM Engine của 4 Agent phải tuân thủ nghiêm ngặt Pydantic Schema, được chuẩn hóa thành JSON cấu trúc trước khi phát qua WebSocket Hub về Client.
2. **Real-time Reactive State (Vue 3 `agentStore.js` Sync):** Giao diện không sử dụng cơ chế Polling HTTP định kỳ. Mọi biến động chỉ số (Sentiment Score, Confidence Rate, Memory Rule) được cập nhật theo sự kiện (Event-driven) qua luồng WebSocket bất đồng bộ, phản xạ trực tiếp vào Vue 3 `reactive` store.
3. **Decoupled Architecture (Tách biệt độ trễ):** Vòng lặp tính toán của 4 Agent (suy luận LLM mất 0.5s – 2s) chạy độc lập hoàn toàn với Vòng lặp Khớp lệnh (Fast Execution Engine < 50ms trong `auto_executor.py` và `paper_worker.py`).
4. **Human-In-The-Loop (HITL) Controls:** Cung cấp cơ chế ghi đè (Override) quyền hạn ngay trên UI: Khóa giao dịch khẩn cấp (Emergency Halt) gọi trực tiếp endpoint `POST /api/v1/agents/governor/override` (đi qua Hard Guardrails 3% Max Daily Drawdown).
5. **Ergonomic Layout Integration:** Không xếp chồng 4 panel tĩnh gây tràn màn hình (> 2000px). Áp dụng mô hình **`AgentCouncilDeck.vue`** dạng Card Deck / Accordion có khả năng thu gọn (Collapsible), tích hợp hài hòa vào cột bên phải (`aside.right-column`) của Cockpit song song với các tab `Consensus`, `Dialogue & HITL` và `News & Macro`.

---

## 3. ĐẶC TẢ CẤU TRÚC BẢNG HIỂN THỊ 4 AGENT (AGENT PANELS SPECIFICATION)

### 3.1. ARBITER PANEL (Giám Đốc Quản Trị Rủi Ro & Phán Quyết Tối Cao)
Bảng trung tâm hiển thị kết quả đồng thuận (Consensus) và kiểm soát rào chắn an toàn cứng (Hard Constraints) từ `strategy_governor.py`.
- **Chỉ số & Phần tử Giao diện (UI Elements):**
  - **Execution Permission Badge:** Trạng thái phân màu `ALLOWED` (Xanh lá - cho phép mở lệnh) / `RESTRICTED` (Vàng - siết chặt tham số) / `BLOCKED` (Đỏ - cấm mở lệnh).
  - **Risk Per Trade Meter:** Tỷ lệ phần trăm rủi ro cho phép đặt cho lệnh kế tiếp (0.25% đến 1.50%).
  - **Dynamic SL Multiplier Indicator:** Hệ số nhân khoảng Stop Loss tính theo ATR (1.00x ATR đến 3.00x ATR).
  - **Daily Drawdown Gauge:** Hiển thị mức sụt giảm tài khoản trong ngày so với ngưỡng ngắt mạch cứng 3.00%.
  - **Reasoning Text Box:** Chuỗi giải thích ngắn gọn nguyên nhân đưa ra phán quyết (`rationale`).
  - **Emergency Halt Toggle Button:** Nút can thiệp người dùng để khóa toàn bộ quyền mở lệnh mới lập tức thông qua API override.

### 3.2. SENTINEL PANEL (Trợ Lý Tình Báo Vĩ Mô & Tin Tức Tức Thời)
Bảng giám sát các biến số định tính ngoài thị trường và lọc nhiễu sự kiện từ `news_agent.py` & `news_guard.py`.
- **Chỉ số & Phần tử Giao diện (UI Elements):**
  - **Macro Sentiment Gauge:** Thanh đo cảm xúc thị trường dạng trục nằm ngang (-1.00 Bearish $\rightarrow$ 0.00 Neutral $\rightarrow$ +1.00 Bullish).
  - **Circuit Breaker Status Badge:** Hiển thị trạng thái bộ ngắt mạch tin tức đỏ (`NORMAL`, `APPROACHING`, `HALT_ACTIVE`).
  - **Event Countdown Clock:** Bộ đếm ngược thời gian thực tới sự kiện kinh tế đỏ USD gần nhất (Ví dụ: USD Core CPI - 18:30 ICT).
  - **Live Breaking News Feed:** Dòng tin tức ForexFactory/Kitco được quét gần nhất kèm nhãn tác động (`CRITICAL`, `HIGH`, `MEDIUM`).
  - **DXY Correlation Bias:** Xu hướng Dollar Index tương quan với Vàng (`BULLISH_DXY`, `BEARISH_DXY`, `NEUTRAL`).

### 3.3. VECTOR PANEL (Kỹ Sư Cấu Trúc Kỹ Thuật & Tra Cứu RAG)
Bảng phân tích mô hình giá, chỉ báo định lượng và đối chiếu tri thức từ cơ sở dữ liệu Vector (`pgvector` 1536 chiều) từ `technical_agent.py`.
- **Chỉ số & Phần tử Giao diện (UI Elements):**
  - **Market Regime Tag:** Trạng thái chế độ thị trường (`TRENDING_EXPANSION`, `HIGH_VOLATILITY_EXPANSION`, `COMPRESSION_CHOP`).
  - **Structural Bias:** Xu hướng ưu tiên (`BULLISH`, `BEARISH`, `NEUTRAL`).
  - **RAG Knowledge Match Box:** Tên mẫu hình hoặc bộ quy tắc kỹ thuật có độ tương đồng Cosine Similarity cao nhất trong Vector DB (Ví dụ: *"SMC Liquidity Grab at Support"*).
  - **Confidence Score Progress Bar:** Mức độ tự tin của tín hiệu kỹ thuật (0% – 100%).
  - **Suggested Trade Setup:** Vùng giá canh vào lệnh (Entry Zone), khoảng giá SL và TP dự kiến theo tỷ lệ R:R.

### 3.4. SCRIBE PANEL (Kiểm Toán Viên Phản Xạ & Quản Lý Bộ Nhớ)
Bảng hiển thị quá trình tự học, mổ xẻ nguyên nhân thắng/thua sau mỗi lệnh đóng và danh sách quy tắc tự động rút ra từ `reflexion_service.py`.
- **Chỉ số & Phần tử Giao diện (UI Elements):**
  - **Post-Mortem Trade Card:** Thẻ tóm tắt thông tin lệnh vừa đóng gần nhất (Ticket ID, BUY/SELL, Realized PnL USD & %).
  - **Root Cause Breakdown:** Phân loại nguyên nhân gốc rễ (Taxonomy: `SL_TOO_TIGHT`, `EARLY_ENTRY`, `CHASED_PRICE`, `VOLATILITY_EXPANSION`).
  - **Lesson Learned Text:** Bài học đúc kết bằng ngôn ngữ tự nhiên.
  - **Active Memory Rules List:** Danh sách các quy tắc rút ra gần đây đã được lưu trữ vào bộ nhớ dài hạn (`episodic_trade_memory`) và đang áp dụng vào hệ thống.

---

## 4. KIẾN TRÚC LUỒNG DỮ LIỆU & SCHEMA STATE MANAGEMENT

### 4.1. Kênh Truyền Dữ Liệu Real-time (WebSocket Payload Contract)
Dữ liệu trạng thái của 4 Agent được phát từ Backend qua kênh WebSocket `/api/v1/ws/agents` (đồng thời dự phòng phát qua kênh chính `/api/v1/ws/market`) dưới dạng khung JSON tập trung:

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
      "max_lot_cap": 0.50,
      "regime_tag": "COMPRESSION_CHOP",
      "reason_summary": "Thị trường nén biến động nhẹ. Giữ rủi ro 1.0% với SL 1.5x ATR."
    },
    "sentinel": {
      "sentiment_score": 0.20,
      "circuit_breaker_active": false,
      "impact_tier": 1,
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
      "pattern_match": "SMC Liquidity Sweep at Support",
      "primary_school": "SMC",
      "action_recommendation": "Ưu tiên canh Mua tại vùng quét thanh khoản với SL hẹp."
    },
    "scribe": {
      "last_trade": {
        "id": 1048,
        "type": "BUY",
        "pnl": -38.50,
        "outcome": "LOSS",
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

### 4.2. Bảng Ánh Xạ Dữ Liệu Backend (Backend Pydantic Mapping)

| Phân Vùng JSON | Trường JSON | Thuộc Tính Model Backend | Nguồn Dữ Liệu / Module |
| :--- | :--- | :--- | :--- |
| **`arbiter`** | `permission` | `"ALLOWED" if active_params.trading_allowed else "BLOCKED"` | `ai_engine.strategy_governor` |
| | `current_risk_percent`| `active_params.risk_per_trade_percent` | `ConsensusReport` |
| | `sl_multiplier` | `active_params.atr_sl_multiplier` | `ConsensusReport` |
| | `daily_drawdown_pct` | `current_daily_drawdown_pct` | `ConsensusReport` |
| | `regime_tag` | `market_regime` | `ConsensusReport` |
| | `reason_summary` | `rationale` | `ConsensusReport` |
| **`sentinel`** | `sentiment_score` | `macro_sentiment_score` (-1.00 đến +1.00) | `MacroInsightReport` |
| | `circuit_breaker_active` | `active_circuit_breaker` (True/False) | `MacroInsightReport` |
| | `next_event` | Phần tử đầu tiên trong `high_impact_events_upcoming` | `news_event_agent` |
| | `recent_news` | Mảng trích xuất từ `FinancialNews` & `breaking_news_alerts` | `news_event_agent` |
| **`vector`** | `bias` | `structural_bias` (`BULLISH`/`BEARISH`/`NEUTRAL`) | `TechnicalAnalysisReport` |
| | `confidence` | `confidence_score * 100` | `TechnicalAnalysisReport` |
| | `pattern_match` | `retrieved_knowledge_chunks[0].title` | `technical_rag_agent` |
| | `rag_similarity` | `retrieved_knowledge_chunks[0].similarity_score * 100` | `pgvector Cosine Sim` |
| **`scribe`** | `last_trade` | Bản ghi gần nhất trong `EpisodicTradeMemory` | `reflexion_service` |
| | `active_memory_rules`| Mảng quy tắc `rule_to_add` được ghim/promote | `episodic_trade_memory` |

### 4.3. Cấu Trúc Reactive State Store Phía Frontend (`agentStore.js`)
Frontend tiếp nhận WebSocket payload, tự động merge vào `agentStore.js` (sử dụng Vue 3 `reactive` singleton pattern hiện có):

```javascript
// frontend/src/stores/agentStore.js (mở rộng nhóm state cho Sprint 04)
export const agentStore = reactive({
  // 1. Nhóm dữ liệu 4 Agent theo thời gian thực
  dashboard: {
    arbiter: {
      permission: 'ALLOWED',
      current_risk_percent: 1.0,
      sl_multiplier: 1.5,
      daily_drawdown_pct: 0.0,
      max_lot_cap: 0.5,
      regime_tag: 'COMPRESSION_CHOP',
      reason_summary: '',
    },
    sentinel: {
      sentiment_score: 0.0,
      circuit_breaker_active: false,
      impact_tier: 1,
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
      action_recommendation: '',
    },
    scribe: {
      last_trade: null,
      active_memory_rules: [],
    },
    lastUpdated: null,
  },

  // 2. Actions xử lý dữ liệu
  updateAgentDashboardState(payload) {
    if (!payload) return
    if (payload.arbiter) Object.assign(this.dashboard.arbiter, payload.arbiter)
    if (payload.sentinel) Object.assign(this.dashboard.sentinel, payload.sentinel)
    if (payload.vector) Object.assign(this.dashboard.vector, payload.vector)
    if (payload.scribe) Object.assign(this.dashboard.scribe, payload.scribe)
    this.dashboard.lastUpdated = new Date()
  },

  // 3. Action can thiệp khẩn cấp (HITL Emergency Halt)
  async toggleEmergencyHalt(reason = 'Khóa khẩn cấp từ Bàn điều hành Trader') {
    const isCurrentlyAllowed = this.dashboard.arbiter.permission === 'ALLOWED'
    const newAllowedState = !isCurrentlyAllowed
    return await this.overrideParameters({
      trading_allowed: newAllowedState,
      halt_reason: newAllowedState ? null : reason,
    })
  },
})
```

---

## 5. BẢNG TIÊU CHÍ NGHIỆM THU (DEFINITION OF DONE - DOD)

1. **Hiển Thị & Thẩm Mỹ Nhất Quán:** Màn hình Trading Cockpit hiển thị đầy đủ 4 panel tương ứng với 4 Agent (Arbiter, Sentinel, Vector, Scribe) dưới dạng Card Deck hoặc Accordion thu gọn, sử dụng 100% hệ thống design tokens trong `style.css` (Dark Theme chuyên nghiệp, glassmorphism, không vỡ layout trên độ phân giải từ 1366x768 trở lên).
2. **Reactivity Thời Gian Thực:** Khi Backend đẩy gói WebSocket `AGENT_STATE_UPDATE` qua kênh `/api/v1/ws/agents` hoặc `/api/v1/ws/market`, các chỉ số trên cả 4 panel cập nhật tức thì (độ trễ phản xạ giao diện < 100ms) mà không cần tải lại trang.
3. **Thước Đo Trực Quan Chính Xác:**
   - Thanh đo cảm xúc (Sentiment Gauge) trên Sentinel Panel thể hiện chính xác trục từ -1.00 đến +1.00 kèm cờ Circuit Breaker cảnh báo.
   - Thang đo độ tự tin (Confidence Rate) và độ tương đồng RAG (Similarity Score) trên Vector Panel hiển thị trực quan qua Progress Bar tỉ lệ %.
4. **Phản Xạ Lệnh Đóng (Post-Mortem Hook):** Khi có một lệnh Paper Trading vừa đóng, Scribe Panel lập tức nhận sự kiện, hiển thị thẻ Post-Mortem tóm tắt nguyên nhân thắng/thua và bổ sung bài học mới vào danh sách Active Memory Rules.
5. **Cơ Chế Khóa Khẩn Cấp (HITL Emergency Halt) Đạt Chuẩn An Toàn:** Khi nhấn nút Emergency Halt trên Arbiter Panel, hệ thống gửi request `POST /api/v1/agents/governor/override`, ngay lập tức chuyển trạng thái `permission` sang `BLOCKED`, khóa toàn bộ quyền mở lệnh mới và ghi nhận nhật ký can thiệp của trader.