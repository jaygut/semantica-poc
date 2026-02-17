"""Portfolio Overview tab for Nereus v4 Intelligence Platform.

NEW in v4: provides a summary grid of all dynamically discovered sites,
aggregate portfolio statistics, color-coded table with habitat pills
and tier badges, and a composition chart.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from investor_demo.components.v4.shared import (  # noqa: E402
    COLORS,
    esv_quality_ratio,
    fmt_usd,
    get_all_sites,
    get_site_data,
    habitat_pill,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aggregate statistics
# ---------------------------------------------------------------------------


def _compute_aggregates(
    sites: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute portfolio-level aggregate statistics."""
    total_esv = sum(s.get("total_esv", 0) for s in sites)
    total_area = sum(s.get("area_km2", 0) for s in sites)
    n_countries = len({s.get("country", "") for s in sites} - {""})
    n_gold = sum(1 for s in sites if s.get("tier") == "Gold")
    n_silver = sum(1 for s in sites if s.get("tier") == "Silver")
    n_bronze = sum(1 for s in sites if s.get("tier") == "Bronze")

    # Habitat distribution
    habitat_counts: dict[str, int] = {}
    for s in sites:
        h = s.get("primary_habitat", "unknown")
        habitat_counts[h] = habitat_counts.get(h, 0) + 1

    # Rating distribution
    rating_counts: dict[str, int] = {}
    for s in sites:
        r = s.get("asset_rating", "")
        if r:
            rating_counts[r] = rating_counts.get(r, 0) + 1

    return {
        "total_esv": total_esv,
        "total_area": total_area,
        "n_sites": len(sites),
        "n_countries": n_countries,
        "n_gold": n_gold,
        "n_silver": n_silver,
        "n_bronze": n_bronze,
        "habitat_counts": habitat_counts,
        "rating_counts": rating_counts,
    }


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _render_kpi_strip(agg: dict[str, Any]) -> None:
    """Render top-level portfolio KPIs."""
    cols = st.columns(5)
    kpis = [
        ("Portfolio ESV", fmt_usd(agg["total_esv"]) + "/yr", "Annual market-price total"),
        ("Sites", str(agg["n_sites"]), "Dynamically discovered"),
        ("Countries", str(agg["n_countries"]), "Unique jurisdictions"),
        (
            "Protected Area",
            f"{agg['total_area']:,.0f} km2",
            "Total area under management",
        ),
        (
            "Data Quality",
            f"{agg['n_gold']}G / {agg['n_silver']}S / {agg['n_bronze']}B",
            "Gold / Silver / Bronze tiers",
        ),
    ]
    for i, (label, value, context) in enumerate(kpis):
        with cols[i]:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">{label}</div>
<div class="kpi-value" style="font-size:36px">{value}</div>
<div class="kpi-context">{context}</div>
</div>
""",
                unsafe_allow_html=True,
            )


def _esv_quality_badge(site_name: str) -> str:
    """Return an HTML badge showing the market-price ESV share for a site."""
    data = get_site_data(site_name)
    if not data:
        return ""
    services = data.get("ecosystem_services", {}).get("services", [])
    ratios = esv_quality_ratio(services)
    mp_pct = ratios.get("market_price", 0)
    if mp_pct >= 0.7:
        color = "#00C853"
        label = f"{mp_pct:.0%} MP"
    elif mp_pct >= 0.4:
        color = "#FFD600"
        label = f"{mp_pct:.0%} MP"
    else:
        color = "#FF6D00"
        label = f"{mp_pct:.0%} MP"
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="display:inline-block;padding:2px 6px;border-radius:4px;'
        f"font-size:11px;font-weight:600;color:{color};"
        f"background:rgba({r},{g},{b},0.15);"
        f'border:1px solid rgba({r},{g},{b},0.3)">{label}</span>'
    )


def _render_site_table(sites: list[dict[str, Any]]) -> None:
    """Render the full portfolio table with habitat pills and tier badges."""
    header = (
        "<tr>"
        "<th>Site</th>"
        "<th>Country</th>"
        "<th>Habitat</th>"
        "<th>ESV</th>"
        "<th>Quality</th>"
        "<th>Rating</th>"
        "<th>NEOLI</th>"
        "<th>Tier</th>"
        "</tr>"
    )

    rows = ""
    for s in sites:
        # Tier badge
        tier = s.get("tier", "Bronze")
        tier_cls = f"tier-{tier.lower()}"

        # Habitat pill
        h_pill = habitat_pill(s.get("primary_habitat", ""))

        # ESV
        esv = s.get("total_esv", 0)
        esv_str = fmt_usd(esv) if esv else "N/A"

        # Data quality badge
        quality = _esv_quality_badge(s.get("name", ""))

        # Rating
        rating = s.get("asset_rating", "-")

        # NEOLI dots
        neoli = s.get("neoli_score", 0)
        dots = ""
        for j in range(5):
            if j < neoli:
                dots += (
                    '<span style="display:inline-block;width:10px;height:10px;'
                    'border-radius:50%;background:#66BB6A;margin-right:3px"></span>'
                )
            else:
                dots += (
                    '<span style="display:inline-block;width:10px;height:10px;'
                    'border-radius:50%;background:#1E293B;border:1px solid #334155;'
                    'margin-right:3px"></span>'
                )

        rows += (
            f"<tr>"
            f"<td style='font-weight:600;color:#E2E8F0'>{s.get('name', '')}</td>"
            f"<td>{s.get('country', '')}</td>"
            f"<td>{h_pill}</td>"
            f"<td style='font-weight:600'>{esv_str}</td>"
            f"<td>{quality}</td>"
            f"<td style='font-weight:600'>{rating}</td>"
            f"<td>{dots}</td>"
            f"<td><span class='{tier_cls}'>{tier}</span></td>"
            f"</tr>"
        )

    st.markdown(
        f"""
