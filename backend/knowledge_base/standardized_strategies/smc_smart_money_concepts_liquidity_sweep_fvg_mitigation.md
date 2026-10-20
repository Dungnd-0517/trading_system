# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## Chiến lược SMC Smart Money Concepts - Liquidity Sweep & FVG Mitigation

> **Mã định danh (Slug):** `smc_smart_money_concepts_liquidity_sweep_fvg_mitigation`  
> **Trường phái học thuật:** `SMC`  
> **Khung thời gian chuẩn:** `D1 -> H1 -> M15`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:2.0`  
> **Cập nhật hệ thống:** `2026-10-16 04:35:58 UTC`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
Phân tích cấu trúc dòng tiền tổ chức (Smart Money Concepts): Xác định xu hướng HTF (D1/H4), vùng cung cầu mất cân bằng POI (Order Block, FVG) tại vùng Discount/Premium và xác nhận tín hiệu kích hoạt M15 CHoCH.

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
- [ ] **Bước 1:** HTF Trend / Bias trên D1 & H4 đồng thuận (D1/H4 Alignment)
- [ ] **Bước 2:** Xác định POI H1 (OB hoặc FVG) nằm đúng vùng Discount (BUY) hoặc Premium (SELL)
- [ ] **Bước 3:** Thời điểm giao dịch nằm trong Kill Zone London hoặc New York AM
- [ ] **Bước 4:** Giá nhúng vào vùng POI H1 (Tap POI)
- [ ] **Bước 5:** Xuất hiện tín hiệu đảo chiều cấu trúc M15 CHoCH kèm displacement
- [ ] **Bước 6:** Tỷ lệ R:R tiềm năng ≥ 1:2.0
- [ ] **Bước 7:** Không có tin tức vĩ mô 3 sao trong vòng 30 phút

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** Mở lệnh khi giá hồi quy nhẹ về OB nội phiên M15 sau khi đã hình thành CHoCH rõ rệt.
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** Đặt Stop Loss cách đáy POI M15 1.5x ATR.
* **Chốt lời (Take Profit):** TP1 tại 1:2.0R (chốt 50%, dời SL hòa vốn); TP2 tại đỉnh Swing High H1 (1:3.0R).
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* Giá nến M15 đóng cửa xuyên thủng hoàn toàn vùng POI H1.
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `0.25% – 1.0%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `0.5%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `3.0%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).