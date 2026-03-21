"""Tests for utils.studio_url."""

import os
import pytest
from unittest.mock import patch
from flask import Flask

from utils.studio_url import build_project_url


@pytest.fixture
def app():
    return Flask(__name__)


class TestBuildProjectUrl:
    def test_basic_url(self, app):
        with app.test_request_context():
            with patch.dict(os.environ, {"PUBLIC_STUDIO_URL": "https://app.yantra4d.com"}):
                url = build_project_url("my-project")
        assert url == "https://app.yantra4d.com/project/my-project"

    def test_storefront_mode(self, app):
        with app.test_request_context():
            with patch.dict(os.environ, {"PUBLIC_STUDIO_URL": "https://app.yantra4d.com"}):
                url = build_project_url("tablaco", mode="storefront")
        assert url == "https://app.yantra4d.com/project/tablaco?mode=storefront"

    def test_preset_with_params(self, app):
        with app.test_request_context():
            with patch.dict(os.environ, {"PUBLIC_STUDIO_URL": "https://example.com"}):
                url = build_project_url(
                    "demo",
                    mode="storefront",
                    preset_id="p1",
                    params={"size": 20},
                )
        assert "/project/demo?" in url
        assert "mode=storefront" in url
        assert "preset=p1" in url
        assert "size=20" in url

    def test_trailing_slash_stripped(self, app):
        with app.test_request_context():
            with patch.dict(os.environ, {"PUBLIC_STUDIO_URL": "https://app.yantra4d.com/"}):
                url = build_project_url("test")
        assert url == "https://app.yantra4d.com/project/test"

    def test_no_hash_in_output(self, app):
        with app.test_request_context():
            with patch.dict(os.environ, {"PUBLIC_STUDIO_URL": "https://example.com"}):
                url = build_project_url(
                    "slug",
                    mode="storefront",
                    preset_id="p1",
                    params={"a": 1, "b": 2},
                )
        assert "#" not in url

    def test_fallback_to_request_host(self, app):
        with app.test_request_context("http://localhost:5000/"):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PUBLIC_STUDIO_URL", None)
                url = build_project_url("proj")
        assert url.startswith("http://localhost")
        assert "/project/proj" in url