<table class="portfolio-table">
<thead>{header}</thead>
<tbody>{rows}</tbody>
</table>
""",
        unsafe_allow_html=True,
    )


def _render_composition_chart(
    sites: list[dict[str, Any]],
    agg: dict[str, Any],
) -> None:
    """Render a horizontal bar chart showing ESV composition by site."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.caption("Plotly not available for composition chart.")
        return

    sorted_sites = sorted(sites, key=lambda s: s.get("total_esv", 0))
    names = [s.get("name", "Unknown") for s in sorted_sites]
    values = [s.get("total_esv", 0) for s in sorted_sites]

    from investor_demo.components.v4.shared import _HABITAT_COLORS

    bar_colors = [
        _HABITAT_COLORS.get(s.get("primary_habitat", ""), "#5B9BD5")
        for s in sorted_sites
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=values,
            orientation="h",
            marker_color=bar_colors,
            text=[fmt_usd(v) for v in values],
            textposition="auto",
            textfont=dict(color="#E2E8F0", size=13),
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(300, len(sites) * 42),
        xaxis=dict(
            title="Annual ESV (USD)",
            gridcolor="#1E293B",
            zeroline=False,
            tickformat="$,.0s",
            color="#94A3B8",
        ),
        yaxis=dict(
            gridcolor="#1E293B",
            color="#CBD5E1",
            tickfont=dict(size=13),
        ),
        title=dict(
            text="ESV by Site",
            font=dict(size=15, color="#94A3B8"),
            x=0.5,
        ),
    )
    st.plotly_chart(fig, key="v4_portfolio_esv_bar")


def _render_habitat_breakdown(agg: dict[str, Any]) -> None:
    """Render habitat type distribution as a small donut chart."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    from investor_demo.components.v4.shared import (
        _HABITAT_COLORS,
        _HABITAT_DISPLAY,
    )

    counts = agg.get("habitat_counts", {})
    if not counts:
        return

    labels = [_HABITAT_DISPLAY.get(k, k.replace("_", " ").title()) for k in counts]
    values = list(counts.values())
    colors = [_HABITAT_COLORS.get(k, "#5B9BD5") for k in counts]

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0B1120", width=2)),
            textinfo="label+value",
            textfont=dict(size=13, color="#E2E8F0"),
            hovertemplate="%{label}: %{value} sites<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        showlegend=False,
        title=dict(
            text="Habitat Distribution",
            font=dict(size=15, color="#94A3B8"),
            x=0.5,
        ),
    )
    st.plotly_chart(fig, key="v4_portfolio_habitat_donut")


def _render_rating_summary(agg: dict[str, Any]) -> None:
    """Render asset rating distribution as a summary."""
    rating_counts = agg.get("rating_counts", {})
    if not rating_counts:
        st.caption("No asset ratings available yet.")
        return

    _RATING_COLORS: dict[str, str] = {
        "AAA": COLORS["success"],
        "AA": "#81C784",
        "A": "#AED581",
        "BBB": COLORS["warning"],
        "BB": "#FFB74D",
        "B": "#FF8A65",
    }

    rows_html = ""
    for rating in ["AAA", "AA", "A", "BBB", "BB", "B"]:
        count = rating_counts.get(rating, 0)
        if count == 0:
            continue
        color = _RATING_COLORS.get(rating, COLORS["text_body"])
        bar_width = min(100, count * 20)
        rows_html += (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">'
            f'<span style="font-weight:700;color:{color};width:40px;font-size:18px">{rating}</span>'
            f'<div style="flex:1;height:8px;border-radius:4px;background:#1E293B;overflow:hidden">'
            f'<div style="width:{bar_width}%;height:100%;border-radius:4px;background:{color}"></div>'
            f"</div>"
            f'<span style="color:#94A3B8;font-size:15px;width:30px;text-align:right">{count}</span>'
            f"</div>"
        )

    st.markdown(
        f"""
<div class="kpi-card" style="padding:24px 28px">
<div class="kpi-label">Asset Rating Distribution</div>
<div style="margin-top:16px">{rows_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_portfolio_overview(**kwargs: Any) -> None:
    """Render the Portfolio Overview tab.

    Displays aggregate statistics, a sortable site table, ESV composition
    chart, habitat donut, and asset rating distribution. All data is
    dynamically discovered from ``examples/*_case_study.json``.
    """
    st.markdown(
        '<div class="section-header" style="margin-top:0">'
        "Portfolio Overview</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Aggregate view across all sites in the '
        "Nereus portfolio. Sites are discovered dynamically from case study "
        "data - no hardcoded site lists.</div>",
        unsafe_allow_html=True,
    )

    sites = get_all_sites()
    if not sites:
        st.warning(
            "No case study files found in examples/. "
            "Add *_case_study.json files to populate the portfolio."
        )
        return

    agg = _compute_aggregates(sites)

    # ---- 1. KPI Strip ----
    _render_kpi_strip(agg)

    # ---- 2. Site Table ----
    st.markdown(
        '<div class="section-header">Site Portfolio</div>',
        unsafe_allow_html=True,
    )
    _render_site_table(sites)

    # ---- 3. Charts side by side ----
    st.markdown(
        '<div class="section-header">Portfolio Composition</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2])
    with col_left:
        _render_composition_chart(sites, agg)
    with col_right:
        _render_habitat_breakdown(agg)

    # ---- 4. Rating Summary ----
    _render_rating_summary(agg)
