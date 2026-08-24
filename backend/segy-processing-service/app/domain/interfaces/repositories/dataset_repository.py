from abc import ABC, abstractmethod

from app.domain.models.segy_metadata import (
    SegyMetadata,
)


class DatasetRepository(ABC):

    @abstractmethod
    def save_metadata(
        self,
        metadata: SegyMetadata,
    ) -> None:
        raise NotImplementedError