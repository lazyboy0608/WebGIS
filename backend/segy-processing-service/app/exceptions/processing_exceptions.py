class ProcessingException(Exception):
    """Base exception for processing errors."""


class CoordinateProcessingException(
    ProcessingException
):
    """Coordinate processing failed."""


class LineBuildingException(
    ProcessingException
):
    """Line building failed."""