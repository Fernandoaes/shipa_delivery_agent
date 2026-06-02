from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Shipa Inbound Voice Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.routers import tools

    app.include_router(tools.router)

    from app.routers import dashboard

    app.include_router(dashboard.router)

    return app


app = create_app()
