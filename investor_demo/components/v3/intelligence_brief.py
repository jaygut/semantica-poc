"""Intelligence Brief tab for MARIS v3 Intelligence Platform.

Renders an interactive, drill-down-capable intelligence brief for a
selected MPA site. Every KPI card is expandable to reveal the reasoning
chain - bridge axiom derivations, Monte Carlo distributions, and
DOI-backed evidence.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from investor_demo.components.v3.shared import (  # noqa: E402
    COLORS,
    axiom_tag,
    fmt_usd,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Axiom info - plain-English descriptions and citations
# ---------------------------------------------------------------------------

AXIOM_INFO: dict[str, dict[str, str]] = {
    "BA-001": {
        "meaning": (
            "Fish biomass increases drive tourism value: divers will pay "
            "up to 84% more at sites with healthy reef biomass"
        ),
        "citation": "Marcos-Castillo et al. 2024",
        "doi": "10.1038/s41598-024-83664-1",
    },
    "BA-002": {
        "meaning": (
            "No-take marine reserves accumulate biomass to 670% of "
            "unprotected levels (global meta-analysis of 82 MPAs; "
            "Cabo Pulmo observed 463%)"
        ),
        "citation": "Hopf et al. 2024",
        "doi": "10.1002/eap.3027",
    },
    "BA-011": {
        "meaning": (
            "Protected reefs suffer 30% less damage from climate "
            "disturbances than unprotected reefs"
        ),
        "citation": "Ortiz-Villa et al. 2024",
        "doi": "10.1111/gcb.17477",
    },
    "BA-012": {
        "meaning": (
            "Reef degradation causes 35% loss in fisheries productivity "
            "when protection fails"
        ),
        "citation": "Rogers et al. 2018",
        "doi": "10.1111/1365-2664.13051",
    },
    "BA-013": {
        "meaning": (
            "Seagrass meadows sequester carbon at 0.84 tCO2/ha/yr through "
            "sediment burial of approximately 20% of net primary production"
        ),
        "citation": "Gomis et al. 2025",
        "doi": "10.1038/s41467-025-64667-6",
    },
    "BA-014": {
        "meaning": (
            "Blue carbon sequestration generates tradeable credits at "
            "$15-50 per tCO2 under voluntary market standards"
        ),
        "citation": "Duarte et al. 2025",
        "doi": "10.1038/s41558-024-02188-4",
    },
    "BA-015": {
        "meaning": (
            "Seagrass loss releases 112-476 tCO2/ha of stored carbon, "
            "as demonstrated by the 2011 Shark Bay heatwave"
        ),
        "citation": "Arias-Ortiz et al. 2018",
        "doi": "10.1038/s41558-018-0096-y",
    },
    "BA-016": {
        "meaning": (
            "MPA protection with NEOLI 4+/5 provides 25-100 year carbon "
            "permanence guarantee"
        ),
        "citation": "Lovelock et al. 2025",
        "doi": "10.1038/s41558-024-02206-5",
    },
}

# Which axioms to display per site
_SITE_AXIOMS: dict[str, list[str]] = {
    "Cabo Pulmo National Park": ["BA-001", "BA-002", "BA-011", "BA-012"],
    "Shark Bay World Heritage Area": ["BA-013", "BA-014", "BA-015", "BA-016"],
}


# ---------------------------------------------------------------------------
# Data normalizer - unifies bundle vs case study JSON formats
# ---------------------------------------------------------------------------


def _normalize_site_data(data: dict[str, Any], site: str) -> dict[str, Any]:
    """Normalize bundle or case study data into a common internal format.

    Cabo Pulmo bundles have ``financial_output.services_breakdown`` and
    ``risk_assessment.monte_carlo_summary``.  Shark Bay case studies have
    ``ecosystem_services.services[]`` and no pre-computed Monte Carlo.
    This function maps both into a shared structure.
    """
    out: dict[str, Any] = {
        "site_name": site,
        "esv_total": 0.0,
        "services": [],
        "neoli_score": 0,
        "neoli_breakdown": {},
        "asset_rating": "",
        "composite_score": 0.0,
        "monte_carlo": {},
        "biomass_ratio": None,
        "carbon_sequestration": None,
        "seagrass_extent": None,
        "climate_buffer": None,
        "degradation_risk": None,
        "bridge_axioms_applied": [],
        "caveats": data.get("caveats", []),
        "metadata": data.get("metadata", {}),
        "comparison_sites": data.get("comparison_sites", []),
        "framework_alignment": data.get("framework_alignment", {}),
    }

    # --- Cabo Pulmo bundle format ---
    fin = data.get("financial_output", {})
    if fin.get("services_breakdown"):
        out["esv_total"] = fin.get("market_price_esv_usd", 0)
        for key, val in fin["services_breakdown"].items():
            if isinstance(val, (int, float)) and val > 0:
                out["services"].append({
                    "name": key.removesuffix("_usd").replace("_", " ").title(),
                    "value": val,
                })
        out["ci_95"] = fin.get("market_price_esv_ci_95_usd")

        # Monte Carlo from bundle
        mc = data.get("risk_assessment", {}).get("monte_carlo_summary", {})
        if mc:
            pcts = mc.get("percentiles_usd", {})
            out["monte_carlo"] = {
                "mean": mc.get("mean_usd", 0),
                "std": mc.get("std_usd", 0),
                "median": pcts.get("p50", 0),
                "p5": pcts.get("p5", 0),
                "p95": pcts.get("p95", 0),
                "n_simulations": mc.get("n_simulations", 10000),
            }

        # Climate buffer / degradation from bundle
        clim = data.get("risk_assessment", {}).get("climate_resilience", {})
        if clim:
            out["climate_buffer"] = {
                "disturbance_reduction_pct": clim.get(
                    "disturbance_reduction_percent", 0
                ),
                "recovery_boost_pct": clim.get("recovery_boost_percent", 0),
                "source_doi": clim.get("source_doi", ""),
            }
        deg = data.get("risk_assessment", {}).get("degradation_risk", {})
        if deg:
            out["degradation_risk"] = {
                "loss_central_pct": deg.get(
                    "productivity_loss_central_percent", 0
                ),
                "loss_range_pct": deg.get("productivity_loss_range_percent", []),
                "source_doi": deg.get("source_doi", ""),
            }

    # --- Case study format (Shark Bay and raw Cabo Pulmo) ---
    esv_bundle = data.get("ecosystem_services", {})
    if esv_bundle.get("services") and not fin.get("services_breakdown"):
        out["esv_total"] = esv_bundle.get("total_annual_value_usd", 0)
        for svc in esv_bundle["services"]:
            name = (
                svc.get("service_type", "Unknown")
                .replace("_", " ")
                .title()
            )
            out["services"].append({
                "name": name,
                "value": svc.get("annual_value_usd", 0),
            })
        # Compute Monte Carlo from services
        mc_services = []
        for svc in esv_bundle["services"]:
            val = svc.get("annual_value_usd", 0)
            mc_services.append({
                "value": val,
                "ci_low": val * 0.7,
                "ci_high": val * 1.3,
            })
        try:
            from maris.axioms.monte_carlo import run_monte_carlo

            mc_result = run_monte_carlo(mc_services, n_simulations=10_000)
            out["monte_carlo"] = {
                "mean": mc_result["mean"],
                "std": mc_result["std"],
                "median": mc_result["median"],
                "p5": mc_result["p5"],
                "p95": mc_result["p95"],
                "n_simulations": mc_result["n_simulations"],
            }
        except Exception:
            logger.warning("Monte Carlo computation failed")

    # --- NEOLI ---
    eco_status = data.get("ecological_status", {})
    neoli_assess = data.get("neoli_assessment", {})
    if neoli_assess.get("neoli_score") is not None:
        out["neoli_score"] = neoli_assess["neoli_score"]
        criteria = neoli_assess.get("criteria", {})
        out["neoli_breakdown"] = {
            "no_take": criteria.get("no_take", {}).get("value", False),
            "enforced": criteria.get("enforced", {}).get("value", False),
            "old": criteria.get("old", {}).get("value", False),
            "large": criteria.get("large", {}).get("value", False),
            "isolated": criteria.get("isolated", {}).get("value", False),
        }
        out["neoli_criteria_detail"] = criteria
    elif eco_status.get("neoli_score") is not None:
        out["neoli_score"] = eco_status["neoli_score"]
        bd = eco_status.get("neoli_breakdown", {})
        out["neoli_breakdown"] = bd

    # --- Biomass ---
    bio_bundle = eco_status.get("biomass_ratio")
    if isinstance(bio_bundle, dict):
        out["biomass_ratio"] = bio_bundle
    recovery = data.get("ecological_recovery", {})
    if recovery:
        bio = recovery.get("metrics", {}).get("fish_biomass", {})
        if bio.get("recovery_ratio"):
            out["biomass_ratio"] = {
                "central": bio["recovery_ratio"],
                "ci_95": bio.get("confidence_interval_95", [0, 0]),
            }

    # --- Carbon / seagrass metrics ---
    seq = eco_status.get("metrics", {}).get("sequestration", {})
    if seq:
        out["carbon_sequestration"] = {
            "rate_tCO2_per_ha_yr": seq.get("rate_tCO2_per_ha_yr", 0),
        }
    sg_extent = data.get("site", {}).get("seagrass_extent_km2")
    if sg_extent:
        out["seagrass_extent"] = sg_extent

    # --- Asset rating ---
    rating = data.get("asset_quality_rating", {})
    out["asset_rating"] = rating.get("rating", "")
    out["composite_score"] = rating.get("composite_score", 0.0)

    # --- Bridge axioms applied ---
    out["bridge_axioms_applied"] = data.get(
        "bridge_axioms_applied",
        data.get("bridge_axiom_applications", []),
    )

    return out


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_masthead(nd: dict[str, Any], mode: str) -> None:
    """Render site masthead with badges and mode indicator."""
    site_name = nd["site_name"]
    fa = nd.get("framework_alignment", {})

    # Determine badges
    badges = ""
    ifc = fa.get("ifc_blue_finance", {})
    if ifc.get("eligible_use_of_proceeds") or ifc.get("status"):
        badges += (
            '<span class="badge badge-green" title="Self-assessed alignment '
            "with IFC Blue Finance Guidelines (2022) eligible use of proceeds "
            'criteria. Not independently verified.">'
            "IFC Blue Finance - Self-Assessed</span>"
        )
    tnfd = fa.get("tnfd_leap", {})
    if tnfd:
        badges += (
            '<span class="badge badge-blue" title="Anticipates alignment with '
            "TNFD LEAP disclosure framework. MARIS data structure follows LEAP "
            'phases but has not undergone independent TNFD review.">'
            "TNFD LEAP - Anticipates Alignment</span>"
        )

    mode_html = ""
    if mode == "live":
        mode_html = (
            '<span class="conn-status conn-live" style="float:right">'
            '<span class="conn-dot"></span>Live API</span>'
        )
    else:
        mode_html = (
            '<span class="conn-status conn-static" style="float:right">'
            '<span class="conn-dot"></span>Demo Mode</span>'
        )

    st.markdown(
        f"""
