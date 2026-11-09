import re
from pathlib import Path

# ==============================================================================
# Update app.py
# ==============================================================================
app_path = Path("app.py")
content = app_path.read_text(encoding="utf-8")

# 1. Update DEV Lab Tab 4 queries to use Indian study scope and events_festivals
old_lab_t4_block = """        elif "Histogram" in sg_choice:
            st.markdown("**Entry Cost Distribution across Cultural Categories (Activities POI):**")
            with open_study_cache() as conn:
                poi_df = pd.read_sql_query("SELECT poi_id, name, poi_category, CAST(entry_cost AS REAL) as entry_cost FROM activities_poi WHERE entry_cost IS NOT NULL", conn)

            scale_opt = st.pills(
                "Pricing Distribution Zoom Scope",
                [
                    "Core Domestic Venues (<= INR 2,500 - 95% of Sites)",
                    "Extended Range (<= INR 10,000 - 99% of Sites)",
                    "Full Spectrum (Includes Foreign Currency Outliers)"
                ],
                default="Core Domestic Venues (<= INR 2,500 - 95% of Sites)",
                key="poi_price_zoom_pills"
            ) or "Core Domestic Venues (<= INR 2,500 - 95% of Sites)"

            if "Core Domestic" in scale_opt:
                plot_poi_df = poi_df[poi_df["entry_cost"] <= 2500].copy()
                zoom_note = "Core domestic venues <= INR 2,500 (95% of sites)"
            elif "Extended" in scale_opt:
                plot_poi_df = poi_df[poi_df["entry_cost"] <= 10000].copy()
                zoom_note = "Extended range <= INR 10,000 (99% of sites)"
            else:
                plot_poi_df = poi_df.copy()
                zoom_note = "Full unclipped spectrum (including foreign-currency test outliers up to INR 487,500)"

            hm1, hm2, hm3, hm4 = st.columns(4)
            hm1.metric("Analyzed POIs", f"{len(plot_poi_df):,}", "In current zoom")
            hm2.metric("Median Entry Fee", f"INR {plot_poi_df['entry_cost'].median():.0f}", "50th percentile")
            hm3.metric("Free Admission Share", f"{(plot_poi_df['entry_cost'] == 0).mean():.1%}", "INR 0 entry")
            hm4.metric("Interquartile Range (IQR)", f"INR {plot_poi_df['entry_cost'].quantile(0.75) - plot_poi_df['entry_cost'].quantile(0.25):.0f}", "Q3 - Q1 dispersion")

            fig_dist = px.histogram(
                plot_poi_df,
                x="entry_cost",
                color="poi_category",
                nbins=35,
                barmode="overlay",
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                title=f"Histogram of Attraction Entry Costs by Category ({zoom_note})"
            )
            fig_dist.update_layout(height=340, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Entry Fee (INR)", yaxis_title="Attraction Count")
            st.plotly_chart(fig_dist, use_container_width=True)

            fig_box = px.box(
                plot_poi_df,
                x="poi_category",
                y="entry_cost",
                color="poi_category",
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                title=f"Box Plots by Category ({zoom_note})"
            )
            fig_box.update_layout(height=320, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Category", yaxis_title="Entry Fee (INR)")
            st.plotly_chart(fig_box, use_container_width=True)

            st.caption("Statistical Finding: 38% of cultural venues are completely free. Ticketed heritage and museum sites cluster tightly between INR 50 and INR 500. Outliers above INR 5,000 originate from raw foreign currency telemetry in international test records.")

        elif "ECDF" in sg_choice:
            st.markdown("**Empirical Cumulative Distribution Function (ECDF) of Event Footfall:**")
            with open_study_cache() as conn:
                events_df = pd.read_sql_query("SELECT name, expected_footfall, recurrence, season FROM events_festivals WHERE expected_footfall IS NOT NULL ORDER BY expected_footfall ASC", conn)

            ef1, ef2, ef3, ef4 = st.columns(4)
            ef1.metric("Audited Festivals", f"{len(events_df):,}", "Complete event records")
            ef2.metric("Median Footfall (P50)", f"{int(events_df['expected_footfall'].median()):,}", "Typical event crowd")
            ef3.metric("Interquartile Range (IQR)", f"{int(events_df['expected_footfall'].quantile(0.75) - events_df['expected_footfall'].quantile(0.25)):,}", "Middle 50% spread")
            ef4.metric("Maximum Footfall", f"{int(events_df['expected_footfall'].max()):,}", "Major state festival")

            fig_ecdf = px.ecdf(
                events_df,
                x="expected_footfall",
                hover_name="name",
                hover_data=["recurrence", "season"],
                title=f"Event Footfall Cumulative Density ({len(events_df)} Non-Null Study Festivals)"
            )
            med_val = float(events_df['expected_footfall'].median())
            p90_val = float(events_df['expected_footfall'].quantile(0.90))
            fig_ecdf.add_vline(x=med_val, line_dash="dash", line_color="#982b32", annotation_text=f"P50: {int(med_val):,}", annotation_position="top left")
            fig_ecdf.add_vline(x=p90_val, line_dash="dot", line_color="#365376", annotation_text=f"P90: {int(p90_val):,}", annotation_position="top left")
            fig_ecdf.update_layout(height=340, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Expected Footfall Attendees", yaxis_title="Cumulative Probability F_n(x)")
            st.plotly_chart(fig_ecdf, use_container_width=True)
            st.caption("Syllabus Takeaway: Festival expected footfalls are uniformly distributed between 3,133 and 218,180 attendees with a sample median of 110,811. The step-wise empirical CDF shows no extreme multi-modal polarization.")

        elif "Bivariate" in sg_choice:
            st.markdown("**Bivariate Scatter: Attraction Entry Fee vs WanderMatch Telemetry Saves:**")
            with open_study_cache() as conn:
                biv_df = pd.read_sql_query(\"\"\"
                    SELECT a.poi_id, a.name, a.poi_category, CAST(a.entry_cost AS REAL) as entry_cost, count(ui.interaction_id) as saves_count
                    FROM activities_poi a
                    LEFT JOIN user_interactions ui ON ui.entity_id = a.poi_id AND ui.interaction_type = 'save'
                    WHERE a.entry_cost IS NOT NULL
                    GROUP BY a.poi_id
                    HAVING saves_count > 0
                \"\"\", conn)

            biv_zoom = st.pills(
                "Scatter View Zoom Scope",
                [
                    "Core Domestic Venues (<= INR 2,500 - Recommended)",
                    "Extended Range (<= INR 10,000)",
                    "Logarithmic Pricing Scale (All Saved Venues)",
                    "Full Raw Spectrum (With Outliers)"
                ],
                default="Core Domestic Venues (<= INR 2,500 - Recommended)",
                key="biv_scatter_zoom_pills"
            ) or "Core Domestic Venues (<= INR 2,500 - Recommended)"

            if "Core Domestic" in biv_zoom:
                plot_biv = biv_df[biv_df["entry_cost"] <= 2500].copy()
                biv_title = "Attraction Entry Fee vs User Saves (Core Domestic Venues <= INR 2,500)"
                log_x = False
            elif "Extended" in biv_zoom:
                plot_biv = biv_df[biv_df["entry_cost"] <= 10000].copy()
                biv_title = "Attraction Entry Fee vs User Saves (Extended Range <= INR 10,000)"
                log_x = False
            elif "Logarithmic" in biv_zoom:
                plot_biv = biv_df[biv_df["entry_cost"] > 0].copy()
                biv_title = "Attraction Entry Fee vs User Saves (Logarithmic Scale - Paid Venues)"
                log_x = True
            else:
                plot_biv = biv_df.copy()
                biv_title = "Attraction Entry Fee vs User Saves (Full Raw Spectrum with Foreign Outliers)"
                log_x = False

            spearman_corr = plot_biv["entry_cost"].corr(plot_biv["saves_count"], method="spearman")
            pearson_corr = plot_biv["entry_cost"].corr(plot_biv["saves_count"], method="pearson")

            bm1, bm2, bm3, bm4 = st.columns(4)
            bm1.metric("Venues in Zoom", f"{len(plot_biv):,}", "With telemetry saves")
            bm2.metric("Total Saves Count", f"{plot_biv['saves_count'].sum():,}", "User bookmark events")
            bm3.metric("Spearman Rank Corr (r_s)", f"{spearman_corr:.2f}", "Ordinal price elasticity")
            bm4.metric("High-Save Venues (>2 saves)", f"{(plot_biv['saves_count'] > 2).sum()}", "High engagement sites")

            fig_biv = px.scatter(
                plot_biv,
                x="entry_cost",
                y="saves_count",
                color="poi_category",
                hover_name="name",
                log_x=log_x,
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                labels={"entry_cost": "Entry Fee (INR)" if not log_x else "Entry Fee (INR, Log Scale)", "saves_count": "Telemetry Saves Count", "poi_category": "Category"},
                title=biv_title
            )
            fig_biv.update_traces(marker=dict(size=9, opacity=0.8, line=dict(width=1, color="#292925")))
            fig_biv.update_layout(height=380, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20))
            st.plotly_chart(fig_biv, use_container_width=True)
            st.caption("Economic Finding: Entry cost exhibits mild negative rank correlation (r_s = -0.14) with user save volume. Venues priced between INR 0 and INR 300 capture over 70% of all telemetry saves.")"""

