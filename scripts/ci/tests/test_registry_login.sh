#!/usr/bin/env bash
# =============================================================================
# scripts/ci/tests/test_registry_login.sh
#
# Tests for scripts/ci/registry_login.sh. The repo has no bats, so this is a
# plain bash harness in the same shape as
# test_last_successful_deploy_sha.sh: no dependencies beyond what the script
# itself needs.
#
# No registry is ever contacted and nothing ever sleeps. Two stubs are placed
# at the front of PATH:
#
#   docker  fails the first FAKE_DOCKER_FAILURES invocations and succeeds after
#           that, recording every argv and every stdin it was handed. That is
#           what lets the test assert the password arrived on STDIN and never
#           in the argument list. Every invocation of the script under test
#           redirects `</dev/null`, matching how Actions runs a `run:` step and
#           so that a script which stopped piping the credential makes the stub
#           read EOF and record nothing, instead of blocking forever.
#   sleep   records the duration it was asked for and returns immediately, so
#           the 10/20/30/40 backoff is asserted as data rather than waited out.
#           A real run of the exhausted case takes 100 seconds; this takes none.
#
# Usage:
#   ./scripts/ci/tests/test_registry_login.sh
#
# Exit 0 when every case passes; 1 if any assertion failed.
# =============================================================================

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TESTS_DIR
readonly SCRIPT_UNDER_TEST="${TESTS_DIR}/../registry_login.sh"

# The exit-code contract deploy.yml depends on. Anything non-zero is fatal to
# the build; the codes exist so a wiring bug reads differently from an outage.
readonly EXIT_OK=0
readonly EXIT_EXHAUSTED=1
readonly EXIT_NOT_CONFIGURED=2

# Not a real credential: a literal chosen so a leak is unmistakable in output.
readonly FAKE_PASSWORD='s3cr3t-not-a-real-token-4a1f9c'

PASSED=0
FAILED=0

TMP_ROOT="$(mktemp -d)"
readonly TMP_ROOT
cleanup() { rm -rf "${TMP_ROOT}"; }
trap cleanup EXIT

# ---- stubs -------------------------------------------------------------------
readonly STUB_BIN="${TMP_ROOT}/bin"
mkdir -p "${STUB_BIN}"

cat > "${STUB_BIN}/docker" <<'STUB'
#!/usr/bin/env bash
# Stands in for the docker CLI. Fails the first FAKE_DOCKER_FAILURES calls.
count=0
[ -f "${FAKE_DOCKER_CALLS}" ] && count="$(cat "${FAKE_DOCKER_CALLS}")"
count=$((count + 1))
printf '%s' "${count}" > "${FAKE_DOCKER_CALLS}"

printf '%s\n' "$*" >> "${FAKE_DOCKER_ARGV}"
# --password-stdin means docker reads the credential from stdin; record exactly
# what it received so the test can prove the password travelled that way.
cat >> "${FAKE_DOCKER_STDIN}"

if [ "${count}" -le "${FAKE_DOCKER_FAILURES:-0}" ]; then
  echo "Error response from daemon: Get \"https://${1}/v2/\": net/http: TLS handshake timeout" >&2
  exit 1
fi
echo "Login Succeeded"
STUB
chmod +x "${STUB_BIN}/docker"

cat > "${STUB_BIN}/sleep" <<'STUB'
#!/usr/bin/env bash
# Records the requested duration and returns at once.
printf '%s\n' "$1" >> "${FAKE_SLEEPS}"
STUB
chmod +x "${STUB_BIN}/sleep"

# ---- harness -----------------------------------------------------------------
# run_case <docker-failures> [extra env assignments...]
# Sets: STATUS, STDOUT, STDERR, OUTPUT (both streams), CALLS, ARGV, STDIN_SEEN, SLEEPS
run_case() {
  local failures="$1"
  shift

  local out_file="${TMP_ROOT}/stdout" err_file="${TMP_ROOT}/stderr"
  local calls_file="${TMP_ROOT}/calls" argv_file="${TMP_ROOT}/argv"
  local stdin_file="${TMP_ROOT}/stdin" sleeps_file="${TMP_ROOT}/sleeps"
  printf '0' > "${calls_file}"
  : > "${argv_file}"
  : > "${stdin_file}"
  : > "${sleeps_file}"

  STATUS=0
  env -i \
    PATH="${STUB_BIN}:${PATH}" \
    HOME="${HOME:-/root}" \
    FAKE_DOCKER_FAILURES="${failures}" \
    FAKE_DOCKER_CALLS="${calls_file}" \
    FAKE_DOCKER_ARGV="${argv_file}" \
    FAKE_DOCKER_STDIN="${stdin_file}" \
    FAKE_SLEEPS="${sleeps_file}" \
    REGISTRY_HOST="ghcr.io" \
    REGISTRY_USER="madfam-bot" \
    REGISTRY_PASSWORD="${FAKE_PASSWORD}" \
    "$@" \
    bash "${SCRIPT_UNDER_TEST}" </dev/null >"${out_file}" 2>"${err_file}" || STATUS=$?

  STDOUT="$(cat "${out_file}")"
  STDERR="$(cat "${err_file}")"
  OUTPUT="${STDOUT}"$'\n'"${STDERR}"
  CALLS="$(cat "${calls_file}")"
  ARGV="$(cat "${argv_file}")"
  STDIN_SEEN="$(cat "${stdin_file}")"
  SLEEPS="$(tr '\n' ' ' < "${sleeps_file}" | sed 's/ *$//')"
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

assert_absent() {
  local label="$1" needle="$2" haystack="$3"
  case "${haystack}" in
    *"${needle}"*) nope "${label}" "found [${needle}] where it must never appear" ;;
    *) ok "${label}" ;;
  esac
}

