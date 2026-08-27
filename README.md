# Yêu cầu hệ thống
- Máy tính sử dụng hệ điều hành Windows 10/11, Linux, MacOS
- Đã cài đặt Python >3.13
- Đã cài đặt PostgreSQL/PostGIS
- Đã cài đặt các thư viện Python: pip, segyio, fastapi, alembic,....

# Các bước cài đặt chương trình
## 1. Clone dự án

```bash
git clone <repository_url>
cd WebGIS
```

________________________________

## 2. Cài đặt Backend

2.1. Backend 1

```text
Di chuyển vào thư mục:
cd backend
cd segy-processing-service

Khởi tạo venv:
python -m venv venv

Cài đặt các thư viện sử dụng pip:
python -m pip install <library_name>

Sao chép file cấu hình môi trường:
cp .env.example .env
```

Cấu hình kết nối CSDL trong .env

```text
DATABASE_URL=postgresql+psycopg://postgres:<your_password>@localhost:5432/webgis
```

2.2. Backend 2 (tương tự backend 1 với folder data-serving)

_________________________________

## 3. Cài đặt Database

```text
Tạo cơ sở dữ liệu mới:
CREATE DATABASE webgis

Thực hiện các migration tạo bảng dữ liệu
alembic upgrade head
```

__________________________________

## 4. Hướng dẫn chạy project

### Terminal 0: Khởi động MinIO Server (Local)

Chạy file script tự động tải và khởi động MinIO (chỉ cần chạy lần đầu sẽ tự download `minio.exe`):

```bash
# Bằng Command Prompt / double click:
start_minio.bat

# Hoặc bằng PowerShell:
.\start_minio.ps1
```

- **S3 API**: `http://localhost:9000`
- **MinIO Web Console**: `http://localhost:9001` (Tài khoản: `minioadmin` / `minioadmin`)

### Terminal 1: Backend 1 (segy-processing-service)

```bash
cd backend
cd segy-processing-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Backend 2 (data-serving)

```bash
cd backend
cd data-serving
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Terminal 3: Frontend

```bash
cd frontend
npm run dev
```

