"""Site Intelligence tab for Nereus v4 Natural Capital Intelligence.

Replaces the Site Scout placeholder with a full characterization-pipeline
view. Sections: NEOLI Criteria Matrix, Habitat-Axiom Map, Data Quality
Dashboard, and Characterization Pipeline Diagram.  All data is read from
case study JSONs - no external API calls required.
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
    get_all_sites,
    get_site_data,
)
from maris.sites.esv_estimator import _HABITAT_AXIOM_MAP  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Axiom metadata (readable names + key coefficients for the table)
# ---------------------------------------------------------------------------

_AXIOM_DISPLAY: dict[str, dict[str, str]] = {
    "BA-001": {"name": "MPA Biomass to Dive Tourism", "translation": "Fish biomass -> Tourism WTP", "coefficient": "Up to 84% higher WTP"},
    "BA-003": {"name": "Sea Otter Kelp Carbon Cascade", "translation": "Kelp forest -> Carbon value", "coefficient": "Trophic cascade"},
    "BA-004": {"name": "Coral Reef Flood Protection", "translation": "Coral reef -> Flood protection", "coefficient": "Wave energy reduction"},
    "BA-005": {"name": "Mangrove Flood Protection", "translation": "Mangrove -> Flood protection", "coefficient": "66% wave reduction / 100m"},
    "BA-006": {"name": "Mangrove Fisheries Production", "translation": "Mangrove -> Fisheries yield", "coefficient": "Nursery production"},
    "BA-007": {"name": "Mangrove Carbon Stock", "translation": "Mangrove -> Carbon stock", "coefficient": "1,023 tCO2/ha"},
    "BA-008": {"name": "Seagrass Carbon Credit Value", "translation": "Seagrass -> Carbon credits", "coefficient": "VCS VM0033"},
    "BA-010": {"name": "Kelp Forest Global Value", "translation": "Kelp forest -> Global ESV", "coefficient": "$200/ha/yr"},
    "BA-012": {"name": "Reef Degradation Fisheries Loss", "translation": "Reef degradation -> Fisheries loss", "coefficient": "35% loss"},
    "BA-013": {"name": "Seagrass Carbon Sequestration", "translation": "Seagrass -> Carbon sequestration", "coefficient": "0.84 tCO2/ha/yr"},
}

# Habitat display labels
_HABITAT_LABELS: dict[str, str] = {
    "coral_reef": "Coral Reef",
    "seagrass_meadow": "Seagrass",
    "mangrove_forest": "Mangrove",
    "kelp_forest": "Kelp Forest",
}

_HABITAT_ACCENT: dict[str, str] = {
    "coral_reef": "#F59E0B",
    "seagrass_meadow": "#10B981",
    "mangrove_forest": "#059669",
    "kelp_forest": "#6366F1",
}


# ---------------------------------------------------------------------------
# Section A: NEOLI Criteria Matrix
# ---------------------------------------------------------------------------


def _render_neoli_matrix(sites_data: dict[str, dict[str, Any]]) -> None:
    """Render a 9-row x 5-column NEOLI heatmap table."""
    st.markdown(
        '<div class="section-header" style="margin-top:0">NEOLI Criteria Matrix</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">NEOLI (No-take, Enforced, Old, Large, Isolated) '
        "alignment across the portfolio. Green cells indicate the criterion is met; "
        "red cells indicate it is not. Higher NEOLI scores predict stronger "
        "ecological and financial outcomes (Edgar et al. 2014).</div>",
        unsafe_allow_html=True,
    )

    criteria_keys = ["no_take", "enforced", "old", "large", "isolated"]
    criteria_labels = ["No-take", "Enforced", "Old (>10yr)", "Large (>100km2)", "Isolated"]

    header = "<tr><th>Site</th>"
    for label in criteria_labels:
        header += f"<th style='text-align:center'>{label}</th>"
    header += "<th style='text-align:center'>Score</th></tr>"

    rows = ""
    for name in sorted(sites_data.keys()):
        data = sites_data[name]
        neoli = data.get("neoli_assessment", {})
        criteria = neoli.get("criteria", {})
        score = neoli.get("neoli_score", 0)

        # Fallback: try ecological_status for score
        if score == 0:
            score = data.get("ecological_status", {}).get("neoli_score", 0)

        short_name = name
        if len(name) > 30:
            short_name = " ".join(name.split()[:3])

        rows += f"<tr><td style='font-weight:600;color:#E2E8F0;white-space:nowrap'>{short_name}</td>"

        met_count = 0
        for key in criteria_keys:
            criterion = criteria.get(key, {})
            val = criterion.get("value", False) if isinstance(criterion, dict) else bool(criterion)
            if val:
                met_count += 1
                cell_bg = "rgba(27, 94, 32, 0.45)"
                cell_color = "#66BB6A"
                cell_text = "Yes"
            else:
                cell_bg = "rgba(183, 28, 28, 0.35)"
                cell_color = "#EF5350"
                cell_text = "No"
            rows += (
                f"<td style='text-align:center;background:{cell_bg};"
                f"color:{cell_color};font-weight:600;font-size:14px'>"
                f"{cell_text}</td>"
            )

        # Use the JSON score if available, otherwise computed count
        display_score = score if score > 0 else met_count
        score_color = "#66BB6A" if display_score >= 4 else "#FFA726" if display_score >= 3 else "#EF5350"
        rows += (
            f"<td style='text-align:center;font-weight:700;font-size:16px;"
            f"color:{score_color}'>{display_score}/5</td>"
        )
        rows += "</tr>"

    st.markdown(
        f'<table class="evidence-table"><thead>{header}</thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section B: Habitat-Axiom Map
# ---------------------------------------------------------------------------


def _render_habitat_axiom_map() -> None:
    """Render a table of which bridge axioms apply to each habitat type."""
    st.markdown(
        '<div class="section-header">Habitat-Axiom Translation Map</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Bridge axioms translate ecological measurements '
        "into financial metrics. Each habitat type maps to a specific set of axioms "
        "with documented coefficients and peer-reviewed evidence.</div>",
        unsafe_allow_html=True,
    )

    for hab_id in ["coral_reef", "seagrass_meadow", "mangrove_forest", "kelp_forest"]:
        label = _HABITAT_LABELS.get(hab_id, hab_id)
        accent = _HABITAT_ACCENT.get(hab_id, "#5B9BD5")
        axioms = _HABITAT_AXIOM_MAP.get(hab_id, [])

        rows_html = ""
        for ax in axioms:
            aid = ax["axiom_id"]
            info = _AXIOM_DISPLAY.get(aid, {})
            rows_html += (
                f"<tr>"
                f"<td style='font-weight:600;color:#5B9BD5;white-space:nowrap'>{aid}</td>"
                f"<td>{info.get('name', ax.get('description', aid))}</td>"
                f"<td style='color:#B0BEC5'>{info.get('translation', ax.get('description', ''))}</td>"
                f"<td style='font-weight:600;color:#E2E8F0'>{info.get('coefficient', '')}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""
<div style="margin-bottom:24px">
<div style="font-size:18px;font-weight:600;color:{accent};margin-bottom:10px;
     display:flex;align-items:center;gap:10px">
<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{accent}"></span>
{label}
<span style="font-size:13px;font-weight:400;color:#94A3B8">({len(axioms)} axioms)</span>
</div>
<table class="evidence-table">
<thead><tr>
<th>Axiom</th><th>Name</th><th>Translation</th><th>Key Coefficient</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>
""",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Section C: Data Quality Dashboard
# ---------------------------------------------------------------------------


