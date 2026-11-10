# Phase 8 repair: implementation and limits

**Local status, 10 November 2026.** This page supersedes older Phase 8 claims elsewhere in the documentation. The application is a local Streamlit build. The synthetic 45-city research study remains separate from the six-zone real-place extract. AI/ML files are on standby and were not run for this repair. No deployment was made.

## What runs

- `app.py` has study, discovery, and conditional real-planner views. The real catalog contains 295,017 settlement records and 62,203 cultural place records from six completed zones; “Complete Extract” describes this imported extract, not complete venue facts or itinerary coverage across India.
- `cultureroute/real_planner.py` accepts selected real source IDs or a settlement, date, start/window, 1–5 stops, visitor group, traveler-entered dwell, step-free requirement, admission budget, and optional return to the start. A settlement searches indexed cultural places within a configurable radius (15 km default), capped at six candidates. Selected IDs retain their source namespaces. Synthetic IDs are rejected.
- The first selected place is the journey start when no settlement is supplied. No journey from the traveler's actual origin is implied. A requested round trip returns to that first place or the chosen settlement.
- The real planner schedules directed routed legs, known opening windows and closures, waits, and dwell. A missing route stops that candidate order. An unavailable backend produces an explicit failure. Unknown hours or status make the schedule **DISCOVERY-ONLY**. Known hours/status with unknown costs, accessibility, or traveler dwell make it **PROVISIONAL**. **VERIFIED** requires current applicable evidence for all required venue constraints and genuine directed legs throughout the represented journey; the current pilot does not establish such a result.
- Admission and fares are nullable. Known admission subtotal is shown separately; unknown total cost never satisfies a hard budget. The traveler dwell input is labeled as an assumption. No real-plan carbon or cab fare estimate is asserted.
- The synthetic planner continues to use the separate supplied study matrices and Jaipur fixture. Its costs and carbon values are study examples, not real-place prices.

## Stores, provenance, and correction

| Store | Purpose |
| --- | --- |
| `data/real_catalog.db` | Real settlements/places and extract metadata; no active evidence or route tables. |
| `data/venue_evidence.db` | Append-only field records and `evidence_retractions`; active resolution excludes retracted claims while history remains inspectable. |
| `data/real_routes.db` | Validated directed OSRM-response cache, keyed by origin, destination, and mode. |
| `data/phase8_repair_backup_20261110/` | Backups of all three generated databases before repair. |
| `data/phase8_quarantine/real_routes_unverified_20261110.db` | 64 old cache rows excluded from active routing. |
| `data/phase8_quarantine/real_routes_validated_before_timing_20261110.db` | Six validated local demonstration legs retained as history while the cache was refreshed to add separate request/response timestamps. |

The quarantined set contains 58 older OSRM-labeled rows lacking the new response provenance fields and six manually inserted 2-point pilot legs (Badami, Aihole, Pattadakal pairs, including a walking row). Source labels alone did not prove the geometry or routing profile. The active cache starts clean. New cached legs require a provider URL, separate request and response timestamps, direction, request endpoints, distance, duration, and a returned polyline with at least three points. The response is checked for endpoint proximity and plausible distance; stale, mismatched, legacy, and two-point rows are refused. A→B and B→A are separate entries. The routing data version is recorded when the operator supplies `CULTUREROUTE_ROUTING_DATA_VERSION`, otherwise explicitly `unreported`.

The Phase 7/8 pilot's 35 prior field claims were retracted from active resolution, with reasons in `evidence_retractions`. Generic ASI circle pages did not directly support the asserted fees, access, operating windows, or the Aihole July closure. Pattadakal step-free access and the Aihole closure are now unknown. Four new Taj Mahal records cite the directly inspected [official ticketing page](https://www.tajmahal.gov.in/ticketing.aspx): Indian adult, foreign adult and child fee tiers, and Friday closure. The closure does **not** verify exact opening hours; the opening-hours field is provisional until times are sourced. Other pilot fields remain unknown. Catalog source extract date, catalog import date, and evidence checked date remain distinct.

## Routing setup and local commands

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 docs/audit_sources.py
py -3.11 -m pytest tests/test_foundation.py tests/test_phase2.py tests/test_phase3.py tests/test_phase4.py tests/test_phase4_osm.py tests/test_phase5.py tests/test_phase5_zone.py tests/test_phase6.py tests/test_phase7.py tests/test_phase8.py tests/test_phase9.py tests/test_phase10.py tests/test_phase11.py tests/test_planner_phase2.py -q
py -3.11 -m streamlit run app.py --server.address localhost --server.port 8502
```

Without a routing provider, real planning reports unavailable. To test with a provider intentionally chosen by the operator, set `CULTUREROUTE_OSRM_DRIVING_URL` in the **same terminal** before starting Streamlit. The public OSRM demonstration server was used only for a limited local validation, never as a default or deployment dependency. Walking remains disabled unless a separate pedestrian graph is configured through `CULTUREROUTE_OSRM_WALKING_URL` and its profile has been independently verified (`CULTUREROUTE_WALKING_PROFILE_VERIFIED=1`). A URL containing `/foot` alone does not verify a pedestrian graph. API timeout, rate limit, no-route, and invalid geometry do not create fallback legs.

The local validation obtained a Badami Cave Temples (`WD:Q825236`) → Durga Temple Aihole (`WD:Q3517553`) driving response from the explicitly configured OSRM demonstration server: 34.65 km and 389 returned geometry points. A real two-stop plan is **DISCOVERY-ONLY** because hours, admission for those venues, and operating details lack current direct evidence. Agra (north) and Sivasagar (north-east) two-place examples also yielded routed **DISCOVERY-ONLY** plans under that explicit provider configuration; this does not verify venue availability or nationwide itinerary coverage. A step-free requirement on the Badami–Aihole pair returns a specific failure because neither venue has verified step-free evidence. Provider selection, production routing infrastructure, pedestrian graph, wider venue evidence, and deployment remain open decisions.
