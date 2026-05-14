#!/usr/bin/env bash
# Pre-render GLB models for the landing page carousel.
#
# Reads project slugs from apps/landing/src/data/projects.ts and renders each
# one via the backend API, converting STL→GLB when needed.

set -euo pipefail

CLEAN=false
if [ "${1:-}" = "--clean" ]; then
  CLEAN=true
  shift
fi

API_BASE="${1:-http://localhost:5000}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECTS_TS="$REPO_ROOT/apps/landing/src/data/projects.ts"
OUTPUT_DIR="$REPO_ROOT/apps/landing/public/models"

for cmd in curl file python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' is not installed"
    exit 1
  fi
done

if [ ! -f "$PROJECTS_TS" ]; then
  echo "ERROR: projects catalog not found: $PROJECTS_TS"
  exit 1
fi

if ! python3 - <<'PY' >/dev/null 2>&1; then
import trimesh  # noqa: F401
PY
then
  echo "ERROR: python3 dependency 'trimesh' is required for STL→GLB conversion fallback"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [ "$CLEAN" = true ]; then
  echo "Cleaning stale models..."
  rm -f "$OUTPUT_DIR"/*.glb "$OUTPUT_DIR"/*.json.tmp "$OUTPUT_DIR"/*.stl
fi

SLUGS="$(python3 - "$PROJECTS_TS" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

matches = re.findall(r"slug:\s*['\"]([^'\"]+)['\"]", text)
for slug in matches:
    print(slug)
PY
)"

if [ -z "$SLUGS" ]; then
  echo "ERROR: no slugs extracted from $PROJECTS_TS"
  exit 1
fi

if ! curl -sSf -o "$OUTPUT_DIR/.health.tmp" -m 10 "$API_BASE/api/health" >/dev/null; then
  echo "ERROR: backend not reachable at $API_BASE/api/health"
  rm -f "$OUTPUT_DIR/.health.tmp"
  exit 1
fi
rm -f "$OUTPUT_DIR/.health.tmp"

count=0
failed=0
FAILED_SLUGS=()

TOTAL_LINES="$(printf "%s\n" "$SLUGS" | wc -l | tr -d ' ')"
echo "=== Pre-rendering $TOTAL_LINES carousel models (GLB) ==="
echo "API: $API_BASE"
echo "Output: $OUTPUT_DIR"
echo ""

for slug in $SLUGS; do
  count=$((count + 1))
  tmpfile="$OUTPUT_DIR/${slug}.tmp"
  glbfile="$OUTPUT_DIR/${slug}.glb"
  status_file="$OUTPUT_DIR/${slug}.manifest.json.tmp"

  printf "[%3d/%s] %s ... " "$count" "$TOTAL_LINES" "$slug"

  http_code="$(curl -s -o "$tmpfile" -w "%{http_code}" \
    -X POST "$API_BASE/api/render" \
    -H "Content-Type: application/json" \
    --max-time 120 \
    -d "{\"project\": \"$slug\", \"parameters\": {}, \"export_format\": \"stl\"}")"

  if [ "$http_code" != "200" ]; then
    echo "FAIL (HTTP $http_code)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:$http_code")
    rm -f "$tmpfile" "$status_file"
    continue
  fi

  if [ "$(file -b --mime-type "$tmpfile")" != "application/json" ]; then
    echo "FAIL (non-JSON render response)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:non-json")
    rm -f "$tmpfile" "$status_file"
    continue
  fi

  if ! python3 - "$tmpfile" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)

parts = payload.get("parts")
if not parts or not isinstance(parts, list):
    raise ValueError("parts missing")
part_url = parts[0].get("url")
if not part_url:
    raise ValueError("part url missing")
print(part_url)
PY
  then
    echo "FAIL (no part URL in response)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:no_part_url")
    rm -f "$tmpfile" "$status_file"
    continue
  fi > "$status_file"

  part_url="$(cat "$status_file")"
  rm -f "$status_file"

  http_model="$(curl -s -o "$tmpfile" -w "%{http_code}" "$API_BASE$part_url" --max-time 60)"
  if [ "$http_model" != "200" ]; then
    echo "FAIL (model download HTTP $http_model)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:model_download:$http_model")
    rm -f "$tmpfile"
    continue
  fi

  mime="$(file -b --mime-type "$tmpfile")"
  part_ext="${part_url##*.}"
  part_ext="$(printf '%s' "$part_ext" | tr '[:upper:]' '[:lower:]')"

  if [ "$part_ext" = "glb" ] || [ "$mime" = "model/gltf+json" ]; then
    mv "$tmpfile" "$glbfile"
  elif [ "$part_ext" = "stl" ] || [ "$mime" = "model/stl" ] || [ "$mime" = "application/sla" ]; then
    if ! python3 - "$tmpfile" "$glbfile" <<'PY'
import sys
import trimesh

mesh = trimesh.load(sys.argv[1], file_type="stl")
mesh.export(sys.argv[2], file_type="glb")
PY
    then
      echo "FAIL (STL→GLB conversion)"
      failed=$((failed + 1))
      FAILED_SLUGS+=("$slug:stl_conversion")
      rm -f "$tmpfile"
      continue
    fi
  else
    echo "FAIL (unknown artifact type: $part_ext/$mime)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:$part_ext/$mime")
    rm -f "$tmpfile"
    continue
  fi

  if [ ! -f "$glbfile" ]; then
    echo "FAIL (missing output artifact)"
    failed=$((failed + 1))
    FAILED_SLUGS+=("$slug:missing_output")
    rm -f "$tmpfile"
    continue
  fi

  size="$(wc -c < "$glbfile" | tr -d ' ')"
  echo "OK (${size} bytes)"
  rm -f "$tmpfile"
done

echo ""
echo "=== Done: $((count - failed))/$count succeeded, $failed failed ==="

printf '{ "generated": "%s", "models": [' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUTPUT_DIR/manifest.json"
first=true
for glb in "$OUTPUT_DIR"/*.glb; do
  [ -f "$glb" ] || continue
  slug="$(basename "$glb" .glb)"
  size="$(wc -c < "$glb" | tr -d ' ')"
  if [ "$first" = true ]; then
    first=false
  else
    echo "," >> "$OUTPUT_DIR/manifest.json"
  fi
  printf '  { "slug": "%s", "size": %s, "format": "glb" }' "$slug" "$size" >> "$OUTPUT_DIR/manifest.json"
done
echo "" >> "$OUTPUT_DIR/manifest.json"
echo "] }" >> "$OUTPUT_DIR/manifest.json"
echo "Manifest written to $OUTPUT_DIR/manifest.json"

if [ "$failed" -gt 0 ]; then
  echo "WARNING: Some models failed to render."
  printf 'Failed: '
  printf '%s ' "${FAILED_SLUGS[@]}"
  echo ""
  exit 1
fi
