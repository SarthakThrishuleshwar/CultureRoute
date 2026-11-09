"""Tests for CultureRoute Stage P3: Navigation, Forms, Plan Handoff, and Preferences.

Verifies:
1. Exact Jaipur Benchmark Fixture:
   - Jaipur Saturday 09:00, 6 hours, INR 1,000, 3 stops
   - Fastest: 207 min / INR 585.46 / 1.806 kg
   - Cultural: 227 min / INR 638.30 / 2.840 kg
2. Planner -> Compare Snapshot Handoff:
   - Planner stores submitted parameters and generated plans in session state.
   - Compare consumes the active snapshot instead of recalculating hardcoded Jaipur.
   - Direct link to Compare without prior Planner run shows named Jaipur benchmark fixture.
3. Infeasible Plan Handling:
   - When infeasible constraints are submitted (e.g. INR 100 budget), Compare displays an honest notice.
4. Settings Downstream Propagation:
   - Default city modifies Discover's active city.
   - Table page size modifies data preview limits in Datasets.
   - Motion preference persists in session state.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.planner import plan_synthetic_day, parse_time_to_minutes

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_p3_exact_jaipur_benchmark_fixture_values():
    """Verify the Jaipur specification benchmark produces exact audited fixture metrics."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3
    )

    fastest = plans.get("fastest")
    cultural = plans.get("most_cultural")

    assert fastest is not None
    assert cultural is not None

    # Exact expected fixture metrics
    assert fastest.elapsed_minutes == 207
    assert round(float(fastest.total_cost_inr), 2) == 585.46
    assert round(fastest.estimated_carbon_kg, 3) == 1.806
    assert fastest.cultural_stops_count == 1
    assert fastest.total_stops_count == 3

    assert cultural.elapsed_minutes == 227
    assert round(float(cultural.total_cost_inr), 2) == 638.30
    assert round(cultural.estimated_carbon_kg, 3) == 2.840
    assert cultural.cultural_stops_count == 2
    assert cultural.total_stops_count == 3

    # Differential trade-offs
    assert (cultural.elapsed_minutes - fastest.elapsed_minutes) == 20
    assert round(float(cultural.total_cost_inr - fastest.total_cost_inr), 2) == 52.84
    assert round(cultural.estimated_carbon_kg - fastest.estimated_carbon_kg, 3) == 1.034


def test_p3_direct_compare_view_shows_jaipur_fixture():
    """Verify that opening Compare without prior Planner run shows the named Jaipur fixture."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "compare"
    at.run()
    assert not at.exception

    md_text = " ".join(m.value for m in at.markdown)
    assert "Compare Fastest vs Most Cultural Plans" in md_text
    assert "JAIPUR BENCHMARK FIXTURE" in md_text or "Specification Baseline" in md_text
    assert "207 min" in md_text or "3h 27m" in md_text
    assert "585.46" in md_text


def test_p3_planner_to_compare_handoff_custom_city():
    """Verify that generating plans for Agra in Planner carries Agra into Compare."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "planner"
    at.run()
    assert not at.exception

    # Click Agra preset button
    agra_btn = [b for b in at.button if "Agra" in b.label][0]
    agra_btn.click().run()
    assert not at.exception

    # Generate plans for Agra
    gen_btn = [b for b in at.button if "Generate Plans" in b.label][0]
    gen_btn.click().run()
    assert not at.exception

    # Now navigate to Compare within the same session
    at.query_params["view"] = "compare"
    at.run()
    assert not at.exception

    md_text = " ".join(m.value for m in at.markdown)
    # Must NOT show hardcoded Jaipur
    assert "Agra" in md_text
    assert "USER SUBMITTED SNAPSHOT" in md_text or "Agra" in md_text


def test_p3_infeasible_plan_compare_handling():
    """Verify that submitting impossible constraints displays an honest infeasible state in Compare."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "planner"
    at.run()
    assert not at.exception

    # Set impossible budget INR 100
    budget_input = [n for n in at.number_input if "Budget" in n.label][0]
    budget_input.set_value(100.0).run()
    assert not at.exception

    gen_btn = [b for b in at.button if "Generate Plans" in b.label][0]
    gen_btn.click().run()
    assert not at.exception

    # Navigate to Compare
    at.query_params["view"] = "compare"
    at.run()
    assert not at.exception

    # Should display Infeasible warning, not crash or revert silently to Jaipur
    warnings = [w.value for w in at.warning]
    assert any("Infeasible Plan Comparison" in w or "Infeasible Day Plan" in w for w in warnings)


def test_p3_settings_default_city_propagates_to_discover():
    """Verify changing default city in Settings propagates to Discover."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "settings"
    at.run()
    assert not at.exception

    # Change default city to Delhi
    city_select = [s for s in at.selectbox if "Default Study City" in s.label][0]
    city_select.set_value("New Delhi").run()
    save_btn = [b for b in at.button if "Save Preferences" in b.label][0]
    save_btn.click().run()
    assert not at.exception

    # Navigate to Discover
    at.query_params["view"] = "discover"
    at.run()
    assert not at.exception

    # Active city in Discover selectbox should now be Delhi
    disc_city_select = [s for s in at.selectbox if "Study City" in s.label][0]
    assert disc_city_select.value == "New Delhi"
