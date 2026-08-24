from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "data-serving"}