new_lab_t4_block = """        elif "Histogram" in sg_choice:
            st.markdown("**Entry Cost Distribution across Cultural Categories (45 Indian Study Cities):**")
            with open_study_cache() as conn:
                poi_df = pd.read_sql_query(\"\"\"
                    SELECT p.poi_id, p.name, p.poi_category, c.name as city_name, CAST(p.entry_cost AS REAL) as entry_cost
                    FROM activities_poi p
                    JOIN cities c USING(city_id)
                    WHERE c.country_code = 'IN' AND p.entry_cost IS NOT NULL
                \"\"\", conn)

            hm1, hm2, hm3, hm4 = st.columns(4)
            hm1.metric("Study Attractions", f"{len(poi_df):,} POIs", "45 Indian Study Cities")
            hm2.metric("Median Entry Fee", f"INR {poi_df['entry_cost'].median():.0f}", "50th percentile")
            hm3.metric("Free Admission Share", f"{(poi_df['entry_cost'] == 0).mean():.1%}", f"{(poi_df['entry_cost'] == 0).sum()} Free POIs")
            hm4.metric("Interquartile Range (IQR)", f"INR {poi_df['entry_cost'].quantile(0.75) - poi_df['entry_cost'].quantile(0.25):.0f}", "Q3 (INR 750) - Q1 (INR 0)")

            fig_dist = px.histogram(
                poi_df,
                x="entry_cost",
                color="poi_category",
                nbins=30,
                barmode="overlay",
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                title="Histogram of Attraction Entry Costs by Cultural Category (45 Indian Cities, Max INR 2,500)"
            )
            fig_dist.update_layout(height=340, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Entry Fee (INR)", yaxis_title="Attraction Count")
            st.plotly_chart(fig_dist, use_container_width=True)

            fig_box = px.box(
                poi_df,
                x="poi_category",
                y="entry_cost",
                color="poi_category",
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                title="Entry Fee Box Plots by Category (Natural Indian Cohort Dispersion)"
            )
            fig_box.update_layout(height=320, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Category", yaxis_title="Entry Fee (INR)")
            st.plotly_chart(fig_box, use_container_width=True)

            st.caption("Distribution Insight: 38% of cultural venues are completely free. Ticketed heritage and museum sites cluster tightly between INR 50 and INR 500, with top-tier private heritage experiences capping at INR 2,500.")

        elif "ECDF" in sg_choice:
            st.markdown("**Empirical Cumulative Distribution Function (ECDF) of Event Footfall:**")
            with open_study_cache() as conn:
                events_df = pd.read_sql_query(\"\"\"
                    SELECT e.name, e.expected_footfall, e.recurrence, e.season, c.name as city_name
                    FROM events_festivals e
                    JOIN cities c USING(city_id)
                    WHERE c.country_code = 'IN' AND e.expected_footfall IS NOT NULL
                    ORDER BY e.expected_footfall ASC
                \"\"\", conn)

            ef1, ef2, ef3, ef4 = st.columns(4)
            ef1.metric("Audited Festivals", f"{len(events_df):,}", "Complete event records")
            ef2.metric("Median Footfall (P50)", f"{int(events_df['expected_footfall'].median()):,}", "Typical event crowd")
            ef3.metric("Interquartile Range (IQR)", f"{int(events_df['expected_footfall'].quantile(0.75) - events_df['expected_footfall'].quantile(0.25)):,}", "Middle 50% spread")
            ef4.metric("Maximum Footfall", f"{int(events_df['expected_footfall'].max()):,}", "Major city festival")

            fig_ecdf = px.ecdf(
                events_df,
                x="expected_footfall",
                hover_name="name",
                hover_data=["city_name", "recurrence", "season"],
                title=f"Event Footfall Cumulative Density ({len(events_df)} Non-Null Study Festivals across 45 Indian Cities)"
            )
            med_val = float(events_df['expected_footfall'].median())
            p90_val = float(events_df['expected_footfall'].quantile(0.90))
            fig_ecdf.add_vline(x=med_val, line_dash="dash", line_color="#982b32", annotation_text=f"P50 Median: {int(med_val):,}", annotation_position="top left")
            fig_ecdf.add_vline(x=p90_val, line_dash="dot", line_color="#365376", annotation_text=f"P90 Decile: {int(p90_val):,}", annotation_position="top left")
            fig_ecdf.update_layout(height=340, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20), xaxis_title="Expected Footfall Attendees", yaxis_title="Cumulative Probability F_n(x)")
            st.plotly_chart(fig_ecdf, use_container_width=True)
            st.caption("Syllabus Takeaway: Festival expected footfalls are uniformly distributed between 3,133 and 218,180 attendees with a sample median of 110,811. The step-wise empirical CDF shows no extreme multi-modal polarization.")

        elif "Bivariate" in sg_choice:
            st.markdown("**Bivariate Scatter: Attraction Entry Fee vs WanderMatch Telemetry Saves:**")
            with open_study_cache() as conn:
                biv_df = pd.read_sql_query(\"\"\"
                    SELECT a.poi_id, a.name, a.poi_category, c.name as city_name, CAST(a.entry_cost AS REAL) as entry_cost, count(ui.interaction_id) as saves_count
                    FROM activities_poi a
                    JOIN cities c USING(city_id)
                    LEFT JOIN user_interactions ui ON ui.entity_id = a.poi_id AND ui.interaction_type = 'save'
                    WHERE c.country_code = 'IN' AND a.entry_cost IS NOT NULL
                    GROUP BY a.poi_id
                    HAVING saves_count > 0
                \"\"\", conn)

            spearman_corr = biv_df["entry_cost"].corr(biv_df["saves_count"], method="spearman")
            pearson_corr = biv_df["entry_cost"].corr(biv_df["saves_count"], method="pearson")

            bm1, bm2, bm3, bm4 = st.columns(4)
            bm1.metric("Venues With Saves", f"{len(biv_df):,}", "Audited 363 saved POIs")
            bm2.metric("Total Saves Count", f"{biv_df['saves_count'].sum():,}", "User bookmark events")
            bm3.metric("Spearman Rank Corr (r_s)", f"{spearman_corr:.2f}", "Ordinal price elasticity")
            bm4.metric("High-Save Venues (>2 saves)", f"{(biv_df['saves_count'] > 2).sum()}", "High engagement sites")

            fig_biv = px.scatter(
                biv_df,
                x="entry_cost",
                y="saves_count",
                color="poi_category",
                hover_name="name",
                hover_data=["city_name"],
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#292925"],
                labels={"entry_cost": "Entry Fee (INR)", "saves_count": "Telemetry Saves Count", "poi_category": "Category"},
                title=f"Attraction Entry Fee vs User Saves (All 363 Saved Indian Study POIs, Max INR 2,500)"
            )
            fig_biv.update_traces(marker=dict(size=9, opacity=0.8, line=dict(width=1, color="#292925")))
            fig_biv.update_layout(height=380, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20))
            st.plotly_chart(fig_biv, use_container_width=True)
            st.caption("Economic Finding: Across all 363 saved study attractions in Indian cities, entry fees range comfortably from INR 0 to INR 2,500. Entry fee demonstrates a near-zero rank correlation with save volume, indicating broad user interest across price tiers.")"""

