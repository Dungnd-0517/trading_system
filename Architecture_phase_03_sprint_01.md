LLM Agent: TradingAgents
Git: https://github.com/tauricresearch/tradingagents

### 1. Vị trí Kiến trúc: Phân tách Hoàn toàn với Vòng lặp Khớp lệnh (Decoupled Architecture)

Để đảm bảo hiệu năng khớp lệnh tức thời dưới 100ms, hệ thống TradingAgents được đóng gói thành một **Asynchronous Intelligence Service (Dịch vụ trí tuệ bất đồng bộ)** nằm trong `backend/ai_engine/`.

TradingAgents không can thiệp trực tiếp vào từng tick giá, mà đóng vai trò là một "Hội đồng Cố vấn" chạy nền, giao tiếp qua Redis Message Bus và PostgreSQL:

```
[ THỊ TRƯỜNG: TICK & NẾN ]
           │
           ▼
+──────────────────────────────────────────────────────────────────────────────+
| FAST EXECUTION ENGINE (Python Pure - Chạy liên tục mỗi tick)                 |
| - Kiểm tra tín hiệu kỹ thuật (Fast Math)                                     |
| - Giám sát SL/TP, Trailing Stop                                              |
| - Đọc bộ tham số hiện tại từ Redis: { SL_multiplier, Lot_cap, Regime }       |
+──────────────────────────────────────▲───────────────────────────────────────+
                                       │ Cập nhật tham số động (Mỗi 15p / theo sự kiện)
+──────────────────────────────────────┴───────────────────────────────────────+
| TRADINGAGENTS SUITE (Chạy nền bất đồng bộ qua ARQ / Async Worker)           |
|                                                                              |
|  1. News & Event Agent        2. Technical RAG Agent     3. Reflexion Agent  |
|  (Phân tích vĩ mô/tin tức)    (So khớp bài học/sách)     (Học từ lệnh đóng)  |
|               │                          │                        │          |
|               └──────────────────────────┼────────────────────────┘          |
|                                          ▼                                   |
|                          4. Strategy Governor Agent                          |
|                          - Tổng hợp đồng thuận (Consensus)                   |
|                          - Đề xuất thay đổi tham số chiến lược               |
+──────────────────────────────────────▲───────────────────────────────────────+
                                       │
+──────────────────────────────────────┴───────────────────────────────────────+
| MEMORY & KNOWLEDGE LAYER (PostgreSQL + pgvector)                             |
| - Vector DB: Tài liệu kỹ thuật SMC, Wyckoff, Price Action                    |
| - Episodic Memory: Nhật ký sai lầm và bài học kinh nghiệm (Post-mortem logs) |
+──────────────────────────────────────────────────────────────────────────────+

```

---

### 2. Cấu trúc 4 Agent Chuyên trách

Mô hình được tinh gọn từ framework của Tauric Research thành 4 vai trò rõ ràng:

| Tên Agent | Nhiệm vụ kỹ thuật | Chu kỳ kích hoạt | Đầu ra (Structured JSON) |
| --- | --- | --- | --- |
| **News & Event Agent** | Quét lịch kinh tế (FairEconomy) và tin RSS (Kitco, FXStreet). Phân loại tác động và phát hiện tin bất thường. | Mỗi 3–5 phút hoặc khi có tin breaking | `sentiment_score` (-1.0 đến +1.0), `impact_tier` (1–3), `market_risk_flag` (NORMAL / HIGH_RISK_HALT). |
| **Technical RAG Agent** | Lấy dữ liệu nến H1/M15 (EMA, ATR, Volume Profile), truy vấn Vector DB tìm mẫu hình và chiến lược tương ứng (SMC, Wyckoff). | Mỗi khi đóng nến M15 | `market_regime` (TRENDING / RANGING / CHOPPY), `suggested_bias` (LONG_ONLY / SHORT_ONLY / NEUTRAL). |
| **Reflexion Agent (Agent Học tập)** | Phân tích các lệnh vừa đóng (Win/Loss). So sánh bối cảnh lúc vào lệnh với nguyên nhân cắn SL/TP để tìm ra lỗi logic. | Kích hoạt ngay khi có lệnh `CLOSED` | `lesson_learned`, `mistake_category` (SL_TOO_TIGHT, TRADED_IN_NEWS, WRONG_BIAS), `rule_to_add`. |
| **Strategy Governor** | Đóng vai trò Trưởng ban Quản trị Rủi ro (CRO). Tiếp nhận nhận định từ 3 Agent trên để phê duyệt hoặc ghi đè tham số vận hành. | Mỗi 15 phút hoặc sau mỗi chu kỳ Reflexion | Bản ghi cập nhật `strategy_runtime_params`. |

