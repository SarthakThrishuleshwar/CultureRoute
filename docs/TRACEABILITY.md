# CultureRoute requirements and evidence traceability

**Status:** Documentation audit. “Source verified” means the supplied databases reproduce a claim; it does not mean a connected website exists.

| Research/product need | PRD requirement | Screen/workflow | Technical component | Source/view | Current evidence |
| --- | --- | --- | --- | --- | --- |
| Explain study and SDG limit | FR-01 | Overview | Streamlit presentation | Source manifest, `india_cities`, `study_trips` | Counts source verified; UI concept static. |
| Find cultural POIs | FR-02 | Discover / T1 | Preparation + map/table | `india_attractions`, `route_options` | 45 cities, 675 POIs, 10/15 coverage source verified. |
| Browse guides | FR-03 | Discover / T1 | Guide filter | `tour_guides`, `languages` | Schema available; app unbuilt. |
| Enter route constraints | FR-04 | Build / T2 | Request validation | User input + city reference | Design specified; app unbuilt. |
| Generate feasible route | FR-05 | Build / T3 | Planner | Attractions + matrix | Source rows available; route fixture pending implementation. |
| Compare objectives | FR-06 | Compare / T4 | Planner ranking | Same input snapshot | Spec baseline only; app unbuilt. |
| Revise / infeasible state | FR-07 | Build/Compare / T6 | Planner + UI state | Input snapshot | Design specified; app unbuilt. |
| Compare three populations | FR-08 | Insights / E4 | Analytics | Catalog, actions, stops | 211/675, 2,144/6,850, 961/3,191 source verified. |
| Weekly forecast | FR-09 | Insights / forecast flow | Forecast | `weekly_cultural_engagement` | 57 weeks, 3.42/3.88 source verified. |
| Inspect records | FR-10 | DEV Lab / E1 | Data browser | Raw and prepared views | Schema dictionary complete; app unbuilt. |
| Guided transforms and merge | FR-11 | DEV Lab / E2–E4 | Transformation engine | Distinct saved/planned POIs | 352/11/303 and outer 666 source verified. |
| Read-only SQL | FR-12 | DEV Lab / E2–E3 | SQL guard/limits | Allowed views | Design specified; app unbuilt. |
| Missing-footfall estimates | FR-13 | Insights / footfall flow | Estimation | `india_events` | 225 events/46 null source verified; fit pending. |
| Export | FR-14 | Traveler/DEV Lab / T6/E5 | Export layer | Visible result + metadata | Design specified; app unbuilt. |

## Documentation consistency checks

| Claim | Expected | Checked by |
| --- | ---: | --- |
| Distinct tables and rows | 24; 48,728 | `audit_sources.py` shared-table comparison |
| Indian cities / attractions / trips | 45 / 675 / 411 | `audit_sources.py` scope predicates |
| Matched actions / selected stops | 6,850 / 3,191 | `audit_sources.py` join and status predicates |
| Cultural shares | 31.3% / 31.3% / 30.1% | Exact numerators in `DATABASE.md` |
| Saved/planned join | 352 both, 11 saved only, 303 planned only | Distinct ID set comparison |
| Weekly baselines | 57 complete weeks; MAE 3.42 / 3.88 | Past-only arithmetic audit |
| Jaipur route | 3h27/₹585.46 and 3h47/₹638.30 | Specification fixture; **not yet runtime verified** |

## Remaining sign-off work

The team must decide the route stop cap/search algorithm, unknown-hours treatment, currency policy, DEV Lab SQL limits, prepared-view storage, deployment/access model, interface language, and missing-footfall distribution. A connected application must then be tested against the route, transform, chart, export, error-state, accessibility, and responsive requirements in the other documents. Until then, the design documents are implementation guidance and the landing page remains a visual prototype.
