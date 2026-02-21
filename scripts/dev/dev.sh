#!/usr/bin/env bash
# Usage: ./scripts/dev.sh [flags]
#   --api-only      Start backend only
#   --studio-only   Start studio only
#   --landing-only  Start landing only
#   --no-api        Start studio + landing
#   --no-studio     Start api + landing
#   --no-landing    Start api + studio
set -e

# Detect OpenSCAD: prefer Snapshot, fall back to stable release
if [ -x "/Applications/OpenSCAD-Snapshot.app/Contents/MacOS/OpenSCAD" ]; then
  export OPENSCAD_PATH="/Applications/OpenSCAD-Snapshot.app/Contents/MacOS/OpenSCAD"
elif [ -x "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD" ]; then
  export OPENSCAD_PATH="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
export OPENSCADPATH="$PROJECT_ROOT/libs:$PROJECT_ROOT/libs/dotSCAD/src"

# Local dev: debug mode on, auth + rate limiting off
export FLASK_DEBUG=true
export AUTH_ENABLED=false
PID_DIR="$PROJECT_ROOT/.dev-pids"
mkdir -p "$PID_DIR"

# Defaults: start everything
START_API=true
START_STUDIO=true
START_LANDING=true

# Parse all flags
for arg in "$@"; do
  case "$arg" in
    --api-only)     START_STUDIO=false; START_LANDING=false ;;
    --studio-only)  START_API=false;    START_LANDING=false ;;
    --landing-only) START_API=false;    START_STUDIO=false  ;;
    --no-api)       START_API=false     ;;
    --no-studio)    START_STUDIO=false  ;;
    --no-landing)   START_LANDING=false ;;
    *)
      echo "Unknown flag: $arg"
      echo "Usage: ./scripts/dev.sh [--api-only|--studio-only|--landing-only|--no-api|--no-studio|--no-landing]"
      exit 1
      ;;
  esac
done

# Kill any existing dev servers
"$SCRIPT_DIR/dev-stop.sh" 2>/dev/null || true

if [ "$START_API" = true ]; then
  echo "Starting backend (Flask :5000)..."
  cd "$PROJECT_ROOT/apps/api"
  if [ -d ".venv" ]; then
    source .venv/bin/activate
  fi
  python3 app.py &
  echo $! > "$PID_DIR/backend.pid"
  cd "$PROJECT_ROOT"
fi

if [ "$START_STUDIO" = true ]; then
  echo "Starting studio (Vite :5173)..."
  cd "$PROJECT_ROOT/apps/studio"
  npm run dev &
  echo $! > "$PID_DIR/studio.pid"
  cd "$PROJECT_ROOT"
fi

if [ "$START_LANDING" = true ]; then
  echo "Starting landing (Astro :4321)..."
  cd "$PROJECT_ROOT/apps/landing"
  npm run dev &
  echo $! > "$PID_DIR/landing.pid"
  cd "$PROJECT_ROOT"
fi

echo ""
echo "Yantra4D running:"
[ "$START_API" = true ]     && echo "  Backend:  http://localhost:5000"
[ "$START_STUDIO" = true ]  && echo "  Studio:   http://localhost:5173"
[ "$START_LANDING" = true ] && echo "  Landing:  http://localhost:4321"
echo ""
echo "Stop with: ./scripts/dev-stop.sh"

wait
