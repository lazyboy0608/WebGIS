from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.block import router as block_router
from app.api.routes.health import router as health_router
from app.api.routes.mvt import router as mvt_router
from app.api.routes.processed_data import router as processed_data_router
from app.api.routes.segy_file import router as segy_file_router

app = FastAPI(
    title="SEG-Y Processing Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,   # Bắt buộc khi frontend gửi credentials: 'include'
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(segy_file_router)
app.include_router(processed_data_router)
app.include_router(block_router)
app.include_router(mvt_router)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
