"""Tests for GitHub token extraction and validation service."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.github_token import get_github_token, _fetch_github_token_from_janua, validate_github_token


class TestGetGithubToken:
    def test_no_claims(self):
        assert get_github_token(None) is None

    def test_empty_claims(self):
        assert get_github_token({}) is None

    def test_token_in_claims(self):
        claims = {"github_token": "ghp_abc123"}
        assert get_github_token(claims) == "ghp_abc123"

    @patch("services.github_token._fetch_github_token_from_janua", return_value="ghp_from_janua")
    def test_fallback_to_janua(self, mock_fetch, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "JANUA_API_KEY", "test-key")
        claims = {"sub": "user123"}
        assert get_github_token(claims) == "ghp_from_janua"
        mock_fetch.assert_called_once_with("user123")

    def test_no_janua_key(self, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "JANUA_API_KEY", "")
        claims = {"sub": "user123"}
        assert get_github_token(claims) is None

    @patch("services.github_token._fetch_github_token_from_janua", return_value=None)
    def test_janua_returns_none(self, mock_fetch, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "JANUA_API_KEY", "test-key")
        claims = {"sub": "user123"}
        assert get_github_token(claims) is None


class TestFetchFromJanua:
    @patch("services.github_token.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "ghp_from_api"}
        mock_get.return_value = mock_resp
        assert _fetch_github_token_from_janua("user123") == "ghp_from_api"

    @patch("services.github_token.requests.get")
    def test_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        assert _fetch_github_token_from_janua("user123") is None

    @patch("services.github_token.requests.get", side_effect=Exception("network error"))
    def test_exception(self, mock_get):
        assert _fetch_github_token_from_janua("user123") is None


class TestValidateGithubToken:
    @patch("services.github_token.requests.get")
    def test_valid_token(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"login": "testuser", "id": 123}
        mock_get.return_value = mock_resp
        result = validate_github_token("ghp_valid")
        assert result["login"] == "testuser"

    @patch("services.github_token.requests.get")
    def test_invalid_token(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        assert validate_github_token("ghp_bad") is None

    @patch("services.github_token.requests.get", side_effect=Exception("timeout"))
    def test_exception(self, mock_get):
        assert validate_github_token("ghp_any") is None
