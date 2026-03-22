"""
FastAPI application factory for the planzen web API.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.sessions import router as sessions_router
from routes.compute import router as compute_router
from routes.export import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    sessions_dir = Path(__file__).parent.parent.parent / "tmp" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="planzen API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router, prefix="/api")
app.include_router(compute_router, prefix="/api")
app.include_router(export_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    # Run from repo root with:  uv run uvicorn main:app --app-dir web/backend --reload
    # Or directly:              python web/backend/main.py
    # Python adds this file's directory to sys.path automatically in both cases.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
