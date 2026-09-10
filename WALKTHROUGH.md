# BÁO CÁO HOÀN THÀNH & HƯỚNG DẪN VẬN HÀNH WEBGIS (SINGLE WEB SERVER LAN)

Đã hoàn tất việc đóng gói toàn bộ hệ thống WebGIS thành **1 Web Server duy nhất** chạy trên **1 máy vật lý** bằng **Docker Multi-Stage**, phục vụ mạng nội bộ (LAN) trên cả hai nền tảng hệ điều hành **Windows** và **Linux/Ubuntu**.

---

## 1. DANH MỤC CÁC TỆP TIN ĐÓNG GÓI

### A. Chuẩn hóa `.dockerignore` & `.gitignore`
- [x] [`.gitignore`](./.gitignore): Chuẩn hóa cho Git và CI/CD.
- [x] [`.dockerignore`](./.dockerignore), [`frontend/.dockerignore`](./frontend/.dockerignore), [`backend/segy-processing-service/.dockerignore`](./backend/segy-processing-service/.dockerignore), [`backend/data-serving/.dockerignore`](./backend/data-serving/.dockerignore): Loại bỏ `.venv`, `node_modules`, `storage`, logs khỏi Docker Build Context.

### B. Cấu hình Multi-Stage & Nginx Gateway
- [x] [`frontend/Dockerfile`](./frontend/Dockerfile): Multi-stage build (Node.js -> Nginx Alpine runtime).
- [x] [`frontend/nginx.conf`](./frontend/nginx.conf): Gateway định tuyến cổng 80, hỗ trợ upload 2GB, WebSocket progress, gzip compression.
- [x] [`backend/segy-processing-service/Dockerfile`](./backend/segy-processing-service/Dockerfile) & [`backend/data-serving/Dockerfile`](./backend/data-serving/Dockerfile): Multi-stage build Python + GDAL/GEOS C-extensions.

### C. Điều phối Docker Compose & Biến môi trường
- [x] [`docker-compose.yml`](./docker-compose.yml): Điều phối 6 services, kết nối qua mạng ảo nội bộ `webgis-network`, chỉ mở duy nhất cổng 80 ra mạng LAN.
- [x] [`.env.production.example`](./.env.production.example) & [`.env`](./.env): Quản lý tập trung biến môi trường và mật khẩu an toàn.

### D. Bộ công cụ Script Vận hành & Quản trị
- **Cho Windows:**
  - [`scripts/deploy_docker.bat`](./scripts/deploy_docker.bat): Script 1-Click build, khởi chạy và migrate Alembic.
  - [`scripts/stop_docker.bat`](./scripts/stop_docker.bat): Dừng toàn bộ hệ thống.
  - [`scripts/backup_database.bat`](./scripts/backup_database.bat): Tự động xuất file sao lưu `.sql`.
  - [`scripts/restore_database.bat`](./scripts/restore_database.bat): Khôi phục database từ file backup.
- **Cho Linux / Ubuntu:**
  - [`scripts/deploy_docker.sh`](./scripts/deploy_docker.sh): Script tự động triển khai trên Ubuntu/Debian.
  - [`scripts/stop_docker.sh`](./scripts/stop_docker.sh): Dừng các container an toàn.
  - [`scripts/backup_database.sh`](./scripts/backup_database.sh): Sao lưu PostGIS vào `backups/`.
  - [`scripts/restore_database.sh`](./scripts/restore_database.sh): Phục hồi database.

---

## 2. HƯỚNG DẪN VẬN HÀNH TRÊN MÁY CHỦ LINUX / UBUNTU

### Bước 1: Cài đặt Docker & Docker Compose (Nếu máy chủ mới tinh)
Trên máy chủ Ubuntu Server, mở terminal và chạy các lệnh sau:

```bash
# 1. Cập nhật apt và cài đặt các gói hỗ trợ
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 2. Thêm khóa GPG chính thức của Docker
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 3. Thêm repository Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Cài đặt Docker Engine & Docker Compose Plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Cấp quyền chạy Docker không cần sudo cho user hiện tại
sudo usermod -aG docker $USER
newgrp docker

# 6. Bật Docker tự khởi động cùng hệ điều hành Ubuntu
sudo systemctl enable docker
sudo systemctl start docker
```

