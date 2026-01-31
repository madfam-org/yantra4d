#!/usr/bin/env bash
# Usage: ./scripts/dev.sh [--frontend-only]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.dev-pids"
mkdir -p "$PID_DIR"

# Kill any existing dev servers
"$SCRIPT_DIR/dev-stop.sh" 2>/dev/null || true

if [ "$1" != "--frontend-only" ]; then
  echo "Starting backend (Flask :5000)..."
  cd "$PROJECT_ROOT/web_interface/backend"
  python3 app.py &
  echo $! > "$PID_DIR/backend.pid"
  cd "$PROJECT_ROOT"
fi

echo "Starting frontend (Vite :5173)..."
cd "$PROJECT_ROOT/web_interface/frontend"
npm run dev &
echo $! > "$PID_DIR/frontend.pid"
cd "$PROJECT_ROOT"

echo ""
echo "Qubic Studio running:"
[ "$1" != "--frontend-only" ] && echo "  Backend:  http://localhost:5000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Stop with: ./scripts/dev-stop.sh"

wait
