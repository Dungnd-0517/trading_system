# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## Chiến lược Wyckoff Wyckoff Method - Phase C Spring Accumulation

> **Mã định danh (Slug):** `wyckoff_wyckoff_method_phase_c_spring_accumulation`  
> **Trường phái học thuật:** `WYCKOFF`  
> **Khung thời gian chuẩn:** `H1 / M15`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:2.0`  
> **Cập nhật hệ thống:** `2026-10-16 04:35:58 UTC`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
Ứng dụng chu kỳ tích lũy/phân phối của Richard Wyckoff. Xác định dòng tiền tổ chức (Smart Money) qua hành vi gom hàng (Accumulation Phase C Spring) hoặc phân phối (Distribution UTAD), kết hợp kiểm tra khối lượng nỗ lực so với kết quả (Effort vs Result - VSA).

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
- [ ] **Bước 1:** Xác định khung tích lũy Trading Range (TR) có Phase A (SC/AR) và Phase B
- [ ] **Bước 2:** Xuất hiện Spring (Phase C) quét thủng Preliminary Support/Đáy Range với khối lượng cạn kiệt
- [ ] **Bước 3:** Nến kiểm tra (Test of Spring) giữ vững trên đáy cũ và hồi phục dứt khoát
- [ ] **Bước 4:** Xuất hiện cây nến Sign of Strength (SOS) vượt ngưỡng kháng cự trung tâm Creek
- [ ] **Bước 5:** Tỷ lệ tiềm năng Risk:Reward ≥ 1:2.5 hướng tới mục tiêu đỉnh biên trên của Range
- [ ] **Bước 6:** Không có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) trong vòng 30 phút

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** Mở vị thế BUY tại nhịp hồi kiểm tra (LPS - Last Point of Support) sau cú bật của Spring hoặc SOS.
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** Đặt Stop Loss cách đáy Spring thấp nhất 1.5x ATR M15 để bảo vệ khỏi các cú quét râu thứ cấp.
* **Chốt lời (Take Profit):** TP1 tại mốc 1:2.0R (đóng 50% khối lượng và dời SL về Breakeven); TP2 tại đỉnh biên trên Range (Jump Across Creek) 1:3.0R - 1:4.0R.
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* Giá đóng cửa nến M15 dứt khoát dưới đáy Spring; hoặc thị trường xuất hiện khối lượng bán tháo bất thường (SOW).
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `0.25% – 1.0%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `0.5%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `3.0%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).