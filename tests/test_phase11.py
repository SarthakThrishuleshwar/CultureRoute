"""Tests for CultureRoute Phase 11: Complete Six-Screen Integration & Verification.

Verifies:
1. Six-Screen Navigation Architecture:
   - Screen 1: Project Overview & Evidence
   - Screen 2: Synthetic Research Study (45 Cities)
   - Screen 3: Real-Place Discovery (Nationwide / Partial Coverage)
   - Screen 4: Build a Cultural Day & Compare Plans
   - Screen 5: Insights & Predictions (Synthetic Research)
   - Screen 6: DEV Lab (Evaluator Workspace & Syllabus Units 1–5)
2. Deep-linking query parameter routing across all 6 views.
3. End-to-end real traveler journey (Discovery -> Provenance -> Directed Routing -> Pilot Planner).
4. End-to-end research evaluator journey (Study -> Jaipur Fixture -> Insights Forecast -> DEV Lab SQL Sandbox & Exports).
5. Strict namespace separation (Real place IDs vs Synthetic entity IDs).
"""

from __future__ import annotations

from pathlib import Path
import pytest
from datetime import date

from cultureroute.study_data import verify_and_audit_study, get_study_cities
from cultureroute.catalog import RealCatalogStore
from cultureroute.evidence import VenueEvidenceStore
from cultureroute.routing import RouteLegStore, TransportMode, compute_directed_leg
from cultureroute.planner import plan_synthetic_day, plan_real_place_day
from cultureroute.analytics import (
    compute_cultural_shares,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study
)
from cultureroute.dev_lab import (
    compute_methodology_comparison,
    compute_canonical_saved_planned_merge,
    ReadOnlySQLSandbox
)

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_DB = ROOT_DIR / "data" / "real_catalog.db"
APP_FILE = ROOT_DIR / "app.py"


def test_six_screens_presence_in_app_entrypoint():
    """Verify app.py explicitly defines and renders all six required application screens."""
    assert APP_FILE.exists()
    content = APP_FILE.read_text(encoding="utf-8")

    expected_screens = [
        "Project Overview & Evidence",
        "Synthetic Research Study (45 Cities)",
        "Real-Place Discovery (Nationwide / Partial Coverage)",
        "Build a Cultural Day & Compare Plans",
        "Insights & Predictions (Synthetic Research)",
        "DEV Lab (Evaluator Workspace & Syllabus Units 1–5)"
    ]

    for screen in expected_screens:
        assert screen in content, f"Screen '{screen}' must be declared in app.py navigation radio"

    # Verify query parameter routing support for each view
    assert 'view_param in ["overview"]' in content
    assert 'view_param in ["study", "45cities"]' in content
    assert 'view_param in ["discover", "explorer", "real"]' in content
    assert 'view_param in ["planner", "plan", "compare"]' in content
    assert 'view_param in ["insights", "predictions"]' in content
    assert 'view_param in ["lab", "devlab"]' in content


