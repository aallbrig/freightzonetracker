#!/usr/bin/env python3
"""
FreightCLI - CLI tool for fetching, extracting, and formatting freight data.
"""

import os
import sys
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
import requests
import pandas as pd

app = typer.Typer(help="FreightCLI - Freight data pipeline tool")
pipeline_app = typer.Typer(help="Pipeline commands for download, extract, format")
audit_app = typer.Typer(help="Audit commands for checking data integrity")

app.add_typer(pipeline_app, name="pipeline")
app.add_typer(audit_app, name="audit")

# Configuration
DATA_DIR = Path.home() / ".local" / "share" / "freightcli"
DOWNLOADS_DIR = DATA_DIR / "downloads"
DB_PATH = DATA_DIR / "data.db"
REPO_ROOT = Path(__file__).parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "hugo" / "site" / "static" / "data"

# HS Code mapping (simplified for MVP)
HS_CODE_MAP = {
    'coal': '2701',
    'crude_oil': '2709',
    'petroleum': '2710',
    'iron_ore': '2601',
    'bananas': '0803',
    'containers': '8609',
    'grain': '1001',
    'wheat': '1001',
    'corn': '1005',
    'soybeans': '1201',
    'automobiles': '8703',
    'steel': '7208',
    'lumber': '4403',
    'cement': '2523',
    'general_cargo': '9999',
}

# Zone boundaries (simplified)
ZONE_BOUNDS = {
    'Indiana': {'lat_min': 37.77, 'lat_max': 41.76, 'lon_min': -88.09, 'lon_max': -84.78},
    'Lake_Superior': {'lat_min': 46.5, 'lat_max': 49.0, 'lon_min': -92.0, 'lon_max': -84.5},
    'California': {'lat_min': 32.5, 'lat_max': 42.0, 'lon_min': -124.5, 'lon_max': -114.1},
}


