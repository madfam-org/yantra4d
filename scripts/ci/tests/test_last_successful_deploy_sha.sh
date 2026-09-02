#!/usr/bin/env bash
# =============================================================================
# scripts/ci/tests/test_last_successful_deploy_sha.sh
#
# Tests for scripts/ci/last_successful_deploy_sha.sh, driven by recorded GitHub
# API responses in tests/fixtures/. The repo has no bats, so this is a plain
# bash harness: no dependencies beyond what the script itself needs.
#
# The GitHub API is never contacted. A stub `curl` is placed at the front of
# PATH; it replays a fixture with a chosen HTTP status (or a chosen transport
# failure) and records the argv the script passed, so the request itself is
# asserted too.
#
# Usage:
#   ./scripts/ci/tests/test_last_successful_deploy_sha.sh
#
# Exit 0 when every case passes; 1 on the first failing assertion count.
# =============================================================================

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TESTS_DIR
readonly FIXTURES_DIR="${TESTS_DIR}/fixtures"
readonly SCRIPT_UNDER_TEST="${TESTS_DIR}/../last_successful_deploy_sha.sh"

# The exit-code contract the workflow depends on. Anything other than RESOLVED
# means "build every service".
readonly EXIT_RESOLVED=0
readonly EXIT_NOT_CONFIGURED=2
readonly EXIT_BUILD_EVERYTHING=3

readonly EXPECTED_SHA="61e45153051a0161a3a8c7f6ef002b8967253a61"

PASSED=0
FAILED=0

TMP_ROOT="$(mktemp -d)"
readonly TMP_ROOT
cleanup() { rm -rf "${TMP_ROOT}"; }
trap cleanup EXIT

# ---- stub curl ---------------------------------------------------------------
readonly STUB_BIN="${TMP_ROOT}/bin"
mkdir -p "${STUB_BIN}"
cat > "${STUB_BIN}/curl" <<'STUB'
#!/usr/bin/env bash
# Replays a recorded response in place of the real curl. Reproduces exactly
# what `curl -s -w '\n%{http_code}'` writes: the body, a newline, the status.
printf '%s\n' "$*" > "${FAKE_CURL_ARGV}"
if [ "${FAKE_CURL_EXIT:-0}" -ne 0 ]; then
  echo "curl: (${FAKE_CURL_EXIT}) simulated transport failure" >&2
  exit "${FAKE_CURL_EXIT}"
fi
cat "${FAKE_CURL_BODY}"
printf '\n%s' "${FAKE_CURL_HTTP_CODE:-200}"
STUB
chmod +x "${STUB_BIN}/curl"

# ---- harness -----------------------------------------------------------------
# run_case <fixture-file> <http-code> <curl-exit> [extra env assignments...]
# Sets: STATUS, STDOUT, STDERR, ARGV
run_case() {
  local fixture="$1" http_code="$2" curl_exit="$3"
  shift 3

  local out_file="${TMP_ROOT}/stdout" err_file="${TMP_ROOT}/stderr"
  local argv_file="${TMP_ROOT}/argv"
  : > "${argv_file}"

  STATUS=0
  env -i \
    PATH="${STUB_BIN}:${PATH}" \
    HOME="${HOME:-/root}" \
    FAKE_CURL_BODY="${fixture}" \
    FAKE_CURL_HTTP_CODE="${http_code}" \
    FAKE_CURL_EXIT="${curl_exit}" \
    FAKE_CURL_ARGV="${argv_file}" \
    GITHUB_TOKEN="fixture-token-not-a-real-secret" \
    GITHUB_REPOSITORY="madfam-org/yantra4d" \
    "$@" \
    bash "${SCRIPT_UNDER_TEST}" >"${out_file}" 2>"${err_file}" || STATUS=$?

  STDOUT="$(cat "${out_file}")"
  STDERR="$(cat "${err_file}")"
  ARGV="$(cat "${argv_file}")"
}