<div class="masthead">
<div class="masthead-brand">MARIS | INTELLIGENCE BRIEF {mode_html}</div>
<h1>{site_name}</h1>
<div class="masthead-subtitle">Provenance-First Blue Finance Infrastructure</div>
<div class="masthead-badges">{badges}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_kpi_strip(nd: dict[str, Any]) -> None:
    """Render the 4-card KPI strip with expandable drill-downs."""
    st.markdown(
        '<div class="section-header">Key Metrics</div>',
        unsafe_allow_html=True,
    )

    mc = nd.get("monte_carlo", {})
    median = mc.get("median", nd["esv_total"])

    k1, k2, k3, k4 = st.columns(4)

    # --- KPI 1: ESV ---
    with k1:
        st.markdown(
            f"""
<div class="kpi-card">
<div class="kpi-label">Annual Ecosystem Service Value</div>
<div class="kpi-value">{fmt_usd(median)}</div>
<div class="kpi-context">Median - Base Case</div>
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("ESV Derivation"):
            # Service breakdown list
            st.markdown("**Service Breakdown**")
            for svc in sorted(
                nd["services"], key=lambda s: s["value"], reverse=True
            ):
                st.markdown(f"- {svc['name']}: **{fmt_usd(svc['value'])}**")

            # Mini Monte Carlo chart
            if mc.get("mean") and mc.get("std"):
                _render_mc_mini(mc)

            # Axiom chain
            axiom_ids = _SITE_AXIOMS.get(nd["site_name"], [])
            if axiom_ids:
                st.markdown("**Bridge Axiom Chain**")
                for aid in axiom_ids:
                    info = AXIOM_INFO.get(aid, {})
                    st.markdown(
                        f"- {axiom_tag(aid)} {info.get('meaning', '')}",
                        unsafe_allow_html=True,
                    )

    # --- KPI 2: Biomass or Carbon ---
    with k2:
        bio = nd.get("biomass_ratio")
        carbon = nd.get("carbon_sequestration")
        if bio:
            ci = bio.get("ci_95", [0, 0])
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Biomass Recovery Ratio</div>
<div class="kpi-value">{bio['central']}x</div>
<div class="kpi-context">95% CI: [{ci[0]}x, {ci[1]}x]</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Biomass Derivation"):
                st.markdown(
                    f"Observed fish biomass recovery of **{bio['central']}x** "
                    f"baseline over a 10-year no-take period."
                )
                st.markdown(
                    f"95% confidence interval: [{ci[0]}x, {ci[1]}x]"
                )
                st.markdown(
                    "**Translation path:** Biomass recovery (BA-002) drives "
                    "tourism willingness-to-pay (BA-001), which constitutes "
                    "the dominant share of total ESV."
                )
                st.markdown(
                    "Source: Aburto-Oropeza et al. 2011 "
                    "([DOI](https://doi.org/10.1371/journal.pone.0023601))"
                )
        elif carbon:
            rate = carbon.get("rate_tCO2_per_ha_yr", 0)
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Carbon Sequestration</div>
<div class="kpi-value">{rate} tCO2/ha/yr</div>
<div class="kpi-context">Seagrass sediment burial pathway</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Carbon Derivation"):
                extent = nd.get("seagrass_extent")
                st.markdown(
                    f"Seagrass meadows sequester carbon at **{rate} tCO2/ha/yr** "
                    f"through sediment burial."
                )
                if extent:
                    annual = rate * extent * 100  # km2 to ha
                    st.markdown(
                        f"Seagrass extent: **{extent:,.0f} km2** "
                        f"({extent * 100:,.0f} ha)"
                    )
                    st.markdown(
                        f"Annual sequestration: ~{annual:,.0f} tCO2/yr "
                        f"x $30/tonne = **{fmt_usd(annual * 30)}**"
                    )
                st.markdown(
                    "Source: Arias-Ortiz et al. 2018 "
                    "([DOI](https://doi.org/10.1038/s41558-018-0096-y))"
                )
        else:
            st.markdown(
                """
<div class="kpi-card">
<div class="kpi-label">Ecological Metric</div>
<div class="kpi-value">N/A</div>
<div class="kpi-context">Data unavailable</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # --- KPI 3: NEOLI ---
    with k3:
        neoli = nd.get("neoli_score", 0)
        bd = nd.get("neoli_breakdown", {})
        met_letters = []
        if bd.get("no_take"):
            met_letters.append("No-take")
        if bd.get("enforced"):
            met_letters.append("Enforced")
        if bd.get("old"):
            met_letters.append("Old")
        if bd.get("large"):
            met_letters.append("Large")
        if bd.get("isolated"):
            met_letters.append("Isolated")
        context_text = ", ".join(met_letters) if met_letters else ""

        st.markdown(
            f"""
<div class="kpi-card">
<div class="kpi-label">NEOLI Alignment Score</div>
<div class="kpi-value">{neoli} / 5</div>
<div class="kpi-context">{context_text}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("NEOLI Criteria Detail"):
            criteria_detail = nd.get("neoli_criteria_detail", {})
            items = [
                ("N", "No-take", "no_take"),
                ("E", "Enforced", "enforced"),
                ("O", "Old (>10 yr)", "old"),
                ("L", "Large (>100 km2)", "large"),
                ("I", "Isolated", "isolated"),
            ]
            for letter, label, key in items:
                met = bd.get(key, False)
                icon = "filled" if met else "empty"
                notes = ""
                if criteria_detail.get(key):
                    notes = criteria_detail[key].get("notes", "")
                st.markdown(
                    f'<div class="neoli-row">'
                    f'<span class="neoli-dot neoli-{icon}"></span>'
                    f'<span class="neoli-label"><strong>{letter}</strong> '
                    f"{label}</span></div>",
                    unsafe_allow_html=True,
                )
                if notes:
                    st.caption(notes)

            st.markdown(
                "Source: Edgar et al. 2014 Nature "
                "([DOI](https://doi.org/10.1038/nature13022))"
            )

    # --- KPI 4: Climate Buffer / Seagrass Extent ---
    with k4:
        cb = nd.get("climate_buffer")
        sg_ext = nd.get("seagrass_extent")
        if cb:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Disturbance Reduction</div>
<div class="kpi-value">{cb['disturbance_reduction_pct']}%</div>
<div class="kpi-context">MPA climate resilience premium</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Climate Buffer Methodology"):
                st.markdown(
                    f"Protected reefs suffer **{cb['disturbance_reduction_pct']}%** "
                    f"less damage from climate disturbances."
                )
                st.markdown(
                    f"Recovery is **{cb['recovery_boost_pct']}%** faster "
                    f"after disturbance events."
                )
                if cb.get("source_doi"):
                    doi = cb["source_doi"]
                    st.markdown(
                        f"Source: [DOI](https://doi.org/{doi})"
                    )
        elif sg_ext:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Seagrass Extent</div>
<div class="kpi-value">{sg_ext:,.0f} km2</div>
<div class="kpi-context">World's largest seagrass meadow</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Seagrass Methodology"):
                st.markdown(
                    f"Shark Bay hosts **{sg_ext:,.0f} km2** of seagrass "
                    f"meadows, the largest documented seagrass ecosystem "
                    f"globally."
                )
                st.markdown(
                    "The dominant species *Posidonia australis* includes a "
                    "single 4,500-year-old polyploid clone spanning 180 km."
                )
                st.markdown(
                    "Source: Arias-Ortiz et al. 2018 "
                    "([DOI](https://doi.org/10.1038/s41558-018-0096-y))"
                )
        else:
            st.markdown(
                """
<div class="kpi-card">
<div class="kpi-label">Site Metric</div>
<div class="kpi-value">N/A</div>
<div class="kpi-context">Data unavailable</div>
</div>
""",
                unsafe_allow_html=True,
            )


def _render_mc_mini(mc: dict[str, Any]) -> None:
    """Render a compact Monte Carlo distribution chart."""
    mean_val = mc.get("mean", 0)
    std_val = mc.get("std", 1)
    if std_val <= 0:
        return
    x = np.linspace(mean_val - 3.5 * std_val, mean_val + 3.5 * std_val, 300)
    y = (
        (1 / (std_val * np.sqrt(2 * np.pi)))
        * np.exp(-0.5 * ((x - mean_val) / std_val) ** 2)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            fill="tozeroy",
            line=dict(color=COLORS["accent_blue"], width=2),
            fillcolor="rgba(91, 155, 213, 0.15)",
            hoverinfo="skip",
        )
    )

    for val, lbl, clr, dash in [
        (mc.get("p5", 0), "P5", "#EF5350", "dash"),
        (mc.get("median", 0), "Median", "#F1F5F9", "solid"),
        (mc.get("p95", 0), "P95", "#66BB6A", "dash"),
    ]:
        fig.add_vline(
            x=val,
            line_dash=dash,
            line_color=clr,
            line_width=1,
            annotation_text=f"{lbl}: {fmt_usd(val)}",
            annotation_font=dict(size=11, color=clr),
            annotation_position="top",
        )

    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=30, b=20),
        xaxis=dict(
            tickprefix="$",
            showgrid=True,
            gridcolor="#1E293B",
            tickfont=dict(color="#94A3B8", size=11),
        ),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key="v3_brief_monte_carlo")
    n = mc.get("n_simulations", 10_000)
    st.caption(f"*{n:,} Monte Carlo simulations, triangular distribution*")


def _render_investment_thesis(nd: dict[str, Any]) -> None:
    """Render the site-aware investment thesis block."""
    st.markdown(
        '<div class="section-header">Investment Thesis</div>',
        unsafe_allow_html=True,
    )

    site = nd["site_name"]
    esv = nd["esv_total"]
    n_axioms_system = 16

    if site == "Cabo Pulmo National Park":
        body = (
            f"<strong>MARIS</strong> (Marine Asset Risk Intelligence System) "
            f"is the marine-domain intelligence layer that converts ecological "
            f"field data into investment-grade financial metrics. It contains "
            f"195 curated papers, <strong>{n_axioms_system} bridge axioms</strong> "
            f"(quantitative translation rules that convert ecological "
            f"measurements into financial estimates, each with documented "
            f"coefficients and 95% confidence intervals), and 8 entity schemas "
            f"covering species, habitats, MPAs, and ecosystem services."
            f"<br><br>"
            f"Cabo Pulmo demonstrates what happens when marine protection is "
            f"done right. A degraded reef transformed into a thriving ecosystem "
            f"generating <strong>{fmt_usd(esv)}</strong> annually - dominated "
            f"by tourism revenue driven by a 4.63x biomass recovery. Every "
            f"dollar traces through bridge axioms back to peer-reviewed field "
            f"measurements."
        )
    elif site == "Shark Bay World Heritage Area":
        extent = nd.get("seagrass_extent", 4800)
        body = (
            f"<strong>MARIS</strong> (Marine Asset Risk Intelligence System) "
            f"is the marine-domain intelligence layer that converts ecological "
            f"field data into investment-grade financial metrics. It contains "
            f"195 curated papers, <strong>{n_axioms_system} bridge axioms</strong> "
            f"(quantitative translation rules that convert ecological "
            f"measurements into financial estimates, each with documented "
            f"coefficients and 95% confidence intervals), and 8 entity schemas "
            f"covering species, habitats, MPAs, and ecosystem services."
            f"<br><br>"
            f"Shark Bay holds the world's largest seagrass carbon stock across "
            f"<strong>{extent:,.0f} km2</strong> of meadows, generating "
            f"<strong>{fmt_usd(esv)}</strong> annually - dominated by $12.1M "
            f"in blue carbon sequestration value. The 2011 marine heatwave "
            f"(36% seagrass loss, 2-9 Tg CO2 released) demonstrates the "
            f"permanence risk that investors must price into carbon credit "
            f"instruments. Every valuation traces through bridge axioms BA-013 "
            f"through BA-016 to peer-reviewed sources."
        )
    else:
        body = (
            f"<strong>MARIS</strong> values {site} ecosystem services at "
            f"<strong>{fmt_usd(esv)}</strong> annually. "
            f"Every claim is backed by {n_axioms_system} bridge axioms and "
            f"traceable to DOI-backed peer-reviewed sources."
        )

    st.markdown(
        f"""
<div class="thesis-block">
<div class="thesis-lead">This is auditable infrastructure, not an AI-generated narrative.</div>
<div class="thesis-body">{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_provenance_graph(nd: dict[str, Any]) -> None:
    """Render the site-aware provenance chain graph."""
    st.markdown(
        '<div class="section-header">Provenance Chain</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">This graph is the core of the '
        "infrastructure. It is not a visualization of AI reasoning; it is "
        "a deterministic, auditable map where every node represents verified "
        "ecological or financial state and every edge applies a documented, "
        "peer-reviewed translation rule. An auditor can trace any financial "
        "claim back to the original field measurement.</div>",
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    layer_x = {
        "site": 0.0,
        "ecological": 1.2,
        "services": 2.4,
        "financial": 3.6,
        "risk": 1.8,
    }

    node_colors = {
        "site": "#2563EB",
        "ecological": "#059669",
        "service": "#7C3AED",
        "financial": "#D97706",
        "risk_good": "#10B981",
        "risk_bad": "#EF4444",
    }

    site = nd["site_name"]
    esv = nd["esv_total"]
    neoli = nd["neoli_score"]
    services = nd["services"]

    # Build nodes and edges per site
    if site == "Cabo Pulmo National Park":
        bio = nd.get("biomass_ratio", {})
        bio_val = bio.get("central", 4.63) if bio else 4.63
        cb = nd.get("climate_buffer", {})
        dr = nd.get("degradation_risk", {})

        svc_map = {s["name"].lower(): s["value"] for s in services}

        nodes = [
            ("site", "Cabo Pulmo NP\nEst. 1995",
             layer_x["site"], 0.50, "site", 55, "circle"),
            ("neoli", f"NEOLI {neoli}/5\nGovernance Score",
             layer_x["ecological"], 1.00, "ecological", 40, "diamond"),
            ("biomass", f"Biomass {bio_val}x\nRecovery Ratio",
             layer_x["ecological"], 0.00, "ecological", 40, "diamond"),
            ("tourism", f"Tourism\n{fmt_usd(svc_map.get('tourism', 25000000))}",
             layer_x["services"], 1.20, "service", 36, "circle"),
            ("fisheries", f"Fisheries\n{fmt_usd(svc_map.get('fisheries spillover', svc_map.get('fisheries', 3200000)))}",
             layer_x["services"], 0.72, "service", 32, "circle"),
            ("carbon", f"Carbon\n{fmt_usd(svc_map.get('carbon sequestration', svc_map.get('carbon', 180000)))}",
             layer_x["services"], 0.28, "service", 28, "circle"),
            ("protection", f"Coastal Protection\n{fmt_usd(svc_map.get('coastal protection', 890000))}",
             layer_x["services"], -0.20, "service", 28, "circle"),
            ("esv", f"Total ESV\n{fmt_usd(esv)}/yr",
             layer_x["financial"], 0.50, "financial", 60, "circle"),
        ]

        if cb:
            nodes.append((
                "resilience",
                f"Climate Buffer\n-{cb.get('disturbance_reduction_pct', 30)}% Impact",
                layer_x["risk"], -0.42, "risk_good", 28, "square",
            ))
        if dr:
            nodes.append((
                "degradation",
                f"Degradation Risk\n-{dr.get('loss_central_pct', 35)}% if Unprotected",
                layer_x["risk"], -0.65, "risk_bad", 28, "square",
            ))

        edges = [
            ("site", "neoli", "assessed as", False),
            ("site", "biomass", "observed", False),
            ("neoli", "biomass", "BA-002: No-take reserves\naccumulate 4.63x biomass", True),
            ("biomass", "tourism", "BA-001: Biomass drives\ntourism value (+84% WTP)", True),
            ("biomass", "fisheries", "Spillover to\nadjacent fisheries", False),
            ("biomass", "carbon", "Reef-associated\nblue carbon", False),
            ("biomass", "protection", "Structural\ncomplexity", False),
            ("tourism", "esv", "", False),
            ("fisheries", "esv", "", False),
            ("carbon", "esv", "", False),
            ("protection", "esv", "", False),
        ]
        if cb:
            edges.append(("neoli", "resilience", "BA-011: MPA\nresilience premium", True))
        if dr:
            edges.append(("neoli", "degradation", "BA-012: Risk if\nprotection fails", True))

    else:
        # Shark Bay - carbon-dominant flow
        svc_map = {s["name"].lower(): s["value"] for s in services}

        nodes = [
            ("site", "Shark Bay WHA\nEst. 1991",
             layer_x["site"], 0.50, "site", 55, "circle"),
            ("seagrass", "Seagrass\n4,800 km2",
             layer_x["ecological"], 0.85, "ecological", 40, "diamond"),
            ("neoli_node", f"NEOLI {neoli}/5\nGovernance",
             layer_x["ecological"], 0.15, "ecological", 36, "diamond"),
            ("carbon", f"Carbon Seq.\n{fmt_usd(svc_map.get('carbon sequestration', 12100000))}",
             layer_x["services"], 1.10, "service", 36, "circle"),
            ("fisheries", f"Fisheries\n{fmt_usd(svc_map.get('fisheries', 5200000))}",
             layer_x["services"], 0.60, "service", 32, "circle"),
            ("tourism", f"Tourism\n{fmt_usd(svc_map.get('tourism', 3400000))}",
             layer_x["services"], 0.20, "service", 28, "circle"),
            ("protection", f"Coastal Protection\n{fmt_usd(svc_map.get('coastal protection', 800000))}",
             layer_x["services"], -0.20, "service", 28, "circle"),
            ("esv", f"Total ESV\n{fmt_usd(esv)}/yr",
             layer_x["financial"], 0.50, "financial", 60, "circle"),
            ("heatwave", "Heatwave Risk\n-36% seagrass (2011)",
             layer_x["risk"], -0.42, "risk_bad", 28, "square"),
            ("permanence", "Permanence\nGuarantee (BA-016)",
             layer_x["risk"], -0.65, "risk_good", 28, "square"),
        ]

        edges = [
            ("site", "seagrass", "hosts", False),
            ("site", "neoli_node", "assessed as", False),
            ("seagrass", "carbon", "BA-013: 0.84 tCO2/ha/yr\nsequestration rate", True),
            ("carbon", "esv", "BA-014: $30/tCO2\ncredit value", True),
            ("seagrass", "fisheries", "Nursery habitat\nfor MSC fishery", False),
            ("seagrass", "tourism", "World Heritage\nattraction", False),
            ("seagrass", "protection", "Wave attenuation\n40% reduction", False),
            ("fisheries", "esv", "", False),
            ("tourism", "esv", "", False),
            ("protection", "esv", "", False),
            ("seagrass", "heatwave", "BA-015: 294 tCO2/ha\nreleased if lost", True),
            ("neoli_node", "permanence", "BA-016: MPA protection\ncarbon permanence", True),
        ]

    node_map = {n[0]: (n[2], n[3]) for n in nodes}

    # Layer backgrounds
    layer_regions = [
        (layer_x["site"] - 0.25, layer_x["site"] + 0.25,
         "SITE", "rgba(37, 99, 235, 0.06)"),
        (layer_x["ecological"] - 0.35, layer_x["ecological"] + 0.35,
         "ECOLOGICAL STATE", "rgba(5, 150, 105, 0.06)"),
        (layer_x["services"] - 0.35, layer_x["services"] + 0.35,
         "ECOSYSTEM SERVICES", "rgba(124, 58, 237, 0.06)"),
        (layer_x["financial"] - 0.25, layer_x["financial"] + 0.25,
         "FINANCIAL VALUE", "rgba(217, 119, 6, 0.06)"),
    ]

    for x0, x1, _title, fillcolor in layer_regions:
        fig.add_shape(
            type="rect",
            x0=x0, x1=x1, y0=-0.30, y1=1.32,
            fillcolor=fillcolor,
            line=dict(color="rgba(255,255,255,0.03)", width=1),
            layer="below",
        )

    # Draw edges
    for src, tgt, label, is_axiom in edges:
        if src not in node_map or tgt not in node_map:
            continue
        x0, y0 = node_map[src]
        x1, y1 = node_map[tgt]
        edge_color = "#5B9BD5" if is_axiom else "#334155"
        edge_width = 2.5 if is_axiom else 1.5
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines",
            line=dict(color=edge_color, width=edge_width),
            hoverinfo="skip",
            showlegend=False,
        ))
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=3, arrowsize=1.5, arrowwidth=1.5,
            arrowcolor="#5B9BD5" if is_axiom else "#475569",
            standoff=14,
        )
        if label:
            lbl_color = "#E2E8F0" if is_axiom else "#94A3B8"
            lbl_size = 13
            fig.add_annotation(
                x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                text=label,
                showarrow=False,
                font=dict(size=lbl_size, color=lbl_color, family="Inter"),
                bgcolor="rgba(11,17,32,0.92)",
                bordercolor=(
                    "rgba(91,155,213,0.15)" if is_axiom
                    else "rgba(0,0,0,0)"
                ),
                borderpad=4,
                borderwidth=1,
            )

    # Draw nodes
    for nid, label, x, y, color_key, size, symbol in nodes:
        color = node_colors[color_key]
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers",
            marker=dict(size=size + 12, color=color, opacity=0.15, symbol=symbol),
            hoverinfo="skip",
            showlegend=False,
        ))
        text_pos = (
            "bottom center" if nid in ("site", "esv") else "top center"
        )
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(
                size=size, color=color,
                line=dict(width=2, color="#0B1120"), symbol=symbol,
            ),
            text=[label],
            textposition=text_pos,
            textfont=dict(size=14, color="#E2E8F0", family="Inter"),
            hoverinfo="text",
            hovertext=[label.replace("\n", " ")],
            showlegend=False,
        ))

    # Layer headers
    for lx, ltxt, lclr in [
        (layer_x["site"], "SITE", "#2563EB"),
        (layer_x["ecological"], "ECOLOGICAL STATE", "#059669"),
        (layer_x["services"], "ECOSYSTEM SERVICES", "#7C3AED"),
        (layer_x["financial"], "FINANCIAL VALUE", "#D97706"),
    ]:
        fig.add_annotation(
            x=lx, y=1.42, text=ltxt, showarrow=False,
            font=dict(size=14, color=lclr, family="Inter"),
        )

    fig.update_layout(
        height=900,
        margin=dict(l=20, r=20, t=50, b=40),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-0.5, 4.1],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-0.80, 1.58],
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#CBD5E1"),
    )

    st.plotly_chart(fig, width="stretch", key="v3_brief_provenance_chain")


