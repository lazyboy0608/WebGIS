from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.database import get_db_session
from app.models import UserModel
from app.services.security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db_session)):
    """Đăng ký tài khoản người dùng mới."""
    # Check if email is already registered
    existing_user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng. Vui lòng chọn email khác.",
        )

    # Hash password and create user
    hashed_pwd = get_password_hash(user_in.password)
    new_user = UserModel(
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        email=user_in.email,
        date_of_birth=user_in.date_of_birth,
        password_hash=hashed_pwd,
        role="user",  # Default role
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate access token
    access_token = create_access_token(
        subject=new_user.id,
        extra_claims={"email": new_user.email, "role": new_user.role, "full_name": new_user.full_name},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db_session)):
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

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role, "full_name": user.full_name},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập."""
    return UserResponse.model_validate(current_user)
