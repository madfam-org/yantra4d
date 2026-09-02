#!/usr/bin/env bash
# =============================================================================
# scripts/ci/last_successful_deploy_sha.sh
#
# Prints the head SHA of the most recent SUCCESSFUL run of the deploy workflow
# on the deploy branch. deploy.yml uses it as the `base` for
# dorny/paths-filter, so change detection asks "what has changed since the last
# thing we actually shipped?" instead of "what did the newest push touch?".
#
# Why that matters: deploy.yml's concurrency group is serial
# (cancel-in-progress: false), and GitHub keeps only ONE pending run per group —
# a third push REPLACES the queued second one. The replaced run never executes,
# so its commits are never examined by any path filter. On 2026-09-02 merges
# #541 → #542 → #543 landed back to back, the surviving run saw only #543
# (backend-only), and the Studio image #542 needed was never built. Diffing
# against the last successful deploy makes a dropped run harmless: the next run
# still sees every path that changed since the last shipped commit.
#
# Environment:
#   GITHUB_TOKEN | GH_TOKEN   required — the job's ${{ github.token }};
#                             needs `actions: read`
#   GITHUB_REPOSITORY         required — owner/repo
#   GITHUB_API_URL            optional — defaults to https://api.github.com
#   DEPLOY_WORKFLOW_FILE      optional — defaults to deploy.yml
#   DEPLOY_BRANCH             optional — defaults to main
#   CURL_MAX_TIME             optional — per-request timeout, defaults to 20s
#
# Output:
#   stdout  the 40-character head SHA, and nothing else, on exit 0
#   stderr  a one-line human reason on every non-zero exit
#
# Exit codes:
#   0  a base SHA was resolved and printed
#   2  not configured (no token, no repository) — a CI wiring bug
#   3  no base could be resolved: first deploy, empty result, HTTP error,
#      transport failure, unparseable or malformed response
#
# The caller MUST treat EVERY non-zero exit as "build every service". Never
# treat an unresolved base as "nothing changed": a silent no-op deploy is how
# the Studio image went missing in the first place. deploy.yml collapses 2 and
# 3 into the same fail-closed path and reports the reason in the job summary.
# =============================================================================

set -uo pipefail

readonly EXIT_OK=0
readonly EXIT_USAGE=2
readonly EXIT_UNRESOLVED=3

log() { printf '%s\n' "last_successful_deploy_sha: $*" >&2; }

# Fail CLOSED: no SHA on stdout, and an exit code the caller reads as
# "build everything".
fail_closed() {
  log "$* — the caller must build every service"
  exit "${EXIT_UNRESOLVED}"
}

not_configured() {
  log "$* — the caller must build every service"
  exit "${EXIT_USAGE}"
}

main() {
  local token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
  local repo="${GITHUB_REPOSITORY:-}"
  local api_url="${GITHUB_API_URL:-https://api.github.com}"
  local workflow="${DEPLOY_WORKFLOW_FILE:-deploy.yml}"
  local branch="${DEPLOY_BRANCH:-main}"
  local max_time="${CURL_MAX_TIME:-20}"

  [ -n "${token}" ] || not_configured "GITHUB_TOKEN (or GH_TOKEN) is not set"
  [ -n "${repo}" ] || not_configured "GITHUB_REPOSITORY is not set"

  local json_tool=""
  if command -v jq >/dev/null 2>&1; then
    json_tool="jq"
  elif command -v python3 >/dev/null 2>&1; then
    json_tool="python3"
  else
    fail_closed "neither jq nor python3 is available to parse the API response"
  fi

  local url="${api_url%/}/repos/${repo}/actions/workflows/${workflow}/runs?branch=${branch}&status=success&per_page=1"

  # --write-out appends "\n<http_code>" after the body; the body is everything
  # except that last line. No -f/--fail: a non-2xx body is still worth reading
  # and the status is what we branch on.
  local response="" curl_status=0
  response="$(
    curl --silent --show-error --location \
      --max-time "${max_time}" \
      --write-out '\n%{http_code}' \
      --header 'Accept: application/vnd.github+json' \
      --header "Authorization: Bearer ${token}" \
      --header 'X-GitHub-Api-Version: 2022-11-28' \
      "${url}" 2>/dev/null
  )" || curl_status=$?

  if [ "${curl_status}" -ne 0 ]; then
    fail_closed "the GitHub API request failed at the transport level (curl exit ${curl_status})"
  fi

  local http_code body
  http_code="$(printf '%s' "${response}" | tail -n 1)"
  body="$(printf '%s' "${response}" | sed '$d')"

  if [ "${http_code}" != "200" ]; then
    fail_closed "the GitHub API answered HTTP ${http_code} for the deploy run history"
  fi

  local sha=""
  case "${json_tool}" in
    jq)
      sha="$(printf '%s' "${body}" | jq -r '.workflow_runs[0].head_sha // empty' 2>/dev/null)" || sha=""
      ;;
    python3)
      sha="$(
        printf '%s' "${body}" | python3 -c '
import json
import sys

try:
    doc = json.load(sys.stdin)
except Exception:
    sys.exit(0)
runs = doc.get("workflow_runs") if isinstance(doc, dict) else None
if not isinstance(runs, list) or not runs:
    sys.exit(0)
first = runs[0]
sha = first.get("head_sha") if isinstance(first, dict) else None
if isinstance(sha, str):
    sys.stdout.write(sha)
' 2>/dev/null
      )" || sha=""
      ;;
  esac

  # An empty list is the honest answer on a first deploy or after a history
  # purge; a short or non-hex value means the contract moved under us. Both are
  # "we do not know", and "we do not know" means build everything.
  # dorny/paths-filter only treats `base` as a commit when it is 40 hex
  # characters — anything shorter would be read as a branch name and silently
  # diff against the wrong thing.
  if [ -z "${sha}" ]; then
    fail_closed "no successful run of ${workflow} on ${branch} was found (first deploy, or the history was purged)"
  fi

  if ! printf '%s' "${sha}" | grep -Eq '^[0-9a-f]{40}$'; then
    fail_closed "the API returned a head_sha that is not a 40-character SHA"
  fi

  printf '%s\n' "${sha}"
  exit "${EXIT_OK}"
}

main "$@"
