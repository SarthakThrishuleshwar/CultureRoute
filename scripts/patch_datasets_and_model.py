from pathlib import Path

# 1. Update datasets_view.py
ds_path = Path("cultureroute/datasets_view.py")
ds_text = ds_path.read_text(encoding="utf-8")

old_ds_origin = """    origin_choice = st.radio(
        "Filter by Origin Pack",
        ["All (24)", "SmartTrip-only (10)", "WanderMatch-only (6)", "Shared (8)"],
        horizontal=True,
        key="f2_origin_choice",
    )"""

new_ds_origin = """    origin_choice = st.pills(
        "Filter by Origin Pack",
        ["All (24)", "SmartTrip-only (10)", "WanderMatch-only (6)", "Shared (8)"],
        default="All (24)",
        key="f2_origin_choice",
    ) or "All (24)"

    st.markdown("**Quick Table Picks:**")
    top_tbl_picks = ["trips", "activities_poi", "user_interactions", "events_festivals", "itineraries", "poi_travel_matrix"]
    picked_top_tbl = st.pills("Quick Table Picks", top_tbl_picks, key="pills_datasets_quick_tbl", label_visibility="collapsed")
    if picked_top_tbl and picked_top_tbl != st.session_state.get("f2_tbl_select_val"):
        st.session_state["f2_tbl_select_val"] = picked_top_tbl
        st.query_params["table"] = picked_top_tbl
        st.rerun()"""

if old_ds_origin in ds_text:
    ds_text = ds_text.replace(old_ds_origin, new_ds_origin)
    ds_path.write_text(ds_text, encoding="utf-8")
    print("datasets_view.py successfully upgraded with pills!")
else:
    print("Warning: old_ds_origin not found in datasets_view.py")


# 2. Update model_view.py
mv_path = Path("cultureroute/model_view.py")
mv_text = mv_path.read_text(encoding="utf-8")

old_mv_city = """            city_names = [cp["city_name"] for cp in pred_cities]
            def_city = st.session_state.get("default_city", "Jaipur")
            sel_idx = city_names.index(def_city) if def_city in city_names else 0
            selected_city = st.selectbox("Select Study City", city_names, index=sel_idx, key="p6_city_inspect_select")"""

new_mv_city = """            city_names = [cp["city_name"] for cp in pred_cities]
            def_city = st.session_state.get("default_city", "Jaipur")

            st.markdown("**Quick City Hubs:**")
            quick_pred_cities = ["Jaipur", "Delhi", "Mumbai", "Varanasi", "Kochi", "Agra", "Bengaluru"]
            picked_pred_city = st.pills("Quick City Hubs", quick_pred_cities, key="pills_model_quick_city", label_visibility="collapsed")
            if picked_pred_city and picked_pred_city != st.session_state.get("p6_city_inspect_select"):
                st.session_state["p6_city_inspect_select"] = picked_pred_city
                st.rerun()

            cur_p6_city = st.session_state.get("p6_city_inspect_select", def_city)
            sel_idx = city_names.index(cur_p6_city) if cur_p6_city in city_names else 0
            selected_city = st.selectbox("Select Study City", city_names, index=sel_idx, key="p6_city_inspect_select")"""

if old_mv_city in mv_text:
    mv_text = mv_text.replace(old_mv_city, new_mv_city)
    mv_path.write_text(mv_text, encoding="utf-8")
    print("model_view.py successfully upgraded with pills!")
else:
    print("Warning: old_mv_city not found in model_view.py")
