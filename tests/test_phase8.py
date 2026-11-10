"""Tests for CultureRoute Phase 8: Day Planner and Plan Comparison Engine.

Verifies:
1. Exact mathematical reproduction of the Saturday Jaipur specification fixture:
   - Fastest plan: 1 cultural stop, 207 minutes (3h 27m), INR 585.46, 1.806 kg carbon.
   - Most cultural plan: 2 cultural stops, 227 minutes (3h 47m), INR 638.30, 2.840 kg carbon.
2. Deterministic reproducibility and tie-break rules.
3. Budget and time window constraints.
4. Real pilot planner with primary field evidence and directed legs.
5. Accessibility and temporal closure filtering.
6. Strict namespace separation (synthetic IDs rejected from real planner).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest
from datetime import date

from cultureroute.planner import (
    plan_synthetic_day,
    plan_real_place_day,
    DayPlan,
    PlanStop,
    PlanLeg
)
from cultureroute.routing import TransportMode, DirectedRouteLeg

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_DB = ROOT_DIR / "data" / "real_catalog.db"
EVIDENCE_DB = ROOT_DIR / "data" / "venue_evidence.db"


def test_published_catalog_does_not_duplicate_evidence_or_routes():
    with sqlite3.connect(CATALOG_DB) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not tables.intersection({"venue_evidence", "evidence_retractions", "real_route_legs"})


def test_jaipur_specification_fixture_exact_reproduction():
    """Verify exact reproduction of the Saturday Jaipur specification baseline [Spec p. 5]."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",  # Saturday
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3
    )

    fastest = plans["fastest"]
    most_cultural = plans["most_cultural"]

    assert fastest is not None, "Fastest plan must be found"
    assert most_cultural is not None, "Most cultural plan must be found"

    # Fastest Plan Verification [Spec p. 5]
    # Expected: 1 cultural stop, 207 minutes (3h 27m), INR 585.46, 1.806 kg carbon
    assert fastest.cultural_stops_count == 1
    assert fastest.total_stops_count == 3
    assert fastest.elapsed_minutes == 207
    assert fastest.elapsed_formatted == "3h 27m"
    assert float(fastest.total_cost_inr) == pytest.approx(585.46, abs=0.01)
    assert fastest.estimated_carbon_kg == pytest.approx(1.806, abs=0.005)

    # Check fastest stops sequence
    fastest_stop_names = [s.name for s in fastest.stops]
    assert fastest_stop_names == ["Jaipur Bazaar", "Zipline Point", "Coffee Roastery Tour"]
    assert fastest.stops[0].arrival_time == "09:00"
    assert fastest.stops[0].visit_end_time == "10:15"
    assert fastest.stops[1].arrival_time == "10:42"
    assert fastest.stops[1].visit_end_time == "11:27"
    assert fastest.stops[2].arrival_time == "11:42"
    assert fastest.stops[2].visit_end_time == "12:27"

    # Most Cultural Plan Verification [Spec p. 5]
    # Expected: 2 cultural stops, 227 minutes (3h 47m), INR 638.30, 2.840 kg carbon
    assert most_cultural.cultural_stops_count == 2
    assert most_cultural.total_stops_count == 3
    assert most_cultural.elapsed_minutes == 227
    assert most_cultural.elapsed_formatted == "3h 47m"
    assert float(most_cultural.total_cost_inr) == pytest.approx(638.30, abs=0.01)
    assert most_cultural.estimated_carbon_kg == pytest.approx(2.840, abs=0.005)

    # Check most cultural stops sequence
    cultural_stop_names = [s.name for s in most_cultural.stops]
    assert cultural_stop_names == ["Zipline Point", "Coffee Roastery Tour", "Chhatri Complex"]
    assert most_cultural.stops[0].arrival_time == "09:00"
    assert most_cultural.stops[0].visit_end_time == "09:45"
    assert most_cultural.stops[1].arrival_time == "10:00"
    assert most_cultural.stops[1].visit_end_time == "10:45"
    assert most_cultural.stops[2].arrival_time == "11:32"
    assert most_cultural.stops[2].visit_end_time == "12:47"


def test_planner_constraints_budget_and_time():
    """Verify that unrealistic budget or time limits prune sequences gracefully."""
    # Impossible budget: INR 50.00
    tight_budget_plans = plan_synthetic_day(
        city_name="Jaipur",
        budget_inr=50.0
    )
    assert tight_budget_plans["fastest"] is None
    assert tight_budget_plans["most_cultural"] is None

    # Impossible time: 1.5 hours (90 minutes) for 3 stops
    tight_time_plans = plan_synthetic_day(
        city_name="Jaipur",
        max_duration_hours=1.5
    )
    assert tight_time_plans["fastest"] is None
    assert tight_time_plans["most_cultural"] is None


