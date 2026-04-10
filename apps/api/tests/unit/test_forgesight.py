"""Tests for ForgeSight Data Intelligence Platform integration client."""
from unittest.mock import patch, MagicMock

from services.integrations.forgesight import ForgeSightClient, Quote, QuoteItem


class TestForgeSightClientAvailability:
    """Test the available property and configuration."""

    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            assert not client.available

    def test_unavailable_when_no_url(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "",
            "FORGESIGHT_API_KEY": "key",
        }):
            client = ForgeSightClient()
            assert not client.available

    def test_unavailable_when_no_key(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "",
        }):
            client = ForgeSightClient()
            assert not client.available

    def test_available_when_fully_configured(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            assert client.available


class TestForgeSightClientGetQuote:
    """Test the get_quote method."""

    def test_returns_error_when_not_available(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "bolt", "quantity": 4}])
            assert quote.error is not None
            assert len(quote.items) == 0

    @patch("services.integrations.forgesight.requests.post")
    def test_successful_quote(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "part_name": "M3 bolt",
                    "quantity": 4,
                    "unit_price": 0.12,
                    "lead_time_days": 3,
                    "available": True,
                }
            ],
            "total_price": 0.48,
            "currency": "USD",
            "valid_until": "2026-04-16T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "M3 bolt", "quantity": 4}])

        assert quote.error is None
        assert len(quote.items) == 1
        assert quote.items[0].part_name == "M3 bolt"
        assert quote.items[0].unit_price == 0.12
        assert quote.items[0].available is True
        assert quote.total_price == 0.48
        assert quote.currency == "USD"

    @patch("services.integrations.forgesight.requests.post")
    def test_timeout_returns_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.Timeout("Connection timed out")

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "bolt", "quantity": 1}])

        assert "timed out" in quote.error
        assert len(quote.items) == 0

    @patch("services.integrations.forgesight.requests.post")
    def test_http_error_returns_error(self, mock_post):
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = req.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "bolt", "quantity": 1}])

        assert "500" in quote.error

    @patch("services.integrations.forgesight.requests.post")
    def test_connection_error_returns_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("Connection refused")

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "bolt", "quantity": 1}])

        assert "unreachable" in quote.error

    @patch("services.integrations.forgesight.requests.post")
    def test_invalid_json_returns_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            quote = client.get_quote([{"part_name": "bolt", "quantity": 1}])

        assert "invalid response" in quote.error


class TestForgeSightClientMaterialPricing:
    """Test the get_material_pricing placeholder."""

    def test_returns_none_when_unavailable(self):
        with patch.dict("os.environ", {"FORGESIGHT_ENABLED": "false"}):
            client = ForgeSightClient()
            assert client.get_material_pricing("pla") is None

    def test_returns_none_when_available(self):
        with patch.dict("os.environ", {
            "FORGESIGHT_ENABLED": "true",
            "FORGESIGHT_API_URL": "https://api.forgesight.io",
            "FORGESIGHT_API_KEY": "test-key",
        }):
            client = ForgeSightClient()
            assert client.get_material_pricing("pla") is None


class TestDataclasses:
    """Test QuoteItem and Quote dataclass construction."""

    def test_quote_item_defaults(self):
        item = QuoteItem(part_name="bolt", quantity=4)
        assert item.unit_price is None
        assert item.lead_time_days is None
        assert item.available is False

    def test_quote_item_with_values(self):
        item = QuoteItem(
            part_name="bolt", quantity=4,
            unit_price=0.50, lead_time_days=7, available=True,
        )
        assert item.unit_price == 0.50
        assert item.available is True

    def test_quote_defaults(self):
        quote = Quote(items=[])
        assert quote.total_price is None
        assert quote.currency == "USD"
        assert quote.valid_until is None
        assert quote.error is None

    def test_quote_with_error(self):
        quote = Quote(items=[], error="Something went wrong")
        assert quote.error == "Something went wrong"
