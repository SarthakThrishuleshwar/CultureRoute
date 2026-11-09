from pathlib import Path
import re

APP_PY = Path(r"C:\SHARAN PROJECTS\Dev AAT\CultureRoute\app.py")
content = APP_PY.read_text(encoding="utf-8")

# 1. Update tab_legacy_discover
old_legacy_discover_pattern = r'with tab_legacy_discover:.*?st\.write\(f"Legacy database detected with \{len\(cat_store\.get_all_states\(\)\)\} covered states/regions\."\)'

new_legacy_discover = '''with tab_legacy_discover:
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
            )'''

content = re.sub(old_legacy_discover_pattern, new_legacy_discover, content, flags=re.DOTALL)

# 2. Update tab_legacy_planner
old_legacy_planner_pattern = r'with tab_legacy_planner:.*?st\.write\("Legacy catalog detected\. Use synthetic day planner for verified research baseline\."\)'

new_legacy_planner = '''with tab_legacy_planner:
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
        st.info("To generate itineraries and evaluate dual-objective Plan A vs Plan B trade-offs, please switch to Tab 1 ('Synthetic Day Planner (45 Study Cities)') above.")'''

content = re.sub(old_legacy_planner_pattern, new_legacy_planner, content, flags=re.DOTALL)

APP_PY.write_text(content, encoding="utf-8")
print("Successfully populated legacy tabs!")
