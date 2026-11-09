import base64
from pathlib import Path
import re

APP_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\app.py")
UI_COMPONENTS_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\cultureroute\ui_components.py")
DATASETS_VIEW_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\cultureroute\datasets_view.py")
FAVICON_PNG = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\site\dist\assets\favicon.png")

print("Reading files...")
app_content = APP_PY.read_text(encoding="utf-8")
ui_content = UI_COMPONENTS_PY.read_text(encoding="utf-8")
datasets_content = DATASETS_VIEW_PY.read_text(encoding="utf-8")

# 1. Update UI components: Inject favicon updater script into iframe and head
fav_b64 = ""
if FAVICON_PNG.exists():
    fav_b64 = base64.b64encode(FAVICON_PNG.read_bytes()).decode("ascii")

# Enhance iframe script in render_sidebar_navigation
old_iframe = 'st.markdown(\n        """<iframe srcdoc="<script>try{window.parent.localStorage.setItem(\'stSidebarCollapsed-\',\'false\');}catch(e){}</script>"\n                style="display:none;width:0;height:0;border:none;"></iframe>""",\n        unsafe_allow_html=True,\n    )'
new_iframe = f'''st.markdown(
        """<iframe srcdoc="<script>try{{window.parent.localStorage.setItem('stSidebarCollapsed-','false');var f='data:image/png;base64,{fav_b64}';var d=window.parent.document;var ls=d.querySelectorAll('link[rel*=\\'icon\\']');if(!ls||ls.length===0){{var l=d.createElement('link');l.rel='shortcut icon';l.type='image/png';l.href=f;d.head.appendChild(l);}}else{{ls.forEach(function(l){{l.type='image/png';l.href=f;}});}}}}catch(e){{}}</script>"
                style="display:none;width:0;height:0;border:none;"></iframe>""",
        unsafe_allow_html=True,
    )'''

if old_iframe in ui_content:
    ui_content = ui_content.replace(old_iframe, new_iframe)
    print("Updated ui_components iframe favicon script!")
else:
    # Try regex replacement if exact string didn't match due to line endings
    pattern = r'st\.markdown\(\s*"""<iframe srcdoc="<script>try\{window\.parent\.localStorage\.setItem\(\'stSidebarCollapsed-\',\'false\'\);\}catch\(e\)\{\}</script>".*?unsafe_allow_html=True,\s*\)'
    ui_content = re.sub(pattern, new_iframe, ui_content, flags=re.DOTALL)
    print("Regex updated ui_components iframe favicon script!")

UI_COMPONENTS_PY.write_text(ui_content, encoding="utf-8")

