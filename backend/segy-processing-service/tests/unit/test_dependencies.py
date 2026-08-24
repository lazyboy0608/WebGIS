from unittest.mock import ( 
    MagicMock,
    patch,
)
# from app.dependencies import create_segy_file_service
from app.api.dependencies import (
    get_segy_file_service,
    get_segy_file_repository,
    get_db_session,
)
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)
from app.services.segy_file_service import SegyFileService


# def test_create_segy_file_service_injects_repository():
#     session = MagicMock()

#     service = create_segy_file_service(session)

#     assert isinstance(service, SegyFileService)

#     assert isinstance(
#         service.repository,
#         SQLAlchemySegyFileRepository,
#     )

#     assert service.repository.session is session

def test_get_segy_file_repository():
    session = MagicMock()

    repository = get_segy_file_repository(session)

    assert isinstance(repository, SQLAlchemySegyFileRepository)
    assert repository.session is session


def test_get_segy_file_service():
    repository = MagicMock(spec=SQLAlchemySegyFileRepository)

    service = get_segy_file_service(repository)

    assert isinstance(service, SegyFileService)
    assert service.repository is repository

def test_get_db_session_closes_session():
    session = MagicMock()

    with patch(
        "app.api.dependencies.SessionLocal",
        return_value=session,
    ):
        generator = get_db_session()

        yielded_session = next(generator)

        assert yielded_session is session

        try:
            next(generator)
        except StopIteration:
            pass

        session.close.assert_called_once()