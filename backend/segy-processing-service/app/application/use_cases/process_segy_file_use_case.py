from app.application.services.processing_persistence import (
    ProcessingResultPersistenceService,
)
from app.application.services.segy_processing import (
    SegyProcessingService,
)
from app.domain.models.processed_segy_data import (
    ProcessedSegyData,
)


class ProcessSegyFileUseCase:
    """
    Application use case for processing a SEG-Y file
    and persisting the resulting data.

    This use case coordinates application services but does
    not contain SEG-Y processing logic or database-specific
    persistence logic.
    """

    def __init__(
        self,
        processing_service: SegyProcessingService,
        persistence_service: ProcessingResultPersistenceService,
    ) -> None:
        self._processing_service = processing_service
        self._persistence_service = persistence_service

    def execute(
        self,
        filename: str,
        segy_file_id: int,
        source_crs: str | None = None,
    ) -> ProcessedSegyData:
        """
        Process a SEG-Y file and persist its processing result.

        Execution order:

        1. Resolve and process the SEG-Y file.
        2. Persist the resulting application-level data.
        3. Return the processed result.

        If processing fails, persistence is not executed.

        If persistence fails, the persistence exception is
        propagated to the caller.
        """

        if source_crs is None:
            processed_data = self._processing_service.process_file(filename)
        else:
            processed_data = self._processing_service.process_file(
                filename,
                source_crs=source_crs,
            )

        self._persistence_service.persist(
            processed_data,
            segy_file_id,
        )

        return processed_data
