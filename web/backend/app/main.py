from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import data, factors, health, jobs, lifecycle, optimization, paper, registry, risk, system, ws


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = PROJECT_ROOT / "web/frontend/dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-OuYi Web API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(registry.router, prefix="/api")
    app.include_router(lifecycle.router, prefix="/api")
    app.include_router(optimization.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(data.router, prefix="/api")
    app.include_router(paper.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    app.include_router(factors.router, prefix="/api")
    app.include_router(ws.router, prefix="/api")

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend_app(path: str) -> FileResponse:
            requested = FRONTEND_DIST / path
            if path and requested.exists() and requested.is_file():
                return FileResponse(requested)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
