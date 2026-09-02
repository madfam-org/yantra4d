"""Tests for the OpenAPI spec gate.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_check_openapi.py -q

``scripts/qa/check_openapi.py`` is the whole ``openapi-validation`` job, which
``ci-success`` requires. It exists for one failure the plain validator cannot
see: PyYAML resolves a duplicate mapping key by silently keeping the LAST
definition, so a spec can define ``/api/catalog/nopscadlib`` twice — different
tags, summaries and response schemas — validate cleanly, and ship with half of
it discarded. That is what happened, and the validation job stayed green
throughout.

So the assertions that matter are: a duplicate key is REJECTED rather than
resolved, it is rejected wherever it appears rather than only at the top level,
and it is rejected BEFORE the validator runs — a spec that is both duplicated
and otherwise valid must be reported as duplicated, not as valid.

``openapi_spec_validator`` is not installed by every lane that runs this
suite, so the cases that need it skip rather than fail; the duplicate-key
cases, which are the reason this script exists, need only PyYAML.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import check_openapi as lane  # noqa: E402

HAVE_VALIDATOR = importlib.util.find_spec("openapi_spec_validator") is not None
needs_validator = pytest.mark.skipif(
    not HAVE_VALIDATOR, reason="openapi_spec_validator is not installed")

VALID = textwrap.dedent("""\
    openapi: 3.0.3
    info:
      title: Yantra4D API
      version: "1.0.0"
    paths:
      /api/health:
        get:
          summary: Liveness
          responses:
            "200":
              description: ok
      /api/projects:
        get:
          summary: List cartridges
          responses:
            "200":
              description: ok
    """)


def load(text: str):
    return yaml.load(text, Loader=lane._StrictLoader)


def spec(tmp_path, monkeypatch, text: str) -> Path:
    path = tmp_path / "docs" / "reference" / "openapi.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(lane, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lane, "SPEC_PATH", path)
    return path


# --- the duplicate-key check ----------------------------------------------

def test_a_unique_mapping_loads_normally():
    assert load("a: 1\nb: 2\n") == {"a": 1, "b": 2}


def test_a_duplicate_top_level_key_is_refused_not_resolved():
    with pytest.raises(lane.DuplicateKeyError) as exc:
        load("a: 1\na: 2\n")
    assert "'a'" in str(exc.value)


def test_a_duplicate_path_is_refused(tmp_path):
    """The exact failure this script was written for."""
    with pytest.raises(lane.DuplicateKeyError) as exc:
        load(textwrap.dedent("""\
            paths:
              /api/catalog/nopscadlib:
                get:
                  summary: First
              /api/catalog/nopscadlib:
                get:
                  summary: Second
            """))
    assert "/api/catalog/nopscadlib" in str(exc.value)


def test_a_duplicate_deep_inside_the_document_is_refused():
    with pytest.raises(lane.DuplicateKeyError):
        load(textwrap.dedent("""\
            paths:
              /api/health:
                get:
                  responses:
                    "200":
                      description: ok
                    "200":
                      description: also ok
            """))


def test_the_error_names_the_line_and_says_what_pyyaml_would_have_done():
    with pytest.raises(lane.DuplicateKeyError) as exc:
        load("a: 1\nb: 2\na: 3\n")
    message = str(exc.value)
    assert "line 3" in message
    assert "column 1" in message
    assert "silently keep the last definition" in message


def test_the_same_key_in_two_different_mappings_is_fine():
    assert load(textwrap.dedent("""\
        first:
          get: a
        second:
          get: b
        """)) == {"first": {"get": "a"}, "second": {"get": "b"}}


def test_repeated_list_entries_are_not_duplicate_keys():
    assert load("tags:\n  - render\n  - render\n") == {"tags": ["render", "render"]}


def test_the_strict_loader_is_still_a_safe_loader():
    """A spec must not be able to construct arbitrary Python objects."""
    with pytest.raises(yaml.YAMLError):
        load("!!python/object/apply:os.system ['echo pwned']\n")


# --- the script's exit codes ----------------------------------------------

def test_a_missing_spec_fails(tmp_path, monkeypatch, capsys):
    path = spec(tmp_path, monkeypatch, "openapi: 3.0.3\n")
    path.unlink()
    assert lane.main() == 1
    assert "MISSING" in capsys.readouterr().out


def test_a_duplicate_key_fails_the_lane(tmp_path, monkeypatch, capsys):
    spec(tmp_path, monkeypatch, VALID + '  /api/health:\n    get:\n      responses:\n'
         '        "200":\n          description: ok\n')
    assert lane.main() == 1
    out = capsys.readouterr().out
    assert "duplicate key" in out
    assert "/api/health" in out


def test_unparseable_yaml_fails_with_a_yaml_error(tmp_path, monkeypatch, capsys):
    spec(tmp_path, monkeypatch, "openapi: 3.0.3\n  bad: [indent\n")
    assert lane.main() == 1
    assert "not valid YAML" in capsys.readouterr().out


@needs_validator
def test_a_valid_spec_passes_and_reports_its_path_count(tmp_path, monkeypatch, capsys):
    spec(tmp_path, monkeypatch, VALID)
    assert lane.main() == 0
    assert "2 paths" in capsys.readouterr().out


@needs_validator
def test_a_structurally_invalid_spec_fails(tmp_path, monkeypatch, capsys):
    spec(tmp_path, monkeypatch, "openapi: 3.0.3\npaths: {}\n")  # no `info`
    assert lane.main() == 1
    assert "failed spec validation" in capsys.readouterr().out


@needs_validator
def test_a_duplicated_but_otherwise_valid_spec_is_reported_as_duplicated(
        tmp_path, monkeypatch, capsys):
    """The whole point: the duplicate check runs BEFORE the validator."""
    duplicated = VALID + (
        '  /api/health:\n'
        '    get:\n'
        '      summary: Liveness again\n'
        '      responses:\n'
        '        "200":\n'
        '          description: ok\n'
    )
    spec(tmp_path, monkeypatch, duplicated)
    assert lane.main() == 1
    out = capsys.readouterr().out
    assert "duplicate key" in out
    assert "failed spec validation" not in out


# --- the committed spec ----------------------------------------------------

def test_the_committed_spec_has_no_duplicate_keys():
    if not lane.SPEC_PATH.is_file():
        pytest.skip("docs/reference/openapi.yaml is not present in this checkout")
    load(lane.SPEC_PATH.read_text(encoding="utf-8"))
