# CultureRoute technical requirements document

**Status:** Proposed technical design · No connected application is present in this workspace  
**Inputs:** [`PRD.md`](PRD.md), [`DATABASE.md`](DATABASE.md), `CultureRoute_DEV_AAT_Project_Specification.pdf` pp. 2–8

## 1. System boundary and planned stack

The specified stack is Python, SQLite, and pandas for preparation and feature logic; Streamlit for the website; Plotly for interactive visuals; Seaborn for statistical plots. One preparation pipeline serves planner, analytics, forecast, and DEV Lab. The specification describes function calls from the website layer, not a public HTTP API. Hosting, authentication, scheduling, and persistent writes are not defined. [Spec p. 4]

| Component | Inputs | Output contract | Related requirement |
| --- | --- | --- | --- |
| Data loader/validator | Two SQLite/CSV packs | Validated canonical tables and audit report | NFR-01, NFR-02 |
| Preparation | Canonical tables and scope rules | Versioned read-only views/dataframes | FR-02, FR-08, FR-10 |
| Route planner | City, day, time/budget/stops/preferences | Ranked plans or structured infeasibility | FR-04–FR-07 |
| Analytics | Prepared views, filters, frequency | Metrics with numerator/denominator and chart-ready rows | FR-08, FR-09 |
| Forecast/estimation | Weekly series; events | Predictions, MAE, estimates, holdout errors | FR-09, FR-13 |
| Transformation engine | Allowed table/view, guided operation or SQL | Before/after result, command, counts, provenance | FR-10–FR-12 |
| Streamlit presentation | Function results | Six screen views and CSV/Parquet downloads | FR-01–FR-14 |

## 2. Data contracts

All keys are opaque strings. Money remains a decimal string at the storage/JSON boundary and becomes `Decimal` for arithmetic; display and export retain currency. Timestamps carry offsets; calendar dates do not. Use the selected city's IANA timezone for interpreting planner day and local opening hours. Latitude/longitude are WGS-84. Comma-separated language tags are parsed as BCP-47 codes. Preserve status and missingness rather than overwriting raw rows. [Pack `data/WORKING_WITH_THE_DATA.md`]

### Proposed internal planner request

```text
PlanRequest {
  city_id: string,
  local_date: YYYY-MM-DD,
  start_local_time: HH:MM,
  window_minutes: positive integer,
  max_total_cost: decimal string,
  currency: "INR" for the initial India planner,
  stop_count: positive integer within an agreed cap,
  preferred_categories: list of category codes,
  step_free_required: boolean,
  preferred_mode: walk | cab | either
}
```

`preferred_mode` and stop-count cap are design proposals. The UI must show any default. A request validator resolves city ID, checks local date/time, positive limits, currency compatibility, and available matrix coverage before search. [PRD FR-04]

### Proposed result

```text
PlanResult {
  input_snapshot, objective: fastest | most_cultural,
  status: feasible | conditional | infeasible,
  stops: [{poi_id, name, category, arrive_local, wait_minutes,
           visit_minutes, depart_local, entry_cost, currency,
           opening_status, accessibility}],
  legs: [{matrix_id, origin_poi_id, dest_poi_id, mode,
          minutes, cost, currency, carbon_kg}],
  totals: {elapsed_minutes, entry_cost, between_stop_fare,
           combined_cost, between_stop_carbon_kg, cultural_stop_count},
  warnings, source_version, calculation_notes
}
```

The `conditional` status is a proposal for unknown opening hours; the team must decide whether to display such plans or exclude them. The source supplies no starting-location or return-home leg, so those costs and times must not be invented.

## 3. Source preparation and validation

1. Open `PS-01.db` and `PS-11.db` read-only. Check schema, primary-key uniqueness, foreign keys, enum values, money formats, and `updated_at`/time conventions. Use the packs' `validate_conformance.py` as an additional check, while retaining a project-specific reconciliation test.
2. Compare the eight shared tables by primary key and row content. Retain SmartTrip's copy only after equality is established. Current source audit confirms identical rows: 11,327 shared rows across eight tables.
3. Apply the India scope via `cities.country_code = 'IN'`; do not infer geography from names. This yields 45 cities, 675 attractions, and 225 events. A trip enters the 411-trip study population when its `destination_city_id` points to an Indian city and `status <> 'cancelled'`.
4. Build separate interaction and selected-stop aggregates before joining either to the attraction catalog. Retain `interaction_id`, `item_id`, `poi_id`, `city_id`, and source table identifiers for drill-down.
5. Reconcile the checkpoints in [`audit_sources.py`](audit_sources.py). Abort/flag a refreshed snapshot if a checkpoint changes until the difference is explained. See [`DATABASE.md`](DATABASE.md) for exact SQL. [Spec pp. 2, 4]

## 4. Route planning algorithm contract

**Eligible candidates:** active India-scope attractions in the selected city, restricted to the 10 per city that occur as matrix origins/destinations for planning. Discovery must still show all 15 city attractions. Apply requested category and step-free conditions. The attraction's `accessibility` applies to the stop only; transfer accessibility is unknown. [Spec pp. 4–5]