---

### 3. Pipeline Tự học & Cải tiến Hiệu suất (Learning & Feedback Loop)

Quá trình "học" của hệ thống được khép kín qua 3 bước:

#### Bước 1: Nạp kiến thức nền tảng (Domain Knowledge Ingestion)

* Sử dụng extension `pgvector` tích hợp thẳng vào PostgreSQL hiện tại của Docker.
* **Quy trình:**
1. Nạp các tài liệu quy tắc giao dịch (chiến lược SMC, mô hình nến, bài học quản lý vốn) dạng Markdown/PDF vào thư mục `backend/knowledge_base/`.
2. Dùng embedding model gọn nhẹ (ví dụ: `text-embedding-3-small` hoặc mô hình HuggingFace cục bộ) để chuyển đổi thành vector và lưu vào bảng `trading_knowledge_vectors`.
3. Khi Technical Agent phân tích, nó tự động tìm các tài liệu tương ứng thông qua Cosine Similarity để bổ sung vào prompt ngữ cảnh.



#### Bước 2: Tự kiểm điểm lệnh (Reflexion on Closed Orders)

Khi một lệnh giả định (hoặc lệnh demo) đóng lại:

1. Engine gửi toàn bộ payload của lệnh: Điểm vào, Điểm thoát, Thời gian giữ lệnh, Drawdown tối đa trong lệnh (MAE/MFE), và tin tức diễn ra trong khoảng thời gian đó.
2. **Reflexion Agent chạy kiểm tra:**
* *Nếu lệnh LỖ:* Phân tích xem lỗi do chiến lược hay do nhiễu thị trường (Noise/News). Trích xuất bài học và lưu vào bảng `episodic_trade_memory`.
* *Nếu lệnh LÃI:* Xác nhận xem lệnh thắng có tuân thủ đúng tỷ lệ R:R hay chỉ là do may mắn ngược xu hướng.



#### Bước 3: Tinh chỉnh tham số động (Dynamic Hyperparameter Tuning)

Strategy Governor Agent đọc bảng bài học gần nhất và điều chỉnh các biến số trong bảng `strategy_runtime_params` (không sửa code, chỉ sửa tham số điều khiển):

* **Spread Buffer:** Nới rộng khoảng cách Stop Loss khi nhận thấy giá vàng thường xuyên quét qua mức hỗ trợ cũ 10–15 points rồi mới quay đầu.
* **Volume Scaling:** Tự động hạ hệ số rủi ro mỗi lệnh từ $1\%$ xuống $0.5\%$ nếu chuỗi lệnh gần nhất cho thấy thị trường bước vào pha biến động bất thường (Chop/High News).
* **Session Filtering:** Thêm quy tắc cấm giao dịch phiên Á nếu các bài học Reflexion chỉ ra rằng chiến lược Breakout bị tỷ lệ thua cao (False Breakout) trong khung giờ này.

---

### 4. Thiết kế Cơ sở Dữ liệu & Schema (PostgreSQL + pgvector)

> [!NOTE]
> **Đồng nhất Single Source of Truth:** Để đảm bảo tính tương thích 100% với Phase 02 và tránh phân mảnh cấu hình, hệ thống **không tạo bảng riêng `strategy_runtime_params`**, mà mở rộng trực tiếp bảng `system_trading_config` kết hợp Redis Cache (`runtime:params:XAUUSD`). Bảng `episodic_trade_memory` có cờ `is_test` theo chuẩn phân lập dữ liệu D18.

