# CultureRoute product requirements document

**Status:** Product specification; for implemented scope and limits see [Phase 8 repair](PHASE8_REPAIR.md). Real-place planning is conditional, and AI/ML is on standby.
**Version:** 1.0 · 8 November 2026
**Primary reference:** `CultureRoute_DEV_AAT_Project_Specification.pdf`, pages 1–8
**Data references:** `SmartTrip (1).zip` and `WanderMatch.zip`, SQLite databases and `01_YOUR_DATA_MODEL.md` files

## 1. Product summary

CultureRoute is a proposed website with two connected experiences. A traveler discovers cultural attractions and compares feasible day itineraries under a budget and time limit. An evaluator uses the DEV Lab to inspect the data, run transformations, and trace charts, estimates, and predictions to source rows. The research question is: **How does the representation of heritage sites, museums, religious sites, and food experiences differ across attraction listings, online interactions, and planned stops?** [Spec pp. 1, 3]

The study is based on **synthetic** data. Its India scope has 45 cities, 675 listed attractions, and 411 non-cancelled destination trips. The two packs contain 24 distinct tables and 48,728 rows after eight identical shared tables are retained once. These counts were reproduced with [`audit_sources.py`](audit_sources.py). The site can illustrate SDG 8.9's local-culture component; it cannot measure real visits, employment, spending, or sustainable-tourism impact. [Spec pp. 1–2]

## 2. Users and jobs

| Role | Job | Evidence of success |
| --- | --- | --- |
| Traveler | Find interesting stops and make a feasible cultural day. | A route has distinct stops, a readable timetable, recorded travel legs, and a total within the chosen budget and window. |
| Evaluator or student | Inspect how each result was produced. | Can open source/prepared rows, see a command and before/after output, inspect calculation metadata, and export the result. |
| Presenter | Demonstrate the research question end to end. | Can reproduce the Jaipur comparison, a join/pivot, and the weekly forecast without changing datasets. |

No interviews or usability testing were supplied, so these are task roles inferred from the project specification, not validated personas.

## 3. Goals, boundaries, and scope

### Goals

1. Make cultural categories discoverable across the 45 Indian cities.
2. Produce and compare two feasible cultural-day plans from identical inputs.
3. Make every displayed analytical value inspectable through its grain, numerator, denominator, filters, time scope, and source rows.
4. Support the DEV syllabus through exploration, transformation, descriptive statistics, visualization, and time-series exercises.
5. Communicate uncertainty and missingness explicitly. [Spec pp. 2–8]

### Out of scope for the specified build

Live booking, real-time travel or price feeds, proof of physical visits, measured jobs or spending, production personalization, and route legs absent from the supplied matrix are not supported by the specification. Flights, hotels, and fares may be explored as source tables but are not part of the cultural day-plan cost. A public API, accounts, deployment platform, and persistent collaboration are not specified. [Spec pp. 1, 2, 4]

### Delivery boundary

The screens below originate in the proposed specification. The separate [`site/dist/index.html`](../site/dist/index.html) remains a static landing-page concept. The connected local Streamlit application now runs from `app.py`; its actual scope and remaining limits are recorded in [Phase 8 repair](PHASE8_REPAIR.md).

## 4. Information architecture

| Screen | Primary task | Main output |
| --- | --- | --- |
| Project Overview | Understand question, SDG limit, study scope; start the Jaipur demo. | Project brief and verified counts. |
| Discover a City | Pick city; filter category, price, and step-free access; browse guides. | Map, attraction table, cultural share, guide languages/specialties. |
| Build a Cultural Day | Enter date, start time, budget, available hours, stop count, preferences. | Feasible schedule, directed legs, itemized cost. |
| Compare Plans | Review fastest versus most-cultural under unchanged inputs; rerun after edits. | Paired maps and timetables, costs, carbon, duration. |
| Insights and Predictions | Compare places/categories and inspect weekly/monthly series and forecasts. | Chart, table, “How calculated”, prediction/error. |
| DEV Lab | Browse raw/prepared data and run guided or read-only SQL transformations. | Before/after rows, command, counts, chart, export. |

