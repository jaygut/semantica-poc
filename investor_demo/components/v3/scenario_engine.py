"""Scenario Lab - interactive what-if analysis for MARIS v3 Intelligence Platform.

Provides parameter sliders (carbon price, habitat loss, tourism growth,
fisheries change) that drive Monte Carlo recalculation and sensitivity
tornado charts. All computations use the pure-Python engines in
``maris.axioms`` so no external services are needed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from copy import deepcopy
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from investor_demo.components.v3.shared import COLORS, fmt_usd
from maris.axioms.monte_carlo import run_monte_carlo
from maris.axioms.sensitivity import run_sensitivity_analysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_CARBON_PRICE = 30  # USD per tonne (Verra VCS VM0033)

# Canonical service name mapping - normalises names across bundle and case study
_SERVICE_NAME_MAP: dict[str, str] = {
    "tourism": "Tourism",
    "tourism_usd": "Tourism",
    "fisheries": "Fisheries",
    "fisheries_usd": "Fisheries",
    "fisheries_spillover": "Fisheries",
    "carbon": "Carbon",
    "carbon_usd": "Carbon",
    "carbon_sequestration": "Carbon",
    "coastal_protection": "Coastal Protection",
    "coastal_protection_usd": "Coastal Protection",
}

# Default confidence intervals by canonical name (per site)
_DEFAULT_CI: dict[str, dict[str, tuple[float, float]]] = {
    "Cabo Pulmo National Park": {
        "Tourism": (20_000_000, 30_000_000),
        "Fisheries": (2_100_000, 4_300_000),
        "Coastal Protection": (600_000, 1_200_000),
        "Carbon": (100_000, 300_000),
    },
    "Shark Bay World Heritage Area": {
        "Carbon": (8_500_000, 15_700_000),
        "Fisheries": (3_600_000, 6_800_000),
        "Tourism": (2_400_000, 4_400_000),
        "Coastal Protection": (500_000, 1_100_000),
    },
}

# Axiom metadata for the impact panel
_AXIOM_CHAIN: list[dict[str, Any]] = [
    {
        "id": "BA-013",
        "name": "Seagrass carbon sequestration rate",
        "coefficient": "0.84 tCO2/ha/yr",
        "affected_by": ["habitat_loss"],
    },
    {
        "id": "BA-014",
        "name": "Carbon stock to credit value",
        "coefficient": "$30/tonne",
        "coefficient_val": 30,
        "affected_by": ["carbon_price"],
    },
    {
        "id": "BA-015",
        "name": "Habitat loss carbon emission",
        "coefficient": "294 tCO2/ha released",
        "affected_by": ["habitat_loss"],
    },
]


# ---------------------------------------------------------------------------
# Service extraction
# ---------------------------------------------------------------------------


def _extract_services(data: dict[str, Any], site: str) -> list[dict[str, Any]]:
    """Parse ecosystem services from either bundle or case-study format.

    Returns a list of dicts with keys:
        service_name, value, ci_low, ci_high
    """
    services: list[dict[str, Any]] = []

    # --- Bundle format (Cabo Pulmo static bundle) ---
    breakdown = (
        data.get("financial_output", {}).get("services_breakdown", {})
    )
    if breakdown:
        for key, val in breakdown.items():
            canonical = _SERVICE_NAME_MAP.get(key, key.replace("_usd", "").title())
            ci = _DEFAULT_CI.get(site, {}).get(canonical, (val * 0.7, val * 1.3))
            services.append({
                "service_name": canonical,
                "value": float(val),
                "ci_low": float(ci[0]),
                "ci_high": float(ci[1]),
            })
        return services

    # --- Case study format (services array) ---
    svc_list = data.get("ecosystem_services", {}).get("services", [])
    for svc in svc_list:
        raw_name = svc.get("service_type", "unknown")
        canonical = _SERVICE_NAME_MAP.get(raw_name, raw_name.replace("_", " ").title())
        val = float(svc.get("annual_value_usd", 0))
        ci = _DEFAULT_CI.get(site, {}).get(canonical, (val * 0.7, val * 1.3))
        services.append({
            "service_name": canonical,
            "value": val,
            "ci_low": float(ci[0]),
            "ci_high": float(ci[1]),
        })

    return services


# ---------------------------------------------------------------------------
# Scenario adjustment logic
# ---------------------------------------------------------------------------


def apply_scenario_adjustments(
    base_services: list[dict[str, Any]],
    adjustments: dict[str, float],
) -> list[dict[str, Any]]:
    """Apply parameter changes to service values.

    Parameters
    ----------
    base_services
        List of service dicts with keys: service_name, value, ci_low, ci_high.
    adjustments
        Dict with keys:
        - carbon_price: new price per tonne (scales carbon proportionally to BA-014)
        - habitat_loss_pct: 0-50, reduces ALL services by this percentage
        - tourism_growth_pct: -20 to +30, scales tourism service
        - fisheries_change_pct: -30 to +20, scales fisheries service

    Returns
    -------
    list[dict]
        Modified service list (deep copy - originals are not mutated).
    """
    modified = deepcopy(base_services)
    carbon_price = adjustments.get("carbon_price", _BASE_CARBON_PRICE)
    habitat_loss = adjustments.get("habitat_loss_pct", 0) / 100.0
    tourism_growth = adjustments.get("tourism_growth_pct", 0) / 100.0
    fisheries_change = adjustments.get("fisheries_change_pct", 0) / 100.0

    carbon_scale = carbon_price / _BASE_CARBON_PRICE

    for svc in modified:
        name = svc["service_name"]

        # Per-service scaling
        if name == "Carbon":
            svc["value"] *= carbon_scale
            svc["ci_low"] *= carbon_scale
            svc["ci_high"] *= carbon_scale
        elif name == "Tourism":
            factor = 1.0 + tourism_growth
            svc["value"] *= factor
            svc["ci_low"] *= factor
            svc["ci_high"] *= factor
        elif name == "Fisheries":
            factor = 1.0 + fisheries_change
            svc["value"] *= factor
            svc["ci_low"] *= factor
            svc["ci_high"] *= factor

        # Habitat loss applies to ALL services (multiplicative)
        if habitat_loss > 0:
            reduction = 1.0 - habitat_loss
            svc["value"] *= reduction
            svc["ci_low"] *= reduction
            svc["ci_high"] *= reduction

    return modified


# ---------------------------------------------------------------------------
# Cached Monte Carlo runner
# ---------------------------------------------------------------------------


def _cache_key(services: list[dict[str, Any]], n: int) -> str:
    """Deterministic hash for a given service configuration."""
    payload = json.dumps(
        [
            {
                "n": s["service_name"],
                "v": round(s["value"], 2),
                "l": round(s["ci_low"], 2),
                "h": round(s["ci_high"], 2),
            }
            for s in services
        ],
        sort_keys=True,
    )
    return hashlib.md5(f"{payload}:{n}".encode()).hexdigest()  # noqa: S324


def _run_mc_cached(
    services: list[dict[str, Any]],
    n_simulations: int = 10_000,
) -> dict[str, Any]:
    """Run Monte Carlo with session-state caching to avoid re-running on every render."""
    key = _cache_key(services, n_simulations)
    cache_store = "scenario_mc_cache"
    if cache_store not in st.session_state:
        st.session_state[cache_store] = {}
    cache: dict[str, Any] = st.session_state[cache_store]
    if key in cache:
        return cache[key]
    result = run_monte_carlo(services, n_simulations=n_simulations)
    cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Plotly charts
# ---------------------------------------------------------------------------


def _build_histogram(
    base_mc: dict[str, Any],
    scenario_mc: dict[str, Any],
) -> go.Figure:
    """Build overlapping Monte Carlo histogram (base in grey, scenario in blue)."""
    fig = go.Figure()

    # Base distribution (grey overlay)
    fig.add_trace(
        go.Histogram(
            x=base_mc["simulations"],
            nbinsx=60,
            marker_color="rgba(148, 163, 184, 0.35)",
            marker_line_color="rgba(148, 163, 184, 0.5)",
            marker_line_width=0.5,
            name=f"Base (median {fmt_usd(base_mc['median'])})",
            opacity=0.6,
        )
    )

    # Scenario distribution (accent blue)
    fig.add_trace(
        go.Histogram(
            x=scenario_mc["simulations"],
            nbinsx=60,
            marker_color=COLORS["accent_blue"],
            marker_line_color="rgba(91, 155, 213, 0.7)",
            marker_line_width=0.5,
            name=f"Scenario (median {fmt_usd(scenario_mc['median'])})",
            opacity=0.7,
        )
    )

    # Vertical reference lines
    fig.add_vline(
        x=scenario_mc["p5"],
        line_dash="dash",
        line_color=COLORS["danger"],
        annotation_text=f"P5 {fmt_usd(scenario_mc['p5'])}",
        annotation_font_color=COLORS["danger"],
        annotation_font_size=12,
    )
    fig.add_vline(
        x=scenario_mc["median"],
        line_color="#FFFFFF",
        annotation_text=f"Median {fmt_usd(scenario_mc['median'])}",
        annotation_font_color="#FFFFFF",
        annotation_font_size=12,
    )
    fig.add_vline(
        x=scenario_mc["p95"],
        line_dash="dash",
        line_color=COLORS["success"],
        annotation_text=f"P95 {fmt_usd(scenario_mc['p95'])}",
        annotation_font_color=COLORS["success"],
        annotation_font_size=12,
    )

    fig.update_layout(
        title=dict(
            text="ESV Distribution - 10,000 Simulations",
            font=dict(size=15, color=COLORS["text_heading"]),
        ),
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_body"]),
        xaxis=dict(
            title="Total ESV (USD)",
            gridcolor="#1E293B",
            tickformat="$,.0f",
            zeroline=False,
        ),
        yaxis=dict(title="Frequency", gridcolor="#1E293B", zeroline=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=13),
        ),
        margin=dict(l=60, r=20, t=60, b=50),
        height=380,
    )
    return fig


def _build_tornado(sensitivity: dict[str, Any]) -> go.Figure:
    """Build horizontal tornado bar chart from sensitivity analysis results."""
    tornado_data = sensitivity.get("tornado_plot_data", [])
    if not tornado_data:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="No sensitivity data available",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color=COLORS["text_muted"]),
                )
            ],
        )
        return fig

    # Sort ascending by impact so largest bar is at top (Plotly draws bottom-up)
    tornado_data = sorted(tornado_data, key=lambda d: d["sensitivity_rank"])
    tornado_data.reverse()

    base_esv = tornado_data[0]["base_esv"]
    names = [d["parameter_name"] for d in tornado_data]
    low_deltas = [d["low_esv"] - base_esv for d in tornado_data]
    high_deltas = [d["high_esv"] - base_esv for d in tornado_data]

    fig = go.Figure()

    # Low side (red, extends left)
    fig.add_trace(
        go.Bar(
            y=names,
            x=low_deltas,
            orientation="h",
            marker_color=COLORS["danger"],
            name="Low (-20%)",
            opacity=0.85,
        )
    )

    # High side (green, extends right)
    fig.add_trace(
        go.Bar(
            y=names,
            x=high_deltas,
            orientation="h",
            marker_color=COLORS["success"],
            name="High (+20%)",
            opacity=0.85,
        )
    )

    fig.update_layout(
        title=dict(
            text="Sensitivity Tornado - OAT Analysis",
            font=dict(size=15, color=COLORS["text_heading"]),
        ),
        barmode="relative",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_body"]),
        xaxis=dict(
            title="ESV Change from Baseline (USD)",
            gridcolor="#1E293B",
            tickformat="$,.0f",
            zeroline=True,
            zerolinecolor="#64748B",
            zerolinewidth=1,
        ),
        yaxis=dict(gridcolor="#1E293B"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=13),
        ),
        margin=dict(l=150, r=20, t=60, b=50),
        height=max(280, 80 * len(names)),
    )
    return fig


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _esv_impact_card(
    base_esv: float,
    scenario_esv: float,
) -> str:
    """Return HTML for the ESV impact KPI card."""
    delta = scenario_esv - base_esv
    delta_pct = (delta / base_esv * 100) if base_esv else 0.0
    if delta > 0:
        arrow = "&#9650;"  # up triangle
        color = COLORS["success"]
    elif delta < 0:
        arrow = "&#9660;"  # down triangle
        color = COLORS["danger"]
    else:
        arrow = "&#9654;"  # right triangle
        color = COLORS["text_muted"]

    sign = "+" if delta >= 0 else ""
    return f"""
    <div class="kpi-card" style="min-height:220px">
        <div class="kpi-label">Scenario ESV Impact</div>
        <div style="display:flex;gap:24px;align-items:flex-end;margin-bottom:14px">
            <div>
                <div style="font-size:13px;color:{COLORS['text_muted']};
                     text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">
                    Base
                </div>
                <div style="font-size:28px;font-weight:700;color:{COLORS['text_heading']}">
                    {fmt_usd(base_esv)}
                </div>
            </div>
            <div style="font-size:24px;color:{COLORS['text_muted']};padding-bottom:4px">
                &rarr;
            </div>
            <div>
                <div style="font-size:13px;color:{COLORS['text_muted']};
                     text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">
                    Scenario
                </div>
                <div style="font-size:28px;font-weight:700;color:{COLORS['text_heading']}">
                    {fmt_usd(scenario_esv)}
                </div>
            </div>
        </div>
        <div style="font-size:22px;font-weight:600;color:{color}">
            <span>{arrow}</span>
            {sign}{fmt_usd(abs(delta))} ({sign}{delta_pct:.1f}%)
        </div>
    </div>
    """


def _axiom_chain_html(adjustments: dict[str, float]) -> str:
    """Render axiom chain impact panel showing affected bridge axioms."""
    carbon_price = adjustments.get("carbon_price", _BASE_CARBON_PRICE)
    habitat_loss_pct = adjustments.get("habitat_loss_pct", 0)

    rows = ""
    for ax in _AXIOM_CHAIN:
        # Determine if this axiom is affected by the current scenario
        affected = False
        impact_parts: list[str] = []

        if "carbon_price" in ax["affected_by"] and carbon_price != _BASE_CARBON_PRICE:
            affected = True
            base_val = ax.get("coefficient_val", _BASE_CARBON_PRICE)
            css = "positive" if carbon_price > base_val else "negative"
            impact_parts.append(
                f'<span class="parameter-impact {css}">'
                f"${base_val} &rarr; ${carbon_price}/tonne</span>"
            )

        if "habitat_loss" in ax["affected_by"] and habitat_loss_pct > 0:
            affected = True
            impact_parts.append(
                f'<span class="parameter-impact negative">'
                f"-{habitat_loss_pct}% habitat loss applied</span>"
            )

        if not affected:
            impact_html = (
                '<span class="parameter-impact neutral">No change</span>'
            )
        else:
            impact_html = " ".join(impact_parts)

        border_color = COLORS["accent_blue"] if affected else COLORS["border_subtle"]
        rows += f"""
        <div style="background:linear-gradient(145deg,#162039 0%,#1A2744 100%);
             border-radius:8px;padding:16px 20px;border:1px solid {border_color};
             margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;
                 flex-wrap:wrap;gap:8px">
                <div>
                    <span style="font-weight:600;color:{COLORS['accent_blue']};
                          font-size:15px;margin-right:8px">{ax['id']}</span>
                    <span style="color:{COLORS['text_body']};font-size:15px">
                        {ax['name']}</span>
                </div>
                <div style="font-size:14px;color:{COLORS['text_secondary']}">
                    Base: {ax['coefficient']}
                </div>
            </div>
            <div style="margin-top:8px">{impact_html}</div>
        </div>
        """

    return rows


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render_scenario_engine(
    data: dict[str, Any],
    site: str,
    mode: str,
    **kwargs: Any,
) -> None:
    """Render the Scenario Lab tab for interactive what-if analysis.

    Parameters
    ----------
    data
        Static bundle dict (Cabo Pulmo) or case study JSON (Shark Bay).
    site
        Canonical site name (e.g. "Cabo Pulmo National Park").
    mode
        "live" or "demo".
    """
    # --- Section header ---
    short_name = site.split(" ")[0] + " " + site.split(" ")[1] if " " in site else site
    st.markdown(
        f'<div class="section-header">SCENARIO LAB - {short_name}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">'
        "Adjust environmental and market parameters to model their impact on "
        "ecosystem service valuations. Monte Carlo simulations recalculate in "
        "real time using 10,000 triangular-distribution draws per service."
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Extract base services ---
    base_services = _extract_services(data, site)
    if not base_services:
        st.warning("No ecosystem service data available for this site.")
        return

    # --- Parameter sliders ---
    st.markdown(
        '<div class="subsection-header">Parameter Controls</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.5])
    with col1:
        carbon_price = st.slider(
            "Carbon Price ($/tonne)",
            min_value=10,
            max_value=100,
            value=_BASE_CARBON_PRICE,
            step=5,
            key="scenario_carbon_price",
        )
    with col2:
        habitat_loss_pct = st.slider(
            "Habitat Loss (%)",
            min_value=0,
            max_value=50,
            value=0,
            step=1,
            key="scenario_habitat_loss",
        )
    with col3:
        tourism_growth_pct = st.slider(
            "Tourism Growth (%)",
            min_value=-20,
            max_value=30,
            value=0,
            step=1,
            key="scenario_tourism_growth",
        )
    with col4:
        fisheries_change_pct = st.slider(
            "Fisheries Change (%)",
            min_value=-30,
            max_value=20,
            value=0,
            step=1,
            key="scenario_fisheries_change",
        )
    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reset to Base", key="scenario_reset"):
            st.session_state["scenario_carbon_price"] = _BASE_CARBON_PRICE
            st.session_state["scenario_habitat_loss"] = 0
            st.session_state["scenario_tourism_growth"] = 0
            st.session_state["scenario_fisheries_change"] = 0
            st.rerun()

    adjustments = {
        "carbon_price": carbon_price,
        "habitat_loss_pct": habitat_loss_pct,
        "tourism_growth_pct": tourism_growth_pct,
        "fisheries_change_pct": fisheries_change_pct,
    }

    # --- Apply adjustments and run Monte Carlo ---
    scenario_services = apply_scenario_adjustments(base_services, adjustments)

    base_mc = _run_mc_cached(base_services, n_simulations=10_000)
    scenario_mc = _run_mc_cached(scenario_services, n_simulations=10_000)

    base_esv = sum(s["value"] for s in base_services)
    scenario_esv = sum(s["value"] for s in scenario_services)

    # --- ESV Impact Card + Monte Carlo Histogram ---
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown(
            _esv_impact_card(base_esv, scenario_esv),
            unsafe_allow_html=True,
        )
        # Service-level breakdown
        st.markdown(
            '<div style="margin-top:16px">'
            '<div class="kpi-card">'
            '<div class="kpi-label">Service Breakdown</div>',
            unsafe_allow_html=True,
        )
        for base_svc, scen_svc in zip(base_services, scenario_services):
            delta = scen_svc["value"] - base_svc["value"]
            if abs(delta) < 0.01:
                color = COLORS["text_muted"]
                sign_str = ""
            elif delta > 0:
                color = COLORS["success"]
                sign_str = "+"
            else:
                color = COLORS["danger"]
                sign_str = ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:6px 0;border-bottom:1px solid #1E293B">'
                f'<span style="color:{COLORS["text_body"]};font-size:15px">'
                f'{scen_svc["service_name"]}</span>'
                f'<span style="color:{color};font-size:15px;font-weight:600">'
                f"{fmt_usd(scen_svc['value'])}"
                f'<span style="font-size:13px;margin-left:6px">'
                f"({sign_str}{fmt_usd(delta)})</span>"
                f"</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    with right_col:
        histogram_fig = _build_histogram(base_mc, scenario_mc)
        st.plotly_chart(histogram_fig, width="stretch", key="v3_scenario_histogram")

    # --- Sensitivity Tornado Chart ---
    st.markdown(
        '<div class="subsection-header">Sensitivity Analysis</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:15px;color:#94A3B8;margin-bottom:12px">'
        "One-at-a-time (OAT) perturbation at +/-20%. "
        "Bars show ESV change when each service varies individually - "
        "longest bar is the dominant risk driver."
        "</div>",
        unsafe_allow_html=True,
    )
    sensitivity = run_sensitivity_analysis(base_services, n_simulations=10_000)
    tornado_fig = _build_tornado(sensitivity)
    st.plotly_chart(tornado_fig, width="stretch", key="v3_scenario_tornado")

    # --- Axiom Chain Impact ---
    st.markdown(
        '<div class="subsection-header">Bridge Axiom Chain Impact</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:15px;color:#94A3B8;margin-bottom:12px">'
        "Bridge axioms affected by the current scenario parameters. "
        "Each axiom translates an ecological measurement into a financial "
        "metric through peer-reviewed coefficients."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_axiom_chain_html(adjustments), unsafe_allow_html=True)

    # --- Demo mode note ---
    if mode == "demo":
        st.markdown(
            '<div class="caveats" style="margin-top:28px">'
            "<h4>Demo Mode</h4>"
            "<p>All computations run locally using pure-Python Monte Carlo "
            "and sensitivity engines (no external services required). "
            "Live recalculation available in Live Intelligence mode with "
            "full Neo4j graph traversal and provenance tracking.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
