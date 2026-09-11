from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db_session
from app.api.schemas.block import BlockInfo, BlockUploadResponse
from app.api.schemas.segy_file import SegyTaskStatusResponse
from app.core.task_manager import get_task_manager
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
    task_id: str | None = Form(None),
    db: Session = Depends(get_db_session),
    current_user_id: int | None = Depends(get_current_user_id),
):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ tải lên file nén định dạng .zip chứa Shapefile.",
        )

    task_mgr = get_task_manager()
    if task_id:
        task_mgr.create_task(task_id, file.filename)

    try:
        contents = await file.read()
        service = BlockProcessingService(db)
        imported_blocks = service.process_shapefile_zip(
            contents,
            file.filename,
            user_id=current_user_id,
            task_id=task_id,
        )

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
        if task_id:
            task_mgr.update_task(task_id, status="FAILED", message=str(e), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if task_id:
            task_mgr.update_task(task_id, status="FAILED", message=f"Lỗi hệ thống khi xử lý Shapefile: {str(e)}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý Shapefile: {str(e)}",
        )


@router.get(
    "/tasks/{task_id}",
    response_model=SegyTaskStatusResponse,
    summary="Lấy thông tin tiến độ xử lý file Block zip bất đồng bộ",
)
def get_block_task_status(
    task_id: str,
) -> SegyTaskStatusResponse:
    task_mgr = get_task_manager()
    task = task_mgr.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} not found",
        )
    return SegyTaskStatusResponse(
        task_id=task.task_id,
        filename=task.filename,
        status=task.status,
        progress_percent=task.progress_percent,
        message=task.message,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
