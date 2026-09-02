"""The `changes` job decides what the rest of CI is allowed to skip.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_ci_changes_classification.py -q

Getting this wrong is expensive in one direction and dangerous in the other. Too
eager and a real code change skips the browser matrix, the app builds, the
backend suite and geometric parity — a merge that was never tested. Too timid
and every merge to main runs the full 22-job matrix twice, once for the merge
commit and once for deploy.yml's `deploy(yantra4d): update digests` push, which
touches only k8s/production/kustomization.yaml.

The safety property is that it fails CLOSED: only a filter that actually ran and
answered exactly "false" is allowed to skip anything. Everything else — the
step skipped, an unusable push base, an event that is neither pull_request nor
push, the action changing its contract — classifies as code. That rule lives in
shell inside the workflow, so this suite EXECUTES the real script out of
ci.yml rather than restating it, and pins the surrounding wiring (which events
the filter runs on, what it diffs against, what counts as no-code) by reading
the file.

Deliberately stdlib-and-regex only, like test_ruff_pin.py: the lane that runs
scripts/tests installs jsonschema and pytest, not PyYAML, and a guard that
skipped for want of a parser would be no guard at all.
"""
from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CI = REPO / ".github" / "workflows" / "ci.yml"
KUSTOMIZATION = "k8s/production/kustomization.yaml"
ZERO_SHA = "0" * 40


def workflow() -> str:
    return CI.read_text(encoding="utf-8")


def step(name: str) -> str:
    """The YAML block of the `changes` step with this name, up to the next step."""
    text = workflow()
    start = text.index(f"      - name: {name}\n")
    rest = text[start + 1:]
    end = rest.find("\n      - name: ")
    return text[start:start + 1 + (len(rest) if end == -1 else end)]


def script(name: str) -> str:
    """The shell of a step's `run: |` block, dedented and ready to execute."""
    block = step(name)
    body = block[block.index("        run: |\n") + len("        run: |\n"):]
    lines = []
    for line in body.splitlines():
        if line.strip() and not line.startswith("          "):
            break
        lines.append(line)
    return textwrap.dedent("\n".join(lines)) + "\n"


def run_step(name: str, tmp_path: Path, env: dict, cwd: Path | None = None):
    """Execute a step's shell the way the runner would, and read its outputs."""
    output = tmp_path / "github_output"
    summary = tmp_path / "github_summary"
    output.touch()
    summary.touch()
    result = subprocess.run(
        ["bash", "-c", script(name)],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin",
             "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary),
             **env},
        cwd=str(cwd or tmp_path), capture_output=True, text=True, check=False)
    outputs = dict(
        line.split("=", 1) for line in
        output.read_text(encoding="utf-8").splitlines() if "=" in line)
    return result, outputs, summary.read_text(encoding="utf-8")


def classify(tmp_path, event_name, filter_code):
    result, outputs, summary = run_step(
        "Classify", tmp_path,
        {"EVENT_NAME": event_name, "FILTER_CODE": filter_code})
    assert result.returncode == 0, result.stderr
    return outputs["code"], summary


# ──────────────────────────────────────────────────────────────────────────────
# the fail-closed rule, executed
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("event,filter_code,expected", [
    # The only two ways to skip anything.
    ("pull_request", "false", "false"),
    ("push", "false", "false"),
    # The filter ran and found code.
    ("pull_request", "true", "true"),
    ("push", "true", "true"),
    # The filter did not run, or did not answer.
    ("pull_request", "", "true"),
    ("push", "", "true"),
    # The action changed its contract and said something else.
    ("push", "maybe", "true"),
    ("push", "False", "true"),
    ("push", "0", "true"),
    # Events that are classified by nothing.
    ("workflow_dispatch", "false", "true"),
    ("schedule", "false", "true"),
    ("", "false", "true"),
])
def test_classification(tmp_path, event, filter_code, expected):
    code, _ = classify(tmp_path, event, filter_code)
    assert code == expected


def test_a_skip_says_why_in_the_job_summary(tmp_path):
    _, summary = classify(tmp_path, "push", "false")
    assert KUSTOMIZATION in summary
    assert "skipped" in summary
    assert "still run" in summary


def test_a_full_run_says_so_in_the_job_summary(tmp_path):
    _, summary = classify(tmp_path, "push", "true")
    assert "full CI matrix runs" in summary


