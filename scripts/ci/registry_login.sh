#!/usr/bin/env bash
# =============================================================================
# scripts/ci/registry_login.sh
#
# Logs Docker in to one container registry, retrying a transient failure.
#
# Why this is not `docker/login-action@v3`: the action has no retry of its own,
# so one transient network failure at login kills a whole build job — and
# because deploy.yml's `commit-digests` job needs all four builds, it kills the
# deploy. Run 33633417615 (main @ 3275f3b6) was lost that way twice on
# 2026-09-02, both times on `net/http: TLS handshake timeout` reaching GHCR,
# while the other build jobs logged in to the same registry seconds later. Each
# failure was about ten seconds long and the Docker Hub login moments earlier
# had succeeded, so the runner's egress was up, just slow.
#
# The credentials, the transport and the ordering are exactly what the action
# used: the password goes in on stdin (never argv, never the environment of the
# `docker` process), tracing is off for the whole body, and nothing is echoed.
# deploy.yml still runs its own `docker logout` in an `if: always()` step,
# mirroring the action's post step.
#
# Environment:
#   REGISTRY_HOST      required — e.g. docker.io, ghcr.io
#   REGISTRY_USER      required — the account to authenticate as
#   REGISTRY_PASSWORD  required — token or password; read from the environment
#                                 and piped to stdin, never passed as an argument
#   REGISTRY_LOGIN_ATTEMPTS   optional — defaults to 5
#   REGISTRY_LOGIN_BACKOFF_S  optional — defaults to 10; attempt N waits N × this
#
# Output:
#   stdout/stderr  whatever `docker login` says, plus one ::warning:: per retry
#                  and one ::error:: when every attempt is spent. The password
#                  is never printed on any path.
#
# Exit codes:
#   0  logged in
#   1  every attempt failed — the deploy cannot push or pull
#   2  not configured (a required variable is missing or empty) — a CI wiring
#      bug, not a network problem. Reported in zero seconds instead of after
#      five doomed attempts: an unset `secrets.*` arrives here as an EMPTY
#      string, not as an unset variable, so `set -u` never sees it.
#
# The caller must treat every non-zero exit as fatal. A build that proceeds
# without a login pushes nothing and pins no digest, which is the failure this
# script exists to make loud.
# =============================================================================

set -euo pipefail
# No tracing anywhere below, whatever the caller set: a traced `printf` of the
# password would put the secret in the log even though it never reaches argv.
set +x

readonly ATTEMPTS="${REGISTRY_LOGIN_ATTEMPTS:-5}"
readonly BACKOFF_S="${REGISTRY_LOGIN_BACKOFF_S:-10}"

for required in REGISTRY_HOST REGISTRY_USER REGISTRY_PASSWORD; do
  if [ -z "${!required:-}" ]; then
    echo "::error::${required} is not set; cannot log in to a container registry." >&2
    exit 2
  fi
done

attempt=1
while [ "${attempt}" -le "${ATTEMPTS}" ]; do
  if printf '%s' "${REGISTRY_PASSWORD}" \
    | docker login "${REGISTRY_HOST}" -u "${REGISTRY_USER}" --password-stdin; then
    exit 0
  fi
  if [ "${attempt}" -lt "${ATTEMPTS}" ]; then
    wait_s=$((attempt * BACKOFF_S))
    echo "::warning::login to ${REGISTRY_HOST} failed (attempt ${attempt} of ${ATTEMPTS}); retrying in ${wait_s}s..."
    sleep "${wait_s}"
  fi
  attempt=$((attempt + 1))
done

echo "::error::login to ${REGISTRY_HOST} failed ${ATTEMPTS} times; the deploy cannot push or pull."
exit 1
