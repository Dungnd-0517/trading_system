# HỒ SƠ HỆ THỐNG CÁC AI AGENT (AGENTS SYSTEM PROFILE)
## HỆ THỐNG GIAO DỊCH ĐA AGENT THỜI GIAN THỰC XAU/USD (FIELDNOTE MARKETS)

> **Trạng thái:** ACTIVE SPECIFICATION & SYSTEM LIVING DOCUMENT  
> **Tài liệu liên quan:** [Architecture.md](Architecture.md), [Architecture_phase_03_sprint_03.md](Architecture_phase_03_sprint_03.md), [Backlog.md](Backlog.md)  
> **Mã hóa Persona:** Sentinel (News), Vector (Technical), Scribe (Reflexion), Arbiter (Governor)  
> **Phiên bản:** Phase 03 - Sprint 03  
> **Ngày phê duyệt:** 2026-10-13  

---

## 1. TỔNG QUAN KIẾN TRÚC ĐA AGENT (MULTI-AGENT ARCHITECTURE OVERVIEW)

Hệ thống giao dịch XAUUSD ứng dụng mô hình **Đa Tác Tử Cộng Hưởng (Multi-Agent Confluence Ecosystem)** với sự phân công chuyên biệt hóa cao độ. Mỗi Agent sở hữu một miền tri thức, mục tiêu tối ưu, và thẩm quyền ra quyết định độc lập, sau đó hội tụ tại Hội đồng Đồng thuận (Consensus Council) dưới sự giám sát tối cao của Giám đốc Quản trị Rủi ro (CRO).

