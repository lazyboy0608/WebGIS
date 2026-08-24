from unittest.mock import Mock

import pytest

from app.domain.models.processed_segy_data import (
    ProcessedSegyData,
)
from app.application.use_cases.process_segy_file_use_case import (
    ProcessSegyFileUseCase,
)


def create_processed_data() -> ProcessedSegyData:
    return Mock(spec=ProcessedSegyData)


def create_use_case():
    processing_service = Mock()
    persistence_service = Mock()

    use_case = ProcessSegyFileUseCase(
        processing_service=processing_service,
        persistence_service=persistence_service,
    )

    return (
        use_case,
        processing_service,
        persistence_service,
    )


def test_execute_processes_file_and_persists_result():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processed_data = create_processed_data()

    processing_service.process_file.return_value = (
        processed_data
    )

    result = use_case.execute(
        filename="slb1.sgy",
        segy_file_id=7,
    )

    processing_service.process_file.assert_called_once_with(
        "slb1.sgy",
    )

    persistence_service.persist.assert_called_once_with(
        processed_data,
        7,
    )

    assert result is processed_data


def test_execute_persists_the_exact_processing_result():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processed_data = create_processed_data()

    processing_service.process_file.return_value = (
        processed_data
    )

    use_case.execute(
        filename="slb1.sgy",
        segy_file_id=42,
    )

    persisted_data = (
        persistence_service.persist.call_args.args[0]
    )

    assert persisted_data is processed_data


def test_execute_passes_correct_segy_file_id_to_persistence():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processed_data = create_processed_data()

    processing_service.process_file.return_value = (
        processed_data
    )

    use_case.execute(
        filename="slb1.sgy",
        segy_file_id=123,
    )

    persisted_file_id = (
        persistence_service.persist.call_args.args[1]
    )

    assert persisted_file_id == 123


def test_execute_processes_before_persisting():
    calls = []

    processing_service = Mock()
    persistence_service = Mock()

    processed_data = create_processed_data()

    def process_file(filename):
        calls.append(
            "process"
        )
        return processed_data

    def persist(data, segy_file_id):
        calls.append(
            "persist"
        )

    processing_service.process_file.side_effect = (
        process_file
    )

    persistence_service.persist.side_effect = (
        persist
    )

    use_case = ProcessSegyFileUseCase(
        processing_service=processing_service,
        persistence_service=persistence_service,
    )

    use_case.execute(
        filename="slb1.sgy",
        segy_file_id=7,
    )

    assert calls == [
        "process",
        "persist",
    ]


def test_execute_does_not_persist_when_processing_fails():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processing_error = RuntimeError(
        "SEG-Y processing failed"
    )

    processing_service.process_file.side_effect = (
        processing_error
    )

    with pytest.raises(
        RuntimeError,
        match="SEG-Y processing failed",
    ):
        use_case.execute(
            filename="slb1.sgy",
            segy_file_id=7,
        )

    processing_service.process_file.assert_called_once_with(
        "slb1.sgy",
    )

    persistence_service.persist.assert_not_called()


def test_execute_propagates_persistence_error():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processed_data = create_processed_data()

    processing_service.process_file.return_value = (
        processed_data
    )

    persistence_error = RuntimeError(
        "Persistence failed"
    )

    persistence_service.persist.side_effect = (
        persistence_error
    )

    with pytest.raises(
        RuntimeError,
        match="Persistence failed",
    ):
        use_case.execute(
            filename="slb1.sgy",
            segy_file_id=7,
        )

    processing_service.process_file.assert_called_once_with(
        "slb1.sgy",
    )

    persistence_service.persist.assert_called_once_with(
        processed_data,
        7,
    )


def test_execute_returns_processed_data_after_persistence():
    (
        use_case,
        processing_service,
        persistence_service,
    ) = create_use_case()

    processed_data = create_processed_data()

    processing_service.process_file.return_value = (
        processed_data
    )

    result = use_case.execute(
        filename="slb1.sgy",
        segy_file_id=7,
    )

    assert result is processed_data

    persistence_service.persist.assert_called_once_with(
        processed_data,
        7,
    )