from pathlib import Path

import pytest

from app.exceptions.segy_exceptions import (
    InvalidSegyFileException,
)
from app.services.segy_validator import (
    SegyValidator,
)


def test_validate_non_existing_file() -> None:

    validator = SegyValidator()

    with pytest.raises(
        InvalidSegyFileException
    ):
        validator.validate(
            Path("not-exist.sgy")
        )