**Feasibility:** candidate sequences contain distinct POI IDs. For each consecutive pair, require a recorded *directed* `poi_travel_matrix` row for the chosen mode. Add leg travel time, waiting until `opens_at` if known, and `typical_duration_minutes`; reject known closure (`closed_days` or `closes_at`), window overrun, or cost overrun. Entry fees and leg fares are summed with `Decimal`; carbon is summed from leg `carbon_kg` and labeled estimated between-stop carbon. Of 675 Indian attractions, 131 have only one opening-hour endpoint and seven have neither. Partial hours are uncertain; paired nulls require an explicit always-open policy aligned with the pack dictionary. Warn or exclude according to the team's conditional-plan decision. The specification does not define dwell time beyond `typical_duration_minutes`, travel to first stop, or return travel, so display that boundary. [Spec p. 4; source audit]

**Ranking proposal:** among feasible sequences under one input snapshot, choose (a) minimum elapsed minutes and (b) maximum number of `heritage`, `museum`, `religious`, or `food` stops. Use deterministic secondary ordering (for example cost, then POI ID sequence) after the team approves it. If objectives select the same sequence, return one route with both objective labels rather than fabricating a difference. Bound enumeration by an agreed stop cap and search time; document whether an approximate search was used.

**Fixture:** reproduce the Jaipur Saturday, 09:00, six-hour, INR 1,000, three-stop comparison from the specification. The numbers in the PRD are expected baselines; route code and source-leg trace must verify them. [Spec p. 5]

## 5. Analytics, forecasts, and estimation

### Descriptive analysis

Return each metric as `{value, unit, numerator, denominator, filters, grain, source_ids, cutoff, missingness_policy}`. The cultural categories are `heritage`, `museum`, `religious`, and `food`. For charts, pair Plotly/Seaborn output with a table and the calculation text. Weekly/monthly resampling uses offset-aware timestamps and labels incomplete periods. Correlation is described as association. [Spec pp. 2, 6–7]

### Weekly engagement forecast

Use the matched Indian cultural-POI interaction records. Parse `occurred_at` with its offset, group by local Monday–Sunday week, and exclude the partial final week. The current snapshot has 57 complete weeks, from 14 July 2025 through 16 August 2026, followed by a partial week beginning 17 August. For each of the last 12 complete target weeks, predict from *earlier* weeks only: previous-week count and trailing four-week arithmetic mean. Compute `MAE = mean(abs(actual - prediction))`. The source audit reproduces 3.42 and 3.88 after two-decimal rounding. Display actuals, predictions, target dates, source cutoff, and evaluation period. [Spec p. 8]

### Missing event footfall

The India subset has 225 events and 46 missing `expected_footfall`. Preserve nulls in source. Compare observed-only summary, median replacement, and a fitted-distribution estimate. The distribution family and maximum-likelihood fitting procedure require a documented decision after inspecting known values and diagnostics; do not claim a model is validated yet. Hide a reproducible sample of known values, fit on the remaining known records only, and report holdout error by method. Estimated cells must be marked in text and color. [Spec p. 6]

## 6. DEV Lab execution contract

Guided Mode builds explicit pandas operations for filter, derive, group, pivot, and merge. A merge must expose left/right key sets and match statuses. The canonical demo compares distinct saved POI IDs to distinct selected planned POI IDs: left 363, right 655, inner 352, saved-only 11, planned-only 303, full outer 666. Joining unaggregated events and stops would produce multiplied rows and is invalid for this exercise. [Spec p. 5]

SQL Mode is a **proposed** read-only execution surface. Restrict queries to allowlisted views; use SQLite read-only connections plus an authorizer that denies `INSERT`, `UPDATE`, `DELETE`, DDL, `ATTACH`, writes through `PRAGMA`, and extension loading. Enforce a progress/time limit and result-row cap; show truncation rather than silently presenting it as complete. Parameterize guided filters and avoid string-built SQL from UI values. Render the executed command, source view, before/after counts, matching counts, and errors. [Spec p. 4]

## 7. Presentation and export

Streamlit reruns must recalculate dependent outputs when inputs change and invalidate stale plan/forecast states. Cache immutable prepared views by source version and filters if performance warrants it; caching strategy is an implementation decision. Planner maps and timetables share stop IDs and color labels. Use Chart/Table/How calculated tabs for analytical graphics. Distinguish observed, missing, and estimated with both text and color. CSV/Parquet exports carry visible filters and provenance in a companion metadata block/file if the file format cannot embed them. [Spec pp. 3–4]

## 8. Verification matrix

| Check | Expected evidence |
| --- | --- |
| Source audit | 18/32,627 + 14/27,428; eight identical shared tables/11,327 rows; 24/48,728 distinct. |
| Study filters | 45 cities, 675 attractions, 411 trips, 6,850 interactions, 3,191 selected stops. |
| Metrics | 211/675, 2,144/6,850, 961/3,191; no multiplied joins. |
| Route | Jaipur fixture plus source POI/matrix IDs, exact Decimal totals, no violated known constraints. |
| DEV Lab | Join sets 363/655, inner 352, outer 666; mutation attempts denied; caps reported. |
| Forecast | 57 complete weeks; 12 chronological predictions; MAE 3.42 and 3.88. |
| Footfall | 225 India events, 46 nulls; source nulls intact; held-out error disclosed. |
| UI and export | Keyboard flow, visible labels/states, chart/table/calculation parity, exported values equal displayed values. |

## 9. Open technical decisions

Decide route stop cap/search method, unknown-hour policy, exact preference scoring, currency policy, query time/row limits, prepared-view materialization, source refresh schedule, deployment/access model, and chosen fitted distribution for missing-footfall estimates. Record each decision with rationale before claiming implementation completeness.
