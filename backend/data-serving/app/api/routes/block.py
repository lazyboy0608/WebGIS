import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.api.schemas.block import (
    BlockGeoJSONFeatureCollection,
    BlockResponse,
    BlockSplitRequest,
    UndoSplitRequest,
    UndoSplitResponse,
)
from app.database import get_db_session
from app.models import UserModel
from app.services.block_service import BlockService

router = APIRouter(prefix="/api/blocks", tags=["Blocks"])


def get_block_service(
    session: Session = Depends(get_db_session),
) -> BlockService:
    return BlockService(session)


@router.get(
    "/geojson",
    response_model=BlockGeoJSONFeatureCollection,
    summary="Lấy dữ liệu không gian Lô địa chấn dưới dạng GeoJSON",
)
def get_blocks_geojson(
    status_filter: Optional[str] = Query(
        "active",
        description="Lọc theo trạng thái: 'active' (mặc định), 'split', hoặc NULL để lấy tất cả",
    ),
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> Dict[str, Any]:
    filter_val = None if status_filter == "all" else status_filter
    user_id = current_user.id if current_user else None
    return service.get_blocks_geojson(status_filter=filter_val, user_id=user_id)


@router.get(
    "",
    response_model=List[BlockResponse],
    summary="Danh sách tất cả Lô địa chấn",
)
def list_blocks(
    status_filter: Optional[str] = Query(
        "active",
        description="Lọc theo trạng thái: 'active', 'split', hoặc 'all'",
    ),
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> List[BlockResponse]:
    filter_val = None if status_filter == "all" else status_filter
    user_id = current_user.id if current_user else None
    return service.get_blocks(status_filter=filter_val, user_id=user_id)


@router.get(
    "/{block_id}",
    response_model=BlockResponse,
    summary="Chi tiết một Lô địa chấn",
)
def get_block_detail(
    block_id: int,
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> BlockResponse:
    user_id = current_user.id if current_user else None
    block = service.get_block_by_id(block_id, user_id=user_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Lô địa chấn với id={block_id}",
        )
    return block


@router.post(
    "/{block_id}/split",
    response_model=List[BlockResponse],
    summary="Thực hiện phân tách Lô địa chấn (Split Block) theo đường cắt",
)
def split_block(
    block_id: int,
    request: BlockSplitRequest,
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> List[BlockResponse]:
    try:
        user_id = current_user.id if current_user else None
        child_blocks = service.split_block(
            block_id=block_id,
            split_line_wkt=request.split_line_wkt,
            new_block_codes=request.new_block_codes,
            user_id=user_id,
        )
        return child_blocks
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi phân tách Lô: {str(e)}",
        )


@router.post(
    "/undo-split",
    response_model=UndoSplitResponse,
    summary="Hoàn tác thao tác tách Lô địa chấn gần nhất (Undo Split)",
)
def undo_split_block(
    request: UndoSplitRequest,
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> UndoSplitResponse:
    """
    Command Pattern — Undo:
    - Xóa các lô con (parent_id = request.parent_block_id)
    - Phục hồi lô cha về status = 'active'
    """
    try:
        user_id = current_user.id if current_user else None
        parent_block, deleted_child_ids = service.undo_split(
            parent_block_id=request.parent_block_id,
            user_id=user_id,
        )
        return UndoSplitResponse(
            restored_block=BlockResponse.model_validate(parent_block),
            deleted_child_ids=deleted_child_ids,
        )
    except ValueError as e:
        http_status = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=http_status, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi hoàn tác tách Lô: {str(e)}",
        )


@router.get(
    "/{block_id}/export-excel",
    summary="Xuất dữ liệu ranh giới Lô (X, Y, Block, Basin) ra file Excel (.xlsx)",
)
def export_block_excel(
    block_id: int,
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> StreamingResponse:
    """
    Truy vấn PostGIS bằng ST_DumpPoints để trích xuất danh sách các điểm đỉnh (X, Y)
    của Lô địa chấn, đóng gói thành file Excel (.xlsx) và stream trực tiếp về máy người dùng.
    """
    try:
        user_id = current_user.id if current_user else None
        excel_bytes, filename = service.export_block_excel(block_id, user_id=user_id)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except ValueError as e:
        http_status = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=http_status, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xuất Excel Lô địa chấn: {str(e)}",
        )


@router.delete(
    "",
    summary="Xóa các Lô địa chấn (xóa toàn bộ hoặc theo tên file nguồn source_file)",
)
def delete_blocks(
    source_file: Optional[str] = Query(None, description="Tên file nguồn cần xóa (nếu không truyền sẽ xóa tất cả)"),
    service: BlockService = Depends(get_block_service),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
) -> Dict[str, Any]:
    try:
        user_id = current_user.id if current_user else None
        if source_file:
            count = service.delete_blocks_by_source_file(source_file, user_id=user_id)
        else:
            count = service.delete_all_blocks(user_id=user_id)
        return {
            "message": f"Đã xóa thành công {count} lô địa chấn",
            "deleted_count": count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xóa Lô địa chấn: {str(e)}",
        )



