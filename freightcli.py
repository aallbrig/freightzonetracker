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
import time
from collections import Counter

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

# Maritime region definitions with bounding boxes and metadata
MARITIME_REGIONS = {
    'Great_Lakes': {
        'bounds': {'lat_min': 41.5, 'lat_max': 49.0, 'lon_min': -92.5, 'lon_max': -75.5},
        'name': 'Great Lakes',
        'description': "Five interconnected freshwater lakes forming North America's largest freshwater lake system, central to bulk cargo shipping.",
        'center': [46.0, -84.0],
        'zoom': 6,
        'key_ports': ['Duluth-Superior', 'Chicago', 'Detroit', 'Cleveland', 'Buffalo', 'Hamilton'],
    },
    'Gulf_of_Mexico': {
        'bounds': {'lat_min': 18.0, 'lat_max': 31.0, 'lon_min': -98.0, 'lon_max': -81.0},
        'name': 'Gulf of Mexico',
        'description': 'Critical hub for petroleum exports and bulk agricultural commodities from the US interior.',
        'center': [24.5, -89.5],
        'zoom': 6,
        'key_ports': ['New Orleans', 'Houston', 'Tampa', 'Mobile', 'Corpus Christi', 'Veracruz'],
    },
    'East_Coast_US': {
        'bounds': {'lat_min': 25.0, 'lat_max': 46.0, 'lon_min': -82.0, 'lon_max': -66.0},
        'name': 'US East Coast',
        'description': 'Major container ports handling transatlantic and coastal trade.',
        'center': [35.5, -74.5],
        'zoom': 5,
        'key_ports': ['New York', 'Savannah', 'Charleston', 'Baltimore', 'Norfolk', 'Miami'],
    },
    'West_Coast_US': {
        'bounds': {'lat_min': 32.0, 'lat_max': 49.0, 'lon_min': -125.0, 'lon_max': -115.0},
        'name': 'US West Coast',
        'description': 'Pacific gateway for transpacific container trade and bulk commodities.',
        'center': [39.0, -121.0],
        'zoom': 5,
        'key_ports': ['Los Angeles', 'Long Beach', 'Seattle', 'Tacoma', 'Oakland', 'Vancouver'],
    },
    'Caribbean': {
        'bounds': {'lat_min': 9.0, 'lat_max': 24.0, 'lon_min': -88.0, 'lon_max': -59.0},
        'name': 'Caribbean Sea',
        'description': 'Key transit zone for vessels moving between the Atlantic and the Panama Canal.',
        'center': [17.0, -74.0],
        'zoom': 5,
        'key_ports': ['Kingston', 'Cartagena', 'Havana', 'Willemstad', 'Port of Spain'],
    },
    'North_Sea': {
        'bounds': {'lat_min': 51.0, 'lat_max': 61.0, 'lon_min': -4.0, 'lon_max': 10.0},
        'name': 'North Sea',
        'description': "One of the world's busiest shipping lanes connecting major European ports.",
        'center': [56.0, 4.0],
        'zoom': 6,
        'key_ports': ['Rotterdam', 'Antwerp', 'Hamburg', 'Amsterdam', 'Felixstowe', 'Oslo'],
    },
    'English_Channel': {
        'bounds': {'lat_min': 49.0, 'lat_max': 52.0, 'lon_min': -5.5, 'lon_max': 2.5},
        'name': 'English Channel',
        'description': 'One of the most congested shipping lanes in the world with over 500 ships transiting daily.',
        'center': [50.5, -1.5],
        'zoom': 7,
        'key_ports': ['Dover', 'Calais', 'Southampton', 'Le Havre', 'Portsmouth'],
    },
    'Mediterranean': {
        'bounds': {'lat_min': 30.0, 'lat_max': 46.0, 'lon_min': -6.0, 'lon_max': 37.0},
        'name': 'Mediterranean Sea',
        'description': 'Historic crossroads of European, Middle Eastern, and African maritime trade.',
        'center': [37.5, 15.0],
        'zoom': 5,
        'key_ports': ['Barcelona', 'Marseille', 'Genoa', 'Piraeus', 'Istanbul', 'Alexandria'],
    },
    'Suez_Canal': {
        'bounds': {'lat_min': 28.5, 'lat_max': 32.5, 'lon_min': 31.5, 'lon_max': 36.0},
        'name': 'Suez Canal',
        'description': "World's most important artificial waterway connecting the Mediterranean to the Red Sea.",
        'center': [30.5, 32.5],
        'zoom': 7,
        'key_ports': ['Port Said', 'Suez', 'Ismailia'],
    },
    'Red_Sea': {
        'bounds': {'lat_min': 12.0, 'lat_max': 28.5, 'lon_min': 32.0, 'lon_max': 44.0},
        'name': 'Red Sea',
        'description': 'Critical transit corridor linking the Suez Canal to the Indian Ocean.',
        'center': [20.0, 38.0],
        'zoom': 6,
        'key_ports': ['Jeddah', 'Aden', 'Hodeidah', 'Djibouti'],
    },
    'Persian_Gulf': {
        'bounds': {'lat_min': 22.0, 'lat_max': 30.0, 'lon_min': 48.0, 'lon_max': 58.0},
        'name': 'Persian Gulf',
        'description': 'Major petroleum export hub handling a significant fraction of global oil shipments.',
        'center': [26.0, 53.0],
        'zoom': 6,
        'key_ports': ['Dubai', 'Abu Dhabi', 'Kuwait City', 'Bandar Abbas', 'Dammam'],
    },
    'Strait_of_Malacca': {
        'bounds': {'lat_min': 1.0, 'lat_max': 6.5, 'lon_min': 99.5, 'lon_max': 104.5},
        'name': 'Strait of Malacca',
        'description': 'One of the most important shipping chokepoints in the world, between Malaysia and Indonesia.',
        'center': [3.0, 101.0],
        'zoom': 7,
        'key_ports': ['Singapore', 'Port Klang', 'Penang', 'Batam'],
    },
    'South_China_Sea': {
        'bounds': {'lat_min': 0.0, 'lat_max': 25.0, 'lon_min': 105.0, 'lon_max': 122.0},
        'name': 'South China Sea',
        'description': 'Major transpacific shipping route handling one-third of global maritime trade volume.',
        'center': [13.0, 113.0],
        'zoom': 5,
        'key_ports': ['Hong Kong', 'Shenzhen', 'Ho Chi Minh City', 'Manila', 'Kaohsiung'],
    },
    'East_China_Sea': {
        'bounds': {'lat_min': 24.0, 'lat_max': 36.0, 'lon_min': 118.0, 'lon_max': 132.0},
        'name': 'East China Sea',
        'description': 'High-traffic maritime zone between China, Japan, South Korea, and Taiwan.',
        'center': [30.0, 125.0],
        'zoom': 6,
        'key_ports': ['Shanghai', 'Ningbo', 'Osaka', 'Busan', 'Taipei'],
    },
    'Panama_Canal': {
        'bounds': {'lat_min': 7.5, 'lat_max': 10.5, 'lon_min': -80.5, 'lon_max': -77.5},
        'name': 'Panama Canal',
        'description': "Engineering marvel connecting Pacific and Atlantic Oceans, handling over 13,000 vessels annually.",
        'center': [9.0, -79.5],
        'zoom': 8,
        'key_ports': ['Balboa', 'Cristobal', 'Panama City'],
    },
    'Bay_of_Bengal': {
        'bounds': {'lat_min': 5.0, 'lat_max': 23.0, 'lon_min': 78.0, 'lon_max': 100.0},
        'name': 'Bay of Bengal',
        'description': 'Important route for South Asian trade, serving Bangladesh, India, and Myanmar.',
        'center': [14.0, 89.0],
        'zoom': 5,
        'key_ports': ['Chittagong', 'Chennai', 'Kolkata', 'Yangon', 'Colombo'],
    },
    'Indian_Ocean_West': {
        'bounds': {'lat_min': -30.0, 'lat_max': 10.0, 'lon_min': 30.0, 'lon_max': 80.0},
        'name': 'Western Indian Ocean',
        'description': 'Key route for oil tankers from the Persian Gulf to Europe and the Americas.',
        'center': [-10.0, 55.0],
        'zoom': 4,
        'key_ports': ['Durban', 'Mombasa', 'Dar es Salaam', 'Mumbai', 'Muscat'],
    },
}