Keep navigation visible. Map and timetable remain paired. Analysis views expose Chart, Table, and How calculated tabs. [Spec p. 3]

## 5. User stories and functional requirements

Priority **P0** is required for a credible end-to-end demo; **P1** completes the stated syllabus and analysis scope.

| ID | Priority | Requirement and acceptance criterion |
| --- | --- | --- |
| FR-01 | P0 | Overview shows the research question, synthetic-data notice, SDG 8.9 caveat, 45 cities, 675 attractions, 411 trips, and a path to both experiences. Counts have a source note. |
| FR-02 | P0 | Discover shows 15 attractions per selected study city, with category, entry price/currency, accessibility, map location, and filter reset. Planner coverage distinguishes the 10 matrix-covered attractions from the full catalog. |
| FR-03 | P1 | Discover lists guide languages and specialties from `tour_guides`; language labels are derived from BCP-47 tags. A missing guide set has an explicit empty state. |
| FR-04 | P0 | Planner accepts city, day, start time, budget, hours, stop count, and preferences; rejects invalid values before search and echoes normalized inputs with results. |
| FR-05 | P0 | Planner uses only recorded directed walking/cab legs; adds visit, waiting, and between-stop travel time; entry fees and leg fares use decimal arithmetic. It flags unknown hours and matrix gaps. No returned plan violates known budget, opening-hour, or duration constraints. |
| FR-06 | P0 | Compare presents **Fastest plan** and **Most cultural stops** for the same input snapshot, with distinct stop names, paired maps/timetables, elapsed time, entry plus between-stop cost, and estimated between-stop carbon. If both objectives select one route, say so. |
| FR-07 | P0 | Changing a constraint invalidates previous results and reruns both objectives. If no feasible route exists, show the blocking conditions and a way to adjust inputs. |
| FR-08 | P0 | Insights shows listings, matched interactions, and selected planned stops with separate denominators. Every chart has table and calculation views, units, sample size, filters, date scope, and source identifiers. |
| FR-09 | P1 | Insights supports city/category comparisons, weekly/monthly time views, partial-period labeling, forecast actuals, forecast dates, source cutoff, and MAE. |
| FR-10 | P0 | DEV Lab can inspect a raw table or prepared view: field names/types, grain, row count, missing values, preview, and source. |
| FR-11 | P0 | DEV Lab Guided Mode performs filter, derive, Group By, pivot, and merge; shows the command/parameters, before/after counts, matched/unmatched keys, and an exportable table. |
| FR-12 | P1 | DEV Lab SQL Mode accepts bounded **read-only** queries against allowed views, blocks mutations and unsupported statements, and reports time/output limits and errors without modifying source files. |
| FR-13 | P1 | Missing-footfall exercise compares observed-only, median replacement, and fitted-distribution estimates while preserving source nulls; estimates and holdout errors are labeled. |
| FR-14 | P1 | Supported result tables export as CSV or Parquet with column names, filters, cutoff, and method metadata where the format permits. A failed export yields an explicit error. |
| FR-15 | P0 | Nationwide Real-Place Day Planner generates ordered multi-stop day plans using exclusively real catalog venues (`WD:...`, `OSM:...`) and genuine directed routing. Synthetic IDs are strictly rejected. |
| FR-16 | P0 | Genuine Directed Routing engine computes and caches asymmetric road and pedestrian legs with verified timestamps and source attribution. Fabricated multipliers or coordinate biases are strictly prohibited. Walking > 25 km is rejected as `UNREACHABLE_BY_MODE`. |

### Example acceptance narratives