# ---- cases -------------------------------------------------------------------

echo "success: the first attempt works"
run_case 0
assert_eq "exit code is 0" "${EXIT_OK}" "${STATUS}"
assert_eq "docker was called exactly once" "1" "${CALLS}"
assert_eq "nothing slept" "" "${SLEEPS}"
assert_absent "no retry warning" "::warning::" "${OUTPUT}"
assert_absent "no error annotation" "::error::" "${OUTPUT}"

echo "success: the request is the one docker/login-action made"
assert_contains "names the registry host" "ghcr.io" "${ARGV}"
assert_contains "names the user" "-u madfam-bot" "${ARGV}"
assert_contains "reads the credential from stdin" "--password-stdin" "${ARGV}"
assert_absent "the password is NOT in argv" "${FAKE_PASSWORD}" "${ARGV}"
assert_eq "the password is what reached stdin" "${FAKE_PASSWORD}" "${STDIN_SEEN}"

echo "retry: three transient failures, then success"
run_case 3
assert_eq "exit code is 0" "${EXIT_OK}" "${STATUS}"
assert_eq "docker was called four times" "4" "${CALLS}"
assert_eq "backoff was 10/20/30" "10 20 30" "${SLEEPS}"
assert_contains "warns on the first failure" \
  "login to ghcr.io failed (attempt 1 of 5); retrying in 10s" "${OUTPUT}"
assert_contains "warns on the third failure" \
  "login to ghcr.io failed (attempt 3 of 5); retrying in 30s" "${OUTPUT}"
assert_absent "does not claim final failure" "::error::" "${OUTPUT}"

echo "retry: the fifth attempt still counts"
run_case 4
assert_eq "exit code is 0" "${EXIT_OK}" "${STATUS}"
assert_eq "docker was called five times" "5" "${CALLS}"
assert_eq "backoff was 10/20/30/40" "10 20 30 40" "${SLEEPS}"

echo "exhausted: every attempt fails"
run_case 99
assert_eq "exit code is the exhausted code" "${EXIT_EXHAUSTED}" "${STATUS}"
assert_eq "docker was called five times and no more" "5" "${CALLS}"
assert_eq "slept 10/20/30/40 — never after the last attempt" "10 20 30 40" "${SLEEPS}"
assert_contains "the error names the registry" \
  "::error::login to ghcr.io failed 5 times" "${OUTPUT}"
assert_contains "the error says what it costs" "cannot push or pull" "${OUTPUT}"

echo "hygiene: the password never reaches any output stream"
assert_absent "absent from stdout" "${FAKE_PASSWORD}" "${STDOUT}"
assert_absent "absent from stderr" "${FAKE_PASSWORD}" "${STDERR}"
assert_absent "absent from every recorded argv" "${FAKE_PASSWORD}" "${ARGV}"

echo "hygiene: the password stays out of the log even under bash -x"
# `set +x` inside the script is the guard: a traced `printf` of the credential
# would put it in the job log although it never reaches argv.
XSTATUS=0
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  FAKE_DOCKER_FAILURES=1 \
  FAKE_DOCKER_CALLS="${TMP_ROOT}/xcalls" \
  FAKE_DOCKER_ARGV="${TMP_ROOT}/xargv" \
  FAKE_DOCKER_STDIN="${TMP_ROOT}/xstdin" \
  FAKE_SLEEPS="${TMP_ROOT}/xsleeps" \
  REGISTRY_HOST="ghcr.io" REGISTRY_USER="madfam-bot" \
  REGISTRY_PASSWORD="${FAKE_PASSWORD}" \
  bash -x "${SCRIPT_UNDER_TEST}" </dev/null >"${TMP_ROOT}/xout" 2>"${TMP_ROOT}/xerr" || XSTATUS=$?
assert_eq "still succeeds after the retry" "${EXIT_OK}" "${XSTATUS}"
assert_absent "absent from a traced run" "${FAKE_PASSWORD}" \
  "$(cat "${TMP_ROOT}/xout" "${TMP_ROOT}/xerr")"

