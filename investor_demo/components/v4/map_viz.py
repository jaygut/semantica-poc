
import pydeck as pdk
import streamlit as st
from typing import Any

def render_global_map(sites: list[dict[str, Any]]) -> None:
    """Render a 3D globe visualization of the portfolio sites using Pydeck."""
    if not sites:
        st.warning("No site data available for map visualization.")
        return

    # Filter out sites without coordinates
    valid_sites = [
        s for s in sites 
        if s.get("latitude") is not None and s.get("longitude") is not None
    ]

    if not valid_sites:
        st.warning("No sites with valid coordinates found.")
        return

    # Normalize ESV for height scaling
    max_esv = max(s.get("total_esv", 0) for s in valid_sites) if valid_sites else 1
    
    # Prepare data for Pydeck
    map_data = []
    for s in valid_sites:
        esv = s.get("total_esv", 0)
        # Height scaling factor (e.g., 100km max height)
        height = (esv / max_esv) * 500000 if max_esv > 0 else 10000
        
        map_data.append({
            "name": s["name"],
            "lat": s["latitude"],
            "lon": s["longitude"],
            "esv": esv,
            "neoli": s.get("neoli_score", 0),
            "height": height,
            "color": [255, 167, 38], # Orange-ish for default
            "tooltip_esv": f"${esv:,.0f}"
        })

    # Define layers
    
    # 1. 3D Columns for ESV
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=map_data,
        get_position=["lon", "lat"],
        get_elevation="height",
        elevation_scale=1,
        radius=30000, # 30km radius columns
        get_fill_color=[91, 155, 213, 200], # Blue transparent
        pickable=True,
        auto_highlight=True,
    )

    # 2. Scatterplot for base markers (circles)
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position=["lon", "lat"],
        get_fill_color=[16, 185, 129], # Green
        get_radius=40000,
        pickable=True,
        opacity=0.5,
    )

    # 3. Text Labels
    text_layer = pdk.Layer(
        "TextLayer",
        data=map_data,
        get_position=["lon", "lat"],
        get_text="name",
        get_color=[226, 232, 240], # Light grey
        get_size=16,
        get_alignment_baseline="'bottom'",
        get_text_anchor="'middle'",
        get_pixel_offset=[0, -20]
    )

    # Define view state (Global view)
    view_state = pdk.ViewState(
        latitude=20.0,
        longitude=0.0,
        zoom=1,
        pitch=45,
        bearing=0
    )

    # Render deck
    r = pdk.Deck(
        layers=[column_layer, scatter_layer, text_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{name}</b><br/>ESV: {tooltip_esv}<br/>NEOLI: {neoli}",
            "style": {"backgroundColor": "#1E293B", "color": "#E2E8F0"}
        },
        map_style=pdk.map_styles.CARTO_DARK,
    )
    
    # Use standard Streamlit Pydeck chart, but since map_style might fail without token, 
    # we rely on Streamlit's default dark map if possible or explicit None.
    # Actually, "None" often triggers a default light map. 
    # "dark" is a safe alias in some versions, but let's try to not set it to force default.
    
    st.pydeck_chart(r, use_container_width=True)