ok()   { PASSED=$((PASSED + 1)); printf '  ok   %s\n' "$1"; }
nope() { FAILED=$((FAILED + 1)); printf '  FAIL %s\n     %s\n' "$1" "$2"; }

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "${expected}" = "${actual}" ]; then
    ok "${label}"
  else
    nope "${label}" "expected [${expected}], got [${actual}]"
  fi
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  case "${haystack}" in
    *"${needle}"*) ok "${label}" ;;
    *) nope "${label}" "expected to find [${needle}] in [${haystack}]" ;;
  esac
}

# ---- cases -------------------------------------------------------------------

echo "success: a successful run resolves to its head SHA"
run_case "${FIXTURES_DIR}/runs_success.json" 200 0
assert_eq "exit code is 0 (resolved)" "${EXIT_RESOLVED}" "${STATUS}"
assert_eq "stdout is the head SHA and nothing else" "${EXPECTED_SHA}" "${STDOUT}"

echo "success: the request asks the API the right question"
assert_contains "queries the deploy workflow's runs" \
  "/repos/madfam-org/yantra4d/actions/workflows/deploy.yml/runs" "${ARGV}"
assert_contains "filters to the deploy branch" "branch=main" "${ARGV}"
assert_contains "filters to successful runs" "status=success" "${ARGV}"
assert_contains "asks for one run" "per_page=1" "${ARGV}"
assert_contains "sends the bearer token" "Authorization: Bearer" "${ARGV}"
assert_contains "pins the API version" "X-GitHub-Api-Version" "${ARGV}"

echo "empty: no successful run yet (first deploy) builds everything"
run_case "${FIXTURES_DIR}/runs_empty.json" 200 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"
assert_contains "says why on stderr" "no successful run" "${STDERR}"
assert_contains "names the fallback" "build every service" "${STDERR}"

echo "http error: 404 builds everything"
run_case "${FIXTURES_DIR}/runs_not_found.json" 404 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"
assert_contains "reports the status code" "HTTP 404" "${STDERR}"

echo "http error: 500 builds everything"
run_case "${FIXTURES_DIR}/runs_server_error.json" 500 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"

echo "http error: 403 rate limit builds everything"
run_case "${FIXTURES_DIR}/runs_rate_limited.json" 403 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"

echo "transport failure: curl cannot reach the API"
run_case "${FIXTURES_DIR}/runs_success.json" 000 7
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"
assert_contains "reports the transport failure" "transport level" "${STDERR}"

echo "malformed: a 200 that is not JSON builds everything"
run_case "${FIXTURES_DIR}/runs_not_json.html" 200 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"

echo "malformed: a head_sha that is not a full SHA is refused"
# dorny/paths-filter reads a non-40-character base as a branch name, so a short
# SHA would silently diff against the wrong thing instead of failing.
run_case "${FIXTURES_DIR}/runs_short_sha.json" 200 0
assert_eq "exit code maps to build-everything" "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
assert_eq "prints no SHA" "" "${STDOUT}"
assert_contains "says the SHA was malformed" "40-character SHA" "${STDERR}"

echo "not configured: no token"
STATUS=0
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  GITHUB_REPOSITORY="madfam-org/yantra4d" \
  bash "${SCRIPT_UNDER_TEST}" >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
assert_eq "exit code is the not-configured code" "${EXIT_NOT_CONFIGURED}" "${STATUS}"
assert_eq "prints no SHA" "" "$(cat "${TMP_ROOT}/stdout")"
assert_contains "still names the fallback" "build every service" "$(cat "${TMP_ROOT}/stderr")"
assert_eq "non-zero, so the caller builds everything" "yes" \
  "$([ "${STATUS}" -ne 0 ] && echo yes || echo no)"

echo "not configured: no repository"
STATUS=0
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  GITHUB_TOKEN="fixture-token-not-a-real-secret" \
  bash "${SCRIPT_UNDER_TEST}" >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
