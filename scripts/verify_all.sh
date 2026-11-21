#!/bin/bash
# Universal verification script

set -e

# Detect python
if [ -d "backend/.venv" ]; then
    PYTHON="backend/.venv/bin/python"
    # Windows fallback
    if [ -f "backend/.venv/Scripts/python.exe" ]; then
        PYTHON="backend/.venv/Scripts/python.exe"
    fi
else
    # Try uv if venv doesn't exist
    if command -v uv &> /dev/null; then
        PYTHON="uv run python"
    else
        echo "No virtualenv or uv detected."
        exit 1
    fi
fi

echo "--- 1. Running Tests ---"
if [ -f "$PYTHON" ] || command -v uv &> /dev/null; then
    export PIMS_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/pims_test"
    cd backend
    ../$PYTHON -m pytest tests/ -v
    cd ..
    echo "Tests PASSED"
else
    echo "SKIPPED: pytest not found"
fi

echo "--- 2. Linting ---"
if command -v npm &> /dev/null && [ -f "frontend/package.json" ]; then
    cd frontend
    npm run lint
    cd ..
    echo "Linting PASSED"
else
    echo "SKIPPED: npm or package.json not found in frontend/"
    exit 1
fi

echo "--- 3. Building ---"
if command -v npm &> /dev/null && [ -f "frontend/package.json" ]; then
    cd frontend
    npm run build
    cd ..
    echo "Build PASSED"
else
    echo "SKIPPED: npm or package.json not found in frontend/"
    exit 1
fi

echo "--- 4. Dependency Check ---"
if command -v uv &> /dev/null; then
    cd backend
    uv lock --check
    cd ..
    echo "Dependencies PASSED"
else
    echo "SKIPPED: uv not found"
    exit 1
fi