- **Traveler (Synthetic):** On a Saturday in Jaipur, starting 09:00 with six hours, INR 1,000, and three distinct stops, the implementation reproduces the specification's two route baselines: 3h27 / INR 585.46 / 1 cultural stop / 1.806 kg, and 3h47 / INR 638.30 / 2 cultural stops / 2.840 kg.
- **Traveler (Real Places):** In Badami and Aihole, planning a driving itinerary visits Badami Cave Temples (`WD:Q825236`), Pattadakal Group of Monuments (`WD:Q817250`), and Durga Temple Aihole (`WD:Q3517553`) over 70.15 km of genuine directed road network with turn-by-turn geometry. During July monsoon closure, Aihole is excluded deterministically.
- **Evaluator:** A distinct-POI saved-versus-planned join returns 363 saved IDs, 655 planned IDs, 352 matches, 11 saved only, 303 planned only, and 666 full-outer IDs. This is reproduced by the source audit. [Spec p. 5]
- **Forecast:** The last-week and trailing-four-week baselines over the last 12 of 57 complete weeks show MAE 3.42 and 3.88 interactions respectively. This is reproduced by the source audit. [Spec p. 8]

## 6. Nonfunctional requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| NFR-01 | Provenance | Every metric and export identifies its source population, filters, grain, and cutoff. |
| NFR-02 | Data integrity | Source packs are opened read-only; shared copies are compared before deduplication; keys and published counts reconcile. |
| NFR-03 | Accessibility | All controls are keyboard usable, have text labels and visible focus, and do not rely on color alone for observed/missing/estimated states. |
| NFR-04 | Responsiveness | All six screens retain readable tables and paired map/timetable context at desktop and narrow widths; exact breakpoints are a UI proposal. |
| NFR-05 | Reproducibility | Repeated calculation from the same source version and filters returns the same values; forecast training never sees the target week. |
| NFR-06 | Safety of evaluator tools | SQL is restricted to allowed read-only operations, bounded in time and output rows, and cannot alter source databases. |
| NFR-07 | Performance | Set and measure realistic route/query/render budgets after implementation; the source does not provide numeric service-level targets. |
| NFR-08 | Truthful Evidence | Unknown venue fields (hours, admission fees, operating status, accessibility) are never defaulted to ₹0 or fabricated. Result levels are classified as VERIFIED, PROVISIONAL, or DISCOVERY-ONLY. |

## 7. Measurement definitions

The metric dictionary and exact filters are in [`DATABASE.md`](DATABASE.md). The three headline cultural shares are **211/675 = 31.3%** of listings, **2,144/6,850 = 31.3%** of matched interactions, and **961/3,191 = 30.1%** of selected stops. A direct join of interaction rows and itinerary rows would multiply counts and is prohibited. [Spec p. 2; source audit]

Product success should be evaluated with task completion rather than invented adoption numbers: the Jaipur fixture is reproducible, each chart exposes its calculation, the join output reconciles, the forecast is leak-free, exports match the visible table, and empty/infeasible states are understandable. Actual user satisfaction requires future user testing.

## 8. Risks and decisions needed

| Decision | Why it matters | Proposed direction |
| --- | --- | --- |
| Planner starting/ending location | Matrix records POI-to-POI legs only. | State that elapsed time starts at the first stop and excludes travel to/from an origin unless new data are supplied. |
| Maximum stop count/search budget | An unrestricted route search can be expensive. | Decide a visible cap and deterministic search strategy before implementation. |
| Unknown opening hours | 131 India attractions have only one time endpoint; seven have neither. An incomplete interval cannot prove open status. | Return a clearly flagged conditional plan or exclude it; decide how paired nulls map to “always open” in the pack dictionary. |
| Currency support | Costs require consistent comparison. | Limit the first planner to INR study-city data or add explicit conversion data; never silently combine currencies. |
| Guide availability | No live availability feed is specified. | Treat profiles as informational, not bookable. |
| UI language | Data include language tags but translations are not supplied. | Select one Indian language for reviewed interface strings if multilingual UI is built. |
| Deployment and access | No hosting or account model is specified. | Document the team's chosen environment before technical sign-off. |

## 9. Source precedence

The CultureRoute specification defines this project's scope. The ZIP data dictionaries and SQLite files define the supplied schema and values. The template video and user-provided images guide visual presentation only. Hackathon process dates, XR directives, and unrelated product aspirations inside the ZIP READMEs are not CultureRoute requirements.