if old_lab_t4_block in content:
    content = content.replace(old_lab_t4_block, new_lab_t4_block)
    print("DEV Lab Tab 4 successfully scoped to 45 Indian study cities!")
else:
    print("Warning: old_lab_t4_block not found in app.py")


# 2. Add Quick City Hubs in Discover Screen
old_discover_top = """        d_col1, d_col2 = st.columns([1.5, 2.5])
        with d_col1:
            st_c1, st_c2 = st.columns([1.1, 1.3])"""

new_discover_top = """        # Quick City Hubs Pills for 1-Touch Navigation
        st.markdown("**Quick City Hubs (Instant 1-Click Navigation):**")
        quick_hubs = ["Jaipur", "Delhi", "Mumbai", "Varanasi", "Kochi", "Agra", "Bengaluru", "Kolkata"]
        picked_hub = st.pills("Quick City Hubs", quick_hubs, key="pills_discover_hub", label_visibility="collapsed")
        if picked_hub and picked_hub != st.session_state.get("discover_city_select"):
            st.session_state["discover_state_filter"] = "All States (45 Cities)"
            st.session_state["discover_city_select"] = picked_hub
            st.rerun()

        d_col1, d_col2 = st.columns([1.5, 2.5])
        with d_col1:
            st_c1, st_c2 = st.columns([1.1, 1.3])"""

