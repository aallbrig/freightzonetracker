# Setting Up Real Data Sources

This guide explains how to configure FreightZoneTracker to pull real-time or near real-time freight data.

## Current Status: Ships Only ✓

Currently, **only ship tracking uses real data** (via AISHub). Trains and trucks still use mock data pending implementation of parsers for AAR/FAF datasets.

---

## Ships: Real-Time AIS Tracking (FREE)

### What You Get
- ✅ Real vessel positions worldwide
- ✅ Ship speed and course
- ✅ Vessel name and MMSI
- ✅ Ship type (tanker, cargo, passenger, etc.)
- ⚠️ Cargo type is **inferred** from vessel type (not actual manifest)
- ⚠️ Rate limited: ~10 requests/minute on free tier

### Setup Instructions

1. **Create Free Account**
   - Visit: https://www.aishub.net/
   - Sign up for free account
   - Verify your email
   - Note your **username** (not an API key)

2. **Set Environment Variable**
   ```bash
   export AISHUB_USERNAME="your_username_here"
   ```

   For permanent setup, add to your shell config:
   ```bash
   # ~/.bashrc or ~/.zshrc
   echo 'export AISHUB_USERNAME="your_username_here"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Test the Connection**
   ```bash
   ./freightcli.py pipeline download --source=ships_marinetraffic --zone=California
   ```

   You should see:
   ```
   🌐 Fetching real AIS data from AISHub for California...
   ✓ Found N vessels in California
   ```

### Understanding the Data

**AIS (Automatic Identification System)** broadcasts from all ships >300 GT:
- Vessels transmit position every 2-10 seconds (dynamic)
- Ship details transmitted every 6 minutes (static)
- Data is aggregated by AISHub from coastal receivers

**Cargo Inference Logic**:
- Ship type code 70-79 → General cargo
- Ship type code 80-89 → Tanker (oil/chemicals)
- Default → Container ship
- *Note: This is an approximation; actual cargo is not broadcast via AIS*

### API Response Format

AISHub returns JSON like:
```json
[
  {
    "MMSI": "367123456",
    "LAT": 33.7491,
    "LON": -118.2694,
    "SOG": 12.3,
    "COG": 45.0,
    "HEADING": 46,
    "NAME": "SHIP NAME",
    "SHIP_TYPE": 70
  }
]
```

Our CLI converts this to:
```json
{
  "ships": [
    {
      "mmsi": "367123456",
      "lat": 33.7491,
      "lon": -118.2694,
      "cargo": "general_cargo",
      "ship_type": 70,
      "name": "SHIP NAME",
      "speed": 12.3,
      "course": 45.0
    }
  ]
}
```

---

## Trains: AAR Weekly Reports (NOT YET IMPLEMENTED)

### What's Available
- ✅ Weekly commodity volumes by type (coal, grain, intermodal, etc.)
- ✅ Aggregated across all Class I railroads
- ❌ NO individual train positions
- ❌ NO real-time tracking

### Data Source
- **URL**: https://www.aar.org/data-center/rail-traffic-data/
- **Format**: CSV/PDF reports released weekly (typically Wednesdays)
- **Cost**: Free, public data
- **Access**: Manual download (no API)

### Sample Data Structure
```csv
Week,Commodity,Carloads,Units
2026-W05,Coal,82450,carloads
2026-W05,Grain,35621,carloads
2026-W05,Intermodal,255340,units
```

### Implementation Needed
1. Web scraper to download weekly CSV
2. Parser to extract commodity volumes by region
3. Route generator to create estimated train positions along rail corridors
4. Position extrapolation based on typical transit times

**Why No Real-Time?**
- Railroads consider train positions proprietary
- No public API or broadcast system like AIS
- Best available: aggregate weekly volumes

---

## Trucks: FAF Freight Flows (NOT YET IMPLEMENTED)

### What's Available
- ✅ Regional freight flow estimates (origin-destination pairs)
- ✅ Commodity types and tonnage
- ✅ Mode breakdown (truck, rail, water, air, etc.)
- ❌ NO individual truck tracking
- ❌ Updated quarterly (not real-time)

### Data Source
- **URL**: https://ops.fhwa.dot.gov/freight/freight_analysis/faf/
- **Format**: CSV datasets (FAF5 is current version)
- **Cost**: Free, public data
- **Access**: Direct download

### Sample Data Structure
```csv
dms_orig,dms_dest,fr_orig,fr_dest,trade_type,sctg2,tons_2022
111,122,11,12,1,01,12500.5
```

Where:
- `dms_orig/dest`: Domestic mode and geography codes
- `sctg2`: Standard Classification of Transported Goods code
- `tons_YYYY`: Annual tonnage for year

### Implementation Needed
1. Download FAF5 CSV dataset
2. Parse origin-destination flows by commodity
3. Map SCTG codes to HS codes
4. Generate truck positions along interstate routes between OD pairs
5. Weighted distribution based on tonnage volumes

**Why No Real-Time?**
- ELD (Electronic Logging Device) data is proprietary to carriers
- No public load tracking system
- Load boards require paid subscriptions
- Best available: quarterly flow estimates

---

## Alternative Data Sources to Consider

### Ships
- **VesselFinder API** (limited free tier): https://www.vesselfinder.com/api
- **NOAA AIS Historical**: https://marinecadastre.gov/ais/ (archived, not real-time)
- **Norwegian Kystverket**: Real-time for Norwegian waters only

### Trains
- **OpenRailwayMap**: Infrastructure data (tracks, stations) - no cargo
- **STB Waybill Sample**: Annual aggregate data, very delayed

### Trucks  
- **US Census CTPP**: Commuter data (not freight)
- **ATRI Truck GPS Data**: Requires membership/purchase

---

## Testing With Mock Data

If you don't set up AISHub credentials, the CLI will automatically fallback to mock data:

```bash
# This works without any API setup
./freightcli.py pipeline download --source=ships_marinetraffic --zone=Indiana
./freightcli.py pipeline format --zone=Indiana
```

You'll see warnings:
```
⚠ AISHUB_USERNAME not set, using mock data (get free account at https://www.aishub.net/)
```

---

## Troubleshooting

### "Error fetching AISHub data"
- Check your username is correct
- Verify internet connectivity
- Check rate limits (free tier: ~10 req/min)
- Try again in a few minutes

### No Vessels Found
- Zone may have no ships currently
- Try a coastal zone (California, Lake Superior)
- Check zone boundaries are correct

### "Duplicate data detected"
- This is normal - CLI deduplicates identical downloads
- Hash comparison prevents re-storing same data
- Not an error

---

## Future Enhancements

### Priority 1: Implement AAR Parser
- [ ] Weekly CSV download automation
- [ ] Commodity volume extraction
- [ ] Rail corridor position generation

### Priority 2: Implement FAF Parser  
- [ ] FAF5 dataset loader
- [ ] SCTG to HS code mapping
- [ ] Interstate route truck positioning

### Priority 3: Enhanced Ship Data
- [ ] Port schedule integration
- [ ] Bill of lading parsing (if available)
- [ ] Vessel tracking history

### Priority 4: Real-Time Enhancements
- [ ] WebSocket support for streaming AIS
- [ ] Caching layer for API responses
- [ ] Background update scheduler

---

## Data Quality Notes

### Position Accuracy
- **Ships**: ±10 meters (GPS accuracy)
- **Trains**: N/A (extrapolated from routes)
- **Trucks**: N/A (extrapolated from flows)

### Update Frequency
- **Ships**: Real-time (2-10 second AIS broadcasts)
- **Trains**: Weekly aggregates
- **Trucks**: Quarterly aggregates

### Cargo Accuracy
- **Ships**: Inferred from vessel type (~70% accurate)
- **Trains**: AAR commodity categories
- **Trucks**: FAF commodity categories

**Bottom Line**: For legal/commercial purposes, this data is illustrative only. For actual shipment tracking, use carrier-specific systems.
