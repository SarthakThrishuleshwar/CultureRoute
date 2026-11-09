"""CultureRoute Editorial UI Presentation Components.

Implements the editorial design system matching the demo prototype (site/dist):
- Palette: Paper #f7f3e9, Charcoal Ink #292925, Oxblood #982b32, Quiet Blue #365376,
  Muted Ink #5c5852 (WCAG 2.2 AA compliant contrast > 4.5:1), Pale Yellow Note #eee3a6.
- Typography: Hand-lettered display headings ("Segoe Print", "Comic Sans MS", "Trebuchet MS", cursive),
  editorial body ("Trebuchet MS", "Segoe UI", sans-serif).
- Dot-matrix tactile paper overlay texture.
- Hand-drawn SVG accents: wavy hero underline, 16-point doodle star, looping indicator arrow.
- Photographed cards with white framing borders, lifted layout, and golden glow hover transitions.
- Tactile pressed buttons, taped sticky notes, and styled editorial navigation.
- Real semantic link navigation with aligned local SVG line icons, grouped by Explore, Study, Help.
- Full reduced-motion compliance honoring both OS settings and in-app preferences.
- Zero emojis and zero unverified real-world travel claims.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "site" / "dist" / "assets"


@lru_cache(maxsize=16)
def get_asset_base64(filename: str) -> str:
    """Read an image file from site/dist/assets and return data URL."""
    filepath = ASSETS_DIR / filename
    if not filepath.exists():
        return ""
    data = filepath.read_bytes()
    suffix = filepath.suffix.lower().lstrip(".")
    if suffix in ["jpg", "jpeg"]:
        mime = "image/jpeg"
    elif suffix == "avif":
        mime = "image/avif"
    else:
        mime = f"image/{suffix}"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def inject_editorial_css() -> None:
    """Inject global editorial stylesheet matching site/dist prototype into Streamlit."""
    is_reduced = st.session_state.get("motion_preference") == "Reduced Motion (Accessibility)"
    reduced_motion_css = """
    *, *:before, *:after {
        transition: none !important;
        animation: none !important;
        transform: none !important;
    }
    """ if is_reduced else ""

    css = f"""
