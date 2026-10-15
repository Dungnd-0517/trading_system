# KIẾN TRÚC KỸ THUẬT: GIAI ĐOẠN 3 - SPRINT 3 (PHASE 03 - SPRINT 03)
## HỆ THỐNG CHAT REAL-TIME ĐA PHIÊN HỘI THOẠI & ĐỒNG BỘ HAI CHIỀU VỚI STRATEGY GOVERNOR
### (DUAL-SURFACE REAL-TIME MULTI-CONVERSATION CHAT & HITL DIALOGUE SYSTEM)

> **Trạng thái:** ARCHITECTURE SPECIFICATION & SPRINT BACKLOG PLAN  
> **Tài liệu nền:** [Architecture.md](Architecture.md), [technical_system.md](technical_system.md)  
> **Tài liệu Sprint trước:** [Architecture_phase_03_sprint_01.md](Architecture_phase_03_sprint_01.md), [Architecture_phase_03_sprint_02.md](Architecture_phase_03_sprint_02.md), [Backlog.md](Backlog.md)  
> **Hồ sơ Cá nhân hóa Agent:** [Agents_Profile.md](Agents_Profile.md) (Sentinel, Vector, Scribe, Arbiter, Council)  
> **Framework tham chiếu:** Tauric Research TradingAgents (`https://github.com/tauricresearch/tradingagents`), Google Gemini Web UI Architecture, Vue 3 Pinia State Management, Redis Pub/Sub, PostgreSQL pgvector.  
> **Phạm vi (Scope):** Xây dựng hệ thống chat thời gian thực toàn diện, đồng bộ hóa 100% với kênh đối thoại hai chiều Trader - Governor (đã kiến tạo trong Task 5 của Sprint 02):  
> 1. **Global Pop-up Chat Widget (Xuyên suốt toàn bộ giao diện):** Widget nổi (floating/dockable) hiện diện liên tục trên mọi màn hình (Trading Cockpit, Orders History, News & Events, Strategy & Analysis, Backtest Lab, Settings), hỗ trợ gửi lệnh override nhanh, xử lý Interactive Approval Cards (Duyệt/Từ chối lệnh), xem Briefing vĩ mô và nhận diện thông báo chưa đọc (Unread badge).  
> 2. **Dedicated Chat Studio Screen (Tab riêng nằm trong Strategy & Analysis):** Không gian hội thoại chuyên sâu với bố cục chia nhiều cuộc trò chuyện (Multi-Conversation Sessions) mô phỏng trải nghiệm người dùng hiện đại của LLM Gemini (Sidebar phân nhóm thời gian, New Chat, Rename, Pin, Delete, Search, Message Thread Markdown phong phú, chọn Agent tham vấn chuyên biệt: Sentinel, Vector, Scribe, Arbiter, Council).  
> 3. **Real-time Two-Way Synchronization Engine:** Cơ chế đồng bộ phản ứng tức thời hai chiều giữa Pop-up Widget và Màn hình Chat Studio thông qua Pinia Store tập trung (`chatStore.js`), WebSocket stream và Redis Pub/Sub, bảo đảm tính nhất quán dữ liệu Single Source of Truth.  
> 4. **Multi-Session Data & Schema Layer:** Migration `0007_phase3_sprint3_chat.sql` bổ sung bảng `chat_conversations`, mở rộng `agent_trader_dialogue` với `conversation_id`, và bảo toàn nghiêm ngặt chuẩn phân lập kiểm thử D18.  
> 5. **Cá nhân hóa Định danh Agent (Persona Identity Personalization - D28):** Quy chuẩn hóa tên gọi độc bản: Sentinel (News), Vector (Technical), Scribe (Reflexion), Arbiter (Governor) kèm hồ sơ hệ thống toàn diện tại [Agents_Profile.md](Agents_Profile.md).  
> **Ngoài phạm vi (Out of Scope):** Thực hiện lệnh tiền thật trên tài khoản MT5 Live (thuộc Phase 04); Huấn luyện lại weights mô hình nền tảng LLM từ đầu.  
> **Ngày lập:** 2026-10-12 (Cập nhật Persona: 2026-10-13)  

---

