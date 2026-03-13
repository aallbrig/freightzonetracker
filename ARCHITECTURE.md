# FreightZoneTracker Architecture

## Overview

FreightZoneTracker is a static web application that tracks freight movement (ships, trains, trucks) through geographic zones. The system consists of two main components:

1. **Python CLI Tool** (`freightcli.py`) - Data pipeline for fetching, processing, and formatting freight data
2. **Hugo Static Website** - Interactive visualization using OpenStreetMap and Leaflet.js

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources (APIs)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MarineTraffic│  │   AAR Rail   │  │  FMCSA/DOT   │      │
│  │  (Ships)     │  │   (Trains)   │  │   (Trucks)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    ┌────────▼────────┐
                    │   FreightCLI    │
                    │  (Python Tool)  │
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
  ┌───────▼────────┐                  ┌─────────▼─────────┐
  │ SQLite Database│                  │  Raw Downloads    │
  │  ~/.local/...  │                  │ ~/.local/.../     │
  │                │                  │   downloads/      │
  │ • sources      │                  │                   │
  │ • downloads    │                  │ • JSON files      │
  │ • extractions  │                  │ • CSV files       │
  │ • audits       │                  │ • Timestamped     │
  │ • pipeline_runs│                  │ • Deduplicated    │
  └────────────────┘                  └───────────────────┘
          │
          │ Format & Export
          │
  ┌───────▼────────────────────────────────────────┐
  │     Hugo Static Site Data Directory            │
  │     hugo/site/static/data/                     │
  │                                                │
  │  • Indiana.json                                │
  │  • Lake_Superior.json                          │
  │  • California.json                             │
  └───────┬────────────────────────────────────────┘
          │
          │ Build & Serve
          │
  ┌───────▼────────────────────────────────────────┐
  │         Hugo Static Website                    │
  │                                                │
  │  ┌──────────────────────────────────────┐     │
  │  │  Leaflet.js Map + Bootstrap UI       │     │
  │  │                                      │     │
  │  │  • Zone selector dropdown            │     │
  │  │  • Interactive map                   │     │
  │  │  • Freight markers                   │     │
  │  │  • Custom zone drawing               │     │
  │  │  • Client-side filtering             │     │
  │  └──────────────────────────────────────┘     │
  └────────────────────────────────────────────────┘
                      │
                      │ HTTP
                      ▼
               ┌─────────────┐
               │   Browser   │
               └─────────────┘
```

## Data Flow

### 1. Data Collection (CLI)

```bash
# Download raw data from sources
freight pipeline download --source=ships_marinetraffic --zone=Indiana

# Process:
1. Fetch data from API (or use mock data)
2. Save to downloads directory
3. Calculate hash for deduplication
4. Store metadata in SQLite database
```

### 2. Data Extraction (CLI)

```bash
# Extract and validate data
freight pipeline extract --file=/path/to/download.json --zone=Indiana

# Process:
1. Read downloaded file
2. Count records extracted
3. Log extraction to database
```

### 3. Data Formatting (CLI)

```bash
# Format for Hugo site
freight pipeline format --zone=Indiana

# Process:
1. Query latest downloads from database
2. Filter by zone bounds
3. Standardize cargo to HS codes
4. Generate JSON with structure:
   {
     "zone": "Indiana",
     "updated_at": "2026-02-04T01:00:00Z",
     "transports": [
       {
         "type": "ship",
         "cargo_hs": "2701",
         "cargo_name": "coal",
         "position": {"lat": 41.8, "lon": -87.6},
         "route_progress": "50%",
         "eta": "2026-02-05T08:00:00Z"
       }
     ]
   }
5. Write to hugo/site/static/data/{zone}.json
```

### 4. Website Generation (Hugo)

```bash
cd hugo/site && hugo server
```

Hugo renders the static site with:
- Base template with Bootstrap & Leaflet CDN links
- Homepage with map tool shortcode
- Static data files accessible at /data/{zone}.json

### 5. Client-Side Rendering (JavaScript)

1. User selects zone from dropdown
2. Fetch `/data/{zone}.json` via AJAX
3. Parse transport data
4. Add markers to Leaflet map
5. Bind popups with cargo details
6. Support custom zone drawing to filter markers

## Component Details

### CLI Tool (`freightcli.py`)

**Technology Stack:**
- Python 3.8+
- Typer (CLI framework)
- requests (HTTP client)
- pandas (data processing)
- sqlite3 (database)

**Commands:**

```
freight
├── status                    # Check API connectivity
├── pipeline
│   ├── download             # Fetch data from sources
│   ├── extract              # Extract records from files
│   └── format               # Format JSON for Hugo
└── audit
    ├── dir                  # Audit download directory
    ├── db                   # Audit database tables
    ├── size                 # Check data sizes
    ├── data                 # Validate integrity
    └── runs                 # Show pipeline history
```

**Database Schema:**

```sql
-- Data sources configuration
sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    type TEXT,
    url TEXT,
    api_key_env TEXT,
    created_at TIMESTAMP
)

-- Downloaded files with deduplication
downloads (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    zone TEXT,
    file_path TEXT,
    file_hash TEXT UNIQUE,  -- SHA256 for deduplication
    file_size INTEGER,
    realtime BOOLEAN,
    downloaded_at TIMESTAMP
)

