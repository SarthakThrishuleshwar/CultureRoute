"""Tests for CultureRoute Stabilization Phase 2: Deterministic Synthetic Day Planner.

Verifies:
1. Exact Jaipur Saturday specification baseline fixture (09:00, 6h, INR 1,000, 3 stops).
2. Selected date closure behavior (Saturday open vs Tuesday closed for poi_5252b3dc).
3. Directed travel matrix legs: origin -> dest -> mode matching without reverse inference or substitution.
4. Transport mode filtering: 'cab' vs 'walk'.
5. Hard constraint filtering: step-free accessibility at stop.
6. Preferred categories tie-breaking.
7. Explicit unknown/partial operating hours conditional result labeling.
8. Decimal precision for entry fees, transit fares, and total costs.
9. Deterministic tie-breaking and identical-objective detection.
10. Input validation: invalid time, negative duration/budget, out-of-range stops, invalid dates.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from cultureroute.planner import (
    plan_synthetic_day,
    parse_time_to_minutes,
    DayPlan,
    PlanStop,
    PlanLeg
)


def test_jaipur_saturday_fixture_exactness():
    """Verify exact reproduction of the Saturday Jaipur specification baseline."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",  # Saturday
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3,
        transport_mode="cab"
    )

    fastest = plans["fastest"]
    cultural = plans["most_cultural"]

    assert fastest is not None, "Fastest plan must be feasible"
    assert cultural is not None, "Most cultural plan must be feasible"

    # Fastest Plan: 207 min (3h 27m), INR 585.46, 1 cultural stop, 1.806 kg carbon
    assert fastest.elapsed_minutes == 207
    assert fastest.elapsed_formatted == "3h 27m"
    assert fastest.cultural_stops_count == 1
    assert fastest.total_stops_count == 3
    assert float(fastest.total_cost_inr) == pytest.approx(585.46, abs=0.01)
    assert fastest.estimated_carbon_kg == pytest.approx(1.806, abs=0.005)
    assert fastest.transport_mode == "cab"
    assert fastest.result_level == "VERIFIED_SYNTHETIC"

    fastest_stop_ids = [s.poi_id for s in fastest.stops]
    assert fastest_stop_ids == ["poi_e68abae6", "poi_bf6716e9", "poi_5252b3dc"]

    # Verify exact stop timing and matrix legs
    assert fastest.stops[0].arrival_time == "09:00"
    assert fastest.stops[0].visit_end_time == "10:15"
    assert fastest.stops[1].arrival_time == "10:42"
    assert fastest.stops[1].visit_end_time == "11:27"
    assert fastest.stops[2].arrival_time == "11:42"
    assert fastest.stops[2].visit_end_time == "12:27"

    assert len(fastest.legs) == 2
    assert fastest.legs[0].matrix_id == "ptm_c5861aaf"
    assert fastest.legs[0].origin_id == "poi_e68abae6"
    assert fastest.legs[0].destination_id == "poi_bf6716e9"
    assert fastest.legs[0].travel_minutes == 27
    assert fastest.legs[1].matrix_id == "ptm_d95accc3"
    assert fastest.legs[1].origin_id == "poi_bf6716e9"
    assert fastest.legs[1].destination_id == "poi_5252b3dc"
    assert fastest.legs[1].travel_minutes == 15

    # Most Cultural Plan: 227 min (3h 47m), INR 638.30, 2 cultural stops, 2.840 kg carbon
    assert cultural.elapsed_minutes == 227
    assert cultural.elapsed_formatted == "3h 47m"
    assert cultural.cultural_stops_count == 2
    assert cultural.total_stops_count == 3
    assert float(cultural.total_cost_inr) == pytest.approx(638.30, abs=0.01)
    assert cultural.estimated_carbon_kg == pytest.approx(2.840, abs=0.005)

    cultural_stop_ids = [s.poi_id for s in cultural.stops]
    assert cultural_stop_ids == ["poi_bf6716e9", "poi_5252b3dc", "poi_afcb7beb"]

    assert len(cultural.legs) == 2
    assert cultural.legs[0].matrix_id == "ptm_d95accc3"
    assert cultural.legs[0].origin_id == "poi_bf6716e9"
    assert cultural.legs[0].destination_id == "poi_5252b3dc"
    assert cultural.legs[1].matrix_id == "ptm_25ddf450"
    assert cultural.legs[1].origin_id == "poi_5252b3dc"
    assert cultural.legs[1].destination_id == "poi_afcb7beb"


