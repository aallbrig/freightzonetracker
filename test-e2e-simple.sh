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

# Check if MarkerCluster is included
if echo "$HTML" | grep -q "markercluster"; then
    echo "✓ MarkerCluster JS included"
else
    echo "❌ MarkerCluster JS not found"
    exit 1
fi

# Check if map element exists
if echo "$HTML" | grep -q 'id="map"'; then
    echo "✓ Map element present"
else
    echo "❌ Map element not found"
    exit 1
fi

# Check for sidebar region list
if echo "$HTML" | grep -q 'id="region-list"'; then
    echo "✓ Region sidebar present"
else
    echo "❌ Region sidebar not found"
    exit 1
fi

# Check i18n _t object is baked in
if echo "$HTML" | grep -q 'var _t'; then
    echo "✓ i18n _t object present"
else
    echo "❌ i18n _t object missing"
    exit 1
fi

# Check data files exist
for zone in Gulf_of_Mexico Great_Lakes East_Coast_US West_Coast_US Mediterranean; do
    if curl -fsS "$SITE_URL/data/${zone}.json" > /dev/null 2>&1; then
        echo "✓ Data file exists: ${zone}.json"
    else
        echo "⚠️  Data file missing: ${zone}.json"
    fi
done

# Check regions index
if curl -fsS "$SITE_URL/data/regions.json" > /dev/null 2>&1; then
    echo "✓ regions.json index exists"
else
    echo "❌ regions.json missing"
    exit 1
fi

# Check About page
if curl -fsS "$SITE_URL/about/" > /dev/null 2>&1; then
    echo "✓ About page accessible"
else
    echo "⚠️  About page not found at /about/"
fi

# Check Spanish and French homepages
for lang in es fr; do
    if curl -fsS "$SITE_URL/${lang}/" > /dev/null 2>&1; then
        echo "✓ /${lang}/ homepage accessible"
    else
        echo "⚠️  /${lang}/ homepage not found"
    fi
done

echo ""
echo "✅ All basic checks passed!"