def test_real_traveler_end_to_end_journey(tmp_path, monkeypatch):
    """Discovery and a mocked provider yield a conditional plan without fabricated facts."""
    store = RealCatalogStore(CATALOG_DB)
    evidence_store = VenueEvidenceStore(ROOT_DIR / "data" / "venue_evidence.db")
    route_store = RouteLegStore(tmp_path / "routes.db")

    # 1. Discover places in Karnataka
    karnataka_places = store.get_places_by_state("Karnataka")
    assert len(karnataka_places) >= 3
    badami = next(p for p in karnataka_places if "Badami" in p.name)
    durga = next(p for p in karnataka_places if "Durga" in p.name)

    # 2. Check field evidence
    res_fee = evidence_store.resolve_field(badami.source_id, "entry_fee", visit_date=date(2026, 8, 15))
    assert res_fee.status.value == "UNKNOWN"

    class Reply:
        status_code = 200
        text = ""
        def __init__(self, coordinates): self.coordinates = coordinates
        def json(self):
            return {"code": "Ok", "routes": [{"distance": 35000, "duration": 2400,
                "geometry": {"coordinates": self.coordinates}}]}

    def provider(url, **_):
        coords = [[badami.longitude, badami.latitude],
                  [(badami.longitude + durga.longitude) / 2, (badami.latitude + durga.latitude) / 2],
                  [durga.longitude, durga.latitude]]
        if f"{durga.longitude:.6f},{durga.latitude:.6f}" in url.split(";")[0]:
            coords.reverse()
        return Reply(coords)

    monkeypatch.setenv("CULTUREROUTE_OSRM_DRIVING_URL", "https://configured.example.invalid")
    monkeypatch.setattr("cultureroute.routing.requests.get", provider)

    # 3. Directed route calculation
    leg = compute_directed_leg(
        origin_id=badami.source_id,
        origin_lat=badami.latitude,
        origin_lon=badami.longitude,
        destination_id=durga.source_id,
        destination_lat=durga.latitude,
        destination_lon=durga.longitude,
        mode=TransportMode.DRIVING,
        store=route_store,
        allow_network=True
    )
    assert leg.is_available is True
    assert len(leg.polyline_points) == 3
    assert leg.distance_km > 25.0
    assert leg.duration_minutes > 30.0

    # 4. Generate real day plan
    plans = plan_real_place_day(catalog_db=CATALOG_DB,
        evidence_db=ROOT_DIR / "data" / "venue_evidence.db", routes_db=tmp_path / "routes.db",
        selected_place_ids=[badami.source_id, durga.source_id],
        visit_date=date(2026, 11, 10), target_stops=2, user_duration_minutes=70)
    assert plans["fastest"] is not None
    assert plans["fastest"].total_stops_count == 2
    assert plans["fastest"].namespace == "REAL"
    assert plans["fastest"].result_level == "DISCOVERY-ONLY"
    assert plans["fastest"].has_unknown_costs
    assert plans["fastest"].total_cost_inr is None
    assert all(s.is_duration_assumption for s in plans["fastest"].stops)


def test_research_evaluator_end_to_end_journey():
    """Verify complete evaluator flow: audit -> Jaipur baseline -> forecast -> DEV lab merge & SQL."""
    # 1. Audit check
    audit = verify_and_audit_study()
    assert (audit.distinct_tables_count, audit.distinct_rows_count) == (24, 48728)

    # 2. Exact Jaipur specification reproduction
    j_plans = plan_synthetic_day(city_name="Jaipur")
    fastest = j_plans["fastest"]
    cultural = j_plans["most_cultural"]
    assert fastest.elapsed_minutes == 207
    assert float(fastest.total_cost_inr) == pytest.approx(585.46, abs=0.01)
    assert fastest.estimated_carbon_kg == pytest.approx(1.806, abs=0.005)
    assert cultural.elapsed_minutes == 227
    assert float(cultural.total_cost_inr) == pytest.approx(638.30, abs=0.01)
    assert cultural.estimated_carbon_kg == pytest.approx(2.840, abs=0.005)

    # 3. Cultural share metrics
    shares = compute_cultural_shares()
    assert shares["listings"].share_percent == 31.3
    assert shares["interactions"].share_percent == 31.3
    assert shares["planned_stops"].share_percent == 30.1

    # 4. Chronological forecast backtest
    fc = compute_weekly_forecast_backtest()
    assert fc.total_complete_weeks == 57
    assert fc.model1_mae == 3.42
    assert fc.model2_mae == 3.88

    # 5. DEV Lab Canonical Merge
    merge = compute_canonical_saved_planned_merge()
    assert (merge.both_count, merge.saved_only_count, merge.planned_only_count, merge.full_outer_count) == (352, 11, 303, 666)

    # 6. DEV Lab SQL Security
    sandbox = ReadOnlySQLSandbox()
    assert sandbox.execute_query("SELECT count(*) FROM cities").is_success is True
    assert sandbox.execute_query("DELETE FROM cities").is_success is False


def test_strict_namespace_isolation(tmp_path):
    """Verify complete isolation between Real (WD:, SETTLE:) and Synthetic (poi_, cty_, trp_) namespaces."""
    # 1. Synthetic ID rejected from real planner
    with pytest.raises(ValueError):
        plan_real_place_day(catalog_db=CATALOG_DB,
            evidence_db=ROOT_DIR / "data" / "venue_evidence.db",
            routes_db=tmp_path / "routes.db", selected_place_ids=["cty_c07454f1"],
            target_stops=1, allow_network=False)

    # 2. Real places store has zero synthetic IDs
    store = RealCatalogStore(CATALOG_DB)
    states = store.get_all_states()
    for st_name in states:
        places = store.get_places_by_state(st_name)
        for p in places:
            assert p.source_id.startswith(("WD:", "OSM:", "ASI:")), f"Invalid real ID: {p.source_id}"
            assert not p.source_id.startswith(("poi_", "cty_", "trp_", "ptm_"))
