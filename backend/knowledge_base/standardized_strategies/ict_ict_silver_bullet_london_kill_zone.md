# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## Chiến lược ICT ICT Silver Bullet & London Kill Zone

> **Mã định danh (Slug):** `ict_ict_silver_bullet_london_kill_zone`  
> **Trường phái học thuật:** `ICT`  
> **Khung thời gian chuẩn:** `M15`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:2.0`  
> **Cập nhật hệ thống:** `2026-10-16 04:35:58 UTC`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
Khai thác thuật toán phân phối giá liên ngân hàng (IPDA), chu kỳ Power of 3 (AMD: Accumulation - Manipulation - Distribution) và mô hình Silver Bullet tại các khung giờ vàng (Kill Zones).

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
- [ ] **Bước 1:** Thời điểm giao dịch nằm trong Kill Zone (London: 14:00-17:00 ICT hoặc NY AM: 19:00-22:00 ICT)
- [ ] **Bước 2:** Giá quét thanh khoản cũ (Buyside/Sellside Liquidity Pool hoặc Judas Swing)
- [ ] **Bước 3:** Xuất hiện sóng dịch chuyển mạnh mẽ (Displacement) tạo sự phá vỡ cấu trúc Market Structure Shift (MSS)
- [ ] **Bước 4:** Để lại khoảng trống giá mất cân bằng Fair Value Gap (FVG) hợp lệ (biên độ ≥ 0.3x ATR)
- [ ] **Bước 5:** Giá hồi quy về vùng FVG (Consequent Encroachment 50% hoặc Optimal Trade Entry 62-79% Fib)
- [ ] **Bước 6:** R:R tối thiểu đạt ≥ 1:2.0 đến vùng thanh khoản đối ứng tiếp theo

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** Đặt Limit Entry tại ngưỡng trên của Bullish FVG (hoặc ngưỡng dưới của Bearish FVG) khi giá chạm vùng hồi quy.
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** Đặt SL vượt qua đỉnh/đáy nến displacement hình thành FVG kèm đệm 1.5x ATR.
* **Chốt lời (Take Profit):** TP1 tại 1:2.0R (chốt 50% và khóa hòa vốn); TP2 tại vùng đỉnh/đáy cũ (Old Highs/Old Lows EQH/EQL).
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* Cây nến M15 đóng cửa xuyên thủng hoàn toàn FVG (Full Inversion Gap).
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `0.25% – 1.0%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `0.5%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `3.0%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).