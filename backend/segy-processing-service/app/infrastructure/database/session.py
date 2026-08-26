from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.config import DATABASE_URL
from app.infrastructure.database.models import UserModel  # noqa: F401


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)