#!/bin/bash
# Quick demonstration of FreightZoneTracker with AISHub real data

set -e

echo "🚢 FreightZoneTracker - Real Data Demo"
echo "======================================"
echo ""

# Check if AISHub username is set
if [ -z "$AISHUB_USERNAME" ]; then
    echo "⚠️  AISHUB_USERNAME not set"
    echo ""
    echo "To use REAL ship tracking data:"
    echo "1. Sign up for free account at https://www.aishub.net/"
    echo "2. Set your username: export AISHUB_USERNAME=\"your_username\""
    echo ""
    echo "Continuing with MOCK data for demo..."
    echo ""
else
    echo "✅ AISHUB_USERNAME is set - will fetch REAL ship data!"
    echo ""
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run: python -m venv venv && source venv/bin/activate && pip install typer requests pandas"
    exit 1
fi

# Check Python dependencies
echo "🔍 Checking dependencies..."
python -c "import typer, requests, pandas" 2>/dev/null || {
    echo "❌ Missing dependencies. Run: pip install typer requests pandas"
    exit 1
}
echo "✅ Dependencies OK"
echo ""

# Download data for all three zones
echo "📥 Downloading freight data..."
echo ""

for zone in Indiana Lake_Superior California; do
    echo "Zone: $zone"
    python freightcli.py pipeline download --source=ships_marinetraffic --zone=$zone 2>&1 | grep -v "DeprecationWarning" | grep -E "(Downloading|Found|Downloaded|⚠|✓)"
    python freightcli.py pipeline download --source=trains_aar --zone=$zone 2>&1 | grep -v "DeprecationWarning" | grep -E "(Downloading|Found|Downloaded|⚠|✓)"
    python freightcli.py pipeline download --source=trucks_fmcsa --zone=$zone 2>&1 | grep -v "DeprecationWarning" | grep -E "(Downloading|Found|Downloaded|⚠|✓)"
    echo ""
done

echo "📊 Formatting data for website..."
echo ""
for zone in Indiana Lake_Superior California; do
    python freightcli.py pipeline format --zone=$zone 2>&1 | grep -v "DeprecationWarning" | grep "✓"
done
echo ""

# Check Hugo
if ! command -v hugo &> /dev/null; then
    echo "❌ Hugo not found. Install with:"
    echo "  - macOS: brew install hugo"
    echo "  - Linux: sudo apt-get install hugo"
    echo "  - Or download from https://github.com/gohugoio/hugo/releases"
    exit 1
fi

echo "✅ Data pipeline complete!"
echo ""
echo "🌐 Starting Hugo server..."
echo ""
echo "Visit: http://localhost:1313"
echo "Press Ctrl+C to stop"
echo ""

cd hugo/site
hugo server
