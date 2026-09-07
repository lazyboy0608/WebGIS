from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.block import router as block_router
from app.api.routes.health import router as health_router
from app.api.routes.processed_data import router as processed_data_router

app = FastAPI(
    title="Data Serving Service",
    version="0.1.0",
    description="Read-only API for serving processed seismic data from PostgreSQL/PostGIS.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(processed_data_router)
app.include_router(auth_router)
app.include_router(block_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
