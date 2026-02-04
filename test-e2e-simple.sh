#!/bin/bash
# Simple E2E test script for FreightZoneTracker

echo "🧪 FreightZoneTracker E2E Tests"
echo "================================"
echo ""

cd "$(dirname "$0")"

# Test 1: Check if data files exist
echo "Test 1: Data files exist"
if [ -f "hugo/site/static/data/Indiana.json" ] && \
   [ -f "hugo/site/static/data/Lake_Superior.json" ] && \
   [ -f "hugo/site/static/data/California.json" ]; then
    echo "   ✓ PASS - All data files exist"
else
    echo "   ✗ FAIL - Missing data files"
    exit 1
fi

# Test 2: Validate JSON files
echo ""
echo "Test 2: JSON files are valid"
for file in hugo/site/static/data/*.json; do
    if python3 -m json.tool "$file" > /dev/null 2>&1; then
        echo "   ✓ PASS - $(basename $file) is valid JSON"
    else
        echo "   ✗ FAIL - $(basename $file) is invalid JSON"
        exit 1
    fi
done

# Test 3: JSON files have transports
echo ""
echo "Test 3: JSON files contain transport data"
for file in hugo/site/static/data/*.json; do
    count=$(python3 -c "import json; data=json.load(open('$file')); print(len(data.get('transports', [])))")
    if [ "$count" -gt 0 ]; then
        echo "   ✓ PASS - $(basename $file) has $count transports"
    else
        echo "   ✗ FAIL - $(basename $file) has no transports"
        exit 1
    fi
done

# Test 4: Hugo build succeeds
echo ""
echo "Test 4: Hugo build succeeds"
cd hugo/site
if hugo --quiet 2>&1; then
    echo "   ✓ PASS - Hugo build successful"
else
    echo "   ✗ FAIL - Hugo build failed"
    exit 1
fi

# Test 5: public/index.html exists and contains map
echo ""
echo "Test 5: Generated HTML contains map elements"
if [ -f "public/index.html" ]; then
    if grep -q "id=\"map\"" public/index.html && \
       grep -q "leaflet" public/index.html && \
       grep -q "DOMContentLoaded" public/index.html; then
        echo "   ✓ PASS - HTML contains map and proper script loading"
    else
        echo "   ✗ FAIL - HTML missing map or script elements"
        exit 1
    fi
else
    echo "   ✗ FAIL - public/index.html not generated"
    exit 1
fi

# Test 6: Data files accessible in public
echo ""
echo "Test 6: Data files accessible in public build"
if [ -f "public/data/Indiana.json" ] && \
   [ -f "public/data/Lake_Superior.json" ] && \
   [ -f "public/data/California.json" ]; then
    echo "   ✓ PASS - Data files accessible in public/"
else
    echo "   ✗ FAIL - Data files not in public/"
    exit 1
fi

# Test 7: Start Hugo server and test HTTP response
echo ""
echo "Test 7: Hugo server runs and responds"
cd ../..
timeout 5 hugo server --port 1314 --bind 127.0.0.1 -s hugo/site > /dev/null 2>&1 &
HUGO_PID=$!
sleep 2

if curl -s -f http://localhost:1314/ > /dev/null 2>&1; then
    echo "   ✓ PASS - Hugo server responds on http://localhost:1314/"
else
    echo "   ✗ FAIL - Hugo server not responding"
    kill $HUGO_PID 2>/dev/null
    exit 1
fi

# Test 8: Check that data endpoint works
echo ""
echo "Test 8: Data endpoint serves JSON"
if curl -s -f http://localhost:1314/data/Indiana.json | python3 -m json.tool > /dev/null 2>&1; then
    echo "   ✓ PASS - Data endpoint serves valid JSON"
else
    echo "   ✗ FAIL - Data endpoint not working"
    kill $HUGO_PID 2>/dev/null
    exit 1
fi

# Cleanup
kill $HUGO_PID 2>/dev/null

echo ""
echo "═══════════════════════════════════════"
echo "✅ All E2E tests passed!"
echo "═══════════════════════════════════════"
echo ""
echo "To view the site:"
echo "  cd hugo/site && hugo server"
echo "  Visit: http://localhost:1313"
echo ""
