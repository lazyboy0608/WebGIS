import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def validate_password_complexity(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
    if not re.search(r'[A-Z]', v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ hoa (A-Z)")
    if not re.search(r'[a-z]', v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ thường (a-z)")
    if not re.search(r'\d', v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số (0-9)")
    if not re.search(r'[@$!%*?&#^()_+\-=\[\]{};\':"\\|,.<>\/?~`]', v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (ví dụ: @, $, !, %, *, ?, &, #...)")
    return v


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Họ và tên")
    phone_number: str = Field(..., min_length=8, max_length=50, description="Số điện thoại")
    email: EmailStr = Field(..., description="Email")
    date_of_birth: date = Field(..., description="Ngày sinh (YYYY-MM-DD)")
    password: str = Field(..., min_length=8, max_length=128, description="Mật khẩu")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Xác nhận mật khẩu")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return self



class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email đăng nhập")
    password: str = Field(..., description="Mật khẩu")
    remember_me: bool = Field(False, description="Ghi nhớ đăng nhập (Persistent Cookie)")


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: EmailStr
    date_of_birth: date
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Họ và tên")
    phone_number: Optional[str] = Field(None, min_length=8, max_length=50, description="Số điện thoại")
    date_of_birth: Optional[date] = Field(None, description="Ngày sinh (YYYY-MM-DD)")


class TokenResponse(BaseModel):
    """
    Response body khi login/register thành công.
    Token được đặt vào HTTPOnly Cookie, không trả về trong body.
    """
    user: UserResponse
    message: str = "Đăng nhập thành công"
