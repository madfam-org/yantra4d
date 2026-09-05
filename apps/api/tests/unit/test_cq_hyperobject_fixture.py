"""The vendored CadQuery engine fixture (RFC 0038 P2).

`cq-hyperobject-test` used to live in `projects/` and was therefore served by
the API, which is why the platform reported one project more than the commons
held (501 over 500 at the time; the commons is 495 today). It was never a
commons object. Since P2 it is vendored under
`tests/fixtures/cartridges/` and is reachable only by pointing a cartridge root
at it — these tests hold that line in both directions.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.project_resolver import find_project_dir

FIXTURES = Path(__file__).parent.parent / "fixtures" / "cartridges"
FIXTURE = FIXTURES / "cq-hyperobject-test"


def test_the_fixture_is_vendored_and_complete():
    assert FIXTURE.is_dir()
    manifest = json.loads((FIXTURE / "project.json").read_text())
    assert manifest["project"]["slug"] == "cq-hyperobject-test"
    # A CadQuery-only cartridge: the script and its reference solid.
    assert (FIXTURE / "box.py").is_file()
    assert (FIXTURE / "box.step").is_file()


def test_the_fixture_is_not_under_any_cartridge_root(monkeypatch, tmp_path):
    """It must not be discoverable as a project by default."""
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path / "private-projects")

    assert find_project_dir("cq-hyperobject-test") is None


def test_the_fixture_resolves_when_a_root_is_pointed_at_it(monkeypatch, tmp_path):
    """A test that WANTS it mounts the fixture directory as a cartridge root."""
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", FIXTURES)
    monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path / "absent")

    resolved = find_project_dir("cq-hyperobject-test")
    assert resolved == FIXTURE.resolve()


def test_the_fixture_is_discovered_only_from_that_root(monkeypatch):
    """Mounted as a root, the manifest service sees it like any cartridge."""
    from config import Config
    from manifest import ManifestService
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [FIXTURES])

    slugs = {p["slug"] for p in ManifestService().discover_projects()}
    assert slugs == {"cq-hyperobject-test"}
