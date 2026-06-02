def _app_with_protected_routes():
    from fastapi import Depends, FastAPI

    from app.deps import require_api_key, require_webhook_secret

    app = FastAPI()

    @app.get("/tool", dependencies=[Depends(require_webhook_secret)])
    def tool():
        return {"ok": True}

    @app.get("/read", dependencies=[Depends(require_api_key)])
    def read():
        return {"ok": True}

    return app


def test_webhook_secret_required():
    from fastapi.testclient import TestClient

    c = TestClient(_app_with_protected_routes())
    assert c.get("/tool").status_code == 401
    assert c.get("/tool", headers={"X-Webhook-Secret": "wrong"}).status_code == 401
    assert c.get("/tool", headers={"X-Webhook-Secret": "dev-webhook-secret-change-me"}).status_code == 200


def test_api_key_required():
    from fastapi.testclient import TestClient

    c = TestClient(_app_with_protected_routes())
    assert c.get("/read").status_code == 401
    assert c.get("/read", headers={"X-API-Key": "dev-dashboard-key-change-me"}).status_code == 200
