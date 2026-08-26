from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Họ và tên")
    phone_number: str = Field(..., min_length=8, max_length=50, description="Số điện thoại")
    email: EmailStr = Field(..., description="Email")
    date_of_birth: date = Field(..., description="Ngày sinh (YYYY-MM-DD)")
    password: str = Field(..., min_length=6, max_length=128, description="Mật khẩu")
    confirm_password: str = Field(..., min_length=6, max_length=128, description="Xác nhận mật khẩu")

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return self


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: EmailStr
    date_of_birth: date
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """
    Response body khi login/register thành công.
    Token được đặt vào HTTPOnly Cookie, không trả về trong body.
    """
    user: UserResponse
    message: str = "Đăng nhập thành công"
