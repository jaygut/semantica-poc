"""TNFD Disclosure tab for Nereus v4 Intelligence Platform.

Generates a TNFD LEAP disclosure with alignment scoring, per-pillar
breakdowns, gap analysis, and downloadable outputs. Works with any site
discovered from ``examples/*_case_study.json``.

Adapted from v3 with dynamic imports from the v4 shared module.
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
    fmt_usd,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pillar definitions - used for per-pillar scoring
# ---------------------------------------------------------------------------

_PILLARS: dict[str, dict[str, Any]] = {
    "GOV": {
        "name": "Governance",
        "ids": ["GOV-A", "GOV-B", "GOV-C"],
        "total": 3,
        "color": COLORS["accent_blue"],
    },
    "STR": {
        "name": "Strategy",
        "ids": ["STR-A", "STR-B", "STR-C", "STR-D"],
        "total": 4,
        "color": COLORS["accent_purple"],
    },
    "RIM": {
        "name": "Risk & Impact Mgmt",
        "ids": ["RIM-A", "RIM-B", "RIM-C", "RIM-D"],
        "total": 4,
        "color": COLORS["accent_teal"],
    },
    "MT": {
        "name": "Metrics & Targets",
        "ids": ["MT-A", "MT-B", "MT-C"],
        "total": 3,
        "color": COLORS["accent_amber"],
    },
}


def _compute_pillar_scores(
    populated_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Compute per-pillar populated counts from the list of populated IDs."""
    result: dict[str, dict[str, Any]] = {}
    for prefix, info in _PILLARS.items():
        count = sum(1 for pid in populated_ids if pid.startswith(prefix))
        total = info["total"]
        pct = (count / total * 100) if total > 0 else 0
        result[prefix] = {
            "name": info["name"],
            "populated": count,
            "total": total,
            "pct": pct,
            "color": info["color"],
        }
    return result


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_alignment_gauge(
    populated_count: int,
    total_disclosures: int,
    score_pct: float,
    populated_ids: list[str],
) -> None:
    """Render the large alignment score gauge and per-pillar progress bars."""
    if score_pct >= 80:
        score_color = COLORS["success"]
    elif score_pct >= 50:
        score_color = COLORS["warning"]
    else:
        score_color = COLORS["danger"]

    st.markdown(
        f"""
<div class="kpi-card" style="text-align:center;margin-bottom:24px">
<div class="kpi-label">TNFD Recommended Disclosures</div>
<div style="font-size:56px;font-weight:700;color:{score_color};line-height:1.2">
{populated_count}/{total_disclosures}
</div>
<div class="kpi-context">{score_pct:.0f}% populated</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Per-pillar bars
    pillar_scores = _compute_pillar_scores(populated_ids)
    cols = st.columns(4)
    for i, (_prefix, ps) in enumerate(pillar_scores.items()):
        color = ps["color"]
        pct = ps["pct"]
        with cols[i]:
            st.markdown(
                f"""
<div class="pillar-bar">
<div class="pillar-name">{ps['name']}</div>
<div class="pillar-score">{ps['populated']}/{ps['total']}</div>
<div class="pillar-fill-bg">
<div class="pillar-fill" style="width:{pct:.0f}%;background:{color}"></div>
</div>
</div>
""",
                unsafe_allow_html=True,
            )


def _render_locate_phase(disclosure: Any) -> None:
    """Render Phase 1 LOCATE expander content."""
    loc = disclosure.locate
    st.markdown(f"**Site:** {loc.site_name}")
    st.markdown(f"**Country:** {loc.country}")
    st.markdown(f"**Biome:** {loc.biome}")

    if loc.area_km2:
        st.markdown(f"**Area:** {loc.area_km2:,.0f} km2")
    if loc.coordinates:
        lat = loc.coordinates.get("latitude", 0)
        lon = loc.coordinates.get("longitude", 0)
        st.markdown(f"**Coordinates:** {lat}, {lon}")

    st.markdown(
        f"**Priority Biodiversity Area:** "
        f"{'Yes' if loc.priority_biodiversity_area else 'No'}"
    )
    if loc.world_heritage_status:
        st.markdown("**World Heritage Status:** Yes")
    if loc.designation_year:
        st.markdown(f"**Designation Year:** {loc.designation_year}")
    if loc.management_authority:
        st.markdown(f"**Management Authority:** {loc.management_authority}")
    if loc.indigenous_partnership:
        st.markdown(
            f"**Indigenous Partnership:** {loc.indigenous_partnership}"
        )

    if loc.habitats:
        st.markdown("---")
        st.markdown("**Habitats**")
        for h in loc.habitats:
            extent = f" - {h.extent_km2:,.0f} km2" if h.extent_km2 else ""
            condition = f" (condition: {h.condition})" if h.condition else ""
            st.markdown(f"- {h.name}{extent}{condition}")


def _render_evaluate_phase(disclosure: Any) -> None:
    """Render Phase 2 EVALUATE expander content."""
    ev = disclosure.evaluate
    if ev.total_esv_usd:
        st.markdown(f"**Total ESV:** {fmt_usd(ev.total_esv_usd)}/year")
    st.markdown(f"**Primary Dependency:** {ev.primary_dependency}")

    if ev.services:
        st.markdown("---")
        st.markdown("**Ecosystem Services**")
        for svc in ev.services:
            val = fmt_usd(svc.annual_value_usd) if svc.annual_value_usd else "N/A"
            share = (
                f" ({svc.share_of_total_esv_pct:.1f}%)"
                if svc.share_of_total_esv_pct
                else ""
            )
            method = f" [{svc.valuation_method}]" if svc.valuation_method else ""
            name = svc.service_type.replace("_", " ").title()
            st.markdown(f"- {name}: **{val}**{share}{method}")

    if ev.species_dependencies:
        st.markdown("---")
        st.markdown("**Key Species Dependencies**")
        for sp in ev.species_dependencies:
            st.markdown(
                f"- *{sp.scientific_name}* ({sp.common_name}) - {sp.role}"
            )

    if ev.impact_pathways:
        st.markdown("---")
        st.markdown(f"**Impact Pathways:** {len(ev.impact_pathways)} identified")
        for ip in ev.impact_pathways[:5]:
            axiom = f" [{ip.bridge_axiom_id}]" if ip.bridge_axiom_id else ""
            st.markdown(f"- {ip.description}{axiom}")

    if ev.bridge_axioms_applied:
        st.markdown("---")
        st.markdown(
            f"**Bridge Axioms Applied:** {', '.join(ev.bridge_axioms_applied)}"
        )


def _render_assess_phase(disclosure: Any) -> None:
    """Render Phase 3 ASSESS expander content."""
    asr = disclosure.assess
    st.markdown(f"**NEOLI Score:** {asr.neoli_score}/5")
    st.markdown(
        f"**Asset Rating:** {asr.asset_rating} "
        f"(composite {asr.composite_score:.2f})"
    )

    if asr.physical_risks:
        st.markdown("---")
        st.markdown("**Physical Risks**")
        for r in asr.physical_risks:
            st.markdown(
                f"- **{r.risk_type}** (severity: {r.severity}, "
                f"likelihood: {r.likelihood})"
            )

    if asr.transition_risks:
        st.markdown("---")
        st.markdown("**Transition Risks**")
        for r in asr.transition_risks:
            st.markdown(
                f"- **{r.risk_type}** (severity: {r.severity}, "
                f"likelihood: {r.likelihood})"
            )

    if asr.systemic_risks:
        st.markdown("---")
        st.markdown("**Systemic Risks**")
        for r in asr.systemic_risks:
            st.markdown(
                f"- **{r.risk_type}** (severity: {r.severity}, "
                f"likelihood: {r.likelihood})"
            )

    if asr.opportunities:
        st.markdown("---")
        st.markdown("**Opportunities**")
        for o in asr.opportunities:
            opp_name = o.opportunity_type.replace("_", " ").title()
            st.markdown(f"- **{opp_name}**: {o.description}")
            if o.estimated_value_range:
                st.markdown(f"  - Estimated range: {o.estimated_value_range}")

    mc = asr.monte_carlo_summary
    if mc:
        st.markdown("---")
        st.markdown("**Monte Carlo Risk Quantification**")
        st.markdown(f"- Simulations: {mc.get('n_simulations', 0):,}")
        st.markdown(f"- Median ESV: {fmt_usd(mc.get('median', 0))}")
        st.markdown(f"- P5 (downside): {fmt_usd(mc.get('p5', 0))}")
        st.markdown(f"- P95 (upside): {fmt_usd(mc.get('p95', 0))}")


def _render_prepare_phase(disclosure: Any) -> None:
    """Render Phase 4 PREPARE - the 14 disclosure sections by pillar."""
    prep = disclosure.prepare

    pillar_groups = [
        ("Governance", prep.governance_sections),
        ("Strategy", prep.strategy_sections),
        ("Risk & Impact Management", prep.risk_management_sections),
        ("Metrics & Targets", prep.metrics_targets_sections),
    ]

    for pillar_name, sections in pillar_groups:
        st.markdown(f"**{pillar_name}**")
        for s in sections:
            status_color = COLORS["success"] if s.populated else COLORS["danger"]
            status_label = "Populated" if s.populated else "Gap"
            st.markdown(
                f'<span style="color:{status_color};font-weight:600">'
                f"[{status_label}]</span> **{s.disclosure_id}: {s.title}**",
                unsafe_allow_html=True,
            )
            if s.content:
                st.markdown(f"> {s.content}")
            elif s.gap_reason:
                st.markdown(f"> *Gap:* {s.gap_reason}")
        st.markdown("---")

    if prep.recommendation:
        st.markdown("**Recommendation**")
        st.markdown(prep.recommendation)

    if prep.provenance_chain:
        st.markdown("---")
        st.markdown("**Provenance Chain**")
        for p in prep.provenance_chain:
            doi_link = (
                f" ([DOI](https://doi.org/{p.source_doi}))"
                if p.source_doi
                else ""
            )
            tier_str = f" [{p.evidence_tier}]" if p.evidence_tier else ""
            st.markdown(f"- {p.claim}{doi_link}{tier_str}")


def _render_gap_analysis(
    gap_ids: list[str],
    gap_details: dict[str, str],
) -> None:
    """Render gap analysis warning section."""
    if not gap_ids:
        st.markdown(
            """
<div class="risk-card risk-card-green" style="margin-top:20px">
<h4>No Gaps Identified</h4>
<p>All 14 TNFD recommended disclosures are populated with evidence-backed
content from the MARIS knowledge graph.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    gap_list_html = ""
    for gid in gap_ids:
        reason = gap_details.get(gid, "Insufficient data")
        gap_list_html += f"<li><strong>{gid}:</strong> {reason}</li>"

    st.markdown(
        f"""
<div class="risk-card risk-card-red" style="margin-top:20px">
<h4>{len(gap_ids)} Gap{'s' if len(gap_ids) != 1 else ''} Identified</h4>
<ul style="color:#B0BEC5;font-size:17px;line-height:1.7">{gap_list_html}</ul>
<p style="margin-top:12px"><strong>Recommendation:</strong> Expand the MARIS
knowledge graph with additional data sources to populate remaining disclosures.
Priority: governance data (GOV-B), value chain impact pathways (RIM-B), and
scenario analysis (STR-C).</p>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_download_buttons(
    disclosure: Any,
    site_slug: str,
    site_data: dict[str, Any],
) -> None:
    """Render three download buttons for disclosure outputs."""
    try:
        from maris.disclosure.renderers import (
            render_json,
            render_markdown,
            render_summary,
        )
        from investor_demo.components.v4.reporting import generate_tnfd_pdf

        md_content = render_markdown(disclosure)
        json_content = render_json(disclosure)
        summary_content = render_summary(disclosure)
        
        # Generate PDF
        pdf_bytes = generate_tnfd_pdf(site_data.get("site", {}), md_content)
        
    except Exception as e:
        logger.warning("Failed to render disclosure outputs: %s", e)
        st.caption(f"Download buttons unavailable - renderer error: {e}")
        return

    st.markdown(
        '<div class="section-header" style="margin-top:32px">'
        "Download Disclosure</div>",
        unsafe_allow_html=True,
    )

    dl1, dl2, dl3, dl4 = st.columns(4)
    with dl1:
        st.download_button(
            label="📄 PDF Report",
            data=pdf_bytes,
            file_name=f"tnfd_report_{site_slug}.pdf",
            mime="application/pdf",
            key=f"v4_dl_pdf_{site_slug}",
        )
    with dl2:
        st.download_button(
            label="⬇️ Markdown",
            data=md_content,
            file_name=f"tnfd_leap_{site_slug}.md",
            mime="text/markdown",
            key=f"v4_dl_md_{site_slug}",
        )
    with dl3:
        st.download_button(
            label="⬇️ JSON",
            data=json_content,
            file_name=f"tnfd_leap_{site_slug}.json",
            mime="application/json",
            key=f"v4_dl_json_{site_slug}",
        )
    with dl4:
        st.download_button(
            label="⬇️ Summary",
            data=summary_content,
            file_name=f"tnfd_executive_summary_{site_slug}.md",
            mime="text/markdown",
            key=f"v4_dl_summary_{site_slug}",
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_tnfd_compliance(
    data: dict[str, Any],
    site: str,
    mode: str,
    **kwargs: Any,
) -> None:
    """Render the TNFD Disclosure tab.

    Generates a TNFD LEAP disclosure for the selected site, scores it
    against the 14 recommended disclosures, and presents an interactive
    dashboard with alignment gauge, phase expanders, gap analysis, and
    download buttons.

    Parameters
    ----------
    data:
        Case study JSON or static bundle.
    site:
        Canonical site name.
    mode:
        "live" or "demo".
    """
    st.markdown(
        '<div class="section-header" style="margin-top:0">'
        "TNFD LEAP Disclosure</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">Auto-generated TNFD LEAP disclosure from '
        "the MARIS knowledge graph. All claims traced to DOI-backed evidence "
        "through bridge axioms. Anticipates alignment with TNFD v1.0 "
        "recommended disclosures.</div>",
        unsafe_allow_html=True,
    )

    # ---- Generate disclosure ----
    disclosure = None
    alignment = None

    try:
        from maris.disclosure.alignment_scorer import AlignmentScorer
        from maris.disclosure.leap_generator_v4 import LEAPGeneratorV4

        generator = LEAPGeneratorV4(project_root=_PROJECT_ROOT)
        disclosure = generator.generate(site)

        scorer = AlignmentScorer()
        alignment = scorer.score(disclosure)
    except Exception as gen_err:
        logger.error("TNFD disclosure generation failed: %s", gen_err)
        st.error(
            f"TNFD disclosure generation failed for {site}: {gen_err}. "
            f"Ensure case study data is available."
        )
        return

    # ---- 1. Alignment Gauge ----
    try:
        _render_alignment_gauge(
            populated_count=alignment.populated_count,
            total_disclosures=alignment.total_disclosures,
            score_pct=alignment.score_pct,
            populated_ids=alignment.populated_ids,
        )
    except Exception as gauge_err:
        logger.warning("Alignment gauge render failed: %s", gauge_err)
        st.caption(f"Alignment gauge unavailable: {gauge_err}")

    # ---- 2. LEAP Phase Expanders ----
    st.markdown(
        '<div class="section-header">LEAP Phases</div>',
        unsafe_allow_html=True,
    )

    try:
        with st.expander("Phase 1: LOCATE - Identify Nature Interface", expanded=False):
            _render_locate_phase(disclosure)
    except Exception as loc_err:
        logger.warning("LOCATE phase render failed: %s", loc_err)
        st.caption(f"Phase 1 unavailable: {loc_err}")

    try:
        with st.expander("Phase 2: EVALUATE - Dependencies and Impacts", expanded=False):
            _render_evaluate_phase(disclosure)
    except Exception as eval_err:
        logger.warning("EVALUATE phase render failed: %s", eval_err)
        st.caption(f"Phase 2 unavailable: {eval_err}")

    try:
        with st.expander("Phase 3: ASSESS - Material Risks and Opportunities", expanded=False):
            _render_assess_phase(disclosure)
    except Exception as assess_err:
        logger.warning("ASSESS phase render failed: %s", assess_err)
        st.caption(f"Phase 3 unavailable: {assess_err}")

    try:
        with st.expander("Phase 4: PREPARE - 14 Recommended Disclosures", expanded=True):
            _render_prepare_phase(disclosure)
    except Exception as prep_err:
        logger.warning("PREPARE phase render failed: %s", prep_err)
        st.caption(f"Phase 4 unavailable: {prep_err}")

    # ---- 3. Gap Analysis ----
    try:
        st.markdown(
            '<div class="section-header">Gap Analysis</div>',
            unsafe_allow_html=True,
        )
        _render_gap_analysis(
            gap_ids=alignment.gap_ids,
            gap_details=alignment.gap_details,
        )
    except Exception as gap_err:
        logger.warning("Gap analysis render failed: %s", gap_err)
        st.caption(f"Gap analysis unavailable: {gap_err}")

    # ---- 4. Download Buttons ----
    try:
        site_slug = site.lower().replace(" ", "_")
        _render_download_buttons(disclosure, site_slug, data)
    except Exception as dl_err:
        logger.warning("Download buttons render failed: %s", dl_err)
        st.caption(f"Downloads unavailable: {dl_err}")
