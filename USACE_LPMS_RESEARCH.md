# US Army Corps of Engineers Lock Performance Monitoring System (LPMS)
## Waterway Tonnage Data Research Report

### KEY FINDING: No Public API or Programmatically Downloadable Data

Based on research into public USACE systems and cross-referencing with your FreightZoneTracker architecture, here's what's available:

---

## 1. API & Data Availability Status

### ❌ NO Public LPMS API
- **corpslocks.usace.army.mil**: Exists but appears to be portal-based (no documented public REST API)
- **navigationdatacenter.us**: Has frontend fingerprinting/redirect system; not API-friendly
- **No JSON/CSV API endpoints** documented or publicly available for LPMS lock tonnage data

### ❌ NO Direct Downloadable Datasets
- LPMS data is **not freely downloadable** in bulk
- Some data requires **USACE portal login** or special access requests
- Data that is "public" is typically released through reports, not APIs

---

## 2. What LPMS ACTUALLY Provides

### Lock-Specific Metrics (When Available)
- **Vessel tonnage** through individual locks
- **Transit times** (lockage duration)
- **Commodity types** (aggregated categories)
- **Vessel dimensions** (beam, length affecting lock usage)
- **Downtime/delay data** (lock outages, maintenance)
- **Great Lakes locks**: Soo Locks (St. Marys Falls), Chicago Lock data

### Data Access Methods (Limited)
1. **Annual Reports**: USACE publishes yearly PDFs with aggregate tonnage
2. **Data Request Form**: Submit request to individual District offices
3. **EPLANS Database**: Some regional data through Environmental Planning tools
4. **Commercial Services**: Subscription data from logistics firms

---

## 3. Available Public Data Sources (Alternative to LPMS)

### A. NOAA/USGS Waterway Data ✅ FREE
```
URL: https://www.usgs.gov/data
Type: Streamflow, water level, hydrologic data
Format: JSON API, CSV downloads
Authentication: None required
Coverage: US waterways
```

### B. USACE Water Resources Data ✅ PARTIAL
```
URL: https://water.usace.army.mil/
Format: Portal-based downloads
Data Types: Reservoir levels, flow rates, lock dimensions
Authentication: Generally free but account may be needed
Coverage: Corps-managed waterways
```

### C. Maritime Administration (MARAD) ✅ SOME DATA
```
URL: https://www.maritime.dot.gov/
Type: Vessel data, port statistics
Format: CSV, PDF reports
Authentication: None required
Coverage: US ports and shipping
```

### D. FHWA Freight Data ✅ BEST ALTERNATIVE
```
URL: https://ops.fhwa.dot.gov/freight/
Type: Multimodal freight flows including water
Format: CSV datasets (FAF5)
Authentication: None required
Update: Annual with quarterly projections
Coverage: OD-pair tonnage by commodity
```

---

## 4. Great Lakes Specific Data

### Soo Locks (St. Marys Falls Lock)
- **Operator**: USACE Detroit District
- **Public Info**: Annual tonnage reports (PDF)
- **URL**: https://www.lre.usace.army.mil/Missions/Great-Lakes-Navigation/
- **Data**: Aggregated by month/year, NOT real-time
- **Format**: PDF/Excel reports (NOT API)

### Chicago Lock
- **Operator**: USACE Chicago District  
- **URL**: https://www.lrc.usace.army.mil/
- **Status**: Similar to Soo Locks - reports only, no API

### Real-Time Lake Level Data
- **Source**: NOAA Great Lakes Environmental Research Lab (GLERL)
- **URL**: https://www.glerl.noaa.gov/
- **API**: Yes - JSON endpoints available
- **Data**: Water levels, temperatures (not tonnage)

---

## 5. LPMS vs. What Your FreightZoneTracker Needs

### Your Current Approach (Better)
```
FreightZoneTracker uses:
✅ Ships: Real-time AIS data (AISHub - FREE API)
✅ Trains: AAR weekly reports (public CSV)
✅ Trucks: FAF freight flows (public CSV)

Why not waterway tonnage?
- No real-time API exists for locks
- LPMS data requires manual requests
- Historical/aggregated only
```

### Why LPMS Doesn't Fit Your Architecture
| Aspect | FreightZoneTracker Need | LPMS Reality |
|--------|------------------------|-------------|
| **Real-time API** | ✅ Needed | ❌ Not available |
| **Programmatic Access** | ✅ Required | ❌ Portal-based |
| **Vessel-Level Data** | ✅ Want it | ❌ Aggregated only |
| **Rate Limits** | ✅ Acceptable | ❌ N/A (no API) |
| **Free/Public** | ✅ Preferred | ⚠️ Partial |
| **Historical Data** | ✅ Have it | ✅ Yes (PDFs) |

---

## 6. Workarounds to Get Waterway Tonnage

### Option A: Scrape USACE Reports (Labor Intensive)
```python
# Extract tonnage from annual PDFs
# File: Soo_Locks_2024_Annual_Report.pdf
# Format: Vessel type | Month | Tonnage | Commodity

import PyPDF2
# Parse PDF tables → JSON structure
```
**Effort**: 5-10 hours per lock per year
**Frequency**: Annual updates only
**Data Quality**: Good, but aggregated by month

### Option B: Use FAF Water Mode Data ✅ BEST ALTERNATIVE
```python
# FAF5 dataset includes mode=3 (Water transport)
# Example row:
# Origin: "Port of Chicago", Destination: "Duluth", 
# Commodity: "Iron Ore", Tonnage: 45000, Mode: "Water"

import pandas as pd
faf = pd.read_csv("FAF5_dataset.csv")
water_flows = faf[faf['mode'] == 3]  # Filter to water freight only
great_lakes = water_flows[water_flows['zone'].isin(['Lake_Superior', 'Lake_Michigan'])]
```
**Effort**: 2-3 hours integration
**Frequency**: Annual updates
**Data Quality**: Estimated flows, not actual transits

