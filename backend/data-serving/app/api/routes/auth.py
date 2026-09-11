import io
import mimetypes
import time
from pathlib import Path
from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate
from app.config import settings
from app.core.rate_limiter import ip_rate_limit
from app.database import get_db_session
from app.infrastructure.storage.minio_client import minio_manager
from app.models import UserModel
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    hash_token,
    verify_password,
    verify_token_hash,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Cookie settings — không dùng HTTPS nên secure=False, samesite='lax'
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": False,      # Đặt True khi deploy lên HTTPS
    "samesite": "lax",    # 'lax' hoạt động với Vite proxy (cùng origin)
}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Đặt cả hai token vào HTTPOnly Cookie."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **COOKIE_SETTINGS,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **COOKIE_SETTINGS,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Xóa cả hai cookie khi logout."""
    response.delete_cookie(key="access_token", **COOKIE_SETTINGS)
    response.delete_cookie(key="refresh_token", **COOKIE_SETTINGS)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    response: Response,
    db: Session = Depends(get_db_session),
    _rl: None = Depends(ip_rate_limit(settings.rate_limit_register, settings.rate_limit_window_seconds)),
):
    """Đăng ký tài khoản người dùng mới."""
    existing_user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng. Vui lòng chọn email khác.",
        )

    hashed_pwd = get_password_hash(user_in.password)
    new_user = UserModel(
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        email=user_in.email,
        date_of_birth=user_in.date_of_birth,
        password_hash=hashed_pwd,
        role="user",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Tạo cặp token
    access_token = create_access_token(
        subject=new_user.id,
        extra_claims={"email": new_user.email, "role": new_user.role, "full_name": new_user.full_name},
    )
    refresh_token = create_refresh_token(subject=new_user.id)

    # Lưu hash refresh token vào DB
    new_user.refresh_token_hash = hash_token(refresh_token)
    db.commit()

    # Đặt cookie vào response
    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        user=UserResponse.model_validate(new_user),
        message="Đăng ký thành công",
    )


@router.post("/login", response_model=TokenResponse)
def login(
    user_in: UserLogin,
    response: Response,
    db: Session = Depends(get_db_session),
    _rl: None = Depends(ip_rate_limit(settings.rate_limit_login, settings.rate_limit_window_seconds)),
):
    """Đăng nhập bằng Email và Password."""
    user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này đã bị tạm khóa. Vui lòng liên hệ quản trị viên.",
        )

    # Tạo cặp token
    access_token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role, "full_name": user.full_name},
    )
    refresh_token = create_refresh_token(subject=user.id)

    # Lưu hash refresh token vào DB (overwrite token cũ)
    user.refresh_token_hash = hash_token(refresh_token)
    db.commit()

    # Đặt cookie vào response
    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        user=UserResponse.model_validate(user),
        message="Đăng nhập thành công",
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db_session),
    _rl: None = Depends(ip_rate_limit(settings.rate_limit_refresh, settings.rate_limit_window_seconds)),
):
    """
    Cấp cặp token mới từ refresh_token cookie.
    Gọi API này khi access_token hết hạn (FE nhận 401).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not refresh_token:
        raise credentials_exception

    payload = decode_refresh_token(refresh_token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    # Kiểm tra refresh token có khớp với hash trong DB không (tránh replay attack)
    if not user.refresh_token_hash or not verify_token_hash(refresh_token, user.refresh_token_hash):
        raise credentials_exception

    # Cấp cặp token mới (rotation)
    new_access_token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role, "full_name": user.full_name},
    )
    new_refresh_token = create_refresh_token(subject=user.id)

    # Cập nhật hash refresh token trong DB
    user.refresh_token_hash = hash_token(new_refresh_token)
    db.commit()

    # Đặt cookie mới
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenResponse(
        user=UserResponse.model_validate(user),
        message="Token đã được làm mới thành công",
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Đăng xuất — xóa cookie và vô hiệu hóa refresh token trong DB."""
    current_user.refresh_token_hash = None
    db.commit()

    _clear_auth_cookies(response)
    return {"message": "Đăng xuất thành công"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    user_in: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Cập nhật thông tin cá nhân (Họ và tên, Số điện thoại, Ngày sinh)."""
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name.strip()
    if user_in.phone_number is not None:
        current_user.phone_number = user_in.phone_number.strip()
    if user_in.date_of_birth is not None:
        current_user.date_of_birth = user_in.date_of_birth

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Tải lên ảnh đại diện, lưu vào MinIO bucket user-avatars và cập nhật avatar_url."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên file không hợp lệ.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ file ảnh định dạng .jpg, .jpeg, .png, .webp, .gif",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dung lượng ảnh đại diện không được vượt quá 10MB.",
        )

    timestamp = int(time.time())
    object_name = f"avatar_user_{current_user.id}_{timestamp}{ext}"
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "image/png"

    # Lưu vào MinIO
    minio_manager.upload_bytes(
        bucket_name=settings.minio_bucket_avatars,
        object_name=object_name,
        data=contents,
        content_type=content_type,
    )

    # Cập nhật avatar_url trong database
    current_user.avatar_url = f"/api/v1/auth/avatar/{object_name}"
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.get("/avatar/{filename}")
def get_avatar(filename: str):
    """Lấy ảnh đại diện từ MinIO và trả về dữ liệu ảnh."""
    clean_filename = Path(filename).name
    try:
        minio_response = minio_manager.client.get_object(
            settings.minio_bucket_avatars,
            clean_filename,
        )
        content_type = mimetypes.guess_type(clean_filename)[0] or "image/png"
        return StreamingResponse(
            io.BytesIO(minio_response.read()),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ảnh đại diện",
        )

