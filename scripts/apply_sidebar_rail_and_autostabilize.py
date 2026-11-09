"""Script to apply Collapsible Mini-Sidebar Rail and UI/UX Auto-Stabilization.

1. Sidebar Rail Mode:
   - When collapsed ([data-collapsed="true"]), sidebar becomes a 68px slim icon rail.
   - SVGs remain visible, centered, and fully interactive in both states.
   - Brand title shows 'CR' monogram glyph when collapsed; full title when expanded.
   - Floating circular toggle button with chevron arrow positioned cleanly on the sidebar right border.
   - Zero wasted space on the left when collapsed: main content dynamically takes calc(100% - 68px).

2. Auto-Stabilization:
   - Fluid block container padding: clamp(1.2rem, 2.5vw, 2.5rem).
   - Horizontal column wrapping and auto-stabilization.

3. Spacing & Overlap Fixes:
   - Chart legends positioned with ample breathing space (below axis or separated margin) preventing title collisions.
   - Compare screen and Discover filter columns aligned with vertical_alignment="bottom", removing empty st.write hacks.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_FILE = ROOT / "cultureroute" / "ui_components.py"
APP_FILE = ROOT / "app.py"
INSIGHTS_FILE = ROOT / "cultureroute" / "insights_view.py"
MODEL_FILE = ROOT / "cultureroute" / "model_view.py"

def update_ui_components():
    text = UI_FILE.read_text(encoding="utf-8")
    if "SIDEBAR THEME & CONTROLS: COLLAPSIBLE MINI-RAIL & EXPANDED VIEWS" in text:
        print("ui_components.py already updated!")
        return

    # 1. Replace the sidebar controls CSS block
    target_block_start = "    /* Sidebar Theme & Controls (fully supporting native open/close toggle) */"
    target_block_end = "    /* Flat Paper Surface (Dot texture removed per Stage F1) */"

    idx_start = text.find(target_block_start)
    idx_end = text.find(target_block_end)
    assert idx_start != -1, "Could not find target_block_start in ui_components.py"
    assert idx_end != -1, "Could not find target_block_end in ui_components.py"

    new_sidebar_css = """    /* =========================================================================
       SIDEBAR THEME & CONTROLS: COLLAPSIBLE MINI-RAIL & EXPANDED VIEWS
       ========================================================================= */

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

