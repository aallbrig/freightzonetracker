---
title: "About FreightZoneTracker"
description: "Learn about FreightZoneTracker — a global maritime vessel explorer powered by AIS data."
---

## What is FreightZoneTracker?

FreightZoneTracker is a global maritime vessel explorer. Select any of the 17 major shipping regions to see active vessels, their flag states, ship types, speeds, headings, and destinations — all powered by real Automatic Identification System (AIS) data refreshed every six hours.

Use the draw tools on the map to draw a custom bounding box and filter vessels to exactly the area you care about. Click any vessel marker to see its full details.

## What is AIS?

The **Automatic Identification System (AIS)** is a maritime collision-avoidance technology mandated by IMO Safety of Life at Sea (SOLAS) regulations for vessels over 300 gross tonnes operating internationally, and all passenger ships regardless of size. Ships broadcast their position, speed, heading, vessel name, and intended destination every few seconds via VHF radio at 161.975 MHz and 162.025 MHz.

Thousands of terrestrial and satellite receivers worldwide collect these signals, creating a near-complete picture of global maritime traffic in near real time.

## Data Sources

FreightZoneTracker uses the **[AISHub](https://www.aishub.net/)** cooperative AIS data network — a free, community-run aggregator that pools vessel signals from volunteer shore-based receivers around the world. The pipeline is automated:

| Data | Source | Cadence |
|------|--------|---------|
| Vessel positions | AISHub (AIS broadcast) | Every 6 hours |
| Vessel names & call signs | AIS vessel data | Every 6 hours |
| Flag states | Inferred from MMSI prefix | Derived |
| Cargo types | Inferred from AIS ship type code | Derived |

## Regions Covered

17 maritime regions are tracked globally:

- **North America** — Great Lakes, Gulf of Mexico, US East Coast, US West Coast
- **Central America** — Caribbean Sea, Panama Canal Zone
- **Europe** — North Sea, English Channel, Mediterranean Sea
- **Middle East** — Suez Canal, Red Sea, Persian Gulf
- **Asia-Pacific** — Strait of Malacca, South China Sea, East China Sea, Bay of Bengal
- **Indian Ocean** — Western Indian Ocean

## How Cargo Types Are Inferred

Individual ship cargo manifests are **not publicly available** for any mode of transport. FreightZoneTracker infers cargo category from the AIS **ship type code** — a classification each vessel self-reports as part of its static AIS data. For example:

| AIS Ship Type | Inferred Cargo | HS Code |
|---------------|---------------|---------|
| 70–79 (Cargo) | General / Container | 8609 |
| 80–89 (Tanker) | Petroleum products | 2710 |
| 60–69 (Passenger) | Passengers | — |
| 30 (Fishing) | Fish, seafood | 0302 |

This is an approximation — the actual cargo of any individual vessel may differ.

## Flag State Inference

Flag states are inferred from the vessel's **MMSI** (Maritime Mobile Service Identity) prefix. Each country's maritime authority is assigned a range of MMSI prefixes. This mapping covers 120+ flag states and is accurate for the vast majority of commercially operated vessels.

## Data Freshness

Data is refreshed automatically every 6 hours via a scheduled GitHub Actions workflow. The `updated_at` timestamp shown in each region's stats panel reflects the last successful data pull.

## Open Source

FreightZoneTracker is fully open source. The CLI tool (`freightcli.py`) and this website are available on [GitHub](https://github.com/aallbrig/freightzonetracker). Contributions, bug reports, and data source suggestions are welcome.