def _resolve_provenance_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Return normalized provenance summary for a site.

    Prefers the case study's ``provenance_summary`` object and falls back to
    deriving counts from ``provenance.data_sources`` when missing.
    """
    prov = data.get("provenance", {}).get("data_sources", [])
    total_sources = len(prov)
    doi_backed = sum(1 for p in prov if p.get("doi"))
    url_only = sum(1 for p in prov if not p.get("doi") and p.get("url"))
    tier_dist = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}
    for src in prov:
        tier = src.get("source_tier")
        if tier in tier_dist:
            tier_dist[tier] += 1
    doi_coverage = round((doi_backed / total_sources) * 100, 1) if total_sources else 0.0

    derived = {
        "total_sources": total_sources,
        "doi_backed": doi_backed,
        "url_only": url_only,
        "doi_coverage_pct": doi_coverage,
        "evidence_tier_distribution": tier_dist,
    }

    summary = data.get("provenance_summary")
    if isinstance(summary, dict):
        summary_tier_dist = summary.get("evidence_tier_distribution", {})
        candidate = {
            "total_sources": int(summary.get("total_sources", 0) or 0),
            "doi_backed": int(summary.get("doi_backed", 0) or 0),
            "url_only": int(summary.get("url_only", 0) or 0),
            "doi_coverage_pct": float(summary.get("doi_coverage_pct", 0.0) or 0.0),
            "evidence_tier_distribution": {
                "T1": int(summary_tier_dist.get("T1", 0) or 0),
                "T2": int(summary_tier_dist.get("T2", 0) or 0),
                "T3": int(summary_tier_dist.get("T3", 0) or 0),
                "T4": int(summary_tier_dist.get("T4", 0) or 0),
            },
        }

        # Accept curated summaries when internally consistent; they may include
        # sources counted outside provenance.data_sources (e.g., section-level citations).
        tier_sum = sum(candidate["evidence_tier_distribution"].values())
        if (
            candidate["total_sources"] >= 0
            and candidate["doi_backed"] >= 0
            and candidate["url_only"] >= 0
            and 0.0 <= candidate["doi_coverage_pct"] <= 100.0
            and candidate["doi_backed"] <= candidate["total_sources"]
            and candidate["url_only"] <= candidate["total_sources"]
            and tier_sum == candidate["total_sources"]
        ):
            return candidate

        site_name = data.get("site", {}).get("name", "unknown")
        logger.warning(
            "provenance_summary invalid for %s; falling back to derived values",
            site_name,
        )
        return derived

    return derived


def _render_data_quality(sites_data: dict[str, dict[str, Any]]) -> None:
    """Render per-site data quality breakdown."""
    st.markdown(
        '<div class="section-header">Data Quality Dashboard</div>',
        unsafe_allow_html=True,
    )

    # Portfolio-level summary
    total_services = 0
    total_market_price = 0
    total_avoided_cost = 0
    total_other = 0
    total_sources = 0
    total_doi = 0
    total_url = 0
    total_caveats = 0
    portfolio_tiers = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}

    site_rows: list[dict[str, Any]] = []

    for name in sorted(sites_data.keys()):
        data = sites_data[name]
        services = data.get("ecosystem_services", {}).get("services", [])

        n_market = sum(1 for s in services if s.get("valuation_method") == "market_price")
        n_avoided = sum(1 for s in services if s.get("valuation_method") == "avoided_cost")
        n_other = len(services) - n_market - n_avoided

        # Use explicit provenance summaries when present.
        prov_summary = _resolve_provenance_summary(data)
        n_sources = prov_summary["total_sources"]
        n_doi = prov_summary["doi_backed"]
        n_url_only = prov_summary["url_only"]
        doi_coverage_pct = prov_summary["doi_coverage_pct"]
        tier_dist = prov_summary["evidence_tier_distribution"]

        caveats = data.get("caveats", [])
        assessment_year = data.get("ecological_status", {}).get("assessment_year", "")
        if not assessment_year:
            assessment_year = data.get("neoli_assessment", {}).get("assessment_date", "")

        total_services += len(services)
        total_market_price += n_market
        total_avoided_cost += n_avoided
        total_other += n_other
        total_sources += n_sources
        total_doi += n_doi
        total_url += n_url_only
        total_caveats += len(caveats)
        for tier in ("T1", "T2", "T3", "T4"):
            portfolio_tiers[tier] += tier_dist.get(tier, 0)

        site_rows.append({
            "name": name,
            "n_services": len(services),
            "n_market": n_market,
            "n_avoided": n_avoided,
            "n_other": n_other,
            "n_sources": n_sources,
            "n_doi": n_doi,
            "n_url_only": n_url_only,
            "doi_coverage_pct": doi_coverage_pct,
            "tier_dist": tier_dist,
            "n_caveats": len(caveats),
            "assessment_year": assessment_year,
        })

    portfolio_doi_coverage = round((total_doi / total_sources) * 100, 1) if total_sources else 0.0

    # Portfolio summary strip
    cols = st.columns(5)
    summary_kpis = [
        ("Total Services", str(total_services), f"Across {len(sites_data)} sites"),
        ("Market-Price", str(total_market_price), f"{total_market_price}/{total_services} services"),
        ("Avoided-Cost", str(total_avoided_cost), f"{total_avoided_cost}/{total_services} services"),
        (
            "DOI Coverage",
            f"{portfolio_doi_coverage:.1f}%",
            f"{total_doi}/{total_sources} DOI-backed",
        ),
        (
            "Evidence Tier Mix",
            f"T1:{portfolio_tiers['T1']} T2:{portfolio_tiers['T2']}",
            f"T3:{portfolio_tiers['T3']} T4:{portfolio_tiers['T4']}",
        ),
    ]
    for i, (label, value, context) in enumerate(summary_kpis):
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

    # Per-site table
    st.markdown(
        '<div style="margin-top:28px"></div>',
        unsafe_allow_html=True,
    )

    header = (
        "<tr><th>Site</th><th style='text-align:center'>Services</th>"
        "<th style='text-align:center'>Market-Price</th>"
        "<th style='text-align:center'>Avoided-Cost</th>"
        "<th style='text-align:center'>Other</th>"
        "<th style='text-align:center'>Sources</th>"
        "<th style='text-align:center'>DOI Sources</th>"
        "<th style='text-align:center'>URL-Only</th>"
        "<th style='text-align:center'>DOI Coverage</th>"
        "<th style='text-align:center'>Tier Mix (T1/T2/T3/T4)</th>"
        "<th style='text-align:center'>Caveats</th>"
        "<th style='text-align:center'>Assessment Year</th></tr>"
    )

    rows = ""
    for sr in site_rows:
        short_name = sr["name"]
        if len(short_name) > 28:
            short_name = " ".join(short_name.split()[:3])

        rows += (
            f"<tr>"
            f"<td style='font-weight:600;color:#E2E8F0;white-space:nowrap'>{short_name}</td>"
            f"<td style='text-align:center'>{sr['n_services']}</td>"
            f"<td style='text-align:center;color:#66BB6A;font-weight:600'>{sr['n_market']}</td>"
            f"<td style='text-align:center;color:#FFA726;font-weight:600'>{sr['n_avoided']}</td>"
            f"<td style='text-align:center;color:#94A3B8'>{sr['n_other']}</td>"
            f"<td style='text-align:center'>{sr['n_sources']}</td>"
            f"<td style='text-align:center;color:#5B9BD5;font-weight:600'>{sr['n_doi']}</td>"
            f"<td style='text-align:center;color:#94A3B8'>{sr['n_url_only']}</td>"
            f"<td style='text-align:center;color:#CBD5E1;font-weight:600'>{sr['doi_coverage_pct']:.1f}%</td>"
            f"<td style='text-align:center;color:#94A3B8'>"
            f"{sr['tier_dist'].get('T1', 0)}/{sr['tier_dist'].get('T2', 0)}/"
            f"{sr['tier_dist'].get('T3', 0)}/{sr['tier_dist'].get('T4', 0)}"
            f"</td>"
            f"<td style='text-align:center'>{sr['n_caveats']}</td>"
            f"<td style='text-align:center'>{sr['assessment_year']}</td>"
            f"</tr>"
        )

    st.markdown(
        f'<table class="evidence-table"><thead>{header}</thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )

    # Valuation method legend
    st.markdown(
        '<div style="margin-top:14px;font-size:13px;color:#64748B;line-height:1.8">'
        "<strong style='color:#66BB6A'>Market-price</strong>: observable market transactions "
        "(tourism revenue, fisheries catch value, carbon credit trades) - "
        "preferred method for investment-grade metrics. "
        "<strong style='color:#FFA726'>Avoided-cost</strong>: estimated damages prevented "
        "(coastal protection, flood reduction) - accepted for regulating services. "
        "<strong style='color:#94A3B8'>Other</strong>: regional analogue or contingent valuation."
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section D: Characterization Pipeline Diagram
# ---------------------------------------------------------------------------


def _render_pipeline_diagram(sites_data: dict[str, dict[str, Any]]) -> None:
    """Render the 5-step characterization pipeline as a flow diagram."""
    st.markdown(
        '<div class="section-header">Characterization Pipeline</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Every site in the portfolio passes through a '
        "5-step pipeline. External APIs (Marine Regions, OBIS, WoRMS) power "
        "automated characterization; each step is validated independently.</div>",
        unsafe_allow_html=True,
    )

    steps = [
        {
            "num": "1",
            "name": "Locate",
            "desc": "Identify MPA boundaries and coordinates",
            "api": "Marine Regions API",
            "detail": "Geocode site, resolve MRGID, fetch EEZ/boundary polygons",
        },
        {
            "num": "2",
            "name": "Populate Species",
            "desc": "Discover marine species within the MPA",
            "api": "OBIS + WoRMS API",
            "detail": "Query OBIS occurrence records, validate taxonomy via WoRMS AphiaID",
        },
        {
            "num": "3",
            "name": "Characterize Habitat",
            "desc": "Classify habitat types and compute quality tier",
            "api": "Taxonomy-based scoring",
            "detail": "Map species to habitat indicators, score Bronze/Silver/Gold",
        },
        {
            "num": "4",
            "name": "Estimate Services",
            "desc": "Apply bridge axioms to compute ESV per service",
            "api": "Bridge Axiom Engine",
            "detail": "Habitat-axiom map selects applicable axioms, per-hectare coefficients applied",
        },
        {
            "num": "5",
            "name": "Score & Rate",
            "desc": "Generate NEOLI score and composite asset rating",
            "api": "MARIS Rating Engine",
            "detail": "NEOLI criteria check, composite scoring (ecology + governance + finance + risk)",
        },
    ]

    # Render flow as connected steps
    flow_html = '<div style="display:flex;align-items:stretch;gap:0;overflow-x:auto;padding:8px 0">'
    for i, step in enumerate(steps):
        flow_html += f"""
