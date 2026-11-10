# CultureRoute data and prediction pipeline

**Status:** Reproducible synthetic source audit and [implemented six-zone real catalog/evidence/route pipeline](PHASE8_REPAIR.md). No production scheduler or deployment is present.
**Companion diagrams:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
**Source contracts:** [`DATABASE.md`](DATABASE.md), [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)

## 1. Purpose and boundaries

The same prepared data supports city discovery, route planning, descriptive analysis, weekly engagement forecasting, missing-footfall exercises, and DEV Lab transformations. The two supplied SQLite files are the authoritative local snapshots. Their CSV exports are alternate representations, not additional records. The optional MediaWiki/API and heritage-HTML exercises described in the project specification are external reference-data exercises; they must be stored and labeled separately from the synthetic study and must not silently alter its counts. [Spec pp. 4, 7]

## 2. Stage contract

| Stage | Input and grain | Transformation | Output and gate |
| --- | --- | --- | --- |
| P0 Snapshot | `PS-01.db`, `PS-11.db` plus manifest hashes | Open read-only; record path, hash, schema/version, run time. | Immutable run manifest; fail on missing/corrupt input. |
| P1 Validate | 18 + 14 raw tables | Check table/column presence, keys/FKs, enum and money formats, timestamp offsets. | Audit report; 32,627 + 27,428 raw rows. |
| P2 Canonicalize | Eight overlapping tables | Compare full PK sets and row content; retain one identical copy. | 24 distinct canonical tables / 48,728 rows; stop on disagreement. |
| P3 Scope | Canonical `cities`, POIs, trips, events | `country_code='IN'`; trip destination India and `status<>'cancelled'`; profile opening-hour completeness. | 45 cities, 675 POIs, 411 trips, 225 events; 131 POIs with one missing time endpoint. |
| P4 Match | `user_interactions`, India POIs | `entity_type='poi'` and `entity_id=poi_id`; retain one action per `interaction_id`. | 6,850 interaction rows; 2,144 cultural actions. |
| P5 Select | Itinerary items + itinerary/trip + India POIs | Active itinerary, confirmed POI item, non-cancelled India destination; retain `item_id`. | 3,191 stop rows; 961 cultural stops. |
| P6 Aggregate | P3–P5 | Group interactions and stops **separately** by POI before left joining to catalog; build city/trip summaries. | 675-row attraction summary with no fan-out. |
| P7 Route/time | Travel matrix; P4 timestamps | Keep recorded directed walk/cab legs; build Monday-start cultural weekly series and mark partial week. | 10 matrix-covered POIs per India city; 57 complete weeks + one partial. |
| P8 Features | P3–P7 | Planner, chart metrics, forecast baselines, missing-footfall estimates, guided transformations. | Function outputs with method, filters, source IDs, cutoff. |
| P9 Present/export | Feature outputs | Render map/timetable/chart/table/How calculated and CSV/Parquet. | Visible and exported values reconcile; errors are explicit. |

Every stage should be idempotent for the same source hashes and code version. Persisting intermediate DataFrames/views is an implementation choice; their **grain and checks** are not optional. `audit_sources.py` currently verifies the source and analytical checkpoints; it does not execute route generation or render the website.

## 3. Lineage by feature

| User-visible output | Prepared inputs | Source columns needed | Method/provenance shown |
| --- | --- | --- | --- |
| City map and catalog | `india_attractions`, `india_cities` | `poi_id`, `city_id`, `lat`, `lng`, `poi_category`, `entry_cost`, `accessibility` | Source POI ID, city filter, 15 catalog vs 10 route-covered. |
| Cultural share chart | Catalog, matched actions, selected stops | `poi_category`, `interaction_id`, `item_id`, statuses | Three independent numerators/denominators and scope filters. |
| Fastest / most-cultural route | Catalog + `route_options` | Hours, duration, entry cost, directed leg minutes/cost/carbon | Input snapshot, POI/matrix IDs, arithmetic, omissions/warnings. |
| Weekly forecast | P4 cultural actions | `occurred_at`, `entity_id`, `poi_category` | Week start/end, last training week, actual, prediction, MAE. |
| Event-footfall estimates | `india_events` | `event_id`, `expected_footfall`, category/city | Observed/missing/estimated status, fit method and holdout error. |
| DEV Lab join | Distinct saved IDs and planned IDs | `interaction_type`, `entity_id`, `item_id`, `poi_id` | Set grain, match status, 352/11/303 breakdown. |

## 4. Forecast subpipeline

1. Filter P4 actions to attractions with `poi_category` in `heritage`, `museum`, `religious`, `food`.
2. Parse `occurred_at` as an offset-aware timestamp. Group by local Monday–Sunday week and retain zero-count complete weeks if a refreshed source has any.
3. Exclude an incomplete final week. The supplied snapshot has 57 complete weeks (14 July 2025–16 August 2026) and a partial week beginning 17 August 2026.
4. For each of the last 12 complete target weeks, compute a previous-week prediction and a mean of the immediately prior four complete weeks. Never use target/future counts to predict the target.
5. Compute mean absolute error over those 12 targets. The supplied data reproduce 3.42 for previous-week and 3.88 for trailing-four-week after rounding to two decimals.
6. Output target week, cutoff, actual, both predictions, absolute errors, model names, and source snapshot. A future forecast must state the last complete source week and the next target week.

The forecast is of synthetic platform actions, not travel demand or visits. [Spec p. 8]

## 5. Missing-footfall subpipeline

The India event subset has 225 records and 46 null `expected_footfall` values. Preserve raw nulls in P3. Produce derived comparison outputs for observed-only, median-imputed, and fitted-distribution methods. Before selecting a distribution, inspect known values with histogram/ECDF and Q-Q diagnostic; record why the distribution is plausible. For evaluation, mask a deterministic subset of known values, fit without seeing their values, then report holdout error. Track `event_id`, original-missing flag, estimate, method, model parameters, training count, and holdout membership. A source missing value must never be exported as if observed. [Spec pp. 6–7]

## 6. Run/refresh procedure

1. Pin input ZIP/database files and record SHA-256 hashes. Do not edit source packs.
2. Run `python docs/audit_sources.py`; require zero assertion failures. For a changed source, investigate differences and update documented baselines intentionally.
3. Run the packs' own conformance checks if they are available from an extracted copy. These checks supplement, not replace, the project-specific scope audit.
4. Build prepared views in dependency order P2→P7; record row counts and key uniqueness after each stage.
5. Re-run calculation fixtures: three cultural shares, saved/planned join, complete-week count and MAEs. The implemented synthetic planner reproduces the Jaipur route fixture with source IDs and exact decimal totals.
6. Version the resulting prepared snapshot and expose its cutoff and method version in the UI/export metadata.
7. On any failure, keep the prior verified snapshot available only if the UI clearly identifies it as stale; otherwise stop serving derived results. The staleness policy is an operational decision.

No scheduled refresh is required by the supplied specification. If one is later introduced, its cadence, ownership, rollback, and access controls must be recorded in [`ARCHITECTURE.md`](ARCHITECTURE.md).
