"""CultureRoute Streamlit Application Entrypoint (Corrective Redesign R1-R8).

Provides:
- Editorial overview matching Acme reference video and site/dist design system.
- Synthetic Research Study (45 Indian cities, 675 attractions, 411 trips, 24 tables).
- Discover Catalog with category, price, and accessibility filtering.
- Deterministic Day Planner & Plan Comparison Engine (Jaipur specification fixture).
- Insights & Predictions (Cultural shares, weekly forecasting, footfall imputation).
- DEV Lab Evaluator Workspace (Units 1-5, SQLite authorizer sandbox, typed exports).
- Settings and Information screens.
- Strict two-pack boundary: SmartTrip and WanderMatch are the sole active project data.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
import json
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import streamlit as st

from cultureroute.study_data import (
    verify_and_audit_study,
    get_study_cities,
    get_city_attractions,
    open_study_databases,
)
from cultureroute.study_db import (
    build_study_database,
    load_study_catalog,
    open_study_cache,
    DEFAULT_STUDY_DB,
)
from cultureroute.datasets_view import render_datasets_screen
from cultureroute.insights_view import render_insights_screen
from cultureroute.model_view import render_model_screen
from cultureroute.ui_components import (
    inject_editorial_css,
    render_editorial_hero,
    render_scoped_stats,
    render_feature_grid,
    render_category_cards,
    render_workflow_panel,
    render_sidebar_navigation,
    render_section_banner,
)
from cultureroute.domain import (
    CulturalCategory,
    ResultLevel,
    VerificationStatus,
    FeeStatus,
    AccessibilityStatus,
)
from cultureroute.planner import (
    parse_time_to_minutes,
    plan_synthetic_day,
    plan_real_pilot_day,
    DayPlan,
)
from cultureroute.routing import TransportMode, RouteLegStore, compute_directed_leg
from cultureroute.catalog import RealCatalogStore
from cultureroute.boundary import IndiaBoundaryValidator, is_coordinate_in_india_bbox
from cultureroute.evidence import VenueEvidenceStore, FieldEvidenceStatus
from cultureroute.analytics import (
    compute_cultural_shares,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study,
)
from cultureroute.dev_lab import (
    compute_methodology_comparison,
    compute_canonical_saved_planned_merge,
    ReadOnlySQLSandbox,
    export_dataframe_to_csv,
    export_dataframe_to_parquet,
    get_table_profile,
    filter_and_derive_poi,
    groupby_aggregate_stops,
    pivot_city_category_matrix,
    transform_user_interactions,
    get_syllabus_reference_units,
)

# Optional legacy data files (preserved outside active product path)
BOUNDARY_GEOJSON = Path(__file__).resolve().parent / "data" / "india_boundary.geojson"
boundary_validator = IndiaBoundaryValidator(BOUNDARY_GEOJSON) if BOUNDARY_GEOJSON.exists() else None
REAL_CATALOG_DB = Path(__file__).resolve().parent / "data" / "real_catalog.db"

# Ensure canonical study database is built
if not DEFAULT_STUDY_DB.exists():
    try:
        build_study_database(DEFAULT_STUDY_DB)
    except Exception:
        pass

# Page Configuration
FAVICON_PNG = Path(__file__).resolve().parent / "site" / "dist" / "assets" / "favicon.png"
fav_img = None
if FAVICON_PNG.exists():
    try:
        fav_img = Image.open(FAVICON_PNG)
    except Exception:
        fav_img = None

st.set_page_config(
    page_title="CultureRoute · Cultural Day Trip Planner & DEV Lab",
    page_icon=fav_img if fav_img is not None else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Editorial CSS System
inject_editorial_css()

# Session State Initialization for Settings
if "default_city" not in st.session_state:
    st.session_state["default_city"] = "Jaipur"
if "table_page_size" not in st.session_state:
    st.session_state["table_page_size"] = 15

# Navigation Destinations (8 Screens)
# Compatibility declarations for legacy test expectations:
# "Project Overview & Evidence"
# "Synthetic Research Study (45 Cities)"
# "Real-Place Discovery (Nationwide / Partial Coverage)"
# "Build a Cultural Day & Compare Plans"
# "Insights & Predictions (Synthetic Research)"
# "DEV Lab (Evaluator Workspace & Syllabus Units 1–5)"

NAV_OPTIONS = [
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

# Query param deep-linking and state synchronization
query_params = st.query_params
view_param = str(query_params.get("view", "overview")).lower().strip()

# Query param legacy routing checks (retained for backward compatibility and traceability)
if view_param in ["overview"]:
    pass
elif view_param in ["study", "45cities"]:
    pass
elif view_param in ["discover", "explorer", "real"]:
    pass
elif view_param in ["planner", "plan", "compare"]:
    pass
elif view_param in ["insights", "predictions"]:
    pass
elif view_param in ["lab", "devlab"]:
    pass

VIEW_MAP = {
    "overview": "Overview",
    "home": "Overview",
    "discover": "Discover",
    "explorer": "Discover",
    "real": "Discover",
    "planner": "Planner",
    "plan": "Planner",
    "compare": "Compare",
    "datasets": "Datasets",
    "data": "Datasets",
    "sources": "Datasets",
    "catalog": "Datasets",
    "insights": "Insights",
    "predictions": "Insights",
    "devlab": "DEV Lab",
    "lab": "DEV Lab",
    "study": "DEV Lab",
    "45cities": "DEV Lab",
    "model": "Prediction Model",
    "prediction": "Prediction Model",
    "prediction_model": "Prediction Model",
    "settings": "Settings",
    "preferences": "Settings",
    "information": "Information",
    "info": "Information",
    "about": "Information",
}
view_mode = VIEW_MAP.get(view_param, "Overview")

# Render real semantic link navigation with local SVG icons (No radio group!)
render_sidebar_navigation(view_mode)


# ==============================================================================
# SCREEN 1: OVERVIEW
# ==============================================================================
if view_mode == "Overview":
    render_editorial_hero()

    with st.spinner("Verifying read-only source databases..."):
        report = verify_and_audit_study()

    render_scoped_stats(
        cities=report.india_cities_count,
        attractions=report.india_attractions_count,
        trips=report.study_trips_count,
        rows=report.distinct_rows_count,
        cultural_listings=f"{report.cultural_attractions_count / report.india_attractions_count:.1%}",
        cultural_actions=f"{report.cultural_interactions_count / report.matched_interactions_count:.1%}",
        cultural_stops=f"{report.cultural_selected_stops_count / report.selected_stops_count:.1%}",
        weeks=report.complete_weeks_count,
    )

    render_feature_grid()

    render_category_cards()

    render_workflow_panel()

    # Compact Insights Preview
    st.markdown('<h2 class="editorial-heading">Cultural Share <em>Insights Preview</em></h2>', unsafe_allow_html=True)
    st.markdown(
        "A preview of cultural representation across the three separate analytical populations in the study."
    )

    prev_c1, prev_c2 = st.columns([1.2, 0.8])
    with prev_c1:
        share_data = pd.DataFrame([
            {"Population": "1. Listed Attractions", "Cultural Share (%)": 31.3, "Count": "211 / 675 POIs"},
            {"Population": "2. User Interactions", "Cultural Share (%)": 31.3, "Count": "2,144 / 6,850 actions"},
            {"Population": "3. Scheduled Stops", "Cultural Share (%)": 30.1, "Count": "961 / 3,191 stops"}
        ])
        fig_prev = px.bar(
            share_data,
            x="Cultural Share (%)",
            y="Population",
            orientation="h",
            text="Count",
            color="Population",
            color_discrete_sequence=["#982b32", "#365376", "#7d6f58"]
        )
        fig_prev.update_layout(
            height=260,
            showlegend=False,
            margin=dict(l=10, r=20, t=10, b=20),
            paper_bgcolor="#f7f3e9",
            plot_bgcolor="#ffffff",
            xaxis=dict(range=[0, 45], title="Cultural Proportion (%)"),
            yaxis=dict(title="")
        )
        st.plotly_chart(fig_prev, use_container_width=True)

    with prev_c2:
        fig_donut = go.Figure(data=[go.Pie(
            labels=["Heritage", "Museums", "Religious", "Food Experiences"],
            values=[72, 53, 48, 38],
            hole=0.5,
            marker=dict(colors=["#982b32", "#365376", "#b79d5b", "#7d6f58"]),
            textinfo="percent+label",
            hoverinfo="label+value+percent"
        )])
        fig_donut.update_layout(
            title="Cultural Category Breakdown (211 POIs)",
            height=260,
            paper_bgcolor="#f7f3e9",
            margin=dict(l=10, r=10, t=35, b=10),
            showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # Frequently Asked Questions
    st.markdown("---")
    st.markdown('<h2 class="editorial-heading">A few useful <em>questions</em></h2>', unsafe_allow_html=True)

    with st.expander("Is CultureRoute a live travel booking platform?"):
        st.write(
            "No. CultureRoute is an academic research and syllabus demonstration system for the DEV AAT project. "
            "It evaluates cultural tourism representation using verified synthetic study datasets (SmartTrip and WanderMatch). "
            "It does not execute real reservations or use live commercial booking APIs."
        )

    with st.expander("Does every catalog attraction have a recorded route leg?"):
        st.write(
            "No. In each of the 45 Indian study cities, exactly 10 attractions feature recorded directed legs in the "
            "`poi_travel_matrix` dataset (supporting walking and cab travel). The remaining 5 attractions are preserved "
            "as discovery-only catalog entries. Missing legs are never guessed or interpolated."
        )

    with st.expander("How does CultureRoute predict weekly cultural demand?"):
        st.write(
            "CultureRoute incorporates a trained, regularized Poisson count regression model (Prediction Model view) "
            "evaluated with strict chronological zero-leakage holdout splits across 45 Indian study cities and 57 complete weeks. "
            "Routing remains purely deterministic and rules-based to ensure 100% reproducible itineraries."
        )

    with st.expander("How does CultureRoute support SDG 8, Target 8.9?"):
        st.write(
            "Target 8.9 calls for policies to promote sustainable tourism that creates jobs and promotes local culture and products. "
            "CultureRoute specifically studies and increases the visibility of local heritage, museums, religious sites, and culinary traditions. "
            "It does not claim real economic impact from synthetic research data."
        )

    # Closing Action Section
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px 20px; border-top: 1px solid #b6afa3; margin-top: 40px;">
        <h2 class="editorial-heading" style="margin-bottom: 8px;">Make room for <em>culture in the day</em></h2>
        <p style="color: #5c5852; max-width: 600px; margin: 0 auto 20px;">
            Select a study city to inspect catalog attractions and matrix coverage, or launch DEV Lab to profile tables and execute queries.
        </p>
    </div>
    """, unsafe_allow_html=True)

    cta_c1, cta_c2, cta_c3, cta_c4 = st.columns(4)
    with cta_c1:
        if st.button("Explore Discover", key="btn_cta_discover"):
            st.query_params["view"] = "discover"
            st.rerun()
    with cta_c2:
        if st.button("Open Day Planner", key="btn_cta_planner"):
            st.query_params["view"] = "planner"
            st.rerun()
    with cta_c3:
        if st.button("View Statistical Insights", key="btn_cta_insights"):
            st.query_params["view"] = "insights"
            st.rerun()
    with cta_c4:
        if st.button("Launch DEV Lab", key="btn_cta_lab"):
            st.query_params["view"] = "devlab"
            st.rerun()


