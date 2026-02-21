#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.dev-pids"

for pidfile in "$PID_DIR"/*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile")
  name=$(basename "$pidfile" .pid)
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null && echo "Stopped $name (PID $pid)"
    pkill -P "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
done

# Fallback: kill any stray processes on known ports
lsof -ti:5000 | xargs kill 2>/dev/null || true
lsof -ti:5173 | xargs kill 2>/dev/null || true
lsof -ti:4321 | xargs kill 2>/dev/null || true

echo "All dev servers stopped."