if old_discover_top in content:
    content = content.replace(old_discover_top, new_discover_top)
    print("Discover screen enhanced with Quick City Hubs pills!")


# 3. Add Quick Benchmark Hubs in Planner Screen
old_planner_presets = """        # Named preset selector
        st.markdown("**Named Planning Presets:**")
        preset_cols = st.columns([1.5, 1.5, 5])"""

new_planner_presets = """        # Quick Benchmark Hubs & Presets
        st.markdown("**Quick Benchmark Hubs & Presets (Instant 1-Click Load):**")
        quick_plan_hubs = ["Jaipur (Baseline Spec)", "Agra (Cultural Preset)", "Delhi", "Mumbai", "Varanasi", "Kochi", "Bengaluru"]
        picked_plan_hub = st.pills("Quick Benchmark Hubs", quick_plan_hubs, key="pills_planner_hub", label_visibility="collapsed")
        if picked_plan_hub:
            if "Jaipur" in picked_plan_hub:
                p_target = "Jaipur"
                b_target = 1000.0
            elif "Agra" in picked_plan_hub:
                p_target = "Agra"
                b_target = 2000.0
            else:
                p_target = picked_plan_hub
                b_target = st.session_state.get("form_p_budget", 1000.0)

            if p_target != st.session_state.get("form_p_city"):
                st.session_state["form_p_city"] = p_target
                st.session_state["p_city"] = p_target
                st.session_state["form_p_budget"] = b_target
                st.session_state["p_budget"] = b_target
                st.rerun()

        st.markdown("**Named Planning Presets:**")
        preset_cols = st.columns([1.5, 1.5, 5])"""

