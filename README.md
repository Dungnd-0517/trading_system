# Trading System | Phase 2 - Sprint 2

Nền tảng phân tích thị trường đa tài sản và giao dịch mô phỏng (Paper Trading) cho XAUUSD (Gold) phát triển bằng FastAPI, Vue 3, PostgreSQL, Redis và WebSocket. Mặc định hệ thống hoạt động ở chế độ mô phỏng nội bộ, không gửi lệnh tới broker thật.

## Cấu trúc

- `backend/`: REST & WebSocket API, background workers (Binance PAXG feed 24/7, news ingestion, paper execution engine), additive migrations và models cơ sở dữ liệu.
- `frontend/`: Vue 3 + Vite, TradingView Lightweight Charts, Trading Cockpit (live chart, orderbook, news 3-day tabs), Orders History, News & Events và Settings.
- `mt5-bridge/`: Adapter HTTP đọc tick MT5 (tùy chọn khi cần kết nối MetaTrader5 terminal thật trên Windows).
- `docker-compose.yml`: Triển khai đồng bộ PostgreSQL 16, Redis 7, backend, frontend (Nginx) và bridge.
- `Architecture.md`: Kiến trúc nền tảng và quy chuẩn tài liệu kỹ thuật.
- `Architecture_phase_02_sprint_01.md` & `Architecture_phase_02_sprint_02.md`: Đặc tả kiến trúc chi tiết từng Sprint của Phase 2.
- `Backlog.md`: Nhật ký tiến độ và lịch sử nghiệm thu tính năng chi tiết.

## Chạy local

1. Cài Docker Desktop và khởi động Docker Engine.
2. Sao chép `.env.example` thành `.env`, cấu hình mật khẩu PostgreSQL và API keys (nếu có).
3. Chạy `docker compose up --build`.
4. Mở Cockpit tại `http://localhost:3000`, API docs tại `http://localhost:8000/docs`, health check tại `http://localhost:8000/health`.

PostgreSQL/Redis được công bố ở cổng 5432/6379 để tiện phát triển. Migrations additive (`0001`, `0002`, `0003`) tự động áp dụng khi backend khởi động. Muốn xóa sạch volume dữ liệu: `docker compose down -v`.

## Tình trạng tích hợp

- **Dữ liệu thị trường (Market Feed):** Tích hợp Binance `PAXGUSDT` WebSocket 24/7 (alias sang `XAUUSD`) kèm synthetic spread ECN 20 points ($0.20/oz); tự động seed 500 nến lịch sử cho cả 6 khung thời gian (`M1`, `M5`, `M15`, `H1`, `H4`, `D1`).
- **Khớp lệnh mô phỏng (Paper Execution):** Worker chạy nền tự động quét SL/TP theo từng tick Bid/Ask thực tế, tính slippage/commission/swap/PnL và phát sự kiện realtime; hỗ trợ đóng vị thế thủ công qua API và giao diện.
- **Tin tức & Lịch kinh tế (News & Events):** Worker thu thập tự động từ 4 nguồn (FairEconomy, Kitco, FXStreet, Finnhub); phân loại 1-3 sao, tính điểm Sentiment; khối Cockpit có 3 tabs ngày (`Yesterday`, `Today`, `Tomorrow` - mặc định Today) kèm nút chuyển hướng sang màn hình toàn bộ Economic Calendar.
- **Giao diện Cockpit & Đa màn hình:** Gồm 4 views chính: **Trading Cockpit** (biểu đồ nến tương tác kèm đường SL/TP/Markers, live metrics, tin tức), **Orders History** (lịch sử lệnh, win rate, PnL), **News & Events** (lịch kinh tế, headlines), **Settings** (cấu hình tham số, tài khoản, chẩn đoán hạ tầng).
- **MT5 Bridge:** Đóng vai trò adapter dự phòng khi cần kết nối terminal MT5 thật trên Windows; hệ thống vận hành hoàn toàn độc lập nhờ feed Binance.
- **AI Engine:** Tích hợp logic ngữ cảnh thị trường và cấu trúc SMC cơ bản; module LLM signals chuyên sâu nằm trong lộ trình Sprint tiếp theo.

## Kiểm thử

- **Backend tests:** Chạy trong Docker qua `docker compose exec backend pytest` (32 tests pass) hoặc local `python -m pytest backend/tests`.
- **Frontend build:** Kiểm tra bundle production qua `cd frontend && npm run build`.
