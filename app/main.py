from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Shipa Inbound Voice Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
