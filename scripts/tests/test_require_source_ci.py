"""Publication must not mistake green PR/old-source CI for accepted main."""
import copy
import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('source_ci', ROOT/'scripts/ci/require_source_ci.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
SHA = 'a' * 40
REPO = 'example/project'
RUN = {'id': 41, 'head_sha': SHA, 'head_branch': 'main', 'event': 'push',
       'path': '.github/workflows/ci.yml', 'head_repository': {'full_name': REPO},
       'status': 'completed', 'conclusion': 'success'}


@pytest.fixture
def evidence():
    return {'main': SHA, 'run': copy.deepcopy(RUN), 'history': [copy.deepcopy(RUN)],
            'jobs': [{'name': 'ci-success', 'conclusion': 'success'}]}


def check(evidence, event_name='workflow_dispatch', event=None, ref='refs/heads/main'):
    def get(path):
        if path.endswith('/git/ref/heads/main'):
            return {'object': {'sha': evidence['main']}}
        if '/workflows/' in path:
            return {'workflow_runs': evidence['history']}
        if '/jobs?' in path:
            return {'jobs': evidence['jobs']}
        assert path.endswith('/actions/runs/41'), path
        return evidence['run']
    return gate.require_source_ci(SHA, REPO, ref, event_name, event or {}, get)


def test_manual_publication_accepts_exact_main(evidence):
    assert check(evidence) == 41


def test_automatic_publication_accepts_trusted_completed_ci(evidence):
    assert check(evidence, 'workflow_run', {'workflow_run': RUN}) == 41


@pytest.mark.parametrize('key,value', [
    ('head_sha', 'b'*40), ('head_branch', 'feature'), ('event', 'pull_request'),
    ('path', '.github/workflows/validate.yml'), ('status', 'in_progress'),
    ('conclusion', 'failure'), ('conclusion', 'cancelled'),
    ('head_repository', {'full_name': 'attacker/fork'}),
])
def test_incorrect_or_unaccepted_ci_is_refused(evidence, key, value):
    evidence['run'][key] = value
    with pytest.raises(ValueError):
        check(evidence)


@pytest.mark.parametrize('key,value', [
    ('head_sha', 'b'*40), ('head_branch', 'feature'), ('event', 'pull_request'),
    ('conclusion', 'failure'), ('head_repository', {'full_name': 'attacker/fork'}),
    ('id', None),
])
def test_untrusted_or_stale_trigger_is_refused(evidence, key, value):
    trigger = copy.deepcopy(RUN)
    trigger[key] = value
    with pytest.raises(ValueError):
        check(evidence, 'workflow_run', {'workflow_run': trigger})


def test_changed_main_is_refused(evidence):
    evidence['main'] = 'b'*40
    with pytest.raises(ValueError, match='Main changed'):
        check(evidence)


def test_no_ci_evidence_is_not_permission(evidence):
    evidence['history'] = []
    with pytest.raises(ValueError, match='No main CI'):
        check(evidence)


@pytest.mark.parametrize('jobs', [[], [{'name': 'validate', 'conclusion': 'success'}],
    [{'name': 'ci-success', 'conclusion': 'skipped'}],
    [{'name': 'ci-success', 'conclusion': 'failure'}]])
def test_missing_or_unsuccessful_aggregate_is_refused(evidence, jobs):
    evidence['jobs'] = jobs
    with pytest.raises(ValueError, match='aggregate'):
        check(evidence)


def test_latest_run_must_pass_even_if_older_run_passed(evidence):
    evidence['history'].append(dict(RUN, id=40))
    evidence['run']['conclusion'] = 'failure'
    with pytest.raises(ValueError):
        check(evidence)


@pytest.mark.parametrize('event,ref', [('push','refs/heads/main'),
                                     ('workflow_dispatch','refs/heads/feature')])
def test_unsupported_dispatch_is_refused(evidence, event, ref):
    with pytest.raises(ValueError):
        check(evidence, event_name=event, ref=ref)


def test_workflow_gates_all_builds_and_refuses_stale_pin():
    workflow = yaml.safe_load((ROOT/'.github/workflows/deploy.yml').read_text())
    triggers = workflow.get('on', workflow.get(True))
    assert 'push' not in triggers
    assert triggers['workflow_run'] == {'workflows': ['CI'], 'types': ['completed'], 'branches': ['main']}
    jobs = workflow['jobs']
    assert 'if' not in jobs['detect-changes'], 'rejected triggers must fail, not create a green baseline'
    steps = jobs['detect-changes']['steps']
    gate_index = next(i for i, s in enumerate(steps) if s.get('run') == 'python3 scripts/ci/require_source_ci.py')
    assert gate_index < next(i for i,s in enumerate(steps) if s.get('id') == 'base')
    assert jobs['detect-changes']['permissions']['actions'] == 'read'
    for name in ['backend','studio','landing','admin']:
        assert jobs['build-'+name]['needs'] == 'detect-changes'
    pin = next(s['run'] for s in jobs['commit-digests']['steps'] if s.get('name') == 'Commit image digests')
    assert pin.index('!= "$GITHUB_SHA"') < pin.index('git reset --hard origin/main')


@pytest.mark.parametrize('main,expected', [(SHA, 0), ('b'*40, 1)])
def test_actual_pin_shell_never_writes_after_source_changes(tmp_path, main, expected):
    workflow = yaml.safe_load((ROOT/'.github/workflows/deploy.yml').read_text())
    command = next(s['run'] for s in workflow['jobs']['commit-digests']['steps']
                   if s.get('name') == 'Commit image digests')
    command = re.sub(r'\$\{\{.*?\}\}', '', command)
    binary = tmp_path/'git'
    binary.write_text('#!/bin/sh\nprintf "%s\n" "$*" >> "$CALL_LOG"\n'
                      'if [ "$1" = rev-parse ]; then printf "%s\n" "$MAIN_SHA"; fi\n')
    binary.chmod(0o755)
    (tmp_path/'k8s/production').mkdir(parents=True)
    log = tmp_path/'calls'
    result = subprocess.run(['bash', '-e', '-c', command], cwd=tmp_path,
                            env=dict(os.environ, PATH=str(tmp_path)+os.pathsep+os.environ['PATH'],
                                     GITHUB_SHA=SHA, MAIN_SHA=main, CALL_LOG=str(log)),
                            capture_output=True, text=True, check=False)
    assert result.returncode == expected, result.stderr
    calls = log.read_text()
    if expected:
        assert 'reset' not in calls and 'add ' not in calls and 'push ' not in calls
    else:
        assert 'reset --hard origin/main' in calls and 'add k8s/' in calls


def test_old_successful_trigger_cannot_override_newer_run(evidence):
    evidence['history'].append(dict(RUN, id=42, conclusion='failure'))
    with pytest.raises(ValueError, match='superseded'):
        check(evidence, 'workflow_run', {'workflow_run': RUN})


def test_api_failure_never_accepts_source():
    def unavailable(_):
        raise OSError('unavailable')
    with pytest.raises(OSError):
        gate.require_source_ci(SHA, REPO, 'refs/heads/main', 'workflow_dispatch', {}, unavailable)
