#!/usr/bin/env bash
# =============================================================================
# scripts/ci/npm_audit_gate.sh
# Runs `npm audit` as a blocking gate, and tells an outage from a finding.
#
# Why this is not a bare `npm audit` step: on 2026-09-19, during npm's own
# maintenance window (17:00–19:00 UTC), the registry's bulk advisory endpoint
# answered 503 and the fallback quick endpoint answered 400 ("this endpoint is
# being retired"). `npm audit` exits 1 on that exactly as it does on a high
# severity finding, so every landing, studio and admin job in the org went red
# for the duration (runs 35458078693 and siblings) with no dependency changed
# and no vulnerability found. A registry outage is not a vulnerability.
#
# So: run the audit; on a clean tree exit 0; on a REAL verdict (vulnerabilities
# reported, or any error that is not the endpoint) fail closed with npm's own
# exit code; on the endpoint-error class retry with a backoff, and when every
# attempt is spent, print one loud ::warning:: and exit 0 — the run is NOT
# audited, which the warning says, and the next push audits again. Nothing
# about a finding is ever softened.
#
# Arguments: passed straight to `npm audit` (e.g. --audit-level=high --omit=dev
#            --legacy-peer-deps).
# Environment:
#   NPM_AUDIT_ATTEMPTS   optional — defaults to 3
#   NPM_AUDIT_BACKOFF_S  optional — defaults to 10; attempt N waits N × this
# Exit:
#   0  audit clean, or the endpoint stayed unreachable (warned, not audited)
#   n  npm's exit code on any real verdict (findings, wiring, permissions)
# =============================================================================

set -uo pipefail

ATTEMPTS="${NPM_AUDIT_ATTEMPTS:-3}"
BACKOFF_S="${NPM_AUDIT_BACKOFF_S:-10}"

# The endpoint-error class: npm's own summary line for it, its ENOAUDIT code,
# the transport errors underneath, and 5xx codes from the registry. A finding
# never prints any of these — it prints "# npm audit report" and a count.
is_endpoint_error() {
  printf '%s' "$1" | grep -qiE \
    'audit endpoint returned an error|ENOAUDIT|E50[0-9]|ETIMEDOUT|ECONNRESET|ECONNREFUSED|EAI_AGAIN|ENOTFOUND|socket hang up|network request to .* failed'
}

attempt=1
while :; do
  output="$(npm audit "$@" 2>&1)"
  status=$?
  printf '%s\n' "${output}"
  if [ "${status}" -eq 0 ]; then
    exit 0
  fi
  if ! is_endpoint_error "${output}"; then
    # Vulnerabilities, or something wrong with the tree or the token: the
    # verdict stands, exactly as a bare `npm audit` would have ended the job.
    exit "${status}"
  fi
  if [ "${attempt}" -lt "${ATTEMPTS}" ]; then
    wait_s=$((attempt * BACKOFF_S))
    echo "::warning::npm audit could not reach the advisory endpoint (attempt ${attempt} of ${ATTEMPTS}); retrying in ${wait_s}s..."
    sleep "${wait_s}"
    attempt=$((attempt + 1))
    continue
  fi
  echo "::warning title=npm audit unavailable::the registry's advisory endpoint failed ${ATTEMPTS} times; no vulnerability data came back, so THIS RUN IS NOT AUDITED. Re-run the job once npm is back (status.npmjs.org), or rely on the next push."
  exit 0
done