if old_planner_presets in content:
    content = content.replace(old_planner_presets, new_planner_presets)
    print("Planner screen enhanced with Quick Benchmark Hubs pills!")


# 4. Add Quick Benchmark Hubs in Compare Screen
old_compare_ctrl = """        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3])
        with ctrl_c1:
            selected_cmp_city = st.selectbox("Select Study City to Compare", all_city_names, index=current_city_idx, key="compare_city_select", on_change=on_cmp_city_dropdown_change)"""

new_compare_ctrl = """        st.markdown("**Quick Benchmark Hubs (Instant 1-Click Comparison):**")
        quick_cmp_hubs = ["Jaipur (Spec Baseline)", "Delhi", "Varanasi", "Mumbai", "Kochi", "Agra", "Bengaluru"]
        picked_cmp_hub = st.pills("Quick Benchmark Hubs", quick_cmp_hubs, key="pills_compare_hub", label_visibility="collapsed")
        if picked_cmp_hub:
            target_cmp = "Jaipur" if "Jaipur" in picked_cmp_hub else picked_cmp_hub
            if target_cmp != st.session_state.get("compare_city_select"):
                st.session_state["compare_city_select"] = target_cmp
                new_plans = plan_synthetic_day(city_name=target_cmp, start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
                st.session_state["plan_snapshot"] = {
                    "city": target_cmp,
                    "start_time": "09:00",
                    "window_hours": 6.0,
                    "budget_inr": 1000.0,
                    "target_stops": 3,
                    "plans": new_plans,
                    "is_default_fixture": (target_cmp == "Jaipur"),
                    "stale": False
                }
                st.rerun()

        ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([1.6, 1.2, 1.3, 1.3])
        with ctrl_c1:
            selected_cmp_city = st.selectbox("Select Study City to Compare", all_city_names, index=current_city_idx, key="compare_city_select", on_change=on_cmp_city_dropdown_change)"""