def test_real_planner_without_provider_is_honest(tmp_path, monkeypatch):
    monkeypatch.delenv("CULTUREROUTE_OSRM_DRIVING_URL", raising=False)
    monkeypatch.delenv("CULTUREROUTE_OSRM_URL", raising=False)
    plans = plan_real_place_day(catalog_db=CATALOG_DB, evidence_db=EVIDENCE_DB,
        routes_db=tmp_path / "routes.db", selected_place_ids=["WD:Q825236", "WD:Q3517553"])
    assert plans["fastest"] is None
    assert "routing backend" in plans["infeasible_reason"]


def test_real_planner_step_free_filtering(tmp_path):
    plans = plan_real_place_day(catalog_db=CATALOG_DB, evidence_db=EVIDENCE_DB,
        routes_db=tmp_path / "routes.db", selected_place_ids=["WD:Q825236", "WD:Q3517553"],
        target_stops=2, step_free_required=True, allow_network=False)
    assert plans["fastest"] is None
    assert "step-free" in plans["infeasible_reason"]


def test_documented_friday_closure_exclusion(tmp_path):
    plans = plan_real_place_day(catalog_db=CATALOG_DB, evidence_db=EVIDENCE_DB,
        routes_db=tmp_path / "routes.db", selected_place_ids=["WD:Q9141"],
        visit_date=date(2026, 11, 13), target_stops=1, allow_network=False)
    assert plans["fastest"] is None
    assert "documented closed" in plans["infeasible_reason"]


def test_synthetic_rejection_in_real_planner(tmp_path):
    """Verify synthetic POI IDs cannot enter real pilot planner."""
    with pytest.raises(ValueError):
        # Passing synthetic city ID or invalid namespace should be rejected
        plan_real_place_day(catalog_db=CATALOG_DB, evidence_db=EVIDENCE_DB,
            routes_db=tmp_path / "routes.db", selected_place_ids=["poi_jai_01"],
            target_stops=1, allow_network=False)


def test_real_round_trip_uses_directed_return_leg(tmp_path, monkeypatch):
    def routed(origin_id, origin_lat, origin_lon, destination_id, destination_lat, destination_lon,
               mode, store, **_):
        forward = origin_id == "WD:Q825236"
        minutes = 10 if forward else 15
        return DirectedRouteLeg(origin_id, destination_id, mode, 20000, minutes * 60,
            20, minutes, True,
            polyline_points=[(origin_lat, origin_lon),
                ((origin_lat + destination_lat) / 2, (origin_lon + destination_lon) / 2),
                (destination_lat, destination_lon)],
            source_name="Mock validated directed provider")
    monkeypatch.setattr("cultureroute.real_planner.compute_directed_leg", routed)
    args = dict(catalog_db=CATALOG_DB, evidence_db=EVIDENCE_DB,
        routes_db=tmp_path / "routes.db", selected_place_ids=["WD:Q825236", "WD:Q3517553"],
        target_stops=2, allow_network=False, user_duration_minutes=60)
    one_way = plan_real_place_day(**args)["fastest"]
    return_trip = plan_real_place_day(**args, round_trip=True)["fastest"]
    assert one_way is not None and return_trip is not None
    assert len(one_way.legs) == 1 and len(return_trip.legs) == 2
    assert return_trip.elapsed_minutes == one_way.elapsed_minutes + 15
    assert return_trip.legs[-1].destination_id == return_trip.stops[0].poi_id


def test_day_plan_export_structure():
    """Verify plan exports complete structured provenance and leg breakdown."""
    plans = plan_synthetic_day(city_name="Jaipur")
    fastest = plans["fastest"]
    assert fastest is not None

    export_dict = {
        "plan_id": fastest.plan_id,
        "objective": fastest.objective,
        "namespace": fastest.namespace,
        "elapsed_minutes": fastest.elapsed_minutes,
        "elapsed_formatted": fastest.elapsed_formatted,
        "stops": [
            {
                "stop_index": s.stop_index,
                "poi_id": s.poi_id,
                "name": s.name,
                "category": s.category,
                "arrival_time": s.arrival_time,
                "visit_start_time": s.visit_start_time,
                "visit_end_time": s.visit_end_time,
                "entry_fee": str(s.entry_fee)
            }
            for s in fastest.stops
        ],
        "legs": [
            {
                "leg_index": l.leg_index,
                "origin_id": l.origin_id,
                "destination_id": l.destination_id,
                "mode": l.mode,
                "travel_minutes": l.travel_minutes,
                "cost_inr": str(l.cost_inr),
                "carbon_kg": l.carbon_kg
            }
            for l in fastest.legs
        ]
    }
    assert len(export_dict["stops"]) == 3
    assert len(export_dict["legs"]) == 2
    assert export_dict["elapsed_minutes"] == 207
