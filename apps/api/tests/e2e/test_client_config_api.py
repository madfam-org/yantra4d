"""E2E tests for /api/config/client endpoint."""
import pytest
from unittest.mock import patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def app(tmp_path):
    from app import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestClientConfigEndpoint:
    """Tests for GET /api/config/client — platform branding resolution."""

    def test_no_license_key_returns_default_branding(self, client, monkeypatch):
        from config import Config

        monkeypatch.setattr(Config, "YANTRA4D_LICENSE_KEY", "")
        res = client.get("/api/config/client")
        assert res.status_code == 200
        data = res.get_json()
        assert data["platformName"] == "Yantra4D"
        assert data["platformLogo"] == "/logo.png"

    @patch("routes.core.client_config.decode_token")
    @patch("routes.core.client_config.resolve_tier")
    @patch("routes.core.client_config.has_tier")
    def test_pro_tier_returns_custom_branding(
        self, mock_has, mock_resolve, mock_decode, client, monkeypatch
    ):
        from config import Config

        monkeypatch.setattr(Config, "YANTRA4D_LICENSE_KEY", "valid-jwt")
        monkeypatch.setattr(Config, "PLATFORM_NAME", "MyBrand")
        monkeypatch.setattr(Config, "PLATFORM_LOGO", "/my-logo.png")
        mock_decode.return_value = {"tier": "pro"}
        mock_resolve.return_value = "pro"
        mock_has.return_value = True

        res = client.get("/api/config/client")
        assert res.status_code == 200
        data = res.get_json()
        assert data["platformName"] == "MyBrand"
        assert data["platformLogo"] == "/my-logo.png"

    @patch("routes.core.client_config.decode_token")
    def test_invalid_token_returns_default_branding(
        self, mock_decode, client, monkeypatch
    ):
        from config import Config

        monkeypatch.setattr(Config, "YANTRA4D_LICENSE_KEY", "bad-token")
        mock_decode.side_effect = Exception("JWT validation failed")

        res = client.get("/api/config/client")
        assert res.status_code == 200
        data = res.get_json()
        assert data["platformName"] == "Yantra4D"
        assert data["platformLogo"] == "/logo.png"

    @patch("routes.core.client_config.decode_token")
    @patch("routes.core.client_config.resolve_tier")
    @patch("routes.core.client_config.has_tier")
    def test_non_pro_tier_returns_default_branding(
        self, mock_has, mock_resolve, mock_decode, client, monkeypatch
    ):
        from config import Config

        monkeypatch.setattr(Config, "YANTRA4D_LICENSE_KEY", "basic-key")
        mock_decode.return_value = {"tier": "basic"}
        mock_resolve.return_value = "basic"
        mock_has.return_value = False

        res = client.get("/api/config/client")
        assert res.status_code == 200
        data = res.get_json()
        assert data["platformName"] == "Yantra4D"
        assert data["platformLogo"] == "/logo.png"

    def test_response_content_type_is_json(self, client, monkeypatch):
        from config import Config

        monkeypatch.setattr(Config, "YANTRA4D_LICENSE_KEY", "")
        res = client.get("/api/config/client")
        assert res.content_type.startswith("application/json")
