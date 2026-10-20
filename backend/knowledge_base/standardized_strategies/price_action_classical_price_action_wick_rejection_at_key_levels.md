# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## Chiến lược Price Action Classical Price Action - Wick Rejection at Key Levels

> **Mã định danh (Slug):** `price_action_classical_price_action_wick_rejection_at_key_levels`  
> **Trường phái học thuật:** `PRICE_ACTION`  
> **Khung thời gian chuẩn:** `M15`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:2.0`  
> **Cập nhật hệ thống:** `2026-10-16 04:35:58 UTC`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
Đọc hành động giá thuần túy (Price Action): Tương quan lực nến, hấp thụ thanh khoản tại cản then chốt, mô hình nến râu từ chối (Wick Rejection) và nến nhấn chìm (Engulfing).

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
- [ ] **Bước 1:** Giá tiếp cận Key Level (Hỗ trợ/Kháng cự then chốt H1)
- [ ] **Bước 2:** Xuất hiện nến rút chân mạnh (Wick Rejection ≥ 60% chiều dài thân nến)
- [ ] **Bước 3:** Nến tiếp theo là nến xác nhận đóng theo hướng đảo chiều
- [ ] **Bước 4:** Tỷ lệ R:R ≥ 1:2.0

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** Mở vị thế ngay khi nến xác nhận đóng cửa.
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** Đặt SL ngoài đầu râu nến từ chối dài nhất cộng 1.2x ATR.
* **Chốt lời (Take Profit):** TP1 tại 1:1.5R dời SL về Entry; TP2 tại vùng cản đối diện 1:2.5R.
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* Giá phá vỡ đầu râu nến từ chối trước khi khớp lệnh.
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `0.25% – 1.0%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `0.5%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `3.0%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).