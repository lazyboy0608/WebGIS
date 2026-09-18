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
│   │   └── Dockerfile              # Multi-stage build Python + GDAL/GEOS C-extensions + non-root appuser
│   └── data-serving/
│       ├── .dockerignore           # Bỏ qua .venv, pycache, tests
│       └── Dockerfile              # Multi-stage build Python + GeoAlchemy + non-root appuser
└── scripts/
    ├── deploy_docker.sh / .bat     # Script triển khai tự động/thủ công
    ├── stop_docker.sh / .bat       # Script dừng hệ thống an toàn
    ├── check_status.sh / .bat      # Script kiểm tra trạng thái 6 container & tài nguyên CPU/RAM
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

## V. KIỂM THỬ TRUY CẬP TỪ MẠNG NỘI BỘ (LAN) & CẤU HÌNH HTTPS

Hệ thống đã được thiết lập hoàn chỉnh giải pháp **HTTPS nội bộ với CA riêng (Internal Certificate Authority)** và **Tên miền cục bộ (`seismicatlas.local`)**. Giải pháp này đảm bảo:
1. **Bảo mật tuyệt đối (100% Free - Không tốn chi phí mua chứng chỉ)**: Dữ liệu tọa độ mỏ, dữ liệu địa chấn SEG-Y, mật khẩu và JWT token được mã hóa an toàn qua TLS 1.3/1.2 trên toàn mạng LAN văn phòng.
2. **Khóa xanh uy tín (Green Padlock - Trusted Connection)**: Trình duyệt Chrome, Edge, Cốc Cốc trên máy tính nhân viên sẽ hiện biểu tượng khóa bảo mật xanh mà không có bất kỳ cảnh báo đỏ nào.
3. **Chuyển hướng tự động (HTTP 301 $\rightarrow$ HTTPS)**: Truy cập `http://seismicatlas.local` hoặc IP máy chủ sẽ tự động chuyển sang `https://seismicatlas.local`.

---

## 1. Tóm tắt các thành phần đã triển khai

| Thành phần | Đường dẫn / Cấu hình | Chi tiết |
| :--- | :--- | :--- |
| **Thư mục Chứng chỉ** | `d:\WebGIS\certs\` | Chứa `rootCA.crt`, `rootCA.key`, `seismicatlas.crt`, `seismicatlas.key` (hạn dùng 10 năm cho CA, 3 năm cho SSL). |
| **Công cụ sinh SSL** | `d:\WebGIS\scripts\generate_ssl_certs.py` | Tự động sinh Root CA và Server Certificate với Subject Alternative Names (SAN) bao gồm `seismicatlas.local`, `*.seismicatlas.local`, `localhost`, `127.0.0.1` và tất cả IP mạng LAN máy chủ. |
| **Cài đặt Root CA 1-Click** | `d:\WebGIS\scripts\install_root_ca.bat` (Win)<br>`d:\WebGIS\scripts\install_root_ca.sh` (Linux) | Tự động thêm Root CA vào Trusted Root Certification Authorities của hệ điều hành. |
| **Cấu hình Domain 1-Click** | `d:\WebGIS\scripts\setup_hosts.bat` (Win)<br>`d:\WebGIS\scripts\setup_hosts.sh` (Linux) | Tự động thêm bản ghi `127.0.0.1 seismicatlas.local` vào file `hosts`. |
| **Nginx Gateway Reverse Proxy** | `d:\WebGIS\frontend\nginx.conf` | Mở cổng 80 (HTTP 301 $\rightarrow$ HTTPS) và cổng 443 (SSL TLS 1.2/1.3, HTTP/2, HSTS, 5 OWASP Security Headers, WSS/WebSocket). |
| **Docker Compose** | `d:\WebGIS\docker-compose.yml` | Ánh xạ cổng `80` và `443`, mount volume `./certs:/etc/nginx/certs:ro` vào container gateway. |
| **Backend Cookie Security** | `backend/data-serving/app/api/routes/auth.py` | Tự động cấu hình `Secure` flag cho Refresh Token cookie tương thích môi trường HTTPS production. |

---

## 2. Hướng Dẫn Sử Dụng Chi Tiết

### Bước 1: Cài đặt Domain và Tin Cậy Root CA trên máy của bạn (Chỉ làm 1 lần)
Mở Command Prompt hoặc PowerShell với quyền **Run as Administrator** tại thư mục dự án và chạy:

1. **Thêm tên miền cục bộ vào file hosts:**
   ```cmd
   scripts\setup_hosts.bat
   ```
2. **Thêm chứng chỉ Root CA vào Windows:**
   ```cmd
   scripts\install_root_ca.bat
   ```
   *(Hệ thống sẽ chạy lệnh `certutil -addstore -f "ROOT" certs\rootCA.crt` và báo thành công)*.

*(Nếu muốn cấu hình cho các máy tính khác trong văn phòng cùng truy cập, xem Mục 3 bên dưới)*.

---

### Bước 2: Khởi động hệ thống với Docker Compose
Chạy lệnh khởi động các container:
```bash
docker-compose up -d --build
```

---

### Bước 3: Truy cập và Kiểm tra
1. Mở trình duyệt (Chrome, Microsoft Edge, Cốc Cốc) và truy cập:
   ```
   https://seismicatlas.local
   ```
2. **Kết quả đạt chuẩn:**
   - Trình duyệt hiển thị biểu tượng **Khóa Bảo Mật (Padlock)**.
   - Nhấp vào biểu tượng khóa $\rightarrow$ Xem chứng chỉ: Được cấp bởi **"SeismicAtlas Internal Root CA"** với trạng thái **"This certificate is valid"**.
   - Mọi API call, GIS Map Tiles, WebSocket (WSS) đều hoạt động trơn tru qua kênh mã hóa HTTPS bảo mật.

---

## 3. Hướng Dẫn Kết Nối Cho Các Máy Khác Trong Mạng LAN Văn Phòng

Khi máy chủ vật lý đặt tại văn phòng (ví dụ có IP LAN là `192.168.1.100`):

1. **Gửi 2 file cho nhân viên / máy trạm:**
   - File `certs/rootCA.crt`
   - File `scripts/install_root_ca.bat`
2. **Trên máy trạm của nhân viên:**
   - Nhấp chuột phải vào `install_root_ca.bat` $\rightarrow$ chọn **Run as Administrator** (hoặc nhấp đúp vào `rootCA.crt` $\rightarrow$ Install Certificate $\rightarrow$ Place in `Trusted Root Certification Authorities`).
   - Mở file `C:\Windows\System32\drivers\etc\hosts` (bằng Notepad Administrator) và thêm dòng:
     ```text
     192.168.1.100    seismicatlas.local
     ```
     *(Hoặc nếu công ty có sẵn Router MikroTik / Pi-hole / Windows Server DNS, chỉ cần thêm 1 bản ghi DNS `seismicatlas.local` trỏ về `192.168.1.100` thì toàn bộ văn phòng tự động nhận diện mà không cần sửa file hosts từng máy)*.
3. Nhân viên chỉ cần mở trình duyệt và gõ `https://seismicatlas.local` để làm việc.

---

## 4. Tái Tạo Chứng Chỉ (Khi Có Thêm IP Mới Hoặc Đổi Tên Miền)
Nếu bạn thay đổi địa chỉ IP máy chủ hoặc muốn bổ sung thêm tên miền phụ:
```cmd
python scripts\generate_ssl_certs.py
```
*(Script sẽ tự động quét lại toàn bộ IP card mạng LAN của máy chủ và tái tạo cặp chứng chỉ mới tương thích)*.

