from sqlalchemy import text

from app.infrastructure.database.session import engine


def test_database_connection() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        assert result.scalar() == 1

def test_postgis_extension() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT PostGIS_Full_Version()")
        )

        version = result.scalar()

        assert version is not None
        assert "POSTGIS=" in version