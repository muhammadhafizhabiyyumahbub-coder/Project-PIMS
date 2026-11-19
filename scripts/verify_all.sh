#!/bin/sh
# PIMS — one-command verification gate.
# Usage: sh scripts/verify_all.sh   (from anywhere; paths resolve from this file)
set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PY="$BACKEND/.venv/Scripts/python.exe"
STATUS=0
SUMMARY=""

step() {
  name="$1"; shift
  echo ""
  echo "=============================================================="
  echo ">>> $name"
  echo "=============================================================="
  if "$@"; then
    SUMMARY="$SUMMARY
PASS  $name"
  else
    SUMMARY="$SUMMARY
FAIL  $name"
    STATUS=1
    echo ">>> $name FAILED — stopping"
    print_summary
    exit 1
  fi
}

print_summary() {
  echo ""
  echo "=============================================================="
  echo "SUMMARY"
  echo "=============================================================="
  printf '%s\n' "$SUMMARY" | sed '/^$/d'
  if [ "$STATUS" -eq 0 ]; then
    echo ""
    echo "RESULT: ALL CHECKS PASSED"
  else
    echo ""
    echo "RESULT: FAILURES PRESENT"
  fi
}

run_backend_tests() {
  cd "$BACKEND" && "$PY" -m pytest tests -q
}

run_frontend_lint() {
  cd "$FRONTEND" && npm run lint
}

run_frontend_build() {
  cd "$FRONTEND" && npm run build
}

run_lock_check() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "skip: uv not installed (lock check skipped)"
    return 0
  fi
  cd "$BACKEND" && uv lock --check
}

step "backend pytest" run_backend_tests
step "frontend eslint" run_frontend_lint
step "frontend next build" run_frontend_build
step "uv lock consistency" run_lock_check

print_summary
exit "$STATUS"