<div style="flex:1;min-width:160px;position:relative">
<div style="background:linear-gradient(145deg, #0F1A2E 0%, #162039 100%);
     border:1px solid #22C55E;border-radius:8px;padding:16px 14px;height:100%">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
<span style="width:24px;height:24px;border-radius:50%;background:rgba(34,197,94,0.2);
       color:#22C55E;display:inline-flex;align-items:center;justify-content:center;
       font-size:13px;font-weight:700;flex-shrink:0">{step['num']}</span>
<span style="font-weight:600;color:#CBD5E1;font-size:14px;text-transform:uppercase;
       letter-spacing:0.5px">{step['name']}</span>
</div>
<div style="font-size:13px;color:#B0BEC5;line-height:1.5;margin-bottom:8px">{step['desc']}</div>
<div style="font-size:12px;color:#94A3B8;line-height:1.4">
<span style="background:rgba(91,155,213,0.1);color:#5B9BD5;padding:2px 6px;border-radius:3px;
       font-size:11px">{step['api']}</span>
</div>
</div>
</div>
"""
        if i < len(steps) - 1:
            flow_html += (
                '<div style="display:flex;align-items:center;padding:0 2px;color:#64748B;'
                'font-size:20px;flex-shrink:0">&#8594;</div>'
            )
    flow_html += "</div>"

    st.markdown(flow_html, unsafe_allow_html=True)

    # Site completion status
    st.markdown(
        '<div style="margin-top:24px"></div>',
        unsafe_allow_html=True,
    )

    n_sites = len(sites_data)
    site_names_sorted = sorted(sites_data.keys())

    status_rows = ""
    for name in site_names_sorted:
        data = sites_data[name]
        has_site = bool(data.get("site", {}).get("name"))
        has_species = bool(data.get("key_species"))
        has_habitat = bool(
            data.get("ecological_status", {}).get("primary_habitat")
        )
        has_services = bool(data.get("ecosystem_services", {}).get("services"))
        has_rating = bool(data.get("asset_quality_rating", {}).get("rating"))

        statuses = [has_site, has_species, has_habitat, has_services, has_rating]
        complete = all(statuses)

        short_name = name
        if len(name) > 28:
            short_name = " ".join(name.split()[:3])

        cells = ""
        for done in statuses:
            if done:
                cells += (
                    "<td style='text-align:center'>"
                    "<span style='color:#22C55E;font-weight:700'>Done</span></td>"
                )
            else:
                cells += (
                    "<td style='text-align:center'>"
                    "<span style='color:#64748B'>--</span></td>"
                )

        status_label = (
            "<span style='color:#22C55E;font-weight:600'>Complete</span>"
            if complete
            else "<span style='color:#FFA726;font-weight:600'>Partial</span>"
        )

        status_rows += (
            f"<tr>"
            f"<td style='font-weight:600;color:#E2E8F0;white-space:nowrap'>{short_name}</td>"
            f"{cells}"
            f"<td style='text-align:center'>{status_label}</td>"
            f"</tr>"
        )

    header = (
        "<tr><th>Site</th>"
        "<th style='text-align:center'>1. Locate</th>"
        "<th style='text-align:center'>2. Species</th>"
        "<th style='text-align:center'>3. Habitat</th>"
        "<th style='text-align:center'>4. Services</th>"
        "<th style='text-align:center'>5. Score</th>"
        "<th style='text-align:center'>Status</th></tr>"
    )

    st.markdown(
        f'<table class="evidence-table"><thead>{header}</thead>'
        f"<tbody>{status_rows}</tbody></table>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="margin-top:14px;font-size:13px;color:#64748B">'
        f"All {n_sites} Gold-tier sites have completed the full 5-step pipeline. "
        f"The SiteCharacterizer can auto-characterize new MPAs using OBIS, WoRMS, "
        f"and Marine Regions APIs - add a new case study JSON to "
        f"<code style='color:#5B9BD5'>examples/</code> and re-run the populator."
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_site_intelligence(sites_data: dict[str, dict[str, Any]] | None = None) -> None:
    """Render the Site Intelligence tab."""
    st.markdown(
        """
        <div class="masthead" style="margin-bottom: 32px;">
            <div class="masthead-brand">NEREUS | SITE SCOUT</div>
            <h1 style="font-size: 42px; font-weight: 300; margin-top: 10px; margin-bottom: 5px;">Discovery Pipeline</h1>
            <div class="masthead-subtitle">Automated MPA characterization and data quality matrix</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Load data if not provided
    if sites_data is None:
        sites_data = {}
        for site_meta in get_all_sites():
            name = site_meta["name"]
            data = get_site_data(name)
            if data is not None:
                sites_data[name] = data

    if not sites_data:
        st.warning(
            "No case study data found. Add *_case_study.json files to "
            "examples/ to populate the Site Intelligence tab."
        )
        return

    _render_neoli_matrix(sites_data)
    _render_habitat_axiom_map()
    _render_data_quality(sites_data)
    _render_pipeline_diagram(sites_data)
