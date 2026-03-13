#!/bin/bash
# Simple E2E test for FreightZoneTracker

set -euo pipefail

SITE_URL="${SITE_URL:-http://localhost:1313}"

echo "🧪 Testing FreightZoneTracker Website..."
echo ""

# Check if server is running
if ! curl -fsS "$SITE_URL/" > /dev/null; then
    echo "❌ Server not running at $SITE_URL"
    exit 1
fi
echo "✓ Server is running"

# Check if HTML loads
HTML=$(curl -fsS "$SITE_URL/")
if echo "$HTML" | grep -q "FreightZoneTracker"; then
    echo "✓ Page loads with title"
else
    echo "❌ Page title not found"
    exit 1
fi

# Check if Leaflet scripts are included
if echo "$HTML" | grep -q "leaflet.js"; then
    echo "✓ Leaflet JS included"
else
    echo "❌ Leaflet JS not found"
    exit 1
fi

# Check if map element exists
if echo "$HTML" | grep -q 'id="map"'; then
    echo "✓ Map element present"
else
    echo "❌ Map element not found"
    exit 1
fi

# Check if initializeMap function exists (new code)
if echo "$HTML" | grep -q "function initializeMap"; then
    echo "✓ New async map initialization code present"
else
    echo "❌ Old code detected"
    exit 1
fi

# Check if data files exist
for zone in Indiana California Lake_Superior; do
    if curl -fsS "$SITE_URL/data/${zone}.json" > /dev/null 2>&1; then
        echo "✓ Data file exists: ${zone}.json"
    else
        echo "⚠️  Data file missing: ${zone}.json"
    fi
done

echo ""
echo "✅ All basic checks passed!"
echo ""
echo "To test in browser:"
echo "  1. Open $SITE_URL/"
echo "  2. Check browser console (F12) for errors"
echo "  3. Select different zones from dropdown"
echo "  4. Click markers to see cargo details"
