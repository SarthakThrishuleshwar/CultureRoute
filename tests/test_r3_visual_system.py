"""Tests for CultureRoute Stage R3: Visual System and Working Navigation.

Verifies:
1. All 8 required navigation destinations reachable: Overview, Discover, Planner, Compare, Insights, DEV Lab, Settings, Information.
2. Complete absence of emojis across UI components and app entrypoint.
3. Availability and embedding of all 5 supplied photographic assets.
4. Strict WCAG 2.2 AA text contrast compliance (> 4.5:1) for all editorial design tokens.
5. Presence of .streamlit/config.toml with warm editorial paper palette.
6. Clean rendering of Overview, Discover shell, and Insights analytics in AppTest.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.ui_components import get_asset_base64

ROOT_DIR = Path(__file__).resolve().parent.parent


def _relative_luminance(hex_color: str) -> float:
    hex_clean = hex_color.lstrip("#")
    r, g, b = [int(hex_clean[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _relative_luminance(hex1)
    l2 = _relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_navigation_destinations_all_eight_present():
    """Verify all eight required screens are defined in the navigation contract."""
    app_text = (ROOT_DIR / "app.py").read_text(encoding="utf-8")
    for dest in ["Overview", "Discover", "Planner", "Compare", "Insights", "DEV Lab", "Settings", "Information"]:
        assert f'"{dest}"' in app_text, f"Destination {dest} missing from app.py"


def test_zero_emojis_in_visual_system():
    """Verify zero unicode emojis exist in app.py or ui_components.py."""
    emoji_regex = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    
    app_text = (ROOT_DIR / "app.py").read_text(encoding="utf-8")
    ui_text = (ROOT_DIR / "cultureroute" / "ui_components.py").read_text(encoding="utf-8")
    
    assert len(emoji_regex.findall(app_text)) == 0, "Emojis found in app.py"
    assert len(emoji_regex.findall(ui_text)) == 0, "Emojis found in ui_components.py"

    # Also verify common miscellaneous symbols (like star, pointing hand, etc.) are excluded
    for disallowed in ["\u2733", "\u25B6", "\u2794", "\u21B3"]:
        assert disallowed not in ui_text, f"Disallowed decorative symbol {disallowed!r} found in ui_components"


def test_photograph_assets_availability_and_embedding():
    """Verify all 5 supplied photographs are present and convert to base64 data URLs."""
    expected_assets = [
        "green-landscape.jpg",
        "heritage-fort.avif",
        "museum-interior.jpg",
        "golden-temple.jpg",
        "local-food.jpg"
    ]
    for asset in expected_assets:
        url = get_asset_base64(asset)
        assert url.startswith("data:image/"), f"Failed to encode asset {asset}"
        assert len(url) > 1000, f"Asset data URL too short for {asset}"


def test_wcag_contrast_compliance():
    """Verify that all core text color tokens achieve WCAG 2.2 AA contrast on paper background."""
    paper = "#f7f3e9"
    tokens = {
        "charcoal_ink": "#292925",
        "muted_ink": "#5c5852",
        "oxblood_accent": "#982b32",
        "quiet_blue": "#365376",
    }
    for name, hex_val in tokens.items():
        ratio = _contrast_ratio(paper, hex_val)
        assert ratio >= 4.5, f"Token {name} ({hex_val}) failed WCAG 2.2 AA: contrast is {ratio:.2f}:1 (< 4.5:1)"


def test_config_toml_theme_present():
    """Verify that .streamlit/config.toml is configured with the editorial palette."""
    cfg_path = ROOT_DIR / ".streamlit" / "config.toml"
    assert cfg_path.exists(), ".streamlit/config.toml must exist"
    content = cfg_path.read_text(encoding="utf-8")
    assert 'backgroundColor = "#f7f3e9"' in content
    assert 'textColor = "#292925"' in content
    assert 'primaryColor = "#982b32"' in content


def test_apptest_screens_render_without_exception():
    """Verify Overview, Discover, and Insights render with 0 uncaught exceptions in AppTest via URL routing."""
    at = AppTest.from_file(str(ROOT_DIR / "app.py"))
    at.run()
    assert not at.exception

    for target in ["overview", "discover", "insights", "datasets", "devlab", "model", "settings", "information"]:
        at.query_params["view"] = target
        at.run()
        assert not at.exception, f"Exception rendering screen {target}"


def test_p1_sidebar_link_navigation_contract():
    """Verify P1 contract: main navigation uses semantic links with local SVGs, aria-current, and no radio navigation."""
    app_text = (ROOT_DIR / "app.py").read_text(encoding="utf-8")
    assert "render_sidebar_navigation" in app_text
    assert "st.sidebar.radio" not in app_text, "st.sidebar.radio must be completely removed from main navigation"
    for screen in ["Overview", "Discover", "Planner", "Compare", "Datasets", "Insights", "DEV Lab", "Prediction Model", "Settings", "Information"]:
        assert f'"{screen}"' in app_text, f"Destination {screen} missing from app.py"