<style>
    /* CSS Design Tokens matching prototype */
    :root {{
        --paper: #f7f3e9;
        --ink: #292925;
        --red: #982b32;
        --oxblood: #982b32;
        --muted: #5c5852;
        --muted-ink: #5c5852;
        --line: #b6afa3;
        --border-line: #b6afa3;
        --yellow: #eee3a6;
        --pale-yellow: #eee3a6;
        --blue: #365376;
        --quiet-blue: #365376;
        --panel: #eee9dd;
        --panel-bg: #eee9dd;
        --card-white: #ffffff;
        --display: "Segoe Print", "Comic Sans MS", "Trebuchet MS", cursive;
        --body: "Trebuchet MS", "Segoe UI", sans-serif;
    }}

    /* Base Paper Canvas */
    html {{
        scroll-behavior: smooth;
    }}
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background-color: var(--paper) !important;
        color: var(--ink) !important;
        font-family: var(--body) !important;
        font-size: 16px;
        line-height: 1.55;
    }}

    /* Hide Deploy button and Streamlit menu clutter while preserving sidebar collapse and expand buttons */
    .stDeployButton,
    [data-testid="stDeployButton"],
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    button[data-testid="stAppDeployButton"],
    .stToolbarActions,
    [data-testid="stToolbarActions"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
    }}

    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        z-index: 99999 !important;
    }}

    /* =========================================================================
       SIDEBAR THEME & CONTROLS: COLLAPSIBLE MINI-RAIL & EXPANDED VIEWS
       ========================================================================= */

    /* Completely eliminate sidebar scrolling and hide scrollbars */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {{
        overflow: hidden !important;
        overflow-y: hidden !important;
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }}

    [data-testid="stSidebarContent"]::-webkit-scrollbar,
    [data-testid="stSidebarUserContent"]::-webkit-scrollbar,
    section[data-testid="stSidebar"]::-webkit-scrollbar {{
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }}

    /* Eliminate Streamlit's default 96px bottom padding on sidebar */
    [data-testid="stSidebarUserContent"] {{
        padding-bottom: 8px !important;
        padding-top: 0 !important;
    }}

    /* Hide empty logo spacer & shrink header to prevent height waste */
    [data-testid="stLogoSpacer"] {{
        display: none !important;
    }}
    [data-testid="stSidebarHeader"] {{
        padding: 4px 10px 0 !important;
        min-height: 0 !important;
        height: 24px !important;
        margin-bottom: 2px !important;
    }}

    /* Expanded Sidebar: 260px width with rich branding and full navigation */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {{
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
        position: relative !important;
        transform: none !important;
        transition: width 0.22s cubic-bezier(0.16, 1, 0.3, 1), min-width 0.22s cubic-bezier(0.16, 1, 0.3, 1), max-width 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}

    /* Collapsed Sidebar: slim 68px icon rail keeping SVGs visible & interactive */
    [data-testid="stSidebar"][data-collapsed="true"],
    section[data-testid="stSidebar"][data-collapsed="true"] {{
        width: 68px !important;
        min-width: 68px !important;
        max-width: 68px !important;
        transform: none !important;
        margin-left: 0 !important;
        overflow-x: hidden !important;
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 8px rgba(41, 41, 37, 0.06) !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarContent"] {{
        width: 68px !important;
        min-width: 68px !important;
        max-width: 68px !important;
        padding: 14px 4px !important;
        overflow-x: hidden !important;
    }}

    /* Rail mode elements visibility */
    .cr-brand-mini {{
        display: none;
    }}
    .cr-brand-full {{
        display: inline;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-brand-full,
    [data-testid="stSidebar"][data-collapsed="true"] .cr-brand-subtitle,
    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-group-title,
    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-link span,
    [data-testid="stSidebar"][data-collapsed="true"] .sticky {{
        display: none !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-brand-mini {{
        display: inline-block !important;
        font-family: var(--display) !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        color: var(--red) !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-sidebar-brand {{
        padding: 4px 0 10px !important;
        margin-bottom: 8px !important;
        border-bottom: 1px solid var(--line) !important;
        text-align: center !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-group {{
        margin-bottom: 6px !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-link,
    [data-testid="stSidebar"][data-collapsed="true"] a.cr-nav-link {{
        width: 44px !important;
        height: 44px !important;
        margin: 4px auto !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 8px !important;
        transform: none !important;
        border: 1px solid transparent !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-link svg,
    [data-testid="stSidebar"][data-collapsed="true"] a.cr-nav-link svg {{
        margin: 0 !important;
        width: 20px !important;
        height: 20px !important;
        transform: none !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] a.cr-nav-link.is-active,
    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-link.is-active {{
        background-color: var(--yellow) !important;
        border: 1.5px solid var(--red) !important;
        box-shadow: 0 2px 5px rgba(50, 43, 28, 0.15) !important;
        transform: none !important;
    }}

    [data-testid="stSidebar"][data-collapsed="true"] a.cr-nav-link:hover,
    [data-testid="stSidebar"][data-collapsed="true"] .cr-nav-link:hover {{
        background-color: rgba(238, 227, 166, 0.6) !important;
        border: 1px solid var(--red) !important;
        transform: scale(1.05) !important;
    }}

    /* Floating Circular Collapse Button (in Expanded Mode) */
    [data-testid="stSidebarCollapseButton"] {{
        position: absolute !important;
        right: -14px !important;
        top: 26px !important;
        z-index: 999999 !important;
    }}
    [data-testid="stSidebarCollapseButton"] button {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        min-height: 28px !important;
        border-radius: 50% !important;
        background: var(--red) !important;
        color: #ffffff !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0 2px 6px rgba(41, 41, 37, 0.25) !important;
        padding: 0 !important;
        cursor: pointer !important;
        transition: transform 0.15s ease, background-color 0.15s ease !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover {{
        background: #782228 !important;
        transform: scale(1.1) !important;
    }}
    [data-testid="stSidebarCollapseButton"] button span {{
        color: #ffffff !important;
        font-size: 16px !important;
    }}

    /* Floating Circular Expand Button (in Collapsed Rail Mode) */
    [data-testid="stSidebarCollapsedControl"] {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        left: 54px !important;
        top: 26px !important;
        z-index: 999999 !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }}
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"] {{
        position: fixed !important;
        left: 54px !important;
        top: 26px !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        min-height: 28px !important;
        border-radius: 50% !important;
        background: var(--red) !important;
        color: #ffffff !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0 2px 6px rgba(41, 41, 37, 0.25) !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 999999 !important;
        cursor: pointer !important;
        transition: transform 0.15s ease, background-color 0.15s ease !important;
    }}
    [data-testid="stExpandSidebarButton"]:hover,
    button[data-testid="stExpandSidebarButton"]:hover {{
        background: #782228 !important;
        transform: scale(1.1) !important;
    }}
    [data-testid="stExpandSidebarButton"] span,
    button[data-testid="stExpandSidebarButton"] span {{
        color: #ffffff !important;
        font-size: 16px !important;
    }}

    /* =========================================================================
       AUTO-STABILIZATION & FLUID RESPONSIVE LAYOUT (NO WASTED LEFT/RIGHT SPACE)
       ========================================================================= */

    .main,
    [data-testid="stMain"] {{
        flex: 1 1 auto !important;
        min-width: 0 !important;
        transition: width 0.22s cubic-bezier(0.16, 1, 0.3, 1), margin-left 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}

    /* Dynamic fluid main container widths avoiding wasted margin gaps */
    [data-testid="stSidebar"][data-collapsed="true"] + div,
    [data-testid="stSidebar"][data-collapsed="true"] ~ .main,
    [data-testid="stSidebar"][data-collapsed="true"] ~ [data-testid="stMain"] {{
        width: calc(100% - 68px) !important;
        margin-left: 0 !important;
    }}

    [data-testid="stSidebar"][data-collapsed="false"] + div,
    [data-testid="stSidebar"][data-collapsed="false"] ~ .main,
    [data-testid="stSidebar"][data-collapsed="false"] ~ [data-testid="stMain"] {{
        width: calc(100% - 260px) !important;
        margin-left: 0 !important;
    }}

    /* Auto-stabilize block container padding across laptop/desktop screens */
    .main .block-container,
    [data-testid="stAppViewBlockContainer"] {{
        max-width: 100% !important;
        padding-top: 1.75rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: clamp(1.2rem, 2.5vw, 2.8rem) !important;
        padding-right: clamp(1.2rem, 2.5vw, 2.8rem) !important;
        box-sizing: border-box !important;
    }}

    /* Responsive column stabilization preventing squished cards and wrapped badges */
    [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.85rem !important;
        align-items: stretch !important;
    }}

    .cr-card, .plan-card, .metric-card {{
        box-sizing: border-box !important;
        max-width: 100% !important;
    }}

    /* Flat Paper Surface (Dot texture removed per Stage F1) */
    body:before,
    .stApp:before,
    [data-testid="stAppViewContainer"]:before {{
        display: none !important;
        content: none !important;
    }}

    /* Typography */
    h1, h2, h3, .editorial-heading,
    [data-testid="stHeading"] h1,
    [data-testid="stHeading"] h2,
    [data-testid="stHeading"] h3,
    [data-testid="stSubheader"] {{
        font-family: var(--display) !important;
        font-weight: 500 !important;
        letter-spacing: -0.055em !important;
        line-height: 1.13 !important;
        color: var(--ink) !important;
    }}

    h1, [data-testid="stHeading"] h1 {{
        font-size: clamp(2.4rem, 4.5vw, 4.2rem) !important;
        margin-bottom: 0.25rem !important;
    }}

    h2, [data-testid="stHeading"] h2 {{
        font-size: clamp(1.8rem, 3.2vw, 2.8rem) !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
    }}

    h3, [data-testid="stHeading"] h3, [data-testid="stSubheader"] {{
        font-size: clamp(1.2rem, 2.0vw, 1.6rem) !important;
    }}

    em {{
        font-style: normal !important;
        color: var(--red) !important;
    }}

    /* Sidebar Navigation System */



    .cr-sidebar-brand {{
        padding: 2px 0 8px;
        border-bottom: 1.5px solid var(--line);
        margin-bottom: 8px;
    }}

    .cr-brand-title {{
        font-family: var(--display);
        font-size: 1.45rem;
        font-weight: 500;
        letter-spacing: -0.05em;
        line-height: 1.1;
        color: var(--ink);
        margin: 0;
    }}

    .cr-brand-title span {{
        color: var(--red);
    }}

    .cr-brand-subtitle {{
        font-family: var(--body);
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 2px;
    }}

    .cr-nav-group {{
        margin-bottom: 6px;
    }}

    .cr-nav-group-title {{
        font-family: var(--body);
        font-size: 0.60rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        padding: 0 4px 2px;
        border-bottom: 1px solid rgba(182, 175, 163, 0.4);
        margin-bottom: 2px;
    }}

    /* High Specificity: Strip default blue link colors and underlines from sidebar */
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] a:link,
    [data-testid="stSidebar"] a:visited,
    [data-testid="stSidebar"] .stMarkdown a,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a,
    [data-testid="stSidebar"] a.cr-nav-link,
    a.cr-nav-link,
    .cr-nav-link {{
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        padding: 5px 10px !important;
        margin: 1px 0 !important;
        text-decoration: none !important;
        color: var(--ink) !important;
        font-family: var(--display) !important;
        font-size: 0.88rem !important;
        line-height: 1.25 !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em !important;
        border-radius: 4px !important;
        border: 1px solid transparent !important;
        border-bottom: 1px dashed var(--line) !important;
        background-color: transparent !important;
        transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease, border-left-color 0.2s ease !important;
        cursor: pointer !important;
    }}

    [data-testid="stSidebar"] a:hover,
    [data-testid="stSidebar"] .stMarkdown a:hover,
    [data-testid="stSidebar"] a.cr-nav-link:hover,
    a.cr-nav-link:hover,
    .cr-nav-link:hover {{
        transform: translateX(6px) !important;
        background-color: rgba(238, 227, 166, 0.45) !important;
        color: var(--red) !important;
        text-decoration: none !important;
        border-bottom: 1px solid var(--red) !important;
        border-left: 4px solid var(--red) !important;
    }}

    [data-testid="stSidebar"] a.cr-nav-link.is-active,
    [data-testid="stSidebar"] a.cr-nav-link[aria-current="page"],
    [data-testid="stSidebar"] .stMarkdown a.is-active,
    a.cr-nav-link.is-active,
    .cr-nav-link.is-active,
    .cr-nav-link[aria-current="page"] {{
        background-color: var(--yellow) !important;
        border-left: 5px solid var(--red) !important;
        border-bottom: 1px solid var(--line) !important;
        border-top: 1px solid rgba(182, 175, 163, 0.4) !important;
        border-right: 1px solid rgba(182, 175, 163, 0.4) !important;
        box-shadow: 2px 3px 6px rgba(50, 43, 28, 0.14) !important;
        transform: rotate(-0.8deg) scale(1.02) !important;
        color: var(--red) !important;
        font-weight: 700 !important;
        text-decoration: none !important;
    }}

    [data-testid="stSidebar"] a svg,
    [data-testid="stSidebar"] .cr-nav-link svg,
    .cr-nav-link svg {{
        flex-shrink: 0 !important;
        width: 20px !important;
        height: 20px !important;
        stroke: currentColor !important;
        stroke-width: 1.8 !important;
        fill: none !important;
        color: var(--muted) !important;
        transition: stroke 0.2s ease, color 0.2s ease, transform 0.2s ease !important;
    }}

    [data-testid="stSidebar"] a:hover svg,
    [data-testid="stSidebar"] a.cr-nav-link:hover svg,
    .cr-nav-link:hover svg {{
        color: var(--red) !important;
        stroke: var(--red) !important;
        transform: scale(1.1) !important;
    }}

    [data-testid="stSidebar"] a.cr-nav-link.is-active svg,
    .cr-nav-link.is-active svg {{
        color: var(--red) !important;
        stroke: var(--red) !important;
        transform: scale(1.05) !important;
    }}

    .cr-nav-link:focus-visible {{
        outline: 3px solid var(--blue) !important;
        outline-offset: 2px !important;
    }}

    /* Section Banner System with Aligned Local SVG Icon Badge */
    .cr-section-banner {{
        padding: 6px 0 20px;
        margin-bottom: 22px;
        border-bottom: 1.5px solid var(--line);
        position: relative;
    }}

    .cr-section-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }}

    .cr-section-icon {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: rgba(152, 43, 50, 0.08);
        border: 1.5px solid var(--red);
        color: var(--red);
        flex-shrink: 0;
        box-shadow: 1px 2px 4px rgba(50, 43, 28, 0.1);
    }}

    .cr-section-icon svg {{
        width: 18px;
        height: 18px;
        stroke: var(--red);
        fill: none;
        stroke-width: 1.8;
    }}

    .cr-eyebrow-text {{
        font-family: var(--body);
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--red);
    }}

    .cr-section-title {{
        margin: 4px 0 6px !important;
        line-height: 1.15 !important;
    }}

    .cr-section-subtitle {{
        font-family: var(--body);
        font-size: 0.96rem;
        color: var(--muted);
        max-width: 800px;
        margin: 0;
        line-height: 1.5;
    }}

    /* Tactile Buttons */
    .button,
    button[kind="primary"],
    .stButton > button {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 15px !important;
        text-decoration: none !important;
        border: 2px solid var(--red) !important;
        padding: 10px 22px !important;
        font-family: var(--display) !important;
        font-size: 0.98rem !important;
        font-weight: 600 !important;
        background-color: var(--paper) !important;
        color: var(--red) !important;
        border-radius: 0 !important;
        box-shadow: 4px 4px 0 var(--red) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        cursor: pointer !important;
    }}

    .button:hover,
    button[kind="primary"]:hover,
    .stButton > button:hover {{
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0 var(--red) !important;
        background-color: #fff9ee !important;
        color: var(--red) !important;
    }}

    .button:active,
    button[kind="primary"]:active,
    .stButton > button:active {{
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0 var(--red) !important;
    }}

    .stDownloadButton > button {{
        display: inline-flex !important;
        align-items: center !important;
        text-decoration: none !important;
        border: 2px solid var(--blue) !important;
        padding: 10px 22px !important;
        font-family: var(--display) !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        background-color: var(--paper) !important;
        color: var(--blue) !important;
        border-radius: 0 !important;
        box-shadow: 4px 4px 0 var(--blue) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }}

    .stDownloadButton > button:hover {{
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0 var(--blue) !important;
        background-color: #f0f4f8 !important;
        color: var(--blue) !important;
    }}

    .text-link, .under-link {{
        font-family: var(--display);
        text-decoration: none;
        border-bottom: 1px solid var(--line);
        padding-bottom: 3px;
        color: var(--ink);
        transition: color 0.2s ease, border-color 0.2s ease;
    }}

    .text-link:hover, .under-link:hover {{
        color: var(--red);
        border-color: var(--red);
    }}

    /* Tabs */
    [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 2px solid var(--line) !important;
        gap: 10px !important;
    }}

    [data-baseweb="tab"] {{
        font-family: var(--display) !important;
        font-size: 1.05rem !important;
        color: var(--muted) !important;
        background-color: transparent !important;
        border: none !important;
        padding: 10px 18px !important;
        transition: all 0.2s ease !important;
    }}

    [data-baseweb="tab"]:hover {{
        color: var(--red) !important;
        background-color: rgba(238, 227, 166, 0.25) !important;
    }}

    [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--red) !important;
        font-weight: 700 !important;
        border-bottom: 3px solid var(--red) !important;
    }}


    /* Screen Auto-Stabilization: eliminate layout shifts and running flicker */
    [data-test-script-state="running"] [data-testid="stMain"],
    [data-test-script-state="running"] .main,
    [data-test-script-state="running"] [data-testid="stSidebar"],
    .stApp[data-test-script-state="running"] [data-testid="stAppViewBlockContainer"] {{
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }}

    /* Stabilize tab transitions and prevent jumping */
    [data-testid="stTabs"] {{
        min-height: 480px;
    }}
    [data-testid="stTabContent"] {{
        animation: fadeIn 0.12s ease-in-out;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0.92; }}
        to {{ opacity: 1; }}
    }}

    /* Innovative Pill styling */
    [data-testid="stPills"] {{
        margin: 6px 0 10px !important;
    }}
    [data-testid="stPills"] button,
    button[data-testid="stBaseButton-pills"] {{
        border-radius: 20px !important;
        border: 1.5px solid var(--line) !important;
        background-color: #ffffff !important;
        color: var(--ink) !important;
        font-family: var(--body) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 4px 14px !important;
        box-shadow: 1px 1px 0 rgba(41, 41, 37, 0.08) !important;
        transition: all 0.12s ease-in-out !important;
    }}
    [data-testid="stPills"] button:hover,
    button[data-testid="stBaseButton-pills"]:hover {{
        border-color: var(--red) !important;
        color: var(--red) !important;
        background-color: #fffaf7 !important;
        transform: translateY(-1px) !important;
        box-shadow: 1px 2px 4px rgba(152, 43, 50, 0.15) !important;
    }}
    [data-testid="stPills"] button[aria-pressed="true"],
    button[data-testid="stBaseButton-pills"][aria-pressed="true"] {{
        background-color: var(--red) !important;
        color: #ffffff !important;
        border-color: var(--red) !important;
        box-shadow: 2px 2px 0 #6e1c22 !important;
    }}

    /* Form Controls */
    [data-baseweb="select"] > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background-color: #fffdfa !important;
        border: 1.5px solid var(--line) !important;
        border-radius: 0 !important;
        color: var(--ink) !important;
        font-family: var(--body) !important;
        box-shadow: 2px 2px 0 rgba(41, 41, 37, 0.08) !important;
    }}

    [data-baseweb="select"] > div:focus-within,
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--red) !important;
        box-shadow: 3px 3px 0 var(--red) !important;
        outline: none !important;
    }}

    label[data-testid="stWidgetLabel"] p {{
        font-family: var(--display) !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: var(--ink) !important;
        letter-spacing: -0.02em !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] {{
        background-color: #fffdfa !important;
        border: 1.5px solid var(--line) !important;
        border-radius: 0 !important;
        box-shadow: 3px 3px 0 rgba(41, 41, 37, 0.06) !important;
        margin-bottom: 16px !important;
    }}

    [data-testid="stExpander"] summary {{
        font-family: var(--display) !important;
        font-size: 1.05rem !important;
        color: var(--ink) !important;
    }}

    [data-testid="stExpander"] summary:hover {{
        color: var(--red) !important;
    }}

    /* Dataframe and Tables */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1.5px solid var(--line) !important;
        box-shadow: 4px 4px 0 rgba(41, 41, 37, 0.08) !important;
        background-color: #ffffff !important;
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-family: var(--display) !important;
        font-size: 2.2rem !important;
        color: var(--ink) !important;
        letter-spacing: -0.05em !important;
    }}

    [data-testid="stMetricLabel"] p {{
        font-family: var(--body) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-size: 0.74rem !important;
        color: var(--muted) !important;
        font-weight: 700 !important;
    }}

    /* Alerts */
    [data-testid="stAlert"] {{
        border-radius: 0 !important;
        border-left: 4px solid var(--red) !important;
        background-color: var(--panel) !important;
        color: var(--ink) !important;
        box-shadow: 2px 2px 5px rgba(50, 43, 28, 0.08) !important;
    }}

    /* Hero Layout */
    .hero-container {{
        display: grid;
        grid-template-columns: 1.4fr 0.6fr;
        gap: 45px;
        align-items: start;
        padding: 25px 0 55px;
        position: relative;
        border-bottom: 1px solid var(--line);
        margin-bottom: 30px;
    }}

    .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-size: 0.74rem;
        font-weight: 700;
        color: var(--red);
        margin-bottom: 16px;
        font-family: var(--body);
    }}

    .hero-container h1 {{
        font-size: clamp(3.0rem, 5.2vw, 5.2rem);
        letter-spacing: -0.075em;
        line-height: 1.08;
        margin: 0;
    }}

    .hero-underline {{
        width: 65%;
        height: 34px;
        display: block;
        margin-left: 18%;
        margin-top: -4px;
        fill: none;
        stroke: var(--red);
        stroke-width: 2.2;
    }}

    .hero-actions {{
        display: flex;
        align-items: center;
        gap: 25px;
        margin-top: 34px;
        margin-bottom: 24px;
        flex-wrap: wrap;
    }}

    .hero-caption {{
        font-size: 0.82rem;
        color: var(--muted);
        margin-top: 28px;
        padding-top: 14px;
        border-top: 1px dashed rgba(182, 175, 163, 0.45);
        max-width: 680px;
        font-family: var(--body);
    }}

    .hero-right {{
        position: relative;
        padding-top: 15px;
    }}

    .hero-intro {{
        font-family: var(--display);
        font-size: 1.15rem;
        line-height: 1.6;
        color: var(--ink);
        margin-bottom: 20px;
    }}

    .doodle-star {{
        width: 65px;
        height: 65px;
        position: absolute;
        top: -15px;
        left: -75px;
        fill: none;
        stroke: var(--red);
        stroke-width: 1.8;
    }}

    .hero-photo {{
        width: min(100%, 340px);
        margin: 20px 0 0;
        padding: 8px 8px 11px;
        background: #fffdf8;
        box-shadow: 0 8px 19px rgba(53, 45, 33, 0.15);
        transform: rotate(2deg);
        overflow: hidden;
        position: relative;
        transition: transform .3s ease, box-shadow .3s ease;
        border: 1px solid var(--line);
    }}

    .hero-photo img {{
        display: block;
        width: 100%;
        height: 180px;
        object-fit: cover;
        transition: transform .35s ease;
    }}

    .hero-photo figcaption {{
        padding: 8px 4px 0;
        font-family: var(--display);
        font-size: 0.78rem;
        text-align: center;
        color: var(--blue);
    }}

    .hero-photo:hover {{
        z-index: 3;
        transform: rotate(0deg) scale(1.065);
        box-shadow: 0 0 0 3px #fff9ee, 0 0 22px 5px rgba(228, 182, 83, 0.6), 0 14px 30px rgba(53, 45, 33, 0.25);
    }}

    .hero-photo:hover img {{
        transform: scale(1.06);
    }}

    .sticky {{
        background: var(--yellow);
        padding: 24px 28px;
        width: max-content;
        max-width: 100%;
        font-family: var(--display);
        font-size: 1rem;
        text-align: center;
        transform: rotate(-3deg);
        position: relative;
        margin: 22px 0 0 20px;
        box-shadow: 3px 6px 7px rgba(50, 43, 28, 0.12);
        border: 1px solid #dfd6a8;
    }}

    .tape {{
        position: absolute;
        width: 70px;
        height: 20px;
        background: rgba(237, 230, 194, 0.75);
        top: -10px;
        left: 50%;
        transform: translateX(-50%) rotate(3deg);
    }}

    .hero-arrow {{
        width: 130px;
        position: absolute;
        bottom: -15px;
        left: 55%;
        fill: none;
        stroke: var(--red);
        stroke-width: 1.8;
        stroke-linecap: round;
    }}

    /* Scoped Stats Strip */
    .stats {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        padding: 30px 0 40px;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        margin: 25px 0 35px;
        gap: 20px;
    }}

    .stat {{
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}

    .stat strong {{
        font-family: var(--display);
        font-size: 2.6rem;
        font-weight: 500;
        letter-spacing: -0.07em;
        line-height: 1;
        color: var(--ink);
    }}

    .stat span {{
        font-size: 0.82rem;
        color: var(--muted);
        line-height: 1.35;
        font-family: var(--body);
    }}

    /* Feature Grid */
    .feature-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 35px 60px;
        margin: 30px 0 45px;
    }}

    .feature {{
        display: flex;
        align-items: flex-start;
        gap: 22px;
    }}

    .feature-icon {{
        display: grid;
        place-items: center;
        width: 48px;
        height: 48px;
        flex: none;
        border: 1.5px solid var(--red);
        border-radius: 50%;
        font-family: var(--display);
        font-size: 1.3rem;
        color: var(--red);
        transform: rotate(-12deg);
    }}

    .feature:nth-child(2) .feature-icon,
    .feature:nth-child(3) .feature-icon {{
        color: var(--blue);
        border-color: var(--blue);
    }}

    .feature h3 {{
        font-family: var(--display);
        font-size: 1.25rem;
        margin: 0 0 8px;
    }}

    .feature p {{
        font-size: 0.88rem;
        color: var(--muted);
        line-height: 1.5;
        margin: 0;
        font-family: var(--body);
    }}

    /* Category Cards */
    .place-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-top: 30px;
        margin-bottom: 45px;
    }}

    .place-card {{
        min-width: 0;
        position: relative;
        transition: transform .3s ease;
    }}

    .place-card.lifted {{
        transform: translateY(20px);
    }}

    .place-art {{
        height: 190px;
        border: 8px solid #fff;
        box-shadow: 0 4px 16px rgba(59, 48, 37, 0.12);
        display: block;
        overflow: hidden;
        position: relative;
        margin-bottom: 16px;
        transition: transform .3s ease, box-shadow .3s ease;
    }}

    .place-art img {{
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
        transition: transform .35s ease;
    }}

    .card-kicker {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: var(--red);
        font-weight: 700;
        display: block;
        font-family: var(--body);
    }}

    .place-card h3 {{
        font-family: var(--display);
        font-size: 1.22rem;
        letter-spacing: -0.04em;
        margin: 6px 0;
    }}

    .place-card p {{
        font-size: 0.85rem;
        color: var(--muted);
        line-height: 1.45;
        font-family: var(--body);
    }}

    .place-card:hover {{
        z-index: 5;
    }}

    .place-card:hover .place-art {{
        transform: translateY(-5px) scale(1.075);
        box-shadow: 0 0 0 3px #fff9ee, 0 0 22px 5px rgba(228, 182, 83, 0.65), 0 13px 25px rgba(53, 45, 33, 0.2);
    }}

    .place-card:hover .place-art img {{
        transform: scale(1.075);
    }}

    /* Workflow Panel */
    .workflow-panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 38px 40px 44px;
        transform: rotate(-0.4deg);
        margin: 40px 0 50px;
    }}

    .workflow-head {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 30px;
        border-bottom: 1px solid var(--line);
        padding-bottom: 18px;
    }}

    .workflow-head h2 {{
        font-family: var(--display);
        font-size: clamp(1.8rem, 2.8vw, 2.6rem);
        margin: 0;
    }}

    .workflow-head span {{
        color: var(--muted);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-family: var(--body);
    }}

    .steps {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 30px;
        margin-top: 30px;
    }}

    .step {{
        position: relative;
        padding-right: 20px;
    }}

    .step:not(:last-child):after {{
        content: "→";
        position: absolute;
        right: -16px;
        top: 10px;
        font-family: var(--display);
        font-size: 2rem;
        color: var(--red);
    }}

    .step b {{
        font-family: var(--display);
        font-weight: 500;
        color: var(--red);
        display: inline-grid;
        place-items: center;
        border: 1.5px solid var(--red);
        width: 32px;
        height: 32px;
        transform: rotate(-7deg);
        margin-bottom: 12px;
    }}

    .step h3 {{
        font-family: var(--display);
        font-size: 1.15rem;
        margin: 0 0 8px;
    }}

    .step p {{
        font-size: 0.84rem;
        color: var(--muted);
        line-height: 1.45;
        margin: 0;
        font-family: var(--body);
    }}

    /* Plan Cards */
    .plan-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 25px;
        margin: 25px 0 35px;
    }}

    .plan-card {{
        position: relative;
        border: 1.5px solid var(--line);
        padding: 26px 30px 28px;
        background: rgba(255, 255, 255, 0.7);
        min-height: 270px;
        box-shadow: 4px 4px 0 rgba(41, 41, 37, 0.06);
    }}

    .featured-plan {{
        background: #f1e8b6 !important;
        border-color: var(--red) !important;
        transform: rotate(-0.7deg);
        box-shadow: 4px 6px 12px rgba(50, 43, 28, 0.12);
    }}

    .plan-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--line);
        padding-bottom: 12px;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    .plan-top strong {{
        font-size: 0.75rem;
        color: var(--red);
        font-weight: 700;
    }}

    .plan-number {{
        font-family: var(--display);
        font-size: 3.2rem;
        line-height: 1;
        margin-top: 16px;
        letter-spacing: -0.08em;
    }}

    .plan-card > p {{
        color: var(--muted);
        font-size: 0.8rem;
        margin: 4px 0 15px;
    }}

    .plan-details {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px 18px;
        margin-top: 15px;
    }}

    .plan-details span {{
        font-size: 0.8rem;
        line-height: 1.4;
    }}

    .plan-details b {{
        color: var(--red);
    }}

    .plan-tag {{
        position: absolute;
        top: -15px;
        right: 25px;
        background: var(--red);
        color: white;
        padding: 4px 12px;
        font-family: var(--display);
        font-size: 0.72rem;
        transform: rotate(4deg);
        font-weight: 600;
        box-shadow: 2px 2px 4px rgba(41, 41, 37, 0.2);
    }}

    /* Badges without emojis */
    .tag-synthetic {{
        display: inline-block;
        background: #ede8dc;
        color: var(--ink);
        border: 1px solid #c8c0b2;
        padding: 2px 8px;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-family: var(--body);
    }}

    .tag-status {{
        display: inline-block;
        background: #e9eff5;
        color: var(--quiet-blue);
        border: 1px solid #b8cbdc;
        padding: 2px 8px;
        font-size: 0.74rem;
        font-weight: 600;
        font-family: var(--body);
    }}

    /* Focus visible */
    a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {{
        outline: 3px solid var(--blue) !important;
        outline-offset: 3px !important;
    }}

    /* Responsive */
    @media (max-width: 900px) {{
        .hero-container {{
            grid-template-columns: 1fr;
            gap: 25px;
        }}
        .stats {{
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .place-grid {{
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .feature-grid {{
            grid-template-columns: 1fr;
            gap: 20px;
        }}
        .steps {{
            grid-template-columns: 1fr;
            gap: 20px;
        }}
        .plan-grid {{
            grid-template-columns: 1fr;
        }}
    }}

    @media (max-width: 540px) {{
        .stats {{
            grid-template-columns: 1fr;
        }}
        .place-grid {{
            grid-template-columns: 1fr;
        }}
        .place-card.lifted {{
            transform: none;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        *, *:before, *:after {{
            transition: none !important;
            animation: none !important;
            transform: none !important;
        }}
    }}

    {reduced_motion_css}
</style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_sidebar_navigation(active_view: str) -> None:
    """Render real link navigation with aligned local SVG icons and page-level URL routing."""
    active_norm = active_view.strip().lower()

    # SVG Icon Definitions (stroke 1.8, 18x18, aria-hidden)
    icons = {
        "overview": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "discover": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
        "planner": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/><path d="M12 19h4.5a3.5 3.5 0 0 0 0-7h-9a3.5 3.5 0 0 1 0-7H12"/></svg>',
        "compare": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        "datasets": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
        "insights": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "devlab": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2v7.31L4.1 20.1A2 2 0 0 0 5.8 23h12.4a2 2 0 0 0 1.7-2.9L14 9.31V2"/><line x1="8.5" y1="2" x2="15.5" y2="2"/><line x1="6.8" y1="15" x2="17.2" y2="15"/></svg>',
        "model": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "settings": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>',
        "information": '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    }

    groups = [
        {
            "name": "EXPLORE",
            "items": [
                ("overview", "Overview"),
                ("discover", "Discover"),
                ("planner", "Planner"),
                ("compare", "Compare"),
            ],
        },
        {
            "name": "STUDY",
            "items": [
                ("datasets", "Datasets"),
                ("insights", "Insights"),
                ("devlab", "DEV Lab"),
                ("model", "Prediction Model"),
            ],
        },
        {
            "name": "HELP",
            "items": [
                ("settings", "Settings"),
                ("information", "Information"),
            ],
        },
    ]

    html = """
    <div class="cr-sidebar-brand">
        <div class="cr-brand-title" title="CultureRoute"><span class="cr-brand-full">Culture<span>Route</span></span><span class="cr-brand-mini">CR</span></div>
        <div class="cr-brand-subtitle">DEV AAT · Cultural Tourism Study</div>
    </div>
    <nav class="cr-sidebar-nav" aria-label="Main Navigation">
    """

    for g in groups:
        html += f'<div class="cr-nav-group"><div class="cr-nav-group-title">{g["name"]}</div>'
        for key, label in g["items"]:
            is_active = (active_norm == key) or (active_norm == label.lower())
            if key == "devlab" and active_norm in ["lab", "study", "devlab"]:
                is_active = True
            elif key == "model" and active_norm in ["model", "prediction", "prediction model"]:
                is_active = True
            elif key == "information" and active_norm in ["information", "info"]:
                is_active = True

            active_attr = ' aria-current="page" class="cr-nav-link is-active"' if is_active else ' class="cr-nav-link"'
            icon_svg = icons.get(key, "")
            html += f'<a href="?view={key}" target="_self"{active_attr} title="{label}">{icon_svg}<span>{label}</span></a>'
        html += "</div>"

    html += """
    </nav>
    <div class="sticky" style="background: #eee3a6; padding: 8px 10px; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; font-size: 0.70rem; line-height: 1.3; color: #292925; transform: rotate(-1deg); position: relative; margin: 8px 2px 4px; box-shadow: 1px 2px 5px rgba(50, 43, 28, 0.10); border: 1px solid #dfd6a8;">
        <span class="tape" style="position: absolute; width: 36px; height: 10px; background: rgba(237, 230, 194, 0.8); top: -5px; left: 50%; transform: translateX(-50%) rotate(1.5deg);"></span>
        <div style="font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #982b32; margin-bottom: 2px;">Study Data Boundary</div>
        <p style="margin: 0; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; font-size: 0.68rem; line-height: 1.25; color: #292925;">
            Read-only SmartTrip & WanderMatch packs. 45 Indian cities. Zero external network calls.
        </p>
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)
    st.markdown(
        """<iframe srcdoc="<script>try{window.parent.localStorage.setItem('stSidebarCollapsed-','false');var f='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAABiKUlEQVR4nO19B3wc1Z3/703ZvqveJctVcgc3mg3Y2KYmJEBsekhCyYWEyyX/Sy4dk3K5JJdLgZBCCmBKYoc0AqEZG4wB996rLKvX7bvT3v/ze7OzXkkr27Ila8W+Lx8jacvMm5n36w2Ag4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg2PEg0AWg1K8fjrcy+AYZhBC+Cb4oIJSSlasWCFSiv9WS3T1wxKlDwuUUmG418aRGaCUCuaeMPfIarZH8Hf6gReQEnzAYD60lQJAEQFYYxBCDADQ+37yEUDGsGSJy9d9rI0GBNsH/mFznITPcNHcPJlAIBIjhERPqSWuWS2ugTUwfw0Y5JFHcD99YPCB2PTIvQHm4z+L4E++17kixx8yamS7WKXr+jRV03MlSbpA1zR8tGWSJJWqmv7BuBEcZwzU+SVRAF3TQxTgoN0mk3hcOeZ0OuriilJPDeOQlGvb6/MtbetrNq4WV65so0uWLDUIGdk2JBnJkn7NmmXi/PnL9FQbrrt7RT4JafMEUbpI1dRLCAgXSJJQ6HTaQZQE9uQtgsefqqqhDTi8F8MxPKAUBFEAu01mVCyKAgiCAIaug6JoEFcUPwFhv2wT31U1fYdsF1a58pce73mI1ZKpaY5MzYCMSGm/BgSy4BHNei3WvmKybgiLNV1fQCidZ7fbCmx2mRF3LKbgT3y++IBoz+tGyv/g23kcpwAhFKWJ+Suh1q/4lyQJgt0uMwZhGAaEwrEIpcY2QZRekwh53Vm8632L8NFnACsByNKlaczNzAUZWWr+FEKIeYODzc+VSJJ0varC7YTQBR63U9J1HSJRRvD4UIzE9QmEi3iOs9pzlBICBqVMcBBRFESnwwYoXKLmPtshy+JyTVH+6au4c1/iOwRWrhRGCiMgI47wm/44VRCFezTNuNvndZWglA+FY3jjUSPgBM8xhHsRKCGUMQRKQXS77MThtEEwGImLorjCMOhyb+nS15P7duUUkumMgGS6N98i/I6mP061EfJFSumdXq/LFgxGQVFUtP9RdRPO+lpMlY8j64DbhZpW4FmCUtQyqSEIguTzuUBVNNB1/XWDwo9OMgLcx8tIpvoIMpIBoD2VJPzjf5xqs5EvUqB3elxOW7c/bEl78YxVe8ayEz9NW4+9TAQCRBLMFzmyDwSA6gahOu0pDHB/MC/AGW4vRueGQUAgPq9T0HUjDSNgezrVD5URyCgGkEi8QLo2mg49Xez12L9BBOHTDofN5veH0RGjC+imPd26Ezoau9UCAUESqeSQKREEECSB6oqGihzBn0p3xBQCGfVYOIYcGL8zDJA8DrB5HQbT6W0ykxSGprO9YSg6wc8woLA4A4ZAKdXx4F6vQ6AGgKKq/1KU+JcLRn18F76PuSdLM8gsIJko9YNNf7yNCMKPXU57efeZEj7SOz4sQkCQRSo5bVQQBarFVSHWGiCh+k4IH++ESEsAuuraQQnFQImrEGzxh4nAormcBWQTCBCqG4Yj1+3y5rkF3Df540vAme8G35gicJbngrsyDySXXQdKiRZViGEKDqY5ns50MBkBEJ/XJcQVTdEN4/tb9u357oIFj2ipe324kREMAGOphCzQ6vb+trwgz/tjh8N2WzSmoo2PQXrRVMj6+a7BFDAkepA9DsPQDIi2BoSuXSegddMx6DjSCoGm7ogWjjeJHke97LS1e0flNzhzXCHR61BHzR3fpCo6TwvOQkgOm96+43h+6HinTzUMqXt/c7UeV3PigehoIgnl3tJcX0FVARTNqIbCmdXgLs81RKcNtEic6HGN7UnGDE7DCAghYl6eB6KR2PpIXPt8YdUd6xOp6HS46xBIpqj8HcefvcYmS39wux1lXd0hHWlaQMl8KsLHh4iS3i7RWFtQaF57AI6/uRfaDjXHtbhW5yry7iycVnVg1OW19aWXjuvOKSqJAuSqZmawLaHbRTnxZzVsFECkADrbiwBhMRptdTSvP5JTv/ZgaeuWY+MDJzqnAIHavMoCz6h5NVCxaDJ4RuUbaEZqEQU1CSBi/9vIdD1R3eN2SJqua5phfCmn9LafsvdWrBCHM1IwbAwAOaCVtutveH6ZzSY/rBsGxOOqRgiRTkf4sseOt5V27W0UjrywGeo3H1X1uLo9v6Zs07gbZ+ypXji5zZM/LgQgoCVGAIJyV32zK3Cszd1xqDU/1tLtjfijnlBde1VGumc5hhaCuTMcRb72nPK8VnBIWsWF1U1yoTdeNGVUQAKvCuBkuSQaNDmPvLar4MjL28a3bjo6i+p0ZnFNac74W2ZD0ezRVPY4qBKICqdnBEwbEPJyPSQcjq04Xtfy4OSLH+qwNOCsYQCWDVRX92xevl1+3uNxXNPVFcL4KjPhT0v4ALRl3SFh7/PvQ+uexg5Pee7qCUvmvDflk1cct4NPwTNoEJFaNh7Ia3j/SEX7rvpxwUZ/dawjNEqJxosMVXeLBqpgBAQeBsxqUFYQTsAgAIIshES7HLDnuurdJTl1+bVlR8ovGVdXNm9Cu8teHDMN/5h4+LWNJbueWjuzbXfDNb6y3OqJt8yBymunUpvXAWowdkqNwNIG8nI9UiyuHAwHYncWjbt743AxATJcxF9/6PcT8ryeZ90e55zOjoBKCJH7+46hGyA7bUBk0Whad1A48Ox70LT7RH3JjOqXZnz+mo1VMyd1Akh6HPxy6/ojeUde3jmxefPROeHm7il6VC0UE8wDKzfwQZsPPfnss9D5R4B5VhL3BT3c+DtjshnhFTqPoIBGOAv8sV/wdmDFDzX3C9jEkKvQs79watXG6qun7qqaP6nF5cpT8CZ2NZ7wbH/sjUlH/rX9w+4i3/SJt14Mo66fbsgOiSiBGDmVs9AwDM3ndUmKonaFI9rtJWPvfHX16tXSggXnlwmc18dtcbnGw8vn5Hodr4iSmB8MRjVBSK/yM48rWml5bqPrYLOw91dr4Mhb+7rKLhn7p8u+ffO7hdWjA/gxf1uja9/z62vqVu25IlTfMYPGtHwWzhFMgkcGbx4wec3Zts2TwE2JjlI1HMeQKNughqqDaJdBckhJTStLQc08EbZTMDIoCBSImAgpG7IYdRf7dlfMHb+mZuklu8qmjOsGEEFRuu3rvvfitIMrN95WNK54/LTPXgVll00w1FBMwHvbnzZgGNSQZVFwOe0Q8IcfKBh91xPnWxMgw0T8r1KAvGg0juE9Me3ndQMdfCj19YPPvS9ufWKN4SrL/dvcZTe9Ouriqa14xNZDx3xbH31jbuvmYwtiXeEalPS6SfRGItErq4k9HfFrcQ1sbjvU3DQLii8chTkS0H24FQ78dTP4j7VhJIXde44kkloiweJBs/QHRI+9MX9i+bopn7x81bgFF7YAyLSrqcG77usr5za8e/i2STfOyJ3y2asMu89JlECU9G8SUEMUBep2OcRAKPxAQdX5ZQLkfKr9PYg/FtcF0j/x23JdFDfmth/9izTtrD80/TML/3DxZz+6ByAK/rZOx/rv/fPKpvcO3qAHYlWoqulC4kFxok8PJumR+B2w4Me3QdlF40CLoibLEmAg0uqHVV94Htp3nwDZbc92TaA/MM0AfxEYM6AAdtlfOLXitRlfvPaVqpkTOgAkcvjtLaVrv7TibofTdtnM/7wWKq+caMS7w0JqFmoqDINSSRIMxgTOsyZAhoP4I9G4IZqJPb0+a6pa9jy3ceyl7cKGH74ErrLcP1/71AN/zSnMjcZBJTt/tXrS/uffvy3eGpqKgRtDBCOh2vNwXn9IyXRc+NM7oWzOGIh1hpOqKTJcJHolGIVXHngSAvWdINklq0qWIz2YwCEGCDKaqh5706hFU1Zc+vUb1wkep24Hibz60O8vr3tt573T77ncM+XT8w1d0QRD0dKaBKlMoMsffqD4PDEBcj5CfU3Hnh7jczo2AyH9E79BQZRFEJ02fcuP/iXuWbm+u/aOy365YNmdGzUtRJp2nchZ/52/Le3a17RYoFTURMJyBU6VJMRxUvVXgjEYvXgqLPjRrRDripj2fwrQVnUWemHXU+/A+h+9DPZcFzcFzgwsiCAYIKKId5b6tk39t6uenrz04mMSOOmev6+rfufrKx8sn1ZVc+n3P6bbfE5RDcb6ZQKiSAyf1yW2tHcvKR/3iT8PNRMYMuKxGio2NDydnyM6XrHZ5dnBYCStzW/a+zKoEUXf/N0XxaPvHjxy9W8++cOqeVPaADS68eevTdv39LrP0HC8VDXzAlHqc4l/hsDNFu8Kw8yHFsOFD8yHONY/9NqAyIBltw2aNhyB1//9GRZ14WbAmcOKKkkYXhaFaOVVk5+e/+PbXkcnoaGq8orFP7jf47RfNee7Nxv5NaVC3B/tw4TZcSg6BiVsV+b3B8PXlo37xIbUnJnBxlASES6auqj8R4/PhcSv9Uf8okMGNarob332GbFx54m3PvbKfz5SfklNuxoKia8+8PuP7vr16oe1qFKqSsTMmOLEf1ZAKX/az2AvFa75DxgJTVTQRGLolDobXtv16X/c9OiDnfsbPbJTUu5651u/Inmu5W98+kmhfVeDYc91Unavex+HEAHbkRFC8txu54vNh58rMfkC9sUYfAzJQU21hehtdcuX5eV5FmGcH2um+yN+Labqbz34jBgKRlZ/Yv13H/UU+iKdR5rdL97+iwdb1x74uEGA6KaDL63TkOO0DwQEWYLWbccTUr2v4mdqYXb2GcYoeJ/EswNF/yBQVSRG6FDLVa/d//tvHfj71kotrho3r/jmn4tmj3li9UPLhfadDbQ/JiAIRAhH4prLYS+22eAZImBWwjIyIhiA6fRboDUffnqx1+18uLs7pKdL8sGNKDHiV/S3HlzOiP+Otx9+PBoKCq37Gn2vfeK3D4cOtc1XTKmfqNDmOKtnguq9ywYtW+tg38oN4Chw91Dv8XdHvhuaNhxm4UAzCsBDgecApg3g3lW7I2Pf++Zf/3vHk2/XxuNt8od/+7mXC2ePeWJNChNIF3bF3Bh/IKzl5XkXtR1bjh1FdLMB6eBiUInKUlOam8cVuqlthyAKxfG4ihVPPRgNy7CQRNCVk5IfiV8NhUn7oVbPmw8++U2tKzpGlUAnXOoPaiRAi6pw8X9dD7W3zAYtorDMF2TEbTvrYc2XV0A8FDMjADwMODgwHYSCIIqRqQ9d9b1Z98/fJ4Hb+Me9j97QsfnYfVf94m49f2KZoIbiaXMFMMLtdNiFYEhZXDT69lWDXUo8yAyAignVf0VBvm9JZ2cwfaIPSiSfU3/3//1RPLGzfu2nNnzvZyj5U4lfk0DnKv8gI9H5JO6PweTbLoaL/vM69nL73gZ49dNPsbexrJoT/6DDwLyBJBP45Px9kpSn/+XuH9wYP9bxqcVP3WdITpuZNdirvBizBV0uu6Cq2mHF75hROPEj4cEsIx40E8DkTERvrVu+ND/Xu6S7O9yv0w9TezHUd/S9g0du+su/PxGJhEknJ/6hB+a4Y4ckWYDuo20nQ4T+KOiqBqKNS/4hgoDZqYauu3Y9+ubXN/9hzcR4vEO6efnnX1Il4c13vvhHgYiCzoi/V+6F6Q+I6T6faxxxhv4nEQ0YNLoVBi/kt5t21z2bZ5ekRyNRhWn5/WX4HXtpO9n95/X+6357/w9cpb5IqL7T+caDT32DS/7zl8sm2U+6ZYgkMEbAE3/OFxNY9fW9f1o/Nh4PkztWf+OXbcdadu346WuiLceFPQb6fFEUBLGrK6h7vc4HO+uev9z0B6wYFIf4IHES7N77iKGB8R2vz1UcjyuYnSv0cfo5bRA42mZs+OFLZOLtlz1eftn4diOmCau++Oz9eld4LNr8XO0/P+hB7MkEV44hhmAIYFDNcG1//I2H2nc3+vR4FBY9ds9ju17Y4D/2z23EluNK6xQ0DFagiEf46YEDP7MDLMFHSIadAZitjZYYbSdW1Drstk/7/RFsk5z2uIIs6lv+52XRXur764Jld2yQQDDe+MKzN8aOtF2OMX7u8OP4wIOCoIug6/5o1ZqvPP8ZXQcYM29y68RbL3l8809eJdFWvyHapbSmQCgU1fPyvDPz7UW3mabAuU+4HgQNYCW29KKgKV9zuRw4nadPoBk5mj3PZRx47n2xYefxYzc98+BKTQsL63/+r+kt7x66QxUJSn6e2ceRHaAgosCL13fPWfX55R/RQIcF375jI3XKb2z78Wui6LSlNQWQ0KJRhQoC/eqBAy/bAZadsxYgDJb0dzpttwYCfaU/y/F32qj/UCtse2K1duGDi55w5vtiLbsafLuffuezlBVW8bLd8w3cOfhsWP0VL/89/6CYNQgGCsCtv35zEkAcrvv1J589/NbelrqXdhD0lfV+LhhOj0RiRm6Opzbf3n2bOWzk3LQAYdCkv9Nu19JIf4Rok4zdv1wt2EpyX8KSXuR47y77yx0QVosNwjp0cul/PsF64Esgu7AJiAC2HBefkHT+Ydr0FIRdT71zf1d9p7N44rju8TfNenLHE2tIvDNMMSTb2zeDBBeLq1QQ4KuUrrCxoPo5aAHCuUr/9sbnJzmdcr/SH3v4Nb5zQDj81p7u+d+55SUABbY9vmpy98Hmq5ADcuI/z8AeuHYZug41Qd2q49CyJQB7n1/HXuOOwPMOQRdAp13R0e9852/XIG0s+P7HNgc7QzsPPve+YPM6jd4ZmSe1AHdtd4N+h5kPcPZawDlI3jWs2Idq+n1ut9Ou4/zk9IlF9MCz75HSSyesqLxoWmuorcO++4/v3S1Q1ouZXdPZr4HjbFR/yWGDrgMNEKgjQLVK2LdyPYgyr/8fJgiaALRlw5FbDr66rUwEhzrr3695ev+LW7VQQycRbH0dgthURNV0qhv6ZxMv0fPKAMy4/3w90LiiSBbEu4LBKC5A7C39ceQSdu9t3HWi6cpHblmLL6/77t8W6G2hWk3kqv+wAZM0bBLYvHZwl+aBI9fNcwCGD4QKYAhx3b3pZ6/eji3sZ927+LBOyHtHX9hMbF6n3tshiINGQqEodTsdM9vqn7sKD3G2eQFnqQGswaw/qunGdTm57mJFUY10gzpx4Xufew9KZlT/I696TKD94FFfw3uHbtQJoWQQYpgc55oVKIAWjbMsQI5hBAURzeHQ8Y5Lty9/Zxx2uJ72qXkv7ntpmxKq7xDSaQFo+zscNkGgxj1mE9MlcB4ZwHwcpoj6/z2qomFecq+lYdKPzIZ2NO9p9M/8j0UbcBrPxp+9cgUElTJDZJfDHX/DBHMQpg3ya8aDsyAP7D5vcq4ix/CAEqCiDtKe59+/UYOgNOf+qw+rcXVP09sHiOy2pwsLisFQlIqCcF1j44oiMzvQbMIzEAhnU/GHSQjtx56rtcnyFaFwjKkkPT9DQXTYDJzY4y7LebNq5tROf3Ojq2VL3ULWpptnnWXIdFwK7uJCsHk9OBF3uFeU3aAgqALQ0Imuiw7+c3s5gEsbvXjqK/v/thmHjfTp4IQaN2reOTnuIqdhfMh8dc2AzYCzkMLz2XeIRK71eJxSYgpqyoWYgzpxQGf95iPKxCUXvwNg1/atWF+j+SOjdYF7/jMBqLURVpKtYMsqczgIx3ACk+cNUdXtB/+y+VIkpFmfvXpXd3PXia49jYLk6qsF4DPUDUwX0D9ivtJGzwcDYOo/AbpQwzzG3ll/rLecw2hZe4AoUXXP9Hvn1wF0y0df3zUf66K5/B9m4KZRVXAW5kPOqApmCrhLioCyQcycCQwn0C+GRTQdexquaD9yOCevamwwb1Th23X/2oENc82srZ4QYlEFhzzN6exckYN9AgZqBgyIATDCJ8Q4duzJHAIwL8r6yvc6hqla0rrVe6FwYvl6CXKUuvcOFIROdM1MDOHmtn8GAB2ACJvbA+7iIlML4BhWoF8MNWQtEKs89Lct41Gcjr7+gm31G4+o4aZuwUwMOskEkBjjimq43c5yEtZnmK+uHBB9DZAYzYPnyM7L3S5HjqpqPb3/pvpPoy1+sfVgkzL2wxfswRcP/2vnRIhrOWxiD4/7ZwwDwEdnUB00ReEOwEwBOgMphRPvHpwNoAqTllxUHw9FTwT2NxMJawT6KvmGhKZc0g8wsGjAABlAESN2w9Aus9ll/L1HmhJrL+W00c5dJ3AEVd2YRTjCKyK1bDp6EZvCm5WDODMLzG6MxyF3bDU4CvLNfoC5OTwPIJOqBQUCgePtM1v37s/15FdF7PnePc0bjzLhmsYMIJqGPcfgkuQRho4BzDcefvhhQSBkjmq2mO5pb6AGIAq0ddMxcBf5dnjyx4Xq1+8pCDf7p+JF8Yq/DAG1NAAAQRQhf+J4oLrOfQCZAdYBWw8rpUdf3zMawKGVzR69vXlbHQ50JUjpvSDE4gp6EGsb9j1biCb6QPwAwkDt/4ceGu8BSi6Ix9W09r+uqKTjaCstnFZxALsXNK4/UoHqP2vrzdX/jAERT0aMDDQBODIGaJmJBiWt2+snAESF6gUT60PtoWC8PSQIstBDC0CiRFPc6ZQLnV554kD9AAPRAEz1PySPdzikXFVl3X772v/NAcHf2B2tnFt7AtMaW3bWjxcMnGzS01zgGB4wu1/ToHhKLYsAUGowE8ByCnJkACgQjLMFjrfVYgStct7ETl3TGgOHW7GVW7rObYYNi7l0bUaqqX4mGMBTX8kOKovGWJtNlihNY//bZRo+0QlKKNZWeumYboCwFGnorj7zc3CcXw0AmYEO+bXjQJBl7gfIHBBU4uP+aGX7/maP01MWE+3y8e79zTjgJZ0fgMGgtHagJxoAAzC5ik6NKaLE1EfaJ4YhiTR0vBPsXufRvJKqsL++0R3rCldjbDMxtpsjI00AjQ8CyTDo2KclphU0bT1WBODWcqoLD/tPdJjNW/rmaxBdM/DlSeaf840hYADzGcETgeSm7x6LHIBApMWPacAdAD6t/VCzV40qhSz9l9v/GVUHUDSlBgxdY6qbzesGyY7mAA/SZAgIGz2uGTb/sY58ANHwlPo6Qy0BbCucTpASVo1PwGtOD1p2xicaiOFnNjAx6CzkNn0ImmWYaaSrrh1yq/NP4Ef9R9pyQTdkLHQYwHk4zpMGwEKCqgq+UZXgyMtlvgFeEJQ5QAILNXQUAYTEwqkVbaGOUFTpCBNB6ukIxI/GFA0EIDV79x7PwVZhZxoJGLDnhwDE+s8YpaCE4mDzOSMANiPcEsghOsW2RTwCkGl1AClOPwwB8lmAGQbUACiFcEeoCP90leZG1UicGppO0jFpc6YI1UiROqCQzhkxgAQ3ocePr3ASIJXpcgCYNIlpRIurus1jjwPoRA1FnQNZDMcQIyHxHYX5LBFIi8eTzID5BLielnEw4poTQBHsHgc2bYhqEbXP+DCEphnUZpNdRSF3pfnKssHVABKzyJCgK5XeDACbS0gCVbvCxN/ij5XNHd+M8cvuo22jeQZg5iFJ9BgFSGEIumIyBI7MCQVG2wKj45EOe8W8mm49rjeH6zuxoWsPdw1L0DEMardLThBoggFMGXwTgFIVfflqv3sENxaLMyfsD3OOGUeG1gH0MQm4BpB5SNCQrhnIr0k66W/BwBb8AhlQVddZZH9wEfGBqAMozGfmgPU4U8OCHCMZA6NPnv6VtXUA5OTgFhHDgrUsCsBNgOwCZwBZiHTSXpSkYVkLx/CCM4BsrQMQE4k/CYXRMLs7cWQZOAPIcg0AmQK2dcyvGQeCxIeDZBs4A8hC9DYBKFCw5/q4IzALwRlAttYB0J4OP9YTsNccOo4PPjgDyEL0NgEMxawHsPN6gKwDZwBZhnRJP1hiavO4QXLYeUVgloEzgCycB8DSfhN1AOZ7wKIDzAzgeV5ZBc4AstAPQIjQa46DwcaDuYr5gJBsA2cAWQRG6B43CLae7b8wBwAZgLukkA8IyTJwBpAlSHX2OfL7Nv/AngBaLM5NgCwDZwBZBmbn077hPkGUwFdVwbQEXg+QPeAMIIuAar8dW4D3nOae8AuI4Kss552BsgycAWQJWMqvrkNB7XgQhPQpv9ghiCO7wBlAlqG/KUCYDuzAdGA+ICSrwBlAFgGJG3P+kdh7vG4VBPEBIVkHzgCyBKjy4/QfJHIk9nSOPj4gJPvAGUAWAT38SOT9vccHhGQfOAPIIg0Ap/8gkfeeAdAjR4AXBGUVOAPIBiQ6ASFxI5EjsaczAfiAkOwDZwBZBEz5xWnA/YEPCMk+cAaQZXUAkiPNENBeE4P4gJDsAWcAWYAzbfrBB4RkHzgDyCL0VweQCj4gJLvAGUAmAaXyEDXk6K8OIPV9bBVePJQDQobw+jjODpwBZAqYmo5deXQgonDe6wCSnx2iEWF4TXhtLA+BM4GMAWcAGUT8ueOKwVXogVhXGARJGHRC6a8OYEgZACHsWvCa8NrwGjkTyBxwBpApIASUYBQu/fqNMHrRFIi0h1jIbrC0gf7qAE6enrBW4dgyHFuHn0pLGJDU13R2LXhNeG14jVwDyBxwBpAJQPvbLoH/aDscfWUHLH7sbrj8kZvAmeeGeHcEcCT0qcZCD0YdgAWcDnSusNaLa8drwGvBa8Jrw2vEa8Vr5hh+8ImQGQJsze0o8MCBv22B0jljYdonLoeyi8fB1sdXwZFXdoIgiSA7ZTB0Y9DrAFLBZgSeA3EKogBqVGWSf9wNF8CMBxdC4aRy2PP8++za8BrxWjkyA5wBZBBwVLfklGHL46ugdNZocJf44PLv3AJjrp0Gm3/+OnQdaAabz8mkK352MOoA+ssV0KJR0x9whszAWhPa+nk1pTDr3xdD5dwadr7OA83smvDaBrJujqEHNwEyzhSQIdTQBbueXgeiLEI8EIWqy2vhut9+CibfeRmTnmpEAYJOwkGsAzhttuCpTiEJbE24NlwjrhXXjGvHa8BrwWvCa+Oqf2aBM4AMAxKR3eeEfSs3QP3aA+DIcTJbWrRJcMlXboBrfvUJKJxSAbHOMPv8mToJT1cHMNDPpZ4b14JrwrXhGnGtuGZcO14DXgteE1f9Mw+cAWQiWL4MgS2PvQFaVAVBFhnxIFFZhDbzwYVMSqvBmEmIp3DsnZFkH4CmgJ/Fc+K58Xi4Fosx4RpxrbhmXDteAzsOz//JSHAGkKm+AJcNOvY1wa7l65jdj68xoovEGYHN+MxVcP3v74OKuRNMousnZNi3DgDHf7Gz9PlHqZHwFXj69xWIAjsXnhPPjWvAtZimSdx836Bszbh2vAa8Fm77ZyY4A8hQmB16HLDrqXXQsuUYSG67yQQSTTuRAHPHFsNVP7mDqd2yxwFxfzRtyJDF43UNAB1wRAJCZCDE1uufzN7Dc2DCEHrzU6V2MrTnj7Jz4Tnx3LgGXIv5GZP4ca24Zlw7XkN/zIRj+MGjAJkKpFUm8WOw9Ver4erH7u7xNr6nRRWm+U++41KounIiU7ePvLwDBJvEPO7WcRR/BCS7C4iIan4ADECHXRAtftPeANQuPADUBoKnFFzFJRDtDIHX6WTnwU+oUQUMRYdx10+HmZ9bBN6KPFACUebT66154OdxzVpcNRkAD/tlLDgDyGCwsd1eBzS+f4g50tDDHu8KJwnOkvQxTLjJd8MV3/sYVF5eAzueeAu6Drey9yWXHaoXToXJt0+DSMfboEb8AMSK9Vv+gESRDkVNwQOTbpsIWuwyaFp/lDEClOp544ph+v1Xwthrp4MeV9k5UUtIdRMwB2aeG/Y8+y5bsz3HxYk/w8EZQIYDiU922WHbr9dA2Zyx4KvKBy2u9VDzkRB1VQcdJfR1F0DFpRNYAhFKbdQO8ieUAjU0UEIdiWpAieXns2NQkw2Ynn8KSjgAvlEuuPK/l0KwoQv2/3kjKOEYzHxwEThyXSy0h/yCmQi91ik5ZJargGvFNXO7P/PBGUCmg6XxihD3R1gy0MKf3gEQ75vRZ3na8XOYaos2uunZ11n+PWYS2nO9TD3HbEK023VWmWd+15GHU4NFNjpcDceZ5EetYtbnFzMOgR59PPapwo64Tlwjfo45Lrnqn/HgDGAEmQIn3jnA0oIxxZbVCKTz+ie89Iqqs+9hTB7Tb+PdYahbtRuaNx+DQF0HhBq7QQ3HTOeeKIK3Ihc8ZblQfGE1lF88FjwVeaDFVIh3WbUIQr/Ez1T/XBccfmk7WyO3+0cOOAMYIUCTHSX05kdfh+ILRzGJjYSeNv6PrxkmUUZaAywcd2zVHug+3AJUN8OJmKFnmRF47HBzNyNkzNf3lOdC5dwJUPuxOVAwqdx09qGjMF0wHzUUm8TMBVwbrpHX+YwccAYwAtOEtz+xBuY9cnPCIdiLKBPUh864Iy9vh00/e40RJyYB2TyOhLPPNPyt0mAkbNEmJpkJOvj2rdwIR/61A6bcPRem33sFGJphNivpFWJkMX+3Hdb/8CW2NjwvV/1HDngewAhCD1X77f197WwWkyMgOm2w4Ucvw1tf+zNL00VbXrKbMX78PPvJGAUSs8kQku9hFh/zF7jYsbCIZ9UXnmN+AXTypTr2mGnic7K14JrwO5z4RxY4Axih2PiTV5kfQJB71tYjka7/n5dgx+/fBpvHzhyCKL2tFGDT5jcfOzoImfefmmZB0sZHhoCMhQA48z1Q/9Z+ePP/Pc+ciWg6MCaAJoksQqw7zNbCMTLBGcCIDAvaoPNgM6uyk1yyqdGjNM5xMZUfa+9dRV5TqickNmv5jV2HQvFkvr4jx8VCe0j4ij/KsvxYApKl5lOTSTgLPdC67Tis/vIKoBg1EAgYhgGy2w57nn0POg80sTXxsN/IA/cBjECwDj+iANGOkEmkSMy5Lmbz7372PXAWuJnUt4AEiyE/fK3ysvFQvWgK5IwuAk9pDoBAINYZgsDxTjjx7kGoe2M3K+1F4rbUebT9HXkuaNp4BLY+tgrm/Oe1LDqABI+MBrUQTvwjE5wBjASkePrNWgAzOWjS7RczCY2hPvT2b/rZ68yZl1rvh5/HIh1XsQ8u+a8boHJeDWMe+D1MHkIg88ivLYMxV2PG4CWw4YcvQ9PmY2D3YR6/eTRkHvg51C4q5o6HsovGgRKKwbgPXQj7/7wJAvWdzPzo0bGIhwMyHtwEGA5Y/fFJIr6e+CeIYvLfydcJUA2lN7YMV0ENhyHc3AFF0ytZhp8aijPv/oG/boZgg0mErOgnhfixTPf6398LVVfUMmceJuqglGc+AFVn8X4M9eHrWNyz+PGPQ+3Ns0CxSo1T1o3ax+5n3jP9BBqWGTuheuEkiLZ3gxIKszXiWnHNyfyBfq8tUcbM5wUMG7gGMNgSup/fU+vwGYFgZR8B0BQ1WS1npeOi9020JYp5CAFnYX5ybFfe+NGgxzSYuHSamZIrCYkknz0s1Gfo9OS8P0UFd7EP5v9gKbgKvYzA0cPPQoAGNX/HbEHUBNjxCWhY0iuJcNk3boRwawAa3j0ENi+aA6ZjUHbboGVrHSvzza8pBTUah9GLp0PH3jA7ZvfROjOaQClE2zuTWgCuxbo2dt7EGtl14rlZJiFuR3LKe9ejnwHXMM4ZnAEMJUGnNNjEbrtWrbwzLxdEJFZNh5zqSpDdLnbswikTTQkpClA4pTYpLXFgJ5OYyAwK8gFEAtGONaAEu8GR64Vjq3az4h+LUK1LQLX94v+6AdwlOczBxxqLGBREWWKaQrQ9CLqmg6vIx9bJWo3hGnWsKxDg0q9+GF7+1G+ZdoBMgUULBHQYhuHY67ugaHoVqJ1h8JT54Prffg+A+CDW3sbuDd6D7iN1ZjNSXYf23fsZY7B+x5+pn+EMY3iQPQwgQbzmDzJ0BD2qkjXf1FUNCmrHgT3Hx6QfTuXBvvyoImNzDuzQg8dj37WbnXpEUU6W5xo00ZaLUlN6IlEBBTWGqnsAtFgICDEfH6b3mg67RGmvQJhpUH7ZBKicN4Gp8qgpIHPAfADs049hwqYNR5j0z59YBtM+MQ+KplaaTEAQmFngG5UPNTfPgq2Pv5mI8dNk5l/r9npQQ3hcEQxNgbi/BSSHHWw5WG9gqvWespLkfR9z1ZXJ9em6mrw21BLOlWFgIxND1U4OIkkMN8HrQA2DpUcIqHmc3O5cwxjpDCCVoFl2W6JVFXsxQdAJmkaJZs2705k9jSpvQuUeQoIWRAkVXnMNgBsYdyJO6FFZGI1JaaziU83+fkoKE0qveSBx24AATvjBOL3Izom5/cxWt76Par1uwOhFkxMqv3kvmLOwPQivfeZp6D7ayhp74LHr39oHje8dgqv+73Yov2Q88xMIImEFQKPmT4Ldy99NMhg8FOYChJv9EA9GweFzg87yAmKskIhqcZY0jNBTJhGlMtiT10PAluNLPLOzZBh43/xB6Nh/iBF73B+Ajv2HmZajBMPgP36C3QM9pkC0q9v0qSBjwQnJiCxnGCOSAViSgRE0Op1w6i06qFBSWw4wSQRRRq+0DnavB5y5OexzruJCcBcXga4qJhEPIUGbUtuEKRWtP0xGxd5j8flEff8ZXDt+09CDTOoJksxi+ljYwxJ0LIaXiNHnjClM2vdWue6O36+F7iOt4Cr2gq4iUePQUBfTErY8torVGZhlwpRFCfBz7uIc5mBEyc/MAPQ7+KMQaugGV4EPNIWArgdAYkwpkV3Ym4n19yxR20r8frYMA9+f8KFrE88F90aC2cdNokcCRwdlAJmBjPcscGqGIYqgxeMQ60SGYUZM2B6znleC2WIRlWS3s7X2ZhgjBdKIbJXl8zCiRsL1lJeAt7wU1FgcfJVl4CktYQ/PU15qErqCIbAiRshI9NjvTnab/fHxoRNBPKneo+xKOM/wfZbwomqMyZwNQZufG5K7kLJWjUnsZPIOErums2YcaPtboT60/1H6o9qPUQNG/AkiQyaBiTxdR1qhY28jlMyoBjWsAGDqsdcJ7vIc6D7WxrIKzWxjApqi9DxvPyPHztrfMhCG0aOuIVU7JODMzzUnI+f4IHfMqGQK9PgPXW1+1UCGbUYskJFbDEOLxSFQ38gck1okCl2HjjDmoQRC0HnoKNs7MX+AaSFI+HosDrGu7hE39mxkMYBEIYvkcIAjPw/USJRJ68KJE0CNRpmDDJ1n+CAll5MxBEtdtPu8jNjxgZux9IStjRuKIrELJuGjZsFMAYMRD9uUzPQ1pX3qBjN/TW2cNwwPP+G97/tyr9cTvQGYRtBP8JddMzYb6XVNabsD93PeIYdVzGRNPU4+l0RNA77B/DeEMQXUAoCFIYHtF5TaqBkiUycsiiIxKW6aVwL4KsvZ3ogHAuDIzwVBEBgjQO1QstkhUH+CaZc2lwu6Dh+FaFsH249KKATRzq6hGas+hBhZDICpnxKEW9og2NDEbnbbrr091DOmhqF0d9jBmZ/HVHNRkpKedLQHmbddkoDqGuTXpFH9NY1pCnYvptPqpn8ArKm5Jx10jGBY+2wzrJa0K/tVYVP8FInfz/JG9Di2qZKm3COBgBJGFTYMjlx3kvDR248OP7T57Tlysv8/axqqaODG92tKmQPQ8q1gHkGsI8ySh3omGPU679lqAIk1J4/Qj32deg/Z80BbngJINtlk6Oy6xR4mGhuuKqQ3BZARGJp20sGoG+x3ZAz4OX/dCVCCQXYuJGzUCFjT04Qz0lqHNUjV8h+MNIwsBpDskIM33pwyIzlNRxZ7K/G++cOAWHcgIegphJpbk+8dff2t5OH6Ov/sPXwFaE74qsrBW1HOzAl7Tg5zBqLaiM5BdBKybDyHjX3fUjFFUerr0Ye+/gJc56nUWPPXk2o2JWYDTzQzMISHfQGwQWeo2Q+2RC0+SigM3QWOd0DBxDJG0OY9oczbjw4/zOJDtd9ck8ZKgHGcl7PIy+oCTJtWhHCLH4JNXWa5cMLRiteLdQTeynxTfSboHzG9/6dykKUzn/A6WCoxOheRQacQkcDal1mOQGSupmRHYkanHq4PbXYlGDKl84lGCJxoANnhZD9RcqN0x/f7OAPZPaVmV6Te+Ql4bpvMpD9bl93GpLz1cCwWzq4o4QdKaokjDCOPASBY6MfyePU38NpKLDGBnPp0Hl00I5RwhNEe2nMoEfCPE++c5PonNyzW55tEjxIENQfUIFBCIFNJxvGtmD7TOPQ0Dkaz5z9uPkvLQEcWah6WY/OklmE6PwHsrIEn6xEgi+Auy2X2+smLMv9hEs/oq6clq/20iMJCfejtxw7C3UfaWLQAk4WQ+Gtuns3Ch2YugME6CzdvOsry/m05idJjxgAMcOR7zFRhK+8AzLRhlKxMUg5EOnf2L517hAIxkiOK7DP4WfwOYwZxDF2ajAnvMVsP62B0Mnch1buP99+CzZN+L1j7yhyhYIYaU29vz/0IIxYjkwGcKfqRRv09L7Z5E0JAQubRO7yYRsvAzcsYRrefOYQsmFqGldVnagO4hr4hRk9Sy/BVVoAai7KfaItqSpy931PLyANKZdAVF6jRELNvSy6sgoN/25zQGkyfh+yxw7E3dsPkOy6BnDHFZoYfazOusFAftv5Ch58eU1kdgLPIw4jfum/ss+E4awzCEohSyonRT1AwuYw5GmPdURAlGew5xSDILoh2trFjni/pjGsT5QRBJ/obWo1Oez//5DNMmVNAIbvxwWYAA0WPDcP+f/Lv02gZ7P/MmXTmWkbzlh3mZuytZWDOvJTI2uulZeSMrmIJONPunQklMyvZ7zhG3FOex1KCT2bsof2uwPofvMxy+/F15uDE+oCE975kxijTo4+1AKj2J2x6TCd2Fbnh/e+/BJ37mk5K/8SNQYZWvXAy0wQwwSjmj8Daby0DqhMI1DdklnTmOCU4AzhX9OfAOgMtQ5ZTnEb9JTH10jL8dcdZDN5ZZEDZnGpQ43HwVuSzHn5sCGciY4/1DXDboXnzUVj/g5dYbj+m9zIHH7YRw9RfDPUlzollwUjkyARcRR7Y89z7sOeP74OcOtgDawWiKuRNKIHSmaMZ88EeBFiGfOjFNawZKDppuXQeOeAM4HyjPyfZmWoZggNkpwsa3jsMocYuZotrMQVqPzab9fCz7HSrqw+27MJKQSzswdx+NlcghslTpucbgVoAqtKSXWZef5T8SPyssjB1HYRAPK7CxCVz2MARayYhdiq253iTPQS4dB454OXAIwFMIzAdn0yNTjTx2P/CZuaoQ1Ufu/dOufsy5v1PHdphDepEhyAW9mCPP//RNmZfYxQAiRaPjam9+1/YCC9/6new+5l3QXLaesTcWdVhIAqjrpwI42640Oz973VA/TsHoH3XCbMXAKr5ibWOxLTYbATXAEYgrEo/wAQm/A/j/oEY697btusE6+HnLPAk4/zWXAEk4K2/fJMRODYIwfbfLKzWGWLpxLGuCIsq9LD5E3kCaC5gZuGlX/tQ0kRBraH7cCszBaQin9mmnGNEgWsAIwyWcw8TdqZ+fB5T2dHmNrMaDZi37CYomVkNsa5wD895j26/AKyFN2oFJ9YdgK4DLUwjsOc4mUaRSvwo+TF8iAyE9RUo8iW8/AIj/JqPzoT8SeW90oI5Rgo4AxihmPOFaxgxm8U+iQQdVQe7zwkL/+8OKJ09hpkJyUzB1G6/LC9CYl2DsS4Aid6qkks2EcVEINEs+kFtYuFP7oCiC0aZhG51FcZegQUemPMfVw9V0QPHEIMzgBEEJDx0vOFosMoras1GHSn2PuvoE1OYbb/4sbsTGoLCKv2s7zMpnYg0WF2De3QOTnwGvf2oRWAPwev/cB9rK4ZjxnucL9FNuPKKiaccV8aRueA+gJECVt6qspl9F9w/v1+VmxU1JSb4XPSf10LF3AnM5sc2XkogzEp62VgwixkgEp2FsVcCJvmgdoChvolLLmKEjcwiVfL3PB9h7+GaGt8/bJoevWYVcGQuOAMYSY4/RYdZDy1muf+nkrasEk43mFOv7KIxUDZnDOvhh228sJMP1g2gNNeiOB3YdCKi/Y9DQAoml0P1VZOhdNZoFurDz5m9EMR+F4a1BLgmXNvab7zAGAin/5EBzgBGAJiqHYhC1eW1MPbaacwuP9WkXvTOyx4n+xuLfrB7LzoNi6dXscEgOOEH5wVaWgQrg63KZ+FCZAToTEQHHzIZdP4xh184bs4G7GciMa4J13b0lZ1QvzbN2DKOjARnAJkOy7mX42IFO8zplwZWaA4dg6iGb370DfCNKoDxN84Ae76TEXC006ygs/tc4CzA/ggnqyhRu2BaA44bE1EjcLEwIpYOY2hxyl2XMWcgmx5k5dz3Aq4N19i6o55FFXq0KePISHAGkOFgMf5gHGY9tAjyakoTE4F7SmG037HZJ04PPvzydtjxxFvQeaiFEfv+v2yC0VdNgnEfmgXOQicYqsIKB3XlZOZhSp9U1ulGi1LY+/J6OPbaLmjbeYKFGpERTL/vShh77XTmi9DiWo+EI9MBqbI1Xvjp+fD+D15iTMSqFuTITHAGkOmqfzDGqvfQIdfb7rc6F+PEHlTpscQX04HRBMCJwFgjE6zvhA3/+0/wH9Ph6l98C2JdTQAEzYJgsv8AQhCxCMcBztxyeOubP4Ptv10JjrwckBwSCxPi5J+3v/ZnOLH2AMz83CJm86NZYhXxWOvFNeJaj7+132w/llpLwJFx4AwgU4GhOibZZZjxbwv61Amw91x29rk9z73Hmn1G2oKsRh9hzQbE79vz3GY7LOIF2WEz6/WxgWeP05lt0LDWIFDfwkwJHALC0ns1s6EoOFDD2AFNG4/C9E9dDrVLLmJqhFVqnFwbAFtz2/b65JRhXqaXmeBB2wwFG8ARjMHUe+ZCyczRoCUcdlbJMBIodvd98wvPwfv/8xJz2qEDLzWujzDrBzALEPsbYD99hf0DqvX4x143FACim12QU5KC2HESx8Vz4LnwnHhuXIOVXWg1UsW14ppx7Wy8GMtU5MhEcA0gA2GO6FJYO6+pd881E34SmXpYvINxfszp37V8HehR1SwBRgJNo2qzEJ5NZl104l1+kJzonTe7DfU9r8Dse2zS0R/RspLhREpxw7qD0LzlGFvj1HvmMS3BiizgmvH146v3ss5DLMU4haFwZAY4a85EJPrLoa2NhGOF35Do2nc3wKv/9iSr6kNPfLJe/xTedqZNhMIsS7DfrrXIKCSJtUJj/fNZk45+jpnQKvDceDxcC64J14ZrZE1GVZ2tHa8htb8BR2aBM4AMA3OkBaLMkVZ1eQ3E/FFGVBhWQ7XbIjRHvtk550wdbGwyb0px0Ll+LvXcuBaLMeEaWWERhiP9mLtQYzowe6Utc2QG+BPJ0HTfqR+fy1R9LO7BxJp/3fd72PPsu4yIMNcfk3vOCAOQ7GekKaQ7hWawNeHacI24Vlwzrh2vAa8FrwmvbaQNzviggzOADIJVhDPzwYUscy/cEoC133wBVv3HcxA43slagCMGakuzvn9xLAoK92/b9/AVdJtOwwEk8VhrwjXiWnHNuHa8BrwWvCa8Nl4ynFngTsAMAUrPWEcIam+ZzSby7nxyLez43dssvo+edyvh56yPz3run/5xs5z/c5DSLCnJgeeR4PBL26F123HWqGTS7ZdA88YjsP+FTayEmOcGZAY4A8gY1V9jwzzHXDsdXv/ccjj62i6WRGM2+Ty3RBrUAHDYSef+w1A177IeLbJ7I3W60dnC0gZw7dGuMKx9+K9wYt1B5gvAqEGkLcSSlXia8PCDM4BMAaVg8zrhve/9A/zHO8BV6GHtuQdLUmKMHqfipgwm63V6CgKRoG33ATZ0E9tzn6vj3upChNeCMwq6DjSzIqFIa/Acj8wxWOAMIBPA7G+J9ddDbQDtaCuTbzAhpExH6ncpid79gwaKrcoou6ZIe4hlK1pjxjmGH5wBZBgTYL8Ocu48U/lFETr2HwLD6DX9d6gZQK8y5cSChuQcHAMHZwCZhCEkDCT6eLcfaMqg0t7v67oCbbv3m3MMh2ItnPAzDjwMmEUQcBIROfUjx7ZgHNkDzgCyAGcc48cJQf21/uL4QIIzgCzBKbP8EtmC8TOpA+D4QIEzgCzCqfL8zSnBCmMSvHw3e8AZQDbgDOsBkDlwEyC7wBlAluBU9QCpPoLYWdQBcIxccAaQRThVPYDZgSjEmMRAKgE5RjY4A8gSpNYDECKmNQFEu53b/1kGzgCyCKeqByBEgOCJRqDaqTMFOT5Y4Awgy5CuHsCsDhQgcLwRjCFKBebITHAGkCU4k3oAyWW2FOfIHnAGkEXorx6ADROlOgTqG7kPIMvAGUCWob96ANQKAvUN5tAQHgLMGnAGkCU4XT0AOgExCsCRXeAMIIvQXz3AySSh/geCcHwwwZ92ttcDDGQgCMcHDpwBZAtOQ+gDGQjC8cEBZwBZhP7qAc52IAjHyAdnAFleD3CuA0E4RjY4A8ginKoe4FwHgnCMTHAGkGXorx5gMAaCcIw8cAaQ5fUAvQeCcB9AdoEzgGyvB6BDOw+AI7PBGUCWob96AM4AshOcAWR5PQCO6x7ygSAcGQvOALIIpwr58YEg2QnOALIMaZN++ECQrAVnAFkIK+2XAgVB5gNBshmcAWRxPYAoy4DNwPhAkOwFZwDZXA8gCgAGMgU+ECRbwRlAFtcDUJ2CyAeCZDU4A8jmegBR5ANBshycAWRzPQA2AzUoHwiSxeAMIMvrAQSJDwTJZnAGkM31AJoCRBDBf7yBDwTJUpwNAzh1rijBFtOUZZgQQnheaSbXA+gG+5sPBMlcnCzXSvx52pYNIh0yBkCITICC1L9tSXFTUckhsUoTQzP6/SxHBtQDiCKT/EE+ECRjYRhUMgyD2CXJoJTqVDMYV+iPseuGLg0JA6CUknA4oAJQv8D6yaVId3Qm6QaRvQ7qyvPYO3c15AHYqLs0p4WaJae81UxG1gP4WRMgnAnIB4JkJmw5zhanx6c27ar3iLKU7yjygq7ofdo2EAJE1TSNEvCbryyhg8YAEqo8mTTpviAF2G9nPeV6lo2h9Jd8yABccuBoOzIAw1Wa285tgEyuB4iBIIgg2vsODOUYZhCghFJw5LjaAHKUrmNtbiKSPEehJ2m6WaCUUkmSSDym+QOq/4D18pD4AAih/U+QNGhKXzlFsLttcUpA5+I/Q+sBZBk0hQ8EyVQgBUsOWxRAFYhmECIIRn/V2vg6AbDZ7Y6hMQEAVjI6pgAHBSENSVOWVUYLxpVAx4Hm0cgrCqdUtIIkxrHm5Ew5Esf5qQeIdnZBqLEZlHAY/HX1fCBIpoECQfM5d1xxPUCO1rzhSKmv1OeyF3oMQ9VJrwau1CaLqDLUG4Yzgub6EDCAIqt29HhigERfgqYUnPlu0ONqDkBYdJV6o4JNDHANILOQOgoMU4FZR2COTAOhAmiuYm8AtelQW8DnynUTzNtIAyphdSelraNGLY2aj/jMInADYABt7IACIcd1DZ38vbgMpphqOvGNLYKYPzo2Gm11lE0ZFXDkuY8L5lK4BpBhTEB02FlRkB7nzUAzDFSgQIhd9pfOrm4BUMXAkfYxudWFqL3RdHMbElr58VRtfUh8AAJIe1UFDZKeOgj+pSsacZblgiALpY3vH84FyFXdpb46dGagU2Og5+IYwnoARQH/0eMQamhi5gAfCJJxDADsPkdjYU1FUIM2WywQGe0bUwRU66P+m58XBTAI2dNTWx9UBrCEuR4jsdjhWEwJiaIooPcx+TbGIBWduCtzqa8019PwzqESAKeRV1t+2EB1hIcCMwr46GLdfpPw+UCQjIwAuMpyD9ldBfET6w/lCJJQkTepDLS4mq5zu6AqGshU3p6qrQ8qA0CbAp0L++oPdxqUHnTYZXy554kMAySnw8ivKhBathydgF+rvGRcHbWJEcIdgRkH0WbjA0EyERSIQQgUTqncD+DWTry5r8Lpc+bbCj3UdACmfJRSisI4Fo2HQoK+23x19+AzABNrxAULHtEMQt+12RgD6BmQNFdEimZUQ7C+c6oGTc7KSye0O/LdBxMJitwMyJR6AEGArkPHoGXbbjDUxIwAjkxR/wVwSN2j59ceAaBiw7uHJpVMqiCOXLdh5gD0jAA4HTKounGgomJfAwppQh7pS5eDWQxEDHGLYRh9HIHYYlqLKaRw5iighNTUrdpVYHcVx4qnVa1PBCo5A8gUYD2AP8CInyODQMAQDQqe0twd1XOntSl6kzPQ2Hlh2SXjWLZtGnPNkGQ042BHgvAHRNMDZADzWY4/BfpaKBiNiKIo9vUDaMRVnodmgOvgP7aNxxdHLZ6yy5DFKDEA402cCWQIsCEopWcsLDjOY/y/ePbojQB2/eA/NpdIklidi/Z/LJ39j+4Cijl4fzf/XglDWAzE/ADC6vVSi2ro250OO77ccwcZFGSXnY6aV0OaNh25CCAmjr1qSrOzyLOPmwGZAdwwmP7bffgYnHh3I4gOG2cEGaT+U4fUPe66afuwnubgX7ZMKZ1c4fKOLtRRuKZqAIkUYDEcjPiBkg2pzvohNAHWCEuXLsVqhNdsdpZ1SHubAWooJlQsnAzEoBcefGV9KXoyyy+ZsHrg5+IYKqD3P9LRBeGWtkQIkN/rTFH/c8cWv1t96fS2aLTB1bG34fKx11+AFnQ6J43hctrR/t9aVH1HIwrngZbgnwUDSIQYdOG1aDSOWkHPYyTMAO/oAr2kpsy386m1s/HFSXdcugPccismOHAzIAPSgUURFH8Qgg1NZntwPhJs+EFB0AWij7l22loA2dj5u7fHyA55YsGMUVSLxIU0floqydjXUXzF/HPNWeT1DBCELNXR09gUEjdFovHdTocN8wH6qB3UoGT8zbOhfU/jtV31dd6yKTVdeRNK3xGxWQhJEz3gOP8gZlIQR0bAkAwg9kLP/tolc44AaOKeP62/pubaC0RXSQ7m//fI16AUqCAIYjgUjYhUfMF8dY1xnlqCrRGnTl2qEEF80uFkpaRGHzMgHBeKLxpj5Jbllm/5xWtTAES44P75rxl2KUiM81wclBh9haEv9o/9zjc+R2btDySIsdde8DdPTnHs8OrNJVooPrvqmilUjSpC3/VQw+txkpiirskdtfSQqf6fefjvXBkAO5FOjb+HgtGYIJA+3n2MV0ouO0z82EXkyCs7P6IoHY5xC2Y2500uf0M2KKHnSQtgjS50HaJd3awGXo1E2GQcLRZnD5oju0EyY3+g9BfkQve+WQ8t2obLWv/Dl68ee/lEb25tmaFHlTThPywWwLJu6bmzVf/PPg+APGJQukIsrrrzYFxR/+rzuTE80GPgPE6dUYJRYdR10wxfsW/yO9/9x3TUAi76wvX/pG5bq2gApjvToX64aiQKktMJsz93L9zwu5/Ah/7wc7j84S9B7uhRLA7OpuNwZCVIZuwPlkxjENAn3XrJs9j95+i6LcWRpu7FE26/mOpxFR17Pb9AwXA67EK3P3zEr0RfMMt/F/SgvzPFOV+daBN/o5rJJH2OhVqA7HXApFsvhgN/3niHv6XRUzVnYkfVVZP/xKqd0mUSniHwprCH048Naz7cCBRMHA83/ekJuOzL/wGjrrwMKudeBBfeezfc9OffQc1Hr2OOMK4JZB8Ga38QUThXc4FKOgi+CaVvXvTZa3YBGMLbX125ZMwVtd78KRVUiygEeh2fUoM6XXYssHl6zJhPxtAkx65855UBJJyBQl7Z7WtCoegan9clpNUCAlGh+obpesm4kjFrvrLyCtQCrlh289tyiW+XZCYGDZwJEMCiCIh3RwCdI8mHYN0nNvDCAMluhyu/8xXIHz8Owp3tTMXDf9GuTpAcdrji2/8FeTXjQItGuTMsm3Au+4OYPi4mfCgFxR8FNayc7Uoowbx/uxi45EvXrcCjb3969Rg9GLtq4j3zDC2qkN7MBWP/Npss+P3hjrhIfmFKfzNBbxg0ALPuWLSJj5ipwX1jldgrULBJwvTPLjSa3z+49Og7W0rtLqc+88FFv6MiiQ+0V4CZZxBnWsXFX74eSyYZI1BCMcCOqfg+lkbigxw1fy6UzJgO0e5O1vjCcvJgBpwSjoLDlwuTb/2oae+xRqcc2QAk5gHvDxGdg+gvoKBGFIh3RdimnXzXpXDBA1diE5yBawIEbX9Kqq+e+lTF3JoORYnJ6//3X5+YcvulYl5tKegxtY/tjxE3r9dJVM14rKLiznazRcfZt98/p7bdlhZACFnTXvfMGp/PPT8YjGCSkNiDYIMxUnrZeDrpwzNz3/zic5+8d8P3fjhxyZy6E+/sf6rxtd0PGCIgBzsjjwtrPuq0wYSPzITCqZUwav4kaFx/GE68cwBDjhBtDbCHiZWJqN6htzGdmYBMQjdUyK8Zy6risikObmpL2K05cc2J3/HeZgPYSDRdh4KJE85of0g2G+iqjpEtcOa7oHByBVTOHQ/ll02AwknlEOuOwMG/boFYd5gxj3QNO/ouAnRZA9E5rvjtuctuflsCJ33hE49fXzSqcOrEj1+mx7sjYm//Q6r0t4nORxOtv87JmT4IYu+kFsDSldIwQSs7cOrnrtLdLsfFL3/2d/Pxghf9+I5XneOK3rbpVMQbcrozMZMiFIPaW2ZD4ZQKCDV0gj3HCbU3z4IFP7oVbnjyPlj4szuh+MJRzETAh3zK4yEL1jT2wJiKlwWRQZRwWlSFeFeYqa5MmjENiiV1ffBNISv3AR1Qqnqaj5qMQlc1cBV54fJHboLr/3A/LP7F3TDtU1dATnUBhFsD4Mh3M01Ai52hFoAZfzqIQo6jfuGP7/gt9tLc88La6o7tx2+d+eXrDUEWBTRR0kD3+lxM+udU3txxrtJ/UBhAqi8gGIq+5vW4REqNnpTHJtLqYPM6hVlfus6of2P3p/a9+O4oHQwy/0e3/47kuY7iDTltghBrPCpBpDUArTvqweZzgs1jZxtZCcawBgHGXD0VJt95KRt51bR5O+Pi6TiyoeETkKFp03a2EXRFYyYEW27CxkMpYPkXkj6GkUogiU2vBKKQV1MCMx9aDAv/73ZY/PO74JKv3ACVl01gzADvy4jNkUhco/W8zJh+yjNkkp+CGlMwfAZntD82b4d4IAJjFpn7ylngYQwU7yOOWHfmeyBY3wGR1iDbm6wz9imAkS8BZ3tIQvjCBxc9mjO6MKIGIra1D7/wuel3zXVgKb0aimMH4D5LsttlIdAdakbp//DDD+MHzjmUPihPOmEGGG0nVtQ6Zdipabqg6wa+1rNwWTfAnu8xdj76hrDt2XWH79n07W8IgqAefXVH+bpv/OX7hq67DZMJ9M+YsKFlOA6CXYKy2WOgeuFkKJ01GrwVeWYaclxjzOCfd/8aAg3tcO3j34faD38UIv6W1AWDMzcfOg8fhr/dej8o4Qj4qgoh7o+wB4vMwNAN03+BDyKxoUTsvEpN9ZCIllPI7M/AHvvJ/1n35eQtHk4TI7FAvDezHloEtUsuApvbzjY5ux5JYL+fWHcQ3v3OP0AJREC0y8NrEpjD5cx4N6Pq1Pd6dMRI/KA4iYp9DH/i82PxMt1ghI/XiIzA7nOCPdcF8e4oRNq74eqffw9qbzz1/gi3dMF1v7uP7TOzq7IIkfYgtO2oh+Nr9jHzM9YVBtljP503C3V25vUfdcuMny767u1vAXjoM4u/+m95hTnXXvGLu3U1HBPTaWGUUi0/3yt1dIQ+UVh9x1PYB4QQog/KbR4MWAtqq1u+rLAg5+HOzqBGCOnjY8AHJbsd+luffVpsO96x5uPrvvV4PBKnu5e/U7PjF29+3dB11+mYABIjbk6UWKgquQq9UDy9Ciovr4XiC6sgd1wJHH11F7z1lT+BI98H877xRRh3w2IQJdbEBMuZoWXrTlj7yA/hxDtbYNonF8CcL17DVOFQIyaBKNB9pI0dP9Lih3Czn5kUwfpOIJKI5oypMgusEWqSUBhjYPEYM9fe6uBKrfd6SFbTv2Ptl5NMJP0O6sFM+n8I/d4vvJaLv3Q9TLn7Moh1hE3CsNaT+J4j3wPNm4/Cqi88x5gFY3L0VMTZ70JOYUr0JOa0101NCWxdMd5ftMGTb1vvIWHLYlIzRMJG4kd13ZHnBtlth7xxxYyB59eUgmiXwFueB84iLxx9ZSe8/fWV4K0qgrlf/yKMu35Rr/2xA95++IfQtGknzPj0IrY/gie6oGNvI9SvPQDNm45CsKGL7T/UPPFZn4ZhMuLH/JfyRZOfuOpHt79qtzvoP+791XXdO0/cd+3yB3R7jks0FI2tNxWGYei5OR4xEAivyqu642o0u1HzhkHAYDIAAitXCpvHdgljSzzrXS7HjHA41sMhmPggIyI9puprHnhSNPKdzyz507dWxuNt8ran367d9eiZMYFUZxaaF1pUYXsI25J7q/Khcu4EaFx/BFq2HgUsVyq/aCaUzb6QOWk69h2CY6vWQqTVD9VXTYX5P1wKstN0BOJGskwA1jwzoQmgVoAMAh90pC0I0fYgO1bXoRZTHZRF6DrcysJCqBri+/g5JHy8y/hdPIYlvVAbYkRo3ZaEfZ5O/ba0j1Pe/7RMxgRGTSrmToDFj97NtJykE7AX8D66Snyw5bE3YMsvVjGCMoe9QB/iPB1MKYyf63UeSyr3uG6U0Inrw9MJhNnVjNFjLonbDt7KfPY7fi6/tjSp2hfUljGCkV028zOaDrLHkZTGptbGZlay/YEEhueXnDJs+NErsOPJt0CUBai6/KIe++P4W++CGoowBjH+xhlM2ncdbGHPFK8fv89U/kRI8Uwkv0X81/38Ey8DSGTd//192t7fv/XIol/cY+RPLScaqv5pHH+yLBqiIETUmD4jt/r2w5Q+fFZpv+kwqMbeihUrRCwVbj3x3Ay3Td6ICUL9mQKYINR9qEV/44EnxYJZo3974+8eekmDsLD5iTUTk0xAACMxVOS0V8GKEpljR2fSCzvdoI/AdPiYYR/L6YOJHe6SfExThgv/bT7brIyBGKhG6qahlpBIjCgTdiVuPkZoEvoHzOxni1EgLG0AP4saAnqNmYkgAJMe+DdztEkC0zTCTd3sd2R1+BP/xtfZa7RHXQX7fn+2Oeu4yib+9mQyCCQMNInQSVq9cAoogdhJ86XPgSgQWWQ+lpfv+S3oigq6Zpi+EdKLONk50mslSGAohZ3JMVam1Mff8ZmgVLakJf60eR2QNz7xGp5DFMBXXcAYGr5mSXdr/A0+B1PTMrUBSNESWHYZEjuuO/G6qV2Yz8Hy7SDDtue44NA/tsLWX74J/mMtoCtKcn/YPMiAzJIVvH8IySGbGgcjeuu4cHqbvxfxa2AIW59YPXHT/7z4tcu+9VHX+JtnQbwjTNhz7/NIqJZf4JNa2/yfKxl91y8GS/W3MOjeHkwRRvWk9ejy/ygqyvlJv6YAMgGfk3bsaqBrHlouFMwe88SHf/u5lzUtLGz+AzKBVV+nmuHSMURIzyxEaF2RRfSpM9RMQj65Ed3luVB1eQ34qgrAXZoDnoo8FlFA29jiwkxKJ+xJtqEMc1MlHT3Ju5ewVVMcN0hk6D+wtghKolQCtpxUqSYAO0+vuW+J8mpG3JZ5kfayBdKTyYiY6RaH977/T3bMG568H9wlOWYLsFM4MnFPi5IArz+0HBo3HIFLvnwDFEwsAxU93NCLONMQAPOcMzPPzhy0vdXiVEaavHMJCZ26Blxngt6T9n3y/eQxEz+TB0uEzZnNL7JnwDQnPKcgsPtrOfBCzd0QakIm7IfG9w9Dx/6mpK+h93rM52Ze14B8OQQMLHyTDICyxSnE/+vVEzf96J9fv/QrH3KNX3oRVTrTE79uGHpBvlfs6gq/UDDqjo9RuloiZMGg9nAb9PHdZlSALfSnncefm5eX57kFmYAgCD3OxTaoP0oKp1XA/EfvNtY8tPz+F+97DD7828+/fOHHr9hvt9uXbX981WcFf6RalciZM4Gk9O75oJLEm0DgWDts29PA1sEkjM/JpJa7NBdyxhQyb29OdSGTds5CL5NSGA+21GyW+IQaQ4JJIFjJZmIRhkrBwMhmwkmIiSLW74llprl37P99X0epm+s6bbZU8XSPuVmZmSVBvDvMXkeHHhLkGTn1EmaQzevENu9QMKkcKudNYFKQqeQpxNkfGDMzDKYFpT9FOsbR831Lq0pNVbAYl2gzpXDSNGLVfCZDwmeBxBv3R7EWBcItAZPQm/3MhxNq6oJQs58xAS2qsmcmOmQm3fu7JPO+DdAhSkCXMLIlCZHRN13wmyu++7G1+CqT/Ej8//UhV81tFxuxjpCQjvgNgxpup10Ih6JHRErvT8T8B03yDxkDMDFfRzvFf5zeHwpGZ3q9rjHBYMQQzLniSeCFx7tPMoHVDy2//+8f/1/hI09//uVJt158pGBqxbff+eqK++F45yWqiEmTpn9tMFaIdrrDYTp9kJDRSdZ1qBU69jUBXWUkpQbakljV6C3PZQlIuWOLmFrtKs1hEhUJExkE7lRLNbbUTHZoZnuaXVBQRWUmQhqpxhT5lCiCyQsSRGAYaEolblr/0ps5kJIXaIY2UaNBuxW91Mjk9NPlRqDJEVUg0hZgfhFcDxIT3p/kqU8VCk0lbutzKFFTHH6p15bUlhgBmy/js0meCiV5ggiZeZYwdfB3XBMSNzpl0f+Cz7HzQDMzAQMnOkHDHAd/lN0/fA5WWJdpY6LAmPoQJEGxfSprVJRyXcemf2bh4xd+/IqDeGff/clLU7c/9tp/XfqVD7tqbk8Qf5piI7PVl8Dm6YSiyh1lYz/eRanMNGsYZAxZwDcZGqx7arbb6XpF04089An06SCUcBjZc520fVcDfe+rfxZ0WXhj6Ztf+40W0ahhqOStLz73ocZ1B+/C2QK6yPwCpk42mGDaX69YP1MFcXMYSeI1nUk0qQmgZMV/SPi+0YVsE3rKcsFTkcs2Yt74EpzxziQNOqlY+E03etq1CY2IEUHqPezjbEOnpN6LcfS4hJNS0DCYFH/rKytg/182wVX/exvU3DybZa1ZzCltlqVDZsT00j2/YQwOTQf0nuN1I8NONWvO1Flp+UlSvfqWIzHpLwmhb8JU0wN1HQmipdC5rylph6PDFVX74InOZM4CMgOEaf8j8zXj/ejMM80N4WTEJcFgTVX+NPvhbJBU+Sl4x5e8Oe/Htz2VX10UttsLtBfv+78bWt8/fO/sL10njL9pFo13hfs4/E42+gDd6bBJgVDsgeLRdz0x2HZ/zyUPISybpbnu2UUFPtfr4UhM1zRUBNL0NkWfgMeBHNt45/89L3Qcad0x/9F7fjnuikktGuiw9ddvTtr79LpPap3h8RqqomfqIBwMWLal9XuKGosMIlEHAUZcSzqerEwuZosm1HIkeCR83OTICJjXGp+4ZoCnPBfcZbmm7YmSUBKYt5t5xxNOLHwPHWtoqrA4d+oSEzaqxVgsh9uhf26FN//jOSiaXgXX//6+hD/DLKDqgQTjwCjAO9/8C+x88h2Y+bmFcMlXPwyKP8KcX5ZjM50vglXXMWdlZ0p40ZTuqFlZJgQjeEbMrYloC4Foe8iMmCRCabHOcFIim7kKpklgrTnpT0nE983HkiiHS+YFJBZwPlIZiLkXZR3DUHJX9dVTl1/6yE1rbXa7Ee4KOP655PE79UD0+st/eCstnlUNcbT5+2PClKr5JXlye3PHI0XVdy/btOnX8uzZn1aHbulDDIsJtB575v68HPdvTscEWGhFIMaOn70u7H5hQ3ftrZf8csG3796oQRy661pcG//nxYWN7x26hcR1n4rebDJEGsFAkLiUtCpyikrMJHPCHOgT204wjZN+xURoLPVQ6DH3mBqHeZxehSIYk7YYCzKghCMUzRpUhWtumgWXffNGM2wa6VnBhhLTkeeC3c+8Cxv+91+M2PImlDBPOWMYknCSUHuHqhJRCMtZ2dtESEZHLBMghZghJWfC0hB6XHePRKuTTr8kAxrO8gUCBgucGBQn+eh5E8ten/XFa/5SNbe2HVPdd72wtvrdb73wYMX0UTVzHv6I4SzyECUY72/Cb9Lj39UVeiK/6vYHqLFawjr/sy31PbNLOA+wVJiO+mfu93lOwwQSYTRbjss49tI2YfP/vQqC2/7KosfuXlE6ZVw3gEYPvrGtbMvP3lgaONo6T9SppIk4TM18GBmd0X+a7LbkRreQxllmaRz9XWRvxoI3BH0XTPIGYjDmmqkw/b4rce58gpDNODaG/vat3Ai7nn6HSXtU9TEhipkbiZBfanJTn/NaiTnp3j+DazuZ6HSepPbZg1q+KPTu41Kdxd4dtbddvOLCf1u4RwIRokrc9sonn7imfVvdbVPvmuuc8sB8g6q6wCoGxVMTv78r9ERu5e0PoAnN8gfOMdf/dDhvxGJpAh3Hnrnfl+P+TSgc1Q0Dr6+vT4DtAbRhc1wUwzU7f/IaOfrWvqYJN89+8or/vmWrCA41DjFh3/L3x+5f8d4NgbqOiwXVcBoCAR0fjqkNZzYzOBf0G4NPw1hSwmaJ/gzM+YUFU5hEg8TuP9oGLdtwUnA32HIc1qHSFkidOiMx44n3XIkesG8/tu7WBWI4i3y7xl47/cXpn5m/w5OTp2C4f+vTb47e9ONXPl5QVTB9xpeug5KZo414d1hgDs40eRwJU0XNL/DJJ4l/hYj9/Yea+BHnlUBSmUBOnuc3kXAMFFU3BCENE7BMArsEotNmHHtpu7DzN2sg3B3ZOuOhq5+bde/iIwCSFtf88pFXdpYd/uuWi9t3n7hCDcRGiZQ9IGyzZJoIiRwXMgzXnGlgNe3oQY+qyZRa1AQwFIbmV588hOwEtYie+Xsx3wtNNNxBDqkzb3zJutHXTVtXc/Pso56cApbtdXTdtqJ1X/vzzfFAdPHU2y8Va+++zBBtEsFS+HRhPnYSNsgPjLyiXNHfHjjvxD8sxJBkAnXLlzqcjl8JhOSFI3FNEPomC5mfN5MvUBuIdYTg0PPryf4Xt2pEENZOuffKly+4d/5RCTwqhkhbDx3OOfri9rEN7x2c5a/rmKmFYhXmg8Oea8xMQG7A0jKTcwqzcWw5OZnhmJRCeJ+yqCdCEoT9n6k1ltaITWpQZCMJ4r4RHFKnuyJ/R+nM0ZvGXj9tX9XFkzuwbz+278LuvZt+9PLCcKP/6urLa3Jq75kL+RPLjHh3RLDM2XTA7lmiKIh2uwxxRVuWW37bI+dL7e97+cPEBBoPL5+T63P83SbLZf5AOG3GYPI7GMeVRQxtGaGGTuHoC5th7z+3alTVt41aNOX1mZ+9endeVXXQ3M6q0L7/mO/IaztHt+44PiFwvKMm7o9WqJF4saBRG7MSLB/SSC3v5RgkULYXTKmAJE0M0SF32rzORndZzqGiqVX7Ry2oPVJx6aQOCVwaps5Eo63O3X94e/SeP753tRaMzx59eW3OhNsvhvwpFYYeUwQ1ovbrK0EYlGouh00iAtEiUeXBgqo7njAl/1Imp87nox223W8xgWN7lpcV5Nn+4PE6r+nqChnoyRPS+QXYl8wMM5ap5nEYwYZOofmtA7D/b5sh0Oyvy6kuWDv2+gu2135szglPfnkEZ6sDRAUN/LbO/U3u1h31Bf5jrQWB+s4StSOUF4+pnmh7cFS/Se0cH1ygQkiBSF5nuzvf3UJkKV4wobjOVZQbLJ0zusU3viTkcqF679EBVFHRWx0H/7G15NDfN0/u3N0wV7RLU2uuu0CounoK5NSUGYaiEquBZ3+VkIlBunpenkeKRuIHQ1HlkyWj71pHN/1aJkMY6jsVhnXTW8VD+Ht34x8ftsvSMrxD0Wj8lNqAlbmFGWOyx24ogSjp3tNE6v61A+o2HNa1sHLUnu/eVzp79I7qBZPrK+fVdDo9ZTEAWQewGQCKYGZVKkI80sEmnHJkJ+wun2oKCp2YxI4/VTEO7fbW9Yd9dav3lDe9d2hSsL5zOsjiuPJJFc4xN1wABTNHgbPYZ+hRlWDzTis1uT8Y1NAlURRzctwQDsVWHO+MPjh58j0dVu0MDBOGXephZ5Nly8xZAx3Hn73Gbpd/7nY7ajo7QwbzwPTjIExlBOjYkpw2KsgijbT4Bf/+ZmjdcBSattVBsD0YoppRLzvlOteogmO+sryOvMkV7bnlORHJZdMr5k3q1jV12O8Dx/mHKMm0bddxd7Cuw6mrmti44UhprD3o9R9uHRMNREcLklDp9DkLSiZVQNkl4wBHdHuqC1hpJM7qY7Ufp5D4qVI/x+eSFEXz67r+TW/ZbY+a7w0v8SMyZuNbJsHhTb/OKRmV/x1RIA/hjQ2Fojr2RkZfzCm/nyjPRD+B5LRhXzWqhGICllkGD7dC9/5m8Nd3QrjVD/72oGJEVYUCVQxVb8Svnb8r5cgcUF2QpAJBEnJwi3mLfS5XnhtyqwvBO6YQ8ieVg63Qi1WirJmAFlUJG9HNEp/M8vPTEb5NliSPxwmhcOzVqKb/e3Hl7QeGw9mX8QygN0fsOvH8QlkWv+d2Oy6ORuIQicV1NLBOxwiS1YDoxUVPtyxQyS5TwSZRQ9WJoRtE6Y4QmsiGC2OXn5HaA4/jnEB1AxxFXrAXeVkUxF7gpoIkmntF0wm25cafqb0iT9cT0iJ8WZYkr9cFwWCkkerwzZzKW3/P3l+9WiILBrek91yQcTvfLHtcKSAj+PWmX8u3VeTeLQrkC06nfWo8rkIkGmMlYf06Cvse0AxzWcXlwLLVWMCHFa/YZasMjyPbQAh2/E0SOBK7JUCs8uMz7ZKMpRSohzLC9zghEom1AJBfBYLRx8vGf7zV3NfLyGB18vnAMgALdMUKkSQchLt2rbBVFdC7LEagqRoEQzGM4LF5Ar07Dp3+4NaPD2zmGsdAq0DPghrMKmfKCNrhsIkupz1B+PRXwZD+y9Jxd7Rkiq0/4hgAgslsuoJpAz0YgUjuFYBchqPJQ9igU1Gx9yBya1ZLMtzr5vjggpoqPhI9xSY3KO1x10Vjyj4C9E9Bqv+ytNQk/NWrH5bmz1+GezNjxUxGMwALZgHdSUaA6G54/mpZFm/XdXqd1+MswYYZsZgCcUU1UioE+/Qj5OAY2N6jLF2XJQpSSiRJFJ1OO8iyCIFAOC6K4qu6brzQEvL9qabm+vhIIXwLI4o4LEaQmitNgy8Ux+Jwg65pH9INepHDYauUJRE0TYdYXAVVZQX2lt3F2MFJr78Zvh3GS+LIHKkOSOT4F+4t1qeBVSYLgsNhA9xT+KlgMBIURWGDJIuvqEBfzClauv/kcc5vHv9gYMRufvQRwBKzB2Hytba/eUOaMkc3tOuIIF6kq/oUl8teYLNjiynCmAJmEqIzkTmAdNZqCx/YMBeWcwwHaEIEyLKIFA82WQJREkHE7kyEAHawCkfiEVESdoNBd4ui+CIowgZ31S0nksdgIT0cj3f+03izmgFYYN7VNctEmD+F9na0dB9fkW+AOo0QMkOUpNGUGtM0VfeKkjBBx5xjSnNwrLl+ivp6jg8mWBWkQCAWU0HV9C5JFIiuG402m9SsacZxQ9MPOd22jZRIe10FN9X3+C7FsVzzBYA1RqZ59TOkKej5Q0Ld0lJDiLBmN4H5WMi1tBMA3kr8S4LSf+Z1H1Opbo+VAZDSYCAKkjTibwXHAKCBBrkOB8RVJSTp2kFfZREBuMGPfSzTfJxQiqYnwLJlu6lJ9COb8LMCyBDQLsMsQ7r6YQnVtURHLg6OtEDpntwz+NMcwvmBRVYSQ6LHOvJzAjAlK+8Bh4mVKwGWLFli9VxnbRT5veHg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODggJGE/w8rYSDp5t1r2gAAAABJRU5ErkJggg==';var d=window.parent.document;var ls=d.querySelectorAll('link[rel*=\'icon\']');if(!ls||ls.length===0){var l=d.createElement('link');l.rel='shortcut icon';l.type='image/png';l.href=f;d.head.appendChild(l);}else{ls.forEach(function(l){l.type='image/png';l.href=f;});}}catch(e){}</script>"
                style="display:none;width:0;height:0;border:none;"></iframe>""",
        unsafe_allow_html=True,
    )




SECTION_ICONS: dict[str, str] = {
    "overview": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
        '<polyline points="9 22 9 12 15 12 15 22"/>'
        '</svg>'
    ),
    "discover": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10"/>'
        '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'
        '</svg>'
    ),
    "planner": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="6" cy="19" r="3"/>'
        '<circle cx="18" cy="5" r="3"/>'
        '<path d="M12 19h4.5a3.5 3.5 0 0 0 0-7h-9a3.5 3.5 0 0 1 0-7H12"/>'
        '</svg>'
    ),
    "compare": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<line x1="18" y1="20" x2="18" y2="10"/>'
        '<line x1="12" y1="20" x2="12" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="14"/>'
        '<path d="M2 20h20"/>'
        '</svg>'
    ),
    "datasets": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>'
        '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
        '</svg>'
    ),
    "insights": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
        '<polyline points="17 6 23 6 23 12"/>'
        '</svg>'
    ),
    "devlab": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M10 2v7.31L4.1 20.1A2 2 0 0 0 5.8 23h12.4a2 2 0 0 0 1.7-2.9L14 9.31V2"/>'
        '<line x1="8.5" y1="2" x2="15.5" y2="2"/>'
        '<line x1="6.8" y1="15" x2="17.2" y2="15"/>'
        '</svg>'
    ),
    "model": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
        '</svg>'
    ),
    "settings": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<line x1="4" y1="21" x2="4" y2="14"/>'
        '<line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/>'
        '<line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/>'
        '<line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/>'
        '</svg>'
    ),
    "information": (
        '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
        '<line x1="9" y1="7" x2="15" y2="7"/>'
        '<line x1="9" y1="11" x2="15" y2="11"/>'
        '</svg>'
    ),
}


def render_section_banner(
    section_key: str,
    title_html: str,
    subtitle: str = "",
    kicker: str = "",
) -> None:
    """Render an authoritative editorial section banner with aligned local SVG icon badge."""
    icon_svg = SECTION_ICONS.get(section_key.lower().strip(), "")
    kicker_part = f'<span class="cr-eyebrow-text">{kicker}</span>' if kicker else ""
    subtitle_part = f'<p class="cr-section-subtitle">{subtitle}</p>' if subtitle else ""

    html = f"""
    <div class="cr-section-banner">
        <div class="cr-section-eyebrow">
            <span class="cr-section-icon" aria-hidden="true">{icon_svg}</span>
            {kicker_part}
        </div>
        <h1 class="editorial-heading cr-section-title">{title_html}</h1>
        {subtitle_part}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_editorial_hero() -> None:
    """Render the editorial split hero with truthful demo actions, framed photo, and taped sticky note."""
    img_landscape = get_asset_base64("green-landscape.jpg")

    html = f"""
    <div class="hero-container">
        <div>
            <div class="eyebrow">Cultural tourism / India / DEV AAT</div>
            <h1 class="editorial-heading">Explore the culture<br>behind <em>every route.</em></h1>
            <svg class="hero-underline" viewBox="0 0 460 34" aria-hidden="true">
                <path d="M4 22C115 6 294 8 455 16M72 31c111-14 256-13 361-7"/>
            </svg>
            <div class="hero-actions">
                <a class="button" href="?view=discover">Explore Study Cities <span aria-hidden="true">↗</span></a>
                <a class="text-link" href="?view=devlab">See the DEV Lab Study <span aria-hidden="true">→</span></a>
            </div>
            <p class="hero-caption">
                An offline study of cultural tourism representation across 45 Indian cities,
                examining the balance between heritage preservation and travel efficiency.
            </p>
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px;">
                <span class="tag-synthetic">45 Indian Cities</span>
                <span class="tag-synthetic">675 Attractions</span>
                <span class="tag-synthetic">24 Canonical Tables</span>
                <span class="tag-synthetic">Zero External Network Calls</span>
            </div>
        </div>
        <div class="hero-right">
            <svg class="doodle-star" viewBox="0 0 100 100" aria-hidden="true">
                <path d="M50 4 59 34 88 15 72 43 99 52 69 59 83 88 55 70 45 99 40 68 8 82 29 55 1 43 34 40 20 11 46 31Z"/>
            </svg>
            <p class="hero-intro">
                Find heritage sites, museums, religious places, and food experiences.
                Then see how the route and the evidence come together.
            </p>
            <figure class="hero-photo">
                <img src="{img_landscape}" alt="Regional Indian landscape illustration" />
                <figcaption>A place to begin exploring</figcaption>
            </figure>
            <div class="sticky">
                45 cities to explore.<br>One route at a time.
                <span class="tape" aria-hidden="true"></span>
            </div>
        </div>
        <svg class="hero-arrow" viewBox="0 0 150 85" aria-hidden="true">
            <path d="M5 29c56-36 82 5 39 30-25 14-34-26 14-26 27 0 42 22 70 33m-17-17 17 17-23 4"/>
        </svg>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_scoped_stats(
    cities: int = 45,
    attractions: int = 675,
    trips: int = 411,
    rows: int = 48728,
    cultural_listings: str = "31.3%",
    cultural_actions: str = "31.3%",
    cultural_stops: str = "30.1%",
    weeks: int = 57,
) -> None:
    """Render the 8 audited scoped statistics in the prototype two-tier format."""
    html = f"""
    <section class="stats" aria-label="Project scope">
        <div class="stat">
            <strong>{cities}</strong>
            <span>Indian cities<br>in the study</span>
        </div>
        <div class="stat">
            <strong>{attractions}</strong>
            <span>listed attractions<br>in scope</span>
        </div>
        <div class="stat">
            <strong>{trips}</strong>
            <span>non-cancelled trips<br>in the analysis</span>
        </div>
        <div class="stat">
            <strong>{rows:,}</strong>
            <span>distinct source rows<br>across 24 tables</span>
        </div>
    </section>

    <section class="stats" style="margin-top: -30px; border-top: none;" aria-label="Cultural representation shares">
        <div class="stat">
            <strong>{cultural_listings}</strong>
            <span>Listings Cultural Share<br>211 of 675 catalog attractions</span>
        </div>
        <div class="stat">
            <strong>{cultural_actions}</strong>
            <span>Interaction Cultural Share<br>2,144 of 6,850 matched events</span>
        </div>
        <div class="stat">
            <strong>{cultural_stops}</strong>
            <span>Planned Cultural Share<br>961 of 3,191 selected stops</span>
        </div>
        <div class="stat">
            <strong>{weeks}</strong>
            <span>Complete Forecast Weeks<br>Last-12 MAE: 3.42 (last-week)</span>
        </div>
    </section>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_feature_grid() -> None:
    """Render the 2x2 architectural feature grid matching the prototype."""
    html = """
    <div style="margin-top: 30px;">
        <div class="eyebrow">01 / Discover and decide</div>
        <h2 class="editorial-heading" style="margin-top: 0;">Everything you need<br>to make a <em>day count</em></h2>
        <p style="color: var(--muted); max-width: 550px; margin-top: -5px; font-size: 0.95rem;">
            Find the places that interest you, check what a route can cover, and keep the method in view.
        </p>
    </div>
    <div class="feature-grid">
        <article class="feature">
            <span class="feature-icon" aria-hidden="true">01</span>
            <div>
                <h3>Directed Travel Matrix</h3>
                <p>
                    10 attractions per city feature recorded directed walking and cab legs in the synthetic travel matrix.
                    The remaining 5 attractions are preserved as discovery-only catalog entries. Missing legs are never guessed.
                </p>
            </div>
        </article>
        <article class="feature">
            <span class="feature-icon" aria-hidden="true">02</span>
            <div>
                <h3>Dual-Objective Day Planner</h3>
                <p>
                    Deterministic itinerary engine ranking feasible schedules for minimum elapsed time versus maximum
                    cultural stop representation. Reproduces the Jaipur Saturday specification baseline with exact currency and carbon accounting.
                </p>
            </div>
        </article>
        <article class="feature">
            <span class="feature-icon" aria-hidden="true">03</span>
            <div>
                <h3>Transparent Statistical Methods</h3>
                <p>
                    Classical Wilson score intervals, conjugate Beta(1,1) Bayesian posteriors, and maximum-likelihood lognormal
                    footfall estimation. Strictly rule-based and transparent without opaque AI/ML black boxes.
                </p>
            </div>
        </article>
        <article class="feature">
            <span class="feature-icon" aria-hidden="true">04</span>
            <div>
                <h3>Evaluator DEV Lab</h3>
                <p>
                    Full 24-table schema catalog profiling, guided pandas operations, SQLite authorizer-enforced read-only sandbox,
                    and formula-safe CSV/Parquet export engines covering all 5 syllabus units.
                </p>
            </div>
        </article>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_category_cards() -> None:
    """Render the four photographic category cards with lifted layout and golden-glow hover."""
    img_fort = get_asset_base64("heritage-fort.avif")
    img_museum = get_asset_base64("museum-interior.jpg")
    img_temple = get_asset_base64("golden-temple.jpg")
    img_food = get_asset_base64("local-food.jpg")

    html = f"""
    <div style="margin-top: 35px;">
        <div class="eyebrow">A little inspiration</div>
        <h2 class="editorial-heading" style="margin-top: 0;">Culture is in the <em>details</em></h2>
        <p style="color: var(--muted); max-width: 550px; margin-top: -5px; font-size: 0.95rem;">
            Categories the project studies across attraction listings, online interactions, and planned stops.
        </p>
    </div>
    <div class="place-grid">
        <article class="place-card">
            <div class="place-art">
                <img src="{img_fort}" alt="Historic stone fort rising above a city" loading="lazy" />
            </div>
            <span class="card-kicker">01 / Heritage &amp; Forts</span>
            <h3>Stories in stone</h3>
            <p>Explore historic places and see whether they make it into a feasible day plan. (72 catalog attractions, 34.1%)</p>
        </article>
        <article class="place-card lifted">
            <div class="place-art">
                <img src="{img_museum}" alt="Ornate heritage interior with decorative walls" loading="lazy" />
            </div>
            <span class="card-kicker">02 / Museums &amp; Galleries</span>
            <h3>Rooms to remember</h3>
            <p>Compare catalog presence with saves and selected itinerary stops. (53 catalog attractions, 25.1%)</p>
        </article>
        <article class="place-card">
            <div class="place-art">
                <img src="{img_temple}" alt="The Golden Temple and surrounding water in Amritsar" loading="lazy" />
            </div>
            <span class="card-kicker">03 / Religious Sites</span>
            <h3>Places of meaning</h3>
            <p>Explore living heritage and see how religious sites appear in planned stops. (48 catalog attractions, 22.7%)</p>
        </article>
        <article class="place-card">
            <div class="place-art">
                <img src="{img_food}" alt="Indian meal with curries, rice, bread, and snacks" loading="lazy" />
            </div>
            <span class="card-kicker">04 / Food Experiences</span>
            <h3>Local flavor, local context</h3>
            <p>Make room for food experiences in a schedule that respects time and budget. (38 catalog attractions, 18.0%)</p>
        </article>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_workflow_panel() -> None:
    """Render the 3-step workflow panel matching the prototype."""
    html = """
    <div class="workflow-panel">
        <div class="workflow-head">
            <h2 class="editorial-heading">How CultureRoute works</h2>
            <span>From a city to a route to its evidence</span>
        </div>
        <div class="steps">
            <div class="step">
                <b>1</b>
                <h3>Pick your place</h3>
                <p>Choose one of the 45 Indian study cities, visit date, start time, budget, and desired stop count.</p>
            </div>
            <div class="step">
                <b>2</b>
                <h3>Shape the day</h3>
                <p>Evaluate recorded directed matrix legs, attraction opening hours, wait times, and entry fees.</p>
            </div>
            <div class="step">
                <b>3</b>
                <h3>See the reasoning</h3>
                <p>Compare Plan A (fastest) against Plan B (most cultural stops). Trace numbers to source data.</p>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
