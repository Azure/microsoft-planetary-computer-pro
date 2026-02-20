# 🌀 Hurricane Forecast System Architecture

> **System Diagram**: Hurricane Path Prediction & Infrastructure Impact Analysis  
> **Core Platform**: Microsoft Planetary Computer Pro + Aurora AI Weather Model

---

## 📑 Table of Contents

1. [System Overview Diagram](#system-overview-diagram)
2. [External System Interfaces](#external-system-interfaces)
3. [Data Flow Architecture](#data-flow-architecture)
4. [Storm Data Acquisition Strategy](#storm-data-acquisition-strategy)
5. [Storm Selection & Classification](#storm-selection--classification)
6. [ECMWF Data Stream Selection](#ecmwf-data-stream-selection)
7. [Aurora Model Integration](#aurora-model-integration)
8. [Intelligent Forecast Termination](#intelligent-forecast-termination)
9. [Cone of Uncertainty Visualization](#cone-of-uncertainty-visualization)
10. [Asymmetric Impact Swath & Coastal Impact Zones](#asymmetric-impact-swath--coastal-impact-zones)
11. [Aurora Tracker Optimal Initialization Algorithm](#aurora-tracker-optimal-initialization-algorithm)
12. [GeoCatalog STAC Integration](#geocatalog-stac-integration)
13. [Infrastructure Query Strategy](#infrastructure-query-strategy)
14. [Authentication Summary](#authentication-summary)
15. [Environment Variables Reference](#environment-variables-reference)
16. [Key Python Dependencies](#key-python-dependencies)

---

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    HURRICANE FORECAST & INFRASTRUCTURE IMPACT SYSTEM                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           ┌─────────────────────┐
                                           │   JUPYTER NOTEBOOK  │
                                           │  (Orchestration)    │
                                           └──────────┬──────────┘
                                                      │
          ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
          │                                           │                                           │
          ▼                                           ▼                                           ▼
┌─────────────────────┐                 ┌───────────────────────────────────────────────────────────────────┐
│  STORM DATA LAYER   │                 │                     MICROSOFT AZURE PLATFORM                      │
│  (External Sources) │                 │  ┌─────────────────────────┐    ┌─────────────────────────────┐  │
│                     │                 │  │   WEATHER DATA LAYER    │    │      OUTPUT LAYER           │  │
│ ┌─────────────────┐ │                 │  │                         │    │                             │  │
│ │   Tropycal      │ │                 │  │ ┌─────────────────────┐ │    │ ┌─────────────────────────┐ │  │
│ │   Library       │ │                 │  │ │  Planetary Computer │ │    │ │  GeoCatalog Pro         │ │  │
│ └────────┬────────┘ │                 │  │ │  STAC Catalog       │ │    │ │  STAC API               │ │  │
│          │          │                 │  │ └──────────┬──────────┘ │    │ └───────────┬─────────────┘ │  │
│          ▼          │                 │  │            │            │    │             │               │  │
│ ┌─────────────────┐ │                 │  │ ┌──────────▼──────────┐ │    │ ┌───────────▼─────────────┐ │  │
│ │  IBTrACS NCEI   │ │                 │  │ │  ECMWF Blob Storage │ │    │ │  Azure Blob Storage     │ │  │
│ │  Direct CSV     │ │                 │  │ │  (OPER + SCDA)      │ │    │ │  (Hurricane Data)       │ │  │
│ └────────┬────────┘ │                 │  │ └─────────────────────┘ │    │ └───────────┬─────────────┘ │  │
│          │          │                 │  └─────────────────────────┘    └─────────────┼───────────────┘  │
│          ▼          │                 │                                               │                  │
│ ┌─────────────────┐ │                 │  ┌─────────────────────────┐                  │                  │
│ │  NHC RSS/JSON   │ │                 │  │    Azure AI Foundry     │                  │                  │
│ │  (Active)       │ │                 │  │  ┌───────────────────┐  │                  │                  │
│ └─────────────────┘ │                 │  │  │ Aurora 0.25° Model│  │                  │                  │
└─────────────────────┘                 │  │  │ + TC Tracker      │  │                  │                  │
          │                             │  │  └───────────────────┘  │                  │                  │
          │                             │  └─────────────────────────┘                  │                  │
          │                             └───────────────────────────────────────────────┼──────────────────┘
          │                                           │                                 │
          │                                           │                                 │
          └───────────────────────┬───────────────────┘                                 │
                                  │                                                     │
                                  ▼                                                     │
                    ┌─────────────────────────────┐                                     │
                    │      DATA PREPARATION       │                                     │
                    │  ┌───────────────────────┐  │                                     │
                    │  │ • GRIB2 → xarray      │  │                                     │
                    │  │ • Lon [-180,180]→[0,360]│ │                                     │
                    │  │ • Pressure level sort │  │                                     │
                    │  │ • Aurora Batch format │  │                                     │
                    │  └───────────────────────┘  │                                     │
                    └──────────────┬──────────────┘                                     │
                                   │                                                    │
                                   ▼                                                    │
                    ┌─────────────────────────────┐         ┌─────────────────────────┐ │
                    │   TRACK VISUALIZATION       │         │  INFRASTRUCTURE QUERY   │ │
                    │  ┌───────────────────────┐  │         │ ┌─────────────────────┐ │ │
                    │  │ Cartopy + Matplotlib  │  │────────►│ │   Overpass API      │ │─┘
                    │  │ Observed vs Predicted │  │         │ │   (OpenStreetMap)   │ │
                    │  └───────────────────────┘  │         │ └─────────────────────┘ │
                    └─────────────────────────────┘         └─────────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │  Folium HTML    │
                         │  (Local Output) │
                         └─────────────────┘
```

---

## External System Interfaces

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        EXTERNAL SYSTEM INTERFACES                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                          │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐     │
│   │                              MICROSOFT AZURE ECOSYSTEM                                          │     │
│   │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                   │     │
│   │  │  Planetary Computer │   │   Azure AI Foundry  │   │   Azure Blob        │                   │     │
│   │  │  Pro (GeoCatalog)   │   │   (Aurora Model)    │   │   Storage           │                   │     │
│   │  │                     │   │                     │   │                     │                   │     │
│   │  │  Auth: AAD Bearer   │   │  Auth: API Token    │   │  Auth: AAD + SAS    │                   │     │
│   │  │  Protocol: STAC API │   │  Protocol: REST     │   │  Protocol: Blob API │                   │     │
│   │  └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                   │     │
│   │                                                                                                │     │
│   │  ┌─────────────────────┐   ┌─────────────────────┐                                             │     │
│   │  │  Planetary Computer │   │   ECMWF Blob        │                                             │     │
│   │  │  STAC Catalog       │   │   (ai4edataeuwest)  │                                             │     │
│   │  │                     │   │                     │                                             │     │
│   │  │  Auth: PC Signer    │   │  Auth: PC SAS Token │                                             │     │
│   │  │  Data: OPER Stream  │   │  Data: SCDA Stream  │                                             │     │
│   │  └─────────────────────┘   └─────────────────────┘                                             │     │
│   └────────────────────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                                          │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐     │
│   │                              TROPICAL CYCLONE DATA SOURCES                                      │     │
│   │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                   │     │
│   │  │  IBTrACS (NCEI)     │   │   HURDAT2 (NHC)     │   │   NHC Active Storms │                   │     │
│   │  │                     │   │                     │   │                     │                   │     │
│   │  │  Auth: None         │   │  Auth: None         │   │  Auth: None         │                   │     │
│   │  │  Format: CSV        │   │  Format: Tropycal   │   │  Format: JSON       │                   │     │
│   │  │  Basins: Global     │   │  Basins: ATL, EPAC  │   │  Data: Real-time    │                   │     │
│   │  └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                   │     │
│   └────────────────────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                                          │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐     │
│   │                              INFRASTRUCTURE DATA (OpenStreetMap)                                │     │
│   │  ┌───────────────────────────────────────────────────────────────────────────────────────┐     │     │
│   │  │  Overpass API Servers (with automatic failover)                                       │     │     │
│   │  │                                                                                       │     │     │
│   │  │  Primary:   overpass-api.de/api/interpreter                                          │     │     │
│   │  │  Fallback:  overpass.kumi.systems/api/interpreter                                    │     │     │
│   │  │  Fallback:  maps.mail.ru/osm/tools/overpass/api/interpreter                          │     │     │
│   │  │                                                                                       │     │     │
│   │  │  Data: power=substation, power=plant, power=line                                     │     │     │
│   │  └───────────────────────────────────────────────────────────────────────────────────────┘     │     │
│   └────────────────────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           DATA FLOW DIAGRAM                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    USER INPUT                           PROCESSING                              OUTPUT
  ─────────────                        ─────────────                          ──────────

  ┌───────────────┐
  │ Storm Name    │
  │ (e.g. Helene) ├──────┐
  │ Year: 2024    │      │
  └───────────────┘      │
                         │     ┌──────────────────────────────────────────────────────────────┐
                         ├────►│                    STORM DATA ACQUISITION                    │
                         │     │                                                              │
                         │     │   Tropycal ──► IBTrACS CSV ──► NHC JSON ──► IBTrACS Active  │
                         │     │      │              │              │              │          │
                         │     │      └──────────────┴──────────────┴──────────────┘          │
                         │     │                         │                                    │
                         │     │                         ▼                                    │
                         │     │              ┌───────────────────┐                           │
                         │     │              │ Optimal Init Finder│                          │
                         │     │              │ • Wind scoring     │                          │
                         │     │              │ • Pressure bonus   │                          │
                         │     │              │ • Genesis penalty  │                          │
                         │     │              └─────────┬─────────┘                           │
                         │     └────────────────────────┼─────────────────────────────────────┘
                         │                              │
                         │                              ▼
                         │     ┌──────────────────────────────────────────────────────────────┐
                         │     │                 ECMWF WEATHER DATA DOWNLOAD                  │
                         │     │                                                              │
                         │     │   Init Time Hour?                                            │
                         │     │        │                                                     │
                         │     │        ├── 00Z/12Z ──► OPER Stream (PC STAC API)            │
                         │     │        │                                                     │
                         │     │        └── 06Z/18Z ──► SCDA Stream (Blob Storage)           │
                         │     │                                                              │
                         │     │   Both T-6h and T0 timesteps downloaded                     │
                         │     └────────────────────────┬─────────────────────────────────────┘
                         │                              │
                         │                              ▼
                         │     ┌──────────────────────────────────────────────────────────────┐
                         │     │                   AURORA BATCH CREATION                      │
                         │     │                                                              │
                         │     │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
                         │     │   │ surf_vars   │  │ atmos_vars  │  │ static_vars │         │
                         │     │   │ [1,2,H,W]   │  │ [1,2,L,H,W] │  │ [H,W]       │         │
                         │     │   └─────────────┘  └─────────────┘  └─────────────┘         │
                         │     │                                                              │
                         │     │   Coordinate Transform: [-180,180] ──► [0,360]              │
                         │     │   Pressure Levels: Sort ascending (50 ──► 1000 hPa)         │
                         │     └────────────────────────┬─────────────────────────────────────┘
                         │                              │
                         │                              ▼
                         │     ┌──────────────────────────────────────────────────────────────┐
                         │     │              AZURE AI FOUNDRY (AURORA MODEL)                 │    ┌────────────────┐
                         │     │                                                              │    │                │
                         │     │   ┌─────────────────────────────────────────────────────┐   │    │  GeoCatalog    │
                         │     │   │  aurora-0.25-finetuned                              │   ├───►│  STAC Ingest   │
                         │     │   │  • 6-hourly forecast steps                          │   │    │                │
                         │     │   │  • TC Tracker extracts storm center                 │   │    │  • Collection  │
                         │     │   │  • Returns: lat, lon, msl, wind per step            │   │    │  • Items       │
                         │     │   └─────────────────────────────────────────────────────┘   │    │  • Render Opts │
                         │     └────────────────────────┬─────────────────────────────────────┘    └────────────────┘
                         │                              │
                         │                              ▼
                         │     ┌──────────────────────────────────────────────────────────────┐
                         │     │                  TRACK VISUALIZATION                         │    ┌────────────────┐
                         │     │                                                              │    │                │
                         │     │   Cartopy Plot:                                              │───►│  PNG Image     │
                         │     │   • Observed track (black solid)                             │    │                │
                         │     │   • Forecast track (blue dashed)                             │    └────────────────┘
                         │     │   • Cone of uncertainty (orange fill)                        │
                         │     └────────────────────────┬─────────────────────────────────────┘
                         │                              │
                         │                              ▼
                         │     ┌──────────────────────────────────────────────────────────────┐
                         │     │              INFRASTRUCTURE IMPACT ANALYSIS                  │    ┌────────────────┐
                         │     │                                                              │    │                │
                         │     │   Overpass API Query:                                        │───►│  Interactive   │
                         │     │   • Tiled requests (5°×5° facilities, 3°×3° lines)          │    │  Folium HTML   │
                         │     │   • Filter to cone polygon (Shapely intersection)           │    │                │
                         │     │   • Categorize by voltage level                              │    │  + Animation   │
                         │     └──────────────────────────────────────────────────────────────┘    └────────────────┘
```

---

## Storm Data Acquisition Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              STORM DATA MULTI-SOURCE FALLBACK STRATEGY                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────────────┐
                                    │      START REQUEST      │
                                    └────────────┬────────────┘
                                                 │
                                                 ▼
                              ┌──────────────────────────────────────┐
                              │  LEVEL 1: Tropycal Library           │
                              │  ─────────────────────────────────   │
                              │  • HURDAT2 for ATL/EPAC              │
                              │  • IBTrACS for other basins          │
                              │  • Fastest, most complete metadata   │
                              └──────────────────┬───────────────────┘
                                                 │
                                      ┌──────────┴──────────┐
                                      │    Success?         │
                                      └──────────┬──────────┘
                                           │           │
                                          YES          NO
                                           │           │
                                           ▼           ▼
                              ┌─────────────────┐  ┌──────────────────────────────────────┐
                              │  Return Data    │  │  LEVEL 2: Tropycal + v04r01 URL      │
                              │  + Cache        │  │  ─────────────────────────────────   │
                              └─────────────────┘  │  • Override IBTrACS URL to v04r01    │
                                                   │  • Newer data for recent storms      │
                                                   └──────────────────┬───────────────────┘
                                                                      │
                                                           ┌──────────┴──────────┐
                                                           │    Success?         │
                                                           └──────────┬──────────┘
                                                                │           │
                                                               YES          NO
                                                                │           │
                                                                ▼           ▼
                                                   ┌─────────────────┐  ┌──────────────────────────────────────┐
                                                   │  Return Data    │  │  LEVEL 3: IBTrACS Direct CSV         │
                                                   │  + Cache        │  │  ─────────────────────────────────   │
                                                   └─────────────────┘  │  • Download ibtracs.last3years.csv   │
                                                                        │  • Parse manually with pandas        │
                                                                        │  • Works when Tropycal API fails     │
                                                                        └──────────────────┬───────────────────┘
                                                                                           │
                                                                                ┌──────────┴──────────┐
                                                                                │    Success?         │
                                                                                └──────────┬──────────┘
                                                                                     │           │
                                                                                    YES          NO
                                                                                     │           │
                                                                                     ▼           ▼
                                                                        ┌─────────────────┐  ┌──────────────────────────────────────┐
                                                                        │  Return Data    │  │  LEVEL 4: Basin-Specific CSV         │
                                                                        │  + Cache        │  │  ─────────────────────────────────   │
                                                                        └─────────────────┘  │  • ibtracs.{basin}.list.v04r01.csv   │
                                                                                             │  • Narrower scope, higher success    │
                                                                                             └──────────────────┬───────────────────┘
                                                                                                                │
                                                                                                     ┌──────────┴──────────┐
                                                                                                     │    Success?         │
                                                                                                     └──────────┬──────────┘
                                                                                                          │           │
                                                                                                         YES          NO
                                                                                                          │           │
                                                                                                          ▼           ▼
                                                                                             ┌─────────────────┐  ┌──────────────────────────────────────┐
                                                                                             │  Return Data    │  │  LEVEL 5: NHC JSON API               │
                                                                                             │  + Cache        │  │  ─────────────────────────────────   │
                                                                                             └─────────────────┘  │  • nhc.noaa.gov/CurrentStorms.json   │
                                                                                                                  │  • Active storms only                │
                                                                                                                  │  • ATL/EPAC basins only              │
                                                                                                                  └──────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  CACHING STRATEGY                                                                                    │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   Location:  ./cache/storm_data/storms_{basin}_{year}.json                                          │
    │                                                                                                      │
    │   Policy:    Past Years ──► Cache forever (historical data is immutable)                            │
    │              Current Year ──► Re-fetch if cache_date ≠ today (storms still developing)              │
    │                                                                                                      │
    │   Contents:  { cache_date, basin_id, year, storms: { id: { name, track, vmax, mslp, ... } } }       │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Active Storm Track Data Acquisition

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       ACTIVE STORM TRACK DATA ACQUISITION (COMPLETE HISTORICAL + FORECAST)               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   For active/current storms, we need COMPLETE track data including:
   • Historical positions (from storm genesis to present)
   • Current position (T+0)
   • Forecast positions (if available)

   This is critical for ECMWF data availability handling - when T0 needs to shift back in time,
   we need the correct historical lat/lon for that earlier time.

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │                    ACTIVE STORM DATA SOURCES BY BASIN                                     │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │   SOURCE              BASIN COVERAGE          PROVIDES                     FORMAT         │
   │   ──────────────────  ────────────────────    ─────────────────────────    ────────────   │
   │   Tropycal Realtime   ATL, EPAC, Global       Complete best track          API            │
   │   NHC RSS + Best Track ATL, EPAC              Current pos + historical     JSON + ATCF    │
   │   JTWC RSS + TCW + BT  WPAC, NIO, SIO, SPAC   Current + forecast + hist   RSS + ATCF     │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   JTWC TRACK DATA PIPELINE (Non-Atlantic Basins)
   ════════════════════════════════════════════════

   ┌─────────────────────┐
   │   JTWC RSS Feed     │
   │   (Storm Discovery) │
   └──────────┬──────────┘
              │ Discover active storms
              │ Extract: storm_id, name, basin_code, tcw_url
              ▼
   ┌──────────────────────────────────────────────────────────────────────────────────┐
   │  PARALLEL DATA FETCH                                                             │
   │                                                                                  │
   │  ┌───────────────────────┐          ┌───────────────────────────────────┐       │
   │  │  TCW Forecast File    │          │  ATCF Best Track File             │       │
   │  │  (T+0 to T+120)       │          │  (Genesis to Present)             │       │
   │  │                       │          │                                   │       │
   │  │  URL: metoc.navy.mil/ │          │  URL: metoc.navy.mil/jtwc/        │       │
   │  │  jtwc/products/       │          │  products/b{basin}{num}{year}.dat │       │
   │  │  {storm_id}.tcw       │          │                                   │       │
   │  │                       │          │  Parse ATCF format:               │       │
   │  │  Parse T000-T120:     │          │  SH, 19, 2026012700, , BEST, ...  │       │
   │  │  T000 155S 0430E 080  │          │                                   │       │
   │  │  T012 161S 0445E 090  │          │                                   │       │
   │  └───────────┬───────────┘          └─────────────────┬─────────────────┘       │
   │              │                                        │                         │
   │              └────────────────┬───────────────────────┘                         │
   │                               │                                                 │
   │                               ▼                                                 │
   │              ┌───────────────────────────────────┐                              │
   │              │     merge_track_data()            │                              │
   │              │                                   │                              │
   │              │  • Combine by timestamp           │                              │
   │              │  • Historical overwrites forecast │                              │
   │              │    for past times                 │                              │
   │              │  • Forecast fills future times    │                              │
   │              │  • Sort chronologically           │                              │
   │              └─────────────────┬─────────────────┘                              │
   │                                │                                                │
   └────────────────────────────────┼────────────────────────────────────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────────┐
                     │  MERGED TRACK DATA                │
                     │                                   │
                     │  • historical_points: 25          │
                     │  • forecast_points: 8             │
                     │  • total: 33 track points         │
                     │                                   │
                     │  Example output:                  │
                     │  "✓ Fytia: 33 points              │
                     │   (25 historical + 8 forecast)"   │
                     └───────────────────────────────────┘


   NHC TRACK DATA PIPELINE (Atlantic & East Pacific)
   ══════════════════════════════════════════════════

   ┌─────────────────────┐
   │   NHC RSS Feed      │
   │   CurrentStorms.json│
   └──────────┬──────────┘
              │ Discover active storms
              │ Extract: storm_id (AL012024), name, current lat/lon
              ▼
   ┌──────────────────────────────────────────────────────────────────────────────────┐
   │  BEST TRACK FETCH                                                                │
   │                                                                                  │
   │  ┌───────────────────────────────────────────────────────────────────────┐       │
   │  │  NHC ATCF Best Track File                                             │       │
   │  │                                                                       │       │
   │  │  URL: ftp.nhc.noaa.gov/atcf/btk/b{basin}{num}{year}.dat              │       │
   │  │  Example: bal012024.dat (Atlantic storm 01 of 2024)                   │       │
   │  │                                                                       │       │
   │  │  Archive fallback: ftp.nhc.noaa.gov/atcf/archive/{year}/...          │       │
   │  │                                                                       │       │
   │  │  Parse ATCF format:                                                   │       │
   │  │  AL, 01, 2024062500, , BEST, 0, 165N, 325W, 30, 1008, ...            │       │
   │  └───────────────────────────────────────────────────────────────────────┘       │
   │                                                                                  │
   │                                    │                                             │
   │                                    ▼                                             │
   │              ┌───────────────────────────────────┐                              │
   │              │     merge_track_data()            │                              │
   │              │                                   │                              │
   │              │  • Best track = historical        │                              │
   │              │  • RSS current pos = forecast T+0 │                              │
   │              │  • Combine and deduplicate        │                              │
   │              └─────────────────┬─────────────────┘                              │
   │                                │                                                │
   └────────────────────────────────┼────────────────────────────────────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────────┐
                     │  MERGED TRACK DATA                │
                     │                                   │
                     │  Example output:                  │
                     │  "✓ Storm: 28 points              │
                     │   (27 historical + 1 current)"    │
                     └───────────────────────────────────┘


   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │                    DATA AVAILABILITY BY SOURCE                                            │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │   SOURCE               HISTORICAL    CURRENT    FORECAST    TIME SHIFT SUPPORT           │
   │   ────────────────     ──────────    ───────    ────────    ─────────────────            │
   │   Tropycal Realtime    ✅ Yes        ✅ Yes     ❌ No       ✅ Full support               │
   │   NHC RSS + Best Track ✅ Yes        ✅ Yes     ❌ No       ✅ Full support               │
   │   JTWC RSS + TCW + BT  ✅ Yes        ✅ Yes     ✅ Yes      ✅ Full support               │
   │   NHC RSS only         ❌ No         ✅ Yes     ❌ No       ⚠️ Current position only      │
   │   JTWC RSS + TCW only  ❌ No         ✅ Yes     ✅ Yes      ⚠️ Current position only      │
   │                                                                                           │
   │   Note: "Time Shift Support" means we can look up historical lat/lon when ECMWF data     │
   │         availability requires shifting T0 backwards in time.                              │
   └───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ECMWF Data Availability Check for Active Storms

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                  ECMWF DATA AVAILABILITY CHECK & AUTOMATIC TIME ADJUSTMENT                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   PROBLEM: ECMWF HRES data has a publication delay (~6-12 hours for public access).
   For active storms, the most recent synoptic time (e.g., today 12Z) may not have data yet.

   SOLUTION: Check if data exists at T0, and automatically shift backwards 6 hours at a time
   until available data is found. Update BOTH the init time AND the storm position.


   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  DATA AVAILABILITY CHECK LOGIC                                                            │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  check_ecmwf_data_exists(datetime, catalog):                                             │
   │                                                                                           │
   │    IF hour in [0, 12]:  # OPER stream                                                    │
   │       → Query STAC catalog for ecmwf-hres collection                                     │
   │       → Return True if items found                                                       │
   │                                                                                           │
   │    IF hour in [6, 18]:  # SCDA stream                                                    │
   │       → Check if time is > 6 hours old (typical SCDA availability window)                │
   │       → Return True if older than 6 hours                                                │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   AUTOMATIC TIME & POSITION ADJUSTMENT WORKFLOW
   ═════════════════════════════════════════════

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  find_available_ecmwf_time(start_time, catalog, storm_df, max_lookback=48h)            │
   └─────────────────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────────────────────────┐
   │  Is ECMWF data available at start_time?                                       │
   │                                                                               │
   │  check_ecmwf_data_exists(start_time, catalog)                                │
   └───────────────────────┬───────────────────────┬───────────────────────────────┘
                          YES                      NO
                           │                        │
                           ▼                        ▼
              ┌────────────────────┐   ┌────────────────────────────────────────┐
              │  Return:           │   │  Go back 6 hours                       │
              │  • start_time      │   │  current_check = start_time - 6h       │
              │  • time_shifted=   │   │                                        │
              │    False           │   │  Loop until found or max_lookback      │
              │  • No position     │   │                                        │
              │    adjustment      │   │  When found:                           │
              └────────────────────┘   │  • Look up lat/lon in storm_df        │
                                       │  • Find closest track point (< 3h)     │
                                       │  • Return adjusted time AND position   │
                                       └────────────────────────────────────────┘


   EXAMPLE: Active Storm Time Shift
   ═════════════════════════════════

   ┌────────────────────────────────────────────────────────────────────────────────────────┐
   │  Input:                                                                                │
   │    • storm_init_time = 2026-02-03 12:00 UTC (today's 12Z)                             │
   │    • storm_init_lat = -15.5°, storm_init_lon = 43.0° (current position from TCW)      │
   │                                                                                        │
   │  ECMWF Check:                                                                          │
   │    • 12:00 UTC → OPER stream → STAC query → No items found (data not published yet)   │
   │    • 06:00 UTC → SCDA stream → Check hours_ago < 6 → Still too recent                 │
   │    • 00:00 UTC → OPER stream → STAC query → ✅ Items found!                           │
   │                                                                                        │
   │  Position Lookup (from storm_df with merged historical + forecast data):              │
   │    • Target time: 2026-02-03 00:00 UTC                                                │
   │    • Closest track point: 2026-02-02 23:30 UTC (0.5h away < 3h threshold)             │
   │    • Historical position: lat=-14.8°, lon=42.5°                                       │
   │                                                                                        │
   │  Output:                                                                               │
   │    • storm_init_time = 2026-02-03 00:00 UTC (shifted back 12h)                        │
   │    • storm_init_lat = -14.8°, storm_init_lon = 42.5° (historical position)            │
   │                                                                                        │
   │  User Message:                                                                         │
   │    "⚠️ Data availability: ECMWF data not available at 2026-02-03 12:00 UTC.           │
   │     Shifted back 12h to 2026-02-03 00:00 UTC.                                          │
   │     📍 Storm position adjusted to historical track: -14.8°, 42.5°"                    │
   └────────────────────────────────────────────────────────────────────────────────────────┘


   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  GLOBAL VARIABLE UPDATES AFTER TIME SHIFT                                                 │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  The following global variables are updated when ECMWF data requires a time shift:       │
   │                                                                                           │
   │  Variable             │ Before Shift         │ After Shift                               │
   │  ─────────────────────┼──────────────────────┼───────────────────────────────────────    │
   │  storm_init_time      │ 2026-02-03 12:00     │ 2026-02-03 00:00                          │
   │  storm_init_lat       │ -15.5° (current)     │ -14.8° (historical)                       │
   │  storm_init_lon       │ 43.0° (current)      │ 42.5° (historical)                        │
   │  time_t0              │ 2026-02-03 12:00     │ 2026-02-03 00:00                          │
   │  time_t_minus_6       │ 2026-02-03 06:00     │ 2026-02-02 18:00                          │
   │                                                                                           │
   │  This ensures Aurora initializes with:                                                   │
   │  • Atmospheric data from the correct (available) time                                    │
   │  • Storm position matching that atmospheric data time                                    │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Storm Selection & Classification

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              STORM SELECTION & ACTIVE/HISTORICAL CLASSIFICATION                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   The system classifies storms into two categories that determine forecast behavior:

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │                              STORM CLASSIFICATION                                         │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │   🔴 ACTIVE/CURRENT STORMS                   📜 HISTORICAL STORMS                        │
   │   ─────────────────────────                  ──────────────────────                       │
   │                                                                                           │
   │   Sources:                                   Sources:                                     │
   │   • source == 'realtime'                     • All other sources                         │
   │   • source == 'ibtracs_active'               • Tropycal historical data                  │
   │   • source == 'jtwc_rss'                     • Past year IBTrACS records                 │
   │   • cache_entry['is_active'] == True                                                     │
   │                                                                                           │
   │   Characteristics:                           Characteristics:                             │
   │   • Storm is still ongoing                   • Storm has completed lifecycle              │
   │   • No known endpoint/dissipation            • Full track data available                  │
   │   • Forecast horizon is estimated            • Known endpoint in dataset                  │
   │                                                                                           │
   │   Forecast Strategy:                         Forecast Strategy:                           │
   │   • Use intelligent early termination        • Forecast to known endpoint                 │
   │   • Monitor intensity during inference       • No early termination needed                │
   │   • Stop when storm weakens/dissipates       • Full forecast always runs                  │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   SELECTION WORKFLOW
   ══════════════════

   ┌─────────────────────┐
   │  User Selects Storm │
   │  from Dropdown      │
   └──────────┬──────────┘
              │
              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  confirm_selection() Function                                    │
   │                                                                  │
   │  1. Retrieve cache_entry for selected storm                     │
   │  2. Determine source type (realtime, ibtracs_active, etc.)      │
   │  3. Set global variables:                                        │
   │     • storm_id, storm_name, storm_year, storm_basin             │
   │     • storm_init_time, storm_end_time                           │
   │     • storm_init_lat, storm_init_lon                            │
   │     • is_active_storm ◄─── KEY CLASSIFICATION FLAG              │
   │                                                                  │
   └──────────┬───────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │  Classification Logic:                                            │
   │                                                                   │
   │  is_active_storm = (                                             │
   │      cache_entry.get('is_active', False) OR                      │
   │      source in ['realtime', 'ibtracs_active', 'jtwc_rss']        │
   │  )                                                                │
   │                                                                   │
   └──────────┬────────────────────────────────────────────────────────┘
              │
              ├────────────────────────────────────────┐
              │                                        │
              ▼                                        ▼
   ┌────────────────────────┐             ┌────────────────────────┐
   │  is_active_storm=True  │             │  is_active_storm=False │
   │                        │             │                        │
   │  • Print: "🔴 ACTIVE   │             │  • No special message  │
   │    STORM - Intelligent │             │  • Full forecast runs  │
   │    forecast termination│             │  • end_time from data  │
   │    enabled"            │             │                        │
   │  • Termination logic   │             │                        │
   │    will be active      │             │                        │
   │  • end_time estimated  │             │                        │
   │    (e.g., +120 hours)  │             │                        │
   └────────────────────────┘             └────────────────────────┘


   UI INDICATORS
   ═════════════

   The storm dropdown includes visual indicators:

   │ Storm Option                                          │ Meaning                    │
   ├───────────────────────────────────────────────────────┼────────────────────────────┤
   │ 🔴 STORM_NAME (2026) [BASIN] C#/TS - Active          │ Currently active storm     │
   │ 🟢 STORM_NAME (2026) [BASIN] C#/TS - Cat #           │ Current year, completed    │
   │ ⚪ STORM_NAME (2024) [BASIN] C#/TS - Cat #           │ Past year (historical)     │
   │ 🏠 (suffix)                                           │ Made landfall (recommended)│
   │ ⭐ DEFAULT                                            │ Default selection          │

```

---

## ECMWF Data Stream Selection

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ECMWF HRES DUAL-STREAM DATA ACQUISITION                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    Aurora requires TWO timesteps (T-6h and T0) for initialization.
    ECMWF publishes data on different streams based on time:

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                           │
    │      00Z ────────► 06Z ────────► 12Z ────────► 18Z ────────► 00Z                         │
    │       │             │             │             │             │                           │
    │       ▼             ▼             ▼             ▼             ▼                           │
    │    ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐                      │
    │    │ OPER │      │ SCDA │      │ OPER │      │ SCDA │      │ OPER │                      │
    │    │ STAC │      │ BLOB │      │ STAC │      │ BLOB │      │ STAC │                      │
    │    └──────┘      └──────┘      └──────┘      └──────┘      └──────┘                      │
    │                                                                                           │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │  STREAM ROUTING LOGIC                                                                     │
    ├───────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                           │
    │  def get_stream_for_time(hour):                                                          │
    │      if hour in [0, 12]:   return ("OPER", "STAC API")    # Planetary Computer catalog   │
    │      if hour in [6, 18]:   return ("SCDA", "Blob Storage") # Direct blob download        │
    │                                                                                           │
    │  Example: Storm init at 06Z                                                              │
    │  ─────────────────────────                                                               │
    │  T0 (06Z)   ──► SCDA stream ──► Blob Storage download                                    │
    │  T-6h (00Z) ──► OPER stream ──► STAC API query + signed URL                              │
    │                                                                                           │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌────────────────────────────────────────────┐        ┌────────────────────────────────────────────┐
    │  OPER STREAM (STAC API)                    │        │  SCDA STREAM (Blob Storage)               │
    ├────────────────────────────────────────────┤        ├────────────────────────────────────────────┤
    │                                            │        │                                            │
    │  Endpoint:                                 │        │  Endpoint:                                 │
    │  planetarycomputer.microsoft.com/          │        │  ai4edataeuwest.blob.core.windows.net/     │
    │  api/stac/v1                               │        │  ecmwf/{date}/{hour}z/ifs/0p25/scda        │
    │                                            │        │                                            │
    │  Auth:                                     │        │  Auth:                                     │
    │  planetary_computer.sign_inplace           │        │  SAS token from PC token API               │
    │                                            │        │  planetarycomputer.microsoft.com/          │
    │  Query:                                    │        │  api/sas/v1/token/ai4edataeuwest/ecmwf     │
    │  • collection: ecmwf-forecast              │        │                                            │
    │  • ecmwf:stream: oper                      │        │  File Selection:                           │
    │  • ecmwf:type: fc                          │        │  Filter for "-0h-" pattern in blob name    │
    │  • ecmwf:step: 0h                          │        │                                            │
    │  • ecmwf:resolution: 0.25                  │        │                                            │
    │                                            │        │                                            │
    └────────────────────────────────────────────┘        └────────────────────────────────────────────┘
```

---

## Aurora Model Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AURORA AI MODEL INTEGRATION                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  INPUT: AURORA BATCH OBJECT                                                                          │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐                 │
    │   │     SURFACE VARS      │   │   ATMOSPHERIC VARS    │   │     STATIC VARS       │                 │
    │   │   [batch, 2, H, W]    │   │  [batch, 2, L, H, W]  │   │       [H, W]          │                 │
    │   ├───────────────────────┤   ├───────────────────────┤   ├───────────────────────┤                 │
    │   │ • 2t  (2m temp)       │   │ • t  (temperature)    │   │ • z   (geopotential)  │                 │
    │   │ • 10u (10m u-wind)    │   │ • u  (u-wind)         │   │ • lsm (land-sea mask) │                 │
    │   │ • 10v (10m v-wind)    │   │ • v  (v-wind)         │   │ • slt (soil type)     │                 │
    │   │ • msl (pressure)      │   │ • q  (humidity)       │   │                       │                 │
    │   │                       │   │ • z  (geopotential)   │   │   Source: Bundled     │                 │
    │   │   Source: ECMWF HRES  │   │                       │   │                       │                 │
    │   │                       │   │   13 pressure levels  │   │                       │                 │
    │   │                       │   │   50→1000 hPa         │   │                       │                 │
    │   └───────────────────────┘   └───────────────────────┘   └───────────────────────┘                 │
    │                                                                                                      │
    │   ┌───────────────────────────────────────────────────────────────────────────────────────────┐     │
    │   │  METADATA                                                                                  │     │
    │   │  • lat: [721] tensor    • lon: [1440] tensor (0-360°)    • time: (datetime,)              │     │
    │   │  • atmos_levels: (50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000)        │     │
    │   └───────────────────────────────────────────────────────────────────────────────────────────┘     │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  AZURE AI FOUNDRY ENDPOINT                                                                           │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   Model: aurora-0.25-finetuned                                                                      │
    │   Resolution: 0.25° (~28km at equator)                                                              │
    │   Forecast Step: 6 hours                                                                            │
    │                                                                                                      │
    │   ┌─────────────────────────────────────────────────────────────────────────────────────────┐       │
    │   │  INFERENCE LOOP                                                                         │       │
    │   │                                                                                         │       │
    │   │  foundry_client = FoundryClient(endpoint, token)                                       │       │
    │   │  channel = BlobStorageChannel(sas_url)  # Data transfer via blob                       │       │
    │   │  tracker = Tracker(init_lat, init_lon, init_time)  # TC tracking                       │       │
    │   │                                                                                         │       │
    │   │  for pred in submit(batch, model_name, num_steps, foundry_client, channel):            │       │
    │   │      tracker.step(pred)  # Extract storm center from each forecast                     │       │
    │   │      preds.append(pred)                                                                │       │
    │   │                                                                                         │       │
    │   │  track_df = tracker.results()  # DataFrame: time, lat, lon, msl, wind                  │       │
    │   └─────────────────────────────────────────────────────────────────────────────────────────┘       │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  OUTPUT: TROPICAL CYCLONE TRACK                                                                      │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   │ time                │ lat    │ lon      │ lon_converted │ msl      │ wind   │                   │
    │   ├─────────────────────┼────────┼──────────┼───────────────┼──────────┼────────┤                   │
    │   │ 2024-09-25 06:00:00 │ 22.45  │ 275.32   │ -84.68        │ 99234.5  │ 42.3   │                   │
    │   │ 2024-09-25 12:00:00 │ 24.12  │ 277.89   │ -82.11        │ 98156.2  │ 51.8   │                   │
    │   │ 2024-09-25 18:00:00 │ 26.34  │ 280.45   │ -79.55        │ 96823.1  │ 63.2   │                   │
    │   │ ...                 │ ...    │ ...      │ ...           │ ...      │ ...    │                   │
    │                                                                                                      │
    │   Note: lon_converted transforms from Aurora's [0,360] back to [-180,180] for visualization         │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Intelligent Forecast Termination

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENT FORECAST TERMINATION FOR ACTIVE STORMS                                   │
│                                                                                                          │
│   Applied ONLY to current/active storms (is_active_storm == True)                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   WHY IS THIS NEEDED?
   ═══════════════════

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  PROBLEM: Fixed Forecast Duration for Active Storms                                       │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  • Historical storms: We know the complete lifecycle → forecast to known endpoint        │
   │  • Active storms: No known endpoint → we use DEFAULT_FORECAST_HOURS (120h = 5 days)      │
   │                                                                                           │
   │  Issue: Many storms dissipate BEFORE the 5-day forecast window ends:                     │
   │                                                                                           │
   │    Example: Tropical Cyclone Luana (2026)                                                │
   │    ─────────────────────────────────────                                                 │
   │    Actual lifespan: ~2.5 days (Jan 22-25, 2026)                                         │
   │    Fixed forecast: 5 days                                                                │
   │    Result: Predictions extend ~2.5 days beyond actual storm dissipation                 │
   │                                                                                           │
   │  This wastes compute and produces meaningless forecasts for dissipated storms.          │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   TERMINATION CRITERIA
   ════════════════════

   The inference loop monitors mean sea level pressure (MSLP) and terminates early when the storm weakens:

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │                              TERMINATION THRESHOLD                                        │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  PRESSURE THRESHOLD                                                                      │
   │  ──────────────────                                                                      │
   │  Threshold: PRESSURE_THRESHOLD_MB = 1008.0 mb                                            │
   │  Consecutive steps required: 2                                                           │
   │                                                                                           │
   │  Rationale: 1008 mb is a typical threshold for a weakening tropical system.              │
   │  When MSLP rises above this for 2 consecutive steps (12 hours), the                      │
   │  system is losing organization and intensity - it has either:                            │
   │    • Dissipated over water                                                               │
   │    • Weakened after landfall                                                             │
   │    • Undergone extratropical transition                                                  │
   │                                                                                           │
   │  Note: Pressure-based termination is used because Aurora's TC Tracker provides           │
   │  reliable MSLP values directly, while wind speed requires additional conversion.         │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   INFERENCE LOOP WITH EARLY TERMINATION
   ═════════════════════════════════════

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │                                                                                         │
   │  # Initialize counters                                                                  │
   │  consecutive_weak_pressure_steps = 0                                                    │
   │  early_termination_reason = None                                                        │
   │                                                                                         │
   │  for pred in submit(batch, model_name, num_steps, ...):                                │
   │      tracker.step(pred)                                                                 │
   │      preds.append(pred)                                                                 │
   │                                                                                         │
   │      # Get current intensity                                                            │
   │      current_track = tracker.results()                                                  │
   │      latest_mslp = current_track.iloc[-1]['msl'] / 100 # Convert Pa → mb               │
   │                                                                                         │
   │      # EARLY TERMINATION CHECK (Active Storms Only)                                     │
   │      if is_active_storm and latest_mslp is not None:                                    │
   │          ┌─────────────────────────────────────────────────────────────────────┐       │
   │          │  # Pressure threshold (consecutive steps)                           │       │
   │          │  if latest_mslp > 1008.0:                                           │       │
   │          │      consecutive_weak_pressure_steps += 1                           │       │
   │          │      if consecutive_weak_pressure_steps >= 2:                       │       │
   │          │          print("⚠️ MSLP above 1008 mb for 2 steps - dissipating")  │       │
   │          │          break  ◄── TERMINATE                                       │       │
   │          │  else:                                                              │       │
   │          │      consecutive_weak_pressure_steps = 0  # Reset counter           │       │
   │          └─────────────────────────────────────────────────────────────────────┘       │
   │                                                                                         │
   │  # Final output includes termination info                                               │
   │  print(f"Actual steps: {step_count}/{NUM_SIX_HOUR_STEPS}")                             │
   │  if early_termination_reason:                                                           │
   │      print(f"⚠️ Early termination: {early_termination_reason}")                        │
   │                                                                                         │
   └─────────────────────────────────────────────────────────────────────────────────────────┘


   DECISION FLOWCHART
   ══════════════════

                           ┌──────────────────────────┐
                           │   Start Inference Step   │
                           └────────────┬─────────────┘
                                        │
                                        ▼
                           ┌──────────────────────────┐
                           │  is_active_storm == True? │
                           └────────────┬─────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                         YES                          NO
                          │                           │
                          ▼                           ▼
           ┌──────────────────────────┐    ┌──────────────────────────┐
           │  Check MSLP > 1008 mb?   │    │  Continue to next step   │
           └────────────┬─────────────┘    │  (no termination logic)  │
                        │                  └──────────────────────────┘
               ┌────────┴────────┐
               │                 │
              YES                NO
               │                 │
               ▼                 ▼
    ┌───────────────────────┐  ┌──────────────────────────┐
    │  Increment counter    │  │  Reset counter to 0      │
    │  consecutive_weak++   │  │  Continue to next step   │
    └───────────┬───────────┘  └──────────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │  counter >= 2?        │
    └───────────┬───────────┘
                │
       ┌────────┴────────┐
       │                 │
      YES                NO
       │                 │
       ▼                 ▼
 ┌──────────────────┐  ┌──────────────────────────┐
 │  TERMINATE       │  │  Continue to next step   │
 │  "MSLP above     │  └──────────────────────────┘
 │   1008 mb"       │
 └──────────────────┘


   EXAMPLE OUTPUT
   ══════════════

   🌀 Starting Aurora inference for Hurricane LUANA...
      Model: aurora-0.25-finetuned
      Forecast steps: 20 (6-hour increments)
      Total forecast period: 120 hours

   🔴 ACTIVE STORM DETECTED - Intelligent forecast termination ENABLED
      Pressure threshold: 1008.0 mb (require 2 consecutive steps)

      ✓ Step 5/20: 2026-01-23 18:00:00 | MSLP: 987.3 mb
      ✓ Step 10/20: 2026-01-25 00:00:00 | MSLP: 1002.5 mb

      ⚠️ EARLY TERMINATION: MSLP (1012.4 mb) above 1008.0 mb for 2 consecutive steps
      Storm is losing organization.

   ✓ Aurora inference completed!
     - Total predictions: 11
     - Actual forecast steps: 11/20
     - ⚠️ Early termination: MSLP (1012.4 mb) exceeded 1008.0 mb for 2 consecutive steps
     - Final forecast time: 2026-01-25 06:00:00
```

---

## Cone of Uncertainty Visualization

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               CONE OF UNCERTAINTY METHODOLOGY                                            │
│                                                                                                          │
│   The cone of uncertainty represents the possible range of storm positions as forecast error grows      │
│   with time. The implementation uses a geometric expansion along the predicted track path.               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


   ALGORITHM OVERVIEW
   ═══════════════════

   The cone is constructed using Shapely's geometric operations:

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  PARAMETERS                                                                               │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  Parameter          │  Value       │  Description                                        │
   │  ───────────────────┼──────────────┼───────────────────────────────────────────────────  │
   │  base_radius        │  0.3°        │  Initial radius at T+0 (forecast start)             │
   │  growth_rate        │  0.12°/step  │  Radius increase per 6-hour forecast step          │
   │  end_multiplier     │  1.5×        │  Extra expansion at final track points (umbrella)  │
   │  buffer_resolution  │  32          │  Points per circle for smooth geometry             │
   │                                                                                           │
   │  Example radius progression:                                                              │
   │    T+0:   0.3° (~33 km)                                                                  │
   │    T+24:  0.3 + (4 × 0.12) = 0.78° (~87 km)                                             │
   │    T+48:  0.3 + (8 × 0.12) = 1.26° (~140 km)                                            │
   │    T+120: 0.3 + (20 × 0.12) = 2.7° (~300 km) with 1.5× multiplier = ~4.05° (~450 km)   │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   GEOMETRIC CONSTRUCTION
   ══════════════════════

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  STEP 1: Create Expanding Circles at Each Track Point                                   │
   │                                                                                         │
   │  for i in range(n_points):                                                              │
   │      radius = base_radius + (i * growth_rate)                                           │
   │                                                                                         │
   │      # Apply umbrella effect for last 3 points                                          │
   │      if i >= n_points - 3:                                                              │
   │          progress = (i - (n_points - 3)) / 2  # 0, 0.5, 1.0                             │
   │          radius *= (1 + progress * (end_multiplier - 1))                                │
   │                                                                                         │
   │      point = Point(lons[i], lats[i])                                                    │
   │      circle = point.buffer(radius, resolution=32)                                       │
   │      circles.append(circle)                                                             │
   └─────────────────────────────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  STEP 2: Create Buffered Line Segments Between Points                                   │
   │                                                                                         │
   │  for i in range(n_points - 1):                                                          │
   │      radius_start = base_radius + (i * growth_rate)                                     │
   │      radius_end = base_radius + ((i + 1) * growth_rate)                                 │
   │      avg_radius = (radius_start + radius_end) / 2                                       │
   │                                                                                         │
   │      segment = LineString([(lons[i], lats[i]), (lons[i+1], lats[i+1])])                │
   │      buffered_segment = segment.buffer(avg_radius, cap_style=2)  # flat caps           │
   │      circles.append(buffered_segment)                                                   │
   └─────────────────────────────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  STEP 3: Union All Geometries for Smooth Cone                                           │
   │                                                                                         │
   │  cone_shape = unary_union(circles)                                                      │
   │                                                                                         │
   │  # Extract polygon coordinates for plotting                                             │
   │  if cone_shape.geom_type == 'Polygon':                                                  │
   │      cone_coords = list(cone_shape.exterior.coords)                                     │
   │  elif cone_shape.geom_type == 'MultiPolygon':                                           │
   │      largest = max(cone_shape.geoms, key=lambda p: p.area)                              │
   │      cone_coords = list(largest.exterior.coords)                                        │
   └─────────────────────────────────────────────────────────────────────────────────────────┘


   VISUAL STRUCTURE
   ════════════════

   The cone grows progressively wider along the forecast track:

            T+0 (Start)                                                    T+120 (End)
               ●                                                              ○
              /|\                                                            /│\
             / | \                                                          / │ \
            /  |  \         Track Direction ─────────────────────►         /  │  \
           │   │   │                                                      /   │   \
           │   │   │                                                     /    │    \
            \  │  /                                                     │     │     │
             \ │ /              ─────────────────────────────►          │     │     │
              \│/                                                        \    │    /
               ●                                                          \   │   /
                                                                           \  │  /
           r = 0.3°                                                         \ │ /
         (~33 km)                                                            \│/
                                                                              ○
                                                                         r = 4.05°
                                                                        (~450 km)


   RENDERING
   ═════════

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  MATPLOTLIB / CARTOPY                                                                     │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  cone_polygon = plt.Polygon(                                                             │
   │      cone_coords,                                                                         │
   │      facecolor='orange',     # Fill color                                                │
   │      edgecolor='darkorange', # Border color                                              │
   │      linewidth=1.5,                                                                       │
   │      alpha=0.3,              # Semi-transparent                                          │
   │      transform=ccrs.PlateCarree(),                                                        │
   │      zorder=0                # Behind track lines                                        │
   │  )                                                                                        │
   │  ax.add_patch(cone_polygon)                                                               │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  FOLIUM (INTERACTIVE MAP)                                                                 │
   ├───────────────────────────────────────────────────────────────────────────────────────────┤
   │                                                                                           │
   │  folium.Polygon(                                                                          │
   │      locations=[[lat, lon] for lat, lon in zip(cone_lats, cone_lons)],                   │
   │      color='darkorange',                                                                  │
   │      weight=2,                                                                            │
   │      fill=True,                                                                           │
   │      fill_color='orange',                                                                 │
   │      fill_opacity=0.25,                                                                   │
   │      popup='Cone of Uncertainty'                                                          │
   │  )                                                                                        │
   │                                                                                           │
   │  Note: The cone polygon is also used for infrastructure intersection analysis            │
   │  to identify power grid assets within the potential storm impact area.                   │
   │                                                                                           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   INFRASTRUCTURE IMPACT ANALYSIS
   ══════════════════════════════

   The cone polygon serves dual purposes:

   1. VISUALIZATION: Shows possible storm positions as orange semi-transparent region
   
   2. SPATIAL FILTERING: Identifies infrastructure at risk

      ┌─────────────────────────────────────────────────────────────────────────────────────┐
      │  # Create Shapely polygon from cone coordinates                                      │
      │  cone_polygon = Polygon(list(zip(cone_lons, cone_lats)))                            │
      │                                                                                      │
      │  # Filter infrastructure to items within the cone                                    │
      │  for infra_item in all_infrastructure:                                               │
      │      point = Point(infra_item['lon'], infra_item['lat'])                            │
      │      if cone_polygon.contains(point):                                                │
      │          at_risk_infrastructure.append(infra_item)                                   │
      │                                                                                      │
      │  # For transmission lines (LineStrings)                                              │
      │  line = LineString(line_coords)                                                      │
      │  if cone_polygon.intersects(line):                                                   │
      │      at_risk_lines.append(line)                                                      │
      └─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Asymmetric Impact Swath & Coastal Impact Zones

> **Notebook Reference**: Section 7.1b — Cells 49–50  
> **Detailed Algorithm Spec**: See [IMPACT_SWATH_ALGORITHM.md](IMPACT_SWATH_ALGORITHM.md) for the full mathematical reference.

The impact swath visualization produces a **single static matplotlib/Cartopy figure** with three layered systems that go beyond the simple cone of uncertainty to show physically motivated hazard areas.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     ASYMMETRIC IMPACT SWATH & COASTAL IMPACT ZONES                                       │
│                                                                                                          │
│   3-layer visualization system that models realistic hurricane hazard footprints                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


   LAYER ARCHITECTURE (bottom → top rendering)
   ════════════════════════════════════════════

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  Z │  Layer                          │ Description                                     │
   ├────┼─────────────────────────────────┼─────────────────────────────────────────────────┤
   │  0 │  Base map (ocean, land fills)   │  Natural Earth 50m coastlines                   │
   │  1 │  Coastal impact tiers           │  Flood → Surge → Core (outermost first)        │
   │  2 │  Swath tiers                    │  Outer → Mid → Inner (outermost first)          │
   │  3 │  Observed track                 │  Black solid line + dots                        │
   │  4 │  Forecast track                 │  Blue dashed line                               │
   │  5 │  Position markers               │  Colored by SS category (Knaff-Zehr)            │
   │  6 │  Start marker                   │  Lime star                                      │
   │  7 │  24h time labels + landfall ▲   │  +24h, +48h, … annotations                     │
   │  8 │  Coastlines, borders, states    │  Drawn on top for clarity                       │
   │  9 │  Landfall annotation boxes      │  MSLP, Vmax, SS category                        │
   └────┴─────────────────────────────────┴─────────────────────────────────────────────────┘
```

### Part 1 — Asymmetric Intensity-Modulated Impact Swath

The swath models the **total hazard footprint** along the forecast track. Its width at each forecast position combines two independent physical quantities:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            IMPACT SWATH WIDTH CALCULATION                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   At each forecast position i:

   ┌──────────────────────────────────────────────────────────────┐
   │  1. NHC Track-Uncertainty Radius (per-side offset)           │
   │     base_half_km = max(nhc_radius_km(lead_hours), 40 km)     │
   │                                                              │
   │     NHC Official Radii:                                      │
   │     Lead(h): 0   6   12   24   36   48   72   96   120      │
   │     Rad(km): 0   40  65   100  140  175  240  325  410      │
   │                                                              │
   │     Linearly interpolated for any lead time.                 │
   │     Minimum floor: 40 km                                     │
   └──────────────────────────────────────────────────────────────┘
                              +
   ┌──────────────────────────────────────────────────────────────┐
   │  2. Pressure-Derived Wind-Extent Buffer                      │
   │     dp = max(1013 − MSLP, 0)                                 │
   │     wind_extent_km = 40 + 2 × min(dp, 70)                   │
   │                                                              │
   │     Empirical fit to Knaff et al. (2013) R34/ROCI:           │
   │     dp=0  → 40 km   (minimal / TD)                          │
   │     dp=30 → 100 km  (Cat 1)                                 │
   │     dp=50 → 140 km  (Cat 3)                                 │
   │     dp=70 → 180 km  (Cat 4-5, capped)                       │
   └──────────────────────────────────────────────────────────────┘
                              =
   ┌──────────────────────────────────────────────────────────────┐
   │  Total impact_half_km = base_half_km + wind_extent_km        │
   │  (converted to degrees via km_to_degrees(km, lat))           │
   └──────────────────────────────────────────────────────────────┘


   RIGHT-OF-TRACK ASYMMETRY
   ════════════════════════

   NH cyclones have stronger winds on the RIGHT side (storm translation
   adds to rotational winds).  Ref: Uhlhorn & Nolan (2012).

                 ┌──────────────────────────────────────────────┐
                 │  Northern Hemisphere (lat ≥ 0):              │
                 │    right_factor = 1.25                       │
                 │    left_factor  = 0.80                       │
                 │                                              │
                 │  Southern Hemisphere (lat < 0):  ← mirrored  │
                 │    right_factor = 0.80                       │
                 │    left_factor  = 1.25                       │
                 └──────────────────────────────────────────────┘

   The perpendicular offsets from the track centre are:

     left_offset  = half_width × tier_fraction × left_factor
     right_offset = half_width × tier_fraction × right_factor

   This makes the swath visibly wider on the right (east) side for
   northward-moving NH storms, matching observed damage patterns.


   3-TIER NESTED SWATH
   ═══════════════════

   ┌──────────┬──────────────────┬───────────────┬───────┬───────────────────┐
   │  Tier    │  Width Fraction  │  Color        │ Alpha │ Label             │
   ├──────────┼──────────────────┼───────────────┼───────┼───────────────────┤
   │  Inner   │  25 %            │  Crimson      │  0.55 │ Inner core        │
   │  Middle  │  55 %            │  Dark Orange  │  0.40 │ Mid-level         │
   │  Outer   │  100 %           │  Gold         │  0.25 │ Outer extent      │
   └──────────┴──────────────────┴───────────────┴───────┴───────────────────┘

   Each tier polygon is built from left/right edge lists, closed into a ring,
   then morphologically smoothed (dilate 0.12°, erode 0.06°) to remove jagged
   step artifacts from the discrete point offsets.
```

### Part 2 — Track-Wide Coastal Impact Zones

A storm doesn't need to make landfall to cause surge and flooding — passing nearby is enough. The algorithm highlights coastlines near the **entire forecast track**, not just at landfall.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           COASTAL IMPACT ZONE ALGORITHM                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   THREE IMPACT TIERS
   ══════════════════

   ┌──────────┬──────────────────┬────────────────┬───────┬────────────────────────────────────┐
   │  Tier    │  Base Radius(km) │  Color         │ Alpha │ Physical Meaning                   │
   ├──────────┼──────────────────┼────────────────┼───────┼────────────────────────────────────┤
   │  Core    │  200             │  Crimson       │  0.50 │ Hurricane-force wind + severe surge│
   │  Surge   │  450             │  Dark Orange   │  0.35 │ TS winds / surge warning           │
   │  Flood   │  750             │  Light Sky Blue│  0.25 │ Outer bands / rainfall flooding    │
   └──────────┴──────────────────┴────────────────┴───────┴────────────────────────────────────┘

   Note: The 200/450/750 km base radii are empirical approximations from
   Helene 2024's actual NHC warning footprint, not from a physical model.


   INTENSITY SCALING
   ═════════════════

   All three radii are scaled by the pressure deficit:

     dp    = max(1013 − MSLP, 0)
     scale = 1.0 + 0.4 × min(dp, 75) / 75

   Gives a linear ramp from 1.0× (TD) to 1.4× (strong Cat 4).


   CONSTRUCTION PIPELINE
   ═════════════════════

   ┌──────────────────────────┐
   │ For EVERY forecast point │
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  Create Shapely circle   │  r = km_to_degrees(base_km × scale, lat)
   │  at each tier radius     │  Point(lon, lat).buffer(r, resolution=48)
   └────────────┬─────────────┘
                │
                ▼
   ┌──────────────────────────┐
   │  unary_union() per tier  │  Merge all circles into one polygon per tier
   └────────────┬─────────────┘
                │
                ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │  COASTLINE INTERSECTION                                                │
   │                                                                        │
   │  1. Load Natural Earth 50m land polygons (clipped to ±12° AOI bbox)   │
   │  2. Intersect tier polygon with land_union.boundary (coastline)        │
   │  3. Buffer resulting lines into drawable strips:                       │
   │       Core: 0.18°  |  Surge: 0.14°  |  Flood: 0.10°                  │
   │                                                                        │
   │  Uses shapely.prepared.prep() for fast contains() checks              │
   └────────────────────────────────────────────────────────────────────────┘
```

### Part 3 — Landfall Detection & Annotation

Landfall is detected as an **ocean→land transition** along the forecast track:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             LANDFALL DETECTION                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   ALGORITHM
   ═════════

   For each consecutive pair of forecast positions (i-1, i):

     IF  NOT land_prep.contains(Point(lon[i-1], lat[i-1]))    ← previous point over ocean
     AND     land_prep.contains(Point(lon[i],   lat[i]))      ← current point over land
     THEN → LANDFALL detected at position i

   Where land_prep = shapely.prepared.prep(natural_earth_land_polygon)


   ANNOTATION
   ══════════

   Each landfall gets a red triangle marker (▲) plus an annotation box:

     ┌──────────────────────────────┐
     │  LANDFALL  +{lead_hours}h    │
     │  {MSLP} mb  |  {Vmax} kt    │
     │  {SS Category}               │
     └──────────────────────────────┘

   Vmax is estimated via Knaff-Zehr (for labels/colors ONLY, not swath widths):

     dp   = max(1013 − MSLP, 0)
     Vmax = 6.3 × √dp + 0.15 × dp       (result in knots)


   SAFFIR-SIMPSON CATEGORY COLORS
   ═════════════════════════════

   ┌──────────┬─────────────┬──────────────────┐
   │ Category │ Vmax (kt)   │ Color            │
   ├──────────┼─────────────┼──────────────────┤
   │ Cat 5    │ ≥ 137       │ #7030A0 (purple) │
   │ Cat 4    │ ≥ 113       │ #C00000 (dk red) │
   │ Cat 3    │ ≥ 96        │ #FF0000 (red)    │
   │ Cat 2    │ ≥ 83        │ #FFC000 (amber)  │
   │ Cat 1    │ ≥ 64        │ #FFFF00 (yellow) │
   │ TS       │ ≥ 34        │ #00B050 (green)  │
   │ TD       │ < 34        │ #5B9BD5 (blue)   │
   └──────────┴─────────────┴──────────────────┘

   These colors are used for:
     • Position markers along the forecast track (Layer 5)
     • Landfall annotation category labels
     • NOT used for swath width calculations
```

### Key Design Constraints

| Constraint | Rationale |
|---|---|
| **Additive wind-extent buffer** (not multiplicative) | Track uncertainty and wind hazard extent are independent physical sources |
| **NHC radius = per-side offset** (not diameter) | NHC radii measure how far the center might deviate, applied to each side |
| **MSLP in Pascals from Aurora** | Divided by 100 to get millibars; NaN → column mean → 1013 mb fallback |
| **Knaff-Zehr for labels only** | Not used for swath widths — only for position marker colors and landfall annotations |
| **Auto-flipping hemisphere asymmetry** | `lat ≥ 0` → stronger right; `lat < 0` → stronger left (Coriolis mirror) |
| **Empirical coastal radii** | 200/450/750 km from Helene 2024 NHC warning footprint, not a physical model |
| **Morphological smoothing** | `buffer(0.12).buffer(-0.06)` removes jagged polygon edges from discrete offsets |

> For the full mathematical specification and helper function signatures, see [IMPACT_SWATH_ALGORITHM.md](IMPACT_SWATH_ALGORITHM.md).

---

## Aurora Tracker Optimal Initialization Algorithm

### Background: How Aurora's TC Tracker Works

Aurora's tropical cyclone tracker ([`aurora.Tracker`](https://github.com/microsoft/aurora/blob/main/aurora/tracker.py)) 
locates storm centers by finding **local pressure minima** in the MSL (mean sea level pressure) field. 
Understanding its internal mechanics explains why we need careful initialization:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           AURORA TRACKER INTERNAL MECHANICS                                              │
│                      (from microsoft/aurora GitHub repository)                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   CORE ALGORITHM: get_closest_min()
   ══════════════════════════════════
   
   1. Extract a box around the expected storm location (±5° lat/lon)
   2. Apply Gaussian smoothing (sigma=1) to reduce noise
   3. Find local minima using scipy.ndimage.minimum_filter(size=8)
   4. Remove edge minima (tracking failures occur at boundaries)
   5. Return the closest minimum to the expected position
   
   
   CRITICAL FAILURE MODE: NoEyeException
   ═════════════════════════════════════
   
   ┌──────────────────────────────────────────────────────────────────────────────────────┐
   │  class NoEyeException(Exception):                                                    │
   │      """Raised when no eye can be found."""                                          │
   │                                                                                      │
   │  # In get_closest_min():                                                             │
   │  if local_minima.sum() == 0:                                                         │
   │      raise NoEyeException()  ◄── No detectable pressure minimum in search box       │
   │                                                                                      │
   │  # At first step:                                                                    │
   │  raise NoEyeException("Completely failed at the first step.")                        │
   │                       ▲                                                              │
   │                       └── FATAL: Cannot initialize tracking at all                   │
   └──────────────────────────────────────────────────────────────────────────────────────┘
   
   
   TRACKING STRATEGY (Tracker.step method)
   ═══════════════════════════════════════
   
   ┌─────────────────┐
   │  Extrapolate    │◄── Guess next position from previous track points
   │  lat/lon guess  │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐     ┌─────────────────┐
   │  Try MSL first  │────►│  NoEyeException │──┐
   │  (boxes: 5°→1.5°)     │  (no minimum)   │  │
   └────────┬────────┘     └─────────────────┘  │
            │ Success                           │
            ▼                                   ▼
   ┌─────────────────┐     ┌─────────────────┐
   │  Snap to local  │     │  Fallback to    │
   │  MSL minimum    │     │  z700 (geopot)  │
   └─────────────────┘     └────────┬────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │  Still fails?   │────► Extrapolate (risky)
                           │  self.fails += 1│      or raise NoEyeException
                           └─────────────────┘


   WHY WEAK STORMS FAIL
   ════════════════════
   
   │  Storm Intensity  │  Pressure Anomaly  │  Tracker Outcome                      │
   ├───────────────────┼────────────────────┼───────────────────────────────────────┤
   │  TD (<34 kt)      │  ~1005-1010 mb     │  ❌ No detectable minimum - fails     │
   │  TS (34-63 kt)    │  ~995-1005 mb      │  ⚠️ Sometimes works, often fails      │
   │  Cat 1+ (≥64 kt)  │  <990 mb           │  ✓ Clear warm-core minimum detected   │
   │  Major (≥100 kt)  │  <970 mb           │  ✓✓ Very strong signal                │
   
   The tracker needs a DETECTABLE LOCAL MINIMUM in the pressure field.
   Weak, disorganized storms have diffuse pressure patterns with no clear center.


   AURORA'S OFFICIAL EXAMPLE: TYPHOON NANMADOL
   ════════════════════════════════════════════
   
   From Microsoft's documentation (microsoft.github.io/aurora/example_tc_tracking.html):
   
   tracker = Tracker(
       init_lat=27.50,           ◄── Already at 27.5°N
       init_lon=132,             
       init_time=datetime(2022, 9, 17, 12, 0)  ◄── Sept 17, 2022
   )
   
   At this initialization point, Nanmadol was:
   • Category 4-equivalent super typhoon
   • Winds: 250 km/h (135 kt)
   • Pressure: 910 hPa (very deep)
   • Clear, well-defined eye
   
   ⚠️  NOTE: Aurora's example uses an ALREADY INTENSE storm, not genesis!
```

### The 64 kt Threshold: Empirical Choice

The **64 kt threshold** (Category 1 hurricane) was chosen empirically based on:

1. **Meteorological convention**: 64 kt marks the transition to hurricane strength on the 
   Saffir-Simpson scale, where storms typically develop a well-defined warm core and eye structure.

2. **Pressure signature**: At ~64 kt, central pressure typically drops to <990 mb, creating 
   a detectable local minimum that Aurora's `minimum_filter(size=8)` can reliably identify.

3. **Aurora's own example**: Microsoft's Typhoon Nanmadol example initializes at **135 kt** - 
   suggesting the model works best with well-organized storms.

4. **`NoEyeException` avoidance**: Through testing, we found storms below ~50 kt frequently 
   trigger `NoEyeException("Completely failed at the first step.")` because the pressure 
   minimum is too weak or diffuse.

> **The 64 kt threshold is NOT explicitly defined in Aurora's code** - it's our empirical 
> choice to maximize tracking success while allowing initialization early enough in the 
> storm lifecycle to have a useful forecast window.

---

### Optimal Initialization Point Selection

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        OPTIMAL INITIALIZATION POINT SELECTION                            │
│                                                                                          │
│   Goal: Find the "Goldilocks" point - not too early, not too late, just right           │
│                                                                                          │
│   CRITICAL CONSTRAINT: Init time MUST align with ECMWF synoptic hours (00/06/12/18 UTC) │
└─────────────────────────────────────────────────────────────────────────────────────────┘


   ECMWF DATA AVAILABILITY CONSTRAINT
   ═══════════════════════════════════

   ┌───────────────────────────────────────────────────────────────────────────────────────────┐
   │  CRITICAL: ECMWF HRES data is ONLY available at synoptic hours:                          │
   │                                                                                           │
   │      00Z ──────── 06Z ──────── 12Z ──────── 18Z ──────── 00Z                             │
   │       ✓            ✓            ✓            ✓            ✓                              │
   │                                                                                           │
   │  Track points at other hours (e.g., 03Z, 09Z, 15Z, 21Z) CANNOT be used for              │
   │  Aurora initialization because no weather data exists for those times.                   │
   │                                                                                           │
   │  The algorithm:                                                                          │
   │  1. ONLY considers track points where hour ∈ {0, 6, 12, 18}                             │
   │  2. Skips all other points (even if they have better intensity scores)                   │
   │  3. If NO synoptic-hour points exist, snaps to nearest valid hour as fallback           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘


   VALIDATION FLOW
   ═══════════════

   ┌─────────────────────┐
   │  For each track     │
   │  point i:           │
   └──────────┬──────────┘
              │
              ▼
   ┌───────────────────────────────────────────┐
   │  Is track_time.hour in {0, 6, 12, 18}?   │
   └─────────────────┬─────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
         YES                    NO
          │                     │
          ▼                     ▼
   ┌─────────────────┐   ┌─────────────────────────────────┐
   │  Continue to    │   │  SKIP this point                │
   │  intensity      │   │  skipped_non_synoptic += 1      │
   │  scoring        │   │                                 │
   └─────────────────┘   │  No ECMWF data available for    │
                         │  this hour - cannot use it      │
                         └─────────────────────────────────┘


   FALLBACK: SNAP TO NEAREST SYNOPTIC HOUR
   ════════════════════════════════════════

   If NO track points fall on synoptic hours (rare, but possible):

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │                                                                                         │
   │  Example: Track only has points at 03Z, 09Z, 15Z, 21Z                                  │
   │                                                                                         │
   │  Fallback algorithm:                                                                    │
   │  1. Find first point with valid wind data                                              │
   │  2. Round to nearest synoptic hour:                                                    │
   │                                                                                         │
   │     03Z ──► 06Z (round up)                                                             │
   │     09Z ──► 12Z (round up)                                                             │
   │     15Z ──► 18Z (round up)                                                             │
   │     21Z ──► 00Z next day (round up)                                                    │
   │     22Z ──► 00Z next day (round up, closer to 00 than 18)                              │
   │                                                                                         │
   │  ⚠️ WARNING: Snapped times have slightly offset storm positions                        │
   │     (storm moves during the hour gap between observation and data)                     │
   │                                                                                         │
   └─────────────────────────────────────────────────────────────────────────────────────────┘


   STORM LIFECYCLE TIMELINE
   ════════════════════════

   Genesis ──────► Intensification ──────► Peak ──────► Decay ──────► Dissipation
      │                   │                  │             │               │
      ▼                   ▼                  ▼             ▼               ▼
   ┌─────┐           ┌─────────┐        ┌───────┐    ┌─────────┐     ┌─────────┐
   │ 25kt│    ───►   │  50-64kt│  ───►  │ >64kt │───►│100-140kt│ ───►│Weakening│
   │ TD  │           │Strong TS│        │Cat 1+ │    │  Major  │     │         │
   └─────┘           └─────────┘        └───────┘    └─────────┘     └─────────┘
      ❌                 ✓✓                ✓✓✓           ⚠️              ❌
    AVOID            GOOD              IDEAL        CAUTION          AVOID
   (-20 pts)       (+30 pts)         (+50 pts)     (-10 pts)      (no window)


   SCORING FUNCTION FOR EACH TRACK POINT
   ══════════════════════════════════════

                    ┌────────────────────────────────────────┐
                    │         FOR EACH POINT i:              │
                    │              score = 0                 │
                    └────────────────┬───────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
   │   WIND      │           │  PRESSURE   │           │  POSITION   │
   │  STRENGTH   │           │   DEPTH     │           │  IN TRACK   │
   └──────┬──────┘           └──────┬──────┘           └──────┬──────┘
          │                         │                         │
          ▼                         ▼                         ▼
   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
   │ ≥64kt: +50   │          │ <1010mb: +20 │          │ i=0:  -15    │
   │ ≥50kt: +30   │          │ <980mb: +10  │          │ i=1:  -5     │
   │ ≥34kt: +10   │          │  (bonus)     │          │              │
   │ <34kt: -20   │          │ No data: -5  │          │ Genesis      │
   │ >140kt: -10  │          │              │          │ Penalty      │
   └──────────────┘          └──────────────┘          └──────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │   FORECAST WINDOW   │
                          │   (remaining pts)   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────┴──────────┐
                          │  ≥10 pts (60h): +15 │
                          │  ≥5 pts  (30h): +10 │
                          │  <3 pts  (18h): -10 │
                          └─────────────────────┘


   SCORE DISTRIBUTION ALONG TRACK
   ═══════════════════════════════

   Score
    100│                          ★ OPTIMAL INIT POINT
       │                        ╱   ╲
     80│                      ╱       ╲
       │                    ╱           ╲
     60│                  ╱               ╲
       │                ╱                   ╲
     40│              ╱                       ╲
       │            ╱                           ╲
     20│          ╱                               ╲
       │        ╱                                   ╲
      0│──────╱─────────────────────────────────────╲─────────
       │    ╱                                         ╲
    -20│──╱─────────────────────────────────────────────╲─────
       └──┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬───► Time
        Gen   +12h  +24h  +36h  +48h  +60h  +72h  +84h  +96h
          │                 │                         │
          │                 │                         │
       Genesis           Sweet                    Limited
       Penalty            Spot                    Forecast
       Zone             (High wind +              Window
                        Good window)

   
   FINAL SELECTION
   ════════════════

   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │    All scored points sorted by:                                 │
   │                                                                 │
   │       1. HIGHEST SCORE (descending)                             │
   │       2. EARLIEST INDEX (ascending) ← tiebreaker                │
   │                                                                 │
   │    Winner = scored_points[0]                                    │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │   RETURN:                      │
                    │   • init_time                  │
                    │   • init_lat, init_lon         │
                    │   • init_vmax, init_mslp       │
                    │   • score (0-100 clamped)      │
                    │   • reason string              │
                    │   • warnings[]                 │
                    └────────────────────────────────┘
```

### Key Algorithmic Insights

| Strategy | Rationale |
|----------|----------|
| **Avoid genesis** | Storm structure is disorganized; vortex not well-defined for tracking |
| **Prefer 50-64 kt** | Strong enough for reliable tracking, not yet at chaotic peak intensity |
| **Penalize >140 kt** | Eyewall replacement cycles make tracking erratic |
| **Require forecast window** | Need future observed track to validate predictions |
| **Pressure as tiebreaker** | Deeper pressure = better organized warm core |

> The algorithm finds the **earliest reliable point** where Aurora's tracker can "lock on" to the storm's warm core structure while still having enough future track data to verify the forecast.

---

## GeoCatalog STAC Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           MICROSOFT PLANETARY COMPUTER PRO - GEOCATALOG INTEGRATION                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  UPLOAD PIPELINE                                                                                     │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   1. SAVE TO NETCDF                           2. UPLOAD TO BLOB                                     │
    │   ───────────────────                         ────────────────────                                   │
    │   • Surface variables only (2D)               • DefaultAzureCredential                              │
    │   • One file per timestamp                    • Container: hurricane-data                            │
    │   • Pattern: hurricane_{name}_{date}_{time}   • Generate SAS for access                             │
    │     _{suffix}_t{idx}.nc                                                                             │
    │                                                                                                      │
    │   3. CREATE STAC COLLECTION                   4. INGEST STAC ITEMS                                  │
    │   ──────────────────────────                  ────────────────────────                               │
    │   • ID: hurricane-{name}-{year}-Input-Data    • One item per timestamp                              │
    │   • API: 2025-04-30-preview                   • datacube + raster extensions                        │
    │   • item_assets definition                    • cube:dimensions, cube:variables                     │
    │                                                                                                      │
    │   5. CONFIGURE RENDER OPTIONS                 6. CONFIGURE MOSAICS                                  │
    │   ────────────────────────────                ──────────────────────                                 │
    │   SDK: PlanetaryComputerProClient             • "most-recent" mosaic                                │
    │   Variables rendered:                         • Empty CQL for all items                             │
    │   • msl: rdylbu_r, 95000-105000                                                                     │
    │   • t2m: plasma, 270-310                                                                            │
    │   • u10/v10: coolwarm, -50 to 50                                                                    │
    │   minZoom: 0 (global view support)                                                                  │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  AUTHENTICATION FLOW                                                                                 │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐                          │
    │   │ DefaultAzure     │      │   Token Request  │      │  Bearer Token    │                          │
    │   │ Credential       │─────►│   Scope:         │─────►│  Header:         │                          │
    │   │                  │      │   geocatalog.    │      │  Authorization:  │                          │
    │   │ Chain:           │      │   spatio.azure.  │      │  Bearer {token}  │                          │
    │   │ • Environment    │      │   com/.default   │      │                  │                          │
    │   │ • Managed ID     │      │                  │      │                  │                          │
    │   │ • Azure CLI      │      │                  │      │                  │                          │
    │   │ • VS Code        │      │                  │      │                  │                          │
    │   └──────────────────┘      └──────────────────┘      └──────────────────┘                          │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Query Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               OPENSTREETMAP INFRASTRUCTURE QUERY STRATEGY                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  OVERPASS API - MULTI-SERVER FAILOVER                                                                │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │                              ┌──────────────────────────────┐                                        │
    │                              │      Query Request           │                                        │
    │                              └──────────────┬───────────────┘                                        │
    │                                             │                                                        │
    │                                             ▼                                                        │
    │                              ┌──────────────────────────────┐                                        │
    │                              │  overpass-api.de             │◄──── Primary (Germany)                 │
    │                              └──────────────┬───────────────┘                                        │
    │                                    │        │                                                        │
    │                               Success?      │                                                        │
    │                                    │        │                                                        │
    │                             ┌──────┴──────┐ │ Timeout/429/Error                                      │
    │                             │             │ │                                                        │
    │                            YES            NO│                                                        │
    │                             │              ▼                                                         │
    │                             │   ┌──────────────────────────────┐                                     │
    │                             │   │  overpass.kumi.systems       │◄──── Fallback 1                     │
    │                             │   └──────────────┬───────────────┘                                     │
    │                             │          │       │                                                     │
    │                             │     Success?     │                                                     │
    │                             │          │       │                                                     │
    │                             │   ┌──────┴──────┐│ Timeout/Error                                       │
    │                             │   │             ││                                                     │
    │                             │  YES           NO│                                                     │
    │                             │   │             ▼                                                      │
    │                             │   │  ┌──────────────────────────────┐                                  │
    │                             │   │  │  maps.mail.ru/.../overpass   │◄──── Fallback 2 (Russia)         │
    │                             │   │  └──────────────────────────────┘                                  │
    │                             │   │                                                                    │
    │                             ▼   ▼                                                                    │
    │                        ┌─────────────┐                                                               │
    │                        │   Return    │                                                               │
    │                        │   Results   │                                                               │
    │                        └─────────────┘                                                               │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  TILED QUERY STRATEGY (Avoids API Timeouts)                                                          │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   Large query areas are split into smaller tiles to avoid Overpass API timeouts:                    │
    │                                                                                                      │
    │   ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
    │   │                              CONE OF UNCERTAINTY BOUNDING BOX                                │   │
    │   │  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐                                          │   │
    │   │  │     │     │     │     │     │     │     │     │  Substations/Plants: 5° × 5° tiles       │   │
    │   │  │ T1  │ T2  │ T3  │ T4  │ T5  │ T6  │ T7  │ T8  │  (Fewer features, larger area OK)        │   │
    │   │  │     │     │     │     │     │     │     │     │                                          │   │
    │   │  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤                                          │   │
    │   │  │     │     │     │     │     │     │     │     │  Transmission Lines: 3° × 3° tiles       │   │
    │   │  │ T9  │ T10 │ T11 │ T12 │ T13 │ T14 │ T15 │ T16 │  (Higher density, smaller tiles needed)  │   │
    │   │  │     │     │     │     │     │     │     │     │                                          │   │
    │   │  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤                                          │   │
    │   │  │     │     │     │     │     │     │     │     │                                          │   │
    │   │  │ T17 │ T18 │ T19 │ T20 │ T21 │ T22 │ T23 │ T24 │  Rate limiting: 1-2 sec between tiles    │   │
    │   │  │     │     │     │     │     │     │     │     │                                          │   │
    │   │  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘                                          │   │
    │   │                                                                                              │   │
    │   └─────────────────────────────────────────────────────────────────────────────────────────────┘   │
    │                                                                                                      │
    │   DEDUPLICATION: Track seen_ids across tile boundaries to avoid duplicate features                  │
    │                                                                                                      │
    │   SPATIAL FILTER: After download, filter to cone polygon using Shapely intersection                 │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  VOLTAGE CLASSIFICATION                                                                              │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                                      │
    │   Category        Voltage Range      Color         Line Weight    Default Visibility                │
    │   ──────────────────────────────────────────────────────────────────────────────────                │
    │   High            ≥ 345 kV           Red           4px            ✓ Shown                           │
    │   Medium-High     ≥ 115 kV           Orange        3px            Hidden (toggle)                   │
    │   Medium          ≥ 69 kV            Amber         2px            Hidden (toggle)                   │
    │   Low             < 69 kV            Yellow        2px            Hidden (toggle)                   │
    │   Unknown         N/A                Gray          2px            Hidden (toggle)                   │
    │                                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Summary

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      AUTHENTICATION METHODS BY SERVICE                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────┬────────────────────────┬───────────────────────────────────────┐
    │  SERVICE                         │  AUTH METHOD           │  CREDENTIALS                          │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  Planetary Computer Pro          │  Azure AD Bearer Token │  DefaultAzureCredential               │
    │  (GeoCatalog STAC)               │                        │  Scope: geocatalog.spatio.azure.com   │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  Azure AI Foundry                │  Bearer Token          │  AURORA_FOUNDRY_TOKEN env var         │
    │  (Aurora Model)                  │                        │                                       │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  Azure Blob Storage              │  Azure AD + SAS        │  DefaultAzureCredential               │
    │  (User data)                     │                        │  STORAGE_ACCOUNT_KEY for SAS gen      │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  Planetary Computer Public       │  PC Signer             │  planetary_computer.sign_inplace      │
    │  (ECMWF OPER via STAC)           │                        │  (automatic token refresh)            │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  ECMWF Blob Storage              │  SAS Token             │  PC token API:                        │
    │  (SCDA Stream)                   │                        │  /api/sas/v1/token/ai4edataeuwest     │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  IBTrACS / HURDAT / NHC          │  None                  │  Public APIs (no auth required)       │
    ├──────────────────────────────────┼────────────────────────┼───────────────────────────────────────┤
    │  Overpass API (OSM)              │  None                  │  Public API (rate-limited)            │
    └──────────────────────────────────┴────────────────────────┴───────────────────────────────────────┘
```

---

## Environment Variables Reference

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      REQUIRED ENVIRONMENT VARIABLES                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    # Microsoft Planetary Computer Pro
    STAC_CATALOG_URL=https://your-geocatalog.spatio.azure.com/stac

    # Azure AI Foundry (Aurora Model)
    AURORA_FOUNDRY_ENDPOINT=https://your-foundry.inference.ai.azure.com
    AURORA_FOUNDRY_TOKEN=your-api-token

    # Azure Blob Storage
    AURORA_BLOB_STORAGE_SAS=https://your-storage.blob.core.windows.net/?sv=...
    OUTPUT_BLOB_CONTAINER_URL=https://your-storage.blob.core.windows.net/container
    STORAGE_ACCOUNT_KEY=your-storage-key
```

---

## Key Python Dependencies

| Package | Purpose | Key Classes/Functions |
|---------|---------|----------------------|
| `microsoft-aurora` | Aurora AI Model | `Batch`, `Metadata`, `Tracker`, `FoundryClient`, `submit()` |
| `azure-planetarycomputer` | MPC Pro SDK | `PlanetaryComputerProClient`, `RenderOption`, `StacMosaic` |
| `azure-identity` | Azure Auth | `DefaultAzureCredential` |
| `azure-storage-blob` | Blob Storage | `BlobServiceClient`, `generate_blob_sas()` |
| `pystac-client` | STAC Catalog | `Client.open()`, `search()` |
| `planetary-computer` | PC Auth | `sign_inplace` modifier |
| `tropycal` | Storm Data | `TrackDataset`, `Realtime` |
| `xarray` | Data Processing | `open_dataset()`, `concat()`, `roll()` |
| `cfgrib` | GRIB2 Reading | xarray engine for ECMWF |
| `cartopy` | Map Projection | `PlateCarree`, features |
| `shapely` | Geometry | `Point`, `LineString`, `Polygon`, `unary_union` |
| `folium` | Interactive Maps | `Map`, `FeatureGroup`, `Polygon` |

---

*Architecture Documentation — January 2026*  
*Microsoft Planetary Computer Pro + Aurora AI Weather Foundation Model*
