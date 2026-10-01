tests/test_smc.py    test no-look-ahead, BOS/CHoCH, DST, tính lot
# Trading System | Stage 01

Nền tảng phân tích thị trường đa tài sản với FastAPI, Vue 3, PostgreSQL, Redis và paper execution. Mặc định hệ thống chỉ mô phỏng, không gửi lệnh tới tài khoản broker.

## Cấu trúc

- `backend/`: REST/WebSocket API, ingestion adapters, AI context, mô phỏng lệnh và schema.
- `frontend/`: Vue 3 cockpit với Lightweight Charts, trạng thái dịch vụ, tin tức và paper positions.
- `mt5-bridge/`: HTTP adapter đọc tick MT5; bridge chỉ hoạt động khi có MetaTrader5 runtime tương thích.
- `docker-compose.yml`: PostgreSQL 16, Redis 7, backend, frontend và bridge.
- `Architecture.md`: kiến trúc nền, quy ước tài liệu và cách cập nhật phase/sprint.
- `Architecture_phase_02_sprint_01.md`: delta Phase 2, Sprint 1; D2–D6 đã chốt, sẵn sàng triển khai code sau khi kiểm tra production gates theo từng provider.

## Chạy local

1. Cài Docker Desktop và khởi động Docker Engine.
2. Sao chép `.env.example` thành `.env`, đặt mật khẩu PostgreSQL riêng.
3. Chạy `docker compose up --build`.
4. Mở cockpit tại `http://localhost:3000`, API docs tại `http://localhost:8000/docs`, health tại `http://localhost:8000/health`.

PostgreSQL/Redis được công bố ở các cổng 5432/6379 để tiện phát triển. Schema chỉ tự nạp ở lần khởi tạo volume DB đầu tiên. Muốn khởi tạo lại dữ liệu phát triển, dừng stack và xóa volume `pgdata` bằng `docker compose down -v`.

## Tình trạng tích hợp

- API và UI đã có khung hoạt động, nhưng market/news collectors chưa được chạy như background workers và DB chưa có dữ liệu ban đầu; biểu đồ sẽ ở trạng thái chờ cho tới khi pipeline ghi dữ liệu.
- MT5 Python package phụ thuộc Windows. Image bridge hiện báo `unavailable` nếu runtime MT5 không có; để kết nối terminal thật cần triển khai bridge trên Windows hoặc bổ sung image Wine/MT5 đã được xác minh cho môi trường đích.
- AI engine hiện có kiểm tra dữ liệu và logic gợi ý cơ bản, chưa gọi LLM provider.
- Đây chưa phải hệ thống production: chưa có migrations, xác thực người dùng, quản lý secrets, giám sát đầy đủ hay xác minh với broker.

## Kiểm thử

Backend tests: `python -m pytest backend/tests`.

Build frontend: `cd frontend; npm install; npm run build`.
