#!/bin/bash
# Quick start script for FreightZoneTracker

echo "🚢 FreightZoneTracker Quick Start"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo "✓ Virtual environment created"
else
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

echo ""
echo "Downloading sample data..."
python freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana 2>&1 | grep -E "✓|Downloaded"
python freightcli.py pipeline download --source=trains_aar --zone=Indiana 2>&1 | grep -E "✓|Downloaded"
python freightcli.py pipeline download --source=trucks_fmcsa --zone=Indiana 2>&1 | grep -E "✓|Downloaded"

echo ""
echo "Downloading data for other zones..."
python freightcli.py pipeline download --source=ships_marinetraffic --zone=Lake_Superior 2>&1 | grep -E "✓|Downloaded"
python freightcli.py pipeline download --source=ships_marinetraffic --zone=California 2>&1 | grep -E "✓|Downloaded"
python freightcli.py pipeline download --source=trains_aar --zone=California 2>&1 | grep -E "✓|Downloaded"
python freightcli.py pipeline download --source=trucks_fmcsa --zone=California 2>&1 | grep -E "✓|Downloaded"

echo ""
echo "Formatting data for Hugo..."
python freightcli.py pipeline format --zone=Indiana 2>&1 | grep -E "✓|Formatted"
python freightcli.py pipeline format --zone=Lake_Superior 2>&1 | grep -E "✓|Formatted"
python freightcli.py pipeline format --zone=California 2>&1 | grep -E "✓|Formatted"

echo ""
echo "✓ Data pipeline complete!"
echo ""
echo "To start the Hugo server, run:"
echo "  cd hugo/site && hugo server"
echo ""
echo "Then visit: http://localhost:1313"
