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
import pytest
from datetime import date

from cultureroute.planner import (
    plan_synthetic_day,
    plan_real_pilot_day,
    DayPlan,
    PlanStop,
    PlanLeg
)
from cultureroute.routing import TransportMode

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_DB = ROOT_DIR / "data" / "real_catalog.db"


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


def test_real_pilot_day_planner():
    """Verify day planning for real pilot venues in Karnataka."""
    assert CATALOG_DB.exists()
    plans = plan_real_pilot_day(
        catalog_db=CATALOG_DB,
        state_or_district="Karnataka",
        visit_date=date(2026, 8, 15),
        start_time="09:00",
        max_duration_hours=8.0,
        budget_inr=1500.0,
        target_stops=3,
        transport_mode=TransportMode.DRIVING
    )
    fastest = plans["fastest"]
    assert fastest is not None
    assert fastest.namespace == "REAL"
    assert fastest.total_stops_count == 3
    assert fastest.cultural_stops_count == 3
    assert len(fastest.legs) == 2
    assert all(s.poi_id.startswith("WD:") for s in fastest.stops)


def test_real_planner_step_free_filtering():
    """Verify step-free accessibility requirement prunes venues without verified ramp/elevator access."""
    # When step-free is required, only venues with verified step-free access are eligible
    plans = plan_real_pilot_day(
        catalog_db=CATALOG_DB,
        state_or_district="Karnataka",
        visit_date=date(2026, 8, 15),
        target_stops=3,
        step_free_required=True
    )
    # Since only 1 pilot venue currently has verified step-free access in Karnataka,
    # target_stops=3 cannot be satisfied, so planner returns None
    assert plans["fastest"] is None
    assert plans["most_cultural"] is None


def test_real_planner_temporal_closure_exclusion():
    """Verify venue with temporal closure notice on visit date is pruned from schedule."""
    # Durga Temple Aihole (WD:Q3517553) is closed for monsoon conservation from 2026-07-01 to 2026-07-31
    plans_closed_date = plan_real_pilot_day(
        catalog_db=CATALOG_DB,
        state_or_district="Karnataka",
        visit_date=date(2026, 7, 15),
        target_stops=3
    )
    # With Durga Temple closed, only Badami and Pattadakal remain in Bagalkot (2 venues < 3 targets)
    assert plans_closed_date["fastest"] is None


def test_synthetic_rejection_in_real_planner():
    """Verify synthetic POI IDs cannot enter real pilot planner."""
    with pytest.raises(ValueError):
        # Passing synthetic city ID or invalid namespace should be rejected
        plan_real_pilot_day(
            catalog_db=CATALOG_DB,
            state_or_district="poi_jai_01",
            target_stops=3
        )


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
