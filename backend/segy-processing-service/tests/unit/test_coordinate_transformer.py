import pytest

from app.domain.models.coordinate import (
    CoordinateUnit,
)
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)


@pytest.fixture
def transformer() -> CoordinateTransformer:
    return CoordinateTransformer()


def test_scalar_one_keeps_coordinate(
    transformer: CoordinateTransformer,
) -> None:

    coordinate = transformer.transform(
        x=1610154,
        y=-191584,
        scalar=1,
        coordinate_units=0,
    )

    assert coordinate.x == 1610154
    assert coordinate.y == -191584

    assert (
        coordinate.units
        == CoordinateUnit.UNKNOWN
    )


def test_positive_scalar(
    transformer: CoordinateTransformer,
) -> None:

    coordinate = transformer.transform(
        x=100,
        y=200,
        scalar=10,
        coordinate_units=0,
    )

    assert coordinate.x == 1000
    assert coordinate.y == 2000


def test_negative_scalar(
    transformer: CoordinateTransformer,
) -> None:

    coordinate = transformer.transform(
        x=1000,
        y=2000,
        scalar=-10,
        coordinate_units=0,
    )

    assert coordinate.x == 100
    assert coordinate.y == 200


def test_zero_scalar_does_not_modify_value(
    transformer: CoordinateTransformer,
) -> None:

    coordinate = transformer.transform(
        x=100,
        y=200,
        scalar=0,
        coordinate_units=0,
    )

    assert coordinate.x == 100
    assert coordinate.y == 200


def test_unknown_coordinate_units(
    transformer: CoordinateTransformer,
) -> None:

    coordinate = transformer.transform(
        x=100,
        y=200,
        scalar=1,
        coordinate_units=0,
    )

    assert (
        coordinate.units
        == CoordinateUnit.UNKNOWN
    )