```sql
-- 1. Kích hoạt tiện ích vector cho Postgres (pgvector/pgvector:pg16)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Lưu trữ kiến thức và tài liệu chiến lược (RAG Knowledge Base)
CREATE TABLE IF NOT EXISTS trading_knowledge (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL, -- SMC, PRICE_ACTION, RISK_MANAGEMENT, MACRO, POST_MORTEM
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536),        -- Kích thước vector chuẩn OpenAI/Gemini/Local Hashing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_knowledge_category ON trading_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_trading_knowledge_embedding ON trading_knowledge USING hnsw (embedding vector_cosine_ops);

-- 3. Bộ nhớ trải nghiệm (Episodic Memory / Reflexion Post-Mortem Logs)
CREATE TABLE IF NOT EXISTS episodic_trade_memory (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES simulated_orders(id) ON DELETE CASCADE,
    outcome VARCHAR(16) NOT NULL,            -- WIN, LOSS, BREAKEVEN
    market_context_summary TEXT NOT NULL,  -- Bối cảnh thị trường lúc vào/thoát lệnh
    root_cause TEXT,                       -- Nguyên nhân cốt lõi (SL quá ngắn, tin ra...)
    lesson_learned TEXT NOT NULL,          -- Bài học kinh nghiệm rút ra
    mistake_category VARCHAR(64),          -- EARLY_ENTRY, SL_TOO_TIGHT, TRADED_DURING_NEWS_SPIKE, FOMO_CHASING...
    rule_to_add TEXT,                      -- Quy tắc đề xuất cho Governor cập nhật
    embedding vector(1536),                -- Hỗ trợ semantic search tìm bài học tương tự
    is_test BOOLEAN NOT NULL DEFAULT FALSE,-- Phân lập dữ liệu kiểm thử (D18)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_order_id ON episodic_trade_memory(order_id);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_outcome ON episodic_trade_memory(outcome);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_mistake ON episodic_trade_memory(mistake_category);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_is_test ON episodic_trade_memory(is_test);
CREATE INDEX IF NOT EXISTS idx_episodic_trade_memory_embedding ON episodic_trade_memory USING hnsw (embedding vector_cosine_ops);

-- 4. Mở rộng system_trading_config với các tham số thích ứng AI (Dynamic Runtime Parameters)
ALTER TABLE system_trading_config
    ADD COLUMN IF NOT EXISTS atr_sl_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    ADD COLUMN IF NOT EXISTS min_risk_reward_ratio NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
    ADD COLUMN IF NOT EXISTS trading_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS halt_reason TEXT,
    ADD COLUMN IF NOT EXISTS updated_by_agent VARCHAR(64) NOT NULL DEFAULT 'SYSTEM_INIT';
```

---

### 5. Bộ Rào chắn Cứng (Hard Constraints Guardrails)

Để triệt tiêu hoàn toàn rủi ro ảo giác (hallucination) hoặc việc Agent "học quá đà" (overfitting) dẫn đến phá hủy tài khoản, mọi đề xuất của Strategy Governor bắt buộc phải đi qua **Bộ lọc quy tắc cứng viết bằng Python thuần**:

```python
from pydantic import BaseModel, Field
from typing import Optional

class AgentParamAdjustment(BaseModel):
    risk_per_trade_percent: float = Field(..., ge=0.25, le=1.50)  # Cấm vượt quá 1.5%
    min_risk_reward_ratio: float = Field(..., ge=1.20, le=4.00)   # Không chấp nhận R:R < 1:1.2
    atr_sl_multiplier: float = Field(..., ge=1.00, le=3.00)       # SL không quá 3x ATR
    trading_allowed: bool = True
    halt_reason: Optional[str] = None
    updated_by_agent: str = "STRATEGY_GOVERNOR"

def validate_and_apply_adjustments(proposed_params: dict, current_daily_drawdown: float):
    # RÀO CHẮN 1: Nếu tổng lỗ trong ngày >= 3%, khóa cứng quyền giao dịch bất kể AI đề xuất gì
    if current_daily_drawdown >= 3.0:
        return {
            "trading_allowed": False,
            "halt_reason": "HARD_LIMIT_BREACHED: Max daily drawdown 3% reached."
        }

    # RÀO CHẮN 2: Ép kiểu và kiểm tra biên độ qua Pydantic
    validated = AgentParamAdjustment(**proposed_params)
    
    # Cập nhật vào DB system_trading_config & Redis Cache (runtime:params:XAUUSD)
    redis_client.set("runtime:params:XAUUSD", validated.model_dump_json())
    return validated.model_dump()
```