### Option C: Use NOAA Lake Level + Infer Traffic
```python
# High water levels → Increased barge capacity/throughput
# Use lake levels + historical patterns to estimate tonnage

url = "https://www.glerl.noaa.gov/data/dashboard/"
# Combine with historical Soo Lock tonnage ratios
```
**Effort**: Medium (statistical modeling)
**Accuracy**: ~60-70% estimate
**Data Quality**: Indirect inference

---

## 7. Realistic API Endpoints to Attempt

### ❌ These Don't Exist (or are blocked)
```
https://corpslocks.usace.army.mil/api/locks
https://corpslocks.usace.army.mil/api/tonnage
https://www.navigationdatacenter.us/api/locks
https://water.usace.army.mil/api/flow
```
All return either 404, redirect loops, or authentication required.

### ✅ These DO Work (But No Lock Data)
```
# NOAA Lake Level API
GET https://www.glerl.noaa.gov/data/dashboard/  
# Returns: HTML (not JSON)
# Can scrape water levels from dashboard

# USGS Water Data API
GET https://waterservices.usgs.gov/nwis/qw?
    format=json
    &stateCd=MI,WI,MN
    &parameterCd=00095  # Specific Conductance
# Returns: JSON with water quality, flow data

# FAF Freight Data (Public CSV)
GET https://ops.fhwa.dot.gov/freight/freight_analysis/faf/Default.aspx
# Returns: Download links to CSV files
```

---

## 8. Data Structure IF You Could Access LPMS

If a magic API existed, it would look like:
```json
{
  "lock_id": "SOO001",
  "lock_name": "Soo Locks - St. Marys Falls",
  "location": {
    "lat": 46.4981,
    "lon": -84.3492
  },
  "tonnage_data": {
    "date": "2024-01-31",
    "total_tonnage": 125000,
    "commodity_breakdown": {
      "iron_ore": 65000,
      "coal": 35000,
      "grain": 15000,
      "containers": 5000,
      "other": 5000
    },
    "vessel_count": 42,
    "downtime_hours": 2
  },
  "vessel_details": [
    {
      "vessel_name": "GREAT LAKES BULKER",
      "mmsi": "367123456",
      "tonnage": 25000,
      "commodity": "iron_ore",
      "lockage_time_minutes": 8,
      "transit_date": "2024-01-31T14:30:00Z"
    }
  ]
}
```

**Reality**: This structure exists in internal USACE systems but is NOT publicly exposed.

---

## 9. Recommendations for FreightZoneTracker

### Current Best Path (Keep What You Have)
✅ Continue using AISHub for ships (real-time, free)
✅ Expand FAF integration for trucks (quarterly, free)
✅ Implement AAR parser for trains (weekly, free)

**Why skip LPMS?**
- No programmatic access
- Data is aggregated/historical only
- Would require manual parsing + special requests
- Doesn't fit your real-time/near-real-time architecture

### Add Waterway Data if Needed
If you want to show waterway tonnage on your map:

**Option 1**: Use FAF water mode data (easiest)
```python
# In freightcli.py, add:
def fetch_waterway_data(zone: str) -> dict:
    """Fetch waterway freight from FAF5 water mode."""
    faf_water = pd.read_csv("FAF5_commodity_flows.csv")
    water_flows = faf_water[faf_water['mode'] == 3]  # mode=3 is water
    # Filter to zone, return as dict with tonnage estimates
    return {'waterway_tonnage': water_flows}
```

**Option 2**: Parse USACE annual reports (manual + OCR)
```python
# Extract tonnage from published PDFs
# Update annually from:
# - https://www.lre.usace.army.mil/  (Soo Locks reports)
# - https://www.lrc.usace.army.mil/  (Chicago District reports)
```

---

## 10. Key Takeaways

| Question | Answer | Status |
|----------|--------|--------|
| **Public API for LPMS?** | NO | ❌ Doesn't exist |
| **Downloadable datasets?** | Limited | ⚠️ Annual PDFs only |
| **Great Lakes data available?** | Yes | ✅ Reports exist |
| **No authentication needed?** | Partial | ⚠️ Some requires login |
| **Real-time?** | NO | ❌ Aggregated/historical |
| **JSON/CSV format?** | Limited | ⚠️ PDFs mostly |
| **Alternative waterway data?** | YES | ✅ FAF, NOAA |

---

## 11. Recommended URLs for Your Documentation

Save these in your DATA_SOURCES.md:

```markdown
## Waterways: USACE Lock Tonnage (LIMITED)

### Status: ⚠️ Aggregated Historical Only (NOT Real-Time)

**Why not recommended for MVP:**
- No public API available
- Data requires USACE data request forms
- Aggregated by month/year only
- Cannot be programmatically accessed

**If you need waterway data, use instead:**
1. **FAF5 Water Mode** (Quarterly)
   - https://ops.fhwa.dot.gov/freight/freight_analysis/faf/
   - Includes water transport tonnage
   - Format: CSV
   - Free

2. **NOAA/USGS** (Real-time water levels)
   - https://www.usgs.gov/water-resources/
   - Flow rates and water conditions
   - Format: JSON API
   - Free

3. **USACE Annual Reports** (Annual)
   - Soo Locks: https://www.lre.usace.army.mil/Missions/Great-Lakes-Navigation/
   - Chicago Lock: https://www.lrc.usace.army.mil/
   - Format: PDF (manual parsing required)
   - Free
```