---

### Bước 2: Triển khai WebGIS trên Ubuntu
1. Clone hoặc copy thư mục dự án `WebGIS` vào máy chủ (ví dụ `/opt/WebGIS` hoặc `/home/ubuntu/WebGIS`).
2. Di chuyển vào thư mục dự án và cấp quyền thực thi cho các scripts:
   ```bash
   cd /path/to/WebGIS
   chmod +x scripts/*.sh
   ```
3. Chạy script triển khai:
   ```bash
   ./scripts/deploy_docker.sh
   ```
   *Hệ thống sẽ tự động build images, khởi chạy 6 services, áp dụng migrations và hiển thị địa chỉ IP mạng LAN để truy cập.*

---

### Bước 3: Mở tường lửa (UFW Firewall) trên Ubuntu
Để các máy trạm khác trong mạng LAN truy cập được vào máy chủ WebGIS, mở cổng 80:

```bash
# Mở cổng 80 TCP
sudo ufw allow 80/tcp

# (Tùy chọn) Nếu cấu hình HTTPS sau này:
sudo ufw allow 443/tcp

# Kiểm tra trạng thái tường lửa
sudo ufw status
```

---

### Bước 4: Quản trị, Sao lưu & Khôi phục dữ liệu trên Ubuntu

- **Xem trạng thái các container:**
  ```bash
  docker compose ps
  ```
- **Xem log thời gian thực:**
  ```bash
  docker compose logs -f
  # Hoặc xem riêng gateway:
  docker compose logs -f gateway
  ```
- **Dừng hệ thống:**
  ```bash
  ./scripts/stop_docker.sh
  ```
- **Sao lưu Database PostGIS định kỳ:**
  ```bash
  ./scripts/backup_database.sh
  ```
  *(Có thể đặt cronjob `0 2 * * * /path/to/WebGIS/scripts/backup_database.sh` để tự động sao lưu lúc 2 giờ sáng mỗi ngày).*
- **Khôi phục Database khi cần:**
  ```bash
  ./scripts/restore_database.sh backups/webgis_backup_YYYY-MM-DD_HH-MM-SS.sql
  ```

---

## 3. HƯỚNG DẪN VẬN HÀNH TRÊN MÁY CHỦ WINDOWS

### Bước 1: Yêu cầu chuẩn bị
- Máy tính đã cài đặt **Docker Desktop for Windows** (bật WSL2 Backend).
- Đảm bảo Docker Desktop đã bật và đang chạy ở góc màn hình (`Docker Engine running`).

### Bước 2: Khởi động 1-Click
- Nhấp đúp chuột vào file:
  👉 **`scripts/deploy_docker.bat`**

### Bước 3: Mở cổng Firewall trên Windows (nếu máy trạm chưa kết nối được)
- Mở **PowerShell với quyền Administrator** và chạy:
  ```powershell
  New-NetFirewallRule -DisplayName "WebGIS LAN Port 80" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
  ```

### Bước 4: Sao lưu & Khôi phục trên Windows
- Nhấp đúp chuột vào [`scripts/backup_database.bat`](./scripts/backup_database.bat) để xuất bản sao lưu `.sql`.
- Để khôi phục: Kéo và thả file `.sql` vào file [`scripts/restore_database.bat`](./scripts/restore_database.bat).

---

## 4. KIỂM THỬ TRUY CẬP TỪ MẠNG NỘI BỘ (LAN)

1. Từ bất kỳ máy tính/laptop nào trong cùng mạng LAN, mở trình duyệt và gõ:
   ```
   http://<IP_MAY_CHU>
   ```
   *(Ví dụ: `http://192.168.1.100`)*
2. **Kiểm tra tính năng:**
   - Đăng nhập / Đăng ký tài khoản người dùng.
   - Upload file địa chấn SEG-Y dung lượng lớn -> Thanh tiến trình WebSocket cập nhật realtime.
   - Hiển thị bản đồ MapLibre và Vector Tiles (MVT).
   - Quản lý lô ranh giới (Seismic blocks): Cắt lô, hoàn tác, xuất báo cáo Excel.