def init_db():
    """Initialize SQLite database with schema."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    # Sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            url TEXT,
            api_key_env TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Downloads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            zone TEXT,
            file_path TEXT,
            file_hash TEXT UNIQUE,
            file_size INTEGER,
            realtime BOOLEAN DEFAULT 0,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    """)
    
    # Extractions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_id INTEGER,
            zone TEXT,
            records_extracted INTEGER,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (download_id) REFERENCES downloads(id)
        )
    """)
    
    # Audits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_type TEXT,
            details TEXT,
            audited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Pipeline runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT,
            status TEXT,
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    # Insert default sources
    sources = [
        ('ships_marinetraffic', 'ships', 'https://www.aishub.net/', 'AISHUB_USERNAME'),
        ('trains_aar', 'trains', 'https://www.aar.org/data-center/', None),
        ('trucks_fmcsa', 'trucks', 'https://ops.fhwa.dot.gov/freight/freight_analysis/faf/', None),
    ]
    
    for name, type_, url, api_key_env in sources:
        cursor.execute("""
            INSERT INTO sources (name, type, url, api_key_env)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                type = excluded.type,
                url = excluded.url,
                api_key_env = excluded.api_key_env
        """, (name, type_, url, api_key_env))
    
    conn.commit()
    conn.close()


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_in_zone(lat: float, lon: float, zone: str) -> bool:
    """Check if coordinates are within zone bounds."""
    if zone not in ZONE_BOUNDS:
        return True  # Unknown zones accept all
    bounds = ZONE_BOUNDS[zone]
    return (bounds['lat_min'] <= lat <= bounds['lat_max'] and
            bounds['lon_min'] <= lon <= bounds['lon_max'])


def log_pipeline_run(command: str, status: str, error_message: Optional[str] = None):
    """Log pipeline run to database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pipeline_runs (command, status, error_message, completed_at)
        VALUES (?, ?, ?, ?)
    """, (command, status, error_message, datetime.now()))
    conn.commit()
    conn.close()


def fetch_ships_data(zone: str, realtime: bool) -> dict:
    """Fetch ship data from AISHub free API (real data) or fallback to mock."""
    # Zone bounding boxes (lat_min, lat_max, lon_min, lon_max)
    zone_bounds = {
        'Indiana': (37.77, 41.76, -88.10, -84.78),  # Indiana + Lake Michigan shore
        'Lake_Superior': (46.5, 49.0, -92.0, -84.5),  # Lake Superior
        'California': (32.5, 42.0, -124.5, -114.0),  # California coast
    }
    
    if zone not in zone_bounds:
        typer.echo(f"⚠ Unknown zone: {zone}, using mock data")
        return {'ships': []}
    
    # Try AISHub API (requires free account username)
    aishub_user = os.getenv('AISHUB_USERNAME', '')
    
    if not aishub_user:
        typer.echo("⚠ AISHUB_USERNAME not set, using mock data (get free account at https://www.aishub.net/)")
        # Fallback to mock data
        mock_data = {
            'Indiana': [
                {'mmsi': '367123456', 'lat': 41.8, 'lon': -87.6, 'cargo': 'coal', 'eta': '2026-02-05T08:00:00Z'},
            ],
            'Lake_Superior': [
                {'mmsi': '316234567', 'lat': 47.5, 'lon': -88.0, 'cargo': 'iron_ore', 'eta': '2026-02-04T20:00:00Z'},
            ],
            'California': [
                {'mmsi': '338456789', 'lat': 33.7, 'lon': -118.3, 'cargo': 'containers', 'eta': '2026-02-07T10:00:00Z'},
            ],
        }
        return {'ships': mock_data.get(zone, [])}
    
    try:
        lat_min, lat_max, lon_min, lon_max = zone_bounds[zone]
        url = "http://data.aishub.net/ws.php"
        params = {
            'username': aishub_user,
            'format': '1',
            'output': 'json',
            'compress': '0',
            'latmin': lat_min,
            'latmax': lat_max,
            'lonmin': lon_min,
            'lonmax': lon_max,
        }
        
        typer.echo(f"🌐 Fetching real AIS data from AISHub for {zone}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        ships = []
        
        # Parse AISHub response format: [{"MMSI": "...", "LAT": ..., "LON": ..., "SHIP_TYPE": ...}, ...]
        for vessel in data:
            if isinstance(vessel, dict):
                # Infer cargo from ship type
                ship_type = vessel.get('SHIP_TYPE', 0)
                cargo = infer_cargo_from_ship_type(ship_type)
                
                ships.append({
                    'mmsi': vessel.get('MMSI', 'unknown'),
                    'lat': float(vessel.get('LAT', 0)),
                    'lon': float(vessel.get('LON', 0)),
                    'cargo': cargo,
                    'ship_type': ship_type,
                    'name': vessel.get('NAME', ''),
                    'speed': vessel.get('SOG', 0),  # Speed over ground
                    'course': vessel.get('COG', 0),  # Course over ground
                    'eta': None,  # Not available in free tier
                })
        
        typer.echo(f"✓ Found {len(ships)} vessels in {zone}")
        return {'ships': ships}
        
    except Exception as e:
        typer.echo(f"⚠ Error fetching AISHub data: {e}, using mock data")
        mock_data = {
            'Indiana': [
                {'mmsi': '367123456', 'lat': 41.8, 'lon': -87.6, 'cargo': 'coal', 'eta': '2026-02-05T08:00:00Z'},
            ],
        }
        return {'ships': mock_data.get(zone, [])}


def infer_cargo_from_ship_type(ship_type: int) -> str:
    """Infer cargo type from AIS ship type code."""
    # AIS ship type codes: https://help.marinetraffic.com/hc/en-us/articles/205579997-What-is-the-significance-of-the-AIS-Shiptype-number-
    cargo_map = {
        70: 'general_cargo',  # Cargo ships
        71: 'general_cargo',
        72: 'general_cargo',
        73: 'general_cargo',
        74: 'general_cargo',
        75: 'general_cargo',
        76: 'general_cargo',
        77: 'general_cargo',
        78: 'general_cargo',
        79: 'general_cargo',
        80: 'crude_oil',  # Tankers
        81: 'crude_oil',
        82: 'crude_oil',
        83: 'crude_oil',
        84: 'crude_oil',
        85: 'petroleum',
        86: 'petroleum',
        87: 'petroleum',
        88: 'petroleum',
        89: 'petroleum',
    }
    return cargo_map.get(ship_type, 'containers')  # Default to containers


def fetch_trains_data(zone: str) -> dict:
    """Fetch train data from AAR (mocked for MVP)."""
    # Mock data - in production, parse AAR CSV/XML
    mock_data = {
        'Indiana': [
            {'train_id': 'CN1234', 'lat': 40.5, 'lon': -86.5, 'cargo': 'grain', 'destination': 'Chicago'},
            {'train_id': 'UP5678', 'lat': 39.9, 'lon': -86.0, 'cargo': 'automobiles', 'destination': 'Detroit'},
        ],
        'California': [
            {'train_id': 'BNSF9012', 'lat': 34.0, 'lon': -118.2, 'cargo': 'containers', 'destination': 'Los Angeles'},
        ],
    }
    
    return {'trains': mock_data.get(zone, [])}


def fetch_trucks_data(zone: str) -> dict:
    """Fetch truck data from FMCSA/DOT (mocked for MVP)."""
    # Mock data - in production, use real API
    mock_data = {
        'Indiana': [
            {'truck_id': 'TRK001', 'lat': 39.8, 'lon': -86.15, 'cargo': 'general_cargo', 'destination': 'Indianapolis'},
            {'truck_id': 'TRK002', 'lat': 41.6, 'lon': -87.5, 'cargo': 'steel', 'destination': 'Gary'},
        ],
        'California': [
            {'truck_id': 'TRK003', 'lat': 37.8, 'lon': -122.4, 'cargo': 'general_cargo', 'destination': 'San Francisco'},
        ],
    }
    
    return {'trucks': mock_data.get(zone, [])}


@pipeline_app.command("download")
def pipeline_download(
    source: str = typer.Option(..., help="Source name (e.g., ships_marinetraffic or ships_aishub)"),
    zone: str = typer.Option(..., help="Zone name (e.g., Indiana)"),
    realtime: bool = typer.Option(False, help="Enable real-time mode")
):
    """Download data from specified source for a zone."""
    init_db()
    command = f"pipeline download --source={source} --zone={zone} --realtime={realtime}"
    
    try:
        typer.echo(f"Downloading {source} data for zone: {zone}")
        
        # Fetch data based on source
        if source in {'ships_marinetraffic', 'ships_aishub'}:
            data = fetch_ships_data(zone, realtime)
            source = 'ships_marinetraffic'
        elif source == 'trains_aar':
            data = fetch_trains_data(zone)
        elif source == 'trucks_fmcsa':
            data = fetch_trucks_data(zone)
        else:
            raise ValueError(f"Unknown source: {source}")
        
        # Save to downloads directory
        source_dir = DOWNLOADS_DIR / source
        source_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = source_dir / f"{zone}_{timestamp}.json"
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Record in database
        file_hash = get_file_hash(file_path)
        file_size = file_path.stat().st_size
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sources WHERE name = ?", (source,))
        source_id = cursor.fetchone()[0]
        
        try:
            cursor.execute("""
                INSERT INTO downloads (source_id, zone, file_path, file_hash, file_size, realtime)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (source_id, zone, str(file_path), file_hash, file_size, realtime))
            conn.commit()
        except sqlite3.IntegrityError:
            typer.echo(f"⚠ Duplicate data detected (same hash already exists)")
            conn.rollback()
            file_path.unlink(missing_ok=True)
        
        conn.close()
        
        typer.echo(f"✓ Downloaded to: {file_path}")
        typer.echo(f"  File size: {file_size} bytes")
        typer.echo(f"  Hash: {file_hash[:16]}...")
        
        log_pipeline_run(command, "success")
        
    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        try:
            log_pipeline_run(command, "failed", str(e))
        except:
            pass  # Avoid secondary errors if DB is locked
        raise typer.Exit(1)