echo "not configured: no password"
STATUS=0
printf '0' > "${TMP_ROOT}/calls"
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  FAKE_DOCKER_FAILURES=0 \
  FAKE_DOCKER_CALLS="${TMP_ROOT}/calls" \
  FAKE_DOCKER_ARGV="${TMP_ROOT}/argv" \
  FAKE_DOCKER_STDIN="${TMP_ROOT}/stdin" \
  FAKE_SLEEPS="${TMP_ROOT}/sleeps" \
  REGISTRY_HOST="ghcr.io" REGISTRY_USER="madfam-bot" \
  bash "${SCRIPT_UNDER_TEST}" </dev/null >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
assert_eq "exit code is the not-configured code" "${EXIT_NOT_CONFIGURED}" "${STATUS}"
assert_eq "docker was never invoked" "0" "$(cat "${TMP_ROOT}/calls")"
assert_contains "names the missing variable" "REGISTRY_PASSWORD is not set" \
  "$(cat "${TMP_ROOT}/stderr")"

echo "not configured: an EMPTY secret is not a network problem"
# An unset `secrets.*` arrives as an empty string, not as an unset variable, so
# `set -u` cannot catch it. Without this guard a missing secret burns five
# doomed attempts and 100 seconds before saying anything useful.
STATUS=0
printf '0' > "${TMP_ROOT}/calls"
: > "${TMP_ROOT}/sleeps"
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  FAKE_DOCKER_FAILURES=0 \
  FAKE_DOCKER_CALLS="${TMP_ROOT}/calls" \
  FAKE_DOCKER_ARGV="${TMP_ROOT}/argv" \
  FAKE_DOCKER_STDIN="${TMP_ROOT}/stdin" \
  FAKE_SLEEPS="${TMP_ROOT}/sleeps" \
  REGISTRY_HOST="ghcr.io" REGISTRY_USER="madfam-bot" REGISTRY_PASSWORD="" \
  bash "${SCRIPT_UNDER_TEST}" </dev/null >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
assert_eq "exit code is the not-configured code" "${EXIT_NOT_CONFIGURED}" "${STATUS}"
assert_eq "docker was never invoked" "0" "$(cat "${TMP_ROOT}/calls")"
assert_eq "and nothing slept" "" "$(tr '\n' ' ' < "${TMP_ROOT}/sleeps" | sed 's/ *$//')"

echo "not configured: no host, no user"
for missing in REGISTRY_HOST REGISTRY_USER; do
  STATUS=0
  declare -a envs=(REGISTRY_HOST="ghcr.io" REGISTRY_USER="madfam-bot" \
    REGISTRY_PASSWORD="${FAKE_PASSWORD}")
  declare -a kept=()
  for pair in "${envs[@]}"; do
    [ "${pair%%=*}" = "${missing}" ] || kept+=("${pair}")
  done
  env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
    FAKE_DOCKER_FAILURES=0 \
    FAKE_DOCKER_CALLS="${TMP_ROOT}/calls" \
    FAKE_DOCKER_ARGV="${TMP_ROOT}/argv" \
    FAKE_DOCKER_STDIN="${TMP_ROOT}/stdin" \
    FAKE_SLEEPS="${TMP_ROOT}/sleeps" \
    "${kept[@]}" \
    bash "${SCRIPT_UNDER_TEST}" </dev/null >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
  assert_eq "missing ${missing} is the not-configured code" \
    "${EXIT_NOT_CONFIGURED}" "${STATUS}"
done

echo "docker.io: the other registry deploy.yml logs in to"
STATUS=0
printf '0' > "${TMP_ROOT}/calls"
: > "${TMP_ROOT}/argv"
: > "${TMP_ROOT}/stdin"
env -i PATH="${STUB_BIN}:${PATH}" HOME="${HOME:-/root}" \
  FAKE_DOCKER_FAILURES=0 \
  FAKE_DOCKER_CALLS="${TMP_ROOT}/calls" \
  FAKE_DOCKER_ARGV="${TMP_ROOT}/argv" \
  FAKE_DOCKER_STDIN="${TMP_ROOT}/stdin" \
  FAKE_SLEEPS="${TMP_ROOT}/sleeps" \
  REGISTRY_HOST="docker.io" REGISTRY_USER="someone" \
  REGISTRY_PASSWORD="${FAKE_PASSWORD}" \
  bash "${SCRIPT_UNDER_TEST}" </dev/null >"${TMP_ROOT}/stdout" 2>"${TMP_ROOT}/stderr" || STATUS=$?
assert_eq "exit code is 0" "${EXIT_OK}" "${STATUS}"
assert_contains "logs in to docker.io" "docker.io" "$(cat "${TMP_ROOT}/argv")"
assert_absent "password absent from argv" "${FAKE_PASSWORD}" "$(cat "${TMP_ROOT}/argv")"

echo
printf 'passed: %d  failed: %d\n' "${PASSED}" "${FAILED}"
[ "${FAILED}" -eq 0 ] || exit 1
