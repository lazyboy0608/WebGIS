from unittest.mock import MagicMock
from app.application.services.mvt_service import MVTService

def test_mvt_service_generate_tile():
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.return_value = b"\x1a\x05tile1"

    service = MVTService(mock_session)
    tile_bytes = service.generate_tile(z=10, x=500, y=300, file_id=1)

    assert isinstance(tile_bytes, bytes)
    assert mock_session.execute.call_count == 3
