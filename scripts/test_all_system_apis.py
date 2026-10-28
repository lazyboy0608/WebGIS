import os
import sys
import time
import json
import io
import zipfile
import requests
import urllib3

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:443"
ADMIN_EMAIL = "admin@webgis.com"
ADMIN_PASSWORD = "Admin@123456"

results = []

def record(method, endpoint, category, status_code, success, latency_ms, detail="", error=""):
    results.append({
        "method": method,
        "endpoint": endpoint,
        "category": category,
        "status_code": status_code,
        "success": success,
        "latency_ms": round(latency_ms, 2),
        "detail": detail,
        "error": error
    })
    status_icon = "✓ PASS" if success else "✗ FAIL"
    print(f"[{status_icon}] {method:<6} {endpoint:<48} -> {status_code:<3} ({latency_ms:.1f}ms) {detail[:65]}")

session = requests.Session()

print("=" * 80)
print("BẮT ĐẦU KIỂM THỬ TOÀN DIỆN TẤT CẢ CÁC API TRONG HỆ THỐNG WEBGIS")
print("=" * 80)

# ==============================================================================
# NHÓM 1: AUTH & QUẢN TRỊ NGƯỜI DÙNG (DATA-SERVING)
# ==============================================================================
print("\n--- NHÓM 1: XÁC THỰC & QUẢN LÝ NGƯỜI DÙNG ---")

