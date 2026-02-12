from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.on_event("startup")
    def on_startup() -> None:
        # For local development convenience. Production should apply Alembic migrations.
        if settings.environment == "dev":
            Base.metadata.create_all(bind=engine)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
