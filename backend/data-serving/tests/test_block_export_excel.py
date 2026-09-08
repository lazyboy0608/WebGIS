import io
from unittest.mock import MagicMock
import pandas as pd
import pytest

from app.services.block_service import BlockService
from app.models import SeismicBlockModel


def test_export_block_excel_success():
    session = MagicMock()
    block = SeismicBlockModel(
        id=1,
        block_code="01&02",
        basin_name="Cuu Long",
    )
    session.query.return_value.filter.return_value.first.return_value = block

    # Mock PostGIS ST_DumpPoints query result
    mock_row1 = MagicMock()
    mock_row1.x = 108.45
    mock_row1.y = 10.6
    mock_row1.block = "01&02"
    mock_row1.basin = "Cuu Long"

    mock_row2 = MagicMock()
    mock_row2.x = 108.7
    mock_row2.y = 10.383333
    mock_row2.block = "01&02"
    mock_row2.basin = "Cuu Long"

    session.execute.return_value.fetchall.return_value = [mock_row1, mock_row2]

    service = BlockService(session)
    excel_bytes, filename = service.export_block_excel(1)

    assert filename == "Block_01_02_Coordinates.xlsx"
    assert isinstance(excel_bytes, bytes)

    # Read back Excel bytes using pandas
    df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="Blk")
    assert list(df.columns) == ["X", "Y", "Block", "Basin"]
    assert len(df) == 2
    assert df.iloc[0]["X"] == 108.45
    assert df.iloc[0]["Y"] == 10.6
    assert df.iloc[0]["Block"] == "01&02"
    assert df.iloc[0]["Basin"] == "Cuu Long"


def test_export_block_excel_not_found():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None

    service = BlockService(session)
    with pytest.raises(ValueError, match="Không tìm thấy Lô địa chấn"):
        service.export_block_excel(999)