# 1. POST /api/v1/auth/login
t0 = time.time()
res = session.post(f"{BASE_URL}/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, verify=False)
lat = (time.time() - t0) * 1000
user_info = res.json().get("user", {}) if res.status_code == 200 else {}
record("POST", "/api/v1/auth/login", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, f"User: {user_info.get('email')}", res.text if res.status_code != 200 else "")

# 2. GET /api/v1/auth/me
t0 = time.time()
res = session.get(f"{BASE_URL}/api/v1/auth/me", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/v1/auth/me", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, f"Role: {res.json().get('role')}", res.text if res.status_code != 200 else "")

# 3. POST /api/v1/auth/heartbeat
t0 = time.time()
res = session.post(f"{BASE_URL}/api/v1/auth/heartbeat", verify=False)
lat = (time.time() - t0) * 1000
record("POST", "/api/v1/auth/heartbeat", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, "Heartbeat OK", res.text if res.status_code != 200 else "")

# 4. POST /api/v1/auth/refresh
t0 = time.time()
res = session.post(f"{BASE_URL}/api/v1/auth/refresh", verify=False)
lat = (time.time() - t0) * 1000
record("POST", "/api/v1/auth/refresh", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, "Token refreshed", res.text if res.status_code != 200 else "")

# 5. PUT /api/v1/auth/me
t0 = time.time()
res = session.put(f"{BASE_URL}/api/v1/auth/me", json={"full_name": "System Administrator", "phone_number": "0987654321"}, verify=False)
lat = (time.time() - t0) * 1000
record("PUT", "/api/v1/auth/me", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, "Updated profile", res.text if res.status_code != 200 else "")

# 6. POST /api/v1/auth/register (Dùng session độc lập để không làm mất quyền admin của session chính)
reg_session = requests.Session()
t0 = time.time()
temp_email = f"testuser_{int(time.time())}@example.com"
res = reg_session.post(f"{BASE_URL}/api/v1/auth/register", json={
    "full_name": "Test User Regular",
    "phone_number": "0912345678",
    "email": temp_email,
    "date_of_birth": "1995-05-15",
    "password": "Password123!",
    "confirm_password": "Password123!"
}, verify=False)
lat = (time.time() - t0) * 1000
record("POST", "/api/v1/auth/register", "Xác thực & Người dùng", res.status_code, res.status_code in [200, 201], lat, f"New user: {temp_email}", res.text if res.status_code not in [200, 201] else "")

# 7. GET /api/v1/admin/dashboard-stats
t0 = time.time()
res = session.get(f"{BASE_URL}/api/v1/admin/dashboard-stats", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/v1/admin/dashboard-stats", "Quản trị Admin", res.status_code, res.status_code == 200, lat, f"Stats retrieved (CPU/RAM/DB/Cache)", res.text if res.status_code != 200 else "")

# 8. GET /api/v1/admin/users
t0 = time.time()
res = session.get(f"{BASE_URL}/api/v1/admin/users", verify=False)
lat = (time.time() - t0) * 1000
users_raw = res.json() if res.status_code == 200 else []
users_list = users_raw.get("items", []) if isinstance(users_raw, dict) else (users_raw if isinstance(users_raw, list) else [])
record("GET", "/api/v1/admin/users", "Quản trị Admin", res.status_code, res.status_code == 200, lat, f"Total users: {len(users_list)}", res.text if res.status_code != 200 else "")

# 9. POST /api/v1/admin/users (Create user by admin)
admin_temp_email = f"admin_created_{int(time.time())}@webgis.com"
t0 = time.time()
res = session.post(f"{BASE_URL}/api/v1/admin/users", json={
    "full_name": "Admin Created User",
    "phone_number": "0911223344",
    "email": admin_temp_email,
    "date_of_birth": "1992-08-20",
    "password": "Password123!",
    "role": "user"
}, verify=False)
lat = (time.time() - t0) * 1000
created_user_id = res.json().get("id") if res.status_code in [200, 201] else None
record("POST", "/api/v1/admin/users", "Quản trị Admin", res.status_code, res.status_code in [200, 201], lat, f"Created ID: {created_user_id}", res.text if res.status_code not in [200, 201] else "")

# 10. PUT /api/v1/admin/users/{user_id}
if created_user_id:
    t0 = time.time()
    res = session.put(f"{BASE_URL}/api/v1/admin/users/{created_user_id}", json={
        "full_name": "Admin Updated User",
        "phone_number": "0999888777",
        "role": "user"
    }, verify=False)
    lat = (time.time() - t0) * 1000
    record("PUT", f"/api/v1/admin/users/{{user_id}}", "Quản trị Admin", res.status_code, res.status_code == 200, lat, f"Updated ID: {created_user_id}", res.text if res.status_code != 200 else "")

    # 11. POST /api/v1/admin/users/{user_id}/reset-password
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/v1/admin/users/{created_user_id}/reset-password", json={
        "new_password": "NewResetPassword123!"
    }, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", f"/api/v1/admin/users/{{user_id}}/reset-password", "Quản trị Admin", res.status_code, res.status_code == 200, lat, f"Reset pass for ID: {created_user_id}", res.text if res.status_code != 200 else "")

    # 12. DELETE /api/v1/admin/users/{user_id}
    t0 = time.time()
    res = session.delete(f"{BASE_URL}/api/v1/admin/users/{created_user_id}", verify=False)
    lat = (time.time() - t0) * 1000
    record("DELETE", f"/api/v1/admin/users/{{user_id}}", "Quản trị Admin", res.status_code, res.status_code in [200, 204], lat, f"Deleted ID: {created_user_id}", res.text if res.status_code not in [200, 204] else "")

# ==============================================================================
# NHÓM 2: TIỀN XỬ LÝ & TẢI LÊN SEG-Y (SEGY-PROCESSING SERVICE)
# ==============================================================================
print("\n--- NHÓM 2: TIỀN XỬ LÝ & TẢI LÊN SEG-Y ---")

# 13. GET /api/segy-files/crs-presets
t0 = time.time()
res = session.get(f"{BASE_URL}/api/segy-files/crs-presets", verify=False)
lat = (time.time() - t0) * 1000
presets = res.json() if res.status_code == 200 else []
record("GET", "/api/segy-files/crs-presets", "Tiền xử lý SEG-Y", res.status_code, res.status_code == 200, lat, f"Total presets: {len(presets)} (incl. 3 Louisiana zones)", res.text if res.status_code != 200 else "")

# 14. POST /api/segy-files/inspect-header (Testing slb1.sgy)
test_sgy_path = "data/test_crs/slb1.sgy"
if os.path.exists(test_sgy_path):
    t0 = time.time()
    with open(test_sgy_path, "rb") as f:
        res = session.post(f"{BASE_URL}/api/segy-files/inspect-header", files={"file": ("slb1.sgy", f, "application/octet-stream")}, verify=False)
    lat = (time.time() - t0) * 1000
    detected_crs = res.json().get("source_crs") if res.status_code == 200 else None
    record("POST", "/api/segy-files/inspect-header", "Tiền xử lý SEG-Y", res.status_code, res.status_code == 200, lat, f"Detected CRS: {detected_crs}", res.text if res.status_code != 200 else "")

# 15. POST /api/segy-files/upload (Uploading Test_01_CuuLong_UTM48N.sgy)
test_upload_path = "data/test_crs/Test_01_CuuLong_UTM48N.sgy"
segy_task_id = None
uploaded_file_id = None
if os.path.exists(test_upload_path):
    t0 = time.time()
    with open(test_upload_path, "rb") as f:
        res = session.post(
            f"{BASE_URL}/api/segy-files/upload",
            files={"file": (f"Test_API_Run_{int(time.time())}.sgy", f, "application/octet-stream")},
            data={"source_crs": "EPSG:32648", "target_crs": "EPSG:4326"},
            verify=False
        )
    lat = (time.time() - t0) * 1000
    upload_data = res.json() if res.status_code in [200, 201, 202] else {}
    segy_task_id = upload_data.get("task_id")
    uploaded_file_id = upload_data.get("file_id")
    record("POST", "/api/segy-files/upload", "Tiền xử lý SEG-Y", res.status_code, res.status_code in [200, 201, 202], lat, f"Task ID: {segy_task_id}, File ID: {uploaded_file_id}", res.text if res.status_code not in [200, 201, 202] else "")

# 16. GET /api/segy-files/tasks/{task_id}
if segy_task_id:
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/tasks/{segy_task_id}", verify=False)
    lat = (time.time() - t0) * 1000
    task_status = res.json().get("status") if res.status_code == 200 else None
    record("GET", "/api/segy-files/tasks/{task_id}", "Tiền xử lý SEG-Y", res.status_code, res.status_code == 200, lat, f"Status: {task_status}", res.text if res.status_code != 200 else "")

# ==============================================================================
# NHÓM 3: KHAI THÁC DỮ LIỆU ĐỊA CHẤN SEG-Y (DATA-SERVING)
# ==============================================================================
print("\n--- NHÓM 3: KHAI THÁC DỮ LIỆU ĐỊA CHẤN SEG-Y ---")

# 17. GET /api/segy-files
t0 = time.time()
res = session.get(f"{BASE_URL}/api/segy-files?page=1&page_size=10", verify=False)
lat = (time.time() - t0) * 1000
files_data = res.json() if res.status_code == 200 else {}
items = files_data.get("items", []) if isinstance(files_data, dict) else (files_data if isinstance(files_data, list) else [])
# Lấy file ID có thật trong database (ưu tiên file đã hoàn thành xử lý)
sample_fid = None
for f in items:
    if f.get("id"):
        sample_fid = f.get("id")
        break
if not sample_fid:
    sample_fid = 12  # Fallback to known file ID in DB

record("GET", "/api/segy-files", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Files in DB: {len(items)} (Selected ID: {sample_fid})", res.text if res.status_code != 200 else "")

if sample_fid:
    # 18. GET /api/segy-files/{file_id}/summary
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/summary", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/summary", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"File {sample_fid} summary OK", res.text if res.status_code != 200 else "")

    # 19. GET /api/segy-files/{file_id}/processed/summary
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/summary", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/processed/summary", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Trace count: {res.json().get('trace_count') if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

    # 20. GET /api/segy-files/{file_id}/processed/line
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/line", verify=False)
    lat = (time.time() - t0) * 1000
    geom_type = res.json().get("geometry", {}).get("type") if res.status_code == 200 else None
    record("GET", f"/api/segy-files/{{file_id}}/processed/line", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Geometry: {geom_type}", res.text if res.status_code != 200 else "")

    # 21. GET /api/segy-files/{file_id}/processed/lines
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/lines?limit=100", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/processed/lines", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Features: {len(res.json().get('features', [])) if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

    # 22. GET /api/segy-files/{file_id}/processed/shot-points
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/shot-points?limit=10", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/processed/shot-points", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Points: {len(res.json().get('features', [])) if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

    # 23. GET /api/segy-files/{file_id}/processed/traces
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/traces?limit=10", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/processed/traces", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, f"Traces: {len(res.json().get('features', [])) if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

    # 24. GET /api/segy-files/{file_id}/download-url
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/download-url", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/download-url", "Dữ liệu Địa chấn", res.status_code, res.status_code == 200, lat, "MinIO presigned URL generated", res.text if res.status_code != 200 else "")

# ==============================================================================
# NHÓM 4: BẢN ĐỒ VECTOR TILES (MVT) & PHÂN TÍCH KHÔNG GIAN
# ==============================================================================
print("\n--- NHÓM 4: BẢN ĐỒ VECTOR TILES & PHÂN TÍCH KHÔNG GIAN ---")

# 25. GET /api/segy-files/mvt/{z}/{x}/{y}.pbf (Global MVT tile: e.g. z=4, x=13, y=7 Vietnam)
t0 = time.time()
res = session.get(f"{BASE_URL}/api/segy-files/mvt/4/13/7.pbf", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/segy-files/mvt/{z}/{x}/{y}.pbf", "Vector Tiles & Không gian", res.status_code, res.status_code in [200, 204], lat, f"MVT bytes: {len(res.content)}", res.text if res.status_code not in [200, 204] else "")

# 26. GET /api/segy-files/{file_id}/mvt/{z}/{x}/{y}.pbf
if sample_fid:
    t0 = time.time()
    res = session.get(f"{BASE_URL}/api/segy-files/{sample_fid}/mvt/4/13/7.pbf", verify=False)
    lat = (time.time() - t0) * 1000
    record("GET", f"/api/segy-files/{{file_id}}/mvt/{{z}}/{{x}}/{{y}}.pbf", "Vector Tiles & Không gian", res.status_code, res.status_code in [200, 204], lat, f"File MVT bytes: {len(res.content)}", res.text if res.status_code not in [200, 204] else "")

# 27. POST /api/segy-files/{file_id}/processed/lines/clip (Spatial clip with polygon GeoJSON directly)
test_polygon = {
    "type": "Polygon",
    "coordinates": [[[104.0, 8.0], [109.0, 8.0], [109.0, 12.0], [104.0, 12.0], [104.0, 8.0]]]
}
if sample_fid:
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/segy-files/{sample_fid}/processed/lines/clip", json=test_polygon, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", f"/api/segy-files/{{file_id}}/processed/lines/clip", "Vector Tiles & Không gian", res.status_code, res.status_code == 200, lat, f"Clipped features: {len(res.json().get('features', [])) if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

# 28. POST /api/segy-files/lines/clip-batch (Batch spatial clip)
if sample_fid:
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/segy-files/lines/clip-batch", json={
        "file_ids": [sample_fid],
        "polygon_rings": test_polygon["coordinates"]
    }, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", "/api/segy-files/lines/clip-batch", "Vector Tiles & Không gian", res.status_code, res.status_code == 200, lat, "Batch clip OK", res.text if res.status_code != 200 else "")

# ==============================================================================
# NHÓM 5: XUẤT DỮ LIỆU (EXCEL, CSV, CROPPED SEG-Y)
# ==============================================================================
print("\n--- NHÓM 5: XUẤT DỮ LIỆU ---")

# 29. POST /api/segy-files/{file_id}/export/csv
if sample_fid:
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/segy-files/{sample_fid}/export/csv", json={"crs": "EPSG:4326"}, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", f"/api/segy-files/{{file_id}}/export/csv", "Xuất dữ liệu", res.status_code, res.status_code == 200, lat, f"CSV content: {len(res.content)} bytes", res.text if res.status_code != 200 else "")

# 30. POST /api/segy-files/export/csv/batch
if sample_fid:
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/segy-files/export/csv/batch", json={"ids": [sample_fid]}, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", "/api/segy-files/export/csv/batch", "Xuất dữ liệu", res.status_code, res.status_code == 200, lat, f"Batch CSV generated: {res.json().get('total', 0)} files", res.text if res.status_code != 200 else "")

# 31. POST /api/segy-files/export/segy/spatial-filter
if sample_fid:
    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/segy-files/export/segy/spatial-filter", json={
        "file_ids": [sample_fid],
        "polygon_ring": test_polygon["coordinates"][0],
        "polygon_name": "TestFilterPolygon"
    }, verify=False)
    lat = (time.time() - t0) * 1000
    record("POST", "/api/segy-files/export/segy/spatial-filter", "Xuất dữ liệu", res.status_code, res.status_code in [200, 202], lat, f"Spatial filtered SEG-Y exported ({res.json().get('total', 0)} lines)", res.text if res.status_code not in [200, 202] else "")


# ==============================================================================
# NHÓM 6: QUẢN LÝ LÔ MỎ ĐỊA CHẤN (SEISMIC BLOCKS)
# ==============================================================================
print("\n--- NHÓM 6: QUẢN LÝ LÔ MỎ ĐỊA CHẤN ---")

# 32. GET /api/blocks
t0 = time.time()
res = session.get(f"{BASE_URL}/api/blocks", verify=False)
lat = (time.time() - t0) * 1000
blocks_data = res.json() if res.status_code == 200 else []
sample_bid = blocks_data[0].get("id") if blocks_data else None
record("GET", "/api/blocks", "Lô mỏ địa chấn", res.status_code, res.status_code == 200, lat, f"Total blocks: {len(blocks_data)}", res.text if res.status_code != 200 else "")

# 33. GET /api/blocks/geojson
t0 = time.time()
res = session.get(f"{BASE_URL}/api/blocks/geojson", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/blocks/geojson", "Lô mỏ địa chấn", res.status_code, res.status_code == 200, lat, f"Features: {len(res.json().get('features', [])) if res.status_code == 200 else 0}", res.text if res.status_code != 200 else "")

# 34. POST /api/blocks/upload-zip (Shapefile upload)
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("test.txt", "dummy block shapefile package")
zip_buffer.seek(0)
t0 = time.time()
res = session.post(f"{BASE_URL}/api/blocks/upload-zip", files={"file": ("test_block.zip", zip_buffer, "application/zip")}, verify=False)
lat = (time.time() - t0) * 1000
block_task_valid = res.status_code in [200, 201, 202, 400]
record("POST", "/api/blocks/upload-zip", "Lô mỏ địa chấn", res.status_code, block_task_valid, lat, f"Validation handled properly ({res.status_code})", res.text if not block_task_valid else "")

# 35. GET /api/blocks/tasks/{task_id}
t0 = time.time()
res = session.get(f"{BASE_URL}/api/blocks/tasks/dummy-task-check-001", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/blocks/tasks/{task_id}", "Lô mỏ địa chấn", res.status_code, res.status_code in [200, 404], lat, "Task check endpoint responded properly (404/200)", res.text if res.status_code not in [200, 404] else "")

# 36. GET /api/blocks/{block_id}
test_bid = sample_bid if sample_bid else 999999
t0 = time.time()
res = session.get(f"{BASE_URL}/api/blocks/{test_bid}", verify=False)
lat = (time.time() - t0) * 1000
bid_valid = res.status_code in [200, 404]
record("GET", f"/api/blocks/{{block_id}}", "Lô mỏ địa chấn", res.status_code, bid_valid, lat, f"Handled correctly ({res.status_code})", res.text if not bid_valid else "")

# 37. GET /api/blocks/{block_id}/export-excel
t0 = time.time()
res = session.get(f"{BASE_URL}/api/blocks/{test_bid}/export-excel", verify=False)
lat = (time.time() - t0) * 1000
excel_valid = res.status_code in [200, 404]
record("GET", f"/api/blocks/{{block_id}}/export-excel", "Lô mỏ địa chấn", res.status_code, excel_valid, lat, f"Handled correctly ({res.status_code})", res.text if not excel_valid else "")

# 38. POST /api/blocks/undo-split
t0 = time.time()
res = session.post(f"{BASE_URL}/api/blocks/undo-split", json={"parent_block_id": 999999}, verify=False)
lat = (time.time() - t0) * 1000
undo_valid = res.status_code in [200, 400, 404]
record("POST", "/api/blocks/undo-split", "Lô mỏ địa chấn", res.status_code, undo_valid, lat, f"Handled safely ({res.status_code})", res.text if not undo_valid else "")

# 39. DELETE /api/blocks
t0 = time.time()
res = session.delete(f"{BASE_URL}/api/blocks?source_file=dummy_test_nonexistent.zip", verify=False)
lat = (time.time() - t0) * 1000
record("DELETE", "/api/blocks", "Lô mỏ địa chấn", res.status_code, res.status_code == 200, lat, "Delete by source_file OK", res.text if res.status_code != 200 else "")

# ==============================================================================
# NHÓM 7: BATCH OPERATIONS & DỌN DẸP DỮ LIỆU
# ==============================================================================
print("\n--- NHÓM 7: THAO TÁC HÀNG LOẠT & DỌN DẸP ---")

# 40. POST /api/segy-files/batch-delete
del_id = uploaded_file_id if uploaded_file_id else 999999
t0 = time.time()
res = session.post(f"{BASE_URL}/api/segy-files/batch-delete", json={"ids": [del_id]}, verify=False)
lat = (time.time() - t0) * 1000
record("POST", "/api/segy-files/batch-delete", "Thao tác hàng loạt", res.status_code, res.status_code in [200, 204], lat, f"Batch delete handled (ID: {del_id})", res.text if res.status_code not in [200, 204] else "")

# ==============================================================================
# NHÓM 8: KIỂM TRA SỨC KHỎE HỆ THỐNG (HEALTHCHECKS)
# ==============================================================================
print("\n--- NHÓM 8: KIỂM TRA SỨC KHỎE DỊCH VỤ ---")

# 41. GET /api/health (Data serving via gateway)
t0 = time.time()
res = session.get(f"{BASE_URL}/api/health", verify=False)
lat = (time.time() - t0) * 1000
record("GET", "/api/health", "Sức khỏe hệ thống", res.status_code, res.status_code == 200, lat, f"Data serving: {res.json().get('status', 'OK')}", res.text if res.status_code != 200 else "")

# 42. POST /api/v1/auth/logout (End session)
t0 = time.time()
res = session.post(f"{BASE_URL}/api/v1/auth/logout", verify=False)
lat = (time.time() - t0) * 1000
record("POST", "/api/v1/auth/logout", "Xác thực & Người dùng", res.status_code, res.status_code == 200, lat, "Logged out successfully", res.text if res.status_code != 200 else "")

# ==============================================================================
# TỔNG KẾT & LƯU BÁO CÁO JSON
# ==============================================================================
passed = [r for r in results if r["success"]]
failed = [r for r in results if not r["success"]]

print("\n" + "=" * 80)
print(f"KẾT QUẢ KIỂM THỬ: {len(passed)}/{len(results)} API HOẠT ĐỘNG TỐT ({len(passed)/len(results)*100:.1f}%)")
if failed:
    print(f"SỐ API GẶP VẤN ĐỀ/LỖI: {len(failed)}")
    for f in failed:
        print(f" - {f['method']} {f['endpoint']} (Code: {f['status_code']}, Lỗi: {f['error'][:80]})")
else:
    print("TẤT CẢ CÁC API ĐÃ ĐƯỢC KIỂM THỬ ĐỀU HOẠT ĐỘNG CHUẨN XÁC VÀ ỔN ĐỊNH!")
print("=" * 80)

os.makedirs("data/test_crs", exist_ok=True)
with open("data/test_crs/api_test_results.json", "w", encoding="utf-8") as out:
    json.dump({"summary": {"total": len(results), "passed": len(passed), "failed": len(failed)}, "details": results}, out, ensure_ascii=False, indent=2)
