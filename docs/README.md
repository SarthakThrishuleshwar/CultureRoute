# CultureRoute documentation

This folder contains the **actual proposed documentation set** for CultureRoute, plus prompts for future revisions. The documents are grounded in the eight-page `CultureRoute_DEV_AAT_Project_Specification.pdf` and the SQLite/data-model files inside `SmartTrip (1).zip` and `WanderMatch.zip`. The template video and supplied photos guide visual design only. Hackathon dates, submission rules, XR instructions, and unrelated product ambitions in the ZIP READMEs are not CultureRoute requirements.

## Read in this order

| Document | What it covers | Current status |
| --- | --- | --- |
| [PRD](PRD.md) | Research problem, product scope, six screens, requirements and acceptance criteria. | Proposed product specification. |
| [TRD](TRD.md) | Component contracts, planner and analytics logic, SQL limits, verification. | Proposed technical design. |
| [Database](DATABASE.md) | 24-table inventory, ERD, India filters, prepared views, metrics, reconciliation SQL. | Source counts verified; views proposed. |
| [Full data dictionary](DATA_DICTIONARY.md) | Every supplied SQLite column, type, required flag, PK/FK. | Generated from actual source schemas. |
| [System architecture](ARCHITECTURE.md) | Context/container, request sequences, pipeline diagram, component responsibilities, decisions. | Target architecture. |
| [Pipeline](PIPELINE.md) | Stage-by-stage input/output gates, lineage, forecast, footfall, refresh procedure. | Target pipeline; source audit executable. |
| [Workflows](WORKFLOWS.md) | Traveler, evaluator, forecast, and footfall journeys with error branches. | Proposed workflows. |
| [UI/UX](UI_UX.md) | Template adaptation, design system, six-screen behavior, responsive and accessibility rules. | Design specification. |
| [Traceability](TRACEABILITY.md) | Requirement-to-screen/component/data/evidence matrix and sign-off gaps. | Current audit. |
| [Phasewise prompts](phasewise_prompts.md) | Reusable prompts to regenerate or expand documents phase by phase. | Supplementary authoring aid. |
| [Visual reference map](uiux_design_reference.md) | Short template-to-CultureRoute mapping and tokens. | Companion to UI/UX specification. |

The [static landing-page prototype](../site/dist/index.html) illustrates the visual language. It does **not** implement the planner, DEV Lab, database pipeline, or six connected application screens.

## Verified source baseline

Run `python docs/audit_sources.py` from the workspace root. It reads both ZIP databases without changing them and verifies: 18 SmartTrip tables/32,627 rows; 14 WanderMatch tables/27,428 rows; eight identical shared tables/11,327 duplicate rows; 24 distinct tables/48,728 rows; 45 Indian cities, 675 attractions, 411 non-cancelled trips, 6,850 matched POI actions, 3,191 selected stops; cultural shares 211/675, 2,144/6,850, and 961/3,191; the 352/11/303 saved/planned join; 225 Indian events with 46 missing footfall values; and 57 complete weeks with MAE 3.42/3.88. The Jaipur route figures come from the specification and remain an implementation fixture.

## Phase 1 Implementation Status

Phase 1 established a runnable local application foundation (`app.py`), package modules (`cultureroute/study_data.py`, `cultureroute/domain.py`), and test suite (`tests/test_foundation.py`).

## Phase 2 Implementation Status: Real-Place Discovery Foundation

Phase 2 introduced the initial real-place discovery capability (`cultureroute/catalog.py`, `cultureroute/ingest.py`, `cultureroute/category_rules.py`, `cultureroute/boundary.py`) and test suite (`tests/test_phase2.py`).

## Phase 3 Implementation Status: Trustworthy Provenance, Rigorous Boundary, and Streaming Ingestion

Phase 3 audited and corrected Phase 2 catalog claims, established a streaming, reproducible real-source importer, and enforced dynamic coverage metadata:

1. **Phase 2 Hard-Coded Record & Field Audit**:
   - Every hard-coded attraction was audited against upstream primary records (Wikidata / OpenStreetMap APIs).
   - Quarantined broken/unsupported IDs: `OSM:node/34829104` (Badami) and `OSM:way/89402819` (Chand Baori) were HTTP 410 Gone; `OSM:way/152940211` and `OSM:way/28391054` had irrelevant tags (waterway stream, motorway link); and `WD:Q1143494` was DECO Cassette System, not Rani ki Vav (`WD:Q7293002`).
   - Quarantined records were replaced with verified Wikidata QIDs with primary source URLs, stable coordinates, and authoritative heritage tags (e.g. Badami Caves `WD:Q825236`, Durga Temple Aihole `WD:Q3517553`, Chand Baori `WD:Q2273412`, Rani ki Vav `WD:Q7293002`, Mahabodhi `WD:Q4513`, Nalanda `WD:Q216243`).
   - Field-level unknown audit: Removed all unsupported opening hours, entry fees, and accessibility claims. All unevidenced fields strictly set to `VerificationStatus.UNKNOWN`, `FeeStatus.UNKNOWN`, and `AccessibilityStatus.UNKNOWN`.
   - Distinct timestamps: Upstream source extract date, import date, and last checked date are maintained as distinct fields.

2. **Rigorous India Boundary Validation**:
   - Replaced rectangular bounding box with an official India territory MultiPolygon (`data/india_boundary.geojson`, 183 KB, derived from naturalearth / datameet public domain boundaries).
   - Implemented point-in-polygon ray casting with spatial bounding-box pre-filtering in `cultureroute/boundary.py`.
   - Rejects border/extraterritorial points (Lahore, Colombo, Kathmandu, deep Arabian Sea/Bay of Bengal) while accepting mainland and island locations (Delhi, Bengaluru, Badami, Kanyakumari, Port Blair).

3. **Reproducible Streaming Importer**:
   - `cultureroute/ingest.py` streams from UNECE UN/LOCODE India extract (`data/unlocode_raw.csv`, Public Domain, 1,341 entries) and verified UNESCO/ASI Wikidata monuments (`data/wikidata_unesco_india.json`, CC0).
   - Computes SHA256 input checksums, stages to temporary SQLite database, performs validation gates, and atomically publishes to `data/real_catalog.db`.
   - Imported 902 valid Indian settlements passing the MultiPolygon boundary check and 57 verified cultural attractions with full provenance.
   - Large raw files and generated `.db` are git-ignored.

4. **Dynamic Coverage Labeling & UI Transparency**:
   - Application dynamically queries catalog metadata table for `coverage_level` ("Partial Coverage"), `covered_regions`, `settlement_count` (902), `place_count` (57), and `snapshot_date`.
   - Out-of-coverage searches honestly report "Not Indexed" instead of implying zero attractions exist.
   - Proximity search is strictly labeled as straight-line distance, not travel time or road route.

5. **Pending for Phase 4**:
   - Directed travel times and road network distances.
   - Multi-day itinerary generation and optimization.
   - Ticketing and booking integration.
   - DEV Lab analytics, forecasting, and live venue verification.


