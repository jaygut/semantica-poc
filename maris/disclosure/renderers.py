"""Output renderers for TNFD LEAP disclosures.

Provides Markdown, JSON, and executive summary formats for generated
TNFD LEAP disclosures. All renderers accept a TNFDDisclosure model
and produce a string output.
"""

from __future__ import annotations

import json

from maris.disclosure.models import TNFDDisclosure, DisclosureSection


def render_markdown(disclosure: TNFDDisclosure) -> str:
    """Render a full TNFD LEAP disclosure as Markdown.

    Produces a structured document with all four LEAP phases and
    the 14 recommended disclosures organized by pillar.
    """
    lines: list[str] = []

    lines.append(f"# TNFD LEAP Disclosure - {disclosure.site_name}")
    lines.append("")
    lines.append(f"**Framework:** {disclosure.framework_version}")
    lines.append(f"**Generated:** {disclosure.generated_at}")
    lines.append("")

    # Phase 1: Locate
    loc = disclosure.locate
    lines.append("## Phase 1: Locate")
    lines.append("")
    lines.append(f"- **Site:** {loc.site_name}")
    lines.append(f"- **Country:** {loc.country}")
    lines.append(f"- **Biome:** {loc.biome}")
    if loc.area_km2:
        lines.append(f"- **Area:** {loc.area_km2:,.0f} km2")
    if loc.coordinates:
        lines.append(
            f"- **Coordinates:** {loc.coordinates.get('latitude', 0)}, "
            f"{loc.coordinates.get('longitude', 0)}"
        )
    lines.append(f"- **Priority Biodiversity Area:** {'Yes' if loc.priority_biodiversity_area else 'No'}")
    if loc.world_heritage_status:
        lines.append("- **World Heritage Status:** Yes")
    if loc.designation_year:
        lines.append(f"- **Designation Year:** {loc.designation_year}")
    if loc.management_authority:
        lines.append(f"- **Management Authority:** {loc.management_authority}")
    if loc.indigenous_partnership:
        lines.append(f"- **Indigenous Partnership:** {loc.indigenous_partnership}")
    lines.append("")

    if loc.habitats:
        lines.append("### Habitats")
        lines.append("")
        for h in loc.habitats:
            extent = f", {h.extent_km2:,.0f} km2" if h.extent_km2 else ""
            lines.append(f"- {h.name}{extent} (condition: {h.condition})")
        lines.append("")

    # Phase 2: Evaluate
    ev = disclosure.evaluate
    lines.append("## Phase 2: Evaluate")
    lines.append("")
    if ev.total_esv_usd:
        lines.append(f"**Total ESV:** ${ev.total_esv_usd:,.0f}/year")
    lines.append(f"**Primary Dependency:** {ev.primary_dependency}")
    lines.append("")

    if ev.services:
        lines.append("### Ecosystem Services")
        lines.append("")
        lines.append("| Service | Annual Value (USD) | Method | Share of ESV |")
        lines.append("|---------|-------------------|--------|-------------|")
        for svc in ev.services:
            val = f"${svc.annual_value_usd:,.0f}" if svc.annual_value_usd else "N/A"
            share = f"{svc.share_of_total_esv_pct:.1f}%" if svc.share_of_total_esv_pct else "N/A"
            lines.append(
                f"| {svc.service_type.replace('_', ' ').title()} | {val} | "
                f"{svc.valuation_method} | {share} |"
            )
        lines.append("")

    if ev.species_dependencies:
        lines.append("### Key Species Dependencies")
        lines.append("")
        for sp in ev.species_dependencies:
            lines.append(f"- *{sp.scientific_name}* ({sp.common_name}) - {sp.role}")
        lines.append("")

    # Phase 3: Assess
    asr = disclosure.assess
    lines.append("## Phase 3: Assess")
    lines.append("")
    lines.append(f"- **NEOLI Score:** {asr.neoli_score}/5")
    lines.append(f"- **Asset Rating:** {asr.asset_rating} (composite {asr.composite_score:.2f})")
    lines.append("")

    if asr.physical_risks:
        lines.append("### Physical Risks")
        lines.append("")
        for r in asr.physical_risks:
            lines.append(f"- **{r.risk_type}** (severity: {r.severity}, likelihood: {r.likelihood})")
        lines.append("")

    if asr.transition_risks:
        lines.append("### Transition Risks")
        lines.append("")
        for r in asr.transition_risks:
            lines.append(f"- **{r.risk_type}** (severity: {r.severity}, likelihood: {r.likelihood})")
        lines.append("")

    if asr.opportunities:
        lines.append("### Opportunities")
        lines.append("")
        for o in asr.opportunities:
            lines.append(f"- **{o.opportunity_type.replace('_', ' ').title()}**: {o.description}")
            if o.estimated_value_range:
                lines.append(f"  - Estimated range: {o.estimated_value_range}")
        lines.append("")

    if asr.monte_carlo_summary:
        mc = asr.monte_carlo_summary
        lines.append("### Monte Carlo Risk Quantification")
        lines.append("")
        lines.append(f"- Simulations: {mc.get('n_simulations', 0):,}")
        lines.append(f"- Median ESV: ${mc.get('median', 0):,.0f}")
        lines.append(f"- P5 (downside): ${mc.get('p5', 0):,.0f}")
        lines.append(f"- P95 (upside): ${mc.get('p95', 0):,.0f}")
        lines.append("")

    # Phase 4: Prepare
    prep = disclosure.prepare
    lines.append("## Phase 4: Prepare")
    lines.append("")

    _render_disclosure_sections(lines, "Governance", prep.governance_sections)
    _render_disclosure_sections(lines, "Strategy", prep.strategy_sections)
    _render_disclosure_sections(lines, "Risk & Impact Management", prep.risk_management_sections)
    _render_disclosure_sections(lines, "Metrics & Targets", prep.metrics_targets_sections)

    if prep.metrics:
        lines.append("### Key Metrics")
        lines.append("")
        lines.append("| Metric | Value | Unit |")
        lines.append("|--------|-------|------|")
        for m in prep.metrics:
            val = m.value
            if isinstance(val, float) and val > 1000:
                val = f"${val:,.0f}"
            lines.append(f"| {m.metric_name} | {val} | {m.unit} |")
        lines.append("")

    if prep.targets:
        lines.append("### Targets")
        lines.append("")
        for t in prep.targets:
            lines.append(
                f"- **{t.target_name}**: baseline={t.baseline_value}, "
                f"target={t.target_value} by {t.target_year} "
                f"({t.aligned_framework}) - {t.status}"
            )
        lines.append("")

    if prep.recommendation:
        lines.append("### Recommendation")
        lines.append("")
        lines.append(prep.recommendation)
        lines.append("")

    # Provenance chain
    if prep.provenance_chain:
        lines.append("## Provenance Chain")
        lines.append("")
        for p in prep.provenance_chain:
            doi_link = f" (DOI: {p.source_doi})" if p.source_doi else ""
            tier = f" [{p.evidence_tier}]" if p.evidence_tier else ""
            lines.append(f"- {p.claim}{doi_link}{tier}")
        lines.append("")

    return "\n".join(lines)


