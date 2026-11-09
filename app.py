"""CultureRoute Streamlit Application Entrypoint.

Provides:
- Overview of CultureRoute and research question.
- Synthetic Research Study (45 cities, 675 attractions, 411 trips, 24 tables).
- Real-Place Discovery (Real settlements & cultural attractions outside and inside study areas with explicit provenance).
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st
import pandas as pd
from cultureroute.study_data import verify_and_audit_study, get_study_cities, get_city_attractions
from cultureroute.domain import CulturalCategory, ResultLevel, VerificationStatus, FeeStatus, AccessibilityStatus
from cultureroute.catalog import RealCatalogStore
from cultureroute.boundary import is_coordinate_in_india_bbox

# Database Path for Real Catalog
REAL_CATALOG_DB = Path(__file__).resolve().parent / "data" / "real_catalog.db"

# Page Configuration
st.set_page_config(
    page_title="CultureRoute — Cultural Day Trip Planner & DEV Lab",
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling to reflect warm editorial cream palette
st.markdown("""
<style>
    .reportview-container, .main .block-container {
        background-color: #faf7f0;
        color: #222222;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .stMetric {
        background: #ffffff;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #e2dac9;
    }
    .badge-synthetic {
        display: inline-block;
        background-color: #e2f0d9;
        color: #2b542c;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .badge-real {
        display: inline-block;
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .badge-discovery {
        background-color: #e2e3e5;
        color: #383d41;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .place-card {
        background: #ffffff;
        border: 1px solid #e2dac9;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .unknown-tag {
        color: #856404;
        background-color: #fff3cd;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .known-tag {
        color: #155724;
        background-color: #d4edda;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# App Navigation
st.sidebar.title("✳ CultureRoute")
st.sidebar.markdown("**Phase 3: Real-Place Discovery & Provenance**")

# Check query params for deep-linking
query_params = st.query_params
default_index = 0
if "view" in query_params:
    view_param = query_params["view"]
    if view_param in ["overview"]:
        default_index = 0
    elif view_param in ["study", "45cities", "lab", "insights"]:
        default_index = 1
    elif view_param in ["discover", "explorer", "real"]:
        default_index = 2

view_mode = st.sidebar.radio(
    "Select Area",
    [
        "Project Overview & Evidence",
        "Synthetic Research Study (45 Cities)",
        "Real-Place Discovery (Nationwide / Partial Coverage)",
    ],
    index=default_index
)

st.sidebar.divider()
st.sidebar.info(
    "**Boundary Notice**:\n"
    "• Synthetic Study data is loaded read-only from SmartTrip & WanderMatch packs.\n"
    "• Real places are indexed from OpenStreetMap, Wikidata, and UN/LOCODE. No itineraries are generated in this phase."
)


# =====================================================================
# VIEW 1: PROJECT OVERVIEW
# =====================================================================
if view_mode == "Project Overview & Evidence":
    st.title("Explore the culture behind every route")
    st.caption("CultureRoute / DEV AAT / Cultural Tourism Research & DEV Lab")

    st.markdown("""
    CultureRoute is designed around an exploratory research question:
    > **How does the representation of heritage sites, museums, religious sites, and food experiences differ across attraction listings, online interactions, and planned stops?**
    
    ### Scope & Evidence Foundations
    - **Synthetic Research Study**: An offline, reproducible study across **45 Indian cities**, covering **675 listed attractions** (15 per city) and **411 non-cancelled destination trips**. All interaction and trip rows are synthetic.
    - **Local Culture Alignment (SDG 8.9)**: Promotes local cultural discovery, but does *not* claim measured job creation, real visits, or economic impact.
    - **Real-Place Discovery (Phase 2)**: An honest real-place discovery engine powered by a local searchable SQLite catalog of verified settlements and culturally defensible attractions. Unknown venue details are preserved as unknown; itineraries are strictly deferred.
    """)

    st.divider()

    st.subheader("Audited Study Baselines")
    with st.spinner("Verifying read-only source databases..."):
        report = verify_and_audit_study()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Study Cities", f"{report.india_cities_count}", "India (country_code='IN')")
    col2.metric("Catalog Attractions", f"{report.india_attractions_count}", "15 POIs / city")
    col3.metric("Study Trips", f"{report.study_trips_count}", "Non-cancelled")
    col4.metric("Canonical Tables", f"{report.distinct_tables_count}", f"{report.distinct_rows_count:,} rows")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Catalog Cultural Share", f"{report.cultural_attractions_count}/{report.india_attractions_count}", "31.3% of listings")
    col6.metric("Interaction Cultural Share", f"{report.cultural_interactions_count}/{report.matched_interactions_count}", "31.3% of interactions")
    col7.metric("Planned Cultural Share", f"{report.cultural_selected_stops_count}/{report.selected_stops_count}", "30.1% of planned stops")
    col8.metric("Complete Forecast Weeks", f"{report.complete_weeks_count}", f"MAE: {report.forecast_last_week_mae}")


# =====================================================================
# VIEW 2: SYNTHETIC RESEARCH STUDY (45 CITIES)
# =====================================================================
elif view_mode == "Synthetic Research Study (45 Cities)":
    st.title("Synthetic Research Study")
    st.markdown('<span class="badge-synthetic">RESEARCH BENCHMARK — READ-ONLY</span>', unsafe_allow_html=True)
    st.markdown(
        "Explore the canonical catalog of the 45 Indian study cities from the deduplicated SmartTrip and WanderMatch packs."
    )

    cities = get_study_cities()
    city_names = [c["name"] for c in cities]

    # Pre-select Jaipur as canonical reference
    default_idx = city_names.index("Jaipur") if "Jaipur" in city_names else 0
    selected_city_name = st.selectbox("Select a Study City", city_names, index=default_idx)

    selected_city = next(c for c in cities if c["name"] == selected_city_name)

    c1, c2, c3, c4 = st.columns(4)
    c1.text(f"City ID: {selected_city['city_id']}")
    c2.text(f"State: {selected_city['state']}")
    c3.text(f"Timezone: {selected_city['timezone']}")
    c4.text(f"Primary Language: {selected_city['primary_language']}")

    st.subheader(f"Attractions in {selected_city_name} (15 Catalog POIs)")
    attractions = get_city_attractions(selected_city["city_id"])
    df_attractions = pd.DataFrame(attractions)

    display_df = df_attractions[[
        "poi_id", "name", "poi_category", "typical_duration_minutes",
        "entry_cost", "currency", "opens_at", "closes_at", "accessibility", "in_travel_matrix"
    ]].copy()
    display_df.rename(columns={
        "poi_id": "POI ID",
        "name": "Attraction Name",
        "poi_category": "Category",
        "typical_duration_minutes": "Duration (min)",
        "entry_cost": "Entry Fee",
        "currency": "Currency",
        "opens_at": "Opens",
        "closes_at": "Closes",
        "accessibility": "Accessibility",
        "in_travel_matrix": "Matrix Covered (10/15)"
    }, inplace=True)

    st.dataframe(display_df, use_container_width=True)

    matrix_covered_count = sum(1 for a in attractions if a["in_travel_matrix"])
    st.caption(
        f"Planner matrix coverage: **{matrix_covered_count} of 15** attractions have recorded directed legs in `poi_travel_matrix`. "
        "The remaining 5 attractions appear in discovery catalog only."
    )


# =====================================================================
# VIEW 3: REAL-PLACE DISCOVERY (NATIONWIDE / PARTIAL COVERAGE)
# =====================================================================
elif view_mode == "Real-Place Discovery (Nationwide / Partial Coverage)":
    st.title("Real-Place Discovery")

    if not REAL_CATALOG_DB.exists():
        st.error(
            f"Catalog index database not found at `{REAL_CATALOG_DB}`. "
            "Please run: `python -m cultureroute.ingest --output data/real_catalog.db`"
        )
        st.stop()

    catalog = RealCatalogStore(REAL_CATALOG_DB)
    meta = catalog.get_all_metadata()
    coverage_level = meta.get("coverage_level", "Partial Coverage")
    covered_regions = meta.get("covered_regions", "Selected Indian regions")
    snapshot_date = meta.get("snapshot_date", "Unrecorded")
    s_count = meta.get("settlements_count", "0")
    p_count = meta.get("places_count", "0")

    st.markdown(
        f'<span class="badge-real">REAL-WORLD SOURCED DATA</span> '
        f'<span class="badge-discovery">{coverage_level.upper()}</span>',
        unsafe_allow_html=True
    )
    st.caption(
        f"**Catalog Scope**: {coverage_level} — {covered_regions} | "
        f"**Source Snapshot**: {snapshot_date} | "
        f"**Indexed**: {s_count} settlements, {p_count} cultural attractions"
    )

    st.sidebar.markdown(
        f"**Catalog Scope**: {coverage_level}\n\n"
        f"• **Settlements Indexed**: {s_count}\n"
        f"• **Attractions Indexed**: {p_count}\n"
        f"• **Snapshot Date**: {snapshot_date}"
    )

    search_type = st.radio("Search Method", ["Settlement Name", "Map Coordinates (Lat / Lon)"], horizontal=True)


    selected_lat: float | None = None
    selected_lon: float | None = None
    selected_locality_label: str = ""

    if search_type == "Settlement Name":
        query = st.text_input("Enter city, town, or village name (e.g. Badami, Anegundi, Gangavathi, Patan, Aurangabad):", value="Badami")
        if query:
            matches = catalog.search_settlements(query)
            if not matches:
                st.warning(f"No settlements matching '{query}' found in current index.")
                st.info("Tip: Try searching for 'Badami', 'Anegundi', 'Patan', 'Abhaneri', 'Gangavathi', 'Dausa', or 'Aurangabad'.")
            elif len(matches) == 1:
                s = matches[0]
                selected_lat, selected_lon = s.latitude, s.longitude
                dist_str = f", {s.district} Dist." if s.district else ""
                selected_locality_label = f"{s.name} ({s.state}{dist_str}) [{s.settlement_type}]"
                st.success(f"Selected: **{selected_locality_label}** (Lat: {s.latitude:.4f}, Lon: {s.longitude:.4f})")
            else:
                # Disambiguation selection
                st.info(f"Found {len(matches)} matching settlements. Please select one to disambiguate:")
                options = {
                    f"{s.name} — {s.state} (District: {s.district or 'Unrecorded'}, Type: {s.settlement_type}) [ID: {s.settlement_id}]": s
                    for s in matches
                }
                choice = st.selectbox("Matching Settlements", list(options.keys()))
                s = options[choice]
                selected_lat, selected_lon = s.latitude, s.longitude
                dist_str = f", {s.district} Dist." if s.district else ""
                selected_locality_label = f"{s.name} ({s.state}{dist_str})"

    elif search_type == "Map Coordinates (Lat / Lon)":
        c_lat, c_lon = st.columns(2)
        with c_lat:
            in_lat = st.number_input("Latitude (WGS-84)", value=15.9189, min_value=5.0, max_value=38.0, step=0.001, format="%.4f")
        with c_lon:
            in_lon = st.number_input("Longitude (WGS-84)", value=75.6842, min_value=67.0, max_value=98.0, step=0.001, format="%.4f")

        if is_coordinate_in_india_bbox(in_lat, in_lon):
            selected_lat, selected_lon = in_lat, in_lon
            selected_locality_label = f"Pin ({in_lat:.4f}, {in_lon:.4f})"
        else:
            st.error("The specified coordinates are outside the geographic bounding box of India.")

    if selected_lat is not None and selected_lon is not None:
        st.divider()
        st.subheader(f"Nearby Cultural Places around {selected_locality_label}")

        col_filter1, col_filter2 = st.columns([2, 1])
        with col_filter1:
            cat_choice = st.selectbox(
                "Filter by Cultural Category",
                ["All Categories", "Heritage", "Museum", "Religious", "Food Experience"],
                index=0
            )
        with col_filter2:
            radius = st.slider("Search Radius (km proximity)", min_value=5, max_value=60, value=30, step=5)

        category_enum = None
        if cat_choice == "Heritage":
            category_enum = CulturalCategory.HERITAGE
        elif cat_choice == "Museum":
            category_enum = CulturalCategory.MUSEUM
        elif cat_choice == "Religious":
            category_enum = CulturalCategory.RELIGIOUS
        elif cat_choice == "Food Experience":
            category_enum = CulturalCategory.FOOD

        nearby_results = catalog.search_nearby_places(
            lat=selected_lat,
            lon=selected_lon,
            radius_km=float(radius),
            category=category_enum
        )

        if not nearby_results:
            st.warning(f"No cultural attractions found within {radius} km proximity.")
            wider_results = catalog.search_nearby_places(lat=selected_lat, lon=selected_lon, radius_km=float(radius * 2), category=category_enum)
            if wider_results:
                st.info(f"Proximity Notice: Expanding radius to {radius * 2} km reveals {len(wider_results)} attractions nearby (e.g. {wider_results[0][0].name} at {wider_results[0][1]} km).")
        else:
            st.success(f"Discovered **{len(nearby_results)} cultural attractions** within {radius} km (proximity distance):")

            for place, distance in nearby_results:
                with st.container():
                    st.markdown(f"""
                    <div class="place-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <h3 style="margin: 0;">{place.name}</h3>
                            <span style="font-weight: 600; color: #555;">{distance} km proximity</span>
                        </div>
                        <div style="margin: 6px 0;">
                            <b>Category:</b> {place.cultural_category.value.title()} ({place.subcategory or 'landmark'}) | 
                            <b>Location:</b> {place.state}{f", {place.district} Dist." if place.district else ""} | 
                            <b>Source:</b> <a href="{place.source_url}" target="_blank">{place.source_id}</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Detail inspection columns
                    d1, d2, d3, d4 = st.columns(4)
                    with d1:
                        if place.opening_hours.status in (VerificationStatus.KNOWN, VerificationStatus.ALWAYS_OPEN):
                            time_str = f"{place.opening_hours.opens_local_time} - {place.opening_hours.closes_local_time}" if place.opening_hours.opens_local_time else "Always Open"
                            st.markdown(f"**Hours:** <span class='known-tag'>{time_str}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("**Hours:** <span class='unknown-tag'>UNKNOWN</span>", unsafe_allow_html=True)

                    with d2:
                        if place.entry_fee.status == FeeStatus.KNOWN_FREE:
                            st.markdown("**Entry Fee:** <span class='known-tag'>FREE</span>", unsafe_allow_html=True)
                        elif place.entry_fee.status == FeeStatus.KNOWN_TICKETED:
                            fee_str = f"₹{place.entry_fee.amount_domestic}" if place.entry_fee.amount_domestic else "Ticketed"
                            st.markdown(f"**Entry Fee:** <span class='known-tag'>{fee_str}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("**Entry Fee:** <span class='unknown-tag'>UNKNOWN</span>", unsafe_allow_html=True)

                    with d3:
                        if place.accessibility.status == AccessibilityStatus.VERIFIED_STEP_FREE:
                            st.markdown("**Access:** <span class='known-tag'>STEP-FREE</span>", unsafe_allow_html=True)
                        elif place.accessibility.status == AccessibilityStatus.PARTIAL_STEP_FREE:
                            st.markdown("**Access:** <span class='known-tag'>PARTIAL STEP-FREE</span>", unsafe_allow_html=True)
                        elif place.accessibility.status == AccessibilityStatus.NOT_ACCESSIBLE:
                            st.markdown("**Access:** <span class='unknown-tag'>NOT ACCESSIBLE</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("**Access:** <span class='unknown-tag'>UNKNOWN</span>", unsafe_allow_html=True)

                    with d4:
                        st.caption(f"Source Extract: {place.source_extract_date} | Checked: {place.last_checked_date}")

                    st.divider()

    st.markdown("""
    ---
    ### Source Licensing and Attribution
    - **OpenStreetMap Data**: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), licensed under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/).
    - **Wikidata Content**: CC0 1.0 Universal Public Domain Dedication.
    - **Settlement Gazetteers**: UNECE UN/LOCODE (Public Domain) and Census of India administrative listings.
    - **Honesty Guarantee**: Import date does not prove venue operational status. Unknown hours, fees, or accessibility are strictly surfaced as UNKNOWN.
    """)
