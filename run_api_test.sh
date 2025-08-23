#!/usr/bin/env bash
set -euo pipefail

HOSTS="127.0.0.1 ::1"
PORT=8000
TEST_CMD="python manage.py test main.tests.test_auth.AuthTests -v2"

# check listening sockets (ss preferred, lsof fallback)
is_listening=false
if command -v ss >/dev/null 2>&1; then
  out="$(ss -ltnp 2>/dev/null || true)"
  for h in $HOSTS; do
    if echo "$out" | grep -qE "${h//./\\.}:${PORT}"; then
      is_listening=true
      break
    fi
  done
elif command -v lsof >/dev/null 2>&1; then
  out="$(lsof -iTCP -sTCP:LISTEN -nP 2>/dev/null || true)"
  for h in $HOSTS; do
    if echo "$out" | grep -qE "${h//./\\.}:${PORT}"; then
      is_listening=true
      break
    fi
  done
fi

# final fallback: quick HTTP probe to localhost
if [ "$is_listening" = false ]; then
  if command -v curl >/dev/null 2>&1; then
    if curl -s --fail --max-time 2 "http://127.0.0.1:${PORT}/" >/dev/null; then
      is_listening=true
    fi
  fi
fi

if [ "$is_listening" = true ]; then
  echo "Server detected on localhost:${PORT} — running tests"
  exec $TEST_CMD
else
  echo "No server detected on localhost:${PORT}. Aborting."
  exit 1
fi
