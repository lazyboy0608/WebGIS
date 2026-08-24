class SegyException(Exception):
    """Base exception for SEG-Y processing."""


class InvalidSegyFileException(SegyException):
    """SEG-Y file is invalid."""


class SegyReadException(SegyException):
    """SEG-Y file cannot be read."""


class UnsupportedSegyFormatException(SegyException):
    """SEG-Y format is not supported."""