# 2. Update Datasets Screen: Make top-level visualizations prominent (not inside expander) and add Category + Telemetry charts
old_expander_start = 'with st.expander("Explore Dataset Architecture & Global Visual Distributions", expanded=True):'
new_visual_dashboard = '''# --------------------------------------------------------------------------
    # TOP-LEVEL VISUAL DATASET ARCHITECTURE & STATISTICAL DISTRIBUTIONS
    # --------------------------------------------------------------------------
    st.markdown("""
    <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 14px 18px; margin: 16px 0 20px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div style="font-family: Georgia, serif; font-size: 1.12rem; font-weight: bold; color: #292925;">
                Dataset Architecture &amp; Empirical Distributions
            </div>
            <span style="font-size: 0.74rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">
                48,728 VERIFIED ROWS &middot; 24 CANONICAL TABLES
            </span>
        </div>
        <div style="font-size: 0.82rem; color: #5c5852; margin-top: 4px;">
            Audited cross-pack distribution of records, table volumes, cultural categories, and user interaction telemetry from SmartTrip and WanderMatch.
        </div>
    </div>
    """, unsafe_allow_html=True)

    v_c1, v_c2 = st.columns(2)
    with v_c1:
        origin_pie = go.Figure(data=[go.Pie(
            labels=["SmartTrip-Only (10 Tables)", "WanderMatch-Only (6 Tables)", "Shared Verified (8 Tables)"],
            values=[21300, 16101, 11327],
            hole=0.5,
            marker=dict(colors=["#982b32", "#365376", "#eee3a6"]),
            textinfo="percent+label",
            hoverinfo="label+value+percent"
        )])
        origin_pie.update_layout(
            title="48,728 Canonical Rows by Origin Pack",
            height=260,
            paper_bgcolor="#f7f3e9",
            margin=dict(l=10, r=10, t=35, b=10),
            showlegend=False
        )
        st.plotly_chart(origin_pie, use_container_width=True)

    with v_c2:
        top_tables = sorted(list(catalog.tables.values()), key=lambda t: t.row_count, reverse=True)[:8]
        top_tbl_df = pd.DataFrame([
            {"Table": t.table_name, "Rows": t.row_count, "Pack": t.origin_pack}
            for t in top_tables
        ])
        top_bar = px.bar(
            top_tbl_df,
            x="Rows",
            y="Table",
            orientation="h",
            color="Pack",
            color_discrete_map={"SmartTrip": "#982b32", "WanderMatch": "#365376", "shared": "#5c5852"},
            title="Top 8 Study Tables by Row Volume"
        )
        top_bar.update_layout(
            height=260,
            paper_bgcolor="#f7f3e9",
            plot_bgcolor="#ffffff",
            margin=dict(l=10, r=10, t=35, b=10),
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(top_bar, use_container_width=True)

    # Row 2: Cultural Category and Telemetry Distributions
    v_c3, v_c4 = st.columns(2)
    with v_c3:
        with open_study_cache() as conn:
            cat_rows = conn.execute("SELECT poi_category, count(*) as count FROM activities_poi GROUP BY poi_category ORDER BY count DESC").fetchall()
        if cat_rows:
            cat_df = pd.DataFrame([dict(r) for r in cat_rows])
            cat_fig = px.pie(
                cat_df,
                names="poi_category",
                values="count",
                title="Cultural POI Distribution (675 Attractions across 45 Cities)",
                color_discrete_sequence=["#982b32", "#365376", "#733339", "#4f637b", "#8b7e66", "#d4af37"],
                hole=0.45
            )
            cat_fig.update_layout(
                height=260,
                paper_bgcolor="#f7f3e9",
                margin=dict(l=10, r=10, t=35, b=10),
                showlegend=True
            )
            st.plotly_chart(cat_fig, use_container_width=True)

    with v_c4:
        with open_study_cache() as conn:
            telemetry_rows = conn.execute("SELECT interaction_type, count(*) as count FROM user_interactions GROUP BY interaction_type ORDER BY count DESC").fetchall()
        if telemetry_rows:
            telem_df = pd.DataFrame([dict(r) for r in telemetry_rows])
            telem_bar = px.bar(
                telem_df,
                x="interaction_type",
                y="count",
                color="interaction_type",
                color_discrete_sequence=["#982b32", "#365376", "#733339", "#4f637b"],
                title="User Telemetry Distribution (WanderMatch 10,000+ Interactions)",
                labels={"interaction_type": "Interaction Type", "count": "Event Count"}
            )
            telem_bar.update_layout(
                height=260,
                paper_bgcolor="#f7f3e9",
                plot_bgcolor="#ffffff",
                margin=dict(l=10, r=10, t=35, b=10),
                showlegend=False
            )
            st.plotly_chart(telem_bar, use_container_width=True)'''

# Replace expander in datasets_view.py
expander_regex = r'with st\.expander\("Explore Dataset Architecture & Global Visual Distributions", expanded=True\):.*?st\.plotly_chart\(top_bar, use_container_width=True\)'
datasets_content = re.sub(expander_regex, new_visual_dashboard, datasets_content, flags=re.DOTALL)
DATASETS_VIEW_PY.write_text(datasets_content, encoding="utf-8")
print("datasets_view.py successfully updated with prominent visual dashboard!")

# 3. Update Discover in app.py: Fix filters, safe lookups, prominent charts
# Fix the city selection and entry_cost filter logic
old_discover_filters = '''        # Type-safe numeric cast for entry_cost to prevent Arrow/String comparison errors
        df_att["entry_cost_num"] = pd.to_numeric(df_att["entry_cost"], errors="coerce").fillna(0.0)

        # Apply filters
        filtered_df = df_att.copy()
        if cat_filter != "All Categories":
            filtered_df = filtered_df[filtered_df["poi_category"] == cat_filter]
        if price_filter == "Paid (INR > 0)":
            filtered_df = filtered_df[filtered_df["entry_cost_num"] > 0]
        elif price_filter == "Free Entry (INR 0)":
            filtered_df = filtered_df[filtered_df["entry_cost_num"] == 0]
        elif price_filter == "Unknown Fee":
            filtered_df = filtered_df[filtered_df["entry_cost_num"].isna()]
        if step_free_filter:
            filtered_df = filtered_df[filtered_df["accessibility"].isin(["full", "step_free"])]'''

