from enum import StrEnum


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    READING = "reading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"