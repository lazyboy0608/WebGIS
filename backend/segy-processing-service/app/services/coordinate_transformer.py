from app.domain.models.coordinate import (
    Coordinate,
    CoordinateUnit,
)


class CoordinateTransformer:
    """
    Normalize SEG-Y coordinate values using
    the SEG-Y coordinate scalar and coordinate units.
    """

    def transform(
        self,
        x: float,
        y: float,
        scalar: int,
        coordinate_units: int,
    ) -> Coordinate:

        x_value = float(x)
        y_value = float(y)

        if scalar > 1:
            x_value *= scalar
            y_value *= scalar

        elif scalar < 0:
            divisor = abs(scalar)

            x_value /= divisor
            y_value /= divisor

        unit = self._resolve_units(
            coordinate_units
        )

        return Coordinate(
            x=x_value,
            y=y_value,
            units=unit,
        )

    def _resolve_units(
        self,
        coordinate_units: int,
    ) -> CoordinateUnit:

        if coordinate_units == 1:
            return CoordinateUnit.LENGTH

        if coordinate_units == 2:
            return CoordinateUnit.DEGREES

        return CoordinateUnit.UNKNOWN