#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${AI_OUYI_WEB_PORT:-8123}"
HOST="${AI_OUYI_WEB_HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

echo "AI-OuYi Web"
echo "root: $ROOT_DIR"
echo "host: $HOST"
echo "port: $PORT"

PIDS="$(lsof -ti "tcp:${PORT}" || true)"
if [[ -n "$PIDS" ]]; then
  echo "releasing port ${PORT}: ${PIDS//$'\n'/ }"
  kill $PIDS || true
  sleep 1

  REMAINING_PIDS="$(lsof -ti "tcp:${PORT}" || true)"
  if [[ -n "$REMAINING_PIDS" ]]; then
    echo "force releasing port ${PORT}: ${REMAINING_PIDS//$'\n'/ }"
    kill -9 $REMAINING_PIDS || true
    sleep 1
  fi
fi

if lsof -ti "tcp:${PORT}" >/dev/null 2>&1; then
  echo "port ${PORT} is still occupied" >&2
  exit 1
fi

cd "$ROOT_DIR/web/frontend"
if [[ ! -d node_modules ]]; then
  echo "installing frontend dependencies"
  npm install
fi

echo "building frontend"
npm run build

cd "$ROOT_DIR"
echo "starting web: http://${HOST}:${PORT}/"
exec "$PYTHON_BIN" web/backend/run_api.py
