"""The CORS dependency upgrade must preserve the API's origin allowlist."""
import pytest


@pytest.fixture
def client(monkeypatch):
    from app import create_app
    from config import Config

    monkeypatch.setattr(Config, "CORS_ORIGINS", ["https://studio.example.test"])
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize("method", ["GET", "OPTIONS"])
def test_allowed_origin_receives_cors_headers(client, method):
    response = client.open(
        "/api/health", method=method,
        headers={"Origin": "https://studio.example.test", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://studio.example.test"
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.parametrize("origin", [
    "https://untrusted.example.test",
    "https://studio.example.test.attacker.test",
    "null",
])
@pytest.mark.parametrize("method", ["GET", "OPTIONS"])
def test_untrusted_origin_receives_no_cors_permission(client, origin, method):
    response = client.open(
        "/api/health", method=method,
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
