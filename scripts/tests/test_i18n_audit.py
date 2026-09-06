"""Tests for the studio i18n audit.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_i18n_audit.py -q

``scripts/qa/i18n_audit.py`` is the whole ``i18n-audit`` job, which
``ci-success`` requires. It is deliberately two different kinds of check, and
confusing them is the failure mode:

  - locale key parity is a HARD GATE. A key present in one locale and absent
    from another ships untranslated UI, so it fails outright.
  - the hardcoded-string count is a RATCHET against
    ``scripts/qa/i18n_baseline.json``. A RISE fails; the standing backlog does
    not block unrelated work, and a FALL passes while asking for the ratchet to
    be lowered. A test that made the backlog fail would make the lane
    unmergeable; a test that let a rise pass would make it pointless.

The two allowlists are also asserted for the property that justifies each:
``ALLOWED_HARDCODED`` matches case-INSENSITIVELY (they are tokens no user
reads), while ``ALLOWED_WEB_API_IDENTIFIERS`` matches case-SENSITIVELY and
against the WHOLE quoted string — so waiving ``'Enter'`` (a KeyboardEvent.key
value) must not also waive ``"Enter your project name"``.

Fixtures are synthetic locale files and component trees in tmp_path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import i18n_audit as lane  # noqa: E402


@pytest.fixture
def studio(tmp_path, monkeypatch):
    """locales/, components/ and a baseline, all repointed at tmp_path."""
    locales = tmp_path / "locales"
    components = tmp_path / "components"
    locales.mkdir()
    components.mkdir()
    baseline = tmp_path / "i18n_baseline.json"
    monkeypatch.setattr(lane, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lane, "LOCALES_DIR", locales)
    monkeypatch.setattr(lane, "COMPONENTS_DIR", components)
    monkeypatch.setattr(lane, "BASELINE_PATH", baseline)
    return locales, components, baseline


def locale(locales: Path, lang: str, data: dict) -> None:
    (locales / f"{lang}.json").write_text(json.dumps(data), encoding="utf-8")


def component(components: Path, name: str, source: str) -> Path:
    path = components / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def set_baseline(baseline: Path, count: int) -> None:
    baseline.write_text(json.dumps({"hardcoded_strings": count}), encoding="utf-8")


# --- key flattening --------------------------------------------------------

def test_nested_keys_flatten_to_dotted_paths():
    assert lane.flatten_keys({"editor": {"save": "Save", "undo": "Undo"}}) == {
        "editor.save", "editor.undo"}


def test_flattening_names_leaves_not_containers():
    keys = lane.flatten_keys({"a": {"b": {"c": "x"}}})
    assert keys == {"a.b.c"}


def test_a_key_holding_a_list_is_one_key():
    assert lane.flatten_keys({"tips": ["one", "two"]}) == {"tips"}


# --- locale parity: a hard gate -------------------------------------------

def test_matching_locales_pass(studio, capsys):
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "es", {"editor": {"save": "Guardar"}})
    assert lane.check_locale_key_parity() is True
    assert "OK (1 keys across 2 locales)" in capsys.readouterr().out


def test_a_key_missing_from_one_locale_fails(studio, capsys):
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save", "undo": "Undo"}})
    locale(locales, "es", {"editor": {"save": "Guardar"}})
    assert lane.check_locale_key_parity() is False
    out = capsys.readouterr().out
    assert "[es] missing key: editor.undo" in out
    assert "editor.save" not in out


def test_parity_is_over_the_union_so_an_extra_key_anywhere_indicts_the_rest(studio):
    """A key added to one locale is missing from every other locale."""
    locales, _, _ = studio
    locale(locales, "en", {"a": "A"})
    locale(locales, "es", {"a": "A", "b": "B"})
    locale(locales, "fr", {"a": "A"})
    assert lane.check_locale_key_parity() is False


def test_an_untranslated_value_is_not_a_parity_failure(studio):
    """Parity is about keys; a copied English string is a translation backlog."""
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "es", {"editor": {"save": "Save"}})
    assert lane.check_locale_key_parity() is True


def test_no_locale_files_at_all_fails(studio, capsys):
    assert lane.check_locale_key_parity() is False
    assert "No locale files found" in capsys.readouterr().out


# --- untranslated markers: the gate parity cannot be -----------------------
#
# `resolveTranslation` is `locales[lang]?.[key] || locales.en?.[key] || key`, so
# a MISSING key falls back to English but a key holding "[UNTRANSLATED] Save" is
# truthy and renders verbatim. Parity is green either way -- which is how the
# four locales sat at ~110 markers each. Zero markers ship today (#133), so this
# is a hard gate with no ratchet.

def test_clean_locales_have_no_markers(studio, capsys):
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "es", {"editor": {"save": "Guardar"}})
    assert lane.check_untranslated_markers() is True
    assert "OK (0 across 2 locales)" in capsys.readouterr().out


def test_a_marker_fails_and_names_its_key(studio, capsys):
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "de", {"editor": {"save": "[UNTRANSLATED] Save"}})
    assert lane.check_untranslated_markers() is False
    out = capsys.readouterr().out
    assert "[de] untranslated: editor.save" in out


def test_a_marker_is_invisible_to_the_parity_gate(studio):
    """The whole reason this check exists: parity passes on a marked locale."""
    locales, _, _ = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "de", {"editor": {"save": "[UNTRANSLATED] Save"}})
    assert lane.check_locale_key_parity() is True
    assert lane.check_untranslated_markers() is False


def test_a_marker_anywhere_in_the_value_counts(studio):
    """The marker is matched as a substring, not a prefix."""
    locales, _, _ = studio
    locale(locales, "en", {"a": "Save [UNTRANSLATED]"})
    assert lane.check_untranslated_markers() is False


def test_markers_are_found_at_any_nesting_depth(studio, capsys):
    locales, _, _ = studio
    locale(locales, "en", {"a": {"b": {"c": "[UNTRANSLATED] deep"}}})
    assert lane.check_untranslated_markers() is False
    assert "[en] untranslated: a.b.c" in capsys.readouterr().out


def test_marker_check_fails_when_there_are_no_locale_files(studio, capsys):
    assert lane.check_untranslated_markers() is False
    assert "No locale files found" in capsys.readouterr().out


def test_flatten_pairs_returns_keys_with_their_values():
    assert lane.flatten_pairs({"editor": {"save": "Save"}}) == [("editor.save", "Save")]


def test_flatten_pairs_ignores_non_string_leaves():
    """flatten_keys counts a list as one key; flatten_pairs has no value to scan."""
    assert lane.flatten_pairs({"tips": ["one", "two"], "a": "A"}) == [("a", "A")]


# --- the hardcoded-string scan --------------------------------------------

def test_a_hardcoded_string_literal_is_found_with_its_location(studio):
    _, components, _ = studio
    component(components, "Toolbar.tsx", 'const heading = "Save the project"\n')
    issues = lane.scan_hardcoded_strings()
    assert len(issues) == 1
    assert "Save the project" in issues[0]
    assert "Toolbar.tsx:1" in issues[0]


def test_a_hardcoded_attribute_value_is_found(studio):
    _, components, _ = studio
    component(components, "Field.jsx", 'const a = <input placeholder="Project name" />\n')
    assert len(lane.scan_hardcoded_strings()) == 1


def test_a_line_that_already_calls_t_is_not_reported(studio):
    _, components, _ = studio
    component(components, "Toolbar.tsx", 'const heading = t("editor.save")\n')
    assert lane.scan_hardcoded_strings() == []


def test_comments_and_imports_are_not_scanned(studio):
    _, components, _ = studio
    component(components, "Toolbar.tsx",
              '// const a = "Save the project"\n'
              ' * const b = "Undo the change"\n'
              'import Thing from "./Some Component Path"\n')
    assert lane.scan_hardcoded_strings() == []


def test_test_files_and_ui_primitives_are_skipped(studio):
    _, components, _ = studio
    component(components, "Toolbar.test.tsx", 'const a = "Save the project"\n')
    component(components, "ui/button.tsx", 'const a = "Save the project"\n')
    assert lane.scan_hardcoded_strings() == []


def test_a_css_token_is_not_a_translatable_string(studio):
    _, components, _ = studio
    component(components, "Box.tsx", 'const display = "Flex"\n')
    assert lane.scan_hardcoded_strings() == []


def test_a_keyboard_event_key_is_waived(studio):
    _, components, _ = studio
    component(components, "Modal.tsx", 'if (e.key === "Escape") onClose()\n')
    assert lane.scan_hardcoded_strings() == []


def test_a_label_that_merely_starts_with_a_waived_identifier_is_still_reported(studio):
    """The waiver is an exact, case-sensitive match on the whole string."""
    _, components, _ = studio
    component(components, "Field.jsx", '<input placeholder="Enter your project name" />\n')
    issues = lane.scan_hardcoded_strings()
    assert len(issues) == 1
    assert "Enter your project name" in issues[0]


def test_findings_are_sorted_so_the_count_is_stable(studio):
    _, components, _ = studio
    component(components, "Zeta.tsx", 'const a = "Save the project"\n')
    component(components, "Alpha.tsx", 'const b = "Undo the change"\n')
    issues = lane.scan_hardcoded_strings()
    assert len(issues) == 2
    assert issues == sorted(issues)


def test_a_missing_components_directory_is_a_warning_not_a_crash(studio, monkeypatch, capsys):
    _, components, _ = studio
    monkeypatch.setattr(lane, "COMPONENTS_DIR", components / "absent")
    assert lane.scan_hardcoded_strings() == []
    assert "Components directory not found" in capsys.readouterr().out


# --- the ratchet -----------------------------------------------------------

def test_the_standing_backlog_does_not_block(studio, capsys):
    _, components, baseline = studio
    component(components, "Toolbar.tsx",
              'const a = "Save the project"\nconst b = "Undo the change"\n')
    set_baseline(baseline, 2)
    assert lane.check_hardcoded_strings() is True
    assert "2 found (baseline 2)" in capsys.readouterr().out


def test_adding_to_the_backlog_fails(studio, capsys):
    _, components, baseline = studio
    component(components, "Toolbar.tsx",
              'const a = "Save the project"\nconst b = "Undo the change"\n')
    set_baseline(baseline, 1)
    assert lane.check_hardcoded_strings() is False
    out = capsys.readouterr().out
    assert "hardcoded strings rose 1 -> 2" in out
    assert "ALLOWED_WEB_API_IDENTIFIERS" in out  # the fix is in the message


def test_fixing_strings_passes_and_asks_for_the_ratchet_to_be_lowered(studio, capsys):
    _, components, baseline = studio
    component(components, "Toolbar.tsx", 'const heading = t("editor.save")\n')
    set_baseline(baseline, 3)
    assert lane.check_hardcoded_strings() is True
    out = capsys.readouterr().out
    assert "fell 3 -> 0" in out
    assert "--update-baseline" in out


def test_the_findings_are_always_printed_so_the_ratchet_is_readable(studio, capsys):
    _, components, baseline = studio
    component(components, "Toolbar.tsx", 'const a = "Save the project"\n')
    set_baseline(baseline, 1)
    lane.check_hardcoded_strings()
    assert "Save the project" in capsys.readouterr().out


def test_a_regression_does_not_bury_the_summary(studio, capsys):
    _, components, baseline = studio
    component(components, "Big.tsx", "".join(
        f'const label{n} = "Label number here"\n' for n in range(60)))
    set_baseline(baseline, 0)
    assert lane.check_hardcoded_strings() is False
    out = capsys.readouterr().out
    assert "... and 10 more" in out


def test_a_missing_baseline_ratchets_at_zero(studio, capsys):
    _, components, _ = studio
    component(components, "Toolbar.tsx", 'const a = "Save the project"\n')
    assert lane.check_hardcoded_strings() is False
    assert "ratcheting against 0" in capsys.readouterr().out


def test_a_malformed_baseline_fails_rather_than_defaulting(studio, capsys):
    """A broken ratchet file must not silently become 'no ceiling'."""
    _, _, baseline = studio
    baseline.write_text("{not json", encoding="utf-8")
    assert lane.read_baseline() is None
    assert lane.check_hardcoded_strings() is False
    assert "Malformed baseline" in capsys.readouterr().out


def test_a_baseline_without_the_expected_key_fails(studio):
    _, _, baseline = studio
    baseline.write_text(json.dumps({"strings": 4}), encoding="utf-8")
    assert lane.read_baseline() is None


def test_update_baseline_rewrites_the_ratchet_to_the_current_count(studio, capsys):
    _, components, baseline = studio
    component(components, "Toolbar.tsx", 'const a = "Save the project"\n')
    set_baseline(baseline, 9)
    assert lane.check_hardcoded_strings(update_baseline=True) is True
    assert json.loads(baseline.read_text(encoding="utf-8"))["hardcoded_strings"] == 1
    assert "baseline updated 9 -> 1" in capsys.readouterr().out


# --- the two checks together ----------------------------------------------

def test_main_passes_only_when_both_checks_pass(studio, capsys):
    locales, _components, baseline = studio
    locale(locales, "en", {"editor": {"save": "Save"}})
    locale(locales, "es", {"editor": {"save": "Guardar"}})
    set_baseline(baseline, 0)
    assert lane.main([]) == 0
    assert "All i18n checks passed" in capsys.readouterr().out


def test_main_fails_on_a_parity_break_even_with_a_clean_ratchet(studio):
    locales, _, baseline = studio
    locale(locales, "en", {"a": "A", "b": "B"})
    locale(locales, "es", {"a": "A"})
    set_baseline(baseline, 0)
    assert lane.main([]) == 1


def test_main_fails_on_a_ratchet_rise_even_with_clean_locales(studio):
    locales, components, baseline = studio
    locale(locales, "en", {"a": "A"})
    locale(locales, "es", {"a": "A"})
    component(components, "Toolbar.tsx", 'const a = "Save the project"\n')
    set_baseline(baseline, 0)
    assert lane.main([]) == 1


def test_update_baseline_does_not_paper_over_a_parity_break(studio):
    """--update-baseline is for the ratchet; the hard gate is not negotiable."""
    locales, _, baseline = studio
    locale(locales, "en", {"a": "A", "b": "B"})
    locale(locales, "es", {"a": "A"})
    set_baseline(baseline, 0)
    assert lane.main(["--update-baseline"]) == 1


# --- the committed baseline ------------------------------------------------

def test_the_committed_baseline_is_a_non_negative_integer():
    baseline = json.loads(lane.BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(baseline["hardcoded_strings"], int)
    assert baseline["hardcoded_strings"] >= 0
