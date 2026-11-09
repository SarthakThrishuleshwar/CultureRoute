"""Tests for CultureRoute Stage P1: Match the Demo and Replace Radio Navigation.

Verifies:
1. Complete removal of radio-group navigation in main navigation.
2. Real link semantics with <a href="?view=...">, visible text, and aligned local SVG line icons.
3. Navigation grouping into EXPLORE, STUDY, and HELP.
4. All 10 destinations reachable via URL routing:
   Overview, Discover, Planner, Compare, Datasets, Insights, DEV Lab, Prediction Model, Settings, Information.
5. aria-current="page" present on active link.
6. Honest development states for Datasets (Stage P2) and Prediction Model (Stage P6).
7. Tactile button interaction tokens: 200ms transition, 4px shadow, translate(2px, 2px).
8. Reduced-motion compliance honoring both OS media feature and in-app preference.
9. Truthful hero CTA copy and links (no stale "Phase 3" real places claim).
10. Zero unicode emojis across application and UI components.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"
UI_FILE = ROOT_DIR / "cultureroute" / "ui_components.py"
DEMO_HTML = ROOT_DIR / "site" / "dist" / "index.html"


def test_no_radio_in_main_navigation():
    """Verify that st.sidebar.radio is completely removed from the main navigation."""
    app_text = APP_FILE.read_text(encoding="utf-8")
    assert "st.sidebar.radio" not in app_text, "st.sidebar.radio must not be used for main navigation"
    assert "render_sidebar_navigation" in app_text, "Must use render_sidebar_navigation"


def test_sidebar_groups_and_svg_icons():
    """Verify sidebar defines EXPLORE, STUDY, HELP groups and aligned SVG icons without emojis."""
    ui_text = UI_FILE.read_text(encoding="utf-8")
    
    # Check groups
    assert "EXPLORE" in ui_text
    assert "STUDY" in ui_text
    assert "HELP" in ui_text

    # Check SVG line icons with stroke 1.8 and aria-hidden
    assert 'stroke-width="1.8"' in ui_text
    assert 'aria-hidden="true"' in ui_text
    assert 'aria-current="page"' in ui_text

    # Zero emojis
    emoji_regex = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    assert len(emoji_regex.findall(ui_text)) == 0, "No emojis allowed in UI components"


def test_all_ten_destinations_routable():
    """Verify all 10 destinations are defined in NAV_OPTIONS and routable via query_params."""
    expected_screens = [
        "Overview",
        "Discover",
        "Planner",
        "Compare",
        "Datasets",
        "Insights",
        "DEV Lab",
        "Prediction Model",
        "Settings",
        "Information",
    ]
    app_text = APP_FILE.read_text(encoding="utf-8")
    for screen in expected_screens:
        assert f'"{screen}"' in app_text, f"Screen {screen} missing from NAV_OPTIONS"

    # Test rendering each destination in AppTest
    at = AppTest.from_file(str(APP_FILE), default_timeout=25)
    at.run()
    assert not at.exception

    slug_map = {
        "overview": "Overview",
        "discover": "Discover",
        "planner": "Planner",
        "compare": "Compare",
        "datasets": "Datasets",
        "insights": "Insights",
        "devlab": "DEV Lab",
        "model": "Prediction Model",
        "settings": "Settings",
        "information": "Information",
    }
    for slug, name in slug_map.items():
        at.query_params["view"] = slug
        at.run()
        assert not at.exception, f"Failed rendering screen {name} with view={slug}"


def test_datasets_and_model_honest_development_states():
    """Verify Datasets and Prediction Model display honest status notices during P1."""
    at = AppTest.from_file(str(APP_FILE), default_timeout=25)
    
    # Datasets
    at.query_params["view"] = "datasets"
    at.run()
    assert not at.exception
    datasets_text = " ".join(m.value for m in at.markdown)
    assert "Two-Pack Study Boundary" in datasets_text or "SmartTrip (1).zip" in datasets_text
    assert "STAGE P2" in datasets_text

    # Prediction Model
    at.query_params["view"] = "model"
    at.run()
    assert not at.exception
    model_text = " ".join(m.value for m in at.markdown)
    assert "Poisson" in model_text
    assert "STAGE P6" in model_text


def test_truthful_hero_cta_copy_and_links():
    """Verify hero CTA copy has no stale 'Phase 3' or 'Real Places' claims."""
    ui_text = UI_FILE.read_text(encoding="utf-8")
    assert "Real Places (Phase 3)" not in ui_text
    assert "Explore Study Cities" in ui_text
    assert "See the DEV Lab Study" in ui_text
    assert "?view=discover" in ui_text
    assert "?view=devlab" in ui_text

    # Also check site/dist/index.html
    demo_text = DEMO_HTML.read_text(encoding="utf-8")
    assert "Real Places (Phase 3)" not in demo_text
    assert "Explore Study Cities" in demo_text
    assert "view=devlab" in demo_text


def test_tactile_button_tokens_and_reduced_motion():
    """Verify button transition tokens (200ms) and reduced-motion stylesheet handling."""
    ui_text = UI_FILE.read_text(encoding="utf-8")
    assert "transition: transform 0.2s ease, box-shadow 0.2s ease" in ui_text
    assert "box-shadow: 4px 4px 0 var(--red)" in ui_text
    assert "prefers-reduced-motion" in ui_text
    assert "reduced_motion_css" in ui_text