---

### 6. Tích hợp Hiển thị lên Giao diện Cockpit (Frontend UI)

Giao diện người dùng trên Vue 3 sẽ được bổ sung 2 panel tương tác:

```
+─────────────────────────────────────────+──────────────────────────────────────────+
| PANEL: MARKET CONTEXT & AGENT CONSENSUS | PANEL: AI REFLEXION & LESSONS LEARNED    |
+─────────────────────────────────────────+──────────────────────────────────────────+
| Regime: TRENDING UP (Độ tin cậy: 85%)   | [Lệnh #1042 - LOSS (-$52)]               |
| Tin tức: BÌNH THƯỜNG (Sentiment: +0.2)  | Bài học: Giá quét râu qua vùng kháng cự   |
| Rủi ro đề xuất: 0.8% / lệnh             | do phiên Âu mở cửa -> Tự động nới SL     |
| SL Multiplier: 1.8x ATR                 | thêm 15 points cho các lệnh cùng setup.  |
| Trạng thái: CHO PHÉP MỞ LỆNH            |                                          |
+─────────────────────────────────────────+──────────────────────────────────────────+
```

---

### 7. Lộ trình Triển khai Sprint 01 (Sprint 01 Task Breakdown & Status)

Sprint 01 được phân rã thành 5 Task kỹ thuật tuần tự và khép kín:

| Task | Tên Hạng mục | Mục tiêu Kỹ thuật | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Task 1** | **Vector Infrastructure & Database Schema** | Nâng cấp image `pgvector/pgvector:pg16`, migration `0005_phase3_agents_memory.sql`, models `TradingKnowledge`, `EpisodicTradeMemory`, mở rộng `SystemTradingConfig`, cách ly test D18 trong `conftest.py`. | **HOÀN THÀNH** |
| **Task 2** | **RAG Knowledge Ingestion Pipeline & Embeddings** | Tạo `backend/knowledge_base/` (SMC, Price Action, Macro Risk, Post-Mortem), xây dựng `EmbeddingService` 1536 chiều (OpenAI/Gemini/Local Hashing), `RAGService`, CLI `ingest_knowledge.py`, API `/api/v1/knowledge/`. | **HOÀN THÀNH** |
| **Task 3** | **Reflexion Engine Service** | Xây dựng `ReflexionService` tự động phân tích post-mortem (SL_TOO_TIGHT, EARLY_ENTRY, TRADED_DURING_NEWS_SPIKE), lưu vào `episodic_trade_memory`, `ReflexionWorker` nghe Redis `ORDER_CLOSED`, API `/api/v1/reflexion/`. | **HOÀN THÀNH** |
| **Task 4** | **Strategy Governor Agent & Hard Guardrails Closure** | Xây dựng `StrategyGovernor` thu thập đồng thuận từ 3 Agents (News, Technical RAG, Reflexion), áp dụng Pydantic Hard Guardrails, Daily Drawdown Lock 3%, đồng bộ `system_trading_config` & Redis `runtime:params:XAUUSD`. | **CHUẨN BỊ TRIỂN KHAI** |
| **Task 5** | **Cockpit UI Integration** | Tích hợp hiển thị trực quan lên Vue 3 Dashboard: Panel Agent Consensus & Parameters Adjustment, Panel Reflexion Memories & Lessons Learned. | **CHỜ TRIỂN KHAI** |