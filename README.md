# FreightZoneTracker

FreightZoneTracker is a maritime-first static web application for exploring freight movement through predefined or custom zones. It combines a Python CLI tool for data collection and formatting with a Hugo website for map-based visualization.

**Current MVP reality:** ships can use near-real-time AIS data via AISHub, while train and truck entries remain placeholders until the public-data parsers are implemented. See [REAL_DATA_SETUP.md](REAL_DATA_SETUP.md) for the honest source-by-source breakdown.

## What the MVP does well

- **Python CLI (`freightcli.py`)**: Fetch, extract, and format freight data from multiple sources
- **Data Sources**: 
  - **Ships**: Near-real-time AIS data via AISHub (free tier) - real source support today
  - **Trains**: Planned AAR weekly reports integration (currently placeholder data)
  - **Trucks**: Planned DOT Freight Analysis Framework integration (currently placeholder data)
- **Cargo Standardization**: Automatic mapping to HS (Harmonized System) codes
- **SQLite Database**: Local storage with audit trails
- **Hugo Website**: Static site with interactive OpenStreetMap visualization
- **Zone Filtering**: Predefined zones (Indiana, Lake Superior, California) with custom zone drawing support

## Prerequisites

- Python 3.8+
- Hugo (latest version)
- pip (Python package manager)
- (Optional) Free AISHub account for real ship data

## Quick Start

**Demo with real AIS ship data** (or mock data if no credentials):

```bash
# 1. Setup (one time)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. (Optional) Set AISHub credentials for REAL ship tracking
export AISHUB_USERNAME="your_username"  # Get free account at https://www.aishub.net/

# 3. Run the demo
./demo-real-data.sh
```

Then visit http://localhost:1313 to see the map!

## Documentation

- **[DATA_SOURCES.md](DATA_SOURCES.md)** - Comprehensive guide to all available data sources, costs, and quality
- **[REAL_DATA_SETUP.md](REAL_DATA_SETUP.md)** - Complete guide to setting up real data sources
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details and research findings
- **[FIXES.md](FIXES.md)** - Bug-fix notes and testing details

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or using a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Hugo

**macOS:**
```bash
brew install hugo
```

**Linux:**
```bash
sudo apt-get install hugo  # Debian/Ubuntu
# or
sudo snap install hugo
```

**Windows:**
```bash
choco install hugo-extended
# or download from https://github.com/gohugoio/hugo/releases
```

### 3. Make CLI Executable

```bash
chmod +x freightcli.py
```

## CLI Usage

### Initialize and Check Status

```bash
# Check connectivity to data sources
./freightcli.py status
```

### Pipeline Commands

#### Download Data

```bash
# Download ship data for Indiana
./freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana

# Download with real-time flag
./freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana --realtime

# Download train data for California
./freightcli.py pipeline download --source=trains_aar --zone=California

# Download truck data for Lake Superior
./freightcli.py pipeline download --source=trucks_fmcsa --zone=Lake_Superior
```

#### Extract Data

```bash
# Extract data from downloaded file
./freightcli.py pipeline extract --file=~/.local/share/freightcli/downloads/ships_marinetraffic/Indiana_20260204_123456.json --zone=Indiana
```

#### Format Data for Website

```bash
# Format data for Hugo site (default output: hugo/site/static/data/)
./freightcli.py pipeline format --zone=Indiana

# Format with custom output directory
./freightcli.py pipeline format --zone=Indiana --output-dir=/custom/path
```

### Audit Commands

```bash
# Audit downloads directory
./freightcli.py audit dir

# Audit database tables
./freightcli.py audit db

# Check data sizes
./freightcli.py audit size

# Validate data integrity
./freightcli.py audit data

# Show recent pipeline runs
./freightcli.py audit runs
```

## Complete Workflow Example

```bash
# 1. Download data for Indiana from all sources
./freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana
./freightcli.py pipeline download --source=trains_aar --zone=Indiana
./freightcli.py pipeline download --source=trucks_fmcsa --zone=Indiana

# 2. Format the data for the website
./freightcli.py pipeline format --zone=Indiana

# 3. Build and serve the Hugo site
cd hugo/site
hugo server

# Visit http://localhost:1313 to view the tracker
```

## Hugo Website

### Build for Production

```bash
cd hugo/site
hugo --minify
```

The static site will be generated in `hugo/site/public/`.

### Deploy to GitHub Pages

This repository uses the modern GitHub Pages artifact flow. No `gh-pages` branch is needed.

1. In GitHub repository settings, enable **Pages**.
2. Set the Pages source to **GitHub Actions**.
3. Push to `main` only when you want the current build promoted to production.

The deployment workflow in `.github/workflows/deploy-pages.yml` builds the Hugo site and deploys the generated artifact with `actions/deploy-pages`.

### Continuous Integration

The CI workflow in `.github/workflows/ci.yml` runs on pushes to `main` and on pull requests. It:

- installs Python, Node.js, and Hugo
- runs `pytest`
- runs the CLI/Hugo smoke tests in `test.sh`
- starts a local Hugo server
- runs the browser E2E tests

