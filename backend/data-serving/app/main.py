import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func

from app.config import settings
from app.database import SessionLocal
from app.models import UserModel
from app.services.security import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.block import router as block_router
from app.api.routes.health import router as health_router
from app.api.routes.mvt import router as mvt_router
from app.api.routes.processed_data import router as processed_data_router


def seed_default_admin():
    """Tự động kiểm tra và khởi tạo tài khoản Admin mặc định khi chạy Web Server / Container."""
    db = SessionLocal()
    try:
        admin_count = db.query(func.count(UserModel.id)).filter(UserModel.role == "admin").scalar() or 0
        if admin_count == 0:
            logger.info("Chưa có tài khoản Admin nào. Đang tự động khởi tạo tài khoản Admin mặc định...")
            admin_user = UserModel(
                full_name=settings.default_admin_fullname,
                phone_number=settings.default_admin_phone,
                email=settings.default_admin_email.lower().strip(),
                date_of_birth=date(1990, 1, 1),
                password_hash=get_password_hash(settings.default_admin_password),
                role="admin",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"==> Đã khởi tạo Admin thành công: {settings.default_admin_email}")
        else:
            logger.info(f"Hệ thống đã có {admin_count} tài khoản Admin sẵn sàng.")
    except Exception as e:
        logger.warning(f"Không thể kiểm tra/khởi tạo Admin mặc định: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Khởi tạo dữ liệu ban đầu
    seed_default_admin()
    yield
    # Shutdown logic if any


app = FastAPI(
    title="Data Serving Service",
    version="0.1.0",
    description="Read-only API for serving processed seismic data from PostgreSQL/PostGIS.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(processed_data_router)
app.include_router(auth_router)
app.include_router(block_router)
app.include_router(mvt_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)