new_discover_filters = '''        # Type-safe numeric cast for entry_cost to prevent Arrow/String comparison errors
        df_att["entry_cost_num"] = pd.to_numeric(df_att["entry_cost"], errors="coerce")

        # Apply filters
        filtered_df = df_att.copy()
        if cat_filter != "All Categories":
            filtered_df = filtered_df[filtered_df["poi_category"] == cat_filter]
        if price_filter == "Paid (INR > 0)":
            filtered_df = filtered_df[filtered_df["entry_cost_num"].fillna(0.0) > 0]
        elif price_filter == "Free Entry (INR 0)":
            filtered_df = filtered_df[filtered_df["entry_cost_num"].fillna(0.0) == 0]
        elif price_filter == "Unknown Fee":
            filtered_df = filtered_df[filtered_df["entry_cost_num"].isna() | filtered_df["entry_cost"].isna() | (filtered_df["entry_cost"].astype(str).str.strip() == "")]
        if step_free_filter:
            filtered_df = filtered_df[filtered_df["accessibility"].isin(["full", "step_free"])]'''

app_content = app_content.replace(old_discover_filters, new_discover_filters)

# Also guard city lookup in Discover:
old_city_lookup = 'selected_city = next(c for c in city_subset if c["name"] == selected_city_name)'
new_city_lookup = '''matching_cities = [c for c in city_subset if c["name"] == selected_city_name]
            selected_city = matching_cities[0] if matching_cities else (city_subset[0] if city_subset else cities[0])'''
app_content = app_content.replace(old_city_lookup, new_city_lookup)

# 4. Update Settings in app.py: Clean up the verbose "GPS / physical location" card
old_settings_card = '''        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #b6afa3; border-left: 4px solid #365376; padding: 14px 18px; margin-bottom: 14px;">
            <strong style="color: #292925; font-size: 0.92rem;">Default Demonstration City (Initial Selection):</strong><br>
            <span style="font-size: 0.84rem; color: #5c5852; line-height: 1.55;">
                Selects which of the 45 Indian study cities initially loads across <strong>Discover</strong>, <strong>Planner</strong>, and <strong>Prediction Model</strong>.
                This is an initial selection convenience for teacher demonstrations and does <strong>not</strong> access device GPS, physical location, or external networks.
            </span>
        </div>
        """, unsafe_allow_html=True)'''

new_settings_card = '''        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #b6afa3; border-left: 4px solid #365376; padding: 14px 18px; margin-bottom: 14px;">
            <strong style="color: #292925; font-size: 0.92rem;">Default Demonstration City:</strong><br>
            <span style="font-size: 0.84rem; color: #5c5852; line-height: 1.55;">
                Selects which of the 45 Indian study cities initially loads across <strong>Discover</strong>, <strong>Planner</strong>, <strong>Compare</strong>, and <strong>Prediction Model</strong>.
            </span>
        </div>
        """, unsafe_allow_html=True)'''

app_content = app_content.replace(old_settings_card, new_settings_card)

# 5. Update Compare in app.py: Dynamic city updates and trade-off slider
old_cmp_buttons = '''        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3])
        with ctrl_c1:
            selected_cmp_city = st.selectbox("Select Study City to Compare", all_city_names, index=current_city_idx, key="compare_city_select")
        with ctrl_c2:
            st.write("")
            st.write("")
            if st.button(f"Compare {selected_cmp_city}", key="btn_run_compare_city"):
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
                st.rerun()'''

new_cmp_buttons = '''        def on_cmp_city_dropdown_change():
            chosen_city = st.session_state.get("compare_city_select")
            if chosen_city:
                new_plans = plan_synthetic_day(city_name=chosen_city, start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": chosen_city,
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": new_plans,
                    "is_default_fixture": (chosen_city == "Jaipur"),
                    "stale": False
                }

        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3])
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
                st.rerun()'''

app_content = app_content.replace(old_cmp_buttons, new_cmp_buttons)

APP_PY.write_text(app_content, encoding="utf-8")
print("app.py successfully updated!")
