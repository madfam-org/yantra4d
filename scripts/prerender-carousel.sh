#!/usr/bin/env bash
# Pre-render GLB models for the landing page carousel.
# Reads project slugs from apps/landing/src/data/projects.ts and renders
# each one via the backend API, converting STL→GLB for optimal web delivery.
#
# Usage:
#   ./scripts/prerender-carousel.sh [API_BASE_URL]
#
# Defaults to http://localhost:5000 if no URL is provided.
# Run against a local or staging backend; committed outputs are served
# as static assets so the landing page makes zero API render calls.

set -euo pipefail

API_BASE="${1:-http://localhost:5000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECTS_TS="$REPO_ROOT/apps/landing/src/data/projects.ts"
OUTPUT_DIR="$REPO_ROOT/apps/landing/public/models"

mkdir -p "$OUTPUT_DIR"

# Extract slugs from the TypeScript projects array
SLUGS=$(grep "slug:" "$PROJECTS_TS" | sed -E "s/.*slug: '([^']+)'.*/\1/")

total=$(echo "$SLUGS" | wc -l | tr -d ' ')
count=0
failed=0

echo "=== Pre-rendering $total carousel models (GLB) ==="
echo "API: $API_BASE"
echo "Output: $OUTPUT_DIR"
echo ""

for slug in $SLUGS; do
  count=$((count + 1))
  tmpfile="$OUTPUT_DIR/${slug}.tmp"
  glbfile="$OUTPUT_DIR/${slug}.glb"
  echo -n "[$count/$total] $slug ... "

  http_code=$(curl -s -o "$tmpfile" -w "%{http_code}" \
    -X POST "$API_BASE/api/render" \
    -H "Content-Type: application/json" \
    -d "{\"project\": \"$slug\", \"parameters\": {}, \"export_format\": \"stl\"}" \
    --max-time 120)

  if [ "$http_code" = "200" ]; then
    # The sync endpoint returns JSON with parts[].url — extract the part URL.
    # Backend now returns GLB URLs for OpenSCAD projects (STL→GLB post-render).
    if file "$tmpfile" | grep -q "JSON\|ASCII text"; then
      part_url=$(python3 -c "
import json, sys
data = json.load(open('$tmpfile'))
if data.get('parts'):
    print(data['parts'][0]['url'])
else:
    sys.exit(1)
" 2>/dev/null) || { echo "FAIL (no parts in response)"; failed=$((failed + 1)); rm -f "$tmpfile"; continue; }

      # Fetch the actual model binary (GLB from updated backend, or STL from older backend)
      curl -s -o "$tmpfile" "$API_BASE$part_url" --max-time 60
    fi

    # If the backend returned an STL (older backend without GLB conversion),
    # convert locally using trimesh
    if file "$tmpfile" | grep -q "STL\|data"; then
      python3 -c "
import trimesh, sys
mesh = trimesh.load('$tmpfile', file_type='stl')
mesh.export('$glbfile', file_type='glb')
" 2>/dev/null
      if [ -f "$glbfile" ]; then
        rm -f "$tmpfile"
      else
        echo "FAIL (STL→GLB conversion)"
        failed=$((failed + 1))
        rm -f "$tmpfile"
        continue
      fi
    else
      # Already GLB — just rename
      mv "$tmpfile" "$glbfile"
    fi

    size=$(wc -c < "$glbfile" | tr -d ' ')
    echo "OK (${size} bytes)"

    # Clean up any leftover STL from previous runs
    rm -f "$OUTPUT_DIR/${slug}.stl"
  else
    echo "FAIL (HTTP $http_code)"
    rm -f "$tmpfile"
    failed=$((failed + 1))
  fi
done

echo ""
echo "=== Done: $((count - failed))/$total succeeded, $failed failed ==="

# Generate manifest.json listing all successfully rendered GLBs
echo "Generating manifest.json ..."
echo '{ "generated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'", "models": [' > "$OUTPUT_DIR/manifest.json"
first=true
for glb in "$OUTPUT_DIR"/*.glb; do
  [ -f "$glb" ] || continue
  slug=$(basename "$glb" .glb)
  size=$(stat -f%z "$glb" 2>/dev/null || stat -c%s "$glb")
  [ "$first" = true ] && first=false || echo ',' >> "$OUTPUT_DIR/manifest.json"
  printf '  { "slug": "%s", "size": %s }' "$slug" "$size" >> "$OUTPUT_DIR/manifest.json"
done
echo '' >> "$OUTPUT_DIR/manifest.json"
echo '] }' >> "$OUTPUT_DIR/manifest.json"
echo "Manifest written to $OUTPUT_DIR/manifest.json"

if [ "$failed" -gt 0 ]; then
  echo "WARNING: Some models failed to render. Re-run with a running backend."
  exit 1
fi
