#!/bin/bash
# Test script for FreightZoneTracker

set -euo pipefail

SITE_PORT="${SITE_PORT:-13131}"
SITE_URL="${SITE_URL:-http://127.0.0.1:${SITE_PORT}}"
HUGO_LOG="$(mktemp)"
FORMAT_OUTPUT_DIR="$(mktemp -d)"
HUGO_PID=""

cleanup() {
    if [ -n "$HUGO_PID" ] && kill -0 "$HUGO_PID" 2>/dev/null; then
        kill "$HUGO_PID"
    fi
    rm -f "$HUGO_LOG"
    rm -rf "$FORMAT_OUTPUT_DIR"
}

trap cleanup EXIT

echo "🧪 Testing FreightZoneTracker MVP"
echo "=================================="
echo ""

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

echo "0. Running Python unit tests..."
pytest -q
echo "   ✓ Python unit tests passed"

echo ""
echo "1. Testing CLI help..."
python freightcli.py --help > /dev/null 2>&1
echo "   ✓ CLI help works"

echo ""
echo "2. Testing status command..."
python freightcli.py status > /dev/null 2>&1
echo "   ✓ Status command works"

echo ""
echo "3. Testing pipeline download..."
python freightcli.py pipeline download --source=ships_marinetraffic --zone=Gulf_of_Mexico > /dev/null 2>&1
echo "   ✓ Pipeline download works"

echo ""
echo "4. Testing pipeline format..."
python freightcli.py pipeline format --zone=Gulf_of_Mexico --output-dir "$FORMAT_OUTPUT_DIR" > /dev/null 2>&1
echo "   ✓ Pipeline format works"

echo ""
echo "5. Testing audit commands..."
python freightcli.py audit db > /dev/null 2>&1
python freightcli.py audit vessels > /dev/null 2>&1
echo "   ✓ Audit db + vessels works"

echo ""
echo "6. Testing Hugo build..."
(cd hugo/site && hugo --quiet)
echo "   ✓ Hugo build works"

echo ""
echo "7. Checking generated files..."
if [ -f "hugo/site/public/index.html" ]; then
    echo "   ✓ index.html generated"
else
    echo "   ✗ index.html not found"
    exit 1
fi

if [ -d "hugo/site/public/data" ]; then
    echo "   ✓ data directory exists"
else
    echo "   ✗ data directory not found"
    exit 1
fi

echo ""
echo "8. Starting Hugo test server..."
(cd hugo/site && hugo server --bind 127.0.0.1 --port "$SITE_PORT" --baseURL "$SITE_URL/" --disableFastRender > "$HUGO_LOG" 2>&1) &
HUGO_PID=$!

for _ in $(seq 1 20); do
    if curl -fsS "$SITE_URL/" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! curl -fsS "$SITE_URL/" > /dev/null 2>&1; then
    echo "   ✗ Hugo test server did not start"
    cat "$HUGO_LOG"
    exit 1
fi
echo "   ✓ Hugo test server is running"

echo ""
echo "9. Running simple E2E tests..."
SITE_URL="$SITE_URL" bash test-e2e-simple.sh

echo ""
echo "10. Running browser E2E tests..."
SITE_URL="$SITE_URL" npm test

echo ""
echo "═══════════════════════════════════════"
echo "✅ All tests passed!"
echo "═══════════════════════════════════════"
echo ""
echo "To view the site locally, run:"
echo "  cd hugo/site && hugo server"
echo "  Then visit: http://localhost:1313"