## MỤC LỤC
1. [Mục tiêu và Định hướng Trọng tâm Sprint 03](#1-mục-tiêu-và-định-hướng-trọng-tâm-sprint-03)
2. [Quyết định Kiến trúc Mới (Decision Log D25–D28)](#2-quyết-định-kiến-trúc-mới-decision-log-d25d28)
3. [Kiến trúc Tổng thể Hệ thống Chat & Sơ đồ Luồng Dữ liệu](#3-kiến-trúc-tổng-thể-hệ-thống-chat--sơ-đồ-luồng-dữ-liệu)
4. [Thiết kế Chi tiết 2 Phân hệ Giao diện (Dual-Surface UI) & Hệ Thống Persona](#4-thiết-kế-chi-tiết-2-phân-hệ-giao-diện-dual-surface-ui)
   - [4.1. Global Pop-up Chat Widget](#41-global-pop-up-chat-widget-xuyên-suốt-toàn-bộ-giao-diện)
   - [4.2. Dedicated Multi-Conversation Chat Studio (Gemini Layout)](#42-dedicated-multi-conversation-chat-studio-gemini-layout-trong-strategy--analysis)
   - [4.3. Cá Nhân Hóa Định Danh Agent (Sentinel, Vector, Scribe, Arbiter)](#43-cá-nhân-hóa-định-danh-agent-sentinel-vector-scribe-arbiter)
5. [Động cơ Đồng bộ Real-Time Hai Chiều (Unified Reactive State & Event Bus)](#5-động-cơ-đồng-bộ-real-time-hai-chiều-unified-reactive-state--event-bus)
6. [Mô hình Dữ liệu & Schema Bổ sung (`0007_phase3_sprint3_chat.sql`)](#6-mô-hình-dữ-liệu--schema-bổ-sung-0007_phase3_sprint3_chatsql)
7. [Hợp đồng Giao tiếp: REST API & WebSocket Protocol](#7-hợp-đồng-giao-tiếp-rest-api--websocket-protocol)
8. [Kế hoạch Triển khai theo Task (Task Breakdown T1–T6)](#8-kế-hoạch-triển-khai-theo-task-task-breakdown-t1t6)
9. [Kiểm thử, Chuẩn D18 & Tiêu chuẩn Nghiệm thu (Definition of Done)](#9-kiểm-thử-chuẩn-d18--tiêu-chuẩn-nghiệm-thu-definition-of-done)

---

## 1. MỤC TIÊU VÀ ĐỊNH HƯỚNG TRỌNG TÂM SPRINT 03

### 1.1. Bối cảnh Kế thừa từ Sprint 02
Trong Phase 03 - Sprint 02, hệ thống đã hoàn thiện xuất sắc toàn bộ 5 Tasks của hệ sinh thái Đa Agent:
* **News & Event Agent:** Phân tích vĩ mô định lượng, sentiment XAUUSD và Circuit Breaker ngắt mạch tin 3 sao.
* **Technical RAG Agent:** Nạp tri thức đa trường phái (CMT, ICT, Wyckoff, Inducement/Traps, SMC), phân loại tự động và phân tích hợp lưu M15.
* **Reflexion Agent:** Phân tích post-mortem lệnh đóng, taxonomy lỗi và pipeline thăng cấp quy tắc vào CSDL tri thức.
* **Strategy Governor Agent:** Tổng hợp ma trận đồng thuận, Hard Guardrails Pydantic, xuất bản Executive Briefings và tiếp nhận chỉ thị ghi đè qua kênh đối thoại hai chiều (`agent_trader_dialogue`).

### 1.2. Thách thức Hiện tại & Động lực Nâng cấp Lên Sprint 03
Mặc dù kênh đối thoại đã hoạt động hoàn hảo ở tầng Backend (xử lý intent, rào chắn cứng, phê duyệt lệnh, phát Redis/WebSocket), trải nghiệm tương tác của Trader trên giao diện Frontend hiện vẫn còn những hạn chế mang tính cục bộ:
1. **Tính Cục Bộ của Giao diện Console:** Khung đối thoại (`GovernorDialogueConsole.vue`) hiện nằm cố định trong sub-tab của cột phải Cockpit Studio. Khi Trader chuyển sang các màn hình nghiệp vụ khác như **Orders History**, **News & Events**, **Strategy & Analysis**, **Backtest Lab** hay **Settings**, Trader hoàn toàn mất liên lạc thị giác với Governor và không thể tiếp nhận kịp thời các Approval Requests khẩn cấp.
2. **Thiếu Khả năng Phân Tách Ngữ Cảnh Đa Hội Thoại (Single Monolithic Thread):** Hiện tại toàn bộ tin nhắn đối thoại được lưu chung trong một danh sách phẳng. Trader không thể phân chia các cuộc trò chuyện theo từng chủ đề hoặc phiên làm việc riêng biệt (ví dụ: *Cuộc trò chuyện 1: "Review rủi ro phiên London"*, *Cuộc trò chuyện 2: "Tra cứu mẫu hình Wyckoff Spring M15"*, *Cuộc trò chuyện 3: "Đánh giá tin CPI Mỹ tối nay"*).
3. **Trải nghiệm Trò chuyện Chưa Đạt Chuẩn AI Hiện Đại:** Thiếu các tính năng tiện ích tiêu chuẩn của các trợ lý AI hàng đầu như Google Gemini (tạo New Chat, đổi tên tự động theo nội dung, ghim cuộc trò chuyện quan trọng, chuyển đổi qua lại giữa các phiên thảo luận mà không mất ngữ cảnh).
4. **Nhu cầu Đồng Bộ Hai Chiều (Dual-Surface Synchronization):** Hệ thống cần một kiến trúc đồng bộ thông minh: một **Pop-up nhỏ gọn** luôn túc trực mọi lúc mọi nơi để phản ứng nhanh, và một **Màn hình Chat Chuyên Sâu** tại tab *Strategy & Analysis* để nghiên cứu sâu, phân tích chiến lược dài và quản lý toàn bộ kho tàng hội thoại.

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC MỚI (DECISION LOG D25–D28)

| ID | Quyết định Kiến trúc | Trạng thái | Tác động Kỹ thuật & Lý do Thiết kế |
| :--- | :--- | :---: | :--- |
| **D25** | **Quản lý Đa Phiên Hội Thoại (Multi-Conversation Session Model) & Mở rộng Schema** | `ACCEPTED` | Xây dựng bảng `chat_conversations` quản lý vòng đời session (tiêu đề, thời gian cập nhật, ghim, lưu trữ, agent mục tiêu). Bảng `agent_trader_dialogue` được bổ sung khóa ngoại `conversation_id REFERENCES chat_conversations(id) ON DELETE CASCADE`. Cho phép Trader duy trì nhiều ngữ cảnh đàm thoại độc lập, không bị phân mảnh hay lẫn lộn thông điệp. |
| **D26** | **Mô hình Giao diện Đồng Bộ Hai Bề Mặt (Dual-Surface Synchronized UI: Global Pop-up + Gemini Studio)** | `ACCEPTED` | Triển khai 2 bề mặt hiển thị độc lập về mặt visual nhưng liên kết chặt chẽ về mặt reactive state: (1) Global Floating Pop-up Widget túc trực tại góc dưới màn hình mọi views; (2) Dedicated Chat Studio toàn màn hình dạng Gemini Layout tại tab Strategy & Analysis. Cả hai cùng kết nối vào một Pinia Store (`chatStore`), chia sẻ cùng một luồng WebSocket stream và Redis Pub/Sub, cập nhật tức thì zero-lag. |
| **D27** | **Định tuyến Agent Tham Vấn & Tiêm Ngữ Cảnh Thị Trường Động (Agent Delegation & Market Context Injection)** | `ACCEPTED` | Cho phép Trader lựa chọn đối thoại trực tiếp với Governor (Chỉ huy & CRO) hoặc tham vấn chuyên sâu từng Agent (`TECHNICAL`, `NEWS`, `REFLEXION`, `COUNCIL`). Tích hợp nút "Attach Market Context" tự động tiêm snapshot giá XAUUSD, nến M15, tin tức nóng và tham số rủi ro vào prompt gửi đi. |
| **D28** | **Cá nhân hóa Định danh Đa Agent (Agent Persona Identity Personalization: Sentinel, Vector, Scribe, Arbiter)** | `ACCEPTED` | Cá nhân hóa tên gọi độc bản cho 4 Agent chính: **Sentinel** (News & Event Agent), **Vector** (Technical RAG Agent), **Scribe** (Reflexion Agent), **Arbiter** (Strategy Governor & CRO), cùng **Council** (Multi-Agent Consensus). Toàn bộ hồ sơ năng lực, hệ thống luật, thẩm quyền và dữ liệu I/O được quy chuẩn hóa trong [Agents_Profile.md](Agents_Profile.md), đồng bộ hóa metadata hiển thị trên REST API `/api/v1/chat/personas` và UI Chat Studio. |

---

## 3. KIẾN TRÚC TỔNG THỂ HỆ THỐNG CHAT & SƠ ĐỒ LUỒNG DỮ LIỆU

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                    GIAO DIỆN FRONTEND (VUE 3)                               |
|                                                                                             |
|   [ BỀ MẶT 1: GLOBAL FLOATING POP-UP ]         [ BỀ MẶT 2: DEDICATED GEMINI CHAT STUDIO ]  |
|   - Túc trực trên mọi Views (Cockpit,          - Nằm trong Tab: Strategy & Analysis         |
|     Orders, News, Backtest, Settings)          - Cột trái: Danh sách Conversations (Gemini) |
|   - Floating Action Pill / Unread Badge        - Cột phải: Main Chat Thread, Full Markdown  |
|   - Thao tác nhanh, Duyệt lệnh khẩn cấp       - Tạo New Chat, Rename, Pin, Agent Selector  |
|                      │                                              │                       |
|                      ▼                                              ▼                       |
|              +──────────────────────────────────────────────────────────────+               |
|              | PINIA REACTIVE STORE: chatStore.js (Single Source of Truth)  |               |
|              | - activeConversationId, conversations[], messagesMap{}       |               |
|              | - unreadCount, isWidgetOpen, typingIndicators{}              |               |
|              +──────────────────────────────┬───────────────────────────────+               |
+─────────────────────────────────────────────┼───────────────────────────────────────────────+
                                              │ HTTP REST API & WebSocket
                                              ▼
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                  BACKEND API GATEWAY (FASTAPI)                              |
|                                                                                             |
|   [ REST ROUTER: /api/v1/chat/ ]              [ WEBSOCKET ROUTER: /api/v1/ws/market ]       |
|   - GET/POST /conversations                   - agent.dialogue.message                      |
|   - PATCH/DELETE /conversations/{id}          - chat.session.updated                        |
|   - GET/POST /conversations/{id}/messages     - governor.approval_response                  |
|                      │                                              │                       |
|                      ▼                                              ▼                       |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   | CHAT & DIALOGUE ORCHESTRATION SERVICE (backend/ai_engine/chat_service.py)           |   |
|   | - Intent Parsing & Command Router (Tạm dừng, Tiếp tục, Rủi ro, SL, Briefing)        |   |
|   | - Hard Guardrails Validator (D21/D24: Kiểm tra dải [0.25%, 1.50%], DD < 3.0%)      |   |
|   | - Agent Dispatcher (Governor, Technical RAG, News Event, Reflexion, Multi-School)   |   |
|   | - Auto-titling Engine (Tự động đặt tiêu đề cuộc trò chuyện từ câu hỏi đầu tiên)     |   |
|   +──────────────────────────┬──────────────────────────────────────┬───────────────────+   |
+──────────────────────────────┼──────────────────────────────────────┼───────────────────────+
                               │                                      │
                               ▼                                      ▼
             +──────────────────────────────────+   +──────────────────────────────────+
             | REDIS MESSAGE BUS & CACHE        |   | POSTGRESQL + PGVECTOR            |
             | - Pub/Sub: agent:trader:dialogue |   | - chat_conversations             |
             | - Cache: runtime:params:XAUUSD   |   | - agent_trader_dialogue          |
             | - Unread Notification Counter    |   | - system_trading_config          |
             +──────────────────────────────────+   +──────────────────────────────────+
```

---

## 4. THIẾT KẾ CHI TIẾT 2 PHÂN HỆ GIAO DIỆN (DUAL-SURFACE UI)

### 4.1. Global Pop-up Chat Widget (Xuyên Suốt Toàn Bộ Giao Diện)
Widget được gắn trực tiếp ở cấp độ gốc của ứng dụng (`App.vue`), đảm bảo luôn hiển thị cố định ở góc dưới bên phải màn hình bất kể người dùng đang đứng ở view nào:
* **Chế độ Thu gọn (Collapsed FAB - Floating Action Button):**
  - Icon Brain / Governor cách điệu với viền gradient pulsing thở nhẹ.
  - Huy hiệu số tin nhắn chưa đọc (Unread Badge) hiển thị số lượng tin nhắn mới hoặc thông báo khẩn từ Governor.
  - Toast Notification Preview: Khi có tin nhắn quan trọng (đặc biệt là yêu cầu phê duyệt lệnh `APPROVAL_REQUEST` hoặc ngắt mạch `CIRCUIT_BREAKER`), một bong bóng thông báo nhỏ tự động trượt ra trong 5 giây cho phép Trader bấm vào để mở ngay widget.
* **Chế độ Mở rộng (Expanded Mini-Popup Console):**
  - Cửa sổ nổi kích thước chuẩn $400\text{px} \times 540\text{px}$ với hiệu ứng kính mờ (Dark Glassmorphism), bóng đổ đa lớp sang trọng.
  - Header: Hiển thị trạng thái hoạt động của Governor (`ACTIVE`, `CIRCUIT_BREAKER`, `HALTED`), nút phóng to chuyển sang Full Studio, nút thu nhỏ.
  - Body: Danh sách tin nhắn rút gọn của phiên hội thoại đang kích hoạt (`activeConversationId`), hiển thị avatar phân biệt Trader vs Governor, định dạng Markdown tóm tắt.
  - Interactive Action Cards: Khi có yêu cầu phê duyệt lệnh, hiển thị thẻ tương tác với 2 nút bấm tức thì `[ APPROVE ]` (Xanh) và `[ REJECT ]` (Đỏ).
  - Footer Input: Ô nhập tin nhắn nhanh kèm 3 phím tắt chỉ thị tức thời (`Briefing`, `Hạ rủi ro 0.5%`, `Tạm dừng`).
  - Nút chuyển đổi nhanh: `[ ↗ Mở Toàn Màn Hình Trong Strategy Studio ]` tự động điều hướng sang Tab Strategy & Analysis và kích hoạt đúng phiên hội thoại đang dở dang.

### 4.2. Dedicated Multi-Conversation Chat Studio (Gemini Layout Trong Strategy & Analysis)
Nằm tại Tab **Strategy & Analysis** dưới dạng một Sub-tab chuyên biệt độc lập (Sub-tab: `AI Chat Studio & Multi-Agent Dialogue`):
* **Cột Trái: Sidebar Quản lý Đa Hội thoại (Conversations Explorer - Gemini Style):**
  - Chiều rộng linh hoạt $280\text{px} - 320\text{px}$, tông màu tối đồng bộ với hệ thống.
  - Nút bấm đầu trang: `+ Cuộc trò chuyện mới` (`+ New Chat`) nổi bật với gradient viền sáng.
  - Ô tìm kiếm hội thoại nhanh theo từ khóa tiêu đề hoặc nội dung tin nhắn.
  - Danh sách phân nhóm thông minh theo dòng thời gian (Time-grouping):
    - **Hôm nay (Today)**
    - **7 ngày trước (Previous 7 Days)**
    - **30 ngày trước (Previous 30 Days)**
    - **Cũ hơn (Older)**
  - Mỗi mục hội thoại hiển thị: Icon Agent đại diện, Tiêu đề cuộc trò chuyện (tối đa 2 dòng), Thời gian cập nhật gần nhất.
  - Menu thao tác nhanh 3 chấm (`...`) cho từng mục:
    - *Ghim lên đầu (Pin to top)*
    - *Đổi tên cuộc trò chuyện (Rename)*
    - *Lưu trữ (Archive)*
    - *Xóa cuộc trò chuyện (Delete)* kèm hộp thoại xác nhận an toàn.
* **Cột Phải: Không Gian Hội Thoại Chính (Main Dialogue Canvas):**
  - **Header Khu Vực:**
    - Tiêu đề cuộc trò chuyện hiện tại (có thể bấm vào để chỉnh sửa trực tiếp).
    - Bộ chọn Agent tham vấn (Agent Persona Switcher):
      - `👑 Arbiter (Strategy Governor & CRO - Trọng tài tối cao)`
      - `📐 Vector (Technical RAG Specialist - Wyckoff, SMC, ICT)`
      - `📰 Sentinel (News & Macro Watchdog - Circuit Breaker)`
      - `🧠 Scribe (Reflexion Learning Coach - Post-Mortem & Error Taxonomy)`
      - `🏛 Council (Multi-Agent Consensus Council - Đồng thuận toàn diện)`
    - Huy hiệu trạng thái kết nối real-time (`● LIVE STREAMING`).
  - **Khu Vực Tin Nhắn (Message Stream):**
    - Trình bày dạng đối thoại hiện đại: Avatar nhận diện, nhãn tên, mốc thời gian chi tiết.
    - Hỗ trợ Markdown toàn diện: In đậm, in nghiêng, danh sách gạch đầu dòng, bảng số liệu tài chính, trích dẫn quy tắc.
    - Hỗ trợ Code Blocks với cú pháp sáng rõ (JSON tham số, mã lệnh trading).
    - Thẻ Nhúng Tương Tác Chuyên Sâu:
      - *Trade Approval Request Card:* Hiển thị đầy đủ thông số lệnh (Symbol XAUUSD, Loại lệnh BUY/SELL, Khối lượng Lot, Điểm Entry, SL, TP, R:R, Rủi ro % vốn) kèm nút `[ PHÊ DUYỆT LỆNH ]` và `[ TỪ CHỐI LỆNH ]`.
      - *Executive Briefing Report Card:* Trình bày bản tin điều hành 4 phân khu với giao diện thẻ trực quan.
      - *Guardrail Warning Alert:* Báo động đỏ khi câu lệnh vi phạm nguyên tắc bảo vệ vốn tối cao.
    - Hiệu ứng AI Thinking Animation: Dấu chấm ba chấm lượn sóng (Pulsing Typing Dots) khi hệ thống đang xử lý truy vấn hoặc vector RAG.
  - **Khung Soạn Thảo Tin Nhắn (Composer Area):**
    - Textarea tự co giãn chiều cao theo nội dung nhập (từ 1 đến 6 dòng).
    - Phím tắt tiện lợi: `Enter` để gửi tin nhắn; `Shift + Enter` để xuống dòng mới.
    - Nút đính kèm ngữ cảnh nhanh: `[ ⚡ Đính kèm Snapshot Thị trường M15 ]` (tự động đính kèm giá hiện tại, trạng thái nến, chỉ số ATR và xu hướng kỹ thuật vào prompt).
    - Hàng phím tắt gợi ý (Quick Prompts Pills):
      - `"Bản tin điều hành mới nhất từ Arbiter"`
      - `"Hạ rủi ro xuống 0.5%"`
      - `"Nới khoảng cách SL lên 2.0x ATR"`
      - `"Vector: Đánh giá cấu trúc M15 theo Wyckoff & ICT"`
      - `"Sentinel: Tình hình tin tức vĩ mô hôm nay"`
      - `"Scribe: Xem lại các bài học kiểm điểm gần nhất"`
      - `"Tạm dừng giao dịch khẩn cấp"`

### 4.3. Cá Nhân Hóa Định Danh Agent (Sentinel, Vector, Scribe, Arbiter)
Nhằm tăng tính trực quan, phân định rành mạch trách nhiệm chuyên môn và nâng tầm trải nghiệm giao tiếp người-máy (HITL), toàn bộ các tác tử AI trong hệ thống được cá nhân hóa định danh theo chuẩn [Agents_Profile.md](Agents_Profile.md):

| Tên Cá Nhân Hóa | Định Danh Hệ Thống | Chức Danh Nghiệp Vụ | Huy Hiệu & Màu Sắc | Trọng Số Biểu Quyết |
| :--- | :---: | :--- | :---: | :---: |
| **Sentinel** | `NEWS` | Người Gác Cổng Vĩ Mô & Giám Sát Tin Tức Khẩn | 📰 `badge-purple` | 35% |
| **Vector** | `TECHNICAL` | Viện Trưởng Viện Kỹ Thuật Đa Trường Phái & Vector RAG | 📐 `badge-blue` | 40% |
| **Scribe** | `REFLEXION` | Người Ghi Sử Ký Giao Dịch & Huấn Luyện Viên Phản Tư | 🧠 `badge-green` | 25% |
| **Arbiter** | `GOVERNOR` | Trọng Tài Tối Cao & Giám Đốc Quản Trị Rủi Ro (CRO) | 🛡️ `badge-gold` | 100% (Quyền phủ quyết) |
| **Council** | `COUNCIL` | Hội Đồng Đa Agent Đồng Thuận Toàn Diện | 🏛️ `badge-amber` | 100% (Tổng hợp) |

Hồ sơ hệ thống chi tiết bao gồm System Prompts, Quy tắc ứng xử (Persona Tone), Ràng buộc bảo vệ vốn và Hợp đồng I/O được quy định đầy đủ tại [Agents_Profile.md](Agents_Profile.md).

---

## 5. ĐỘNG CƠ ĐỒNG BỘ REAL-TIME HAI CHIỀU (UNIFIED REACTIVE STATE & EVENT BUS)

Cơ chế cốt lõi đảm bảo tính nhất quán tuyệt đối giữa **Global Pop-up** và **Dedicated Chat Studio** dựa trên 3 trụ cột kỹ thuật:

```
[ FRONTEND GLOBAL POP-UP ]                   [ FRONTEND DEDICATED STUDIO ]
          │                                                │
          ├─── Gửi tin nhắn / Đổi conversation ────────────┤
          ▼                                                ▼
+──────────────────────────────────────────────────────────────────────────+
| PINIA STORE (frontend/src/stores/chatStore.js)                           |
| - conversations: Array<ChatConversation>                                 |
| - activeConversationId: number | null                                    |
| - messagesMap: Record<number, Array<ChatMessage>>                        |
| - unreadCount: number                                                    |
| - isWidgetOpen: boolean                                                  |
| - sendUserMessage(conversationId, text)                                  |
| - switchConversation(conversationId)                                     |
| - handleIncomingSocketEvent(event)                                       |
+────────────────────────────────────┬─────────────────────────────────────+
                                     │
                    WebSocket Sync   │   HTTP Mutations
                                     ▼
+──────────────────────────────────────────────────────────────────────────+
| FASTAPI BACKEND (WebSocket Manager & Chat Service)                       |
| - Redis Pub/Sub: agent:trader:dialogue                                   |
| - Bắn sự kiện: chat.message.new, chat.session.updated, governor.approval  |
+──────────────────────────────────────────────────────────────────────────+
```

### Nguyên Lý Đồng Bộ:
1. **Single Source of Truth (Pinia `chatStore`):** Cả Pop-up Widget và Chat Studio đều liên kết dữ liệu trực tiếp với `chatStore`. Khi `activeConversationId` hoặc `messagesMap` thay đổi, cả hai bề mặt giao diện tự động cập nhật phản ứng thông qua Vue 3 Reactivity (Zero State Drift).
2. **Real-time Event Broadcasting:** Khi một tin nhắn được tạo ra (từ phía Trader hoặc từ Governor Agent), Backend lập tức phát sóng sự kiện qua kênh Redis Pub/Sub `agent:trader:dialogue`. WebSocket server chuyển tiếp ngay đến trình duyệt với event type `chat.message.new`.
3. **Phân biệt Trạng thái Đọc/Chưa đọc (Smart Read/Unread Tracking):**
   - Nếu Trader đang mở Chat Studio hoặc đang mở Pop-up Widget ở đúng cuộc trò chuyện đó: Tin nhắn mới lập tức được đánh dấu đã đọc (`unread = false`).
   - Nếu Trader đang ở view khác và Pop-up đang đóng: Tăng biến đếm `unreadCount += 1`, hiển thị badge đỏ trên Pop-up FAB và kích hoạt toast preview.

---

## 6. MÔ HÌNH DỮ LIỆU & SCHEMA BỔ SUNG (`0007_phase3_sprint3_chat.sql`)

### 6.1. Migration DDL: `backend/migrations/0007_phase3_sprint3_chat.sql`
```sql
-- Migration 0007: Phase 03 - Sprint 03 - Multi-Conversation Real-time Chat System

-- 1. Bảng quản lý danh sách cuộc trò chuyện (Chat Conversations)
CREATE TABLE IF NOT EXISTS chat_conversations (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    agent_target VARCHAR(64) NOT NULL DEFAULT 'GOVERNOR', -- 'GOVERNOR', 'TECHNICAL', 'NEWS', 'REFLEXION', 'COUNCIL'
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_test BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated_at ON chat_conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_is_pinned ON chat_conversations(is_pinned);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_is_test ON chat_conversations(is_test);

-- 2. Nâng cấp bảng agent_trader_dialogue để gắn kết với conversation
ALTER TABLE agent_trader_dialogue
    ADD COLUMN IF NOT EXISTS conversation_id BIGINT REFERENCES chat_conversations(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS client_msg_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS target_agent VARCHAR(64) NOT NULL DEFAULT 'GOVERNOR';

CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_conv_id ON agent_trader_dialogue(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_trader_dialogue_client_msg_id ON agent_trader_dialogue(client_msg_id);
```

### 6.2. SQLAlchemy ORM Models (`backend/core/models.py`)
```python
class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, default="Cuộc trò chuyện mới")
    agent_target = Column(String(64), nullable=False, default="GOVERNOR")
    is_pinned = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    is_test = Column(Boolean, nullable=False, default=False)

    dialogues = relationship("AgentTraderDialogue", back_populates="conversation", cascade="all, delete-orphan")
```

---

## 7. HỢP ĐỒNG GIAO TIẾP: REST API & WEBSOCKET PROTOCOL

### 7.1. REST API Controllers (`/api/v1/chat/`)
* `GET /api/v1/chat/conversations`: Lấy danh sách cuộc trò chuyện (hỗ trợ lọc `is_archived`, sắp xếp theo `is_pinned` DESC và `updated_at` DESC).
* `POST /api/v1/chat/conversations`: Tạo cuộc trò chuyện mới.
  - *Request Body:* `{"title": "Review rủi ro phiên Mỹ", "agent_target": "GOVERNOR"}`
* `PATCH /api/v1/chat/conversations/{id}`: Cập nhật tiêu đề, ghim (`is_pinned`), hoặc lưu trữ (`is_archived`).
* `DELETE /api/v1/chat/conversations/{id}`: Xóa cuộc trò chuyện và toàn bộ tin nhắn liên quan.
* `GET /api/v1/chat/conversations/{id}/messages`: Lấy toàn bộ lịch sử tin nhắn trong cuộc trò chuyện.
* `POST /api/v1/chat/conversations/{id}/messages`: Gửi tin nhắn mới vào cuộc trò chuyện và nhận phản hồi tức thời từ Agent.
  - *Request Body:*
    ```json
    {
      "message": "Nới SL lên 2.0x ATR và kiểm tra tình hình tin tức",
      "target_agent": "GOVERNOR",
      "attach_market_context": true
    }
    ```

### 7.2. WebSocket Protocol Events (`/api/v1/ws/market`)
* `chat.message.new`: Bắn gói tin nhắn mới được ghi nhận vào hệ thống.
  ```json
  {
    "type": "chat.message.new",
    "conversation_id": 1,
    "message": {
      "id": 105,
      "sender": "GOVERNOR",
      "message_text": "Đã cập nhật tham số ATR SL Multiplier thành 2.0x...",
      "message_type": "COMMAND_RESPONSE",
      "timestamp": "2026-10-12T15:45:00+07:00"
    }
  }
  ```
* `chat.session.updated`: Bắn tín hiệu khi có thay đổi tiêu đề hoặc ghim session để cập nhật Sidebar ở mọi client.
* `governor.approval_request`: Bắn thông báo khẩn yêu cầu Trader phê duyệt lệnh, kích hoạt popup trên cả 2 bề mặt.

---

## 8. KẾ HOẠCH TRIỂN KHAI THEO TASK (TASK BREAKDOWN T1–T6)

Kế hoạch thực hiện Phase 03 - Sprint 03 được phân rã thành 6 Task kỹ thuật bài bản, tuần tự và bảo đảm chuẩn D18:

| Mã Task | Tên Task & Trách Nhiệm Kỹ Thuật | Sản Phẩm Bàn Giao Cụ Thể | Tiêu Chuẩn Hoàn Thành (DoD) |
| :--- | :--- | :--- | :--- |
| **Task 1** | **Database Migration `0007`, ORM Models & Infrastructure Setup** | File migration `0007_phase3_sprint3_chat.sql`, model `ChatConversation`, mở rộng `AgentTraderDialogue`, fixture dọn dẹp D18 trong `conftest.py`. | Migration chạy mượt mà, test suite backend pass 100%, dữ liệu test sạch sẽ sau mỗi lượt test. |
| **Task 2** | **Backend Chat Service, Multi-Session Management & REST API Router** | Service `backend/ai_engine/chat_service.py`, router `/api/v1/chat/`, auto-titling logic, định tuyến agent đa persona, unit tests backend. | Tạo/sửa/xóa session chuẩn xác, bóc tách lệnh an toàn qua Hard Guardrails D21/D24, phát Redis Pub/Sub tức thì. |
| **Task 3** | **Dedicated Multi-Conversation Chat Studio Component (Gemini Style) Trong Strategy & Analysis** | Component `AIChatStudioView.vue` tích hợp vào `StrategyAnalysisView.vue` (Sub-tab chuyên biệt), Sidebar chia session theo thời gian (Today/7D/Older), Markdown thread, Interactive Approval Cards, Quick Prompts. | Trải nghiệm mượt mà chuẩn Gemini, tạo New Chat tức thời, đổi tên/xóa session không reload trang, tương tác 2 chiều hoàn hảo. |
| **Task 4** | **Global Pop-up Chat Widget Xuyên Suốt Toàn Giao Diện** | Component `GlobalChatWidget.vue` nhúng tại `App.vue`, Floating Action Pill, Unread Badge, Mini Chat Console, Quick Commands, nút chuyển nhanh sang Full Studio. | Hiển thị cố định trên mọi màn hình (Cockpit, Orders, News, Strategy, Backtest, Settings), duyệt lệnh khẩn cấp tức thì. |
| **Task 5** | **Động Cơ Đồng Bộ Real-time Hai Chiều (Unified Pinia State & Event Bus)** | Pinia Store `frontend/src/stores/chatStore.js`, kết nối WebSocket `/api/v1/ws/market`, xử lý sự kiện `chat.message.new`, đồng bộ Pop-up & Studio. | Gửi tin nhắn ở Pop-up lập tức hiện ở Chat Studio và ngược lại, unread counter nhảy số chuẩn xác, zero data loss. |
| **Task 6** | **Kiểm Thử Toàn Diện, Phân Lập D18 & Biên Dịch Hệ Thống (E2E Validation & Build)** | Bộ unit/integration tests `test_chat_system_sprint3.py`, kiểm thử dọn dẹp CSDL test, biên dịch frontend `npm run build`. | 100% backend tests pass, frontend build thành công không có lỗi, hệ sinh thái hoàn thiện khép kín. |

---

## 9. KIỂM THỬ, CHUẨN D18 & TIÊU CHUẨN NGHIỆM THU (DEFINITION OF DONE)

### 9.1. Rào Chắn An Toàn & Chuẩn Phân Lập D18
* **100% D18 Compliant:** Mọi bản ghi kiểm thử trong `chat_conversations` và `agent_trader_dialogue` bắt buộc có `is_test = TRUE`. Fixture `conftest.py` tự động quét sạch các bản ghi thử nghiệm sau khi hoàn tất test suite.
* **Bảo toàn Hard Guardrails (D21/D24):** Bất kể tin nhắn được gửi từ Pop-up hay Dedicated Chat Studio, các chỉ thị thay đổi rủi ro vẫn phải vượt qua bộ thẩm định Pydantic nghiêm ngặt ($0.25\% \le \text{Risk} \le 1.50\%$, Drawdown $< 3.0\%$).

### 9.2. Tiêu Chí Nghiệm Thu Tổng Thể (Definition of Done - DoD)
- [ ] Bảng `chat_conversations` và các trường bổ sung được tạo thành công trong PostgreSQL.
- [ ] Backend cung cấp đầy đủ các REST API endpoints `/api/v1/chat/...` với mã phản hồi chuẩn RESTful.
- [ ] Dedicated Chat Studio hoạt động mượt mà trong Tab Strategy & Analysis với bố cục đa hội thoại phong cách Gemini.
- [ ] Global Pop-up Widget xuất hiện liên tục và hoạt động ổn định trên toàn bộ các view của ứng dụng.
- [ ] Hai bề mặt giao tiếp đồng bộ thời gian thực 100% qua WebSocket và Pinia Store.
- [ ] Toàn bộ backend test suite đạt kết quả **Passed 100%**.
- [ ] Frontend biên dịch thành công (`npm run build`) không có cảnh báo hay lỗi cú pháp.
- [ ] Cá nhân hóa định danh các AI Agent (Sentinel, Vector, Scribe, Arbiter) và hoàn thiện hồ sơ hệ thống [Agents_Profile.md](Agents_Profile.md).
- [ ] Tiến độ được ghi nhận đầy đủ, minh bạch vào [Backlog.md](Backlog.md).
