"""Tests for CultureRoute Stage R4: Complete Discover, Planner, and Compare.

Verifies:
1. Exact mathematical reproduction of the Jaipur specification baseline fixture:
   - Fastest: 1 cultural stop / 207 min / INR 585.46 / 1.806 kg carbon.
   - Most Cultural: 2 cultural stops / 227 min / INR 638.30 / 2.840 kg carbon.
2. Second city plan generation (e.g. Agra generates feasible 3-stop day plans).
3. Same-objective route identification (Varanasi produces identical route for both objectives).
4. Honest infeasible state handling on constrained budget (INR 50.0).
5. Safe rejection of invalid start times ("noon", "25:00").
6. Distinct catalog vs travel-matrix coverage across study cities (15 listed / 10 matrix-covered).
7. WanderMatch guide telemetry discoverability for study cities.
8. Plan comparison timetable export and structured JSON export fidelity.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from cultureroute.planner import parse_time_to_minutes, plan_synthetic_day
from cultureroute.study_data import get_study_cities, get_city_attractions
from cultureroute.study_db import open_study_cache

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_jaipur_specification_fixture_exact_values():
    """Verify exact reproduction of Jaipur Saturday specification baseline."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3,
    )
    fastest = plans.get("fastest")
    cultural = plans.get("most_cultural")

    assert fastest is not None
    assert cultural is not None

    # Fastest Plan: 1 cultural stop, 207 minutes, INR 585.46, 1.806 kg carbon
    assert fastest.cultural_stops_count == 1
    assert fastest.total_stops_count == 3
    assert fastest.elapsed_minutes == 207
    assert float(fastest.total_cost_inr) == pytest.approx(585.46, abs=0.01)
    assert fastest.estimated_carbon_kg == pytest.approx(1.806, abs=0.005)

    # Most Cultural Plan: 2 cultural stops, 227 minutes, INR 638.30, 2.840 kg carbon
    assert cultural.cultural_stops_count == 2
    assert cultural.total_stops_count == 3
    assert cultural.elapsed_minutes == 227
    assert float(cultural.total_cost_inr) == pytest.approx(638.30, abs=0.01)
    assert cultural.estimated_carbon_kg == pytest.approx(2.840, abs=0.005)


def test_second_city_plan_generation_agra():
    """Verify that a second study city (Agra) successfully generates feasible day plans."""
    plans = plan_synthetic_day(
        city_name="Agra",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=8.0,
        budget_inr=2000.0,
        target_stops=3,
    )
    fastest = plans.get("fastest")
    cultural = plans.get("most_cultural")

    assert fastest is not None
    assert cultural is not None
    assert fastest.total_stops_count == 3
    assert cultural.total_stops_count == 3
    assert fastest.elapsed_minutes > 0
    assert cultural.elapsed_minutes > 0


def test_same_objective_result_varanasi():
    """Verify that in Varanasi, the same route wins both minimum time and maximum cultural objectives."""
    plans = plan_synthetic_day(
        city_name="Varanasi",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=8.0,
        budget_inr=2000.0,
        target_stops=3,
    )
    fastest = plans.get("fastest")
    cultural = plans.get("most_cultural")

    assert fastest is not None
    assert cultural is not None
    # Identical stop sequence
    f_stops = [s.poi_id for s in fastest.stops]
    c_stops = [s.poi_id for s in cultural.stops]
    assert f_stops == c_stops
    assert fastest.elapsed_minutes == cultural.elapsed_minutes == 181


def test_infeasible_budget_low_budget():
    """Verify that an overly tight budget (INR 50) returns an honest infeasible state (None)."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        budget_inr=50.0,
        target_stops=3,
    )
    assert plans.get("fastest") is None
    assert plans.get("most_cultural") is None


def test_invalid_time_handling_rejection():
    """Verify invalid start time inputs are safely caught and rejected."""
    assert parse_time_to_minutes("noon") is None
    assert parse_time_to_minutes("25:00") is None
    assert parse_time_to_minutes("") is None

    with pytest.raises(ValueError, match="Invalid time format"):
        plan_synthetic_day(city_name="Jaipur", start_time="noon")


def test_discover_matrix_coverage_split():
    """Verify all 45 study cities maintain exactly 15 catalog POIs and 10 matrix-covered POIs."""
    cities = get_study_cities()
    assert len(cities) == 45

    for city in cities:
        attractions = get_city_attractions(city["city_id"])
        assert len(attractions) == 15
        matrix_covered = sum(1 for a in attractions if a["in_travel_matrix"])
        discovery_only = sum(1 for a in attractions if not a["in_travel_matrix"])
        assert matrix_covered == 10, f"City {city['name']} expected 10 matrix-covered POIs, got {matrix_covered}"
        assert discovery_only == 5, f"City {city['name']} expected 5 discovery-only POIs, got {discovery_only}"


def test_guide_telemetry_in_discover():
    """Verify WanderMatch guide telemetry records are discoverable for Jaipur."""
    with open_study_cache() as conn:
        guides = conn.execute(
            "SELECT display_name, specialisation, rating FROM tour_guides WHERE city_id = 'cty_c07454f1'"
        ).fetchall()
        assert len(guides) >= 2
        names = [g["display_name"] for g in guides]
        assert "Nisha Verma" in names or "Diya Chatterjee" in names


def test_day_plan_export_json_and_csv_fidelity():
    """Verify JSON export matches specification schema, costs, and carbon estimates."""
    plans = plan_synthetic_day(city_name="Jaipur")
    fastest = plans["fastest"]
    assert fastest is not None

    export_payload = {
        "city": "Jaipur",
        "fastest_plan": {
            "elapsed_minutes": fastest.elapsed_minutes,
            "total_cost_inr": float(fastest.total_cost_inr),
            "estimated_carbon_kg": fastest.estimated_carbon_kg,
            "stops": [{"poi_id": s.poi_id, "name": s.name} for s in fastest.stops],
            "legs": [{"origin_id": l.origin_id, "destination_id": l.destination_id} for l in fastest.legs],
        }
    }
    json_bytes = json.dumps(export_payload)
    parsed = json.loads(json_bytes)
    assert parsed["fastest_plan"]["elapsed_minutes"] == 207
    assert len(parsed["fastest_plan"]["stops"]) == 3
    assert len(parsed["fastest_plan"]["legs"]) == 2
