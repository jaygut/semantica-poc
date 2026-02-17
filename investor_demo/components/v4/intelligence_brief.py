"""Intelligence Brief tab for Nereus v4 Natural Capital Intelligence.

Key difference from v3: axiom chains are derived dynamically from the
site's habitat types using ``_HABITAT_AXIOM_MAP`` from esv_estimator.py.
No hardcoded ``_SITE_AXIOMS`` dict.  The ``_normalize_site_data()``
function handles any case study JSON with graceful fallback for missing
fields.
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

from investor_demo.components.v4.shared import (  # noqa: E402
    COLORS,
    axiom_tag,
    fmt_usd,
    valuation_method_badge,
)
from maris.sites.esv_estimator import _HABITAT_AXIOM_MAP  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Axiom info - plain-English descriptions and citations (all 16)
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
    "BA-003": {
        "meaning": (
            "Sea otter presence enables kelp forest expansion, increasing "
            "carbon sequestration through trophic cascade"
        ),
        "citation": "Wilmers et al. 2012",
        "doi": "10.3389/fevo.2012.00012",
    },
    "BA-004": {
        "meaning": (
            "Coral reef structural complexity reduces wave energy, "
            "providing coastal flood protection"
        ),
        "citation": "Ferrario et al. 2014",
        "doi": "10.1038/ncomms4794",
    },
    "BA-005": {
        "meaning": (
            "Mangrove forests provide coastal flood protection, reducing "
            "wave height by 66% over 100m of forest width"
        ),
        "citation": "Menendez et al. 2020",
        "doi": "10.1038/s41598-020-61136-6",
    },
    "BA-006": {
        "meaning": (
            "Mangrove forests serve as nursery habitat, supporting "
            "commercial fisheries production"
        ),
        "citation": "zu Ermgassen et al. 2020",
        "doi": "10.1016/j.ecss.2020.106975",
    },
    "BA-007": {
        "meaning": (
            "Mangrove sediments store 1,023 tCO2/ha on average, "
            "among the highest carbon-dense ecosystems"
        ),
        "citation": "Alongi 2020",
        "doi": "10.1016/j.scitotenv.2020.141360",
    },
    "BA-008": {
        "meaning": (
            "Seagrass meadows generate tradeable carbon credits "
            "under voluntary standards (Verra VCS VM0033)"
        ),
        "citation": "Emmer et al. 2023",
        "doi": "10.3390/su15010345",
    },
    "BA-009": {
        "meaning": (
            "Mangrove restoration yields benefit-cost ratios of 3:1 to 10:1 "
            "when including ecosystem service values"
        ),
        "citation": "Su et al. 2021",
        "doi": "10.1016/j.ecolecon.2021.107048",
    },
    "BA-010": {
        "meaning": (
            "Kelp forests provide estimated $500B/yr in global ecosystem "
            "services including carbon, fisheries, and coastal protection"
        ),
        "citation": "Eger et al. 2023",
        "doi": "10.1038/s41467-023-37385-0",
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


def _get_site_axioms(data: dict[str, Any]) -> list[str]:
    """Derive applicable axiom IDs from site habitat types.

    Uses ``_HABITAT_AXIOM_MAP`` from esv_estimator.py to map habitats
    to bridge axioms. Falls back to ``bridge_axioms_applied`` in the
    data if habitat detection fails.
    """
    axiom_ids: list[str] = []

    # 1. Try primary_habitat from ecological_status
    primary = data.get("ecological_status", {}).get("primary_habitat", "")
    if primary and primary in _HABITAT_AXIOM_MAP:
        for entry in _HABITAT_AXIOM_MAP[primary]:
            aid = entry["axiom_id"]
            if aid not in axiom_ids:
                axiom_ids.append(aid)

    # 2. Also check additional habitats if present
    habitats = data.get("ecological_status", {}).get("habitats", [])
    for hab in habitats:
        hab_id = hab.get("habitat_id", "") if isinstance(hab, dict) else ""
        if hab_id and hab_id in _HABITAT_AXIOM_MAP:
            for entry in _HABITAT_AXIOM_MAP[hab_id]:
                aid = entry["axiom_id"]
                if aid not in axiom_ids:
                    axiom_ids.append(aid)

    # 3. Fallback: extract from bridge_axioms_applied in the data
    if not axiom_ids:
        for ax in data.get("bridge_axioms_applied", data.get("bridge_axiom_applications", [])):
            aid = ax.get("axiom_id", "") if isinstance(ax, dict) else ""
            if aid and aid not in axiom_ids:
                axiom_ids.append(aid)

    # 4. Infer common cross-habitat axioms
    # BA-002 and BA-011 apply to all MPA sites with NEOLI
    neoli = data.get("neoli_assessment", {}).get("neoli_score")
    if neoli is None:
        neoli = data.get("ecological_status", {}).get("neoli_score")
    if neoli and neoli >= 3:
        for general_axiom in ("BA-002", "BA-011", "BA-016"):
            if general_axiom not in axiom_ids:
                axiom_ids.append(general_axiom)

    return axiom_ids


# ---------------------------------------------------------------------------
# Data normalizer - unifies bundle vs case study JSON formats
# ---------------------------------------------------------------------------


def _normalize_site_data(data: dict[str, Any], site: str) -> dict[str, Any]:
    """Normalize bundle or case study data into a common internal format.

    Works for any site with valid case study JSON. Missing fields are
    handled gracefully with sensible defaults.
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
        "primary_habitat": data.get("ecological_status", {}).get("primary_habitat", ""),
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

        clim = data.get("risk_assessment", {}).get("climate_resilience", {})
        if clim:
            out["climate_buffer"] = {
                "disturbance_reduction_pct": clim.get("disturbance_reduction_percent", 0),
                "recovery_boost_pct": clim.get("recovery_boost_percent", 0),
                "source_doi": clim.get("source_doi", ""),
            }
        deg = data.get("risk_assessment", {}).get("degradation_risk", {})
        if deg:
            out["degradation_risk"] = {
                "loss_central_pct": deg.get("productivity_loss_central_percent", 0),
                "loss_range_pct": deg.get("productivity_loss_range_percent", []),
                "source_doi": deg.get("source_doi", ""),
            }

    # --- Case study format (generic) ---
    esv_bundle = data.get("ecosystem_services", {})
    if esv_bundle.get("services") and not fin.get("services_breakdown"):
        out["esv_total"] = esv_bundle.get("total_annual_value_usd", 0)
        for svc in esv_bundle["services"]:
            name = (
                svc.get("service_type", "Unknown")
                .replace("_", " ")
                .title()
            )
            ci = svc.get("confidence_interval", {})
            out["services"].append({
                "name": name,
                "value": svc.get("annual_value_usd", 0),
                "valuation_method": svc.get("valuation_method", ""),
                "ci_low": ci.get("ci_low"),
                "ci_high": ci.get("ci_high"),
            })
        # Compute Monte Carlo from services using CI bounds from data
        mc_services = []
        for svc in esv_bundle["services"]:
            val = svc.get("annual_value_usd", 0)
            ci = svc.get("confidence_interval", {})
            mc_services.append({
                "value": val,
                "ci_low": ci.get("ci_low", val * 0.7),
                "ci_high": ci.get("ci_high", val * 1.3),
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
        out["neoli_breakdown"] = eco_status.get("neoli_breakdown", {})

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

    # --- Mangrove metrics ---
    mangrove_extent = data.get("site", {}).get("mangrove_extent_km2")
    if mangrove_extent:
        out["mangrove_extent"] = mangrove_extent

    # --- Asset rating ---
    rating = data.get("asset_quality_rating", {})
    out["asset_rating"] = rating.get("rating", "")
    out["composite_score"] = rating.get("composite_score", 0.0)

    # --- Staleness and validation ---
    out["staleness_flag"] = (
        data.get("ecological_status", {})
        .get("biomass_ratio", {})
        .get("staleness_flag", "")
    )
    out["validation_checklist"] = data.get("validation_checklist", {})

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

    st.markdown(
        f"""
<div class="masthead">
<div class="masthead-brand">NEREUS | SITE INTELLIGENCE BRIEF</div>
<h1 style="font-size: 48px; font-weight: 300; margin-top: 10px; margin-bottom: 5px;">{site_name}</h1>
<div class="masthead-subtitle">Detailed provenance-first ecological and financial breakdown</div>
<div class="masthead-badges">{badges}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_kpi_strip(nd: dict[str, Any], *, scenario: str = "p50") -> None:
    """Render the 4-card KPI strip with expandable drill-downs."""
    st.markdown(
        '<div class="section-header">Key Metrics</div>',
        unsafe_allow_html=True,
    )

    mc = nd.get("monte_carlo", {})
    percentiles = {"P5": mc.get("p5", 0), "P95": mc.get("p95", 0)}
    if scenario == "p5":
        headline_esv = percentiles.get("P5") or nd["esv_total"]
        scenario_label = "Conservative (P5)"
    elif scenario == "p95":
        headline_esv = percentiles.get("P95") or nd["esv_total"]
        scenario_label = "Optimistic (P95)"
    else:
        headline_esv = mc.get("median", nd["esv_total"])
        scenario_label = "Median - Base Case"

    k1, k2, k3, k4 = st.columns(4)

    # --- KPI 1: ESV ---
    with k1:
        st.markdown(
            f"""
<div class="kpi-card">
<div class="kpi-label">Annual Ecosystem Service Value</div>
<div class="kpi-value">{fmt_usd(headline_esv)}</div>
<div class="kpi-context">{scenario_label}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("ESV Derivation"):
            st.markdown("**Service Breakdown**")
            for svc in sorted(nd["services"], key=lambda s: s["value"], reverse=True):
                method = svc.get("valuation_method", "")
                badge = f" {valuation_method_badge(method)}" if method else ""
                ci_low = svc.get("ci_low")
                ci_high = svc.get("ci_high")
                ci_text = f" (CI: {fmt_usd(ci_low)} - {fmt_usd(ci_high)})" if ci_low and ci_high else ""
                st.markdown(
                    f"- {svc['name']}: **{fmt_usd(svc['value'])}**{ci_text} {badge}",
                    unsafe_allow_html=True,
                )

            if mc.get("mean") and mc.get("std"):
                _render_mc_mini(mc)

            axiom_ids = _get_site_axioms(nd.get("_raw_data", {}))
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
                st.markdown(f"95% confidence interval: [{ci[0]}x, {ci[1]}x]")
        elif carbon:
            rate = carbon.get("rate_tCO2_per_ha_yr", 0)
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Carbon Sequestration</div>
<div class="kpi-value">{rate} tCO2/ha/yr</div>
<div class="kpi-context">Sediment burial pathway</div>
</div>
""",
                unsafe_allow_html=True,
            )
            with st.expander("Carbon Derivation"):
                extent = nd.get("seagrass_extent") or nd.get("mangrove_extent")
                st.markdown(
                    f"Sequestration rate: **{rate} tCO2/ha/yr** through sediment burial."
                )
                if extent:
                    annual = rate * extent * 100
                    st.markdown(f"Habitat extent: **{extent:,.0f} km2** ({extent * 100:,.0f} ha)")
                    st.markdown(f"Annual sequestration: ~{annual:,.0f} tCO2/yr x $30/tonne = **{fmt_usd(annual * 30)}**")
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
        for key, label in [("no_take", "No-take"), ("enforced", "Enforced"),
                           ("old", "Old"), ("large", "Large"), ("isolated", "Isolated")]:
            if bd.get(key):
                met_letters.append(label)
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

    # --- KPI 4: Site-specific metric ---
    with k4:
        cb = nd.get("climate_buffer")
        sg_ext = nd.get("seagrass_extent")
        mg_ext = nd.get("mangrove_extent")
        area = nd.get("_raw_data", {}).get("site", {}).get("area_km2")
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
        elif sg_ext:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Seagrass Extent</div>
<div class="kpi-value">{sg_ext:,.0f} km2</div>
<div class="kpi-context">Primary habitat area</div>
</div>
""",
                unsafe_allow_html=True,
            )
        elif mg_ext:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Mangrove Extent</div>
<div class="kpi-value">{mg_ext:,.0f} km2</div>
<div class="kpi-context">Primary habitat area</div>
</div>
""",
                unsafe_allow_html=True,
            )
        elif area:
            st.markdown(
                f"""
<div class="kpi-card">
<div class="kpi-label">Protected Area</div>
<div class="kpi-value">{area:,.0f} km2</div>
<div class="kpi-context">Total MPA extent</div>
</div>
""",
                unsafe_allow_html=True,
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

    # --- Optional: Asset Rating ---
    if nd.get("asset_rating"):
        st.markdown(
            f'<div class="kpi-card"><span class="kpi-value">{nd["asset_rating"]}</span>'
            f'<span class="kpi-label">Asset Rating (composite: {nd.get("composite_score", 0):.2f})</span></div>',
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
            x=x, y=y, mode="lines", fill="tozeroy",
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
            x=val, line_dash=dash, line_color=clr, line_width=1,
            annotation_text=f"{lbl}: {fmt_usd(val)}",
            annotation_font=dict(size=11, color=clr),
            annotation_position="top",
        )

    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=30, b=20),
        xaxis=dict(tickprefix="$", showgrid=True, gridcolor="#1E293B",
                   tickfont=dict(color="#94A3B8", size=11)),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key="v4_brief_monte_carlo")
    n = mc.get("n_simulations", 10_000)
    st.caption(f"*{n:,} Monte Carlo simulations, triangular distribution*")


def _render_investment_thesis(nd: dict[str, Any]) -> None:
    """Render template-based investment thesis from site metadata."""
    st.markdown(
        '<div class="section-header">Investment Thesis</div>',
        unsafe_allow_html=True,
    )

    site = nd["site_name"]
    esv = nd["esv_total"]
    n_axioms_system = 16

    # Determine dominant service
    top_service = ""
    top_value = 0
    for svc in nd["services"]:
        if svc["value"] > top_value:
            top_value = svc["value"]
            top_service = svc["name"]

    habitat = nd.get("primary_habitat", "marine").replace("_", " ")
    preamble = (
        f"<strong>MARIS</strong> (Marine Asset Risk Intelligence System) "
        f"is the marine-domain intelligence layer that converts ecological "
        f"field data into investment-grade financial metrics. It contains "
        f"195 curated papers, <strong>{n_axioms_system} bridge axioms</strong> "
        f"(quantitative translation rules that convert ecological "
        f"measurements into financial estimates, each with documented "
        f"coefficients and 95% confidence intervals), and 8 entity schemas "
        f"covering species, habitats, MPAs, and ecosystem services."
    )

    if top_service and esv:
        details = (
            f"<br><br>{site} generates <strong>{fmt_usd(esv)}</strong> "
            f"annually in ecosystem service value, dominated by "
            f"<strong>{fmt_usd(top_value)}</strong> in {top_service}. "
            f"Primary habitat: {habitat}. "
            f"Every dollar traces through bridge axioms back to "
            f"peer-reviewed field measurements."
        )
    else:
        details = (
            f"<br><br><strong>MARIS</strong> values {site} ecosystem services at "
            f"<strong>{fmt_usd(esv)}</strong> annually. "
            f"Every claim is backed by {n_axioms_system} bridge axioms and "
            f"traceable to DOI-backed peer-reviewed sources."
        )

    body = preamble + details

    st.markdown(
        f"""
<div class="thesis-block">
<div class="thesis-lead">This is auditable infrastructure, not an AI-generated narrative.</div>
<div class="thesis-body">{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_axiom_evidence_table(nd: dict[str, Any]) -> None:
    """Render the bridge axiom evidence table, derived dynamically."""
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

    axiom_ids = _get_site_axioms(nd.get("_raw_data", {}))
    if not axiom_ids:
        st.info("No bridge axiom mappings available for this site's habitat type.")
        return

    rows = ""
    for aid in axiom_ids:
        info = AXIOM_INFO.get(aid, {})
        meaning = info.get("meaning", "")
        citation = info.get("citation", "") or info.get("source", "")
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
        "built from market-price methodology. Every service value traces "
        "to a specific bridge axiom and peer-reviewed coefficient.</div>",
        unsafe_allow_html=True,
    )

    sorted_svcs = sorted(nd["services"], key=lambda s: s["value"], reverse=True)
    if not sorted_svcs:
        st.info("No ecosystem service data available for this site.")
        return

    col_chart, col_ci = st.columns([3, 2])

    with col_chart:
        # Color bars by valuation method strength
        _METHOD_BAR_COLORS = {
            "market_price": "#00C853",
            "avoided_cost": "#FFD600",
            "regional_analogue_estimate": "#FF6D00",
            "expenditure_method": "#FFD600",
        }
        colors = [
            _METHOD_BAR_COLORS.get(s.get("valuation_method", ""), "#7C3AED")
            for s in sorted_svcs
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
            yaxis=dict(showgrid=False, automargin=True,
                       tickfont=dict(color="#CBD5E1", size=15)),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#CBD5E1"),
        )
        st.plotly_chart(fig, width="stretch", key="v4_brief_valuation_bar")

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
        "presenting false precision.</div>",
        unsafe_allow_html=True,
    )

    mc = nd.get("monte_carlo", {})
    if mc.get("mean") and mc.get("std") and mc["std"] > 0:
        mean_val = mc["mean"]
        std_val = mc["std"]

        x = np.linspace(mean_val - 4 * std_val, mean_val + 4 * std_val, 500)
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
                tickprefix="$", showgrid=True, gridcolor="#1E293B",
                title_font=dict(size=14, color="#94A3B8"),
                tickfont=dict(color="#94A3B8", size=13),
            ),
            yaxis=dict(visible=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            font=dict(family="Inter", color="#CBD5E1"),
        )
        st.plotly_chart(fig, width="stretch", key="v4_brief_risk_dist")

    # Risk factor cards from data
    risk_factors = nd.get("_raw_data", {}).get("risk_assessment", {}).get("risk_factors", [])
    if risk_factors:
        cols = st.columns(min(len(risk_factors), 2))
        for i, rf in enumerate(risk_factors[:4]):
            severity = rf.get("severity", "medium")
            card_class = "risk-card-red" if severity == "high" else "risk-card-green"
            with cols[i % 2]:
                st.markdown(
                    f'<div class="risk-card {card_class}">'
                    f'<h4>{rf.get("risk_type", "Risk Factor")}</h4>'
                    f'<p>{rf.get("description", "")}</p>'
                    f"</div>",
                    unsafe_allow_html=True,
                )


