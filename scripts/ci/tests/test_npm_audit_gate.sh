#!/usr/bin/env bash
# =============================================================================
# scripts/ci/tests/test_npm_audit_gate.sh
#
# Tests for scripts/ci/npm_audit_gate.sh, in the same plain-bash shape as
# test_registry_login.sh: no bats, no network, nothing sleeps. Two stubs go at
# the front of PATH:
#
#   npm    plays one of four registries, chosen by FAKE_NPM_MODE:
#            clean    exit 0, "found 0 vulnerabilities"
#            vulns    exit 1, an audit report with 2 high severity findings
#            outage   exit 1, the 2026-09-19 transcript (bulk 503, quick 400,
#                     "audit endpoint returned an error") — for the first
#                     FAKE_NPM_OUTAGES calls, then clean
#            broken   exit 1, an error that is NOT the endpoint (ELOCKVERIFY)
#          and records every argv it was handed.
#   sleep  records the duration and returns at once, so the 10/20 backoff is
#          asserted as data rather than waited out.
#
# Usage:  ./scripts/ci/tests/test_npm_audit_gate.sh
# Exit 0 when every case passes; 1 if any assertion failed.
# =============================================================================

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TESTS_DIR
readonly SCRIPT_UNDER_TEST="${TESTS_DIR}/../npm_audit_gate.sh"

PASSED=0
FAILED=0

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
mkdir -p "${WORK}/bin"

cat > "${WORK}/bin/npm" <<'STUB'
#!/usr/bin/env bash
count_file="${FAKE_STATE}/npm-calls"
count=$(( $(cat "${count_file}" 2>/dev/null || echo 0) + 1 ))
echo "${count}" > "${count_file}"
printf '%s\n' "$*" >> "${FAKE_STATE}/npm-argv"
mode="${FAKE_NPM_MODE:-clean}"
if [ "${mode}" = "outage" ] && [ "${count}" -gt "${FAKE_NPM_OUTAGES:-1}" ]; then mode=clean; fi
case "${mode}" in
  clean)
    echo "found 0 vulnerabilities"; exit 0 ;;
  vulns)
    echo "# npm audit report"; echo; echo "lodash  <4.17.21"; echo "Severity: high"; echo; echo "2 high severity vulnerabilities"; exit 1 ;;
  outage)
    echo "npm notice This endpoint is being retired. Use the bulk advisory endpoint instead."
    echo "npm warn audit 400 Bad Request - POST https://registry.npmjs.org/-/npm/v1/security/audits/quick - Bad Request"
    echo "npm error audit endpoint returned an error"; exit 1 ;;
  broken)
    echo "npm error code ELOCKVERIFY"; echo "npm error Errors were found in your package-lock.json"; exit 1 ;;
esac
STUB
cat > "${WORK}/bin/sleep" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "${FAKE_STATE}/sleeps"
STUB
chmod +x "${WORK}/bin/npm" "${WORK}/bin/sleep"

ok()   { PASSED=$((PASSED + 1)); printf '  ok   %s\n' "$1"; }
nope() { FAILED=$((FAILED + 1)); printf '  FAIL %s\n     %s\n' "$1" "$2"; }

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "${expected}" = "${actual}" ]; then ok "${label}"; else nope "${label}" "expected '${expected}', got '${actual}'"; fi
}
assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if printf '%s' "${haystack}" | grep -qF -- "${needle}"; then ok "${label}"; else nope "${label}" "did not find '${needle}'"; fi
}
assert_absent() {
  local label="$1" needle="$2" haystack="$3"
  if printf '%s' "${haystack}" | grep -qF -- "${needle}"; then nope "${label}" "found '${needle}'"; else ok "${label}"; fi
}

# run_case <mode> <outages> <attempts> [audit args...] → sets OUT, STATUS, CALLS, SLEEPS, ARGV
run_case() {
  local mode="$1" outages="$2" attempts="$3"; shift 3
  export FAKE_STATE="${WORK}/state-$RANDOM$RANDOM"
  mkdir -p "${FAKE_STATE}"
  OUT="$(PATH="${WORK}/bin:${PATH}" FAKE_NPM_MODE="${mode}" FAKE_NPM_OUTAGES="${outages}" NPM_AUDIT_ATTEMPTS="${attempts}" NPM_AUDIT_BACKOFF_S=10 bash "${SCRIPT_UNDER_TEST}" "$@" 2>&1 </dev/null)"
  STATUS=$?
  CALLS="$(cat "${FAKE_STATE}/npm-calls" 2>/dev/null || echo 0)"
  SLEEPS=""
  if [ -f "${FAKE_STATE}/sleeps" ]; then SLEEPS="$(tr '\n' ' ' < "${FAKE_STATE}/sleeps" | sed 's/ $//')"; fi
  ARGV="$(cat "${FAKE_STATE}/npm-argv" 2>/dev/null | head -1)"
}

echo "case: clean tree"
run_case clean 0 3 --audit-level=high --omit=dev
assert_eq "exits 0" 0 "${STATUS}"
assert_eq "npm called once" 1 "${CALLS}"
assert_eq "arguments pass through" "audit --audit-level=high --omit=dev" "${ARGV}"
assert_eq "no sleep" "" "${SLEEPS}"

echo "case: vulnerabilities found — fails closed, no retry"
run_case vulns 0 3 --audit-level=high --omit=dev --legacy-peer-deps
assert_eq "exits with npm's code" 1 "${STATUS}"
assert_eq "npm called once" 1 "${CALLS}"
assert_eq "no sleep" "" "${SLEEPS}"
assert_contains "the report is in the output" "2 high severity vulnerabilities" "${OUT}"
assert_absent "no outage warning" "npm audit unavailable" "${OUT}"
assert_eq "legacy-peer-deps passes through" "audit --audit-level=high --omit=dev --legacy-peer-deps" "${ARGV}"

echo "case: endpoint down once, then back"
run_case outage 1 3 --audit-level=high --omit=dev
assert_eq "exits 0" 0 "${STATUS}"
assert_eq "npm called twice" 2 "${CALLS}"
assert_eq "one backoff of 10s" "10" "${SLEEPS}"
assert_contains "retry is announced" "retrying in 10s" "${OUT}"
assert_absent "no unavailable warning after a recovery" "npm audit unavailable" "${OUT}"

echo "case: endpoint down for every attempt — warns loudly, does not fail the job"
run_case outage 9 3 --audit-level=high --omit=dev
assert_eq "exits 0" 0 "${STATUS}"
assert_eq "npm called three times" 3 "${CALLS}"
assert_eq "backoff 10 then 20" "10 20" "${SLEEPS}"
assert_contains "the loud warning" "::warning title=npm audit unavailable::" "${OUT}"
assert_contains "says the run is not audited" "NOT AUDITED" "${OUT}"

echo "case: a single attempt"
run_case outage 9 1 --audit-level=high --omit=dev
assert_eq "exits 0" 0 "${STATUS}"
assert_eq "npm called once" 1 "${CALLS}"
assert_eq "no sleep" "" "${SLEEPS}"

echo "case: an error that is not the endpoint — fails closed"
run_case broken 0 3 --audit-level=high --omit=dev
assert_eq "exits with npm's code" 1 "${STATUS}"
assert_eq "npm called once" 1 "${CALLS}"
assert_eq "no sleep" "" "${SLEEPS}"
assert_absent "no outage warning" "npm audit unavailable" "${OUT}"

echo
echo "passed ${PASSED}, failed ${FAILED}"
[ "${FAILED}" -eq 0 ]