# Backward-compatible alias used by is_in_zone() and tests
ZONE_BOUNDS = {k: v['bounds'] for k, v in MARITIME_REGIONS.items()}

# MMSI prefix (first 3 digits) → (ISO2 country code, country name)
MMSI_FLAG_MAP = {
    '211': ('DE', 'Germany'), '218': ('DE', 'Germany'),
    '219': ('DK', 'Denmark'), '220': ('DK', 'Denmark'),
    '224': ('ES', 'Spain'), '225': ('ES', 'Spain'),
    '226': ('FR', 'France'), '227': ('FR', 'France'), '228': ('FR', 'France'),
    '229': ('MT', 'Malta'), '248': ('MT', 'Malta'), '249': ('MT', 'Malta'), '256': ('MT', 'Malta'),
    '230': ('FI', 'Finland'),
    '232': ('GB', 'United Kingdom'), '233': ('GB', 'United Kingdom'),
    '234': ('GB', 'United Kingdom'), '235': ('GB', 'United Kingdom'),
    '236': ('GI', 'Gibraltar'),
    '237': ('GR', 'Greece'), '239': ('GR', 'Greece'),
    '240': ('GR', 'Greece'), '241': ('GR', 'Greece'),
    '244': ('NL', 'Netherlands'), '245': ('NL', 'Netherlands'), '246': ('NL', 'Netherlands'),
    '247': ('IT', 'Italy'),
    '250': ('IE', 'Ireland'),
    '251': ('IS', 'Iceland'),
    '255': ('PT', 'Portugal'), '263': ('PT', 'Portugal'),
    '257': ('NO', 'Norway'), '258': ('NO', 'Norway'), '259': ('NO', 'Norway'),
    '261': ('PL', 'Poland'),
    '265': ('SE', 'Sweden'), '266': ('SE', 'Sweden'),
    '271': ('TR', 'Turkey'),
    '272': ('UA', 'Ukraine'),
    '273': ('RU', 'Russia'),
    '275': ('LV', 'Latvia'),
    '276': ('EE', 'Estonia'),
    '277': ('LT', 'Lithuania'),
    '303': ('US', 'United States'),
    '304': ('AG', 'Antigua and Barbuda'), '305': ('AG', 'Antigua and Barbuda'),
    '308': ('BS', 'Bahamas'), '309': ('BS', 'Bahamas'), '311': ('BS', 'Bahamas'),
    '310': ('BM', 'Bermuda'),
    '312': ('BZ', 'Belize'),
    '316': ('CA', 'Canada'),
    '319': ('KY', 'Cayman Islands'),
    '321': ('CU', 'Cuba'),
    '336': ('MX', 'Mexico'),
    '338': ('US', 'United States'),
    '339': ('PA', 'Panama'),
    '351': ('PA', 'Panama'), '352': ('PA', 'Panama'), '353': ('PA', 'Panama'),
    '354': ('PA', 'Panama'), '355': ('PA', 'Panama'), '356': ('PA', 'Panama'),
    '357': ('PA', 'Panama'), '370': ('PA', 'Panama'), '371': ('PA', 'Panama'),
    '372': ('PA', 'Panama'), '373': ('PA', 'Panama'), '374': ('PA', 'Panama'),
    '358': ('US', 'United States'),
    '366': ('US', 'United States'), '367': ('US', 'United States'),
    '368': ('US', 'United States'), '369': ('US', 'United States'),
    '379': ('US', 'United States'),
    '375': ('VC', 'Saint Vincent'), '376': ('VC', 'Saint Vincent'), '377': ('VC', 'Saint Vincent'),
    '710': ('AR', 'Argentina'),
    '725': ('BR', 'Brazil'),
    '730': ('CL', 'Chile'),
    '735': ('CO', 'Colombia'),
    '775': ('UY', 'Uruguay'),
    '780': ('VE', 'Venezuela'),
    '403': ('SA', 'Saudi Arabia'),
    '412': ('CN', 'China'), '413': ('CN', 'China'), '414': ('CN', 'China'),
    '416': ('TW', 'Taiwan'),
    '419': ('IN', 'India'),
    '422': ('IR', 'Iran'),
    '425': ('IQ', 'Iraq'),
    '427': ('IL', 'Israel'),
    '428': ('JP', 'Japan'), '431': ('JP', 'Japan'), '432': ('JP', 'Japan'),
    '440': ('KR', 'South Korea'), '441': ('KR', 'South Korea'),
    '447': ('KW', 'Kuwait'),
    '450': ('LB', 'Lebanon'),
    '459': ('OM', 'Oman'),
    '461': ('PK', 'Pakistan'),
    '463': ('PH', 'Philippines'), '548': ('PH', 'Philippines'),
    '466': ('QA', 'Qatar'),
    '470': ('SG', 'Singapore'), '561': ('SG', 'Singapore'),
    '563': ('SG', 'Singapore'), '564': ('SG', 'Singapore'),
    '477': ('HK', 'Hong Kong'),
    '525': ('ID', 'Indonesia'),
    '533': ('MY', 'Malaysia'),
    '536': ('MH', 'Marshall Islands'), '538': ('MH', 'Marshall Islands'),
    '567': ('TH', 'Thailand'),
    '574': ('VN', 'Vietnam'),
    '503': ('AU', 'Australia'),
    '512': ('NZ', 'New Zealand'), '542': ('NZ', 'New Zealand'),
    '601': ('ZA', 'South Africa'),
    '605': ('DZ', 'Algeria'),
    '619': ('EG', 'Egypt'),
    '625': ('GH', 'Ghana'),
    '633': ('LR', 'Liberia'), '636': ('LR', 'Liberia'), '637': ('LR', 'Liberia'),
    '650': ('NG', 'Nigeria'),
    '660': ('SO', 'Somalia'),
    '665': ('TZ', 'Tanzania'),
}

