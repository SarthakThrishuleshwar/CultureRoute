"""Script to eliminate scrolling in the sidebar by streamlining vertical geometry
and suppressing scrollbars.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_FILE = ROOT / "cultureroute" / "ui_components.py"

def run():
    text = UI_FILE.read_text(encoding="utf-8")

    # 1. Update the sidebar container styling to completely remove overflow and scrollbars
    old_sidebar_base = """    /* Expanded Sidebar: 260px width with rich branding and full navigation */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
        position: relative !important;
        transform: none !important;
        transition: width 0.22s cubic-bezier(0.16, 1, 0.3, 1), min-width 0.22s cubic-bezier(0.16, 1, 0.3, 1), max-width 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }"""

    new_sidebar_base = """    /* Completely eliminate sidebar scrolling and hide scrollbars */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        overflow: hidden !important;
        overflow-y: hidden !important;
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }

    [data-testid="stSidebarContent"]::-webkit-scrollbar,
    [data-testid="stSidebarUserContent"]::-webkit-scrollbar,
    section[data-testid="stSidebar"]::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Eliminate Streamlit's default 96px bottom padding on sidebar */
    [data-testid="stSidebarUserContent"] {
        padding-bottom: 8px !important;
        padding-top: 0 !important;
    }

    /* Hide empty logo spacer & shrink header to prevent height waste */
    [data-testid="stLogoSpacer"] {
        display: none !important;
    }
    [data-testid="stSidebarHeader"] {
        padding: 4px 10px 0 !important;
        min-height: 0 !important;
        height: 24px !important;
        margin-bottom: 2px !important;
    }

    /* Expanded Sidebar: 260px width with rich branding and full navigation */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
        position: relative !important;
        transform: none !important;
        transition: width 0.22s cubic-bezier(0.16, 1, 0.3, 1), min-width 0.22s cubic-bezier(0.16, 1, 0.3, 1), max-width 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }"""

    # Account for double curly braces if f-string
    old_target = old_sidebar_base.replace("{", "{{").replace("}", "}}")
    new_target = new_sidebar_base.replace("{", "{{").replace("}", "}}")
    assert old_target in text, "Could not find old_sidebar_base in ui_components.py"
    text = text.replace(old_target, new_target)

    # 2. Update brand, nav groups, and nav links in CSS
    old_brand_css = """    .cr-sidebar-brand {
        padding: 6px 0 16px;
        border-bottom: 2px solid var(--line);
        margin-bottom: 16px;
    }

    .cr-brand-title {
        font-family: var(--display);
        font-size: 1.85rem;
        font-weight: 500;
        letter-spacing: -0.06em;
        line-height: 1.1;
        color: var(--ink);
    }

    .cr-brand-title span {
        color: var(--red);
    }

    .cr-brand-subtitle {
        font-family: var(--body);
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-top: 4px;
    }

    .cr-nav-group {
        margin-bottom: 16px;
    }

    .cr-nav-group-title {
        font-family: var(--body);
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--muted);
        padding: 0 4px 6px;
        border-bottom: 1px solid rgba(182, 175, 163, 0.4);
        margin-bottom: 6px;
    }

    /* High Specificity: Strip default blue link colors and underlines from sidebar */
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] a:link,
    [data-testid="stSidebar"] a:visited,
    [data-testid="stSidebar"] .stMarkdown a,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a,
    [data-testid="stSidebar"] a.cr-nav-link,
    a.cr-nav-link,
    .cr-nav-link {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 9px 12px !important;
        margin: 4px 0 !important;
        text-decoration: none !important;
        color: var(--ink) !important;
        font-family: var(--display) !important;
        font-size: 1.04rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em !important;
        border-radius: 3px !important;
        border: 1px solid transparent !important;
        border-bottom: 1px dashed var(--line) !important;
        background-color: transparent !important;
        transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease, border-left-color 0.2s ease !important;
        cursor: pointer !important;
    }"""

    new_brand_css = """    .cr-sidebar-brand {
        padding: 2px 0 8px;
        border-bottom: 1.5px solid var(--line);
        margin-bottom: 8px;
    }

    .cr-brand-title {
        font-family: var(--display);
        font-size: 1.45rem;
        font-weight: 500;
        letter-spacing: -0.05em;
        line-height: 1.1;
        color: var(--ink);
        margin: 0;
    }

    .cr-brand-title span {
        color: var(--red);
    }

    .cr-brand-subtitle {
        font-family: var(--body);
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 2px;
    }

    .cr-nav-group {
        margin-bottom: 6px;
    }

    .cr-nav-group-title {
        font-family: var(--body);
        font-size: 0.60rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        padding: 0 4px 2px;
        border-bottom: 1px solid rgba(182, 175, 163, 0.4);
        margin-bottom: 2px;
    }

    /* High Specificity: Strip default blue link colors and underlines from sidebar */
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] a:link,
    [data-testid="stSidebar"] a:visited,
    [data-testid="stSidebar"] .stMarkdown a,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a,
    [data-testid="stSidebar"] a.cr-nav-link,
    a.cr-nav-link,
    .cr-nav-link {
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
    }"""

    old_target_brand = old_brand_css.replace("{", "{{").replace("}", "}}")
    new_target_brand = new_brand_css.replace("{", "{{").replace("}", "}}")
    assert old_target_brand in text, "Could not find old_brand_css in ui_components.py"
    text = text.replace(old_target_brand, new_target_brand)

    # 3. Streamline the Study Data Boundary Sticky Note HTML
    old_sticky = """    <div class="sticky" style="background: #eee3a6; padding: 16px 14px 14px; font-family: 'Segoe Print', 'Comic Sans MS', 'Trebuchet MS', cursive; font-size: 0.78rem; line-height: 1.45; color: #292925; transform: rotate(-1.5deg); position: relative; margin: 25px 4px 15px; box-shadow: 2px 4px 8px rgba(50, 43, 28, 0.12); border: 1px solid #dfd6a8;">
        <span class="tape" style="position: absolute; width: 55px; height: 16px; background: rgba(237, 230, 194, 0.8); top: -8px; left: 50%; transform: translateX(-50%) rotate(2deg);"></span>
        <div style="font-size: 0.70rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #982b32; margin-bottom: 4px;">Study Data Boundary</div>
        <p style="margin: 0; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; font-size: 0.76rem; color: #292925;">
            Read-only SmartTrip & WanderMatch packs. 45 Indian cities. Zero external network calls.
        </p>
    </div>"""

    new_sticky = """    <div class="sticky" style="background: #eee3a6; padding: 8px 10px; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; font-size: 0.70rem; line-height: 1.3; color: #292925; transform: rotate(-1deg); position: relative; margin: 8px 2px 4px; box-shadow: 1px 2px 5px rgba(50, 43, 28, 0.10); border: 1px solid #dfd6a8;">
        <span class="tape" style="position: absolute; width: 36px; height: 10px; background: rgba(237, 230, 194, 0.8); top: -5px; left: 50%; transform: translateX(-50%) rotate(1.5deg);"></span>
        <div style="font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #982b32; margin-bottom: 2px;">Study Data Boundary</div>
        <p style="margin: 0; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; font-size: 0.68rem; line-height: 1.25; color: #292925;">
            Read-only SmartTrip & WanderMatch packs. 45 Indian cities. Zero external network calls.
        </p>
    </div>"""

    assert old_sticky in text, "Could not find old_sticky in ui_components.py"
    text = text.replace(old_sticky, new_sticky)

    UI_FILE.write_text(text, encoding="utf-8")
    print("Sidebar streamlined and scrolling eliminated successfully!")

if __name__ == "__main__":
    run()