### Scheduled data refresh

The repository also includes `.github/workflows/refresh-data.yml`, which can:

- run on a schedule every 6 hours
- be triggered manually from the Actions tab
- refresh the tracked zone JSON files in `hugo/site/static/data`
- commit refreshed data back to `main` when the tracked output actually changes, which in turn triggers the Pages deploy workflow

To enable real ship data in GitHub Actions, add this repository secret:

```bash
AISHUB_USERNAME=your_aishub_username
```

If the secret is not configured, the workflow still runs, but ship downloads fall back to the CLI's mock data behavior.

### Release workflow

- Keep work local while iterating.
- Create logical commits as features harden.
- Push to `main` when you want GitHub Pages updated.
- Tag semver releases when the state is milestone-worthy:

```bash
git tag -a v0.2.0 -m "FreightZoneTracker v0.2.0"
git push origin main --tags
```

## Project Structure

```
freightzonetracker/
├── freightcli.py                    # Main CLI tool
├── README.md                        # This file
├── .gitignore                       # Git ignore rules
└── hugo/
    └── site/
        ├── config.toml              # Hugo configuration
        ├── content/
        │   └── _index.md            # Homepage content
        ├── layouts/
        │   ├── _default/
        │   │   └── baseof.html      # Base template
        │   └── shortcodes/
        │       └── tool.html        # Map tool shortcode
        └── static/
            └── data/                # JSON data files (generated by CLI)
                ├── Indiana.json
                ├── Lake_Superior.json
                └── California.json
```

## Data Storage

- **Database**: `~/.local/share/freightcli/data.db`
- **Downloads**: `~/.local/share/freightcli/downloads/{source}/`
- **Website Data**: `hugo/site/static/data/{zone}.json`

## Data Sources & API Keys

### Ships (Real-Time AIS Data - FREE)

The CLI now uses **AISHub** for real vessel position tracking:

1. **Sign up for free account**: https://www.aishub.net/
2. **Get your username** (no API key needed, just username)
3. **Set environment variable**:
   ```bash
   export AISHUB_USERNAME="your_username"
   ```
4. **Limitations**: 
   - Free tier: ~10 requests/minute
   - Provides: Real vessel positions, ship type, speed, course
   - Does NOT provide: Actual cargo manifest (inferred from vessel type)

**Without AISHub credentials**, the CLI falls back to mock data.

### Trains (AAR Weekly Reports)

- **Source**: Association of American Railroads (https://www.aar.org/data-center/rail-traffic-data/)
- **Data Type**: Aggregated weekly commodity volumes (NOT real-time positions)
- **Access**: Public, no API (CSV/PDF downloads)
- **Status**: Currently using mock data (manual download/parsing not yet implemented)

### Trucks (FAF Regional Flows)

- **Source**: DOT Freight Analysis Framework (https://ops.fhwa.dot.gov/freight/freight_analysis/faf/)
- **Data Type**: Regional freight flow estimates (quarterly updates)
- **Access**: Public datasets, no API
- **Status**: Currently using mock data (dataset parsing not yet implemented)

### Data Reality Check

⚠️ **Important**: True real-time cargo manifests are NOT publicly available for any transport mode due to security and commercial confidentiality. The best we can do:
- **Ships**: Real positions via AIS + cargo type inference
- **Trains/Trucks**: Aggregate flows + position estimates

## HS Code Mapping

Cargo types are standardized to HS (Harmonized System) codes:

- Coal: 2701
- Crude Oil: 2709
- Petroleum: 2710
- Iron Ore: 2601
- Bananas: 0803
- Containers: 8609
- Grain/Wheat: 1001
- Corn: 1005
- Soybeans: 1201
- Automobiles: 8703
- Steel: 7208
- Lumber: 4403
- Cement: 2523
- General Cargo: 9999

## Zones

Predefined zones with geographic boundaries:

- **Indiana**: 37.77°N to 41.76°N, -88.09°W to -84.78°W
- **Lake Superior**: 46.5°N to 49.0°N, -92.0°W to -84.5°W
- **California**: 32.5°N to 42.0°N, -124.5°W to -114.1°W

Custom zones can be drawn on the map using the drawing tools.

## Troubleshooting

### CLI Not Executable
```bash
chmod +x freightcli.py
```

### Python Dependencies Missing
```bash
pip install -r requirements.txt
```

### Hugo Not Found
Install Hugo using your package manager (see Installation section).

### No Data Showing on Map
1. Ensure you've run the pipeline format command
2. Check that JSON files exist in `hugo/site/static/data/`
3. Verify Hugo server is running

## Development

### Database Schema

The SQLite database includes:
- `sources`: Data source configurations
- `downloads`: Downloaded file records with deduplication
- `extractions`: Extraction metadata
- `audits`: Audit log entries
- `pipeline_runs`: Command execution history

### Adding New Data Sources

1. Add source entry to `init_db()` function
2. Create fetch function (e.g., `fetch_newsource_data()`)
3. Add source handling in `pipeline_download` command
4. Update README with new source instructions

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs/features.

## Support

For issues or questions, please open a GitHub issue.
