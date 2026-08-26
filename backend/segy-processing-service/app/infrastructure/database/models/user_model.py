from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class UserModel(Base):
    """Minimal mapping of the users table owned by data-serving.

    Registered so SQLAlchemy can resolve segy_files.user_id → users.id.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
