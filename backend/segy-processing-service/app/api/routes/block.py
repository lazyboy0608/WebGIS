from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.api.schemas.block import BlockInfo, BlockUploadResponse
from app.services.block_processing_service import BlockProcessingService

router = APIRouter(
    prefix="/api/blocks",
    tags=["Blocks"],
)


@router.post(
    "/upload-zip",
    response_model=BlockUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload .zip Shapefile phân lô, nạp vào MinIO và PostGIS (EPSG:4326)",
)

async def upload_block_zip(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ tải lên file nén định dạng .zip chứa Shapefile.",
        )

    try:
        contents = await file.read()
        service = BlockProcessingService(db)
        imported_blocks = service.process_shapefile_zip(contents, file.filename)

        blocks_info = [
            BlockInfo(
                id=b.id,
                block_code=b.block_code,
                operator=b.operator,
                basin_name=b.basin_name,
                area_km2=b.area_km2,
                status=b.status,
                parent_id=b.parent_id,
                source_file=b.source_file,
                created_at=b.created_at,
            )
            for b in imported_blocks
        ]

        return BlockUploadResponse(
            message=f"Đã nhập thành công {len(imported_blocks)} Lô địa chấn vào hệ thống.",
            imported_count=len(imported_blocks),
            blocks=blocks_info,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý Shapefile: {str(e)}",
        )
