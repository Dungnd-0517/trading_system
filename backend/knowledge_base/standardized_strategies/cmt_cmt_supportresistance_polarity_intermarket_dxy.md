# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## Chiến lược CMT CMT Support/Resistance Polarity & Intermarket DXY

> **Mã định danh (Slug):** `cmt_cmt_supportresistance_polarity_intermarket_dxy`  
> **Trường phái học thuật:** `CMT`  
> **Khung thời gian chuẩn:** `H4 / M15`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:2.0`  
> **Cập nhật hệ thống:** `2026-10-16 04:35:58 UTC`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
Dựa trên giáo trình Chartered Market Technician (CMT): Nguyên lý phân cực Hỗ trợ - Kháng cự (Support/Resistance Polarity), xác nhận xu hướng bằng Lý thuyết Dow và phân tích liên thị trường (DXY & Lãi suất thực).

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
- [ ] **Bước 1:** Khung lớn H4 xác nhận xu hướng tăng theo Lý thuyết Dow (Higher Highs / Higher Lows)
- [ ] **Bước 2:** Chỉ số Dollar Index (DXY) phân kỳ nghịch hướng xác nhận đà tăng của Vàng XAUUSD
- [ ] **Bước 3:** Giá hồi về kiểm tra ngưỡng Phân Cực (Polarity Level: Kháng cự cũ chuyển thành Hỗ trợ mới)
- [ ] **Bước 4:** Tín hiệu đảo chiều xác nhận tại M15 (Nến Pinbar / Bullish Engulfing)
- [ ] **Bước 5:** R:R đạt chuẩn tối thiểu ≥ 1:1.8

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** Vào lệnh tại mức giá đóng cửa của nến xác nhận M15 khi kiểm tra thành công ngưỡng Polarity.
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** Đặt SL dưới đáy vùng hỗ trợ phân cực 1.5x ATR M15.
* **Chốt lời (Take Profit):** TP1 tại đỉnh gần nhất của sóng H4; TP2 theo tỷ lệ mở rộng Fibonacci 1.618.
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* Giá phá vỡ hỗ trợ phân cực và đóng nến H1 phía dưới.
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `0.25% – 1.0%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `0.5%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `3.0%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).