"""
    text = text[:idx_start] + new_sidebar_css + text[idx_end:]

    # 2. Remove the old duplicate min-width: 280px rule
    old_duplicate_minwidth = """    /* Sidebar Navigation System */
    [data-testid="stSidebar"] {
        background-color: #f0ebe0 !important;
        border-right: 1.5px solid var(--line) !important;
        box-shadow: 2px 0 12px rgba(41, 41, 37, 0.06) !important;
        min-width: 280px !important;
    }"""
    # handle both single and double braces if present
    text = text.replace(old_duplicate_minwidth, "    /* Sidebar Navigation System */")
    text = text.replace(old_duplicate_minwidth.replace("{", "{{").replace("}", "}}"), "    /* Sidebar Navigation System */")

    # 3. Update brand title in render_sidebar_navigation
    old_brand = '<div class="cr-brand-title">Culture<span>Route</span></div>'
    new_brand = '<div class="cr-brand-title" title="CultureRoute"><span class="cr-brand-full">Culture<span>Route</span></span><span class="cr-brand-mini">CR</span></div>'
    text = text.replace(old_brand, new_brand)

    # 4. Add title="{label}" to nav links
    old_link = 'html += f\'<a href="?view={key}" target="_self"{active_attr}>{icon_svg}<span>{label}</span></a>\''
    new_link = 'html += f\'<a href="?view={key}" target="_self"{active_attr} title="{label}">{icon_svg}<span>{label}</span></a>\''
    text = text.replace(old_link, new_link)

    UI_FILE.write_text(text, encoding="utf-8")
    print("Updated cultureroute/ui_components.py successfully!")

def update_app():
    text = APP_FILE.read_text(encoding="utf-8")

    # 1. Discover filters: vertical_alignment="bottom" and remove st.write
    old_fc = """            # Filters with reset option
            fc1, fc2, fc3, fc4 = st.columns([1.3, 1.3, 1.4, 0.8])
            with fc1:
                cat_filter = st.selectbox("Category Filter", ["All Categories", "heritage", "museum", "religious", "food", "entertainment", "nature"], key="discover_cat_filter")
            with fc2:
                price_filter = st.selectbox("Fee Status", ["All Prices", "Paid (INR > 0)", "Free Entry (INR 0)", "Unknown Fee"], key="discover_price_filter")
            with fc3:
                step_free_filter = st.checkbox("Step-Free Only", value=False, key="discover_step_free")
            with fc4:
                st.write("")
                st.write("")
                st.button("Reset", key="btn_reset_discover_filters", on_click=reset_discover_filters)"""

    new_fc = """            # Filters with reset option
            fc1, fc2, fc3, fc4 = st.columns([1.3, 1.3, 1.4, 0.8], vertical_alignment="bottom")
            with fc1:
                cat_filter = st.selectbox("Category Filter", ["All Categories", "heritage", "museum", "religious", "food", "entertainment", "nature"], key="discover_cat_filter")
            with fc2:
                price_filter = st.selectbox("Fee Status", ["All Prices", "Paid (INR > 0)", "Free Entry (INR 0)", "Unknown Fee"], key="discover_price_filter")
            with fc3:
                step_free_filter = st.checkbox("Step-Free Only", value=False, key="discover_step_free")
            with fc4:
                st.button("Reset", key="btn_reset_discover_filters", on_click=reset_discover_filters)"""
    assert old_fc in text, "Could not find old_fc in app.py"
    text = text.replace(old_fc, new_fc)

    # 2. Discover Ranked Distance bar chart: prevent title/legend collision
    old_bar_layout = """                    fig_bar.update_layout(
                        height=calc_h,
                        paper_bgcolor="#f7f3e9",
                        plot_bgcolor="#ffffff",
                        yaxis=dict(autorange="reversed", title=""),
                        xaxis=dict(title="Distance from City Center (km)"),
                        margin=dict(l=20, r=40, t=40, b=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )"""

    new_bar_layout = """                    fig_bar.update_layout(
                        height=calc_h + 30,
                        paper_bgcolor="#f7f3e9",
                        plot_bgcolor="#ffffff",
                        yaxis=dict(autorange="reversed", title=""),
                        xaxis=dict(title="Distance from City Center (km)"),
                        margin=dict(l=20, r=30, t=55, b=65),
                        title=dict(
                            text=f"{selected_city_name} Attractions Ranked by Distance from City Center",
                            x=0,
                            y=0.96,
                            font=dict(size=14, color="#292925")
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.18,
                            xanchor="center",
                            x=0.5,
                            title_text=""
                        )
                    )"""
    assert old_bar_layout in text, "Could not find old_bar_layout in app.py"
    text = text.replace(old_bar_layout, new_bar_layout)

    # 3. Discover Geographic map: prevent title/legend collision
    old_map_layout = """                        fig_map.update_layout(
                            height=440,
                            paper_bgcolor="#f7f3e9",
                            margin=dict(l=0, r=0, t=40, b=0),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )"""

    new_map_layout = """                        fig_map.update_layout(
                            height=460,
                            paper_bgcolor="#f7f3e9",
                            margin=dict(l=0, r=0, t=55, b=55),
                            title=dict(
                                text=f"{selected_city_name} Interactive Map (OpenStreetMap)",
                                x=0,
                                y=0.96,
                                font=dict(size=14, color="#292925")
                            ),
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.12,
                                xanchor="center",
                                x=0.5,
                                title_text=""
                            )
                        )"""
    assert old_map_layout in text, "Could not find old_map_layout in app.py"
    text = text.replace(old_map_layout, new_map_layout)

    # 4. Compare controls: vertical_alignment="bottom" and remove st.write
    old_cmp_ctrl = """        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3])
        with ctrl_c1:
            selected_cmp_city = st.selectbox("Select Study City to Compare", all_city_names, index=current_city_idx, key="compare_city_select", on_change=on_cmp_city_dropdown_change)
        with ctrl_c2:
            st.write("")
            st.write("")
            if st.button(f"Recalculate {selected_cmp_city}", key="btn_run_compare_city"):
                new_plans = plan_synthetic_day(city_name=selected_cmp_city, start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": selected_cmp_city,
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": new_plans,
                    "is_default_fixture": (selected_cmp_city == "Jaipur"),
                    "stale": False
                }
                st.rerun()
        with ctrl_c3:
            st.write("")
            st.write("")
            if st.button("Load Jaipur Baseline", key="btn_load_jaipur_baseline_cmp"):
                jaipur_plans = plan_synthetic_day(city_name="Jaipur", start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": "Jaipur",
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": jaipur_plans,
                    "is_default_fixture": True,
                    "stale": False
                }
                st.rerun()
        with ctrl_c4:
            st.write("")
            st.write("")
            if st.button("Load Agra Preset (4 Stops)", key="btn_load_agra_preset_cmp"):"""

    new_cmp_ctrl = """        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3], vertical_alignment="bottom")
        with ctrl_c1:
            selected_cmp_city = st.selectbox("Select Study City to Compare", all_city_names, index=current_city_idx, key="compare_city_select", on_change=on_cmp_city_dropdown_change)
        with ctrl_c2:
            if st.button(f"Recalculate {selected_cmp_city}", key="btn_run_compare_city"):
                new_plans = plan_synthetic_day(city_name=selected_cmp_city, start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": selected_cmp_city,
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": new_plans,
                    "is_default_fixture": (selected_cmp_city == "Jaipur"),
                    "stale": False
                }
                st.rerun()
        with ctrl_c3:
            if st.button("Load Jaipur Baseline", key="btn_load_jaipur_baseline_cmp"):
                jaipur_plans = plan_synthetic_day(city_name="Jaipur", start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": "Jaipur",
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": jaipur_plans,
                    "is_default_fixture": True,
                    "stale": False
                }
                st.session_state["compare_city_select"] = "Jaipur"
                st.rerun()
        with ctrl_c4:
            if st.button("Load Agra Preset (4 Stops)", key="btn_load_agra_preset_cmp"):"""
    assert old_cmp_ctrl in text, "Could not find old_cmp_ctrl in app.py"
    text = text.replace(old_cmp_ctrl, new_cmp_ctrl)

    # 5. Compare direct trade-off bar chart: prevent title/legend collision
    old_cmp_bar = """        fig_cmp_bar.update_layout(
            barmode="group",
            height=280,
            paper_bgcolor="#f7f3e9",
            plot_bgcolor="#ffffff",
            margin=dict(l=20, r=20, t=30, b=20),
            title=f"Direct Trade-Off Comparison: Plan A vs Plan B ({cmp_city})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )"""

    new_cmp_bar = """        fig_cmp_bar.update_layout(
            barmode="group",
            height=300,
            paper_bgcolor="#f7f3e9",
            plot_bgcolor="#ffffff",
            margin=dict(l=20, r=20, t=55, b=50),
            title=dict(
                text=f"Direct Trade-Off Comparison: Plan A vs Plan B ({cmp_city})",
                x=0,
                y=0.96,
                font=dict(size=14, color="#292925")
            ),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5,
                title_text=""
            )
        )"""
    assert old_cmp_bar in text, "Could not find old_cmp_bar in app.py"
    text = text.replace(old_cmp_bar, new_cmp_bar)

    APP_FILE.write_text(text, encoding="utf-8")
    print("Updated app.py successfully!")

def update_insights():
    text = INSIGHTS_FILE.read_text(encoding="utf-8")
    old_p1 = """                plot_bgcolor="#ffffff",
                margin=dict(l=20, r=20, t=30, b=20),
                yaxis=dict(title="Percentage (%)", range=[0, 100]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )"""
    new_p1 = """                plot_bgcolor="#ffffff",
                margin=dict(l=20, r=20, t=50, b=45),
                yaxis=dict(title="Percentage (%)", range=[0, 100]),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title_text="")
            )"""
    assert old_p1 in text, "Could not find old_p1 in insights_view.py"
    text = text.replace(old_p1, new_p1)

    old_p2 = """                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title="Week Start (Monday)",
                yaxis_title="Cultural Interactions Count",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )"""
    new_p2 = """                margin=dict(l=20, r=20, t=50, b=45),
                xaxis_title="Week Start (Monday)",
                yaxis_title="Cultural Interactions Count",
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title_text="")
            )"""
    assert old_p2 in text, "Could not find old_p2 in insights_view.py"
    text = text.replace(old_p2, new_p2)

    INSIGHTS_FILE.write_text(text, encoding="utf-8")
    print("Updated cultureroute/insights_view.py successfully!")

def update_model():
    text = MODEL_FILE.read_text(encoding="utf-8")
    old_m = """                height=340,
                paper_bgcolor="#f7f3e9",
                plot_bgcolor="#ffffff",
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(title="Error (Interactions / City-Week)", range=[0, 1.6]),
            )"""
    new_m = """                height=340,
                paper_bgcolor="#f7f3e9",
                plot_bgcolor="#ffffff",
                margin=dict(l=20, r=20, t=50, b=45),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title_text=""),
                yaxis=dict(title="Error (Interactions / City-Week)", range=[0, 1.6]),
            )"""
    assert old_m in text, "Could not find old_m in model_view.py"
    text = text.replace(old_m, new_m)

    MODEL_FILE.write_text(text, encoding="utf-8")
    print("Updated cultureroute/model_view.py successfully!")

if __name__ == "__main__":
    update_ui_components()
    update_app()
    update_insights()
    update_model()
    print("All updates successfully completed!")
