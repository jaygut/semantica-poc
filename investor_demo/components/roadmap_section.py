"""Scaling Intelligence section - shared between static and live dashboards."""

import streamlit as st


def render_roadmap_section():
    """Render the Scaling Intelligence section.

    Presents the MARIS extension roadmap to investors: data foundation,
    intelligence stack positioning, and phased execution plan. Uses only
    existing CSS classes from the dashboard style block.
    """

    # --- Section Header ---
    st.markdown(
        '<div class="section-header">Scaling Intelligence</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">'
        "Cabo Pulmo and Shark Bay demonstrate the full provenance chain for two "
        "deeply characterized sites with contrasting ESV profiles - tourism-dominant "
        "versus carbon-dominant. The same infrastructure scales to any marine "
        "habitat by ingesting authoritative global databases and applying "
        "bridge axiom translation automatically."
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Thesis Block ---
    st.markdown(
        """
<div class="thesis-block">
<div class="thesis-lead">
The competitive advantage is not the data. It is the translation layer.
</div>
<div class="thesis-body">
Marine biodiversity data is increasingly open. OBIS, WoRMS, and the EU
Digital Europe Programme's linked-data initiatives publish species
occurrences, taxonomic backbones, and habitat maps as public goods. What
these databases do not provide, and structurally cannot, is financial
translation: bridge axioms that convert ecological state into ecosystem
service values, confidence intervals that quantify uncertainty, and
framework alignment that maps outputs to TNFD disclosures and blue bond
eligibility. <strong>MARIS provides the three intelligence layers that
sit above raw biodiversity data</strong>, turning open science into
investment-grade infrastructure.
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # --- KPI Strip ---
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            """
<div class="kpi-card">
<div class="kpi-label">Marine Databases Mapped</div>
<div class="kpi-value">27</div>
<div class="kpi-context">Prioritized for automated ingestion</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            """
<div class="kpi-card">
<div class="kpi-label">Occurrence Records Available</div>
<div class="kpi-value">130M+</div>
<div class="kpi-context">OBIS, GBIF, and regional networks</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            """
<div class="kpi-card">
<div class="kpi-label">MPAs in Global Pipeline</div>
<div class="kpi-value">18,000+</div>
<div class="kpi-context">MPAtlas global registry</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            """
<div class="kpi-card">
<div class="kpi-label">Platform Target</div>
<div class="kpi-value">100+</div>
<div class="kpi-context">Fully characterized sites</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # --- Intelligence Stack ---
    st.markdown(
        '<div class="subsection-header">Intelligence Stack</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-desc">'
        "Public databases provide the biological substrate. MARIS adds "
        "ecological interpretation, service valuation, and financial "
        "translation: the layers that make raw data investable."
        "</div>",
        unsafe_allow_html=True,
    )

    l0, l12, l3 = st.columns(3)
    with l0:
        st.markdown(
            """
<div class="fw-card">
<h4>Layer 0: Public Data</h4>
<ul>
<li><strong>OBIS</strong> &middot; 130M+ occurrence records</li>
<li><strong>WoRMS</strong> &middot; 247K accepted marine species</li>
<li><strong>Allen Coral Atlas</strong> &middot; Global reef mapping</li>
<li><strong>MPAtlas</strong> &middot; 18,000+ MPA boundaries</li>
<li><strong>Marine Regions</strong> &middot; Standardized geographies</li>
</ul>
<p style="margin-top:12px;color:#94A3B8;font-size:15px">
Open access. EU Digital Europe funds linked-data
infrastructure for this layer.
</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with l12:
        st.markdown(
            """
<div class="fw-card">
<h4>Layers 1-2: Ecological Intelligence</h4>
<ul>
<li><strong>Site characterization</strong> &middot; Species, habitats, governance</li>
<li><strong>Bridge axioms</strong> &middot; Ecological state to service values</li>
<li><strong>NEOLI scoring</strong> &middot; Automated governance assessment</li>
<li><strong>Trophic modeling</strong> &middot; Food-web risks and cascades</li>
<li><strong>Confidence intervals</strong> &middot; 95% CI on every output</li>
</ul>
<p style="margin-top:12px;color:#94A3B8;font-size:15px">
16 axioms today, extensible to any marine habitat type.
</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with l3:
        st.markdown(
            """
<div class="fw-card">
<h4>Layer 3: Financial Translation</h4>
<ul>
<li><strong>ESV computation</strong> &middot; Monte Carlo, 10K simulations</li>
<li><strong>Asset ratings</strong> &middot; Ecological + governance composite</li>
<li><strong>TNFD LEAP alignment</strong> &middot; Nature-related disclosure</li>
<li><strong>IFC Blue Finance</strong> &middot; Blue bond eligibility screening</li>
<li><strong>Portfolio analytics</strong> &middot; Cross-site benchmarking</li>
</ul>
<p style="margin-top:12px;color:#94A3B8;font-size:15px">
<strong style="color:#5B9BD5">This is the MARIS moat.</strong>
No public database provides this layer.
</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # --- Execution Roadmap ---
    st.markdown(
        '<div class="subsection-header">Execution Roadmap</div>',
        unsafe_allow_html=True,
    )

    p1, p2 = st.columns(2)
    with p1:
        st.markdown(
            """
<div class="risk-card risk-card-green" style="height:100%">
<h4>Phase 1 &middot; Reference Site (Current)</h4>
<p><strong>2 fully characterized sites</strong> with complete provenance
from field measurement to financial output. 195 papers, 16 bridge
axioms, 893 graph nodes.</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            """
<div class="risk-card" style="border-left:3px solid #5B9BD5;height:100%">
<h4>Phase 2 &middot; Regional Expansion</h4>
<p><strong>10 coral reef MPAs</strong> characterized via automated
ingestion from OBIS, WoRMS, and MPAtlas. Automated NEOLI scoring
and cross-site benchmarking.</p>
</div>
""",
            unsafe_allow_html=True,
        )

    p3, p4 = st.columns(2)
    with p3:
        st.markdown(
            """
<div class="risk-card" style="border-left:3px solid #5B9BD5;height:100%">
<h4>Phase 3 &middot; Habitat Expansion</h4>
<p><strong>50+ sites across coral reefs, mangroves, and seagrass.</strong>
Expanded axiom library for blue carbon, coastal protection, and
sustainable fisheries.</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with p4:
        st.markdown(
            """
<div class="risk-card risk-card-green" style="height:100%">
<h4>Phase 4 &middot; Full Platform</h4>
<p><strong>100+ MPAs with satellite-derived condition tracking.</strong>
Automated degradation alerts, dynamic risk repricing, and continuous
enrichment from 27 databases.</p>
</div>
""",
            unsafe_allow_html=True,
        )