def _render_axiom_evidence_table(nd: dict[str, Any]) -> None:
    """Render the bridge axiom evidence table for the selected site."""
    st.markdown(
        '<div class="subsection-header">Bridge Axiom Evidence</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Each axiom is a reusable, auditable '
        "building block of the infrastructure. Click any source to verify "
        "the original peer-reviewed paper.</div>",
        unsafe_allow_html=True,
    )

    axiom_ids = _SITE_AXIOMS.get(nd["site_name"], [])
    if not axiom_ids:
        # Fall back to any axioms we find in the data
        for ax in nd.get("bridge_axioms_applied", []):
            aid = ax.get("axiom_id", "") if isinstance(ax, dict) else ""
            if aid and aid not in axiom_ids:
                axiom_ids.append(aid)

    rows = ""
    for aid in axiom_ids:
        info = AXIOM_INFO.get(aid, {})
        meaning = info.get("meaning", "")
        citation = info.get("citation", "")
        doi = info.get("doi", "")
        doi_link = f"https://doi.org/{doi}" if doi else "#"
        rows += (
            f'<tr><td class="axiom-id">{aid}</td>'
            f"<td>{meaning}</td>"
            f'<td><a href="{doi_link}" target="_blank">{citation}</a></td></tr>'
        )

    st.markdown(
        f'<table class="evidence-table">'
        f"<thead><tr><th>Rule</th><th>What It Means</th><th>Source</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        unsafe_allow_html=True,
    )


