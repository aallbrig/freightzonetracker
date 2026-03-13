# Data Sources Quick Reference

## Current Implementation Status

| Transport | Data Source | Type | Status | Update Frequency |
|-----------|-------------|------|--------|------------------|
| 🚢 **Ships** | AISHub | Real-time positions | ✅ **IMPLEMENTED** | Real-time (2-10s) |
| 🚂 **Trains** | AAR Reports | Aggregate volumes | ⏳ Mock (parser pending) | Weekly |
| 🚛 **Trucks** | FAF Dataset | Regional flows | ⏳ Mock (parser pending) | Quarterly |

---

## Ships: AISHub (FREE)

### ✅ Implemented and Working

**What You Get:**
- Real vessel positions via AIS (Automatic Identification System)
- Ship identification (MMSI, name, flag)
- Speed and course
- Ship type (tanker, cargo, passenger, etc.)

**What You DON'T Get:**
- Actual cargo manifest (inferred from vessel type)
- Destination port (not in free tier)
- ETA (not in free tier)

**Setup:**
1. Create free account: https://www.aishub.net/
2. Get your username (no API key needed)
3. `export AISHUB_USERNAME="your_username"`
4. Run: `python freightcli.py pipeline download --source=ships_marinetraffic --zone=California`

**API Endpoint:**
```
http://data.aishub.net/ws.php
  ?username=YOUR_USERNAME
  &format=1
  &output=json
  &latmin=32.5&latmax=42.0
  &lonmin=-124.5&lonmax=-114.0
```

**Rate Limits:** ~10 requests/minute (free tier)

**Coverage:** Global (where AIS receivers exist - mostly coastal areas)

---

## Trains: AAR (FREE, NOT YET IMPLEMENTED)

### ⏳ Data Available, Parser Needed

**What's Available:**
- Weekly rail traffic reports
- Commodity volumes by type (coal, grain, intermodal, etc.)
- Carload counts for 20+ commodity categories
- Year-over-year comparisons

**What's NOT Available:**
- Individual train positions
- Real-time tracking
- Specific cargo manifests
- Waybill details (those are anonymized/delayed)

**Data Source:**
- URL: https://www.aar.org/data-center/rail-traffic-data/
- Format: CSV/PDF reports (released Wednesdays)
- Access: Public, no registration needed
- Example: "Week 5, 2026: Coal = 82,450 carloads"

**Sample Data:**
```csv
Week,Commodity,Carloads,Units
2026-W05,Coal,82450,carloads
2026-W05,Grain,35621,carloads
2026-W05,Intermodal,255340,units
2026-W05,Chemicals,18234,carloads
```

**Implementation Plan:**
1. Scrape/download weekly CSV from AAR website
2. Parse commodity volumes by region (if available in detailed reports)
3. Load rail corridor geographic data (e.g., OpenRailwayMap)
4. Generate estimated train positions along corridors weighted by volume
5. Map AAR commodity codes to HS codes

**Why Not Real-Time?**
- Railroads consider train positions proprietary (competitive info)
- No public tracking system like AIS for maritime
- FRA (Federal Railroad Admin) only publishes safety data, not operations

---

## Trucks: FAF (FREE, NOT YET IMPLEMENTED)

### ⏳ Data Available, Parser Needed

**What's Available:**
- Freight Analysis Framework (FAF5) dataset
- Origin-Destination pairs with tonnage estimates
- Commodity breakdowns by SCTG code
- Multi-modal (truck, rail, water, air, pipeline)
- Regional flow matrices

**What's NOT Available:**
- Individual truck positions
- Real-time tracking
- Specific shipment details
- ELD (Electronic Logging Device) data

**Data Source:**
- URL: https://ops.fhwa.dot.gov/freight/freight_analysis/faf/
- Format: Large CSV datasets (~500MB)
- Access: Public, free download
- Updates: Annually with quarterly projections
- Example: "Ohio to Indiana, SCTG 01 (grain): 12,500 tons/year"

**Sample Data:**
```csv
dms_orig,dms_dest,sctg2,tons_2022,mode
111,122,01,12500.5,1
```
Where:
- `dms_orig/dest`: Domestic geography codes (state/metro area)
- `sctg2`: Standard Classification of Transported Goods
- `mode`: 1=Truck, 2=Rail, 3=Water, etc.

**Implementation Plan:**
1. Download FAF5 dataset (one-time)
2. Filter to OD pairs where origin or destination is in target zone
3. Map SCTG codes to HS codes
4. Load highway network data (interstate routes)
5. Generate truck positions along routes between OD pairs
6. Weight distribution by tonnage

**Why Not Real-Time?**
- ELD data is proprietary to carriers/platforms (e.g., KeepTruckin, Samsara)
- Load boards (DAT, TruckStop) require paid subscriptions
- No public tracking mandate like AIS
- Best available: aggregate flow estimates

---

## Cargo Manifest Reality

### Why No Real Cargo Data?

**Ships:**
- CBP (Customs and Border Protection) restricts manifest access
- ACE (Automated Commercial Environment) is for trade participants only
- Security concern: knowing what ships carry where
- Commercial confidentiality

**Trains:**
- STB (Surface Transportation Board) publishes anonymized Waybill Sample
- Released annually with 1+ year delay
- Individual shipments not identifiable
- Competitive railroad information

**Trucks:**
- Bill of Lading is between shipper and carrier (commercial document)
- No public registry or filing requirement
- FMCSA only tracks safety, not cargo
- Load boards show available loads, not active shipments

