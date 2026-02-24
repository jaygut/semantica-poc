"""Scenario Lab - interactive what-if analysis for Nereus v4/v6 Natural Capital Intelligence.

Key difference from v3: axiom chains are derived dynamically from site
habitat types using ``_HABITAT_AXIOM_MAP``. No hardcoded per-site chains.

v6 additions: SSP Climate Pathway, Counterfactual, Restoration ROI tabs,
Tipping Point proximity, and Scenario Workbench (save/compare).
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from investor_demo.components.v4.shared import COLORS, fmt_usd  # noqa: E402
from maris.axioms.monte_carlo import run_monte_carlo  # noqa: E402
from maris.axioms.sensitivity import run_sensitivity_analysis  # noqa: E402
from maris.sites.esv_estimator import _HABITAT_AXIOM_MAP  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_CARBON_PRICE = 30  # USD per tonne (Verra VCS VM0033)

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
    "carbon_stock": "Carbon Stock",
    "carbon_credits": "Carbon Credits",
    "ecosystem_value": "Ecosystem Value",
}

# Axiom metadata for all 16 axioms - used to build chains dynamically
_AXIOM_META: dict[str, dict[str, Any]] = {
    "BA-001": {"name": "MPA biomass to dive tourism value", "coefficient": "Up to 84% higher WTP", "affected_by": ["tourism_growth"]},
    "BA-002": {"name": "No-take MPA biomass multiplier", "coefficient": "4.63x over 10yr", "affected_by": ["habitat_loss"]},
    "BA-003": {"name": "Sea otter kelp carbon cascade", "coefficient": "Trophic cascade", "affected_by": ["habitat_loss"]},
    "BA-004": {"name": "Coral reef flood protection", "coefficient": "Wave energy reduction", "affected_by": ["habitat_loss"]},
    "BA-005": {"name": "Mangrove flood protection", "coefficient": "66% wave reduction per 100m", "affected_by": ["habitat_loss"]},
    "BA-006": {"name": "Mangrove fisheries production", "coefficient": "Nursery habitat", "affected_by": ["habitat_loss", "fisheries_change"]},
    "BA-007": {"name": "Mangrove carbon stock", "coefficient": "1,023 tCO2/ha", "affected_by": ["habitat_loss"]},
    "BA-008": {"name": "Seagrass carbon credit value", "coefficient": "VCS VM0033", "affected_by": ["carbon_price"]},
    "BA-009": {"name": "Mangrove restoration BCR", "coefficient": "3:1 to 10:1", "affected_by": ["habitat_loss"]},
    "BA-010": {"name": "Kelp forest global value", "coefficient": "$200/ha/yr", "affected_by": ["habitat_loss"]},
    "BA-011": {"name": "MPA climate resilience", "coefficient": "30% reduction", "affected_by": ["habitat_loss"]},
    "BA-012": {"name": "Reef degradation fisheries loss", "coefficient": "35% loss", "affected_by": ["habitat_loss", "fisheries_change"]},
    "BA-013": {"name": "Seagrass carbon sequestration rate", "coefficient": "0.84 tCO2/ha/yr", "affected_by": ["habitat_loss"]},
    "BA-014": {"name": "Carbon stock to credit value", "coefficient": "$30/tonne", "coefficient_val": 30, "affected_by": ["carbon_price"]},
    "BA-015": {"name": "Habitat loss carbon emission", "coefficient": "294 tCO2/ha released", "affected_by": ["habitat_loss"]},
    "BA-016": {"name": "MPA protection carbon permanence", "coefficient": "25-100yr guarantee", "affected_by": ["habitat_loss"]},
}

# SSP labels for the radio selector
_SSP_LABELS: dict[str, str] = {
    "SSP1-2.6": "SSP1-2.6 (Paris-aligned, 1.8C)",
    "SSP2-4.5": "SSP2-4.5 (Current trajectory, 2.7C)",
    "SSP5-8.5": "SSP5-8.5 (High emissions, 4.4C)",
}

# Sites eligible for Restoration ROI tab (mangrove/seagrass)
_RESTORATION_SITES = {"sundarbans", "cispata", "shark bay", "belize"}


def _get_site_axiom_chain(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive the axiom chain for a site from its habitat types."""
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()

    primary = data.get("ecological_status", {}).get("primary_habitat", "")
    habitats_to_check = [primary] if primary else []

    # Also check additional habitats
    for hab in data.get("ecological_status", {}).get("habitats", []):
        h_id = hab.get("habitat_id", "") if isinstance(hab, dict) else ""
        if h_id and h_id not in habitats_to_check:
            habitats_to_check.append(h_id)

    for hab_id in habitats_to_check:
        for entry in _HABITAT_AXIOM_MAP.get(hab_id, []):
            aid = entry["axiom_id"]
            if aid not in seen:
                seen.add(aid)
                meta = _AXIOM_META.get(aid, {})
                chain.append({
                    "id": aid,
                    "name": meta.get("name", entry.get("description", aid)),
                    "coefficient": meta.get("coefficient", ""),
                    "coefficient_val": meta.get("coefficient_val"),
                    "affected_by": meta.get("affected_by", []),
                })

    # If nothing found, return a minimal default chain
    if not chain:
        for aid in ("BA-002", "BA-011"):
            meta = _AXIOM_META[aid]
            chain.append({
                "id": aid,
                "name": meta["name"],
                "coefficient": meta["coefficient"],
                "affected_by": meta["affected_by"],
            })

    return chain