def _render_disclosure_sections(
    lines: list[str],
    pillar_name: str,
    sections: list[DisclosureSection],
) -> None:
    """Render a set of disclosure sections under a pillar heading."""
    lines.append(f"### {pillar_name}")
    lines.append("")
    for s in sections:
        status = "populated" if s.populated else "gap"
        lines.append(f"**{s.disclosure_id}: {s.title}** [{status}]")
        lines.append("")
        if s.content:
            lines.append(s.content)
        elif s.gap_reason:
            lines.append(f"*Gap:* {s.gap_reason}")
        lines.append("")


def render_json(disclosure: TNFDDisclosure) -> str:
    """Render the disclosure as a formatted JSON string."""
    return json.dumps(disclosure.model_dump(), indent=2, default=str)


def render_summary(disclosure: TNFDDisclosure) -> str:
    """Render a 1-page executive summary of the TNFD LEAP disclosure.

    Produces a concise overview suitable for board-level communication.
    """
    loc = disclosure.locate
    ev = disclosure.evaluate
    asr = disclosure.assess
    prep = disclosure.prepare

    lines: list[str] = []

    lines.append(f"# TNFD LEAP Executive Summary - {disclosure.site_name}")
    lines.append("")
    lines.append(f"**Site:** {loc.site_name}, {loc.country}")
    lines.append(f"**Biome:** {loc.biome}")
    if loc.area_km2:
        lines.append(f"**Area:** {loc.area_km2:,.0f} km2")
    lines.append(f"**Asset Rating:** {asr.asset_rating} (NEOLI {asr.neoli_score}/5)")
    lines.append("")

    # ESV headline
    if ev.total_esv_usd:
        lines.append(f"**Total ESV:** ${ev.total_esv_usd:,.0f}/year")
        lines.append(f"**Primary driver:** {ev.primary_dependency}")
    lines.append("")

    # Risk summary
    total_risks = len(asr.physical_risks) + len(asr.transition_risks) + len(asr.systemic_risks)
    lines.append(f"**Risks identified:** {total_risks}")
    if asr.physical_risks:
        high_risks = [r for r in asr.physical_risks if r.severity == "high"]
        if high_risks:
            risk_names = ", ".join(r.risk_type for r in high_risks)
            lines.append(f"**High-severity risks:** {risk_names}")
    lines.append("")

    # Opportunities
    if asr.opportunities:
        lines.append(f"**Opportunities:** {len(asr.opportunities)}")
        for o in asr.opportunities:
            lines.append(f"- {o.opportunity_type.replace('_', ' ').title()}: {o.estimated_value_range}")
        lines.append("")

    # Disclosure completeness
    all_sections = (
        prep.governance_sections
        + prep.strategy_sections
        + prep.risk_management_sections
        + prep.metrics_targets_sections
    )
    populated = sum(1 for s in all_sections if s.populated)
    total = len(all_sections)
    lines.append(f"**Disclosure completeness:** {populated}/{total} TNFD recommended disclosures populated")
    lines.append("")

    # Recommendation
    if prep.recommendation:
        lines.append(f"**Recommendation:** {prep.recommendation}")
        lines.append("")

    return "\n".join(lines)
