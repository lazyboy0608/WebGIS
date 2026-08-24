from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.trace import Trace


class SegyReader(ABC):

    @abstractmethod
    def read_metadata(
        self,
        file_path: Path,
    ) -> SegyMetadata:
        raise NotImplementedError

    @abstractmethod
    def iter_traces(
        self,
        file_path: Path,
        include_samples: bool = False,
    ) -> Iterator[Trace]:
        raise NotImplementedError