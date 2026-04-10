"""Tests for ForgeSight Data Intelligence Platform integration client."""
from unittest.mock import patch, MagicMock

from services.integrations.forgesight import (
    ForgeSightClient, MaterialBenchmark, Quote, QuoteItem,
    MATERIAL_CATEGORY_MAP, DEFAULT_PRICING,
)


class TestForgeSightClientAvailability:
    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            assert not client.available

    def test_unavailable_when_no_email(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true", "FORGESIGHT_EMAIL": "",
            "FORGESIGHT_PASSWORD": "pass",
        }):
            client = ForgeSightClient()
            assert not client.available

    def test_unavailable_when_no_password(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true", "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "",
        }):
            client = ForgeSightClient()
            assert not client.available

    def test_available_when_fully_configured(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            assert client.available


class TestForgeSightAuth:
    @patch("services.integrations.forgesight.requests.post")
    def test_authenticate_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 3600}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            token = client._authenticate()

        assert token == "tok123"
        mock_post.assert_called_once()

    @patch("services.integrations.forgesight.requests.post")
    def test_authenticate_caches_token(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 3600}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            client._authenticate()
            client._authenticate()

        assert mock_post.call_count == 1  # Only 1 HTTP call, second uses cache

    @patch("services.integrations.forgesight.requests.post")
    def test_authenticate_failure_returns_none(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("refused")

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "wrong",
        }):
            client = ForgeSightClient()
            assert client._authenticate() is None


class TestGetMaterialBenchmark:
    def test_returns_default_when_disabled(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            benchmark = client.get_material_benchmark("pla")

        assert benchmark.source == "hardcoded_default"
        assert benchmark.p50_per_kg == DEFAULT_PRICING["pla"]
        assert benchmark.currency == "USD"

    def test_returns_default_for_unknown_material(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            benchmark = client.get_material_benchmark("unobtanium")

        assert benchmark.source == "hardcoded_default"
        assert "Unknown material" in (benchmark.error or "")

    @patch("services.integrations.forgesight.requests.get")
    @patch("services.integrations.forgesight.requests.post")
    def test_returns_live_benchmark(self, mock_auth, mock_get):
        mock_auth_resp = MagicMock()
        mock_auth_resp.json.return_value = {"access_token": "tok", "expires_in": 3600}
        mock_auth_resp.raise_for_status = MagicMock()
        mock_auth.return_value = mock_auth_resp

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "p10": 180.0, "p50": 250.0, "p90": 380.0,
            "currency": "MXN", "sample_count": 42, "updated_at": "2026-04-10",
        }
        mock_get_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_resp

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            benchmark = client.get_material_benchmark("pla", "CDMX")

        assert benchmark.source == "forgesight"
        assert benchmark.p10_per_kg == 180.0
        assert benchmark.p50_per_kg == 250.0
        assert benchmark.p90_per_kg == 380.0
        assert benchmark.currency == "MXN"
        assert benchmark.sample_count == 42

    @patch("services.integrations.forgesight.requests.get")
    @patch("services.integrations.forgesight.requests.post")
    def test_caches_benchmark(self, mock_auth, mock_get):
        mock_auth_resp = MagicMock()
        mock_auth_resp.json.return_value = {"access_token": "tok", "expires_in": 3600}
        mock_auth_resp.raise_for_status = MagicMock()
        mock_auth.return_value = mock_auth_resp

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "p10": 180.0, "p50": 250.0, "p90": 380.0,
            "currency": "MXN", "sample_count": 42,
        }
        mock_get_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_resp

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            client.get_material_benchmark("pla")
            client.get_material_benchmark("pla")  # Should hit cache

        assert mock_get.call_count == 1

    @patch("services.integrations.forgesight.requests.get")
    @patch("services.integrations.forgesight.requests.post")
    def test_falls_back_on_timeout(self, mock_auth, mock_get):
        import requests as req
        mock_auth_resp = MagicMock()
        mock_auth_resp.json.return_value = {"access_token": "tok", "expires_in": 3600}
        mock_auth_resp.raise_for_status = MagicMock()
        mock_auth.return_value = mock_auth_resp

        mock_get.side_effect = req.Timeout("timed out")

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_EMAIL": "test@example.com",
            "FORGESIGHT_PASSWORD": "secret",
        }):
            client = ForgeSightClient()
            benchmark = client.get_material_benchmark("pla")

        assert benchmark.source == "hardcoded_default"
        assert "timed out" in (benchmark.error or "")


class TestCategoryMapping:
    def test_all_default_materials_have_mappings(self):
        for material_id in DEFAULT_PRICING:
            assert material_id in MATERIAL_CATEGORY_MAP

    def test_supported_materials(self):
        client = ForgeSightClient()
        materials = client.get_supported_materials()
        assert "pla" in materials
        assert "petg" in materials
        assert "abs" in materials


class TestDataclasses:
    def test_material_benchmark_defaults(self):
        b = MaterialBenchmark(
            material="pla", category="FDM - PLA", region="CDMX",
            p10_per_kg=16.0, p50_per_kg=20.0, p90_per_kg=26.0,
        )
        assert b.currency == "MXN"
        assert b.source == "forgesight"
        assert b.error is None

    def test_quote_defaults(self):
        q = Quote()
        assert q.items == []
        assert q.error is None

    def test_quote_item(self):
        qi = QuoteItem(part_name="bolt", quantity=4)
        assert qi.unit_price is None
        assert qi.available is False