-- Extraction records
extractions (
    id INTEGER PRIMARY KEY,
    download_id INTEGER,
    zone TEXT,
    records_extracted INTEGER,
    extracted_at TIMESTAMP
)

-- Audit log
audits (
    id INTEGER PRIMARY KEY,
    audit_type TEXT,
    details TEXT,
    audited_at TIMESTAMP
)

-- Pipeline execution history
pipeline_runs (
    id INTEGER PRIMARY KEY,
    command TEXT,
    status TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
)
```

### Hugo Website

**Directory Structure:**

```
hugo/site/
├── config.toml              # Hugo configuration
├── content/
│   └── _index.md            # Homepage content
├── layouts/
│   ├── _default/
│   │   ├── baseof.html      # Base template
│   │   ├── list.html        # List template
│   │   └── single.html      # Single page template
│   └── shortcodes/
│       └── tool.html        # Map tool shortcode
└── static/
    └── data/                # JSON data files (CLI output)
        ├── Indiana.json
        ├── Lake_Superior.json
        └── California.json
```

**Templates:**

1. **baseof.html**: Base template with:
   - Bootstrap 5 CSS/JS from CDN
   - Leaflet.js CSS/JS from CDN
   - Leaflet.draw plugin from CDN
   - Responsive navbar and footer

2. **tool.html**: Interactive map component with:
   - Zone selector dropdown
   - Leaflet map initialization
   - Marker rendering from JSON
   - Drawing tools for custom zones
   - Client-side filtering logic

### Data Format

**Zone JSON Structure:**

```json
{
  "zone": "Indiana",
  "updated_at": "2026-02-04T01:00:00Z",
  "transports": [
    {
      "type": "ship",           // ship | train | truck
      "cargo_hs": "2701",       // HS code
      "cargo_name": "coal",     // Human-readable name
      "position": {
        "lat": 41.8,            // Latitude
        "lon": -87.6            // Longitude
      },
      "route_progress": "50%",  // Optional
      "eta": "2026-02-05T08:00:00Z",      // Optional (ISO 8601)
      "destination": "Chicago"  // Optional
    }
  ]
}
```

## HS Code Mapping

Harmonized System codes for cargo standardization:

| Cargo Type       | HS Code |
|------------------|---------|
| Coal             | 2701    |
| Crude Oil        | 2709    |
| Petroleum        | 2710    |
| Iron Ore         | 2601    |
| Bananas          | 0803    |
| Containers       | 8609    |
| Grain/Wheat      | 1001    |
| Corn             | 1005    |
| Soybeans         | 1201    |
| Automobiles      | 8703    |
| Steel            | 7208    |
| Lumber           | 4403    |
| Cement           | 2523    |
| General Cargo    | 9999    |

## Zone Definitions

Predefined zones with geographic boundaries:

```python
ZONE_BOUNDS = {
    'Indiana': {
        'lat_min': 37.77, 'lat_max': 41.76,
        'lon_min': -88.09, 'lon_max': -84.78
    },
    'Lake_Superior': {
        'lat_min': 46.5, 'lat_max': 49.0,
        'lon_min': -92.0, 'lon_max': -84.5
    },
    'California': {
        'lat_min': 32.5, 'lat_max': 42.0,
        'lon_min': -124.5, 'lon_max': -114.1
    }
}
```

## Security & Privacy

- **No backend server**: Static site generation eliminates server vulnerabilities
- **API keys**: Stored in environment variables, never committed to code
- **Client-side only**: All data processing happens in the browser
- **Read-only**: Website cannot modify source data

## Scalability Considerations

**Current MVP Limitations:**
- Mock data for testing (production needs real APIs)
- Position extrapolation (not real-time tracking)
- Manual zone updates required
- Limited to predefined zones

**Future Enhancements:**
1. Real-time data streaming via WebSockets
2. Automatic periodic updates (cron jobs)
3. More data sources (ports, warehouses, load boards)
4. Historical data analysis and trends
5. Mobile app integration
6. Custom zone persistence
7. API for third-party integrations

## Development Workflow

1. **Setup**: Install dependencies, initialize database
2. **Data Collection**: Run download commands for each source/zone
3. **Data Processing**: Format data for Hugo
4. **Build**: Generate static site with Hugo
5. **Deploy**: Upload public/ directory to hosting
6. **Update**: Repeat steps 2-5 for data refresh

## Deployment Options

- **GitHub Pages**: Free, git-based deployment
- **Netlify**: Automatic builds from Git
- **Vercel**: Serverless with edge CDN
- **AWS S3 + CloudFront**: Scalable cloud hosting
- **Any static hosting**: nginx, Apache, etc.

## Monitoring & Maintenance

- **CLI audit commands**: Check data integrity
- **Pipeline run logs**: Track execution history
- **Hugo build logs**: Monitor site generation
- **Browser console**: Debug client-side issues

## Performance

- **Static files**: Fast loading, no server processing
- **CDN assets**: Bootstrap and Leaflet from CDN
- **Minimal JSON**: Only zone-specific data loaded
- **Client-side filtering**: No server requests for custom zones

## Testing

```bash
# Run comprehensive test suite
./test.sh

# Manual testing
python freightcli.py status
python freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana
python freightcli.py pipeline format --zone=Indiana
cd hugo/site && hugo server
```

## License

MIT License - See LICENSE file for details.
