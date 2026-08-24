from dataclasses import dataclass
from enum import Enum

class CoordinateUnit(str, Enum):
    UNKNOWN = "unknown"
    LENGTH = "length"
    SECONDS = "seconds"
    DEGREES = "degrees"

@dataclass(frozen=True)
class Coordinate:
    x: float
    y: float
    units: CoordinateUnit = CoordinateUnit.UNKNOWN