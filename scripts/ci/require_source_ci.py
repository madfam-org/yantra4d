"""Refuse publication unless current main has successful exact-source CI.

workflow_run uses the default-branch SHA, which need not be the triggering CI
SHA. Compare both before using any build credentials. No CI artifacts are read.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def require_source_ci(source, repository, ref, event_name, event, get):
    if not re.fullmatch(r"[0-9a-f]{40}", source) or ref != "refs/heads/main":
        raise ValueError("Publication requires an exact source SHA on main")
    trigger_id = None
    if event_name == "workflow_run":
        trigger = event.get("workflow_run", {})
        if (trigger.get("event") != "push" or trigger.get("head_branch") != "main"
                or trigger.get("head_sha") != source
                or trigger.get("head_repository", {}).get("full_name") != repository
                or trigger.get("conclusion") != "success"):
            raise ValueError("CI trigger is untrusted, unsuccessful, or no longer the publication source")
        trigger_id = trigger.get("id")
        if type(trigger_id) is not int or trigger_id <= 0:
            raise ValueError("Missing CI trigger identity")
    elif event_name != "workflow_dispatch":
        raise ValueError("Publication requires completed CI or a gated manual dispatch")

    prefix = f"repos/{repository}"
    current = get(f"{prefix}/git/ref/heads/main")
    if current.get("object", {}).get("sha") != source:
        raise ValueError("Main changed; publish its accepted source instead")
    # Select locally: branch-filtered workflow history has omitted live runs.
    history = get(f"{prefix}/actions/workflows/ci.yml/runs?per_page=100")
    runs = [r for r in history.get("workflow_runs", [])
            if r.get("head_sha") == source and r.get("head_branch") == "main"
            and r.get("event") == "push"]
    if not runs:
        raise ValueError("No main CI run found for the publication source")
    latest_id = max(runs, key=lambda r: r["id"])["id"]
    if trigger_id is not None and trigger_id != latest_id:
        raise ValueError("A newer CI run superseded this trigger")
    trigger_id = latest_id
    run = get(f"{prefix}/actions/runs/{trigger_id}")
    if (run.get("head_sha") != source or run.get("head_branch") != "main"
            or run.get("event") != "push" or run.get("path") != ".github/workflows/ci.yml"
            or run.get("head_repository", {}).get("full_name") != repository
            or run.get("status") != "completed" or run.get("conclusion") != "success"):
        raise ValueError("Exact-source main CI has not passed")
    jobs = get(f"{prefix}/actions/runs/{trigger_id}/jobs?filter=latest&per_page=100")
    # The required aggregate is authoritative; absent/truncated evidence refuses.
    aggregate = [j for j in jobs.get("jobs", []) if j.get("name") == "ci-success"]
    if len(aggregate) != 1 or aggregate[0].get("conclusion") != "success":
        raise ValueError("Required ci-success aggregate has not passed")
    return trigger_id


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("Missing read-only Actions API token")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")

    def get(path):
        request = urllib.request.Request(f"{api}/{path}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    source = os.environ["GITHUB_SHA"]
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual != source:
        raise ValueError("Checkout does not match publication source")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    run_id = require_source_ci(source, os.environ["GITHUB_REPOSITORY"],
                              os.environ["GITHUB_REF"], os.environ["GITHUB_EVENT_NAME"], event, get)
    print(f"Accepted main CI {run_id} for source {source}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        # Never print response bodies or request headers (which carry auth).
        print(f"Source CI gate refused publication: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
