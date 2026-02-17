
import plotly.graph_objects as go
import streamlit as st
from typing import Any

from investor_demo.components.v4.shared import (
    fmt_usd,
    COLORS,
    _HABITAT_DISPLAY,
)

def render_comparison_tool(all_sites: list[dict[str, Any]]) -> None:
    """Render the multi-site comparison tool."""
    
    st.markdown(
        """
        <div class="masthead">
            <div class="masthead-brand">NEREUS | COMPARATIVE ANALYTICS</div>
            <h1 style="font-size: 42px; font-weight: 300; margin-top: 10px; margin-bottom: 5px;">Portfolio Benchmarking</h1>
            <div class="masthead-subtitle">Side-by-side performance comparison across all portfolio dimensions</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Site selector
    site_names = [s["name"] for s in all_sites]
    default_sites = site_names[:3] if len(site_names) >= 3 else site_names
    
    selected_names = st.multiselect(
        "Select Sites to Compare",
        options=site_names,
        default=default_sites,
        max_selections=4
    )

    if not selected_names:
        st.info("Please select at least one site to view comparisons.")
        return

    # Filter data
    selected_sites = [s for s in all_sites if s["name"] in selected_names]

    # --- Metrics Table ---
    st.markdown("#### Key Metrics Overview")
    
    cols = st.columns(len(selected_sites))
    
    # Define metrics to show
    metrics = [
        ("Region", "region"),
        ("Habitat", "primary_habitat"),
        ("Rating", "asset_rating"),
        ("NEOLI Score", "neoli_score"),
        ("Total ESV", "total_esv"),
        ("Area (km²)", "area_km2"),
    ]

    for idx, site in enumerate(selected_sites):
        with cols[idx]:
            st.markdown(f"**{site['name']}**")
            st.caption(f"{site.get('country', 'Unknown')}")
            
            for label, key in metrics:
                val = site.get(key, "N/A")
                if key == "total_esv":
                    val = fmt_usd(float(val))
                elif key == "primary_habitat":
                    val = _HABITAT_DISPLAY.get(val, val)
                
                st.markdown(f"<small style='color:#94A3B8'>{label}</small><br/>"
                            f"<span style='font-size:16px;color:#E2E8F0'>{val}</span>", 
                            unsafe_allow_html=True)
                st.markdown("---")


    # --- Analysis Charts ---
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Multi-Dimensional Score")
        # Radar Chart
        # Note: We need normalized scores (0-1 or 0-100). 
        # For this demo, let's normalize NEOLI (0-5) to 0-100, composite (0-1) to 0-100.
        categories = ['NEOLI', 'Composite Rating', 'Data Richness (Tier)', 'ESV Density']
        
        fig = go.Figure()

        for site in selected_sites:
            # Normalize logic
            neoli_norm = (site.get("neoli_score", 0) / 5.0) * 100
            comp_norm = (site.get("composite_score", 0.0)) * 100
            
            # Simple tier quant
            tier_map = {"Gold": 100, "Silver": 70, "Bronze": 40}
            tier_score = tier_map.get(site.get("tier", "Bronze"), 40)
            
            # ESV Density (simplified normalization relative to group max)
            area = site.get("area_km2", 1) or 1
            esv_density = site.get("total_esv", 0) / area
            max_density = max((s.get("total_esv", 0) / (s.get("area_km2", 1) or 1)) for s in selected_sites) if selected_sites else 1
            density_norm = (esv_density / max_density) * 100 if max_density > 0 else 0

            fig.add_trace(go.Scatterpolar(
                r=[neoli_norm, comp_norm, tier_score, density_norm],
                theta=categories,
                fill='toself',
                name=site["name"]
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100]),
                bgcolor='#162039'
            ),
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#B0BEC5'),
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### Total Ecosystem Value (USD)")
        # Bar chart of ESV
        
        fig_bar = go.Figure()
        
        sites_sorted = sorted(selected_sites, key=lambda x: x.get("total_esv", 0), reverse=True)
        
        fig_bar.add_trace(go.Bar(
            x=[s["name"] for s in sites_sorted],
            y=[s.get("total_esv", 0) for s in sites_sorted],
            marker_color=COLORS["accent_blue"],
            text=[fmt_usd(s.get("total_esv", 0)) for s in sites_sorted],
            textposition='auto',
        ))
        
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#B0BEC5'),
            yaxis=dict(showgrid=True, gridcolor='#243352'),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