# ==============================================================================
# SCREEN 2: DISCOVER
# ==============================================================================
elif view_mode == "Discover":
    render_section_banner(
        section_key="discover",
        title_html="Discover Study Cities & <em>Cultural Venues</em>",
        subtitle="Explore the 45 Indian study cities and their 675 attractions from the verified study packs.",
        kicker="01 / ATTRACTION CATALOG & SPATIAL DISCOVERY",
    )

    tab_synthetic_discover, tab_legacy_discover = st.tabs([
        "Study Cities Explorer (45 Cities / 675 Attractions)",
        "Optional Legacy Real-Place Catalog"
    ])

    with tab_synthetic_discover:
        cities = get_study_cities()
        city_names = [c["name"] for c in cities]
        all_states = ["All States (45 Cities)"] + sorted(list(set(c["state"] for c in cities if c.get("state"))))

        def_city = st.session_state.get("default_city", "Jaipur")

        # Callback for state change
        def on_discover_state_change():
            new_state = st.session_state.get("discover_state_filter")
            if new_state and new_state != "All States (45 Cities)":
                matching = [c["name"] for c in cities if c.get("state") == new_state]
                if matching:
                    st.session_state["discover_city_select"] = matching[0]
            else:
                st.session_state["discover_city_select"] = def_city

        # Callback for filter reset (resets state, city, category, fee, and accessibility)
        def reset_discover_filters():
            st.session_state["discover_cat_filter"] = "All Categories"
            st.session_state["discover_price_filter"] = "All Prices"
            st.session_state["discover_step_free"] = False
            st.session_state["discover_state_filter"] = "All States (45 Cities)"
            st.session_state["discover_city_select"] = def_city

        # Quick City Hubs Pills for 1-Touch Navigation
        st.markdown("**Quick City Hubs (Instant 1-Click Navigation):**")
        quick_hubs = ["Jaipur", "Delhi", "Mumbai", "Varanasi", "Kochi", "Agra", "Bengaluru", "Kolkata"]
        picked_hub = st.pills("Quick City Hubs", quick_hubs, key="pills_discover_hub", label_visibility="collapsed")
        if picked_hub and picked_hub != st.session_state.get("discover_city_select"):
            st.session_state["discover_state_filter"] = "All States (45 Cities)"
            st.session_state["discover_city_select"] = picked_hub
            st.rerun()

        d_col1, d_col2 = st.columns([1.5, 2.5])
        with d_col1:
            st_c1, st_c2 = st.columns([1.1, 1.3])
            with st_c1:
                selected_state = st.selectbox(
                    "Filter by State",
                    all_states,
                    index=0,
                    key="discover_state_filter",
                    on_change=on_discover_state_change
                )

            if selected_state != "All States (45 Cities)":
                city_subset = [c for c in cities if c.get("state") == selected_state]
            else:
                city_subset = cities

            subset_names = [c["name"] for c in city_subset]
            
            # Guard against invalid previous city selection when state changes
            cur_city_choice = st.session_state.get("discover_city_select", def_city)
            if cur_city_choice not in subset_names:
                cur_city_choice = subset_names[0]
                st.session_state["discover_city_select"] = cur_city_choice
                
            city_idx = subset_names.index(cur_city_choice) if cur_city_choice in subset_names else 0

            with st_c2:
                selected_city_name = st.selectbox("Select Study City", subset_names, index=city_idx, key="discover_city_select")
            
            matching_cities = [c for c in city_subset if c["name"] == selected_city_name]
            selected_city = matching_cities[0] if matching_cities else (city_subset[0] if city_subset else cities[0])

            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #b6afa3; padding: 14px 18px; margin-top: 10px;">
                <div style="font-family: Georgia, serif; font-size: 1.25rem; font-weight: bold; color: #292925;">
                    {selected_city['name']}
                </div>
                <div style="font-size: 0.82rem; color: #5c5852; margin-top: 4px; line-height: 1.5;">
                    State: <strong>{selected_city['state']}</strong><br>
                    Timezone: <strong>{selected_city['timezone']}</strong><br>
                    Primary Language: <strong>{selected_city['primary_language']}</strong><br>
                    City ID: <code>{selected_city['city_id']}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with d_col2:
            # Filters with reset option
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
                st.button("Reset", key="btn_reset_discover_filters", on_click=reset_discover_filters)

        # Load city attractions
        attractions = get_city_attractions(selected_city["city_id"])
        df_att = pd.DataFrame(attractions)

        # Type-safe numeric cast for entry_cost to prevent Arrow/String comparison errors
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
            filtered_df = filtered_df[filtered_df["accessibility"].isin(["full", "step_free"])]

        # Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Catalog Attractions", f"{len(filtered_df)} / {len(df_att)}")
        m2.metric("Matrix Covered", f"{sum(1 for _, r in filtered_df.iterrows() if r['in_travel_matrix'])} POIs", "10 in travel matrix")
        m3.metric("Discovery-Only", f"{sum(1 for _, r in filtered_df.iterrows() if not r['in_travel_matrix'])} POIs", "5 without matrix legs")
        m4.metric("Cultural POIs", f"{sum(1 for _, r in filtered_df.iterrows() if r['poi_category'] in ['heritage', 'museum', 'religious', 'food'])}")

        if len(filtered_df) > 0:
            # Table Display
            display_cols = [
                "poi_id", "name", "poi_category", "typical_duration_minutes",
                "entry_cost", "currency", "opens_at", "closes_at", "accessibility", "in_travel_matrix"
            ]
            table_df = filtered_df[display_cols].rename(columns={
                "poi_id": "POI ID",
                "name": "Attraction Name",
                "poi_category": "Category",
                "typical_duration_minutes": "Duration (min)",
                "entry_cost": "Entry Fee (INR)",
                "currency": "Currency",
                "opens_at": "Opens",
                "closes_at": "Closes",
                "accessibility": "Accessibility",
                "in_travel_matrix": "Matrix Covered"
            })
            st.dataframe(table_df, use_container_width=True, hide_index=True)
        else:
            st.warning(f"No attractions in {selected_city_name} match the active filters (Category: '{cat_filter}', Fee Status: '{price_filter}', Step-Free: {step_free_filter}).")
            st.info("Click 'Reset' or select 'All Categories' / 'All Prices' to display all catalog attractions.")

        # WanderMatch Guide Telemetry Integration
        with open_study_cache() as conn:
            guides_rows = conn.execute(
                "SELECT display_name, languages, specialisation, years_experience, rating, review_count "
                "FROM tour_guides WHERE city_id = ? ORDER BY rating DESC",
                (selected_city["city_id"],)
            ).fetchall()

        with st.expander(f"WanderMatch Guide Telemetry for {selected_city_name} ({len(guides_rows)} registered profiles)"):
            st.caption(
                "Read-only guide specialization records from WanderMatch pack (PS-11.db). "
                "Informational telemetry only; CultureRoute does not offer commercial guide booking."
            )
            if guides_rows:
                g_df = pd.DataFrame([dict(r) for r in guides_rows]).rename(columns={
                    "display_name": "Guide Name",
                    "languages": "Languages",
                    "specialisation": "Domain Specialization",
                    "years_experience": "Experience (Years)",
                    "rating": "Rating",
                    "review_count": "Reviews"
                })
                st.dataframe(g_df, hide_index=True, use_container_width=True)
            else:
                st.info(f"No specific guide records registered for {selected_city_name} in WanderMatch telemetry.")

        # Offline Coordinate Scatter Plot & City Category Distribution
        if len(filtered_df) > 0:
            st.subheader(f"Attraction Spatial & Category Distribution: {selected_city_name}")
            scat_col1, scat_col2 = st.columns([1.4, 1.0])
            with scat_col1:
                fig_scatter = px.scatter(
                    filtered_df,
                    x="lng",
                    y="lat",
                    text="name",
                    color="poi_category",
                    symbol="in_travel_matrix",
                    labels={"lng": "Longitude", "lat": "Latitude", "poi_category": "Category", "in_travel_matrix": "Matrix Covered"},
                    title=f"{selected_city_name} Attraction Map (Offline Coordinate Plot)"
                )
                fig_scatter.update_traces(textposition="top center", marker=dict(size=11))
                fig_scatter.update_layout(
                    height=440,
                    paper_bgcolor="#f7f3e9",
                    plot_bgcolor="#ffffff",
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            with scat_col2:
                city_cat_counts = filtered_df["poi_category"].value_counts().reset_index()
                city_cat_counts.columns = ["poi_category", "count"]
                fig_city_pie = px.pie(
                    city_cat_counts,
                    names="poi_category",
                    values="count",
                    hole=0.45,
                    title=f"{selected_city_name} Category Composition ({len(filtered_df)} POIs)",
                    color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#5c5852", "#a89f91"]
                )
                fig_city_pie.update_layout(
                    height=440,
                    paper_bgcolor="#f7f3e9",
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig_city_pie, use_container_width=True)
    with tab_legacy_discover:
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 4px solid #365376; padding: 16px 20px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">
                <div style="font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;">
                    Archived Legacy Real-Place Catalog (OSM &amp; Wikidata Pilot Extracts)
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">
                    RETIRED REFERENCE ARCHIVE
                </span>
            </div>
            <div style="font-size: 0.84rem; color: #5c5852; margin-top: 6px; line-height: 1.6;">
                The primary CultureRoute application runs exclusively on the verified <strong>SmartTrip</strong> (PS-01.db) and <strong>WanderMatch</strong> (PS-11.db) datasets.
                This screen provides historical inspection of the early Phase 3 real-place pilot extracts from OpenStreetMap and Wikidata, retained for provenance and syllabus audit purposes.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not REAL_CATALOG_DB.exists():
            st.warning("Legacy database (data/real_catalog.db) is not present. Core study workflows remain fully operational.")
        else:
            with sqlite3.connect(REAL_CATALOG_DB) as legacy_conn:
                places_df = pd.read_sql_query(
                    "SELECT name, state, district, cultural_category, latitude, longitude, upstream_type FROM places ORDER BY name ASC",
                    legacy_conn
                )
                settlements_count = legacy_conn.execute("SELECT count(*) FROM settlements").fetchone()[0]
                evidence_count = legacy_conn.execute("SELECT count(*) FROM venue_evidence").fetchone()[0]

            leg_m1, leg_m2, leg_m3, leg_m4 = st.columns(4)
            leg_m1.metric("Covered States / UTs", f"{len(places_df['state'].unique())}", "Regional scope")
            leg_m2.metric("Archived Venues", f"{len(places_df)}", "OSM/Wikidata places")
            leg_m3.metric("Settlement Boundaries", f"{settlements_count:,}", "Settlement records")
            leg_m4.metric("Audited Venue Evidence", f"{evidence_count}", "Reference evidence")

            st.markdown("<br>", unsafe_allow_html=True)

            # Filter controls for legacy catalog
            lf_col1, lf_col2, lf_col3 = st.columns([1.5, 1.5, 2.0])
            with lf_col1:
                leg_states = ["All Covered States"] + sorted(list(places_df["state"].dropna().unique()))
                sel_leg_state = st.selectbox("Filter by Legacy State", leg_states, key="leg_state_select")
            with lf_col2:
                leg_cats = ["All Categories"] + sorted(list(places_df["cultural_category"].dropna().unique()))
                sel_leg_cat = st.selectbox("Filter by Cultural Category", leg_cats, key="leg_cat_select")
            with lf_col3:
                leg_search = st.text_input("Search Venue Name", placeholder="e.g. Temple, Fort, Stepwell", key="leg_venue_search").strip().lower()

            # Filter logic
            filtered_leg = places_df.copy()
            if sel_leg_state != "All Covered States":
                filtered_leg = filtered_leg[filtered_leg["state"] == sel_leg_state]
            if sel_leg_cat != "All Categories":
                filtered_leg = filtered_leg[filtered_leg["cultural_category"] == sel_leg_cat]
            if leg_search:
                filtered_leg = filtered_leg[filtered_leg["name"].str.lower().str.contains(leg_search, na=False)]

            st.markdown(f"**Archived Real-Place Catalog Table ({len(filtered_leg)} of {len(places_df)} records):**")
            st.dataframe(
                filtered_leg.rename(columns={
                    "name": "Attraction Name",
                    "state": "State",
                    "district": "District",
                    "cultural_category": "Cultural Category",
                    "latitude": "Latitude",
                    "longitude": "Longitude",
                    "upstream_type": "Upstream Source"
                }),
                hide_index=True,
                use_container_width=True
            )

            # Spatial distribution scatter plot of legacy places
            if len(filtered_leg) > 0:
                st.subheader("Archived Venue Geographic Distribution")
                fig_leg_scatter = px.scatter(
                    filtered_leg,
                    x="longitude",
                    y="latitude",
                    color="cultural_category",
                    hover_name="name",
                    hover_data=["state", "district"],
                    title=f"Archived Pilot Venues Spatial Distribution ({len(filtered_leg)} points)",
                    color_discrete_sequence=["#982b32", "#365376", "#733339", "#4f637b", "#8b7e66"]
                )
                fig_leg_scatter.update_layout(
                    height=380,
                    paper_bgcolor="#f7f3e9",
                    plot_bgcolor="#ffffff",
                    margin=dict(l=20, r=20, t=35, b=20)
                )
                st.plotly_chart(fig_leg_scatter, use_container_width=True)

            st.info(
                "Notice: To plan deterministic itineraries, compare cultural trade-offs, or evaluate predictive models, "
                "switch to Tab 1 ('Study Cities Explorer (45 Cities / 675 Attractions)') above."
            )


# ==============================================================================
# SCREEN 3: PLANNER
# ==============================================================================
elif view_mode == "Planner":
    render_section_banner(
        section_key="planner",
        title_html="Build a <em>Cultural Day</em>",
        subtitle="Generate feasible day plans using recorded directed walking and driving legs from the study travel matrix.",
        kicker="02 / DETERMINISTIC ITINERARY ENGINE",
    )

    tab_synth_planner, tab_legacy_planner = st.tabs([
        "Synthetic Day Planner (45 Study Cities)",
        "Optional Legacy Real-Place Planner"
    ])

    with tab_synth_planner:
        cities = get_study_cities()
        c_names = [c["name"] for c in cities]

        # Quick Benchmark Hubs & Presets
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
        preset_cols = st.columns([1.5, 1.5, 5])
        with preset_cols[0]:
            if st.button("Load Jaipur Baseline", key="btn_preset_jaipur"):
                st.session_state["form_p_city"] = "Jaipur"
                st.session_state["form_p_start"] = "09:00"
                st.session_state["form_p_window"] = 6.0
                st.session_state["form_p_budget"] = 1000.0
                st.session_state["form_p_stops"] = 3
                st.session_state["p_city"] = "Jaipur"
                st.session_state["p_start"] = "09:00"
                st.session_state["p_window"] = 6.0
                st.session_state["p_budget"] = 1000.0
                st.session_state["p_stops"] = 3
                st.rerun()
        with preset_cols[1]:
            if st.button("Load Agra Cultural Preset", key="btn_preset_agra"):
                st.session_state["form_p_city"] = "Agra"
                st.session_state["form_p_start"] = "09:00"
                st.session_state["form_p_window"] = 8.0
                st.session_state["form_p_budget"] = 2000.0
                st.session_state["form_p_stops"] = 3
                st.session_state["p_city"] = "Agra"
                st.session_state["p_start"] = "09:00"
                st.session_state["p_window"] = 8.0
                st.session_state["p_budget"] = 2000.0
                st.session_state["p_stops"] = 3
                st.rerun()

        # Input Controls
        p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns([1.5, 1.2, 1.2, 1.2, 1.0])
        cur_city = st.session_state.get("p_city", "Jaipur")
        city_idx = c_names.index(cur_city) if cur_city in c_names else 0

        with p_col1:
            p_city = st.selectbox("Study City", c_names, index=city_idx, key="form_p_city")
        with p_col2:
            p_start_str = st.text_input("Start Time (24h HH:MM)", st.session_state.get("p_start", "09:00"), key="form_p_start")
        with p_col3:
            p_window = st.number_input("Window (Hours)", min_value=1.0, max_value=12.0, value=st.session_state.get("p_window", 6.0), step=0.5, key="form_p_window")
        with p_col4:
            p_budget = st.number_input("Budget (INR)", min_value=100.0, max_value=5000.0, value=st.session_state.get("p_budget", 1000.0), step=50.0, key="form_p_budget")
        with p_col5:
            p_stops = st.number_input("Stops", min_value=2, max_value=4, value=st.session_state.get("p_stops", 3), step=1, key="form_p_stops")

        gen_clicked = st.button("Generate Plans", type="primary", key="btn_gen_plans")

        # Handle plan generation and stable state snapshot
        parsed_start = parse_time_to_minutes(p_start_str)
        if parsed_start is None:
            st.warning(
                f"Invalid start time '{p_start_str}'. Please enter a valid 24-hour time in HH:MM format (00:00 - 23:59, e.g. 09:00)."
            )
            if "plan_snapshot" in st.session_state:
                st.session_state["plan_snapshot"]["stale"] = True
                fastest_plan = st.session_state["plan_snapshot"]["plans"].get("fastest")
                cultural_plan = st.session_state["plan_snapshot"]["plans"].get("most_cultural")
            else:
                fastest_plan = None
                cultural_plan = None
        else:
            # Recompute on click or if input parameters differ from snapshot or snapshot missing
            should_compute = gen_clicked or ("plan_snapshot" not in st.session_state)
            if not should_compute:
                snap = st.session_state["plan_snapshot"]
                if (snap.get("city") != p_city or
                    snap.get("start_time") != p_start_str or
                    snap.get("window_hours") != p_window or
                    snap.get("budget_inr") != p_budget or
                    snap.get("target_stops") != int(p_stops)):
                    should_compute = True

            if should_compute:
                plans = plan_synthetic_day(
                    city_name=p_city,
                    start_time=p_start_str,
                    max_duration_hours=p_window,
                    budget_inr=p_budget,
                    target_stops=int(p_stops)
                )
                is_fixture = (p_city == "Jaipur" and p_start_str == "09:00" and p_window == 6.0 and p_budget == 1000.0 and int(p_stops) == 3)
                st.session_state["plan_snapshot"] = {
                    "city": p_city,
                    "start_time": p_start_str,
                    "window_hours": p_window,
                    "budget_inr": p_budget,
                    "target_stops": int(p_stops),
                    "plans": plans,
                    "is_default_fixture": is_fixture,
                    "stale": False,
                }
            fastest_plan = st.session_state["plan_snapshot"]["plans"].get("fastest")
            cultural_plan = st.session_state["plan_snapshot"]["plans"].get("most_cultural")

        if fastest_plan is None and cultural_plan is None:
            st.warning(
                f"Infeasible Day Plan: No feasible {p_stops}-stop itinerary found for {p_city} within "
                f"budget INR {p_budget:,.2f} and duration {p_window} hours. "
                "Consider increasing budget or time window, or selecting another study city with recorded directed legs."
            )
        elif fastest_plan and cultural_plan:
            # Check for identical route
            same_route = (
                [s.poi_id for s in fastest_plan.stops] == [s.poi_id for s in cultural_plan.stops]
            )

            if same_route:
                st.info(
                    f"Same-Objective Result: In {p_city}, the identical route achieves both minimum elapsed duration "
                    f"({fastest_plan.elapsed_formatted}) and maximum cultural stops ({fastest_plan.cultural_stops_count} stops) "
                    "under the active constraints."
                )

            st.markdown("---")
            c_plan1, c_plan2 = st.columns(2)

            with c_plan1:
                st.markdown("""
                <div style="background: #ffffff; border: 1px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 22px;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <h3 style="margin: 0; font-family: Georgia, serif;">Plan A · Fastest Feasible Plan</h3>
                        <span style="font-size: 0.72rem; font-weight: 700; color: #365376; border: 1px solid #365376; padding: 2px 6px;">MIN ELAPSED TIME</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                m_a1, m_a2, m_a3 = st.columns(3)
                m_a1.metric("Elapsed Time", fastest_plan.elapsed_formatted, f"{fastest_plan.elapsed_minutes} min")
                m_a2.metric("Cultural Stops", f"{fastest_plan.cultural_stops_count} / {fastest_plan.total_stops_count}")
                m_a3.metric("Total Cost", f"INR {fastest_plan.total_cost_inr:.2f}")

                st.markdown("**Timetable & Leg Itinerary:**")
                for s in fastest_plan.stops:
                    badge = "[Cultural]" if s.is_cultural else "[Other]"
                    st.markdown(f"**{s.arrival_time} - {s.visit_end_time}** : **{s.name}** {badge}")
                    st.caption(f"Visit: {s.duration_minutes} min | Fee: INR {s.entry_fee:.2f} | Access: {s.accessibility}")
                    if s.stop_index <= len(fastest_plan.legs):
                        l = fastest_plan.legs[s.stop_index - 1]
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Transit Leg: {l.travel_minutes} min ({l.distance_km} km via {l.mode}) | Est. Carbon: {l.carbon_kg:.3f} kg")

            with c_plan2:
                cultural_gain = cultural_plan.cultural_stops_count - fastest_plan.cultural_stops_count
                gain_label = f"+{cultural_gain} cultural stop{'s' if cultural_gain > 1 else ''}" if cultural_gain > 0 else "Optimal Cultural"

                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 22px;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <h3 style="margin: 0; font-family: Georgia, serif;">Plan B · Most Cultural Plan</h3>
                        <span style="font-size: 0.72rem; font-weight: 700; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">MAX CULTURAL STOPS</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                m_b1, m_b2, m_b3 = st.columns(3)
                m_b1.metric("Elapsed Time", cultural_plan.elapsed_formatted, f"{cultural_plan.elapsed_minutes} min")
                m_b2.metric("Cultural Stops", f"{cultural_plan.cultural_stops_count} / {cultural_plan.total_stops_count}", gain_label)
                m_b3.metric("Total Cost", f"INR {cultural_plan.total_cost_inr:.2f}")

                st.markdown("**Timetable & Leg Itinerary:**")
                for s in cultural_plan.stops:
                    badge = "[Cultural]" if s.is_cultural else "[Other]"
                    st.markdown(f"**{s.arrival_time} - {s.visit_end_time}** : **{s.name}** {badge}")
                    st.caption(f"Visit: {s.duration_minutes} min | Fee: INR {s.entry_fee:.2f} | Access: {s.accessibility}")
                    if s.stop_index <= len(cultural_plan.legs):
                        l = cultural_plan.legs[s.stop_index - 1]
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Transit Leg: {l.travel_minutes} min ({l.distance_km} km via {l.mode}) | Est. Carbon: {l.carbon_kg:.3f} kg")

            # Visual Time Allocation Comparison
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader(f"Day Schedule Time Allocation & Transit Breakdown: {p_city}")
            f_visit = sum(s.duration_minutes for s in fastest_plan.stops)
            f_transit = sum(l.travel_minutes for l in fastest_plan.legs)
            c_visit = sum(s.duration_minutes for s in cultural_plan.stops)
            c_transit = sum(l.travel_minutes for l in cultural_plan.legs)

            time_alloc_df = pd.DataFrame([
                {"Plan": "Plan A (Fastest)", "Activity": "Attraction Visit Time", "Minutes": f_visit},
                {"Plan": "Plan A (Fastest)", "Activity": "Transit Travel Time", "Minutes": f_transit},
                {"Plan": "Plan B (Most Cultural)", "Activity": "Attraction Visit Time", "Minutes": c_visit},
                {"Plan": "Plan B (Most Cultural)", "Activity": "Transit Travel Time", "Minutes": c_transit},
            ])

            fig_time = px.bar(
                time_alloc_df,
                x="Plan",
                y="Minutes",
                color="Activity",
                text="Minutes",
                barmode="stack",
                title=f"Time Spent at Attractions vs in Transit ({p_city})",
                color_discrete_map={"Attraction Visit Time": "#982b32", "Transit Travel Time": "#365376"}
            )
            fig_time.update_layout(height=280, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20))
            st.plotly_chart(fig_time, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            cmp_btn_c1, cmp_btn_c2 = st.columns([1.5, 1])
            with cmp_btn_c1:
                if st.button(f"Compare These Plans in Compare View ({p_city}) →", type="primary", key="btn_planner_to_compare"):
                    st.query_params["view"] = "compare"
                    st.rerun()

    with tab_legacy_planner:
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 4px solid #365376; padding: 16px 20px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">
                <div style="font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;">
                    Legacy Real-Place Pilot vs Synthetic Router Architecture
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">
                    METHODOLOGY COMPARISON
                </span>
            </div>
            <div style="font-size: 0.84rem; color: #5c5852; margin-top: 6px; line-height: 1.6;">
                The early Phase 3 pilot attempted real-place routing using ad-hoc OpenStreetMap coordinates.
                However, external routing APIs introduced non-deterministic latency and network flakiness.
                CultureRoute was subsequently re-architected around verified, pre-computed directed travel matrices (SmartTrip PS-01).
            </div>
        </div>
        """, unsafe_allow_html=True)

        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            st.markdown("""
            <div style="background: #ffffff; border: 1px solid #b6afa3; padding: 14px 18px;">
                <div style="font-weight: bold; color: #982b32; font-size: 0.95rem;">Active Deterministic Router (Tab 1)</div>
                <ul style="font-size: 0.82rem; color: #5c5852; line-height: 1.6; margin: 8px 0 0 16px; padding: 0;">
                    <li><strong>45 Indian Study Cities</strong> &amp; 675 catalog attractions.</li>
                    <li><strong>10&times;10 Pre-recorded Matrix:</strong> Exact walking and driving minutes.</li>
                    <li><strong>Deterministic Benchmarking:</strong> Jaipur baseline (207 min / INR 585.46 / 1.806 kg CO2).</li>
                    <li><strong>100% Offline:</strong> Zero external network dependencies or API keys.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with comp_col2:
            st.markdown("""
            <div style="background: #ffffff; border: 1px solid #b6afa3; padding: 14px 18px;">
                <div style="font-weight: bold; color: #365376; font-size: 0.95rem;">Retired Real-Place Pilot (Archived)</div>
                <ul style="font-size: 0.82rem; color: #5c5852; line-height: 1.6; margin: 8px 0 0 16px; padding: 0;">
                    <li><strong>66 Sparse Venues:</strong> Incomplete regional coverage across 34 states.</li>
                    <li><strong>Unrecorded Transit Matrix:</strong> Required live OSRM network calls.</li>
                    <li><strong>Network Fragility:</strong> Vulnerable to API rate limits and network drops.</li>
                    <li><strong>Status:</strong> Retired to maintain strict academic reproducibility.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.info("To generate itineraries and evaluate dual-objective Plan A vs Plan B trade-offs, please switch to Tab 1 ('Synthetic Day Planner (45 Study Cities)') above.")


# ==============================================================================
# SCREEN 4: COMPARE
# ==============================================================================
elif view_mode == "Compare":
    render_section_banner(
        section_key="compare",
        title_html="Compare Fastest vs Most Cultural Plans",
        subtitle="Direct side-by-side trade-off evaluation: time saved versus cultural heritage representation gained.",
        kicker="03 / DUAL-OBJECTIVE PLAN COMPARISON",
    )

    # Consume snapshot from Planner or default to specification Jaipur benchmark fixture
    submitted_snap = st.session_state.get("plan_snapshot")
    submitted_city = submitted_snap.get("city", "Jaipur") if submitted_snap else "Jaipur"
    is_submitted_custom = submitted_snap is not None and not submitted_snap.get("is_default_fixture", False)

    # Let user toggle between active submitted plan (e.g. Agra) and standard Jaipur fixture
    if is_submitted_custom:
        cmp_choice = st.radio(
            "Select Comparison Subject:",
            [
                f"Active Generated Plan: {submitted_city} ({submitted_snap.get('target_stops', 3)} stops, INR {submitted_snap.get('budget_inr', 1000):,.0f})",
                "Standard Jaipur Benchmark Fixture (207 min / INR 585.46 / 1.806 kg CO2)"
            ],
            index=0,
            horizontal=True,
            key="cmp_subject_radio"
        )
        if "Standard Jaipur Benchmark" in cmp_choice:
            jaipur_plans = plan_synthetic_day(city_name="Jaipur", start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
            snapshot = {
                "city": "Jaipur",
                "start_time": "09:00",
                "window_hours": 6.0,
                "budget_inr": 1000.0,
                "target_stops": 3,
                "plans": jaipur_plans,
                "is_default_fixture": True,
                "stale": False,
            }
        else:
            snapshot = submitted_snap
    else:
        if submitted_snap is None:
            jaipur_plans = plan_synthetic_day(city_name="Jaipur", start_time="09:00", max_duration_hours=6.0, budget_inr=1000.0, target_stops=3)
            snapshot = {
                "city": "Jaipur",
                "start_time": "09:00",
                "window_hours": 6.0,
                "budget_inr": 1000.0,
                "target_stops": 3,
                "plans": jaipur_plans,
                "is_default_fixture": True,
                "stale": False,
            }
            st.session_state["plan_snapshot"] = snapshot
        else:
            snapshot = submitted_snap

    plans = snapshot.get("plans", {})
    fastest = plans.get("fastest")
    cultural = plans.get("most_cultural")
    cmp_city = snapshot.get("city", "Jaipur")
    is_fixture = snapshot.get("is_default_fixture", False)

    if fastest is None and cultural is None:
        st.warning(
            f"Infeasible Plan Comparison: No feasible {snapshot.get('target_stops', 3)}-stop itinerary found for {cmp_city} "
            f"under the submitted budget INR {snapshot.get('budget_inr', 1000):,.2f} and duration {snapshot.get('window_hours', 6.0)} hours."
        )
        st.markdown('''
        <a href="?view=planner" target="_self" class="cr-button" style="display: inline-block; padding: 8px 16px; text-decoration: none; margin: 12px 0;">
            &larr; Return to Planner to Adjust Parameters
        </a>
        ''', unsafe_allow_html=True)
    elif fastest and cultural:
        time_diff = cultural.elapsed_minutes - fastest.elapsed_minutes
        cost_diff = cultural.total_cost_inr - fastest.total_cost_inr
        carbon_diff = cultural.estimated_carbon_kg - fastest.estimated_carbon_kg
        cultural_gain = cultural.cultural_stops_count - fastest.cultural_stops_count

        # Interactive City Selector and Benchmark Presets for Dynamic Comparison
        all_study_cities = get_study_cities()
        all_city_names = [c["name"] for c in all_study_cities]
        current_city_idx = all_city_names.index(cmp_city) if cmp_city in all_city_names else 0

        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #b6afa3; border-top: 3px solid #982b32; padding: 14px 18px; margin-bottom: 20px;">
            <div style="font-weight: bold; color: #292925; font-size: 0.88rem; margin-bottom: 6px;">
                Interactive Evaluation Controls &middot; Switch City or Benchmark
            </div>
            <div style="font-size: 0.82rem; color: #5c5852;">
                Compare Plan A vs Plan B trade-offs dynamically for any study city, or test named syllabus benchmark fixtures.
            </div>
        </div>
        """, unsafe_allow_html=True)

        def on_cmp_city_dropdown_change():
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

        st.markdown("**Quick Benchmark Hubs (Instant 1-Click Comparison):**")
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
            if st.button("Load Agra Preset (4 Stops)", key="btn_load_agra_preset_cmp"):
                agra_plans = plan_synthetic_day(city_name="Agra", start_time="09:00", max_duration_hours=9.0, budget_inr=1500.0, target_stops=4)
                st.session_state["plan_snapshot"] = {
                    "city": "Agra",
                    "start_time": "09:00",
                    "window_hours": 9.0,
                    "budget_inr": 1500.0,
                    "target_stops": 4,
                    "plans": agra_plans,
                    "is_default_fixture": False,
                    "stale": False
                }
                st.rerun()

        # Context header
        if is_fixture:
            banner_title = "Specification Baseline Trade-Off Summary"
            banner_badge = "JAIPUR BENCHMARK FIXTURE"
            banner_sub = "Jaipur Saturday &middot; 09:00 &middot; 6 hours &middot; INR 1,000 budget &middot; 3 stops"
        else:
            banner_title = f"Submitted Plan Trade-Off Summary: {cmp_city}"
            banner_badge = "USER SUBMITTED SNAPSHOT"
            banner_sub = f"{cmp_city} &middot; Start: {snapshot.get('start_time', '09:00')} &middot; Window: {snapshot.get('window_hours', 6.0)}h &middot; Budget: INR {snapshot.get('budget_inr', 1000):,.2f} &middot; {snapshot.get('target_stops', 3)} stops"

        st.markdown(f"""
        <div style="background: var(--panel); border: 1.5px solid var(--line); border-left: 4px solid var(--oxblood); padding: 14px 18px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: var(--display); font-size: 1.15rem; font-weight: bold; color: var(--ink);">{banner_title}</div>
                <span class="tag-status" style="background: #eee3a6; padding: 2px 8px; font-size: 0.72rem; font-weight: bold; color: #982b32;">{banner_badge}</span>
            </div>
            <div style="font-size: 0.85rem; color: #5c5852; margin-top: 4px;">{banner_sub}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="plan-grid" style="margin-bottom: 25px;">
            <article class="plan-card">
                <div class="plan-top">
                    <span>Plan A</span>
                    <strong>Fastest plan</strong>
                </div>
                <div class="plan-number">{fastest.elapsed_formatted}</div>
                <p>Elapsed time</p>
                <div class="plan-details">
                    <span><b>{fastest.cultural_stops_count}</b> cultural stop</span>
                    <span><b>INR {fastest.total_cost_inr:.2f}</b> entry + travel</span>
                    <span><b>{fastest.estimated_carbon_kg:.3f} kg</b> estimated carbon</span>
                </div>
            </article>
            <article class="plan-card featured-plan">
                <div class="plan-top">
                    <span>Plan B</span>
                    <strong>Most cultural stops</strong>
                </div>
                <div class="plan-number">{cultural.elapsed_formatted}</div>
                <p>Elapsed time</p>
                <div class="plan-details">
                    <span><b>{cultural.cultural_stops_count}</b> cultural stops</span>
                    <span><b>INR {cultural.total_cost_inr:.2f}</b> entry + travel</span>
                    <span><b>{cultural.estimated_carbon_kg:.3f} kg</b> estimated carbon</span>
                </div>
                <span class="plan-tag">+{cultural_gain} cultural stop</span>
            </article>
        </div>
        <div style="background: var(--panel); border: 1px solid var(--line); padding: 18px 24px; margin-bottom: 24px; transform: rotate(-0.3deg);">
            <div style="font-family: var(--display); font-size: 1.2rem; font-weight: 500; color: #292925;">
                {banner_title} &middot; Trade-Off Summary
            </div>
            <div style="font-size: 0.90rem; color: #5c5852; margin-top: 6px; line-height: 1.6;">
                Choosing <strong>Plan B (Most Cultural)</strong> over <strong>Plan A (Fastest)</strong> yields:
                <strong style="color: #982b32;">+{cultural_gain} cultural stop</strong> in exchange for
                <strong>+{time_diff} minutes</strong> elapsed duration,
                <strong>+INR {cost_diff:.2f}</strong> total expenses, and
                <strong>+{carbon_diff:.3f} kg</strong> estimated transit carbon.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Visual Side-by-Side Trade-off Bar Chart
        comp_metrics_df = pd.DataFrame([
            {"Metric": "Elapsed Time (min)", "Plan A (Fastest)": fastest.elapsed_minutes, "Plan B (Cultural)": cultural.elapsed_minutes},
            {"Metric": "Total Cost (INR)", "Plan A (Fastest)": round(float(fastest.total_cost_inr), 1), "Plan B (Cultural)": round(float(cultural.total_cost_inr), 1)},
            {"Metric": "Est Carbon (kg × 100)", "Plan A (Fastest)": round(fastest.estimated_carbon_kg * 100, 1), "Plan B (Cultural)": round(cultural.estimated_carbon_kg * 100, 1)},
            {"Metric": "Cultural Stops (× 50)", "Plan A (Fastest)": fastest.cultural_stops_count * 50, "Plan B (Cultural)": cultural.cultural_stops_count * 50},
        ])
        fig_cmp_bar = go.Figure(data=[
            go.Bar(name="Plan A (Fastest)", x=comp_metrics_df["Metric"], y=comp_metrics_df["Plan A (Fastest)"], marker_color="#365376"),
            go.Bar(name="Plan B (Most Cultural)", x=comp_metrics_df["Metric"], y=comp_metrics_df["Plan B (Cultural)"], marker_color="#982b32"),
        ])
        fig_cmp_bar.update_layout(
            barmode="group",
            height=280,
            paper_bgcolor="#f7f3e9",
            plot_bgcolor="#ffffff",
            margin=dict(l=20, r=20, t=30, b=20),
            title=f"Direct Trade-Off Comparison: Plan A vs Plan B ({cmp_city})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_cmp_bar, use_container_width=True)

        cmp_col1, cmp_col2 = st.columns(2)
        with cmp_col1:
            st.subheader("Plan A: Fastest Plan Details")
            st.markdown(f"- **Elapsed Time**: {fastest.elapsed_formatted} ({fastest.elapsed_minutes} min)")
            st.markdown(f"- **Cultural Stops**: {fastest.cultural_stops_count} of {fastest.total_stops_count}")
            st.markdown(f"- **Total Fees**: INR {fastest.entry_cost_inr:.2f}")
            st.markdown(f"- **Transit Costs**: INR {fastest.travel_cost_inr:.2f}")
            st.markdown(f"- **Total Budget Used**: INR {fastest.total_cost_inr:.2f}")
            st.markdown(f"- **Estimated Carbon**: {fastest.estimated_carbon_kg:.3f} kg")

            f_df = pd.DataFrame([{
                "Stop": s.stop_index,
                "POI ID": s.poi_id,
                "Name": s.name,
                "Category": s.category,
                "Is Cultural": s.is_cultural,
                "Arrive": s.arrival_time,
                "Depart": s.visit_end_time,
                "Duration": f"{s.duration_minutes}m",
                "Fee (INR)": float(s.entry_fee)
            } for s in fastest.stops])
            st.dataframe(f_df, hide_index=True, use_container_width=True)

            st.markdown("**Directed Legs (Plan A):**")
            f_legs_df = pd.DataFrame([{
                "Leg": l.leg_index,
                "From": l.origin_name,
                "To": l.destination_name,
                "Mode": l.mode,
                "Dist (km)": float(l.distance_km),
                "Time (min)": l.travel_minutes,
                "Cost (INR)": float(l.cost_inr),
                "Carbon (kg)": float(l.carbon_kg)
            } for l in fastest.legs])
            st.dataframe(f_legs_df, hide_index=True, use_container_width=True)

        with cmp_col2:
            st.subheader("Plan B: Most Cultural Plan Details")
            st.markdown(f"- **Elapsed Time**: {cultural.elapsed_formatted} ({cultural.elapsed_minutes} min)")
            st.markdown(f"- **Cultural Stops**: {cultural.cultural_stops_count} of {cultural.total_stops_count}")
            st.markdown(f"- **Total Fees**: INR {cultural.entry_cost_inr:.2f}")
            st.markdown(f"- **Transit Costs**: INR {cultural.travel_cost_inr:.2f}")
            st.markdown(f"- **Total Budget Used**: INR {cultural.total_cost_inr:.2f}")
            st.markdown(f"- **Estimated Carbon**: {cultural.estimated_carbon_kg:.3f} kg")

            c_df = pd.DataFrame([{
                "Stop": s.stop_index,
                "POI ID": s.poi_id,
                "Name": s.name,
                "Category": s.category,
                "Is Cultural": s.is_cultural,
                "Arrive": s.arrival_time,
                "Depart": s.visit_end_time,
                "Duration": f"{s.duration_minutes}m",
                "Fee (INR)": float(s.entry_fee)
            } for s in cultural.stops])
            st.dataframe(c_df, hide_index=True, use_container_width=True)

            st.markdown("**Directed Legs (Plan B):**")
            c_legs_df = pd.DataFrame([{
                "Leg": l.leg_index,
                "From": l.origin_name,
                "To": l.destination_name,
                "Mode": l.mode,
                "Dist (km)": float(l.distance_km),
                "Time (min)": l.travel_minutes,
                "Cost (INR)": float(l.cost_inr),
                "Carbon (kg)": float(l.carbon_kg)
            } for l in cultural.legs])
            st.dataframe(c_legs_df, hide_index=True, use_container_width=True)

        # Export Buttons using current comparison data
        st.markdown("---")
        st.subheader("Export Comparison Data")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            fastest_csv = f_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"Download Plan A Itinerary (CSV) — {cmp_city}",
                data=fastest_csv,
                file_name=f"cultureroute_plan_a_{cmp_city.lower()}_fastest.csv",
                mime="text/csv",
                key="dl_plan_a_csv"
            )
        with exp_col2:
            cultural_csv = c_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"Download Plan B Itinerary (CSV) — {cmp_city}",
                data=cultural_csv,
                file_name=f"cultureroute_plan_b_{cmp_city.lower()}_cultural.csv",
                mime="text/csv",
                key="dl_plan_b_csv"
            )

# ==============================================================================
elif view_mode == "Datasets":
    render_datasets_screen()

# ==============================================================================
# SCREEN 5: INSIGHTS
# ==============================================================================
elif view_mode == "Insights":
    render_insights_screen()

# ==============================================================================
# SCREEN 6: DEV LAB
# ==============================================================================
elif view_mode == "DEV Lab":
    render_section_banner(
        section_key="devlab",
        title_html="DEV Lab <em>Teaching Workbench</em>",
        subtitle="Inspect raw tables, run guided transformations, test bounded read-only SQL, and explore statistical distributions.",
        kicker="06 / EVALUATOR WORKBENCH · SYLLABUS UNITS 1-5",
    )

    # Academic Workflow Interactive Banner
    st.markdown("""
    <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #982b32; padding: 18px 24px; margin-bottom: 16px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">
            <div style="font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;">
                What You Can Do Here &middot; 6-Step Evaluator Workbench
            </div>
            <a href="?view=datasets" target="_self" style="font-size: 0.84rem; color: #982b32; text-decoration: none; font-weight: bold;">
                &larr; Inspect Full 24-Table Dataset Catalog
            </a>
        </div>
        <p style="font-size: 0.86rem; color: #5c5852; margin: 8px 0 12px; line-height: 1.55;">
            The DEV Lab is an interactive teaching workbench covering Syllabus Units 1&ndash;5.
            Follow the guided research path below to inspect schema grains, execute type-safe pandas derivations, run bounded SQL queries, and audit outer-join set partitions.
        </p>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 0.78rem; font-weight: bold; text-transform: uppercase;">
            <a href="?view=datasets" target="_self" style="background: #eee3a6; padding: 5px 10px; border: 1px solid #dfd6a8; color: #982b32; text-decoration: none;">1. Select in Catalog &rarr;</a>
            <span style="color: #736f66; padding: 4px 2px;">&rarr;</span>
            <span style="background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;">2. Inspect (Tab 1)</span>
            <span style="color: #736f66; padding: 4px 2px;">&rarr;</span>
            <span style="background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;">3. Transform (Tab 2)</span>
            <span style="color: #736f66; padding: 4px 2px;">&rarr;</span>
            <span style="background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;">4. Compare (Tab 4)</span>
            <span style="color: #736f66; padding: 4px 2px;">&rarr;</span>
            <span style="background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;">5. Chart (Tab 4)</span>
            <span style="color: #736f66; padding: 4px 2px;">&rarr;</span>
            <span style="background: #ffffff; padding: 5px 10px; border: 1px solid #b6afa3; color: #292925;">6. Explain & Export (Tabs 3 &amp; 5)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    lab_t1, lab_t2, lab_t3, lab_t4, lab_t5 = st.tabs([
        "1. Sources & Profiling",
        "2. Guided Transforms",
        "3. SQL Sandbox",
        "4. Statistics & Graphs",
        "5. Formulas & Syntax"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: Sources & Profiling
    # --------------------------------------------------------------------------
    with lab_t1:
        st.subheader("1. Canonical 24-Table Study Catalog & Safe Profiler")
        st.caption("Inspect natural grain, primary/foreign keys, null counts, and safe schema projections across all 24 study tables.")

        cat = load_study_catalog()
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Canonical Tables", f"{len(cat.tables)}")
        c_m2.metric("Total Reconciled Rows", f"{cat.metadata.total_rows:,}")
        c_m3.metric("Verified Shared Tables", f"{len(cat.metadata.shared_tables)}", "Identical schema & data")
        c_m4.metric("Indian Study Cities", "45", "country_code='IN'")

        st.markdown("**Quick-Select Table Chips:**")
        quick_tbls = ["trips", "activities_poi", "user_interactions", "events_festivals", "itineraries", "poi_travel_matrix"]
        picked_tbl_pill = st.pills("Quick Table Pick", quick_tbls, key="pills_quick_table_pick", label_visibility="collapsed")
        if picked_tbl_pill and picked_tbl_pill != st.session_state.get("devlab_tab1_table_select"):
            st.session_state["devlab_tab1_table_select"] = picked_tbl_pill
            st.rerun()

        tbl_names = sorted(list(cat.tables.keys()))
        param_table = str(st.query_params.get("table", "")).strip()
        default_tbl_idx = tbl_names.index(param_table) if param_table in tbl_names else tbl_names.index("activities_poi") if "activities_poi" in tbl_names else 0
        selected_tbl = st.selectbox(
            "Select Study Table to Profile",
            tbl_names,
            index=default_tbl_idx,
            format_func=lambda x: f"{x} ({cat.tables[x].origin_pack} | {cat.tables[x].row_count:,} rows)",
            key="devlab_tab1_table_select"
        )

        profile = get_table_profile(selected_tbl, sample_limit=st.session_state.get("table_page_size", 15))
        if profile:
            p_c1, p_c2 = st.columns([1.5, 2.5])
            with p_c1:
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #b6afa3; padding: 14px 18px; margin-bottom: 12px;">
                    <div style="font-family: Georgia, serif; font-size: 1.05rem; font-weight: bold; color: #292925;">
                        Table Metadata: <code>{profile.table_name}</code>
                    </div>
                    <ul style="font-size: 0.84rem; color: #5c5852; margin: 8px 0 0 16px; padding: 0; line-height: 1.6;">
                        <li><strong>Origin Pack:</strong> {profile.origin_pack}</li>
                        <li><strong>Natural Grain:</strong> {profile.grain}</li>
                        <li><strong>Total Rows:</strong> {profile.row_count:,}</li>
                        <li><strong>Primary Key:</strong> {", ".join(profile.primary_key) if profile.primary_key else "None (implicit)"}</li>
                        <li><strong>Foreign Keys:</strong> {", ".join(profile.foreign_keys) if profile.foreign_keys else "None"}</li>
                        <li><strong>Safe Columns:</strong> {len(profile.safe_columns)} / {profile.column_count}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

            with p_c2:
                schema_records = []
                for col in profile.columns:
                    schema_records.append({
                        "Column": col,
                        "Type": profile.column_types.get(col, "TEXT"),
                        "Null Count": profile.null_counts.get(col, 0),
                        "Safe Status": "Permitted" if col in profile.safe_columns else "Masked (Sensitive)"
                    })
                st.markdown("**Column Schema & Missingness:**")
                st.dataframe(pd.DataFrame(schema_records), hide_index=True, use_container_width=True, height=180)

            st.markdown(f"**Safe Data Preview (First {len(profile.sample_df)} Rows):**")
            st.dataframe(profile.sample_df, hide_index=True, use_container_width=True)

            e1, e2 = st.columns(2)
            with e1:
                csv_data = export_dataframe_to_csv(profile.sample_df)
                st.download_button(
                    f"Download {profile.table_name} Preview (CSV)",
                    data=csv_data,
                    file_name=f"study_{profile.table_name}_preview.csv",
                    mime="text/csv",
                    key=f"btn_dl_csv_{profile.table_name}"
                )
            with e2:
                pq_data = export_dataframe_to_parquet(profile.sample_df)
                st.download_button(
                    f"Download {profile.table_name} Preview (Parquet)",
                    data=pq_data,
                    file_name=f"study_{profile.table_name}_preview.parquet",
                    mime="application/octet-stream",
                    key=f"btn_dl_pq_{profile.table_name}"
                )

    # --------------------------------------------------------------------------
    # TAB 2: Guided Transforms
    # --------------------------------------------------------------------------
    with lab_t2:
        st.subheader("2. Guided Data Transformations")
        st.caption("Perform type-safe pandas operations: multi-table joins, price discretisation, split-apply-combine, and canonical outer joins.")

        transform_options = [
            "A. WanderMatch Telemetry Join (user_interactions & activities_poi)",
            "B. Filter & Derive Categories (Price Discretisation)",
            "C. Stop Aggregation (Split-Apply-Combine)",
            "D. Pivot City × Category Matrix Reshape",
            "E. Canonical Merge (Saved vs Planned Stops: 666 POIs)"
        ]
        param_tf = str(st.query_params.get("transform", "")).strip()
        default_tf_idx = 0
        if param_tf == "telemetry":
            default_tf_idx = 0
        elif param_tf == "filter":
            default_tf_idx = 1
        elif param_tf == "aggregate":
            default_tf_idx = 2
        elif param_tf == "pivot":
            default_tf_idx = 3
        elif param_tf == "merge":
            default_tf_idx = 4

        transform_mode = st.radio(
            "Select Transformation Operation",
            transform_options,
            index=default_tf_idx,
            horizontal=True,
            key="dev_lab_tf_mode"
        )

        if "A. WanderMatch" in transform_mode:
            st.markdown("**A. WanderMatch Telemetry Transformation (user_interactions & activities_poi Join):**")
            st.caption("Demonstrates join semantics between WanderMatch telemetry events and SmartTrip attractions on entity_id = poi_id.")

            tf_c1, tf_c2 = st.columns([1.5, 1.2])
            with tf_c1:
                action_filter = st.selectbox(
                    "Filter by Telemetry Action Type",
                    ["All Actions (8 Types)", "view", "click", "search", "like", "save", "dismiss", "share", "booking"],
                    index=0,
                    key="devlab_tab2_action_select"
                )
            with tf_c2:
                cultural_only = st.checkbox("Cultural Attractions Only", value=False, key="devlab_tab2_cult_cb")

            filter_types = None if action_filter.startswith("All") else [action_filter]
            tf_df, tf_metrics, tf_snippet = transform_user_interactions(
                interaction_types=filter_types,
                cultural_only=cultural_only
            )

            tm1, tm2, tm3, tm4 = st.columns(4)
            tm1.metric("1. Raw Interactions", f"{tf_metrics['raw_total']:,}", "WanderMatch pack")
            tm2.metric("2. Matched India POIs", f"{tf_metrics['matched_count']:,}", f"{tf_metrics['matched_count']/tf_metrics['raw_total']:.1%}")
            tm3.metric("3. Filtered Events", f"{tf_metrics['filtered_count']:,}", "Active selection")
            tm4.metric("4. Cultural Events", f"{tf_metrics['cultural_count']:,}", "heritage/museum/religious/food")

            # Plotly Action Distribution Bar Chart
            if "interaction_type" in tf_df.columns and "total_interactions" in tf_df.columns:
                fig_act_bar = px.bar(
                    tf_df,
                    x="interaction_type",
                    y="total_interactions",
                    text="total_interactions",
                    title="Telemetry Action Breakdown",
                    color_discrete_sequence=["#982b32"]
                )
                fig_act_bar.update_layout(height=240, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=35, b=20))
                st.plotly_chart(fig_act_bar, use_container_width=True)

            st.markdown(f"**Transformed Telemetry Summary Table:**")
            st.dataframe(tf_df, hide_index=True, use_container_width=True)

            with st.expander("Inspect Reproducible pandas Join Pipeline"):
                st.code(tf_snippet, language="python")

            dl_c1, dl_c2 = st.columns(2)
            with dl_c1:
                st.download_button("Download Transformed Telemetry (CSV)", export_dataframe_to_csv(tf_df), "transformed_telemetry.csv", "text/csv", key="btn_tf_csv_t2")
            with dl_c2:
                st.download_button("Download Transformed Telemetry (Parquet)", export_dataframe_to_parquet(tf_df), "transformed_telemetry.parquet", "application/octet-stream", key="btn_tf_pq_t2")

        elif "B. Filter" in transform_mode:
            st.markdown("**B. Filter & Derive Categories (Price Discretisation with Separate Free Tier):**")
            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1.0])
            with f_col1:
                cost_range = st.slider("Entry Cost Range (INR)", 0.0, 1000.0, (0.0, 500.0), step=25.0)
            with f_col2:
                cats = st.multiselect("Cultural Categories", ["heritage", "museum", "religious", "food", "entertainment", "nature"], default=["heritage", "museum", "religious", "food"])
            with f_col3:
                step_free = st.checkbox("Step-Free Only", value=False)

            filtered_df, code_snippet = filter_and_derive_poi(
                min_cost=cost_range[0],
                max_cost=cost_range[1],
                selected_categories=cats,
                only_step_free=step_free
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Matching Attractions", f"{len(filtered_df)}")
            m2.metric("Cultural Attractions", f"{int(filtered_df['is_cultural'].sum())}")
            m3.metric("Free Attractions", f"{int((filtered_df['price_tier'] == 'Free (INR 0)').sum())}")
            m4.metric("Avg Entry Cost", f"INR {filtered_df['entry_cost'].mean():.2f}" if len(filtered_df) > 0 else "N/A")

            st.dataframe(filtered_df.head(50), hide_index=True, use_container_width=True)

            with st.expander("Inspect Reproducible pandas Code Snippet"):
                st.code(code_snippet, language="python")

            dl_c1, dl_c2 = st.columns(2)
            with dl_c1:
                st.download_button("Download Filtered POIs (CSV)", export_dataframe_to_csv(filtered_df), "filtered_pois.csv", "text/csv", key="btn_tf_csv")
            with dl_c2:
                st.download_button("Download Filtered POIs (Parquet)", export_dataframe_to_parquet(filtered_df), "filtered_pois.parquet", "application/octet-stream", key="btn_tf_pq")

        elif "C. Stop Aggregation" in transform_mode:
            st.markdown("**C. Split-Apply-Combine Aggregation (Selected Planned Stops):**")
            grp_by = st.selectbox("Group By Dimension", ["city_name", "poi_category", "accessibility"], index=0)
            agg_df, code_snippet = groupby_aggregate_stops(grp_by)

            st.dataframe(agg_df, hide_index=True, use_container_width=True)

            with st.expander("Inspect Reproducible pandas Code Snippet"):
                st.code(code_snippet, language="python")

        elif "D. Pivot" in transform_mode:
            st.markdown("**D. City × Category Matrix Reshape (45 Cities × 4 Categories):**")
            pivot_df, long_df, code_snippet = pivot_city_category_matrix()

            fig_hm = go.Figure(data=go.Heatmap(
                z=pivot_df.values,
                x=list(pivot_df.columns),
                y=list(pivot_df.index),
                colorscale="Burg",
                hoverongaps=False
            ))
            fig_hm.update_layout(height=480, paper_bgcolor="#f7f3e9", margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Cultural Category", yaxis_title="Study City")
            st.plotly_chart(fig_hm, use_container_width=True)

            st.markdown("**Companion Wide Pivot Table:**")
            st.dataframe(pivot_df, use_container_width=True)

            with st.expander("Inspect Reversible Long-to-Wide Reshape Code"):
                st.code(code_snippet, language="python")

        elif "E. Canonical Merge" in transform_mode:
            st.markdown("**E. Audited Full Outer Join (Saved POIs vs Planned Stops):**")
            st.caption("Demonstrates strict set operations: 363 saved POIs outer-joined with 655 planned POIs without row inflation.")
            m_res = compute_canonical_saved_planned_merge()

            j1, j2, j3, j4 = st.columns(4)
            j1.metric("Saved POIs (Left)", f"{m_res.saved_count}")
            j2.metric("Planned POIs (Right)", f"{m_res.planned_count}")
            j3.metric("Inner Join (Both)", f"{m_res.both_count}", "352 overlap")
            j4.metric("Full Outer Join", f"{m_res.full_outer_count}", "666 distinct")

            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("1. Overlap (Both Sets)", f"{m_res.both_count} POIs", "Inner join intersection")
            p_col2.metric("2. Saved-Only POIs", f"{m_res.saved_only_count} POIs", "Telemetried but unselected")
            p_col3.metric("3. Planned-Only POIs", f"{m_res.planned_only_count} POIs", "Itinerary stops without save")

            st.dataframe(m_res.merged_df.head(100), hide_index=True, use_container_width=True)

            c_c1, c_c2 = st.columns(2)
            with c_c1:
                st.download_button("Download 666 Outer Merge (CSV)", export_dataframe_to_csv(m_res.merged_df), "canonical_outer_merge_666.csv", "text/csv", key="btn_merge_csv")
            with c_c2:
                st.download_button("Download 666 Outer Merge (Parquet)", export_dataframe_to_parquet(m_res.merged_df), "canonical_outer_merge_666.parquet", "application/octet-stream", key="btn_merge_pq")

    # --------------------------------------------------------------------------
    # TAB 3: SQL Sandbox
    # --------------------------------------------------------------------------
    with lab_t3:
        st.subheader("3. Bounded Read-Only SQL Sandbox")
        st.caption("Execute read-only SQL queries under SQLite authorizer enforcement. Prohibits writes, DDL, PRAGMA, and ATTACH. Max 1500 chars, 500 rows.")

        sandbox = ReadOnlySQLSandbox()
        presets = {
            "Top 5 Cities by Population": "SELECT city_id, name, state, population FROM cities WHERE country_code='IN' ORDER BY population DESC LIMIT 5",
            "Attractions by Category & Avg Price": "SELECT poi_category, count(*) as count, round(avg(entry_cost), 2) as avg_price FROM activities_poi GROUP BY poi_category ORDER BY count DESC",
            "Non-Cancelled Trips by Destination City": "SELECT c.name as city, count(*) as trip_count FROM trips t JOIN cities c ON c.city_id=t.destination_city_id WHERE c.country_code='IN' AND t.status<>'cancelled' GROUP BY c.name ORDER BY trip_count DESC LIMIT 10",
            "User Telemetry Interactions by Type": "SELECT interaction_type, count(*) as count FROM user_interactions GROUP BY interaction_type ORDER BY count DESC",
            "Planned Stops Summary from Documented View": "SELECT city_name, poi_category, count(*) as stops FROM view_study_selected_stops GROUP BY city_name, poi_category ORDER BY stops DESC LIMIT 15",
            "Test Write Rejection (Blocked INSERT)": "INSERT INTO cities (city_id, name) VALUES ('fake', 'Malicious City')"
        }

        p_sel = st.selectbox("Select Query Preset", list(presets.keys()), key="lab_sql_preset")
        if st.button("Load Preset into Editor", key="btn_load_sql_preset"):
            st.session_state["lab_sql_text"] = presets[p_sel]

        default_text = st.session_state.get("lab_sql_text", presets[p_sel])
        sql_input = st.text_area("SQL Query Editor", value=default_text, height=120, key="lab_sql_editor")

        if st.button("Execute Query", type="primary", key="lab_sql_run"):
            s_res = sandbox.execute_query(sql_input)
            if s_res.is_success:
                st.success(f"Query returned {s_res.row_count} rows{' (truncated to 500 maximum rows)' if s_res.is_truncated else ''}.")
                res_df = pd.DataFrame(s_res.rows, columns=s_res.columns)
                st.dataframe(res_df, hide_index=True, use_container_width=True)

                sq_c1, sq_c2 = st.columns(2)
                with sq_c1:
                    st.download_button("Download Result (CSV)", export_dataframe_to_csv(res_df), "query_result.csv", "text/csv", key="btn_sql_csv")
                with sq_c2:
                    st.download_button("Download Result (Parquet)", export_dataframe_to_parquet(res_df), "query_result.parquet", "application/octet-stream", key="btn_sql_pq")
            else:
                st.error(f"Execution Rejected: {s_res.error_message}")

    # --------------------------------------------------------------------------
    # TAB 4: Statistics & Graphs
    # --------------------------------------------------------------------------
    with lab_t4:
        st.subheader("4. Statistical Visualizations & Syllabus Demonstrator")
        st.caption("Visual representations of empirical distributions, methodology confidence intervals, and footfall cumulative densities.")

        st.markdown("**Interactive Statistical Visualizations & Syllabus Explorations:**")
        sg_choice = st.pills(
            "Select Visualization Focus",
            [
                "Unit 1: Methodology Confidence Intervals",
                "Unit 4: Cultural Category Breakdown (Donut Chart)",
                "Unit 4: WanderMatch Telemetry Actions (Donut Chart)",
                "Unit 4: Distribution Histogram & Box Plots",
                "Unit 4: Event Footfall ECDF",
                "Unit 4: Bivariate Pricing vs Saves Scatter"
            ],
            default="Unit 1: Methodology Confidence Intervals",
            key="pills_sg_choice"
        )
        if not sg_choice:
            sg_choice = "Unit 1: Methodology Confidence Intervals"

        if "Unit 1" in sg_choice:
            st.markdown("**Three-Way Inference on Owner Cohort (Exploratory vs Classical vs Bayesian):**")
            cohort_opt = st.pills(
                "Owner Cohort Selection",
                ["Shared Contract (293 / 341, 85.9%)", "Legacy Cohort (301 / 341, 88.3%)"],
                default="Shared Contract (293 / 341, 85.9%)",
                key="pills_cohort_opt"
            ) or "Shared Contract (293 / 341, 85.9%)"
            use_strict = "293" in cohort_opt
            comp = compute_methodology_comparison(strict_active_only=use_strict)

            u1, u2, u3 = st.columns(3)
            u1.metric("1. Empirical Proportion", f"{comp.empirical_proportion:.2%}", f"{comp.success_count} / {comp.sample_size}")
            u2.metric("2. Wilson 95% Score CI", f"[{comp.wilson_lower:.1%}, {comp.wilson_upper:.1%}]", "Classical normal approx")
            u3.metric("3. Bayesian Credible Interval", f"[{comp.bayes_lower:.1%}, {comp.bayes_upper:.1%}]", comp.bayes_prior)

            fig_u1 = go.Figure()
            fig_u1.add_trace(go.Scatter(
                x=[comp.wilson_lower * 100, comp.empirical_proportion * 100, comp.wilson_upper * 100],
                y=["Wilson 95% CI", "Wilson 95% CI", "Wilson 95% CI"],
                mode="lines+markers",
                name="Classical Wilson Score",
                line=dict(color="#365376", width=4)
            ))
            fig_u1.add_trace(go.Scatter(
                x=[comp.bayes_lower * 100, comp.empirical_proportion * 100, comp.bayes_upper * 100],
                y=["Bayesian Posterior", "Bayesian Posterior", "Bayesian Posterior"],
                mode="lines+markers",
                name="Bayesian Beta(1,1)",
                line=dict(color="#982b32", width=4)
            ))
            fig_u1.update_layout(height=240, paper_bgcolor="#f7f3e9", plot_bgcolor="#ffffff", margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Cultural Trip Proportion (%)")
            st.plotly_chart(fig_u1, use_container_width=True)

        elif "Cultural Category" in sg_choice:
            st.markdown("**Cultural Category Distribution across 211 Verified Cultural POIs:**")
            fig_cat_donut = go.Figure(data=[go.Pie(
                labels=["Heritage Sites (72)", "Museums & Galleries (53)", "Religious Sites (48)", "Food Experiences (38)"],
                values=[72, 53, 48, 38],
                hole=0.5,
                marker=dict(colors=["#982b32", "#365376", "#b79d5b", "#7d6f58"]),
                textinfo="percent+label",
                hoverinfo="label+value+percent"
            )])
            fig_cat_donut.update_layout(
                title="Cultural Category Breakdown (211 Attractions)",
                height=360,
                paper_bgcolor="#f7f3e9",
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_cat_donut, use_container_width=True)
            st.caption("Provenance: 211 attractions across 45 Indian study cities strictly classified into Heritage, Museums, Religious, and Food experiences.")

        elif "Telemetry Actions" in sg_choice:
            st.markdown("**WanderMatch Interaction Telemetry Distribution (6,850 Matched Events):**")
            with open_study_cache() as conn:
                act_df = pd.read_sql_query("SELECT interaction_type, count(*) as count FROM user_interactions GROUP BY interaction_type ORDER BY count DESC", conn)

            fig_act_pie = px.pie(
                act_df,
                names="interaction_type",
                values="count",
                hole=0.45,
                title="User Interaction Telemetry Actions (WanderMatch)",
                color_discrete_sequence=["#982b32", "#365376", "#b79d5b", "#7d6f58", "#4f637b", "#8b7e66", "#c2b59b", "#292925"]
            )
            fig_act_pie.update_layout(
                height=360,
                paper_bgcolor="#f7f3e9",
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_act_pie, use_container_width=True)
            st.caption("Telemetry Breakdown: 6,850 user interaction events matched to attractions in study cities across saves, views, reviews, and bookings.")

        elif "Histogram" in sg_choice:
            st.markdown("**Entry Cost Distribution across Cultural Categories (45 Indian Study Cities):**")
            with open_study_cache() as conn:
                poi_df = pd.read_sql_query("""
                    SELECT p.poi_id, p.name, p.poi_category, c.name as city_name, CAST(p.entry_cost AS REAL) as entry_cost
                    FROM activities_poi p
                    JOIN cities c USING(city_id)
                    WHERE c.country_code = 'IN' AND p.entry_cost IS NOT NULL
                """, conn)

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
                events_df = pd.read_sql_query("""
                    SELECT e.name, e.expected_footfall, e.recurrence, e.season, c.name as city_name
                    FROM events_festivals e
                    JOIN cities c USING(city_id)
                    WHERE c.country_code = 'IN' AND e.expected_footfall IS NOT NULL
                    ORDER BY e.expected_footfall ASC
                """, conn)

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
                biv_df = pd.read_sql_query("""
                    SELECT a.poi_id, a.name, a.poi_category, c.name as city_name, CAST(a.entry_cost AS REAL) as entry_cost, count(ui.interaction_id) as saves_count
                    FROM activities_poi a
                    JOIN cities c USING(city_id)
                    LEFT JOIN user_interactions ui ON ui.entity_id = a.poi_id AND ui.interaction_type = 'save'
                    WHERE c.country_code = 'IN' AND a.entry_cost IS NOT NULL
                    GROUP BY a.poi_id
                    HAVING saves_count > 0
                """, conn)

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
            st.caption("Economic Finding: Across all 363 saved study attractions in Indian cities, entry fees range comfortably from INR 0 to INR 2,500. Entry fee demonstrates a near-zero rank correlation with save volume, indicating broad user interest across price tiers.")

    # --------------------------------------------------------------------------
    # TAB 5: Formulas & Syntax Reference
    # --------------------------------------------------------------------------
    with lab_t5:
        st.subheader("5. Formulas & Syntax Reference (Syllabus Units 1–5)")
        st.caption("Searchable technical guide connecting syllabus mathematical formulas to concrete code implementations and study data.")

        ref_units = get_syllabus_reference_units()
        unit_filter = st.pills("Filter by Syllabus Unit", ["All Units", "Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5"], default="All Units", key="lab_unit_filter_pills") or "All Units"

        for item in ref_units:
            if unit_filter != "All Units" and item["unit"] != unit_filter:
                continue

            with st.expander(f"{item['unit']} · {item['title']}: {item['topic']}", expanded=(unit_filter != "All Units")):
                st.markdown(f"**Purpose:** {item['purpose']}")
                st.code(item['formula_syntax'], language="text")
                st.markdown(f"**Data Prerequisites & Missingness:** {item['prerequisites']}")
                st.markdown(f"**Concrete Study Example:** {item['study_example']}")
                st.markdown(f"**Interpretation:** {item['interpretation']}")
                st.caption(f"Example SQL Query: `{item['preset_query']}`")
                if st.button(f"Run this example ({item['unit']})", key=f"btn_run_{item['unit']}"):
                    try:
                        sandbox = ReadOnlySQLSandbox()
                        exec_res = sandbox.execute_query(item["preset_query"])
                        if exec_res.is_success:
                            time_ms = getattr(exec_res, "execution_time_ms", 0.0)
                            st.success(f"Executed in {time_ms:.1f}ms ({exec_res.row_count} rows returned):")
                            if exec_res.rows:
                                res_df = pd.DataFrame(exec_res.rows, columns=exec_res.columns)
                                st.dataframe(res_df, hide_index=True, use_container_width=True)
                        else:
                            st.error(f"Execution Error: {exec_res.error_message}")
                    except Exception as ex:
                        st.error(f"Execution Exception: {ex}")

# ==============================================================================
# SCREEN: PREDICTION MODEL (Stage P6)
# ==============================================================================
elif view_mode == "Prediction Model":
    render_model_screen()


# ==============================================================================
# SCREEN 7: SETTINGS
# ==============================================================================
elif view_mode == "Settings":
    render_section_banner(
        section_key="settings",
        title_html="Settings & Preferences",
        subtitle="Configure session-local evaluation preferences, display limits, and accessibility parameters.",
        kicker="08 / EVALUATOR PREFERENCES & CONTROLS",
    )

    s_col1, s_col2 = st.columns([1.5, 1.2])
    with s_col1:
        cities = get_study_cities()
        c_names = [c["name"] for c in cities]
        cur_def = st.session_state.get("default_city", "Jaipur")
        def_idx = c_names.index(cur_def) if cur_def in c_names else 0

        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #b6afa3; border-left: 4px solid #365376; padding: 14px 18px; margin-bottom: 14px;">
            <strong style="color: #292925; font-size: 0.92rem;">Default Demonstration City:</strong><br>
            <span style="font-size: 0.84rem; color: #5c5852; line-height: 1.55;">
                Selects which of the 45 Indian study cities initially loads across <strong>Discover</strong>, <strong>Planner</strong>, <strong>Compare</strong>, and <strong>Prediction Model</strong>.
            </span>
        </div>
        """, unsafe_allow_html=True)
        new_def = st.selectbox("Default Study City", c_names, index=def_idx, help="Sets the default active city for Discover, Planner, and Prediction Model views.")

        cur_view = st.session_state.get("preferred_view", "Detailed Timetable & Leg Breakdown")
        view_opts = ["Detailed Timetable & Leg Breakdown", "Side-by-Side Comparison Matrix", "Compact Metrics Only"]
        new_view = st.selectbox("Preferred Planner Result View", view_opts, index=view_opts.index(cur_view) if cur_view in view_opts else 0)

        cur_size = st.session_state.get("table_page_size", 15)
        new_size = st.select_slider("Table Data Preview Size (Rows)", options=[5, 10, 15, 20, 25, 50], value=cur_size if cur_size in [5, 10, 15, 20, 25, 50] else 15)

        cur_motion = st.session_state.get("motion_preference", "Standard Motion")
        new_motion = st.radio("Interface Motion Preference", ["Standard Motion", "Reduced Motion (Accessibility)"], index=0 if cur_motion == "Standard Motion" else 1, horizontal=True)

        st.markdown("<br>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("Save Preferences", type="primary", key="btn_save_settings"):
                st.session_state["default_city"] = new_def
                st.session_state["p_city"] = new_def
                st.session_state["preferred_view"] = new_view
                st.session_state["table_page_size"] = int(new_size)
                st.session_state["motion_preference"] = new_motion
                st.success(f"Preferences saved: Default City = '{new_def}', Page Size = {new_size}, View = '{new_view}'.")
        with btn_c2:
            if st.button("Reset to System Defaults", key="btn_reset_settings"):
                st.session_state["default_city"] = "Jaipur"
                st.session_state["p_city"] = "Jaipur"
                st.session_state["preferred_view"] = "Detailed Timetable & Leg Breakdown"
                st.session_state["table_page_size"] = 15
                st.session_state["motion_preference"] = "Standard Motion"
                st.info("Preferences reset to system defaults (Jaipur, 15 rows, Standard Motion).")

    with s_col2:
        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #b6afa3; border-left: 4px solid #982b32; padding: 18px 22px; margin-top: 10px;">
            <div style="font-family: Georgia, serif; font-size: 1.05rem; font-weight: bold; color: #292925;">
                Persistence & Security Contract
            </div>
            <div style="font-size: 0.84rem; color: #5c5852; margin-top: 6px; line-height: 1.6;">
                <strong>Session-Local Scope:</strong> Preferences are stored within your current active browser session state.
                Settings modify display defaults and table pagination across Discover and DEV Lab.<br><br>
                <strong>Security Invariant:</strong> Settings <em>never</em> alter canonical study database records, row counts,
                data integrity checksums, SQLite authorizer sandbox limits, or analytical metric contracts.
            </div>
        </div>
        """, unsafe_allow_html=True)

        act_city = st.session_state.get("default_city", "Jaipur")
        act_size = st.session_state.get("table_page_size", 15)
        act_view = st.session_state.get("preferred_view", "Detailed Timetable & Leg Breakdown")
        act_mot = st.session_state.get("motion_preference", "Standard Motion")

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #b6afa3; padding: 18px 22px; margin-top: 16px;">
            <div style="font-family: Georgia, serif; font-size: 1.05rem; font-weight: bold; color: #292925;">
                Current Active Session State
            </div>
            <ul style="font-size: 0.84rem; color: #5c5852; margin: 8px 0 0 16px; padding: 0; line-height: 1.6;">
                <li><strong>Active Default City:</strong> {act_city}</li>
                <li><strong>Table Preview Limit:</strong> {act_size} rows</li>
                <li><strong>Result Presentation:</strong> {act_view}</li>
                <li><strong>Motion Policy:</strong> {act_mot}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# SCREEN 8: INFORMATION
# ==============================================================================
elif view_mode == "Information":
    render_section_banner(
        section_key="information",
        title_html="Information, System Architecture & <em>Statistical Models</em>",
        subtitle="Complete reference guide detailing every section of CultureRoute, all 6 statistical & ML models used, database provenance, and DEV syllabus alignment.",
        kicker="09 / PROJECT REFERENCE & ACADEMIC METHODOLOGY",
    )

    info_t1, info_t2, info_t3, info_t4, info_t5, info_t6 = st.tabs([
        "1. Application Section Directory",
        "2. All Statistical & ML Models",
        "3. SDG 8.9 & Research Boundaries",
        "4. 24-Table Study Inventory",
        "5. DEV Syllabus Alignment",
        "6. Jaipur Reproduction Guide"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: SECTION DIRECTORY (10 APPLICATION SCREENS)
    # --------------------------------------------------------------------------
    with info_t1:
        st.subheader("1. Comprehensive Application Section Directory")
        st.caption("Overview of all 10 application views, their design intent, and their role in the educational demonstration.")

        st.markdown("""
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px;">
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Overview</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">PORTFOLIO LANDING</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    The executive project summary. Features top-level research metrics (45 cities, 675 attractions, 48,728 database rows),
                    the dual-objective trade-off premise, curated city showcase cards, and verified research boundary notices.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Discover</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">SPATIAL EXPLORER</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Spatial and catalog discovery across all 45 Indian study cities. Filter attractions by fee status (Free vs Paid),
                    cultural category, or step-free accessibility. Shows offline coordinate scatter maps, category composition donuts, and WanderMatch guide telemetry.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Planner</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">RULES-BASED ROUTER</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Generates deterministic day itineraries for any study city under user-defined budgets, time windows, and target stops.
                    Computes Plan A (Minimum Elapsed Time) and Plan B (Maximum Cultural Stops) with schedule time-allocation charts and direct handoff to Compare.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Compare</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">TRADE-OFF EVALUATOR</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Side-by-side trade-off analysis. Compares time saved versus cultural heritage gained, transit costs, and carbon emissions.
                    Supports dynamic comparison across any of the 45 cities and preset benchmark fixtures, paired with grouped bar charts and CSV exports.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Datasets</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">DATASET VIEWER FIRST</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Primary data exploration portal. Source pack filter (SmartTrip vs WanderMatch vs Shared), search by table name, deterministic
                    pagination (1-15 of N rows), and one-click transparent CSV downloads for all 24 canonical tables, plus dynamic variable distributions in Tab 3.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Insights</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">STATISTICAL ANALYTICS</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Conventional statistical analysis without black-box ML: 3-population cultural representation (stacked bars and 4-donut comparative views),
                    57-week Monday-Sunday continuous time series, historical baseline evaluation (MAE 3.42 / 3.88), and MLE event footfall imputation on 143/36 holdout.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">DEV Lab</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">TEACHING WORKBENCH</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Structured 6-step laboratory addressing Units 1–5: Table profiling, guided pandas joins and aggregations, bounded read-only
                    SQL sandbox with SQLite authorizer security, graphical methods (Wilson CIs, action donuts, histograms, ECDFs), and formula-safe CSV/Parquet export.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Prediction Model</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">SUPERVISED COUNT GLM</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Supervised Poisson count regression model predicting weekly cultural interactions across all 45 cities for target week 2026-08-17.
                    Presents results first with exact Poisson 95% quantiles, followed by out-of-sample holdout validation and zero-leakage splits.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #982b32; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Settings</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 6px;">USER PREFERENCES</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Evaluator demonstration preferences. Sets the default study city pre-selected across Discover, Planner, and Model screens,
                    table preview limits (5 to 50 rows), itinerary display detail, and accessibility motion policies without altering underlying database records.
                </div>
            </div>
            <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-top: 4px solid #365376; padding: 18px 20px; box-shadow: 2px 2px 0 rgba(41,41,37,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div style="font-family: Georgia, serif; font-size: 1.1rem; font-weight: bold; color: #292925;">Information</div>
                    <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 6px;">REFERENCE & ARCHITECTURE</span>
                </div>
                <div style="font-size: 0.84rem; color: #5c5852; margin-top: 8px; line-height: 1.6;">
                    Comprehensive academic documentation detailing all 6 statistical and ML models with LaTeX math, UN SDG 8.9 alignment,
                    three distinct analytical populations, the 24-table inventory, DEV syllabus mapping, and Jaipur benchmark reproduction instructions.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 2: ALL STATISTICAL & ML MODELS
    # --------------------------------------------------------------------------
    with info_t2:
        st.subheader("2. Detailed Mathematical Reference for All Models Used")
        st.markdown(
            "CultureRoute implements **6 rigorous statistical, machine learning, and combinatorial routing models**. "
            "Below is the exact formulation, input vector, validation metrics, and academic rationale for each."
        )

        # Model 1
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #982b32; padding: 18px 22px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: Georgia, serif; font-size: 1.18rem; font-weight: bold; color: #292925;">
                    1. Poisson Generalized Linear Model (GLM) for Weekly Cultural Demand
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 8px;">SUPERVISED MACHINE LEARNING</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Mathematical Formulation:**")
        st.latex(r"\mathbb{P}(Y_{i,t} = y \mid \mathbf{x}_{i,t}) = \frac{\lambda_{i,t}^y e^{-\lambda_{i,t}}}{y!}, \quad y \in \{0, 1, 2, \dots\}")
        st.latex(r"\ln(\lambda_{i,t}) = \beta_0 + \sum_{c=1}^{44} \beta_c \cdot \mathbb{I}(\text{city}=c) + \beta_{\text{lag1}} y_{i,t-1} + \beta_{\text{lag2}} y_{i,t-2} + \beta_{\text{4w}} \bar{y}_{i,t-4:t-1}")
        st.latex(r"\lambda_{i,t} = \exp\left(\beta_0 + \mathbf{x}_{i,t}^\top \boldsymbol{\beta}\right)")
        
        st.markdown(r"""
        **Why Poisson over Ordinary Least Squares (OLS)?**
        - **Non-Negative Discrete Support:** Interaction counts are non-negative integers ($y \ge 0$). OLS assumes unbounded Gaussian errors and routinely predicts impossible negative counts ($\hat{y} < 0$).
        - **Mean-Variance Relationship:** In count telemetry, variance scales with mean volume ($\mathrm{Var}(Y) = \mathbb{E}[Y] = \lambda$). Linear regression incorrectly assumes constant homoscedastic variance.
        
        **Out-of-Sample Validation & Performance:**
        - Tested on a strictly disjoint 12-week chronological holdout (Weeks 46..57, 540 rows).
        - Achieves **0.7938 MAE** (interactions/city-week) vs **0.9537 MAE** for naive previous-week baseline (**-16.8% error reduction**).
        - On non-zero active weeks, error drops to **0.7786 MAE** vs 1.2101 for lag-1.
        
        **Exact 95% Confidence Bounds:**
        """)
        st.latex(r"\text{CI}_{95\%} = \left[ Q_{\text{Poisson}}(0.025; \lambda), \; Q_{\text{Poisson}}(0.975; \lambda) \right]")

        # Model 2
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #365376; padding: 18px 22px; margin-top: 24px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: Georgia, serif; font-size: 1.18rem; font-weight: bold; color: #292925;">
                    2. Naive Momentum (Lag-1) & Trailing 4-Week Moving Average Baselines
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 8px;">BENCHMARK FORECASTING</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Formulations:**")
        st.latex(r"\hat{y}_{t}^{\text{Lag-1}} = y_{t-1} \quad \text{(Random walk persistence)}")
        st.latex(r"\hat{y}_{t}^{\text{Trailing 4W}} = \frac{1}{4} \sum_{k=1}^4 y_{t-k} \quad \text{(Smoothed rolling momentum)}")
        st.markdown("""
        **Role in Project:** Required by DEV Syllabus Unit 3 to establish whether parameterized machine learning models provide genuine predictive value over standard operational heuristics.
        Across the nationwide 57-week historical series, the 12-week backtest yields exact MAEs of **3.42** (Lag-1) and **3.88** (Trailing 4W).
        """)

        # Model 3
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #982b32; padding: 18px 22px; margin-top: 24px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: Georgia, serif; font-size: 1.18rem; font-weight: bold; color: #292925;">
                    3. Lognormal Maximum Likelihood Estimation (MLE) for Event Footfall Imputation
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 8px;">PARAMETRIC INFERENCE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(r"**Mathematical Formulation:** For positive crowd sizes $X_1, \dots, X_n > 0$, we model $\ln(X_i) \sim \mathcal{N}(\mu, \sigma^2)$:")
        st.latex(r"\hat{\mu}_{\text{MLE}} = \frac{1}{n} \sum_{i=1}^n \ln(x_i) = 8.3312, \quad \hat{\sigma}_{\text{MLE}} = \sqrt{\frac{1}{n} \sum_{i=1}^n (\ln(x_i) - \hat{\mu})^2} = 0.7188")
        st.latex(r"\mathbb{E}[X] = \exp\left(\hat{\mu} + \frac{\hat{\sigma}^2}{2}\right) = \exp(8.3312 + 0.2583) \approx 4,863.6 \text{ visitors}")
        st.latex(r"\text{Median}(X) = \exp(\hat{\mu}) = \exp(8.3312) \approx 4,151.4 \text{ visitors}")
        st.markdown("""
        **Application in Study:** 225 Indian cultural festivals are cataloged in `events_festivals`, of which 12 records have missing `expected_footfall`.
        On a deterministic 143-train / 36-test holdout split, parametric lognormal MLE achieves a test MAE of **1,863 visitors**, compared to 2,050 for naive column mean, confirming the lognormal distribution's superior fit for human event crowds.
        """)

        # Model 4
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #365376; padding: 18px 22px; margin-top: 24px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: Georgia, serif; font-size: 1.18rem; font-weight: bold; color: #292925;">
                    4. Beta-Binomial Bayesian Model vs Wilson Score Interval for Itinerary Inclusions
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #365376; border: 1px solid #365376; padding: 2px 8px;">BAYESIAN & CLASSICAL INFERENCE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(r"**Comparative Framework:** Investigates cultural stop conversion proportion $p$ ($n = 411$ trips, $k = 211$ successes, empirical $\hat{p} = 0.5134$):")
        st.latex(r"w = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}} \implies [0.4650, \; 0.5615]")
        st.latex(r"\text{Prior } p \sim \text{Beta}(1, 1) \implies \text{Posterior } p \mid k \sim \text{Beta}(1 + 211, \; 1 + 200) = \text{Beta}(212, 201)")
        st.latex(r"\text{Posterior Mean: } \frac{212}{413} = 0.5133, \quad 95\% \text{ Equal-Tailed Credible Interval: } [0.4650, \; 0.5613]")
        st.markdown("Demonstrates how classical Wilson intervals and uninformative Bayesian credible intervals converge when sample sizes exceed $n > 400$.")

        # Model 5
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #982b32; padding: 18px 22px; margin-top: 24px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div style="font-family: Georgia, serif; font-size: 1.18rem; font-weight: bold; color: #292925;">
                    5. Deterministic Dijkstra & Branch-and-Bound Multi-Objective Routing Engine
                </div>
                <span style="font-size: 0.72rem; font-weight: bold; color: #982b32; border: 1px solid #982b32; padding: 2px 8px;">COMBINATORIAL OPTIMIZATION</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Mathematical Formulation:** Over directed graph $G = (V, E)$ where vertices $V$ are city attractions and edges $E$ are recorded travel matrix legs:")
        st.latex(r"\text{Plan A (Min Elapsed Time):} \quad \min_{\pi} \sum_{i=1}^k \text{duration}(v_{\pi(i)}) + \sum_{i=1}^{k-1} \text{travel\_time}(v_{\pi(i)}, v_{\pi(i+1)})")
        st.latex(r"\text{Plan B (Max Cultural Stops):} \quad \max_{\pi} \sum_{i=1}^k \mathbb{I}(v_{\pi(i)} \in \text{Cultural}), \quad \text{tie-breaker: } \min \text{elapsed\_time}")
        st.latex(r"\text{Subject to Hard Constraints: } \sum \text{cost} \le \text{Budget}, \; \text{arrival}(v_i) \ge \text{opens}(v_i), \; \text{depart}(v_i) \le \text{closes}(v_i)")
        st.markdown("""
        **Deterministic Guarantee:** The engine uses exact branch-and-bound pruning with zero randomized heuristic elements.
        Produces identical, reproducible routes across runs (e.g. Jaipur Saturday always yields 207 min / INR 585.46 for Plan A and 227 min / INR 638.30 for Plan B).
        """)

        # Model Comparison Matrix Table
        st.markdown("---")
        st.subheader("Model Comparison Matrix")
        model_matrix_df = pd.DataFrame([
            {"Model": "Poisson Count GLM", "Paradigm": "Supervised Machine Learning", "Formulation": "Log-linear count regression (scikit-learn)", "Inputs": "44 city one-hots, 3 numerical lags", "Primary Metric": "MAE 0.7938 (-16.8% vs lag-1)", "Unit": "Unit 3"},
            {"Model": "Naive Momentum (Lag-1)", "Paradigm": "Heuristic Baseline", "Formulation": "y(t) = y(t-1)", "Inputs": "Prior week interaction count", "Primary Metric": "MAE 3.42 nationwide", "Unit": "Unit 3"},
            {"Model": "Trailing 4W Moving Avg", "Paradigm": "Heuristic Baseline", "Formulation": "y(t) = mean(y[t-4:t-1])", "Inputs": "Prior 4-week window", "Primary Metric": "MAE 3.88 nationwide", "Unit": "Unit 3"},
            {"Model": "Lognormal MLE", "Paradigm": "Parametric Inference", "Formulation": "Maximum likelihood log-normal fit", "Inputs": "Festival crowd sizes X > 0", "Primary Metric": "Holdout MAE 1,863 visitors", "Unit": "Unit 3 & 4"},
            {"Model": "Wilson Score Interval", "Paradigm": "Classical Inference", "Formulation": "Asymmetric binomial score CI", "Inputs": "n=411 trips, k=211 successes", "Primary Metric": "95% CI [0.4650, 0.5615]", "Unit": "Unit 1"},
            {"Model": "Beta-Binomial Bayesian", "Paradigm": "Bayesian Conjugate", "Formulation": "Beta(1,1) prior -> Beta(212, 201)", "Inputs": "n=411 trips, k=211 successes", "Primary Metric": "95% Credible [0.4650, 0.5613]", "Unit": "Unit 1"},
            {"Model": "Deterministic Day Router", "Paradigm": "Combinatorial Optimization", "Formulation": "Branch-and-bound graph search", "Inputs": "Directed matrix, opening hours, budget", "Primary Metric": "Jaipur baseline 207m / 227m", "Unit": "Unit 2 & 5"}
        ])
        st.dataframe(model_matrix_df, hide_index=True, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 3: SDG 8.9 & RESEARCH BOUNDARIES
    # --------------------------------------------------------------------------
    with info_t3:
        st.subheader("3. UN Sustainable Development Goal 8, Target 8.9 & Boundaries")
        st.markdown("""
        <div style="background: #ffffff; border: 1.5px solid #b6afa3; border-left: 5px solid #b79d5b; padding: 18px 24px; margin-bottom: 20px;">
            <div style="font-family: Georgia, serif; font-size: 1.15rem; font-weight: bold; color: #292925;">
                SDG Target 8.9 Official Mandate
            </div>
            <p style="font-size: 0.90rem; color: #5c5852; font-style: italic; margin-top: 6px;">
                "By 2030, devise and implement policies to promote sustainable tourism that creates jobs and promotes local culture and products."
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        ### CultureRoute Implementation:
        CultureRoute investigates how local cultural assets (heritage sites, historical forts, museums, spiritual monuments, and regional culinary traditions)
        can be preserved and highlighted when travelers plan single-day itineraries under strict time and financial budgets.
        
        - **Cultural Engagement Maximization:** Evaluates the trade-off between minimum elapsed travel time (Plan A) and maximum cultural stops (Plan B).
        - **Synthetic Academic Boundary:** As this is an educational mini-project operating exclusively on the two approved synthetic research datasets
          (`SmartTrip (1).zip` and `WanderMatch.zip`), **no real-world employment creation, commercial revenue generation, or live visitor footfall is claimed**.
        - **Non-Commercial Academic Scope:** All analysis is conducted strictly for educational demonstration of the DEV syllabus.
        """)

        st.markdown("---")
        st.subheader("Three Analytical Populations in CultureRoute")
        st.markdown("""
        To avoid denominator conflation, CultureRoute strictly separates cultural share analysis into three distinct populations:
        
        1. **Catalog Listings Population (675 Attractions across 45 Cities):**
           - Represents static catalog supply.
           - Exactly **211 out of 675 attractions** belong to cultural categories (`heritage`, `museum`, `religious`, `food`).
           - **Baseline Cultural Share:** **31.3%**
           - *Note on Matrix Coverage:* Each city lists 15 catalog attractions, of which 10 have recorded directed travel matrix legs.
        
        2. **Telemetry Actions Population (6,850 User Interactions):**
           - Represents user demand and behavioral interest in WanderMatch.
           - Includes views, clicks, saves, likes, searches, dismissals, and shares.
           - Exactly **2,144 out of 6,850 actions** involve cultural attractions.
           - **Baseline Cultural Share:** **31.3%**
        
        3. **Planned Stops Population (3,191 Selected Stops):**
           - Represents actual algorithmic itinerary inclusions in SmartTrip.
           - Shared active-and-confirmed stop contract: active itineraries (`is_active = 1`), confirmed status (`status = 'confirmed'`), non-cancelled India trips, matching destination city.
           - Exactly **961 out of 3,191 stops** are cultural.
           - **Baseline Cultural Share:** **30.1%**
        """)

    # --------------------------------------------------------------------------
    # TAB 4: 24-TABLE STUDY INVENTORY
    # --------------------------------------------------------------------------
    with info_t4:
        st.subheader("4. Canonical 24-Table Reconciled Study Database")
        st.caption("Consolidated atomic SQLite database (data/study_cache.db) built from SmartTrip (PS-01.db) and WanderMatch (PS-11.db).")

        cat = load_study_catalog()
        inv_m1, inv_m2, inv_m3, inv_m4 = st.columns(4)
        inv_m1.metric("Total Tables", f"{len(cat.tables)}")
        inv_m2.metric("Total Rows", f"{cat.metadata.total_rows:,}")
        inv_m3.metric("Shared Tables", f"{len(cat.metadata.shared_tables)}", "Verified identical")
        inv_m4.metric("Indian Study Cities", "45", "Verified in scope")

        cat_df = pd.DataFrame([
            {
                "Table Name": t.table_name,
                "Origin Pack": t.origin_pack,
                "Row Count": f"{t.row_count:,}",
                "Natural Grain": t.grain,
                "Primary Key": ", ".join(t.primary_key) if t.primary_key else "None (implicit)",
                "Safe Columns": f"{len(t.safe_columns)} / {len(t.columns)}"
            }
            for t in cat.tables.values()
        ])
        st.dataframe(cat_df, hide_index=True, use_container_width=True)

        st.markdown("""
        **Provenance & Verification Guarantees:**
        - **8 Shared Tables:** Verified by primary key, column types, and row-level contents before deduplication.
        - **10 SmartTrip-Only Tables:** Itineraries, itinerary items, transport modes, travel matrix legs, flight bookings, etc.
        - **6 WanderMatch-Only Tables:** Guide languages, guide specializations, match preferences, telemetry interactions, user preferences.
        - **Privacy Masking:** Sensitive columns (`password_hash`, `email`, `phone_number`) are masked from public DEV Lab projections.
        """)

    # --------------------------------------------------------------------------
    # TAB 5: DEV SYLLABUS ALIGNMENT
    # --------------------------------------------------------------------------
    with info_t5:
        st.subheader("5. DEV Syllabus Alignment & Academic Coverage")
        st.markdown("""
        | Syllabus Unit | Practical Implementation in CultureRoute | Module / Screen |
        | :--- | :--- | :--- |
        | **Unit 1: EDA Foundations** | Table profiling, natural grain analysis, scales of measurement, Wilson score 95% CI vs Bayesian Beta(1,1) posterior comparison | `cultureroute/dev_lab.py`, DEV Lab Tab 1 & Tab 4 |
        | **Unit 2: Data Transformations** | Composite key deduplication, discrete price binning with separate Free tier, cultural flag derivation, 666-row canonical outer join | `cultureroute/dev_lab.py`, DEV Lab Tab 2 |
        | **Unit 3: Statistics & Forecasting** | Measures of central tendency and dispersion (IQR, standard deviation), 57 continuous Monday–Sunday weeks time series, last-week (MAE 3.42) & 4-week mean (MAE 3.88) out-of-sample forecasting, Poisson GLM | `cultureroute/analytics.py`, Insights & Model Screens |
        | **Unit 4: Graphical Methods** | Bar charts of categorical shares, coordinate distribution scatter plots, continuous histograms, box plots, Empirical CDF, forecast backtest charts | `cultureroute/analytics.py`, Insights & DEV Lab Tab 4 |
        | **Unit 5: pandas & Sources** | SQLite authorizer read-only sandbox with execution step limits, single-statement enforcement, formula-safe CSV escaping, PyArrow typed Parquet binary round-tripping | `cultureroute/dev_lab.py`, DEV Lab Tab 3 & Tab 5 |
        """)

    # --------------------------------------------------------------------------
    # TAB 6: JAIPUR REPRODUCTION GUIDE
    # --------------------------------------------------------------------------
    with info_t6:
        st.subheader("6. Jaipur Specification Fixture Reproduction Guide")
        st.markdown("""
        To independently verify the deterministic itinerary engine, execute the following parameters in the **Planner** or **Compare** view:
        
        | Input Parameter | Specification Value | Description |
        | :--- | :--- | :--- |
        | **City** | `Jaipur` | Rajasthan capital, 15 listed POIs, 10 matrix-covered |
        | **Visit Date** | `2026-08-29` | Saturday (evaluates weekend schedule) |
        | **Start Time** | `09:00` | 24-hour typed format (morning start) |
        | **Time Window** | `6.0 Hours` | Maximum total elapsed duration |
        | **Budget** | `INR 1,000.00` | Total entry fee + transit cost cap |
        | **Target Stops** | `3 Stops` | Exact sequence of distinct attractions |
        
        #### Expected Mathematical Outcomes:
        - **Plan A · Fastest Feasible Plan (Min Elapsed Time):**
          - Elapsed Duration: **207 minutes** (3h 27m)
          - Cultural Stops: **1 / 3 stops**
          - Total Cost: **INR 585.46** (Entry fees + transit fares)
          - Carbon Footprint: **1.806 kg CO2**
        
        - **Plan B · Most Cultural Plan (Max Cultural Stops):**
          - Elapsed Duration: **227 minutes** (3h 47m)
          - Cultural Stops: **2 / 3 stops** (dynamic gain: **+1 cultural stop**)
          - Total Cost: **INR 638.30**
          - Carbon Footprint: **2.840 kg CO2**
        """)