assert_eq "exit code is the not-configured code" "${EXIT_NOT_CONFIGURED}" "${STATUS}"

echo "overrides: branch and workflow file are configurable"
run_case "${FIXTURES_DIR}/runs_success.json" 200 0 \
  DEPLOY_BRANCH="release" DEPLOY_WORKFLOW_FILE="ship.yml"
assert_contains "honours DEPLOY_WORKFLOW_FILE" "workflows/ship.yml/runs" "${ARGV}"
assert_contains "honours DEPLOY_BRANCH" "branch=release" "${ARGV}"

echo "overrides: GITHUB_API_URL (GitHub Enterprise) is honoured"
run_case "${FIXTURES_DIR}/runs_success.json" 200 0 \
  GITHUB_API_URL="https://ghe.example.invalid/api/v3/"
assert_contains "uses the supplied API host without doubling the slash" \
  "https://ghe.example.invalid/api/v3/repos/madfam-org/yantra4d/actions" "${ARGV}"

echo "parser fallback: works with python3 when jq is absent"
if command -v python3 >/dev/null 2>&1; then
  # A PATH holding only the stub curl plus a python3 shim: the script must fall
  # back to python3 rather than failing closed while a parser is available.
  NO_JQ_BIN="${TMP_ROOT}/nojq"
  mkdir -p "${NO_JQ_BIN}"
  ln -sf "$(command -v python3)" "${NO_JQ_BIN}/python3"
  for tool in bash sed tail grep printf env cat; do
    tool_path="$(command -v "${tool}" 2>/dev/null)" || continue
    ln -sf "${tool_path}" "${NO_JQ_BIN}/${tool}"
  done
  ln -sf "${STUB_BIN}/curl" "${NO_JQ_BIN}/curl"
  STATUS=0
  env -i PATH="${NO_JQ_BIN}" HOME="${HOME:-/root}" \
    FAKE_CURL_BODY="${FIXTURES_DIR}/runs_success.json" \
    FAKE_CURL_HTTP_CODE="200" \
    FAKE_CURL_EXIT="0" \
    FAKE_CURL_ARGV="${TMP_ROOT}/argv" \
    GITHUB_TOKEN="fixture-token-not-a-real-secret" \
    GITHUB_REPOSITORY="madfam-org/yantra4d" \
    bash "${SCRIPT_UNDER_TEST}" >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
  assert_eq "exit code is 0 (resolved) without jq" "${EXIT_RESOLVED}" "${STATUS}"
  assert_eq "stdout is the head SHA without jq" "${EXPECTED_SHA}" "$(cat "${TMP_ROOT}/stdout")"
  STATUS=0
  env -i PATH="${NO_JQ_BIN}" HOME="${HOME:-/root}" \
    FAKE_CURL_BODY="${FIXTURES_DIR}/runs_empty.json" \
    FAKE_CURL_HTTP_CODE="200" \
    FAKE_CURL_EXIT="0" \
    FAKE_CURL_ARGV="${TMP_ROOT}/argv" \
    GITHUB_TOKEN="fixture-token-not-a-real-secret" \
    GITHUB_REPOSITORY="madfam-org/yantra4d" \
    bash "${SCRIPT_UNDER_TEST}" >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
  assert_eq "empty result still builds everything without jq" \
    "${EXIT_BUILD_EVERYTHING}" "${STATUS}"
else
  echo "  skip python3 fallback (no python3 on this host)"
fi

echo "hygiene: the token never reaches stdout"
run_case "${FIXTURES_DIR}/runs_success.json" 200 0
case "${STDOUT}" in
  *fixture-token*) nope "token absent from stdout" "the token was printed" ;;
  *) ok "token absent from stdout" ;;
esac

echo
printf 'passed: %d  failed: %d\n' "${PASSED}" "${FAILED}"
[ "${FAILED}" -eq 0 ] || exit 1