# AIS ship type codes → display name
AIS_SHIP_TYPES = {
    0: 'Unknown',
    30: 'Fishing', 31: 'Towing', 32: 'Towing (large)', 33: 'Dredger',
    34: 'Diving Ops', 35: 'Military', 36: 'Sailing', 37: 'Pleasure Craft',
    40: 'High Speed Craft', 41: 'HSC', 42: 'HSC', 43: 'HSC', 44: 'HSC', 49: 'HSC',
    50: 'Pilot Vessel', 51: 'Search & Rescue', 52: 'Tug', 53: 'Port Tender',
    54: 'Anti-Pollution', 55: 'Law Enforcement', 58: 'Medical Transport', 59: 'Noncombatant',
    60: 'Passenger', 61: 'Passenger', 62: 'Passenger', 63: 'Passenger', 64: 'Passenger', 69: 'Passenger',
    70: 'Cargo', 71: 'Cargo', 72: 'Cargo', 73: 'Cargo', 74: 'Cargo',
    75: 'Cargo', 76: 'Cargo', 77: 'Cargo', 78: 'Cargo', 79: 'Cargo',
    80: 'Tanker', 81: 'Tanker', 82: 'Tanker', 83: 'Tanker', 84: 'Tanker',
    85: 'Tanker', 86: 'Tanker', 87: 'Tanker', 88: 'Tanker', 89: 'Tanker',
    90: 'Other', 91: 'Other', 92: 'Other', 93: 'Other', 94: 'Other',
    95: 'Other', 96: 'Other', 97: 'Other', 98: 'Other', 99: 'Other',
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vessel_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi TEXT NOT NULL,
            name TEXT,
            flag TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            zone TEXT,
            speed REAL,
            heading INTEGER,
            destination TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vpos_mmsi ON vessel_positions(mmsi)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vpos_zone ON vessel_positions(zone)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS region_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            vessel_count INTEGER NOT NULL,
            ship_count INTEGER DEFAULT 0,
            snapshot_date TEXT NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(zone, snapshot_date)
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


def get_flag_from_mmsi(mmsi: str) -> tuple:
    """Infer flag state from MMSI prefix (first 3 digits = MID code)."""
    prefix = str(mmsi)[:3]
    return MMSI_FLAG_MAP.get(prefix, ('', ''))


def fetch_ships_data(zone: str, realtime: bool) -> dict:
    """Fetch ship data from AISHub free API or fall back to realistic mock data."""
    if zone not in MARITIME_REGIONS:
        typer.echo(f"⚠ Unknown zone: {zone}, using empty data")
        return {'ships': []}

    bounds = MARITIME_REGIONS[zone]['bounds']
    aishub_user = os.getenv('AISHUB_USERNAME', '')

    if not aishub_user:
        typer.echo("⚠ AISHUB_USERNAME not set — using demo data (register free at https://www.aishub.net/)")
        return {'ships': _get_mock_ships(zone)}

    try:
        url = "http://data.aishub.net/ws.php"
        params = {
            'username': aishub_user,
            'format': '1',
            'output': 'json',
            'compress': '0',
            'latmin': bounds['lat_min'],
            'latmax': bounds['lat_max'],
            'lonmin': bounds['lon_min'],
            'lonmax': bounds['lon_max'],
        }
        typer.echo(f"🌐 Fetching AIS data for {zone} ({bounds['lat_min']},{bounds['lon_min']} → {bounds['lat_max']},{bounds['lon_max']})...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        ships = []
        vessels = data if isinstance(data, list) else data.get('vessels', [])
        for vessel in vessels:
            if not isinstance(vessel, dict):
                continue
            ship_type = int(vessel.get('SHIP_TYPE', vessel.get('ship_type', 0)) or 0)
            cargo = infer_cargo_from_ship_type(ship_type)
            mmsi = str(vessel.get('MMSI', vessel.get('mmsi', '')) or '')
            # AISHub SOG is in tenths of a knot in some versions
            sog_raw = float(vessel.get('SOG', vessel.get('sog', 0)) or 0)
            speed = round(sog_raw / 10.0, 1) if sog_raw > 100 else round(sog_raw, 1)
            ships.append({
                'mmsi': mmsi,
                'name': (str(vessel.get('SHIPNAME', vessel.get('NAME', '')) or '')).strip(),
                'flag': str(vessel.get('FLAG', '') or '').strip(),
                'lat': float(vessel.get('LAT', vessel.get('lat', 0)) or 0),
                'lon': float(vessel.get('LON', vessel.get('lon', 0)) or 0),
                'cargo': cargo,
                'ship_type': ship_type,
                'speed': speed,
                'heading': int(vessel.get('HEADING', vessel.get('heading', 0)) or 0),
                'destination': (str(vessel.get('DESTINATION', vessel.get('destination', '')) or '')).strip(),
                'eta': None,
            })
        typer.echo(f"✓ Found {len(ships)} vessels in {zone}")
        return {'ships': ships}

    except Exception as e:
        typer.echo(f"⚠ AISHub error: {e} — using demo data")
        return {'ships': _get_mock_ships(zone)}


def _get_mock_ships(zone: str) -> list:
    """Return realistic demo vessel data per zone."""
    mock = {
        'Great_Lakes': [
            {'mmsi': '366982840', 'name': 'AMERICAN SPIRIT', 'flag': 'US', 'lat': 46.8, 'lon': -84.5,
             'cargo': 'iron_ore', 'ship_type': 70, 'speed': 12.2, 'heading': 270, 'destination': 'DULUTH'},
            {'mmsi': '316001234', 'name': 'FEDERAL ELBE', 'flag': 'CA', 'lat': 47.2, 'lon': -84.8,
             'cargo': 'grain', 'ship_type': 70, 'speed': 9.8, 'heading': 90, 'destination': 'HAMILTON'},
            {'mmsi': '316045678', 'name': 'ALGOMA HARVESTER', 'flag': 'CA', 'lat': 48.5, 'lon': -88.3,
             'cargo': 'grain', 'ship_type': 70, 'speed': 8.1, 'heading': 180, 'destination': 'CHICAGO'},
            {'mmsi': '366112233', 'name': 'EDGAR B. SPEER', 'flag': 'US', 'lat': 47.0, 'lon': -90.0,
             'cargo': 'iron_ore', 'ship_type': 70, 'speed': 11.5, 'heading': 90, 'destination': 'GARY'},
        ],
        'English_Channel': [
            {'mmsi': '235067890', 'name': 'MAERSK BRANI', 'flag': 'GB', 'lat': 50.8, 'lon': 1.2,
             'cargo': 'containers', 'ship_type': 70, 'speed': 18.4, 'heading': 45, 'destination': 'ROTTERDAM'},
            {'mmsi': '248345678', 'name': 'MSC BEATRICE', 'flag': 'MT', 'lat': 50.5, 'lon': -0.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 19.7, 'heading': 270, 'destination': 'FELIXSTOWE'},
            {'mmsi': '227123456', 'name': 'CMA CGM RIGEL', 'flag': 'FR', 'lat': 50.1, 'lon': 0.8,
             'cargo': 'containers', 'ship_type': 70, 'speed': 17.2, 'heading': 60, 'destination': 'LE HAVRE'},
            {'mmsi': '244012345', 'name': 'FLANDRIA SEAWAYS', 'flag': 'NL', 'lat': 51.2, 'lon': 2.1,
             'cargo': 'general_cargo', 'ship_type': 79, 'speed': 14.0, 'heading': 45, 'destination': 'ANTWERP'},
        ],
        'North_Sea': [
            {'mmsi': '257234567', 'name': 'STATOIL PIONEER', 'flag': 'NO', 'lat': 58.5, 'lon': 2.8,
             'cargo': 'crude_oil', 'ship_type': 80, 'speed': 13.1, 'heading': 180, 'destination': 'ROTTERDAM'},
            {'mmsi': '211456789', 'name': 'ATLANTIC TRADER', 'flag': 'DE', 'lat': 55.2, 'lon': 7.4,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 11.8, 'heading': 225, 'destination': 'HAMBURG'},
            {'mmsi': '244789012', 'name': 'MERCATOR AMSTERDAM', 'flag': 'NL', 'lat': 53.2, 'lon': 3.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 15.6, 'heading': 270, 'destination': 'AMSTERDAM'},
            {'mmsi': '235012789', 'name': 'NORTH BRIDGE', 'flag': 'GB', 'lat': 56.5, 'lon': -0.5,
             'cargo': 'petroleum', 'ship_type': 85, 'speed': 10.2, 'heading': 0, 'destination': 'ABERDEEN'},
        ],
        'Gulf_of_Mexico': [
            {'mmsi': '367456789', 'name': 'EAGLE HOUSTON', 'flag': 'US', 'lat': 28.5, 'lon': -92.3,
             'cargo': 'crude_oil', 'ship_type': 80, 'speed': 12.0, 'heading': 180, 'destination': 'HOUSTON'},
            {'mmsi': '339567890', 'name': 'CIMBRIA', 'flag': 'PA', 'lat': 24.5, 'lon': -87.0,
             'cargo': 'grain', 'ship_type': 70, 'speed': 14.3, 'heading': 315, 'destination': 'NEW ORLEANS'},
            {'mmsi': '367000111', 'name': 'AMERICAN PETROLEUM', 'flag': 'US', 'lat': 29.3, 'lon': -89.5,
             'cargo': 'petroleum', 'ship_type': 85, 'speed': 8.5, 'heading': 90, 'destination': 'MOBILE'},
        ],
        'East_Coast_US': [
            {'mmsi': '338456789', 'name': 'APL CHINA', 'flag': 'US', 'lat': 40.5, 'lon': -74.0,
             'cargo': 'containers', 'ship_type': 70, 'speed': 16.2, 'heading': 45, 'destination': 'NEW YORK'},
            {'mmsi': '353789012', 'name': 'EVER GIVEN', 'flag': 'PA', 'lat': 32.1, 'lon': -79.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 18.7, 'heading': 315, 'destination': 'SAVANNAH'},
            {'mmsi': '311234567', 'name': 'NASSAU STAR', 'flag': 'BS', 'lat': 30.2, 'lon': -80.0,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 11.3, 'heading': 0, 'destination': 'CHARLESTON'},
        ],
        'West_Coast_US': [
            {'mmsi': '338789012', 'name': 'PRESIDENT KENNEDY', 'flag': 'US', 'lat': 33.7, 'lon': -118.3,
             'cargo': 'containers', 'ship_type': 70, 'speed': 15.8, 'heading': 270, 'destination': 'LOS ANGELES'},
            {'mmsi': '440123456', 'name': 'HYUNDAI UNITY', 'flag': 'KR', 'lat': 37.8, 'lon': -122.4,
             'cargo': 'automobiles', 'ship_type': 70, 'speed': 13.2, 'heading': 90, 'destination': 'OAKLAND'},
            {'mmsi': '412456789', 'name': 'COSCO SHIPPING', 'flag': 'CN', 'lat': 47.6, 'lon': -124.0,
             'cargo': 'containers', 'ship_type': 70, 'speed': 17.1, 'heading': 90, 'destination': 'SEATTLE'},
        ],
        'Mediterranean': [
            {'mmsi': '247123456', 'name': 'COSTA FASCINOSA', 'flag': 'IT', 'lat': 38.1, 'lon': 15.6,
             'cargo': 'general_cargo', 'ship_type': 60, 'speed': 18.5, 'heading': 270, 'destination': 'BARCELONA'},
            {'mmsi': '237456789', 'name': 'LATSCO HELLAS', 'flag': 'GR', 'lat': 36.8, 'lon': 24.2,
             'cargo': 'petroleum', 'ship_type': 80, 'speed': 11.4, 'heading': 270, 'destination': 'PIRAEUS'},
            {'mmsi': '229345678', 'name': 'MALTA TRADER', 'flag': 'MT', 'lat': 35.9, 'lon': 14.4,
             'cargo': 'containers', 'ship_type': 70, 'speed': 14.7, 'heading': 90, 'destination': 'VALLETTA'},
        ],
        'Strait_of_Malacca': [
            {'mmsi': '477123456', 'name': 'ORIENT OVERSEAS', 'flag': 'HK', 'lat': 2.8, 'lon': 103.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 14.2, 'heading': 315, 'destination': 'SINGAPORE'},
            {'mmsi': '564123456', 'name': 'PACIFIC CARRIER', 'flag': 'SG', 'lat': 1.8, 'lon': 104.2,
             'cargo': 'petroleum', 'ship_type': 80, 'speed': 12.0, 'heading': 315, 'destination': 'PORT KLANG'},
            {'mmsi': '525678901', 'name': 'JAKARTA EXPRESS', 'flag': 'ID', 'lat': 4.5, 'lon': 101.0,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 10.8, 'heading': 135, 'destination': 'BATAM'},
        ],
        'Persian_Gulf': [
            {'mmsi': '403234567', 'name': 'ARABIAN SEA', 'flag': 'SA', 'lat': 26.1, 'lon': 55.5,
             'cargo': 'crude_oil', 'ship_type': 80, 'speed': 13.5, 'heading': 135, 'destination': 'JEDDAH'},
            {'mmsi': '466345678', 'name': 'QATAR GAS', 'flag': 'QA', 'lat': 25.4, 'lon': 52.8,
             'cargo': 'petroleum', 'ship_type': 80, 'speed': 10.2, 'heading': 90, 'destination': 'DUBAI'},
        ],
        'South_China_Sea': [
            {'mmsi': '477789012', 'name': 'COSCO EUROPE', 'flag': 'HK', 'lat': 18.5, 'lon': 114.2,
             'cargo': 'containers', 'ship_type': 70, 'speed': 16.4, 'heading': 315, 'destination': 'HONG KONG'},
            {'mmsi': '412789012', 'name': 'MINSHENG GLORY', 'flag': 'CN', 'lat': 10.2, 'lon': 110.5,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 12.1, 'heading': 0, 'destination': 'SHANGHAI'},
        ],
        'East_China_Sea': [
            {'mmsi': '431234567', 'name': 'MOL TRIUMPH', 'flag': 'JP', 'lat': 31.2, 'lon': 122.8,
             'cargo': 'containers', 'ship_type': 70, 'speed': 18.2, 'heading': 45, 'destination': 'OSAKA'},
            {'mmsi': '441234567', 'name': 'HMM ALGECIRAS', 'flag': 'KR', 'lat': 28.5, 'lon': 124.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 17.8, 'heading': 315, 'destination': 'BUSAN'},
        ],
        'Suez_Canal': [
            {'mmsi': '256789012', 'name': 'EVER ACE', 'flag': 'MT', 'lat': 31.8, 'lon': 32.3,
             'cargo': 'containers', 'ship_type': 70, 'speed': 8.5, 'heading': 135, 'destination': 'PORT SAID'},
            {'mmsi': '636345678', 'name': 'LIBERIA STAR', 'flag': 'LR', 'lat': 30.1, 'lon': 32.5,
             'cargo': 'crude_oil', 'ship_type': 80, 'speed': 9.2, 'heading': 0, 'destination': 'SUEZ'},
        ],
        'Red_Sea': [
            {'mmsi': '636456789', 'name': 'ATLAS CARRIER', 'flag': 'LR', 'lat': 20.5, 'lon': 39.5,
             'cargo': 'containers', 'ship_type': 70, 'speed': 14.5, 'heading': 315, 'destination': 'JEDDAH'},
        ],
        'Caribbean': [
            {'mmsi': '353456789', 'name': 'CARIBBEAN TRADER', 'flag': 'PA', 'lat': 15.5, 'lon': -75.0,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 13.8, 'heading': 270, 'destination': 'CARTAGENA'},
        ],
        'Panama_Canal': [
            {'mmsi': '352123456', 'name': 'NEOPANAMAX EXPRESS', 'flag': 'PA', 'lat': 9.1, 'lon': -79.6,
             'cargo': 'containers', 'ship_type': 70, 'speed': 5.0, 'heading': 315, 'destination': 'BALBOA'},
        ],
        'Bay_of_Bengal': [
            {'mmsi': '419123456', 'name': 'MUMBAI CARRIER', 'flag': 'IN', 'lat': 13.5, 'lon': 85.2,
             'cargo': 'general_cargo', 'ship_type': 70, 'speed': 11.0, 'heading': 270, 'destination': 'COLOMBO'},
        ],
        'Indian_Ocean_West': [
            {'mmsi': '601234567', 'name': 'AFRICA TRADER', 'flag': 'ZA', 'lat': -15.0, 'lon': 45.0,
             'cargo': 'crude_oil', 'ship_type': 80, 'speed': 12.5, 'heading': 225, 'destination': 'DURBAN'},
        ],
    }
    return mock.get(zone, [])


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

        transports = []
        latest_downloaded_at = max((downloaded_at for _, _, downloaded_at in downloads), default=None)

        for file_path, source_type, downloaded_at in downloads:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if 'ships' in data:
                    for ship in data['ships']:
                        if not is_in_zone(ship['lat'], ship['lon'], zone):
                            continue
                        cargo = ship.get('cargo', 'general_cargo')
                        ship_type_code = int(ship.get('ship_type', 0) or 0)
                        mmsi = str(ship.get('mmsi', '') or '')
                        # Prefer explicit flag field; fall back to MMSI inference
                        explicit_flag = str(ship.get('flag', '') or '').strip().upper()
                        if explicit_flag and len(explicit_flag) == 2:
                            flag_code = explicit_flag
                            inferred = get_flag_from_mmsi(mmsi)
                            flag_name = inferred[1] if inferred[0] == flag_code else flag_code
                        else:
                            flag_code, flag_name = get_flag_from_mmsi(mmsi)

                        sog = float(ship.get('speed', ship.get('SOG', 0)) or 0)

                        transports.append({
                            'type': 'ship',
                            'mmsi': mmsi or None,
                            'name': (ship.get('name', ship.get('NAME', '')) or '').strip() or None,
                            'flag': flag_code or None,
                            'flag_name': flag_name or None,
                            'ship_type_code': ship_type_code,
                            'ship_type_name': AIS_SHIP_TYPES.get(ship_type_code, 'Unknown'),
                            'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                            'cargo_name': cargo,
                            'position': {'lat': ship['lat'], 'lon': ship['lon']},
                            'speed': round(sog, 1),
                            'heading': int(ship.get('heading', ship.get('HEADING', 0)) or 0) or None,
                            'destination': (ship.get('destination', ship.get('DESTINATION', '')) or '').strip() or None,
                            'eta': ship.get('eta') or None,
                        })

                if 'trains' in data:
                    for train in data['trains']:
                        if is_in_zone(train['lat'], train['lon'], zone):
                            cargo = train.get('cargo', 'general_cargo')
                            transports.append({
                                'type': 'train',
                                'name': train.get('train_id', ''),
                                'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                                'cargo_name': cargo,
                                'position': {'lat': train['lat'], 'lon': train['lon']},
                                'destination': train.get('destination', ''),
                                'route_progress': '60%',
                            })

                if 'trucks' in data:
                    for truck in data['trucks']:
                        if is_in_zone(truck['lat'], truck['lon'], zone):
                            cargo = truck.get('cargo', 'general_cargo')
                            transports.append({
                                'type': 'truck',
                                'name': truck.get('truck_id', truck.get('carrier', '')),
                                'cargo_hs': HS_CODE_MAP.get(cargo, '9999'),
                                'cargo_name': cargo,
                                'position': {'lat': truck['lat'], 'lon': truck['lon']},
                                'destination': truck.get('destination', ''),
                                'route_progress': '75%',
                            })

            except Exception as e:
                typer.echo(f"⚠ Error processing {file_path}: {e}")
                continue

        # Compute stats
        ships_list = [t for t in transports if t['type'] == 'ship']
        trains_list = [t for t in transports if t['type'] == 'train']
        trucks_list = [t for t in transports if t['type'] == 'truck']
        flag_counter = Counter(
            (t.get('flag'), t.get('flag_name')) for t in ships_list if t.get('flag')
        )
        type_counter = Counter(t.get('ship_type_name', 'Unknown') for t in ships_list)
        stats = {
            'ships': len(ships_list),
            'trains': len(trains_list),
            'trucks': len(trucks_list),
            'top_flags': [[flag, count, name] for (flag, name), count in flag_counter.most_common(5)],
            'top_ship_types': [[type_name, count] for type_name, count in type_counter.most_common(5)],
        }

        region_meta = MARITIME_REGIONS.get(zone, {})
        output_file = output_path / f"{zone}.json"
        formatted_data = {
            'zone': zone,
            'zone_name': region_meta.get('name', zone),
            'zone_description': region_meta.get('description', ''),
            'bounds': region_meta.get('bounds', {}),
            'key_ports': region_meta.get('key_ports', []),
            'updated_at': latest_downloaded_at or datetime.now().isoformat(),
            'vessel_count': len(transports),
            'stats': stats,
            'transports': transports,
        }

        with open(output_file, 'w') as f:
            json.dump(formatted_data, f, indent=2)

        typer.echo(f"✓ Formatted {len(transports)} transports to: {output_file}")

        # Record vessel positions and daily snapshot for history tracking
        _record_history(zone, transports)

        _update_regions_index(output_path)

        log_pipeline_run(command, "success")

    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        try:
            log_pipeline_run(command, "failed", str(e))
        except Exception:
            pass
        raise typer.Exit(1)


def _record_history(zone: str, transports: list):
    """Store vessel positions and a daily region snapshot in SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        ship_count = 0
        for t in transports:
            if t.get('type') == 'ship' and t.get('mmsi'):
                ship_count += 1
                pos = t.get('position', {})
                cursor.execute(
                    """INSERT INTO vessel_positions (mmsi, name, flag, lat, lon, zone, speed, heading, destination)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (t['mmsi'], t.get('name'), t.get('flag'),
                     pos.get('lat'), pos.get('lon'), zone,
                     t.get('speed'), t.get('heading'), t.get('destination')),
                )
        cursor.execute(
            """INSERT INTO region_snapshots (zone, vessel_count, ship_count, snapshot_date)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(zone, snapshot_date) DO UPDATE SET
                   vessel_count = excluded.vessel_count,
                   ship_count = excluded.ship_count,
                   recorded_at = CURRENT_TIMESTAMP""",
            (zone, len(transports), ship_count, today),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        typer.echo(f"  (history recording skipped: {e})", err=True)


def _update_regions_index(output_path: Path):
    """Rebuild regions.json index from all available zone files."""
    regions = []
    for region_id, meta in MARITIME_REGIONS.items():
        zone_file = output_path / f"{region_id}.json"
        vessel_count = 0
        updated_at = None
        if zone_file.exists():
            try:
                with open(zone_file) as f:
                    zd = json.load(f)
                    vessel_count = zd.get('vessel_count', len(zd.get('transports', [])))
                    updated_at = zd.get('updated_at')
            except Exception:
                pass
        regions.append({
            'id': region_id,
            'name': meta['name'],
            'description': meta['description'],
            'center': meta['center'],
            'zoom': meta['zoom'],
            'bounds': meta['bounds'],
            'key_ports': meta['key_ports'],
            'vessel_count': vessel_count,
            'updated_at': updated_at,
            'data_url': f'/data/{region_id}.json',
        })
    regions.sort(key=lambda r: (-r['vessel_count'], r['name']))
    index = {
        'updated_at': datetime.now().isoformat(),
        'region_count': len(regions),
        'regions': regions,
    }
    regions_file = output_path / "regions.json"
    with open(regions_file, 'w') as f:
        json.dump(index, f, indent=2)
    typer.echo(f"✓ Updated regions index ({len(regions)} regions): {regions_file}")


@pipeline_app.command("run")
def pipeline_run(
    zone: str = typer.Option(..., help="Zone to run full pipeline for"),
    source: str = typer.Option("ships_marinetraffic", help="Data source"),
    output_dir: Optional[str] = typer.Option(None, help="Override output directory"),
):
    """Run full pipeline (download + format) for a single zone."""
    typer.echo(f"\n▶ Pipeline: {zone}")
    pipeline_download(source=source, zone=zone, realtime=False)
    pipeline_format(zone=zone, output_dir=output_dir)
    typer.echo(f"✓ Done: {zone}")


@pipeline_app.command("run-all")
def pipeline_run_all(
    source: str = typer.Option("ships_marinetraffic", help="Data source"),
    output_dir: Optional[str] = typer.Option(None, help="Override output directory"),
    delay: float = typer.Option(7.0, help="Seconds between zones (API rate limiting)"),
):
    """Run full pipeline for all maritime regions."""
    zones = list(MARITIME_REGIONS.keys())
    typer.echo(f"Running pipeline for {len(zones)} maritime regions...\n")
    success_count = 0
    for i, zone in enumerate(zones):
        typer.echo(f"[{i+1}/{len(zones)}] {zone}")
        try:
            pipeline_download(source=source, zone=zone, realtime=False)
            pipeline_format(zone=zone, output_dir=output_dir)
            success_count += 1
        except Exception as e:
            typer.echo(f"  ✗ Failed: {e}")
        if i < len(zones) - 1:
            time.sleep(delay)
    typer.echo(f"\n✓ Completed {success_count}/{len(zones)} regions")


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


@audit_app.command("vessels")
def audit_vessels():
    """Show vessel position history statistics."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM vessel_positions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT mmsi) FROM vessel_positions")
    unique = cursor.fetchone()[0]

    cursor.execute("""
        SELECT zone, COUNT(*) AS cnt FROM vessel_positions
        GROUP BY zone ORDER BY cnt DESC LIMIT 10
    """)
    by_zone = cursor.fetchall()

    cursor.execute("""
        SELECT zone, vessel_count, snapshot_date FROM region_snapshots
        ORDER BY snapshot_date DESC, vessel_count DESC LIMIT 10
    """)
    snapshots = cursor.fetchall()

    conn.close()

    typer.echo(f"Total position records : {total}")
    typer.echo(f"Unique vessels tracked : {unique}")
    if by_zone:
        typer.echo("\nTop zones by records:")
        for zone, cnt in by_zone:
            typer.echo(f"  {zone}: {cnt}")
    if snapshots:
        typer.echo("\nRecent daily snapshots:")
        for zone, count, date in snapshots:
            typer.echo(f"  {date}  {zone}: {count} vessels")


if __name__ == "__main__":
    app()
