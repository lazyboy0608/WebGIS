from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)
from app.services.segy_file_service import SegyFileService


def get_segy_file_service() -> SegyFileService:
    session: Session = SessionLocal()

    repository = SQLAlchemySegyFileRepository(
        session
    )

    return SegyFileService(
        repository
    )

def create_segy_file_service(
    session: Session,
) -> SegyFileService:
    repository = SQLAlchemySegyFileRepository(
        session
    )

    return SegyFileService(
        repository
    )