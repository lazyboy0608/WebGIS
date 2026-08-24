
from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from app.infrastructure.database.base import Base
from app.infrastructure.database.config import DATABASE_URL

from app.infrastructure.database.models.segy_file_model import (
    SegyFileModel,
)
from app.infrastructure.database.models.seismic_line_model import (
    SeismicLineModel,
)
from app.infrastructure.database.models.seismic_shot_point_model import (
    SeismicShotPointModel,
)
from app.infrastructure.database.models.seismic_trace_model import (
    SeismicTraceModel,
)


# ---------------------------------------------------------
# Alembic configuration
# ---------------------------------------------------------

config = context.config


# ---------------------------------------------------------
# SQLAlchemy metadata
# ---------------------------------------------------------

target_metadata = Base.metadata


# ---------------------------------------------------------
# Database URL
# ---------------------------------------------------------

config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL,
)


# ---------------------------------------------------------
# Offline migration
# ---------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# Online migration
# ---------------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in online mode."""

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if context.is_offline_mode():

    run_migrations_offline()

else:

    run_migrations_online()

