"""Wait for serving readiness, and for the new renderer when one was built."""
import argparse
import json
import subprocess
import time

# The window covers the slowest measured rollout plus 30 %. Measured from the
# start of this step to readiness (backend image built, Recreate rollout):
# deploy runs 36666928905 4m33s, 36716038813 3m32s, 37348262719 5m03s and
# 37360504031 5m33s passed; 37325884583 timed out at 6m00s and the pod was
# healthy about 2m30s later, so about 8m30s. 8m30s x 1.3 = 11m03s, rounded up
# to 12 minutes. verify-deploy's timeout-minutes in deploy.yml stays above it.
DEFAULT_TIMEOUT_S = 720


def say(message):
    """Print now. The runner pipes stdout, so Python block-buffers it, and every
    "Waiting ..." line used to reach the log at exit under one shared timestamp,
    which hid how long the rollout actually took."""
    print(message, flush=True)


def probe(url, timeout):
    result = subprocess.run(
        ["curl", "--silent", "--show-error", "--max-time", str(timeout),
         "--header", "Cache-Control: no-cache", "--write-out", "\n%{http_code}", url],
        capture_output=True, text=True, timeout=timeout + 1, check=False,
    )
    if result.returncode:
        raise ValueError("readiness transport failed")
    body, status = result.stdout.rsplit("\n", 1)
    return int(status), json.loads(body)


def wait_for_release(url, expected_revision, timeout=DEFAULT_TIMEOUT_S, interval=30):
    started = time.monotonic()
    deadline = started + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            status, body = probe(url, min(15, remaining))
            revision_matches = not expected_revision or body.get("render_revision") == expected_revision
            if status == 200 and body.get("status") in {"healthy", "degraded"} and revision_matches:
                say(f"Published renderer is ready after {time.monotonic() - started:.0f}s"
                    if expected_revision else
                    "Backend is ready; no backend image was built in this run")
                return 0
            say(f"[{time.monotonic() - started:4.0f}s] Waiting for readiness/release: "
                f"HTTP {status}, revision_matches={revision_matches}")
        except (ValueError, TypeError, AttributeError, OSError, subprocess.TimeoutExpired):
            say(f"[{time.monotonic() - started:4.0f}s] Waiting for a valid readiness response")
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    say(f"Readiness/release verification timed out after {timeout}s")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://api.yantra4d.com/api/health/ready")
    parser.add_argument("--expected-revision", default="")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                        help="seconds to wait (default: %(default)s)")
    args = parser.parse_args()
    raise SystemExit(wait_for_release(args.url, args.expected_revision, timeout=args.timeout))