@pipeline_app.command("extract")
def pipeline_extract(
    file: str = typer.Option(..., help="Path to downloaded file"),
    zone: str = typer.Option(..., help="Zone name")
):
    """Extract and standardize data from downloaded file."""
    init_db()
    command = f"pipeline extract --file={file} --zone={zone}"
    
    try:
        file_path = Path(file)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file}")
        
        typer.echo(f"Extracting data from: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        records_extracted = 0
        for key in data:
            records_extracted += len(data[key])
        
        # Record extraction
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        
        file_hash = get_file_hash(file_path)
        cursor.execute("SELECT id FROM downloads WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        download_id = result[0] if result else None
        
        cursor.execute("""
            INSERT INTO extractions (download_id, zone, records_extracted)
            VALUES (?, ?, ?)
        """, (download_id, zone, records_extracted))
        
        conn.commit()
        conn.close()
        
        typer.echo(f"✓ Extracted {records_extracted} records")
        log_pipeline_run(command, "success")
        
    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        log_pipeline_run(command, "failed", str(e))
        raise typer.Exit(1)


@pipeline_app.command("format")
def pipeline_format(
    zone: str = typer.Option(..., help="Zone name to format"),
    output_dir: Optional[str] = typer.Option(None, help="Override output directory")
):
    """Format extracted data to JSON for Hugo site."""
    init_db()
    command = f"pipeline format --zone={zone}"
    
    try:
        output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        output_path.mkdir(parents=True, exist_ok=True)
        
        typer.echo(f"Formatting data for zone: {zone}")
        
        # Find latest downloads for zone
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.file_path, s.type, d.downloaded_at
            FROM downloads d
            JOIN sources s ON d.source_id = s.id
            WHERE d.zone = ?
            ORDER BY d.downloaded_at DESC
            LIMIT 10
        """, (zone,))
        
        downloads = cursor.fetchall()
        conn.close()
        
        if not downloads:
            typer.echo(f"⚠ No downloads found for zone: {zone}")
            return
        
        # Aggregate data
        transports = []
        latest_downloaded_at = max((downloaded_at for _, _, downloaded_at in downloads), default=None)
        
        for file_path, source_type, downloaded_at in downloads:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Process ships
                if 'ships' in data:
                    for ship in data['ships']:
                        if is_in_zone(ship['lat'], ship['lon'], zone):
                            cargo = ship.get('cargo', 'general_cargo')
                            transports.append({
                                'type': 'ship',
                                'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                                'cargo_name': cargo,
                                'position': {
                                    'lat': ship['lat'],
                                    'lon': ship['lon']
                                },
                                'route_progress': '50%',  # Mock
                                'eta': ship.get('eta', '')
                            })
                
                # Process trains
                if 'trains' in data:
                    for train in data['trains']:
                        if is_in_zone(train['lat'], train['lon'], zone):
                            cargo = train.get('cargo', 'general_cargo')
                            transports.append({
                                'type': 'train',
                                'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                                'cargo_name': cargo,
                                'position': {
                                    'lat': train['lat'],
                                    'lon': train['lon']
                                },
                                'destination': train.get('destination', ''),
                                'route_progress': '60%'  # Mock
                            })
                
                # Process trucks
                if 'trucks' in data:
                    for truck in data['trucks']:
                        if is_in_zone(truck['lat'], truck['lon'], zone):
                            cargo = truck.get('cargo', 'general_cargo')
                            transports.append({
                                'type': 'truck',
                                'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                                'cargo_name': cargo,
                                'position': {
                                    'lat': truck['lat'],
                                    'lon': truck['lon']
                                },
                                'destination': truck.get('destination', ''),
                                'route_progress': '75%'  # Mock
                            })
            
            except Exception as e:
                typer.echo(f"⚠ Error processing {file_path}: {e}")
                continue
        
        # Write formatted JSON
        output_file = output_path / f"{zone}.json"
        formatted_data = {
            'zone': zone,
            'updated_at': latest_downloaded_at or datetime.now().isoformat(),
            'transports': transports
        }
        
        with open(output_file, 'w') as f:
            json.dump(formatted_data, f, indent=2)
        
        typer.echo(f"✓ Formatted {len(transports)} transports to: {output_file}")
        log_pipeline_run(command, "success")
        
    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        log_pipeline_run(command, "failed", str(e))
        raise typer.Exit(1)


@app.command("status")
def status():
    """Check connectivity to data sources."""
    init_db()
    
    typer.echo("Checking data source connectivity...\n")
    
    sources = [
        ('AISHub AIS Feed', 'https://www.aishub.net', 'AISHUB_USERNAME'),
        ('AAR Rail Data', 'https://www.aar.org', None),
        ('FHWA Freight Analysis Framework', 'https://ops.fhwa.dot.gov/freight/freight_analysis/faf/', None),
    ]
    
    for name, url, api_key_env in sources:
        try:
            response = requests.head(url, timeout=5)
            status_code = response.status_code
            
            if api_key_env:
                has_key = bool(os.getenv(api_key_env))
                credential_status = "✓" if has_key else "✗ (not set)"
                typer.echo(f"{name}: {status_code} | Credential: {credential_status}")
            else:
                typer.echo(f"{name}: {status_code}")
        
        except Exception as e:
            typer.echo(f"{name}: ✗ Error - {e}")
    
    typer.echo(f"\nDatabase: {DB_PATH}")
    typer.echo(f"Downloads: {DOWNLOADS_DIR}")


@audit_app.command("dir")
def audit_dir():
    """Audit downloads directory structure."""
    init_db()
    
    typer.echo(f"Auditing downloads directory: {DOWNLOADS_DIR}\n")
    
    if not DOWNLOADS_DIR.exists():
        typer.echo("✗ Downloads directory does not exist")
        return
    
    total_size = 0
    file_count = 0
    
    for source_dir in DOWNLOADS_DIR.iterdir():
        if source_dir.is_dir():
            files = list(source_dir.glob("*.json")) + list(source_dir.glob("*.csv"))
            source_size = sum(f.stat().st_size for f in files)
            total_size += source_size
            file_count += len(files)
            
            typer.echo(f"{source_dir.name}: {len(files)} files, {source_size / 1024:.2f} KB")
    
    typer.echo(f"\nTotal: {file_count} files, {total_size / 1024:.2f} KB")
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audits (audit_type, details) VALUES (?, ?)",
                   ('dir', f'{file_count} files, {total_size} bytes'))
    conn.commit()
    conn.close()


@audit_app.command("db")
def audit_db():
    """Audit database tables and record counts."""
    init_db()
    
    typer.echo(f"Auditing database: {DB_PATH}\n")
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    tables = ['sources', 'downloads', 'extractions', 'audits', 'pipeline_runs']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        typer.echo(f"{table}: {count} records")
    
    cursor.execute("INSERT INTO audits (audit_type, details) VALUES (?, ?)",
                   ('db', 'Database audit completed'))
    conn.commit()
    conn.close()


@audit_app.command("size")
def audit_size():
    """Check total size of data."""
    init_db()
    
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    downloads_size = sum(f.stat().st_size for f in DOWNLOADS_DIR.rglob('*') if f.is_file()) if DOWNLOADS_DIR.exists() else 0
    
    typer.echo(f"Database size: {db_size / 1024:.2f} KB")
    typer.echo(f"Downloads size: {downloads_size / 1024:.2f} KB")
    typer.echo(f"Total size: {(db_size + downloads_size) / 1024:.2f} KB")


@audit_app.command("data")
def audit_data():
    """Validate data integrity and completeness."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    # Check for orphaned extractions
    cursor.execute("""
        SELECT COUNT(*) FROM extractions WHERE download_id IS NULL
    """)
    orphaned = cursor.fetchone()[0]
    
    # Check duplicate hashes
    cursor.execute("""
        SELECT file_hash, COUNT(*) as cnt FROM downloads
        GROUP BY file_hash HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    
    typer.echo(f"Orphaned extractions: {orphaned}")
    typer.echo(f"Duplicate files: {len(duplicates)}")
    
    cursor.execute("INSERT INTO audits (audit_type, details) VALUES (?, ?)",
                   ('data', f'orphaned: {orphaned}, duplicates: {len(duplicates)}'))
    conn.commit()
    conn.close()


@audit_app.command("runs")
def audit_runs():
    """Show recent pipeline runs."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT command, status, started_at FROM pipeline_runs
        ORDER BY started_at DESC LIMIT 10
    """)
    
    runs = cursor.fetchall()
    conn.close()
    
    typer.echo("Recent pipeline runs:\n")
    for command, status, started_at in runs:
        status_icon = "✓" if status == "success" else "✗"
        typer.echo(f"{status_icon} {started_at} | {command}")


if __name__ == "__main__":
    app()