# ──────────────────────────────────────────────────────────────────────────────
# the push base guard, executed against a real repository
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def repo(tmp_path):
    """Two commits, so there is a reachable `before` to diff against."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=str(tmp_path),
                              capture_output=True, text=True, check=True).stdout.strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "ci@example.invalid")
    git("config", "user.name", "ci")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "first")
    first = git("rev-parse", "HEAD")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    git("commit", "-aqm", "second")
    return tmp_path, first


def resolve(repo, tmp_path, before):
    result, outputs, summary = run_step(
        "Resolve the push base", tmp_path, {"BEFORE": before}, cwd=repo)
    assert result.returncode == 0, result.stderr
    return outputs["usable"], summary


def test_a_reachable_before_is_usable(repo, tmp_path):
    directory, first = repo
    usable, _ = resolve(directory, tmp_path, first)
    assert usable == "true"


def test_a_new_branch_reports_an_all_zero_before_and_is_refused(repo, tmp_path):
    """GitHub sends 40 zeros for the first push to a branch."""
    directory, _ = repo
    usable, summary = resolve(directory, tmp_path, ZERO_SHA)
    assert usable == "false"
    assert "classifying as code" in summary


def test_a_before_that_is_no_longer_reachable_is_refused(repo, tmp_path):
    """A force push can name a commit this checkout does not contain."""
    directory, _ = repo
    usable, _ = resolve(directory, tmp_path, "d" * 40)
    assert usable == "false"


def test_an_empty_before_is_refused(repo, tmp_path):
    directory, _ = repo
    usable, _ = resolve(directory, tmp_path, "")
    assert usable == "false"


def test_the_guard_does_not_fail_the_job_when_it_refuses(repo, tmp_path):
    """It must classify as code, not blow up the run under `set -e`."""
    directory, _ = repo
    result, _, _ = run_step("Resolve the push base", tmp_path,
                            {"BEFORE": ZERO_SHA}, cwd=directory)
    assert result.returncode == 0


# ──────────────────────────────────────────────────────────────────────────────
# the wiring the executed scripts sit in
# ──────────────────────────────────────────────────────────────────────────────

def test_the_filter_runs_on_pull_requests_and_on_pushes():
    condition = step("Filter changed paths")
    assert "github.event_name == 'pull_request'" in condition
    assert "github.event_name == 'push'" in condition


def test_a_push_only_reaches_the_filter_through_the_base_guard():
    assert "steps.base.outputs.usable == 'true'" in step("Filter changed paths")


def test_a_push_is_diffed_against_the_commit_before_it():
    assert "base: ${{ github.event.before }}" in step("Filter changed paths")


def test_the_pull_request_path_still_needs_no_checkout():
    """The API path must not silently fall back to a diff it cannot compute."""
    checkout = step("Check out for the push diff")
    assert "if: github.event_name == 'push'" in checkout
    assert "fetch-depth: 0" in checkout


def test_the_predicate_quantifier_is_still_every():
    """With the default `some`, '**' matches everything and the negations do nothing."""
    assert "predicate-quantifier: 'every'" in step("Filter changed paths")


def test_the_deploy_digest_bump_is_not_code():
    assert f"- '!{KUSTOMIZATION}'" in step("Filter changed paths")


def test_the_digest_bump_path_is_the_one_deploy_actually_writes():
    """A negation for a path nothing writes would silently do nothing."""
    deploy = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert f"git add {KUSTOMIZATION}" in deploy
    assert (REPO / KUSTOMIZATION).is_file()


@pytest.mark.parametrize("pattern", [
    "'**'", "'!**/*.md'", "'!docs/**'", "'!apps/docs/**'",
    "'!runbooks/**'", "'!.github/*.md'",
])
def test_the_existing_no_code_patterns_are_intact(pattern):
    assert f"- {pattern}" in step("Filter changed paths")


def test_no_job_that_can_be_skipped_reads_the_digest_bump():
    """The premise of excluding it: the gated jobs never look at it."""
    text = workflow()
    gated = text[text.index("\n  studio:\n"):]
    for needle in ("kustomization", "k8s/", "infra/"):
        assert needle not in gated, f"a gated job references {needle!r}"


def test_the_action_stays_pinned_to_a_commit():
    assert re.search(r"uses: dorny/paths-filter@[0-9a-f]{40} # v3\.0\.4",
                     step("Filter changed paths"))
