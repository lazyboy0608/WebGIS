# HƯỚNG DẪN TRIỂN KHAI VÀ VẬN HÀNH WEBGIS TỰ ĐỘNG BẰNG CI/CD GITHUB ACTIONS (ON-PREMISE)

> **Tổng quan:** Hệ thống WebGIS được đóng gói thành **1 Web Server duy nhất** chạy trên **1 máy vật lý** bằng **Docker Multi-Stage**, phục vụ người dùng trong **mạng cục bộ (LAN)** và được tự động hóa quy trình cập nhật mã nguồn bằng **GitHub Actions CI/CD (Self-Hosted Runner)** mà **không cần IP Public / không cần mở cổng Router**.

---

## I. DANH MỤC CÁC TỆP TIN ĐÃ THIẾT LẬP

```
WebGIS/
├── .github/
│   └── workflows/
│       └── deploy.yml              # [NEW] Pipeline CI/CD tự động deploy khi git push
├── .gitignore                      # Chuẩn hóa cho Git và CI/CD
├── .dockerignore                   # Loại bỏ .venv, node_modules, storage khỏi Build Context
├── docker-compose.yml              # Điều phối 6 services & persistent named volumes
├── .env.production.example         # Mẫu biến môi trường cho deploy / CI/CD
├── .env                            # File biến môi trường hoàn chỉnh trên máy chủ
├── frontend/
│   ├── .dockerignore               # Bỏ qua node_modules, dist
│   ├── Dockerfile                  # Multi-stage build (Node.js -> Nginx Alpine runtime)
│   └── nginx.conf                  # Cấu hình Nginx Gateway cổng 80, gzip, upload 2GB, WebSocket
├── backend/
│   ├── segy-processing-service/
│   │   ├── .dockerignore           # Bỏ qua .venv, storage, data, pycache
│   │   └── Dockerfile              # Multi-stage build Python + GDAL/GEOS C-extensions
│   └── data-serving/
│       ├── .dockerignore           # Bỏ qua .venv, pycache, tests
│       └── Dockerfile              # Multi-stage build Python + GeoAlchemy
└── scripts/
    ├── deploy_docker.sh / .bat     # Script triển khai thủ công
    ├── stop_docker.sh / .bat       # Script dừng hệ thống
    ├── backup_database.sh / .bat   # Script tự động sao lưu PostGIS database
    └── restore_database.sh / .bat  # Script khôi phục PostGIS database
```

---

## II. HƯỚNG DẪN CÀI ĐẶT GITHUB ACTIONS RUNNER TRÊN MÁY CHỦ UBUNTU (CHỈ LÀM 1 LẦN DUY NHẤT)

### Bước 1: Chuẩn bị máy chủ Ubuntu (Cài đặt Docker nếu máy mới tinh)
Mở Terminal trên máy chủ Ubuntu và chạy các lệnh sau:

```bash
# 1. Cài đặt các gói phụ trợ
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 2. Thêm khóa GPG của Docker
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 3. Thêm repository Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Cài đặt Docker Engine & Docker Compose Plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Cấp quyền chạy Docker không cần sudo
sudo usermod -aG docker $USER
newgrp docker

# 6. Bật Docker tự khởi động cùng máy tính khi bật nguồn
sudo systemctl enable docker
sudo systemctl start docker
```

---

### Bước 2: Lấy Token Runner từ GitHub Repository
1. Mở trình duyệt, truy cập vào Repository GitHub chứa dự án WebGIS của bạn.
2. Vào **Settings** (của Repository) -> Mục bên trái chọn **Actions** -> Chọn **Runners**.
3. Bấm vào nút màu xanh **`New self-hosted runner`**.
4. Chọn hệ điều hành: **Linux**, Kiến trúc: **x64**.
5. GitHub sẽ hiển thị các dòng lệnh và **Token** được cấp riêng cho bạn.

---

### Bước 3: Cài đặt và kích hoạt Runner Service trên máy Ubuntu
Mở Terminal máy chủ Ubuntu và thực hiện lần lượt:

```bash
# 1. Tạo thư mục chứa runner và tải package chính thức của GitHub
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf ./actions-runner-linux-x64.tar.gz

# 2. Cấu hình kết nối Runner với Repo (Dùng URL và TOKEN hiển thị trên GitHub của bạn)
./config.sh --url https://github.com/YOUR_USERNAME/YOUR_REPO --token YOUR_TOKEN_FROM_GITHUB

# Nhấn Enter cho tất cả các câu hỏi để lấy giá trị mặc định:
# - Enter name of runner: [Nhấn Enter]
# - Enter additional labels: [Nhấn Enter]
# - Enter name of work folder: [Nhấn Enter]

# 3. Cài đặt Runner thành Systemd Service (Tự chạy ngầm cùng Ubuntu khi bật máy)
sudo ./svc.sh install
sudo ./svc.sh start
```