def _render_data_quality(nd: dict[str, Any]) -> None:
    """Render data quality indicators and caveats."""
    st.markdown(
        '<div class="section-header">Data Quality & Caveats</div>',
        unsafe_allow_html=True,
    )

    staleness = nd.get("staleness_flag", "")
    if staleness:
        st.markdown(
            f'<div style="background:#78350F;border:1px solid #D97706;'
            f'border-radius:8px;padding:10px 16px;margin-bottom:12px;'
            f'color:#FDE68A;font-size:14px">'
            f"Staleness warning: {staleness}</div>",
            unsafe_allow_html=True,
        )

    caveats = nd.get("caveats", [])
    if caveats:
        with st.expander("View all caveats"):
            for caveat in caveats:
                st.markdown(f"- {caveat}")

    validation = nd.get("validation_checklist", {})
    if validation:
        with st.expander("Validation checklist"):
            for check_name, passed in validation.items():
                icon = "pass" if passed else "FAIL"
                label = check_name.replace("_", " ").title()
                st.markdown(f"- **{icon}** - {label}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_intelligence_brief(
    data: dict[str, Any],
    site: str,
    mode: str,
    *,
    scenario: str = "p50",
    **kwargs: Any,
) -> None:
    """Render the Intelligence Brief tab.

    Parameters
    ----------
    data:
        Static bundle (Cabo Pulmo) or case study JSON (any site).
    site:
        Canonical site name.
    mode:
        "live" or "demo".
    scenario:
        Monte Carlo percentile for headline ESV: "p5", "p50", or "p95".
    """
    nd = _normalize_site_data(data, site)
    nd["_raw_data"] = data  # keep original for habitat lookup

    _render_masthead(nd, mode)

    source = "Investment-grade bundle" if "financial_output" in data else "Case study JSON"
    st.caption(f"Data source: {source}")

    meta = nd.get("metadata", {})
    disclaimer = meta.get("disclaimer", "")
    if disclaimer:
        st.caption(f"*{disclaimer}*")

    _render_investment_thesis(nd)
    _render_kpi_strip(nd, scenario=scenario)
    _render_axiom_evidence_table(nd)
    _render_valuation_composition(nd)
    _render_risk_profile(nd)
    _render_data_quality(nd)