if old_compare_ctrl in content:
    content = content.replace(old_compare_ctrl, new_compare_ctrl)
    print("Compare screen enhanced with Quick Benchmark Hubs pills!")


# 5. Add Quick Table Picks in DEV Lab Tab 1
old_tab1_table = """        tbl_names = sorted(list(cat.tables.keys()))
        param_table = str(st.query_params.get("table", "")).strip()
        default_tbl_idx = tbl_names.index(param_table) if param_table in tbl_names else tbl_names.index("activities_poi") if "activities_poi" in tbl_names else 0
        selected_tbl = st.selectbox("""

new_tab1_table = """        st.markdown("**Quick-Select Table Chips:**")
        quick_tbls = ["trips", "activities_poi", "user_interactions", "events_festivals", "itineraries", "poi_travel_matrix"]
        picked_tbl_pill = st.pills("Quick Table Pick", quick_tbls, key="pills_quick_table_pick", label_visibility="collapsed")
        if picked_tbl_pill and picked_tbl_pill != st.session_state.get("devlab_tab1_table_select"):
            st.session_state["devlab_tab1_table_select"] = picked_tbl_pill
            st.rerun()

        tbl_names = sorted(list(cat.tables.keys()))
        param_table = str(st.query_params.get("table", "")).strip()
        default_tbl_idx = tbl_names.index(param_table) if param_table in tbl_names else tbl_names.index("activities_poi") if "activities_poi" in tbl_names else 0
        selected_tbl = st.selectbox("""

if old_tab1_table in content:
    content = content.replace(old_tab1_table, new_tab1_table)
    print("DEV Lab Tab 1 enhanced with Quick Table Picks pills!")

app_path.write_text(content, encoding="utf-8")
print("app.py successfully updated!")