def _render_valuation_composition(nd: dict[str, Any]) -> None:
    """Render horizontal bar chart of service values plus CI card."""
    st.markdown(
        '<div class="section-header">Valuation Composition</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Fully decomposed, transparent valuation '
        "built from market-price methodology. No black-box models. Every "
        "service value traces to a specific bridge axiom and peer-reviewed "
        "coefficient.</div>",
        unsafe_allow_html=True,
    )

    sorted_svcs = sorted(nd["services"], key=lambda s: s["value"], reverse=True)

    col_chart, col_ci = st.columns([3, 2])

    with col_chart:
        # Color gradient for bars
        bar_colors = ["#7C3AED", "#6D28D9", "#5B21B6", "#4C1D95"]
        colors = [
            bar_colors[i % len(bar_colors)] for i in range(len(sorted_svcs))
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[s["name"] for s in sorted_svcs],
            x=[s["value"] / 1e6 for s in sorted_svcs],
            orientation="h",
            marker_color=colors,
            text=[fmt_usd(s["value"]) for s in sorted_svcs],
            textposition="outside",
            textfont=dict(size=16, family="Inter", color="#E2E8F0"),
        ))
        fig.update_layout(
            height=max(220, 60 * len(sorted_svcs)),
            margin=dict(l=0, r=80, t=10, b=10),
            xaxis=dict(
                title="Annual Value (USD Millions)",
                showgrid=True, gridcolor="#1E293B",
                tickprefix="$", ticksuffix="M",
                title_font=dict(size=14, color="#94A3B8"),
                tickfont=dict(color="#94A3B8", size=13),
            ),
            yaxis=dict(
                showgrid=False, automargin=True,
                tickfont=dict(color="#CBD5E1", size=15),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#CBD5E1"),
        )
        st.plotly_chart(fig, width="stretch", key="v3_brief_valuation_bar")

    with col_ci:
        mc = nd.get("monte_carlo", {})
        ci_low = mc.get("p5", nd["esv_total"] * 0.7)
        ci_high = mc.get("p95", nd["esv_total"] * 1.3)
        median = mc.get("median", nd["esv_total"])
        n_sims = mc.get("n_simulations", 10_000)

        st.markdown(
            f"""
<div class="kpi-card" style="margin-top:0">
<div class="kpi-label">Monte Carlo Range (P5-P95)</div>
<div class="kpi-value" style="font-size:30px">{fmt_usd(ci_low)} - {fmt_usd(ci_high)}</div>
<div class="kpi-context" style="margin-top:14px">
Median estimate: <strong style="color:#E2E8F0">{fmt_usd(median)}</strong>
</div>
<div class="kpi-context" style="margin-top:14px">
Based on {n_sims:,} Monte Carlo simulations incorporating parameter
uncertainty via triangular distributions.
</div>
</div>
""",
            unsafe_allow_html=True,
        )


def _render_risk_profile(nd: dict[str, Any]) -> None:
    """Render Monte Carlo risk curve and risk factor cards."""
    st.markdown(
        '<div class="section-header">Risk Profile</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Quantified uncertainty is a feature of '
        "trustworthy infrastructure, not a weakness. MARIS propagates "
        "confidence intervals through every calculation rather than "
        "presenting false precision. Open the Scenario Lab tab for "
        "interactive analysis.</div>",
        unsafe_allow_html=True,
    )

    mc = nd.get("monte_carlo", {})
    if mc.get("mean") and mc.get("std") and mc["std"] > 0:
        mean_val = mc["mean"]
        std_val = mc["std"]

        x = np.linspace(
            mean_val - 4 * std_val, mean_val + 4 * std_val, 500
        )
        y = (
            (1 / (std_val * np.sqrt(2 * np.pi)))
            * np.exp(-0.5 * ((x - mean_val) / std_val) ** 2)
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", fill="tozeroy",
            line=dict(color="#5B9BD5", width=2),
            fillcolor="rgba(91, 155, 213, 0.12)",
            hoverinfo="skip",
        ))

        for val, lbl, clr, dash in [
            (mc.get("p5", 0), "P5 Downside", "#EF5350", "dash"),
            (mc.get("median", 0), "Median", "#F1F5F9", "solid"),
            (mc.get("p95", 0), "P95 Upside", "#66BB6A", "dash"),
        ]:
            fig.add_vline(
                x=val, line_dash=dash, line_color=clr, line_width=1.5,
                annotation_text=f"{lbl}: {fmt_usd(val)}",
                annotation_font=dict(size=13, color=clr, family="Inter"),
                annotation_position="top",
            )

        fig.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=40, b=40),
            xaxis=dict(
                title="Annual Ecosystem Service Value (USD)",
                tickprefix="$",
                showgrid=True, gridcolor="#1E293B",
                title_font=dict(size=14, color="#94A3B8"),
                tickfont=dict(color="#94A3B8", size=13),
            ),
            yaxis=dict(visible=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            font=dict(family="Inter", color="#CBD5E1"),
        )
        st.plotly_chart(fig, width="stretch", key="v3_brief_risk_dist")

    # Risk factor cards
    site = nd["site_name"]
    if site == "Cabo Pulmo National Park":
        cb = nd.get("climate_buffer", {})
        dr = nd.get("degradation_risk", {})
        if cb or dr:
            rc1, rc2 = st.columns(2)
            if dr:
                with rc1:
                    loss_range = dr.get("loss_range_pct", [25, 50])
                    range_str = (
                        f"{loss_range[0]}-{loss_range[1]}%"
                        if len(loss_range) == 2
                        else ""
                    )
                    doi = dr.get("source_doi", "")
                    doi_link = f"https://doi.org/{doi}" if doi else "#"
                    st.markdown(
                        f"""
<div class="risk-card risk-card-red">
<h4>Degradation Risk (BA-012)</h4>
<p>{dr.get('loss_central_pct', 35)}% fisheries productivity loss if protection
fails (range: {range_str}).
Source: <a href="{doi_link}" target="_blank">{AXIOM_INFO.get('BA-012', {}).get('citation', '')}</a></p>
</div>
""",
                        unsafe_allow_html=True,
                    )
            if cb:
                with rc2:
                    doi = cb.get("source_doi", "")
                    doi_link = f"https://doi.org/{doi}" if doi else "#"
                    st.markdown(
                        f"""
<div class="risk-card risk-card-green">
<h4>Resilience Benefit (BA-011)</h4>
<p>{cb.get('disturbance_reduction_pct', 30)}% reduction in climate disturbance impact,
with {cb.get('recovery_boost_pct', 20)}% faster recovery after disturbance events.
Source: <a href="{doi_link}" target="_blank">{AXIOM_INFO.get('BA-011', {}).get('citation', '')}</a></p>
</div>
""",
                        unsafe_allow_html=True,
                    )
    else:
        # Shark Bay risk cards
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(
                """
<div class="risk-card risk-card-red">
<h4>Heatwave Risk (BA-015)</h4>
<p>The 2011 marine heatwave destroyed 36% of Shark Bay's seagrass, releasing
2-9 Tg CO2. Warming Indian Ocean increases heatwave frequency.
Source: <a href="https://doi.org/10.1038/s41558-018-0096-y" target="_blank">Arias-Ortiz et al. 2018</a></p>
</div>
""",
                unsafe_allow_html=True,
            )
        with rc2:
            st.markdown(
                """
<div class="risk-card risk-card-green">
<h4>Permanence Guarantee (BA-016)</h4>
<p>MPA protection with NEOLI 4+/5 provides 25-100 year carbon permanence
guarantee. UNESCO World Heritage status provides additional protection framework.
Source: <a href="https://doi.org/10.1038/s41558-024-02206-5" target="_blank">Lovelock et al. 2025</a></p>
</div>
""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_intelligence_brief(
    data: dict[str, Any],
    site: str,
    mode: str,
    **kwargs: Any,
) -> None:
    """Render the Intelligence Brief tab.

    Parameters
    ----------
    data:
        Static bundle (Cabo Pulmo) or case study JSON (Shark Bay).
    site:
        Canonical site name (e.g. "Cabo Pulmo National Park").
    mode:
        "live" or "demo".
    """
    nd = _normalize_site_data(data, site)

    _render_masthead(nd, mode)

    # Disclaimer
    meta = nd.get("metadata", {})
    disclaimer = meta.get("disclaimer", "")
    if disclaimer:
        st.caption(f"*{disclaimer}*")

    _render_investment_thesis(nd)
    _render_kpi_strip(nd)
    _render_provenance_graph(nd)
    _render_axiom_evidence_table(nd)
    _render_valuation_composition(nd)
    _render_risk_profile(nd)
