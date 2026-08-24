from dataclasses import dataclass


@dataclass(frozen=True)
class CoordinateReferenceSystem:
    """
    Represents a coordinate reference system used by
    seismic geometry.
    """

    name: str

    authority: str | None = None

    code: int | None = None

    units: str | None = None