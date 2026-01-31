"""Shared test fixtures for backend API tests."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "web_interface" / "backend"))


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Ensure Config paths point to tmp_path and manifest cache is cleared for every test."""
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "SCAD_DIR", tmp_path)
    monkeypatch.setattr(Config, "MULTI_PROJECT", True)

    import manifest as manifest_mod
    manifest_mod._manifest_cache.clear()
    yield
    manifest_mod._manifest_cache.clear()
