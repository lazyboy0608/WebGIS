from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class AdminDashboardStats(BaseModel):
    total_users: int = Field(..., description="Tổng số người dùng")
    active_users: int = Field(..., description="Số người dùng đang hoạt động")
    admin_users: int = Field(..., description="Số lượng quản trị viên")
    cpu_usage_percent: float = Field(..., description="Mức sử dụng CPU (%)")
    cpu_cores: int = Field(..., description="Số nhân CPU")
    ram_usage_percent: float = Field(..., description="Mức sử dụng RAM (%)")
    ram_used_gb: float = Field(..., description="RAM đã sử dụng (GB)")
    ram_total_gb: float = Field(..., description="Tổng dung lượng RAM (GB)")
    disk_usage_percent: float = Field(..., description="Mức sử dụng Ổ đĩa (%)")
    disk_used_gb: float = Field(..., description="Dung lượng Ổ đĩa đã sử dụng (GB)")
    disk_total_gb: float = Field(..., description="Tổng dung lượng Ổ đĩa (GB)")
    active_sessions: int = Field(..., description="Số lượng phiên truy cập thời gian thực")
    cache_hit_ratio: float = Field(..., description="Tỷ lệ Cache Hit của Redis (%)")
    database_status: str = Field(..., description="Trạng thái kết nối PostGIS")
    user_growth: List[Dict[str, Any]] = Field(default_factory=list, description="Dữ liệu tăng trưởng người dùng theo ngày")
    role_distribution: Dict[str, int] = Field(default_factory=dict, description="Phân bổ theo vai trò")
    status_distribution: Dict[str, int] = Field(default_factory=dict, description="Phân bổ theo trạng thái kích hoạt")


class AdminUserItem(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: str
    date_of_birth: date
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    segy_files_count: int = 0

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., min_length=8, max_length=20)
    email: EmailStr
    date_of_birth: date
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(user|admin)$")
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=8, max_length=20)
    date_of_birth: Optional[date] = None
    role: Optional[str] = Field(None, pattern="^(user|admin)$")
    is_active: Optional[bool] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: Optional[str] = Field(None, min_length=6, description="Mật khẩu mới (Nếu để trống hệ thống sẽ cấp mật khẩu tạm WebGIS@2026)")
