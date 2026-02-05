#!/usr/bin/env python3
"""Benchmark render times for all projects against a running backend.

Requires a running backend at the specified URL (default http://localhost:5000).
Renders each project's first mode with default parameters and records timing.

Usage:
    python scripts/benchmark-renders.py                    # all projects
    python scripts/benchmark-renders.py --project tablaco  # single project
    python scripts/benchmark-renders.py --url http://api:5000 --output docs/benchmarks.md
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def fetch_json(url, data=None, timeout=300):
    """Make an HTTP request and return parsed JSON."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": body}, e.code
    except urllib.error.URLError as e:
        return {"error": str(e.reason)}, 0


def check_backend(base_url):
    """Verify backend is reachable."""
    data, status = fetch_json(f"{base_url}/api/health")
    if status != 200:
        print(f"ERROR: Backend not reachable at {base_url} (status={status})")
        sys.exit(1)
    if not data.get("openscad_available"):
        print("WARNING: OpenSCAD not available — renders will fail")
    return data


def get_projects(base_url):
    """Fetch list of available projects."""
    data, status = fetch_json(f"{base_url}/api/projects")
    if status != 200:
        print(f"ERROR: Failed to fetch projects (status={status})")
        sys.exit(1)
    return data


def get_manifest(base_url, slug):
    """Fetch manifest for a project."""
    data, status = fetch_json(f"{base_url}/api/projects/{slug}/manifest")
    if status != 200:
        return None
    return data


def benchmark_render(base_url, slug, mode, scad_file, parameters, timeout=300):
    """Render a project and return timing info."""
    payload = {
        "project": slug,
        "mode": mode,
        "scad_file": scad_file,
        "parameters": parameters,
    }
    start = time.monotonic()
    data, status = fetch_json(f"{base_url}/api/render", data=payload, timeout=timeout)
    elapsed = time.monotonic() - start
    return {
        "elapsed_s": round(elapsed, 2),
        "status": status,
        "success": status == 200,
        "error": data.get("error") if status != 200 else None,
    }


def build_default_params(manifest):
    """Extract default parameter values from manifest."""
    params = {}
    for p in manifest.get("parameters", []):
        params[p["id"]] = p.get("default", 0)
    return params


def run_benchmarks(base_url, project_filter=None, timeout=300):
    """Run benchmarks for all (or filtered) projects."""
    health = check_backend(base_url)
    print(f"Backend: {base_url} — OpenSCAD: {'yes' if health.get('openscad_available') else 'NO'}\n")

    projects = get_projects(base_url)
    if project_filter:
        projects = [p for p in projects if p["slug"] == project_filter]
        if not projects:
            print(f"ERROR: Project '{project_filter}' not found")
            sys.exit(1)

    results = []
    for proj in sorted(projects, key=lambda p: p["slug"]):
        slug = proj["slug"]
        manifest = get_manifest(base_url, slug)
        if not manifest or not manifest.get("modes"):
            print(f"  SKIP {slug} — no manifest or modes")
            continue

        mode = manifest["modes"][0]
        mode_id = mode["id"]
        scad_file = mode["scad_file"]
        defaults = build_default_params(manifest)

        print(f"  Rendering {slug}/{mode_id} ...", end=" ", flush=True)
        result = benchmark_render(base_url, slug, mode_id, scad_file, defaults, timeout)
        status_str = f"{result['elapsed_s']}s" if result["success"] else f"FAIL ({result['status']})"
        print(status_str)

        results.append({
            "project": slug,
            "mode": mode_id,
            "scad_file": scad_file,
            **result,
        })

    return results


def format_markdown(results):
    """Format results as a Markdown table."""
    lines = [
        "# Render Benchmarks\n",
        "Render times for each project's first mode with default parameters.\n",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        "| Project | Mode | SCAD File | Time (s) | Status |",
        "|---------|------|-----------|----------|--------|",
    ]
    for r in results:
        status = "OK" if r["success"] else f"FAIL {r['status']}"
        lines.append(
            f"| {r['project']} | {r['mode']} | {r['scad_file']} | {r['elapsed_s']} | {status} |"
        )

    # Summary
    successful = [r for r in results if r["success"]]
    if successful:
        times = [r["elapsed_s"] for r in successful]
        lines.extend([
            "",
            "## Summary",
            "",
            f"- **Projects rendered**: {len(successful)}/{len(results)}",
            f"- **Fastest**: {min(times)}s",
            f"- **Slowest**: {max(times)}s",
            f"- **Average**: {sum(times) / len(times):.2f}s",
            f"- **Total**: {sum(times):.2f}s",
        ])

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Benchmark Qubic project render times")
    parser.add_argument("--url", default="http://localhost:5000", help="Backend base URL")
    parser.add_argument("--project", help="Benchmark a single project by slug")
    parser.add_argument("--output", help="Write results to a Markdown file (e.g. docs/benchmarks.md)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-render timeout in seconds")
    args = parser.parse_args()

    print(f"Qubic Render Benchmarks\n{'=' * 40}")
    results = run_benchmarks(args.url, args.project, args.timeout)

    md = format_markdown(results)
    print(f"\n{md}")

    if args.output:
        with open(args.output, "w") as f:
            f.write(md)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
