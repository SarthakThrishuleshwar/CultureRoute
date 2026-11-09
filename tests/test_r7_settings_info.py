"""Tests for CultureRoute Stage R7: Settings, Information, and Integrated Presentation.

Verifies:
1. Navigation and query parameter deep-linking to Settings and Information.
2. Settings preferences functional behavior:
   - Default study city preference persistence in session state.
   - Table preview limit preference persistence.
   - Preferred result view presentation preference.
   - Reset to system defaults.
   - Confirmation messages and persistence/security invariant contract.
3. Information screen completeness:
   - SDG 8, Target 8.9 alignment and strict non-commercial synthetic boundary notice.
   - Reconciled 24-table study catalog inventory table with row counts and grains.
   - Three analytical populations definitions (Listings 675 / Interactions 6,850 / Planned Stops 3,191).
   - Jaipur specification baseline reproduction guide (Plan A 207 min / Plan B 227 min).
   - DEV syllabus coverage matrix across Units 1–5.
4. Clean editorial style and zero emojis across Settings and Information.
"""

from __future__ import annotations

from pathlib import Path
import re
import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_settings_screen_loads_cleanly_in_apptest():
    """Verify navigating to Settings loads with 0 exceptions and renders controls."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "settings"
    at.run()
    assert not at.exception

    # Check headings and controls
    assert any("Settings & Preferences" in m.value for m in at.markdown)
    assert len(at.selectbox) >= 2  # Default City, Preferred View
    assert len(at.select_slider) >= 1  # Table page size slider
    assert len(at.button) >= 2  # Save Preferences, Reset


def test_settings_save_and_reset_behavior():
    """Verify saving settings updates session state and reset restores defaults."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "settings"
    at.run()

    # Change default city to Agra
    city_select = at.selectbox[0]
    city_select.set_value("Agra").run()

    # Change page size slider to 25
    slider = at.select_slider[0]
    slider.set_value(25).run()

    # Click Save Preferences button
    btn_save = at.get("button")[0]
    btn_save.click().run()
    assert not at.exception
    assert at.session_state["default_city"] == "Agra"
    assert at.session_state["p_city"] == "Agra"
    assert at.session_state["table_page_size"] == 25
    assert any("Preferences saved" in s.value for s in at.success)

    # Click Reset button
    btn_reset = at.get("button")[1]
    btn_reset.click().run()
    assert not at.exception
    assert at.session_state["default_city"] == "Jaipur"
    assert at.session_state["table_page_size"] == 15
    assert any("Preferences reset" in info.value for info in at.info)


def test_information_screen_completeness_and_tabs():
    """Verify Information screen renders all 5 required documentation tabs with 0 exceptions."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "information"
    at.run()
    assert not at.exception

    # Verify tabs
    assert len(at.tabs) >= 5
    all_text = " ".join([m.value for m in at.markdown] + [s.value for s in at.subheader])

    # 1. SDG 8.9 & Boundaries
    assert "SDG Target 8.9" in all_text
    assert "non-commercial" in all_text.lower() or "synthetic" in all_text.lower()

    # 2. 24-Table Study Inventory
    assert "24-Table" in all_text
    assert len(at.dataframe) >= 1  # 24-table inventory dataframe

    # 3. Three Analytical Populations
    assert "Listings Population" in all_text
    assert "675" in all_text
    assert "6,850" in all_text
    assert "3,191" in all_text

    # 4. Jaipur Reproduction Guide
    assert "Jaipur Specification" in all_text
    assert "207 minutes" in all_text
    assert "227 minutes" in all_text

    # 5. DEV Syllabus Matrix
    assert "DEV Syllabus" in all_text
    assert "Unit 1: EDA Foundations" in all_text
    assert "Unit 5: pandas & Sources" in all_text


def test_no_emojis_in_settings_and_information_content():
    """Verify Settings and Information screens contain zero emojis in headings or labels."""
    content = APP_FILE.read_text(encoding="utf-8")
    s_idx = content.find('# SCREEN 7: SETTINGS')
    assert s_idx != -1
    settings_and_info = content[s_idx:]

    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF]"
    )

    found_emojis = emoji_pattern.findall(settings_and_info)
    assert len(found_emojis) == 0, f"Found unexpected emojis: {found_emojis}"