# ---------------------------------------------------------------------------
# Service extraction
# ---------------------------------------------------------------------------


def _extract_services(data: dict[str, Any], site: str) -> list[dict[str, Any]]:
    """Parse ecosystem services from either bundle or case-study format."""
    services: list[dict[str, Any]] = []

    breakdown = data.get("financial_output", {}).get("services_breakdown", {})
    if breakdown:
        for key, val in breakdown.items():
            canonical = _SERVICE_NAME_MAP.get(key, key.replace("_usd", "").title())
            services.append({
                "service_name": canonical,
                "value": float(val),
                "ci_low": float(val) * 0.7,
                "ci_high": float(val) * 1.3,
            })
        return services

    svc_list = data.get("ecosystem_services", {}).get("services", [])
    for svc in svc_list:
        raw_name = svc.get("service_type", "unknown")
        canonical = _SERVICE_NAME_MAP.get(raw_name, raw_name.replace("_", " ").title())
        val = float(svc.get("annual_value_usd", 0))
        ci = svc.get("confidence_interval", {})
        services.append({
            "service_name": canonical,
            "value": val,
            "ci_low": float(ci.get("ci_low", val * 0.7)),
            "ci_high": float(ci.get("ci_high", val * 1.3)),
        })

    return services


# ---------------------------------------------------------------------------
# Scenario adjustment logic
# ---------------------------------------------------------------------------


def apply_scenario_adjustments(
    base_services: list[dict[str, Any]],
    adjustments: dict[str, float],
) -> list[dict[str, Any]]:
    """Apply parameter changes to service values."""
    modified = deepcopy(base_services)
    carbon_price = adjustments.get("carbon_price", _BASE_CARBON_PRICE)
    habitat_loss = adjustments.get("habitat_loss_pct", 0) / 100.0
    tourism_growth = adjustments.get("tourism_growth_pct", 0) / 100.0
    fisheries_change = adjustments.get("fisheries_change_pct", 0) / 100.0

    carbon_scale = carbon_price / _BASE_CARBON_PRICE

    for svc in modified:
        name = svc["service_name"]
        if name in ("Carbon", "Carbon Stock", "Carbon Credits"):
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
    payload = json.dumps(
        [{"n": s["service_name"], "v": round(s["value"], 2),
          "l": round(s["ci_low"], 2), "h": round(s["ci_high"], 2)}
         for s in services],
        sort_keys=True,
    )
    return hashlib.md5(f"{payload}:{n}".encode()).hexdigest()  # noqa: S324


def _run_mc_cached(
    services: list[dict[str, Any]],
    n_simulations: int = 10_000,
) -> dict[str, Any]:
    key = _cache_key(services, n_simulations)
    cache_store = "v4_scenario_mc_cache"
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