Sau khi chạy xong, quay lại trang GitHub (Settings > Actions > Runners): Bạn sẽ thấy Runner hiện trạng thái **🟢 Idle (Online)**.

---

### Bước 4: Mở cổng tường lửa (UFW Firewall) trên Ubuntu
Để các máy tính trong mạng LAN truy cập vào máy chủ:

```bash
sudo ufw allow 80/tcp
sudo ufw status
```

---

## III. QUY TRÌNH LÀM VIỆC VÀ CẬP NHẬT CODE TỰ ĐỘNG HÀNG NGÀY

Từ bây giờ, bạn **không cần nén file .zip và không cần dùng WinSCP nữa**.

Mỗi khi bạn hoàn thành một tính năng hoặc sửa lỗi trên máy phát triển (Windows):

```bash
# 1. Thêm các thay đổi
git add .

# 2. Commit với nội dung mô tả
git commit -m "Cập nhật tính năng X"

# 3. Đẩy lên GitHub
git push origin main
```

### Điều gì sẽ tự động diễn ra:
1. **GitHub Actions** ngay lập tức kích hoạt workflow `.github/workflows/deploy.yml`.
2. **Self-Hosted Runner** trên máy chủ Ubuntu nhận tín hiệu qua kết nối Outbound HTTPS:
   - Tự động kéo mã nguồn mới nhất về.
   - Tự động chạy `docker compose up -d --build` (chỉ mất 10 - 30 giây nhờ Docker layer cache).
   - Tự động chạy `alembic upgrade head` để cập nhật bảng cơ sở dữ liệu nếu có migration mới.
   - Tự động dọn dẹp các Docker images cũ thừa (`docker image prune -f`).
3. Toàn bộ người dùng trong mạng LAN chỉ cần F5 lại trình duyệt `http://<IP_MAY_CHU>` là thấy ngay phiên bản mới!

---

## IV. CÁC LỆNH QUẢN TRỊ VÀ SAO LƯU DỮ LIỆU ĐỊNH KỲ

### 1. Xem trạng thái và log hệ thống trên Ubuntu
```bash
# Xem trạng thái 6 container
docker compose ps

# Xem log thời gian thực của toàn bộ hệ thống
docker compose logs -f

# Xem riêng log Nginx Gateway (cổng 80)
docker compose logs -f gateway
```

### 2. Sao lưu Database PostGIS định kỳ
```bash
# Chạy script sao lưu dữ liệu ra thư mục backups/
./scripts/backup_database.sh
```
*(Bạn có thể thiết lập cronjob tự động sao lưu lúc 2h sáng mỗi ngày bằng cách gõ `crontab -e` và thêm dòng: `0 2 * * * /home/ubuntu/WebGIS/scripts/backup_database.sh`).*

### 3. Khôi phục Database từ bản sao lưu
```bash
./scripts/restore_database.sh backups/webgis_backup_YYYY-MM-DD_HH-MM-SS.sql
```

### 4. Dừng hệ thống khi cần bảo trì
```bash
./scripts/stop_docker.sh
```

---

## V. KIỂM THỬ TRUY CẬP TỪ MẠNG NỘI BỘ (LAN)

1. Từ bất kỳ máy tính/laptop nào trong mạng LAN, mở trình duyệt và gõ:
   ```
   http://<IP_MAY_CHU_UBUNTU>
   ```
   *(Ví dụ: `http://192.168.1.100`)*
2. **Kiểm tra các luồng nghiệp vụ:**
   - Đăng nhập / Đăng ký tài khoản người dùng (`/login`).
   - Đăng nhập tài khoản Quản trị viên (`/admin`) với tài khoản mặc định được tự động seed khi khởi động:
     - **Email:** `admin@webgis.com`
     - **Mật khẩu:** `Admin@123456`
   - Quản trị viên theo dõi mức độ sử dụng CPU, RAM, Ổ đĩa máy chủ thời gian thực, quản lý danh sách người dùng, cấp quyền và đặt lại mật khẩu cho thành viên.
   - Upload file địa chấn `.segy` dung lượng lớn -> Thanh tiến trình WebSocket cập nhật realtime.
   - Bản đồ MapLibre hiển thị các đường khảo sát và mảnh Vector Tiles (MVT).
   - Upload Shapefile ranh giới lô, thử nghiệm cắt lô, hoàn tác và xuất báo cáo Excel.

