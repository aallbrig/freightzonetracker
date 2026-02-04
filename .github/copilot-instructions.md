# GitHub Copilot Instructions for FreightZoneTracker Project

## Project Overview
Develop a complete MVP for a static Hugo website named 'FreightZoneTracker' that allows users to query freight types (trucks, trains, ships) moving through predefined or custom zones (e.g., Indiana, Lake Superior). The site displays real-time/near real-time data on a map, standardized to HS codes for cargo. Use a Python CLI tool ('FreightCLI') to fetch data from free sources, extract/standardize it, store in SQLite, and export formatted JSON to the Hugo site's data directory for client-side JS rendering. Keep everything simple: No backend server, static generation via Hugo, client-side JS for interactivity.

## Key Requirements
- **Tech Stack**:
  - CLI: Python 3+ with Typer (for CLI), requests (API pulls), pandas (data processing), sqlite3 (DB), hashlib (dedup), json/os/pathlib/datetime (utils).
  - Website: Hugo (latest), Bootstrap 5 via CDN for styling, Leaflet.js (via CDN) for OpenStreetMap integration with zone drawing (use Leaflet.draw plugin via CDN).
  - Data Flow: CLI downloads/extracts data → SQLite → Formats JSON → Hugo data dir → JS fetches JSON and renders on map.
- **Free Data Sources** (focus on these; use env vars for any API keys):
  - Ships: MarineTraffic API (free tier: https://www.marinetraffic.com/en/ais-api-docs; signup for key).
  - Trains: AAR Weekly Rail Traffic Data (CSV/XML from https://www.aar.org/data-center/rail-traffic-data/; aggregate by commodity).
  - Trucks: FMCSA/DOT public APIs (e.g., https://www.fmcsa.dot.gov/developer; or free load boards like TruckSmarter if API available).
  - Standardize cargo to HS codes using a simple mapping dict (e.g., {'coal': '2701'}); extrapolate positions from manifests/ETAs (assume averages if needed).
- **CLI Features** (named 'freightcli.py'; root command 'freight'):
  - Pipeline subcommands: 'pipeline download' (source, zone, --realtime flag), 'pipeline extract' (file, zone), 'pipeline format' (zone, --output-dir override; default to repo_root/hugo/site/data/).
  - Status: 'status' (checks connectivity to sources).
  - Audit: Subcommands like 'audit dir', 'audit db', 'audit size', 'audit data', 'audit runs'.
  - DB: SQLite at ~/.local/share/freightcli/data.db with tables: sources, downloads, extractions, audits, pipeline_runs (exact schema as provided in prior responses).
  - Downloads to ~/.local/share/freightcli/downloads/{source}/{timestamp}.json/csv; use hashes for dedup.
  - Real-time: If supported (e.g., websockets for AIS), stream; else, one-off pulls.
  - JSON Format: {"zone": "Indiana", "transports": [{"type": "ship", "cargo_hs": "0803", "position": {"lat": 41.8, "lon": -87.6}, "route_progress": "50%", "eta": "2026-02-04T12:00"}] }.
- **Hugo Website**:
  - Structure: config.toml (theme: none/minimal; use partials/shortcodes).
  - Homepage (content/_index.md): Contains the tool as main content using shortcode {{% tool %}}.
  - Shortcode (layouts/shortcodes/tool.html): Bootstrap container with zone dropdown, map div, JS for Leaflet map, fetching JSON from /data/{zone}.json, adding markers/popups (cargo, type). Add draw control for custom zones (filter data by bounds).
  - Base template (layouts/_default/baseof.html): Include Bootstrap CDN (<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">) and Leaflet CDN (<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />, <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>); add Leaflet.draw if needed.
  - Data Dir: static/data/ for JSON files (populated by CLI).
  - Build: hugo --minify for deployment.
- **Repo Structure**:
  - freightcli.py (CLI script).
  - hugo/ (Hugo root): site/ (content, layouts, config.toml, static/data/).
  - README.md: Instructions to run CLI, build Hugo.
  - .gitignore: Ignore DB, downloads.
- **Strategy**: Use manifests/extrapolation for positions (not per-unit real-time to keep simple). Handle errors, log audits.

## Coding Guidelines
- Python CLI: Use Typer for commands; pandas for extraction; ensure HS mapping.
- JS: Client-side only; fetch JSON, render markers.
- Test: Include basic error handling, connectivity checks.
- MVP Focus: High success with JS/OpenStreetMap; defer Godot.

## Prompts for Copilot
- Generate CLI code with exact commands/schema.
- Create Hugo shortcode for tool with map/JS.
- Debug data flow from CLI to Hugo.
- Suggest improvements for zone filtering.