def _build_histogram(base_mc: dict[str, Any], scenario_mc: dict[str, Any]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=base_mc["simulations"], nbinsx=60,
        marker_color="rgba(148, 163, 184, 0.35)",
        marker_line_color="rgba(148, 163, 184, 0.5)",
        marker_line_width=0.5,
        name=f"Base (median {fmt_usd(base_mc['median'])})",
        opacity=0.6,
    ))
    fig.add_trace(go.Histogram(
        x=scenario_mc["simulations"], nbinsx=60,
        marker_color=COLORS["accent_blue"],
        marker_line_color="rgba(91, 155, 213, 0.7)",
        marker_line_width=0.5,
        name=f"Scenario (median {fmt_usd(scenario_mc['median'])})",
        opacity=0.7,
    ))
    for val, lbl, clr in [
        (scenario_mc["p5"], "P5", COLORS["danger"]),
        (scenario_mc["median"], "Median", "#FFFFFF"),
        (scenario_mc["p95"], "P95", COLORS["success"]),
    ]:
        dash = "dash" if lbl != "Median" else "solid"
        fig.add_vline(
            x=val, line_dash=dash, line_color=clr,
            annotation_text=f"{lbl} {fmt_usd(val)}",
            annotation_font_color=clr, annotation_font_size=12,
        )
    fig.update_layout(
        title=dict(
            text="ESV Distribution - 10,000 Simulations",
            font=dict(size=16, color=COLORS["text_heading"]),
            x=0,
            y=0.98,
            xanchor="left"
        ),
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_body"]),
        xaxis=dict(
            title=dict(
                text="Total ESV (USD)",
                font=dict(size=13, color=COLORS["text_secondary"])
            ),
            gridcolor="#1E293B",
            tickformat="$,.0f",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(
                text="Frequency",
                font=dict(size=13, color=COLORS["text_secondary"])
            ),
            gridcolor="#1E293B",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=COLORS["text_body"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=60, r=30, t=100, b=50),
        height=400,
    )
    return fig


def _build_tornado(sensitivity: dict[str, Any]) -> go.Figure:
    tornado_data = sensitivity.get("tornado_plot_data", [])
    if not tornado_data:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="No sensitivity data available", xref="paper",
                              yref="paper", showarrow=False, font=dict(color=COLORS["text_muted"]))],
        )
        return fig

    tornado_data = sorted(tornado_data, key=lambda d: d["sensitivity_rank"])
    tornado_data.reverse()

    base_esv = tornado_data[0]["base_esv"]
    names = [d["parameter_name"] for d in tornado_data]
    low_deltas = [d["low_esv"] - base_esv for d in tornado_data]
    high_deltas = [d["high_esv"] - base_esv for d in tornado_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(y=names, x=low_deltas, orientation="h",
                         marker_color=COLORS["danger"], name="Low (-20%)", opacity=0.85))
    fig.add_trace(go.Bar(y=names, x=high_deltas, orientation="h",
                         marker_color=COLORS["success"], name="High (+20%)", opacity=0.85))
    fig.update_layout(
        title=dict(
            text="Sensitivity Tornado - OAT Analysis",
            font=dict(size=16, color=COLORS["text_heading"]),
            x=0,
            y=0.98,
            xanchor="left"
        ),
        barmode="relative",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_body"]),
        xaxis=dict(
            title=dict(
                text="ESV Change from Baseline (USD)",
                font=dict(size=13, color=COLORS["text_secondary"])
            ),
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
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=COLORS["text_body"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=150, r=40, t=100, b=50),
        height=max(320, 80 * len(names)),
    )
    return fig


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _esv_impact_card(base_esv: float, scenario_esv: float) -> str:
    delta = scenario_esv - base_esv
    delta_pct = (delta / base_esv * 100) if base_esv else 0.0
    if delta > 0:
        arrow, color = "&#9650;", COLORS["success"]
    elif delta < 0:
        arrow, color = "&#9660;", COLORS["danger"]
    else:
        arrow, color = "&#9654;", COLORS["text_muted"]
    sign = "+" if delta >= 0 else ""
    return f"""
    <div class="kpi-card" style="min-height:220px">
        <div class="kpi-label">Scenario ESV Impact</div>
        <div style="display:flex;gap:24px;align-items:flex-end;margin-bottom:14px">
            <div>
                <div style="font-size:13px;color:{COLORS['text_muted']};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Base</div>
                <div style="font-size:28px;font-weight:700;color:{COLORS['text_heading']}">{fmt_usd(base_esv)}</div>
            </div>
            <div style="font-size:24px;color:{COLORS['text_muted']};padding-bottom:4px">&rarr;</div>
            <div>
                <div style="font-size:13px;color:{COLORS['text_muted']};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Scenario</div>
                <div style="font-size:28px;font-weight:700;color:{COLORS['text_heading']}">{fmt_usd(scenario_esv)}</div>
            </div>
        </div>
        <div style="font-size:22px;font-weight:600;color:{color}">
            <span>{arrow}</span> {sign}{fmt_usd(abs(delta))} ({sign}{delta_pct:.1f}%)
        </div>
    </div>
    """


def _axiom_chain_html(adjustments: dict[str, float], axiom_chain: list[dict[str, Any]]) -> str:
    """Render axiom chain impact panel using the site's dynamic chain."""
    carbon_price = adjustments.get("carbon_price", _BASE_CARBON_PRICE)
    habitat_loss_pct = adjustments.get("habitat_loss_pct", 0)
    tourism_growth_pct = adjustments.get("tourism_growth_pct", 0)
    fisheries_change_pct = adjustments.get("fisheries_change_pct", 0)

    rows = ""
    for ax in axiom_chain:
        affected = False
        impact_parts: list[str] = []

        if "carbon_price" in ax["affected_by"] and carbon_price != _BASE_CARBON_PRICE:
            affected = True
            base_val = ax.get("coefficient_val", _BASE_CARBON_PRICE)
            css = "positive" if carbon_price > base_val else "negative"
            impact_parts.append(f'<span class="parameter-impact {css}">${base_val} &rarr; ${carbon_price}/tonne</span>')

        if "habitat_loss" in ax["affected_by"] and habitat_loss_pct > 0:
            affected = True
            impact_parts.append(f'<span class="parameter-impact negative">-{habitat_loss_pct}% habitat loss applied</span>')

        if "tourism_growth" in ax["affected_by"] and tourism_growth_pct != 0:
            affected = True
            css = "positive" if tourism_growth_pct > 0 else "negative"
            sign = "+" if tourism_growth_pct > 0 else ""
            impact_parts.append(f'<span class="parameter-impact {css}">{sign}{tourism_growth_pct}% tourism growth</span>')

        if "fisheries_change" in ax["affected_by"] and fisheries_change_pct != 0:
            affected = True
            css = "positive" if fisheries_change_pct > 0 else "negative"
            sign = "+" if fisheries_change_pct > 0 else ""
            impact_parts.append(f'<span class="parameter-impact {css}">{sign}{fisheries_change_pct}% fisheries change</span>')

        impact_html = " ".join(impact_parts) if affected else '<span class="parameter-impact neutral">No change</span>'
        border_color = COLORS["accent_blue"] if affected else COLORS["border_subtle"]

        rows += f"""
        <div style="background:linear-gradient(145deg,#162039 0%,#1A2744 100%);
             border-radius:8px;padding:16px 20px;border:1px solid {border_color};margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                <div>
                    <span style="font-weight:600;color:{COLORS['accent_blue']};font-size:15px;margin-right:8px">{ax['id']}</span>
                    <span style="color:{COLORS['text_body']};font-size:15px">{ax['name']}</span>
                </div>
                <div style="font-size:14px;color:{COLORS['text_secondary']}">Base: {ax['coefficient']}</div>
            </div>
            <div style="margin-top:8px">{impact_html}</div>
        </div>
        """
    return rows


# ---------------------------------------------------------------------------
# v6 Scenario Intelligence helpers
# ---------------------------------------------------------------------------


def _run_climate_scenario_safe(site: str, ssp: str, target_year: int) -> dict[str, Any] | None:
    """Run the climate scenario engine, returning None on failure."""
    try:
        from maris.scenario.climate_scenarios import run_climate_scenario
        from maris.scenario.models import ScenarioRequest
        req = ScenarioRequest(
            scenario_type="climate",
            site_scope=[site],
            ssp_scenario=ssp,
            target_year=target_year,
        )
        result = run_climate_scenario(req)
        return result.model_dump()
    except Exception:
        logger.exception("Climate scenario failed for %s", site)
        return None


def _run_counterfactual_safe(site: str) -> dict[str, Any] | None:
    """Run the counterfactual engine, returning None on failure."""
    try:
        from maris.scenario.counterfactual_engine import run_counterfactual
        from maris.scenario.models import ScenarioRequest
        req = ScenarioRequest(
            scenario_type="counterfactual",
            site_scope=[site],
        )
        result = run_counterfactual(req)
        return result.model_dump()
    except Exception:
        logger.exception("Counterfactual scenario failed for %s", site)
        return None


def _run_restoration_roi_safe(
    site_data: dict, investment: float, horizon: int, discount_rate: float,
) -> dict[str, Any] | None:
    """Run real options valuation, returning None on failure."""
    try:
        from maris.scenario.real_options_valuator import compute_conservation_option_value
        result = compute_conservation_option_value(
            site_data=site_data,
            investment_cost_usd=investment,
            time_horizon_years=horizon,
            discount_rate=discount_rate,
        )
        return result
    except Exception:
        logger.exception("Restoration ROI failed")
        return None


def _render_scenario_kpi_strip(
    base_esv: float, scenario_esv: float, uncertainty: dict | None = None,
) -> None:
    """Render a 3-column KPI strip for scenario results."""
    col1, col2, col3 = st.columns(3)
    delta_pct = ((scenario_esv - base_esv) / base_esv * 100) if base_esv else 0.0
    col1.metric("Baseline ESV", f"${base_esv / 1e6:.1f}M")
    col2.metric("Scenario ESV", f"${scenario_esv / 1e6:.1f}M")
    col3.metric("Delta", f"{delta_pct:+.1f}%", delta=f"${abs(scenario_esv - base_esv) / 1e6:.1f}M")

    if uncertainty:
        st.caption(
            f"P5: ${uncertainty.get('p5', 0) / 1e6:.1f}M | "
            f"P50: ${uncertainty.get('p50', 0) / 1e6:.1f}M | "
            f"P95: ${uncertainty.get('p95', 0) / 1e6:.1f}M"
        )


def _render_propagation_expander(result: dict[str, Any]) -> None:
    """Render propagation trace and confidence penalties in expanders."""
    trace = result.get("propagation_trace", [])
    if trace:
        with st.expander("Propagation Trace (full axiom arc)"):
            for step in trace:
                st.markdown(f"**{step['axiom_id']}**: {step['description']}")
                st.caption(
                    f"{step['input_parameter']} {step['input_value']:.2f} -> "
                    f"{step['output_parameter']} {step['output_value']:.2f}"
                )

    penalties = result.get("confidence_penalties", [])
    if penalties:
        with st.expander("Confidence Penalties Applied"):
            for penalty in penalties:
                st.caption(f"{penalty['reason']}: {penalty['penalty']:+.2f}")


def _is_restoration_eligible(site: str) -> bool:
    """Check if a site is eligible for Restoration ROI (mangrove/seagrass)."""
    site_lower = site.lower()
    return any(kw in site_lower for kw in _RESTORATION_SITES)


# ---------------------------------------------------------------------------
# Scenario Workbench
# ---------------------------------------------------------------------------


def _render_scenario_workbench(
    scenario_label: str, result_summary: dict[str, Any],
    key_suffix: str = "",
) -> None:
    """Render save/compare controls for the Scenario Workbench."""
    if "saved_scenarios" not in st.session_state:
        st.session_state["saved_scenarios"] = []

    st.markdown(
        '<div class="subsection-header" style="margin-top:28px">Scenario Workbench</div>',
        unsafe_allow_html=True,
    )

    _save_key = f"v6_save_scenario_{key_suffix}" if key_suffix else "v6_save_scenario"
    if st.button("Save Scenario", key=_save_key):
        st.session_state["saved_scenarios"].append({
            "label": scenario_label,
            **result_summary,
        })
        st.success(f"Saved: {scenario_label}")

    saved = st.session_state.get("saved_scenarios", [])
    if saved:
        with st.expander(f"Compare Scenarios ({len(saved)} saved)"):
            header = "| Scenario | Baseline | Projected | Delta |\n|---|---|---|---|\n"
            rows = ""
            for s in saved[-5:]:  # Show last 5
                rows += (
                    f"| {s.get('label', 'N/A')} "
                    f"| ${s.get('baseline_esv', 0) / 1e6:.1f}M "
                    f"| ${s.get('scenario_esv', 0) / 1e6:.1f}M "
                    f"| ${(s.get('scenario_esv', 0) - s.get('baseline_esv', 0)) / 1e6:.1f}M |\n"
                )
            st.markdown(header + rows)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render_scenario_engine(
    data: dict[str, Any],
    site: str,
    mode: str,
    **kwargs: Any,
) -> None:
    """Render the Scenario Lab tab for interactive what-if analysis."""
    short_name = " ".join(site.split()[:2]) if " " in site else site
    st.markdown(
        f"""
        <div class="masthead">
            <div class="masthead-brand">NEREUS | SCENARIO LAB</div>
            <h1 style="font-size: 42px; font-weight: 300; margin-top: 10px; margin-bottom: 5px;">{site}</h1>
            <div class="masthead-subtitle">Interactive what-if analysis and risk sensitivity modeling</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    base_services = _extract_services(data, site)
    if not base_services:
        st.warning("No ecosystem service data available for this site.")
        return

    base_esv = sum(s["value"] for s in base_services)
    primary_habitat = data.get("ecological_status", {}).get("primary_habitat", "")

    # ---- Scenario type tabs (v6) ----
    tab_labels = ["Climate Pathway", "Counterfactual", "Restoration ROI", "Custom"]
    tab_climate, tab_counterfactual, tab_roi, tab_custom = st.tabs(tab_labels)

    # ================================================================
    # Tab: Climate Pathway
    # ================================================================
    with tab_climate:
        st.markdown(
            '<div class="subsection-header">SSP Climate Pathway</div>',
            unsafe_allow_html=True,
        )

        ssp_options = list(_SSP_LABELS.values())
        ssp_choice = st.radio(
            "Select SSP Scenario",
            ssp_options,
            index=1,
            key="v6_ssp_radio",
        )
        # Reverse-map label to SSP key
        ssp_key = next(k for k, v in _SSP_LABELS.items() if v == ssp_choice)

        target_year = st.slider(
            "Target Year", min_value=2030, max_value=2100, value=2050,
            step=10, key="v6_target_year",
        )

        if st.button("Run Climate Scenario", key="v6_run_climate"):
            result = _run_climate_scenario_safe(site, ssp_key, target_year)
            if result and result.get("baseline_case"):
                b_esv = result["baseline_case"].get("total_esv_usd", base_esv)
                s_esv = result["scenario_case"].get("total_esv_usd", 0)
                _render_scenario_kpi_strip(b_esv, s_esv, result.get("uncertainty"))

                st.markdown(
                    f'<div style="font-size:15px;color:#B0BEC5;padding:12px 0">'
                    f'{result.get("answer", "")}</div>',
                    unsafe_allow_html=True,
                )

                # Tipping point for coral reef sites
                if primary_habitat == "coral_reef":
                    tp = result.get("tipping_point_proximity")
                    if tp:
                        st.warning(f"Tipping Point: {tp}")

                _render_propagation_expander(result)
                _render_scenario_workbench(
                    f"{ssp_key} {target_year} - {short_name}",
                    {"baseline_esv": b_esv, "scenario_esv": s_esv},
                    key_suffix="climate",
                )
            else:
                st.info("Scenario computed in demo mode - live engine returned no data.")
                _render_scenario_workbench(
                    f"{ssp_key} {target_year} - {short_name} (demo)",
                    {"baseline_esv": base_esv, "scenario_esv": base_esv * 0.5},
                    key_suffix="climate",
                )

    # ================================================================
    # Tab: Counterfactual
    # ================================================================
    with tab_counterfactual:
        st.markdown(
            '<div class="subsection-header">Counterfactual Analysis</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:15px;color:#94A3B8;margin-bottom:16px">'
            f"What would {short_name} be worth without protection? "
            f"Reverts key ecological parameters to pre-protection baselines."
            f"</div>",
            unsafe_allow_html=True,
        )

        if st.button("Run Counterfactual", key="v6_run_counterfactual"):
            result = _run_counterfactual_safe(site)
            if result and result.get("baseline_case"):
                b_esv = result["baseline_case"].get("total_esv_usd", base_esv)
                s_esv = result["scenario_case"].get("total_esv_usd", 0)
                _render_scenario_kpi_strip(b_esv, s_esv, result.get("uncertainty"))

                st.markdown(
                    f'<div style="font-size:15px;color:#B0BEC5;padding:12px 0">'
                    f'{result.get("answer", "")}</div>',
                    unsafe_allow_html=True,
                )

                tp = result.get("tipping_point_proximity")
                if tp:
                    st.warning(f"Tipping Point: {tp}")

                _render_propagation_expander(result)
                _render_scenario_workbench(
                    f"Counterfactual - {short_name}",
                    {"baseline_esv": b_esv, "scenario_esv": s_esv},
                    key_suffix="counterfactual",
                )
            else:
                st.info("Scenario computed in demo mode - live engine returned no data.")
                _render_scenario_workbench(
                    f"Counterfactual - {short_name} (demo)",
                    {"baseline_esv": base_esv, "scenario_esv": base_esv * 0.35},
                    key_suffix="counterfactual",
                )

    # ================================================================
    # Tab: Restoration ROI
    # ================================================================
    with tab_roi:
        st.markdown(
            '<div class="subsection-header">Restoration ROI</div>',
            unsafe_allow_html=True,
        )

        if _is_restoration_eligible(site):
            investment = st.slider(
                "Investment Cost ($M)", min_value=1, max_value=50,
                value=5, step=1, key="v6_investment",
            )
            horizon = st.slider(
                "Time Horizon (years)", min_value=5, max_value=30,
                value=20, step=5, key="v6_horizon",
            )
            discount_rate = st.selectbox(
                "Discount Rate",
                [0.03, 0.04, 0.05],
                index=1,
                format_func=lambda x: f"{x:.0%}",
                key="v6_discount",
            )

            if st.button("Compute ROI", key="v6_run_roi"):
                result = _run_restoration_roi_safe(
                    data, investment * 1_000_000, horizon, discount_rate,
                )
                if result and "error" not in result:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("BCR", f"{result.get('bcr', 0):.2f}x")
                    c2.metric("Static NPV", f"${result.get('static_npv', 0) / 1e6:.1f}M")
                    c3.metric("Option Value", f"${result.get('option_value', 0) / 1e6:.1f}M")
                    c4.metric("Payback", f"{result.get('payback_years', 0):.1f} yrs")

                    st.caption(
                        f"P5: ${result.get('p5_npv', 0) / 1e6:.1f}M | "
                        f"P50: ${result.get('p50_npv', 0) / 1e6:.1f}M | "
                        f"P95: ${result.get('p95_npv', 0) / 1e6:.1f}M"
                    )

                    premium = result.get("option_premium_pct", 0)
                    st.markdown(
                        f'<div style="font-size:15px;color:#B0BEC5;padding:12px 0">'
                        f"Option premium of {premium:.1f}% above static NPV captures "
                        f"management flexibility value."
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    _render_scenario_workbench(
                        f"ROI ${investment}M - {short_name}",
                        {
                            "baseline_esv": base_esv,
                            "scenario_esv": base_esv + result.get("static_npv", 0),
                        },
                        key_suffix="roi",
                    )
                else:
                    st.info("Scenario computed in demo mode - ROI engine returned no data.")
        else:
            st.info(
                f"{short_name} is a {primary_habitat.replace('_', ' ')} site. "
                "Restoration ROI is available for mangrove and seagrass sites "
                "(Sundarbans, Cispata Bay, Shark Bay, Belize)."
            )

    # ================================================================
    # Tab: Custom (preserves ALL existing v4 controls)
    # ================================================================
    with tab_custom:
        # Parameter sliders
        st.markdown('<div class="subsection-header">Parameter Controls</div>', unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.5])
        with col1:
            carbon_price = st.slider("Carbon Price ($/tonne)", min_value=10, max_value=100,
                                     value=_BASE_CARBON_PRICE, step=5, key="v4_scenario_carbon_price")
        with col2:
            habitat_loss_pct = st.slider("Habitat Loss (%)", min_value=0, max_value=50,
                                         value=0, step=1, key="v4_scenario_habitat_loss")
        with col3:
            tourism_growth_pct = st.slider("Tourism Growth (%)", min_value=-20, max_value=30,
                                           value=0, step=1, key="v4_scenario_tourism_growth")
        with col4:
            fisheries_change_pct = st.slider("Fisheries Change (%)", min_value=-30, max_value=20,
                                             value=0, step=1, key="v4_scenario_fisheries_change")
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Reset to Base", key="v4_scenario_reset"):
                st.session_state["v4_scenario_carbon_price"] = _BASE_CARBON_PRICE
                st.session_state["v4_scenario_habitat_loss"] = 0
                st.session_state["v4_scenario_tourism_growth"] = 0
                st.session_state["v4_scenario_fisheries_change"] = 0
                st.rerun()

        adjustments = {
            "carbon_price": carbon_price,
            "habitat_loss_pct": habitat_loss_pct,
            "tourism_growth_pct": tourism_growth_pct,
            "fisheries_change_pct": fisheries_change_pct,
        }

        scenario_services = apply_scenario_adjustments(base_services, adjustments)
        base_mc = _run_mc_cached(base_services, n_simulations=10_000)
        scenario_mc = _run_mc_cached(scenario_services, n_simulations=10_000)
        scenario_esv = sum(s["value"] for s in scenario_services)

        left_col, right_col = st.columns([1, 2])
        with left_col:
            st.markdown(_esv_impact_card(base_esv, scenario_esv), unsafe_allow_html=True)
            st.markdown(
                '<div style="margin-top:16px"><div class="kpi-card"><div class="kpi-label">Service Breakdown</div>',
                unsafe_allow_html=True,
            )
            for base_svc, scen_svc in zip(base_services, scenario_services):
                delta = scen_svc["value"] - base_svc["value"]
                if abs(delta) < 0.01:
                    color, sign_str = COLORS["text_muted"], ""
                elif delta > 0:
                    color, sign_str = COLORS["success"], "+"
                else:
                    color, sign_str = COLORS["danger"], ""
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1E293B">'
                    f'<span style="color:{COLORS["text_body"]};font-size:15px">{scen_svc["service_name"]}</span>'
                    f'<span style="color:{color};font-size:15px;font-weight:600">'
                    f"{fmt_usd(scen_svc['value'])}"
                    f'<span style="font-size:13px;margin-left:6px">({sign_str}{fmt_usd(delta)})</span>'
                    f"</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div></div>", unsafe_allow_html=True)

        with right_col:
            histogram_fig = _build_histogram(base_mc, scenario_mc)
            st.plotly_chart(histogram_fig, width="stretch", key="v4_scenario_histogram")

        # Tipping Point Proximity for coral reef sites in Custom tab
        if primary_habitat == "coral_reef":
            recovery = data.get("ecological_recovery", {})
            biomass_ratio = recovery.get("metrics", {}).get("fish_biomass", {}).get("recovery_ratio")
            if biomass_ratio is not None:
                biomass_kg_ha = float(biomass_ratio) * 200.0
                try:
                    from maris.scenario.tipping_point_analyzer import get_threshold_proximity
                    proximity_msg = get_threshold_proximity(biomass_kg_ha)
                    if proximity_msg:
                        st.warning(f"Tipping Point: {proximity_msg}")
                except ImportError:
                    pass

        # Sensitivity Tornado
        st.markdown('<div class="subsection-header">Sensitivity Analysis</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:15px;color:#94A3B8;margin-bottom:12px">'
            "One-at-a-time (OAT) perturbation at +/-20%. Bars show ESV change when "
            "each service varies individually - longest bar is the dominant risk driver."
            "</div>",
            unsafe_allow_html=True,
        )
        sensitivity = run_sensitivity_analysis(base_services, n_simulations=10_000)
        tornado_fig = _build_tornado(sensitivity)
        st.plotly_chart(tornado_fig, width="stretch", key="v4_scenario_tornado")

        # Axiom Chain Impact - dynamically derived
        st.markdown('<div class="subsection-header">Bridge Axiom Chain Impact</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:15px;color:#94A3B8;margin-bottom:12px">'
            "Bridge axioms affected by the current scenario parameters. "
            "Each axiom translates an ecological measurement into a financial "
            "metric through peer-reviewed coefficients."
            "</div>",
            unsafe_allow_html=True,
        )
        axiom_chain = _get_site_axiom_chain(data)
        st.markdown(_axiom_chain_html(adjustments, axiom_chain), unsafe_allow_html=True)

        # Workbench for custom tab
        _render_scenario_workbench(
            f"Custom - {short_name}",
            {"baseline_esv": base_esv, "scenario_esv": scenario_esv},
            key_suffix="custom",
        )

    if mode == "demo":
        st.markdown(
            '<div class="caveats" style="margin-top:28px">'
            "<h4>Demo Mode</h4>"
            "<p>All computations run locally using pure-Python Monte Carlo "
            "and sensitivity engines (no external services required).</p>"
            "</div>",
            unsafe_allow_html=True,
        )
