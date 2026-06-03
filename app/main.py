from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Shipa Inbound Voice Backend")

    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["X-API-Key"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.routers import tools

    app.include_router(tools.router)

    from app.routers import dashboard

    app.include_router(dashboard.router)

    from app.routers import ingest

    app.include_router(ingest.router)

    from app.routers import twin

    app.include_router(twin.router)

    return app


app = create_app()
