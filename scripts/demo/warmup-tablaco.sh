#!/usr/bin/env bash
# warmup-tablaco.sh — Pre-render all Tablaco modes to populate the render cache.
#
# Usage:
#   ./scripts/demo/warmup-tablaco.sh                    # default: localhost:5000
#   ./scripts/demo/warmup-tablaco.sh https://api.yantra4d.com   # production
#
# This script calls POST /api/render for each mode (unit, assembly, grid)
# with default parameters. Renders populate the L2 Redis cache (24hr TTL)
# so subsequent client visits get instant cache hits.

set -euo pipefail

API_BASE="${1:-http://localhost:5000}"
PROJECT="tablaco"
STUDIO_URL="${STUDIO_URL:-https://app.yantra4d.com}"

echo "=== Tablaco Cache Warmup ==="
echo "API: $API_BASE"
echo ""

# Default parameters from manifest
DEFAULT_PARAMS='{
  "size": 20.0,
  "thick": 2.5,
  "rod_D": 3.0,
  "clearance": 0.2,
  "fit_clear": 0,
  "edge_rounding": 1.0,
  "letter_emboss": true,
  "letter_depth": 0.5,
  "letter_size": 10,
  "letter_bottom": "V",
  "letter_top": "F",
  "show_base": true,
  "show_walls": true,
  "show_mech": true,
  "show_letter": true,
  "show_wall_left": true,
  "show_wall_right": true,
  "show_mech_base_ring": true,
  "show_mech_pillars": true,
  "show_mech_snap_beams": true,
  "show_bottom": true,
  "show_top": true,
  "show_rods": true,
  "show_stoppers": true,
  "show_tubing": true,
  "rows": 2,
  "cols": 2,
  "rod_extension": 10,
  "rotation_clearance": 2,
  "tubing_H": 2,
  "tubing_wall": 1
}'

render_mode() {
  local mode="$1"
  shift
  local parts="$*"

  echo "--- Rendering $mode ($parts) ---"

  local parts_json
  parts_json=$(echo "$parts" | tr ' ' '\n' | sed 's/.*/"&"/' | paste -sd, -)

  local payload
  payload=$(cat <<PAYLOAD
{
  "project": "$PROJECT",
  "mode": "$mode",
  "parameters": $DEFAULT_PARAMS,
  "parts": [$parts_json],
  "export_format": "stl"
}
PAYLOAD
)

  local response
  response=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/api/render" \
    -H "Content-Type: application/json" \
    -d "$payload")

  local http_code
  http_code=$(echo "$response" | tail -1)
  local body
  body=$(echo "$response" | sed '$d')

  if [ "$http_code" = "200" ]; then
    echo "  OK (HTTP $http_code) — cached"
  else
    echo "  FAILED (HTTP $http_code)"
    echo "  $body" | head -3
  fi
  echo ""
}

# Warm up all 3 modes
render_mode "unit" main
render_mode "assembly" bottom top
render_mode "grid" bottom top rods stoppers tubing

echo "=== Shareable Demo Links ==="
echo "  Unit:     $STUDIO_URL/project/$PROJECT/unit/standard"
echo "  Assembly: $STUDIO_URL/project/$PROJECT/assembly/standard"
echo "  Grid:     $STUDIO_URL/project/$PROJECT/grid/standard"
echo ""
echo "Done."
