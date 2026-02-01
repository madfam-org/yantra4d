#!/usr/bin/env bash
# Usage: ./scripts/dev.sh [--frontend-only|--studio-only|--landing-only|--no-landing]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.dev-pids"
mkdir -p "$PID_DIR"

# Kill any existing dev servers
"$SCRIPT_DIR/dev-stop.sh" 2>/dev/null || true

if [ "$1" != "--frontend-only" ]; then
  echo "Starting backend (Flask :5000)..."
  cd "$PROJECT_ROOT/apps/api"
  python3 app.py &
  echo $! > "$PID_DIR/backend.pid"
  cd "$PROJECT_ROOT"
fi

if [ "$1" != "--landing-only" ]; then
  echo "Starting studio (Vite :5173)..."
  cd "$PROJECT_ROOT/apps/studio"
  npm run dev &
  echo $! > "$PID_DIR/studio.pid"
  cd "$PROJECT_ROOT"
fi

if [ "$1" != "--frontend-only" ] && [ "$1" != "--studio-only" ]; then
  echo "Starting landing (Astro :4321)..."
  cd "$PROJECT_ROOT/apps/landing"
  npm run dev &
  echo $! > "$PID_DIR/landing.pid"
  cd "$PROJECT_ROOT"
fi

echo ""
echo "Qubic running:"
[ "$1" != "--frontend-only" ] && [ "$1" != "--studio-only" ] && [ "$1" != "--landing-only" ] && echo "  Backend:  http://localhost:5000"
[ "$1" != "--landing-only" ] && echo "  Studio:   http://localhost:5173"
[ "$1" != "--frontend-only" ] && [ "$1" != "--studio-only" ] && echo "  Landing:  http://localhost:4321"
echo ""
echo "Stop with: ./scripts/dev-stop.sh"

wait