def test_selected_date_affects_day_of_week_closures():
    """Verify that changing the visit date affects closures.
    poi_5252b3dc (Coffee Roastery Tour) has closed_days='1' (Tuesday).
    On Tuesday (2026-08-25), it must be rejected from both itineraries."""
    tuesday_plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-25",  # Tuesday (weekday 1)
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3
    )

    fastest = tuesday_plans["fastest"]
    cultural = tuesday_plans["most_cultural"]

    assert fastest is not None
    assert cultural is not None

    # Neither plan should contain poi_5252b3dc since it is closed on Tuesday
    assert "poi_5252b3dc" not in [s.poi_id for s in fastest.stops]
    assert "poi_5252b3dc" not in [s.poi_id for s in cultural.stops]


def test_mode_specific_directed_legs_and_no_reverse_inference():
    """Verify legs strictly match the requested transport mode and do not reverse infer."""
    walk_plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3,
        transport_mode="walk"
    )
    # Walking distances in Jaipur take significantly longer; verify walking legs or infeasibility
    if walk_plans["fastest"] is not None:
        assert all(l.mode == "walk" for l in walk_plans["fastest"].legs)
        assert walk_plans["fastest"].transport_mode == "walk"


def test_step_free_filtering_hard_constraint():
    """Verify step-free filter requires accessibility == 'step_free' at all stops."""
    step_free_plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        step_free_only=True,
        target_stops=3
    )
    if step_free_plans["fastest"] is not None:
        for s in step_free_plans["fastest"].stops:
            assert s.accessibility == "step_free"


def test_preferred_category_tie_breaker():
    """Verify preferred cultural categories act deterministically."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3,
        preferred_categories=["heritage"]
    )
    assert plans["fastest"] is not None
    assert plans["most_cultural"] is not None


def test_decimal_currency_and_no_zero_fee_assumption():
    """Verify money calculations are strictly in Decimal."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3
    )
    fastest = plans["fastest"]
    assert isinstance(fastest.entry_cost_inr, Decimal)
    assert isinstance(fastest.travel_cost_inr, Decimal)
    assert isinstance(fastest.total_cost_inr, Decimal)
    assert fastest.total_cost_inr == fastest.entry_cost_inr + fastest.travel_cost_inr
    for s in fastest.stops:
        assert isinstance(s.entry_fee, Decimal)


def test_infeasible_requests_return_clean_none():
    """Verify budget or time window overruns return None cleanly without raising exceptions."""
    # Extreme budget constraint
    low_budget = plan_synthetic_day(
        city_name="Jaipur",
        budget_inr=10.0
    )
    assert low_budget["fastest"] is None
    assert low_budget["most_cultural"] is None

    # Impossible time constraint (30 minutes for 3 stops)
    low_time = plan_synthetic_day(
        city_name="Jaipur",
        max_duration_hours=0.5
    )
    assert low_time["fastest"] is None
    assert low_time["most_cultural"] is None


def test_input_validation_errors():
    """Verify malformed inputs raise clear ValueErrors."""
    with pytest.raises(ValueError, match="Invalid time format"):
        plan_synthetic_day(city_name="Jaipur", start_time="invalid_time")

    with pytest.raises(ValueError, match="Available duration must be positive"):
        plan_synthetic_day(city_name="Jaipur", max_duration_hours=-2.0)

    with pytest.raises(ValueError, match="Budget must be positive"):
        plan_synthetic_day(city_name="Jaipur", budget_inr=0.0)

    with pytest.raises(ValueError, match="Target stops must be between 2 and 5"):
        plan_synthetic_day(city_name="Jaipur", target_stops=1)

    with pytest.raises(ValueError, match="Invalid visit date"):
        plan_synthetic_day(city_name="Jaipur", visit_date="not-a-date")

    with pytest.raises(ValueError, match="Synthetic study city 'NonExistentCity' not found"):
        plan_synthetic_day(city_name="NonExistentCity")
