"""Wait for serving readiness, and for the new renderer when one was built."""
import argparse
import json
import subprocess
import time


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


def wait_for_release(url, expected_revision, timeout=360, interval=30):
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            status, body = probe(url, min(15, remaining))
            revision_matches = not expected_revision or body.get("render_revision") == expected_revision
            if status == 200 and body.get("status") in {"healthy", "degraded"} and revision_matches:
                print("Published renderer is ready" if expected_revision else
                      "Backend is ready; no backend image was built in this run")
                return 0
            print(f"Waiting for readiness/release: HTTP {status}, revision_matches={revision_matches}")
        except (ValueError, TypeError, AttributeError, OSError, subprocess.TimeoutExpired):
            print("Waiting for a valid readiness response")
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    print("Readiness/release verification timed out")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://api.yantra4d.com/api/health/ready")
    parser.add_argument("--expected-revision", default="")
    args = parser.parse_args()
    raise SystemExit(wait_for_release(args.url, args.expected_revision))