### What We CAN Infer

**Ships:**
- Vessel type → cargo type (tanker = oil, bulk carrier = grain/ore)
- Vessel size → capacity range
- Port schedules (some ports publish)
- Historical patterns (ship X usually carries Y)

**Trains:**
- AAR commodity volumes → regional flows
- Known routes (UP serves Midwest, BNSF serves West)
- Car types (hopper = grain, tank = oil)

**Trucks:**
- FAF commodity flows → OD patterns
- Manufacturing locations (auto plant = car carriers)
- Agricultural seasons (harvest = grain trucks)

---

## Alternative/Future Data Sources

### Ships (Alternatives)
| Source | Type | Cost | Coverage |
|--------|------|------|----------|
| **AISHub** | AIS | FREE ✓ | Global |
| VesselFinder | AIS | Limited free | Global |
| MarineTraffic | AIS + Cargo | $$$$ | Global + Manifests |
| NOAA AIS | Historical | FREE | US Waters |
| Kystverket | Real-time | FREE | Norway only |

### Trains (No Real Alternatives)
- Railinc (industry data exchange) - **Private/Paid only**
- Individual railroad APIs (UP, BNSF) - **Not public**
- OpenRailwayMap - Infrastructure only, no cargo
- Amtrak API - Passenger rail only

### Trucks (No Real Alternatives)  
- DAT Load Board - **Paid subscription**
- TruckStop - **Paid subscription**
- FourKites, Project44 - **Enterprise SaaS ($$$$$)**
- State weigh station data - Aggregate only

---

## Data Quality Comparison

### Position Accuracy
| Mode | Current (Mock) | With Real Data | Commercial Systems |
|------|----------------|----------------|-------------------|
| Ships | N/A | ±10m (GPS) | ±10m (GPS) |
| Trains | N/A | ~10km (extrapolated) | ±100m (carrier GPS) |
| Trucks | N/A | ~50km (extrapolated) | ±10m (ELD GPS) |

### Cargo Accuracy
| Mode | Current (Mock) | With Real Data | Commercial Systems |
|------|----------------|----------------|-------------------|
| Ships | 100% (fake) | ~70% (inferred) | 95%+ (manifest) |
| Trains | 100% (fake) | ~80% (AAR categories) | 100% (waybill) |
| Trucks | 100% (fake) | ~70% (FAF categories) | 100% (BOL) |

### Update Latency
| Mode | Current (Mock) | With Real Data | Commercial Systems |
|------|----------------|----------------|-------------------|
| Ships | Instant | 2-10 seconds | 2-10 seconds |
| Trains | Instant | 1 week | Real-time |
| Trucks | Instant | 3 months | Real-time |

---

## Cost Comparison

### Free/Open Sources (This Project)
- **Ships**: FREE (AISHub free tier)
- **Trains**: FREE (AAR public reports)
- **Trucks**: FREE (FAF public dataset)
- **Total Cost**: $0/month
- **Limitation**: Ships only real-time; trains/trucks aggregate/delayed

### Commercial APIs
- **MarineTraffic**: $200-$2000/month (depends on API tier)
- **Railinc (trains)**: Industry membership required ($$$)
- **FourKites/Project44**: $5,000-$50,000+/month (enterprise SaaS)
- **Total Cost**: $5,000-$50,000+/month
- **Benefit**: Real-time tracking, actual cargo data, full coverage

---

## Recommendations

### For Demo/Research/Education
✅ **Use current implementation:**
- AISHub for real ship positions (free, easy)
- Mock data for trains/trucks (or implement parsers for better data)
- Total cost: $0
- Sufficient for proof-of-concept, demos, learning

### For Production Logistics
❌ **This tool is insufficient:**
- Ships: Cargo inference not reliable for operations
- Trains: Weekly aggregates too delayed for dispatch
- Trucks: Quarterly data useless for real-time logistics
- **Use**: Commercial TMS/visibility platforms (FourKites, Project44, etc.)

### For Statistical Analysis
✅ **Implement full parsers:**
- AAR train data: Good for commodity trend analysis
- FAF truck data: Good for regional trade flow research
- Combined: Excellent for supply chain network modeling
- Total cost: $0 + development time

---

## Next Implementation Steps

### Phase 1: AAR Train Parser (2-3 days)
- [ ] Scrape AAR weekly reports (or manual download)
- [ ] Parse CSV → extract commodity volumes
- [ ] Download rail corridor geo data
- [ ] Implement position extrapolation algorithm
- [ ] Map AAR commodity codes → HS codes
- [ ] Update `fetch_trains_data()` in CLI

### Phase 2: FAF Truck Parser (2-3 days)
- [ ] Download FAF5 dataset
- [ ] Load into pandas/SQLite
- [ ] Filter OD pairs by zone
- [ ] Map SCTG codes → HS codes
- [ ] Download highway network geo data
- [ ] Implement position extrapolation algorithm
- [ ] Update `fetch_trucks_data()` in CLI

### Phase 3: Enhancements (1-2 weeks)
- [ ] WebSocket support for streaming AIS
- [ ] Caching layer (Redis/file cache)
- [ ] Historical data storage and playback
- [ ] Route prediction algorithms
- [ ] Port schedule integration
- [ ] Background update scheduler (cron jobs)

---

## Support

Questions about data sources? Check:
- [REAL_DATA_SETUP.md](REAL_DATA_SETUP.md) - Detailed setup guide
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details
- Open a GitHub issue for specific questions