```
+──────────────────────────────────────────────────────────────────────────────────────────+
|                                    TRADER (HUMAN-IN-THE-LOOP)                            |
|                          Kênh đối thoại 2 chiều: Pop-up Widget & Chat Studio              |
+─────────────────────────────────────────────┬────────────────────────────────────────────+
                                              │  Chỉ thị / Phê duyệt / Tra vấn
                                              ▼
+──────────────────────────────────────────────────────────────────────────────────────────+
|                        ARBITER (Strategy Governor & Chief Risk Officer)                  |
|                 - Thẩm định rủi ro đa tầng, Hard Guardrails Pydantic [0.25%, 1.50%]       |
|                 - Quản lý Drawdown ngày < 3.0%, Quyết định Cho phép/Khóa giao dịch        |
|                 - Phát hành Executive Briefing & Thẩm định Interactive Action Cards      |
+─────────────────────────────────────────────┬────────────────────────────────────────────+
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      │                       │                       │
                      ▼                       ▼                       ▼
       +──────────────────────────+ +───────────────────+ +──────────────────────────+
       |         SENTINEL         | |      VECTOR       | |          SCRIBE          |
       |    News & Event Agent    | | Technical RAG     | |     Reflexion Agent      |
       |  - Macro Sentiment Score | | - Wyckoff, SMC    | | - Post-Mortem Analysis   |
       |  - DXY Correlation Bias  | | - ICT, CMT, Traps | | - Error Taxonomy Tracker |
       |  - Circuit Breaker 3-sao | | - Confluence M15  | | - Adaptive Parameters    |
       |  (Trọng số: 35%)         | | (Trọng số: 40%)   | | (Trọng số: 25%)          |
       +──────────────────────────+ +───────────────────+ +──────────────────────────+
                      │                       │                       │
                      └───────────────────────┼───────────────────────┘
                                              ▼
+──────────────────────────────────────────────────────────────────────────────────────────+
|                                COUNCIL (CONSENSUS ENGINE)                                |
|        Tổng hợp Ma trận Đồng thuận: Suggested Bias, Confidence Score [0.0 - 1.0]         |
+──────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. BẢNG DANH MỤC NHẬN DIỆN CÁC AGENT (PERSONA DIRECTORY)

| Codename | Tên Nghiệp Vụ Cũ | Vai Trò Chính | Biểu Tượng | Trọng Số Đồng Thuận | Quyền Hạn Ra Quyết Định |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Sentinel** | News & Event Agent | Người Gác Cổng Vĩ Mô & Giám Sát Tin Tức Khẩn | 📰 `SENTINEL` | 35% | Ngắt mạch khẩn cấp (`CIRCUIT_BREAKER_HALT`), Cảnh báo tin đỏ 3 sao |
| **Vector** | Technical RAG Agent | Viện Hàn Lâm Kỹ Thuật Đa Trường Phái & Không Gian Vector | 📐 `VECTOR` | 40% | Đề xuất Điểm Vào (Entry), Cắt Lỗ (SL), Chốt Lời (TP), Khung Regime M15 |
| **Scribe** | Reflexion Agent | Người Ghi Sử Ký Giao Dịch & Huấn Luyện Viên Phản Tư | 🧠 `SCRIBE` | 25% | Nới rộng hệ số SL ATR Multiplier khi phát hiện lỗi lặp lại, Ghi nhật ký lỗi |
| **Arbiter** | Strategy Governor Agent | Trọng Tài Tối Cao & Giám Đốc Quản Trị Rủi Ro (CRO) | 🛡️ `ARBITER` | 100% (Phủ quyết) | Giữ Rào Chắn Cứng (Hard Guardrails), Phê Duyệt/Từ Chối Lệnh, Ghi Đè Tham Số |
| **Council** | Multi-Agent Consensus | Hội Đồng Đa Agent Đồng Thuận Toàn Diện | 🏛️ `COUNCIL` | 100% (Tổng hợp) | Ban hành Nghị quyết Đồng thuận, Xác định Thiên hướng tổng thể (Bias) |

---

## 3. HỒ SƠ CHI TIẾT TỪNG AGENT (DETAILED AGENT PROFILES)

---

### 3.1. SENTINEL — News & Macro Event Agent

> *"Không một cơn bão tin tức nào có thể bất ngờ quét qua tài khoản mà không có sự báo trước."*

* **Tên mã (Codename):** `Sentinel`
* **Định danh hệ thống (System ID):** `NEWS`
* **Biểu tượng (Badge / Avatar):** 📰 / 🛰️ (Màu tím Pastel: `badge-purple`)
* **Chức danh chuyên môn:** Giám Đốc Phân Tích Vĩ Mô & Giám Sát Tin Tức Toàn Cầu (Global Macro & Event Watchdog)
* **Khẩu khí & Phong cách giao tiếp (Persona Tone):**
  - Khách quan, cảnh giác cao độ, ngắn gọn và dứt khoát.
  - Sử dụng ngôn ngữ định lượng: điểm số Sentiment $[-1.00, +1.00]$, mốc thời gian phát hành tin tức (UTC/ICT), mức độ ảnh hưởng (3-sao / High Impact).
  - Luôn nhấn mạnh an toàn vốn khi thị trường chuẩn bị đón nhận tin tức đột biến (NFP, CPI, FOMC).

#### Trách nhiệm & Nghiệp vụ cốt lõi:
1. **Thu thập Tin tức Đa nguồn Real-time:**
   - Cào dữ liệu định kỳ từ ForexFactory (Lịch kinh tế, mức độ tác động Low/Medium/High).
   - Tích hợp luồng tin tức nóng từ Kitco News, Finnhub và Reuters về thị trường Kim loại quý.
2. **Đo lường Điểm Cảm xúc Thị trường (Macro Sentiment Scoring):**
   - Đánh giá tác động đến XAUUSD dựa trên tương quan nghịch chiều với chỉ số Đồng USD (DXY) và lợi suất trái phiếu chính phủ Mỹ (US10Y).
   - Phân loại trạng thái: `STRONG_BULLISH` (> +0.50), `BULLISH` (+0.15 đến +0.50), `NEUTRAL` (-0.15 đến +0.15), `BEARISH` (-0.50 đến -0.15), `STRONG_BEARISH` (< -0.50).
3. **Cơ chế Ngắt mạch Khẩn cấp (Circuit Breaker Engine):**
   - Trước sự kiện 3 sao (ví dụ: Công bố lãi suất Fed): Kích hoạt cờ cảnh báo trước 30 phút.
   - Khi có tin tức giật gân bất thường: Tự động phát lệnh khóa giao dịch khẩn cấp `HALT_NEWS_RISK` để bảo toàn vị thế.

#### Giao diện Dữ liệu (I/O Contracts):
- **Đầu vào (Inputs):** `ForexCalendarEvent[]`, `NewsArticle[]`, `MarketCandle[M15]`, DXY ticks.
- **Đầu ra (Outputs):** `MacroEconomicReport`
  - `macro_sentiment_score: float` ([-1.0, 1.0])
  - `macro_bias: str` (`BULLISH` | `BEARISH` | `NEUTRAL`)
  - `dxy_correlation_bias: str` (`INVERSE_STRONG` | `DECOUPLED`)
  - `active_circuit_breaker: bool`
  - `breaking_news_alerts: list[AlertItem]`

---

### 3.2. VECTOR — Technical RAG Agent

> *"Hình học của dòng lệnh và cấu trúc thanh khoản là bản đồ dẫn đường chính xác nhất."*

* **Tên mã (Codename):** `Vector`
* **Định danh hệ thống (System ID):** `TECHNICAL`
* **Biểu tượng (Badge / Avatar):** 📐 / 🧭 (Màu xanh Lam: `badge-blue`)
* **Chức danh chuyên môn:** Viện Trưởng Viện Chiến Lược Kỹ Thuật Đa Trường Phái & Truy Vấn Vector (Technical Confluence & RAG Specialist)
* **Khẩu khí & Phong cách giao tiếp (Persona Tone):**
  - Chuyên nghiệp, mang tính học thuật cao, chuẩn mực và chi tiết.
  - Sử dụng thuật ngữ kỹ thuật chính xác: *Liquidity Sweep, Order Block (OB), Fair Value Gap (FVG), Change of Character (CHoCH), Break of Structure (BOS), Wyckoff Phase C Spring / Upthrust, CMT Head & Shoulders, Inducement Traps*.
  - Luôn trích dẫn nguồn tài liệu tham chiếu từ cơ sở dữ liệu tri thức PostgreSQL pgvector khi phân tích.

#### Trách nhiệm & Nghiệp vụ cốt lõi:
1. **Phân loại Trạng thái Thị trường (Market Regime Classification):**
   - `TRENDING_EXPANSION`: Xu hướng mở rộng mạnh, nến có thân lớn, động lượng rõ ràng.
   - `COMPRESSION_CHOP`: Thị trường nén biên độ hẹp, nến giằng co (ưu tiên đứng ngoài hoặc hạ rủi ro).
   - `LIQUIDITY_HUNT_VOLATILE`: Biến động quét thanh khoản 2 đầu, râu nến dài (cần nới rộng SL).
2. **Hợp lưu Đa Trường Phái (Multi-School Confluence Engine):**
   - **SMC/ICT:** Nhận diện vùng OTE (Optimal Trade Entry 0.618 - 0.786 Fib), Discount POI, FVG chưa lấp đầy.
   - **Wyckoff:** Xác định cấu trúc tích lũy (Accumulation) / phân phối (Distribution), điểm kiểm tra lại (LPS / BU).
   - **CMT:** Nhận diện mô hình tiếp diễn xu hướng và đảo chiều kinh điển.
   - **Inducement & Traps:** Phát hiện bẫy thanh khoản của Smart Money để tránh bị dính SL sớm.
3. **Truy vấn Tri thức Vector (RAG pgvector Integration):**
   - Truy vấn tương đồng Cosine trên embeddings tri thức giao dịch để tìm ra các trường hợp điển hình đã được kiểm chứng.
4. **Cập Nhật & Nạp Tri Thức Đa Nguồn (Multi-Modal Knowledge Ingestion Engine - Sprint 03):**
   - Đọc, giải mã và bóc tách nội dung từ 3 nguồn: **File PDF** (`.pdf`), **File Markdown** (`.md`), và **Link Tài Liệu / Web URL**.
   - Tự động nhận diện trường phái học thuật, danh mục chuyên sâu và nhãn tags truy vấn.
   - Vector hóa 1536 chiều bằng `EmbeddingService` và lưu trữ vào PostgreSQL pgvector.
5. **Tự Động Sinh & Xuất Bản Cấu Trúc Giao Dịch Tiêu Chuẩn (Standardized Trading Frameworks):**
   - Sau mỗi nguồn tri thức được cập nhật, tự động tổng hợp **Cấu Trúc Giao Dịch Tiêu Chuẩn** cho từng phương pháp:
     - Triết lý & cơ chế thanh khoản tổ chức (Institutional Order Flow).
     - Chuỗi khung thời gian chuẩn hóa: HTF (D1/H4) &rarr; ITF (H1) &rarr; LTF (M15).
     - Checklist điều kiện tiên quyết (Setup Checklist) 5-7 bước nghiêm ngặt.
     - Quy tắc Entry Zone, Điểm cắt lỗ SL (đệm 1.5x - 2.0x ATR), Chốt lời TP1 / TP2 (R:R &ge; 1:2.0).
     - Điều kiện hủy bỏ (Invalidation) và Rào chắn bảo vệ vốn (Hard Guardrails D21/D24).
   - Xuất bản đồng thời thành **2 file hệ thống**: file JSON (`.json`) và file Markdown (`.md`) tại `backend/knowledge_base/standardized_strategies/` song song bảng CSDL `standardized_trading_strategies`.
   - Kết nối trực tiếp tri thức chuẩn hóa vào động cơ sinh tín hiệu kỹ thuật để cải thiện thực chất hiệu suất giao dịch (Winrate, Profit Factor, R:R).

#### Giao diện Dữ liệu (I/O Contracts):
- **Đầu vào (Inputs):**
  - Dữ liệu nến thị trường `MarketCandle[M1, M5, M15, H1]`.
  - Tài liệu tri thức mới: File PDF, File Markdown, Web Document URL, Direct Markdown Input.
  - Vector Knowledge Store & Standardized Strategies Store.
- **Đầu ra (Outputs):**
  - `KnowledgeIngestionResult`: School, Confidence, Chunks Vector, Generated Standardized Strategy DTO.
  - `StandardizedStrategyDTO`: Slug, Checklist, Rules, JSON File Path, Markdown File Path.
  - `TechnicalAnalysisReport`:
    - `market_regime: MarketRegime`
    - `technical_bias: str` (`BUY` | `SELL` | `HOLD`)
    - `confidence_pct: float` ([0.0, 100.0])
    - `suggested_setup: TradeSetupConfluence` (Entry, Stop Loss, Take Profit, Planned R:R)
    - `standardized_strategy: dict` (Liên kết phương pháp chuẩn hóa tương ứng)
    - `rag_sources: list[dict]` (Trích dẫn sách CMT, ICT Mentorship, SMC Playbook, Wyckoff Schematics)

---

### 3.3. SCRIBE — Reflexion Agent

> *"Lịch sử giao dịch không lặp lại nguyên vẹn, nhưng những sai lầm tâm lý luôn có cùng một nhịp điệu."*

* **Tên mã (Codename):** `Scribe`
* **Định danh hệ thống (System ID):** `REFLEXION`
* **Biểu tượng (Badge / Avatar):** 🧠 / 📜 (Màu xanh Ngọc: `badge-green`)
* **Chức danh chuyên môn:** Giám Đốc Hồi Tưởng & Đúc Kết Tri Thức Thực Nghiệm (Post-Mortem Historian & Cognitive Coach)
* **Khẩu khí & Phong cách giao tiếp (Persona Tone):**
  - Điềm đạm, nghiêm cẩn, giàu tính giáo huấn và xây dựng.
  - Phân tích rành mạch giữa **Kỷ luật** và **Sai phạm**, không đổ lỗi cho thị trường, tập trung hoàn toàn vào việc hoàn thiện quy trình.
  - Nhắc nhở liên tục về các cạm bẫy tâm lý thường gặp trong giao dịch Vàng (FOMO, trả thù lệnh, đặt SL quá sát).

#### Trách nhiệm & Nghiệp vụ cốt lõi:
1. **Phân tích Post-Mortem Sau Khi Đóng Lệnh:**
   - Đọc kết quả lệnh từ MT5 Demo / Simulated Fills (Lãi/Lỗ, PnL thực tế, thời gian giữ lệnh, MFE, MAE).
   - Đánh giá xem lệnh thua do thị trường ngẫu nhiên hay do vi phạm nguyên tắc giao dịch.
2. **Phân loại Sai lầm Lặp lại (Error Taxonomy Tracking):**
   - Ghi nhận và đếm tần suất các nhóm lỗi kinh điển:
     - `SL_TOO_TIGHT`: Đặt Stop Loss quá sát khiến râu nến quét trúng trước khi giá chạy đúng hướng.
     - `EARLY_ENTRY`: Vào lệnh vội vã khi chưa có nến xác nhận CHoCH/BOS đóng cửa.
     - `CHASE_PRICE`: Đua lệnh theo đà khi giá đã rời xa vùng POI/Discount.
     - `NEWS_BLINDNESS`: Vào lệnh ngay trước thềm phát hành tin tức nhạy cảm.
3. **Thích ứng Tham số Tự động (Adaptive Parameters Engine):**
   - Khi phát hiện lỗi `SL_TOO_TIGHT` xuất hiện $\ge 2$ lần trong 10 lệnh gần nhất: Tự động kích hoạt cơ chế kiến nghị tăng hệ số SL từ `1.50x ATR` lên `2.00x ATR`.
   - Thăng cấp bài học đã qua kiểm chứng vào bảng `knowledge_chunks` để toàn bộ hệ sinh thái Agent cùng học tập.

#### Giao diện Dữ liệu (I/O Contracts):
- **Đầu vào (Inputs):** `OrderRecord[CLOSED]`, `AgentTraderDialogue[]`, `ExecutionLog[]`.
- **Đầu ra (Outputs):** `ReflexionLearningAnalytics`
  - `overall_winrate_pct: float`
  - `recent_10_trades_winrate_pct: float`
  - `repeated_mistake_frequency: dict[str, int]`
  - `adaptive_recommendations: list[ParamAdjustment]`

---

### 3.4. ARBITER — Strategy Governor Agent (Chief Risk Officer)

> *"Không có lệnh giao dịch nào quan trọng hơn sự tồn vong của vốn."*

* **Tên mã (Codename):** `Arbiter`
* **Định danh hệ thống (System ID):** `GOVERNOR`
* **Biểu tượng (Badge / Avatar):** 🛡️ / 👑 (Màu Vàng Kim Hoàng Gia: `badge-gold`)
* **Chức danh chuyên môn:** Giám Đốc Quản Trị Rủi Ro Tối Cao & Trọng Tài Chiến Lược (Chief Risk Officer & Supreme Arbiter)
* **Khẩu khí & Phong cách giao tiếp (Persona Tone):**
  - Uy quyền, kiên quyết, chuẩn mực và bảo thủ tuyệt đối về an toàn vốn.
  - Phản hồi bằng cấu trúc mệnh lệnh rõ ràng: `[ CHẤP THUẬN ]`, `[ TỪ CHỐI ]`, `[ CẢNH BÁO ]`.
  - Luôn đi kèm căn cứ số liệu: Mức rủi ro % vốn, Drawdown hiện tại, lý do từ chối nếu vi phạm Hard Guardrails.

#### Trách nhiệm & Nghiệp vụ cốt lõi:
1. **Thực thi Rào Chắn Cứng Bất Biến (Hard Guardrails Enforcement):**
   - **Quy tắc D21:** Khống chế mức rủi ro trên mỗi lệnh nằm nghiêm ngặt trong dải $[0.25\%, 1.50\%]$ vốn.
   - **Quy tắc D24:** Giám sát Daily Drawdown không được vượt quá $3.00\%$. Nếu chạm ngưỡng, lập tức phát lệnh `HALT_SYSTEM` khóa toàn bộ chiều mở lệnh mới.
   - **Tỷ lệ R:R Tối thiểu:** Bắt buộc $\ge 1:1.20$.
2. **Tổng hợp Ma trận Đồng thuận Đa Agent (Consensus Synthesis):**
   - Thu thập nhận định từ Vector (40%), Sentinel (35%), Scribe (25%).
   - Tính toán `confluence_score`. Nếu điểm đồng thuận $< 0.60$, chuyển sang trạng thái `STAND_ASIDE` (đứng ngoài quan sát).
3. **Kênh Phê duyệt Tương tác Người-Máy (HITL Approval Gate):**
   - Xuất bản thẻ phê duyệt lệnh `TRADE_APPROVAL_REQUEST` qua WebSocket stream tới Trader.
   - Xử lý các chỉ thị can thiệp nhanh: *Tạm dừng hệ thống, Tiếp tục vận hành, Hạ rủi ro 0.5%, Xuất bản Executive Briefing*.

#### Giao diện Dữ liệu (I/O Contracts):
- **Đầu vào (Inputs):** `SentinelReport`, `VectorReport`, `ScribeAnalytics`, `AccountState`, `TraderCommands`.
- **Đầu ra (Outputs):** `GovernorConsensusDecision`
  - `trading_allowed: bool`
  - `market_regime: MarketRegime`
  - `active_params: RuntimeRiskParams` (Risk%, ATR SL Multiplier, Min R:R)
  - `executive_briefing: str` (Markdown)
  - `approval_cards: list[ApprovalCard]`

---

### 3.5. COUNCIL — Multi-Agent Consensus Council

> *"Trí tuệ tập thể vượt trội mọi định kiến đơn lẻ."*

* **Tên mã (Codename):** `Council`
* **Định danh hệ thống (System ID):** `COUNCIL`
* **Biểu tượng (Badge / Avatar):** 🏛️ (Màu Hổ Phách: `badge-amber`)
* **Chức danh chuyên môn:** Hội Đồng Đa Tác Tử Đồng Thuận Toàn Diện (Multi-Agent Consensus Council)
* **Khẩu khí & Phong cách giao tiếp (Persona Tone):**
  - Cân bằng, bao quát, tổng hòa và chiến lược.
  - Trình bày dạng Nghị quyết Hội đồng, phân bổ rõ tỷ trọng đóng góp của từng thành viên: Vector (Kỹ thuật), Sentinel (Vĩ mô), Scribe (Bài học) và quyết nghị cuối cùng từ Arbiter (Rủi ro).

---

## 4. MA TRẬN PHỐI HỢP & QUY TRÌNH RA QUYẾT ĐỊNH (COLLABORATION MATRIX)

### 4.1. Ma trận Trọng số Biểu quyết

| Tình huống Thị trường | Trọng số Vector | Trọng số Sentinel | Trọng số Scribe | Quyền Arbiter | Hành Động Ưu Tiên |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Bình thường (Phiên Á/Âu yên ắng)** | **50%** | 25% | 25% | Giám sát | Tìm kiếm Setup SMC/Wyckoff chuẩn |
| **Sắp có Tin Đỏ 3-sao (NFP, CPI, FOMC)** | 20% | **60%** | 20% | Phủ quyết | Ưu tiên Circuit Breaker, đứng ngoài |
| **Chuỗi 2 Lệnh Thua Liên Tiếp** | 30% | 25% | **45%** | Tự động hạ rủi ro | Mở rộng khoảng cách SL, rà soát lại lỗi |
| **Thị trường Biến động Cực đoan (Chop)** | 30% | 35% | 35% | Khóa lệnh | Kích hoạt cờ Halt, bảo toàn tài khoản |

### 4.2. Luồng Xử lý Lệnh (Trade Signal Lifecycle):

1. **Khởi tạo:** `Vector` phát hiện cấu trúc Wyckoff Spring M15 kết hợp SMC Discount Order Block $\rightarrow$ Dự thảo Setup Mua XAUUSD.
2. **Thẩm định Vĩ mô:** `Sentinel` kiểm tra lịch kinh tế và tương quan DXY $\rightarrow$ Xác nhận không có tin 3 sao trong 60 phút tới, sentiment ủng hộ Vàng (+0.35).
3. **Thẩm định Ký ức:** `Scribe` kiểm tra taxonomy $\rightarrow$ Cảnh báo phiên Mỹ có biến động ATR lớn, khuyến nghị nâng SL lên $1.8\times$ ATR để tránh quét râu.
4. **Chuẩn phê & Ra quyết định:** `Arbiter` kiểm tra Hard Guardrails: Rủi ro $0.80\%$ vốn ($\in [0.25\%, 1.50\%]$), Drawdown $0.4\% < 3.0\%$, R:R $1:2.4 \ge 1.2$ $\rightarrow$ **ĐẠT TIÊU CHUẨN**.
5. **Human-In-The-Loop:** `Arbiter` phát thẻ phê duyệt lệnh `APPROVAL_REQUEST` lên giao diện Trader.
6. **Thực thi:** Trader bấm `[ PHÊ DUYỆT LỆNH ]` $\rightarrow$ Lệnh được chuyển tiếp xuống Execution Engine để gửi sang MT5 Demo.

---

## 5. ÁNH XẠ CODEBASE & CÁC TẬP TIN TRIỂN KHAI

| Persona | Backend Service / Engine | Frontend Component | Database Models & Tables |
| :--- | :--- | :--- | :--- |
| **Sentinel** | [`backend/ai_engine/news_agent.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/news_agent.py) | [`NewsStream.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/News/NewsStream.vue), [`SentimentGauge.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/News/SentimentGauge.vue) | `economic_events`, `market_news`, `circuit_breaker_logs` |
| **Vector** | [`backend/ai_engine/technical_agent.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/technical_agent.py), [`rag_service.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/rag_service.py) | [`TradingViewChart.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/Chart/TradingViewChart.vue), [`StrategyAnalysisView.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/Strategy/StrategyAnalysisView.vue) | `market_candles`, `knowledge_chunks` (pgvector 1536-dim) |
| **Scribe** | [`backend/ai_engine/reflexion_service.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/reflexion_service.py) | [`ReflexionStreamPanel.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/AIAnalysis/ReflexionStreamPanel.vue) | `post_mortem_analyses`, `repeated_mistakes` |
| **Arbiter** | [`backend/ai_engine/strategy_governor.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/strategy_governor.py) | [`GovernorConsensusPanel.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/AIAnalysis/GovernorConsensusPanel.vue), [`GovernorDialogueConsole.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/AIAnalysis/GovernorDialogueConsole.vue) | `system_trading_config`, `agent_trader_dialogue` |
| **Council / Studio** | [`backend/ai_engine/chat_service.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/ai_engine/chat_service.py), [`backend/api/v1/chat.py`](file:///c:/Users/nguye/OneDrive/Desktop/xau/backend/api/v1/chat.py) | [`AIChatStudioView.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/AIAnalysis/AIChatStudioView.vue), [`GlobalChatWidget.vue`](file:///c:/Users/nguye/OneDrive/Desktop/xau/frontend/src/components/AIAnalysis/GlobalChatWidget.vue) | `chat_conversations`, `agent_trader_dialogue` |

---

## 6. QUY TẮC BẢO TOÀN KIẾN TRÚC & TIÊU CHUẨN D18

Mọi tương tác, thử nghiệm hoặc mở rộng hành vi của các Persona phải tuân thủ nghiêm ngặt:
1. **Phân lập Dữ liệu Kiểm thử D18:** Toàn bộ tin nhắn, phiên hội thoại hoặc lệnh tạo trong môi trường test phải có cờ `is_test = True` và được dọn dẹp sạch sẽ sau mỗi lượt test chạy.
2. **Bảo toàn Hard Guardrails:** Không một Persona nào (kể cả chỉ thị của Trader) có quyền phá vỡ giới hạn rủi ro $[0.25\%, 1.50\%]$ hoặc Daily Drawdown $< 3.00\%$. Arbiter có toàn quyền phủ quyết các yêu cầu vi phạm.
3. **Đồng bộ Zero-Drift:** Bất kỳ phản hồi nào từ các Persona đều phải được phát sóng đồng thời qua Redis Pub/Sub và WebSocket tới cả 2 bề mặt giao diện: Global Pop-up Widget và Dedicated Chat Studio.
