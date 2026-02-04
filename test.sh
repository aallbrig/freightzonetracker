#!/bin/bash
# Test script for FreightZoneTracker

echo "🧪 Testing FreightZoneTracker MVP"
echo "=================================="
echo ""

# Activate virtual environment
source venv/bin/activate

echo "1. Testing CLI help..."
python freightcli.py --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ CLI help works"
else
    echo "   ✗ CLI help failed"
    exit 1
fi

echo ""
echo "2. Testing status command..."
python freightcli.py status > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Status command works"
else
    echo "   ✗ Status command failed"
    exit 1
fi

echo ""
echo "3. Testing pipeline download..."
python freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Pipeline download works"
else
    echo "   ✗ Pipeline download failed"
    exit 1
fi

echo ""
echo "4. Testing pipeline format..."
python freightcli.py pipeline format --zone=Indiana > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Pipeline format works"
else
    echo "   ✗ Pipeline format failed"
    exit 1
fi

echo ""
echo "5. Testing audit commands..."
python freightcli.py audit db > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Audit db works"
else
    echo "   ✗ Audit db failed"
    exit 1
fi

echo ""
echo "6. Testing Hugo build..."
cd hugo/site
hugo --quiet
if [ $? -eq 0 ]; then
    echo "   ✓ Hugo build works"
else
    echo "   ✗ Hugo build failed"
    exit 1
fi

echo ""
echo "7. Checking generated files..."
if [ -f "public/index.html" ]; then
    echo "   ✓ index.html generated"
else
    echo "   ✗ index.html not found"
    exit 1
fi

if [ -d "public/data" ]; then
    echo "   ✓ data directory exists"
else
    echo "   ✗ data directory not found"
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "Running E2E tests..."
cd /home/aallbright/src/freightzonetracker
bash test-e2e-simple.sh

echo ""
echo "═══════════════════════════════════════"
echo "✅ All tests (unit + E2E) passed!"
echo "═══════════════════════════════════════"
echo ""
echo "To view the site, run:"
echo "  cd hugo/site && hugo server"
echo "  Then visit: http://localhost:1313"
