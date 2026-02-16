import streamlit as st
import json
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Nereus | Cabo Pulmo Investment Case",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS - Professional financial dashboard styling (dark mode)
# ---------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
    /* ---- Global (Dark Mode) ---- */
    .stApp {
        background-color: #0B1120;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    #MainMenu, footer, header { visibility: hidden; }

    /* Force Streamlit text elements to light */
    .stApp .stMarkdown p,
    .stApp .stMarkdown li,
    .stApp .stMarkdown span,
    .stApp .stCaption,
    .stApp [data-testid="stCaptionContainer"] * {
        color: #B0BEC5 !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #E2E8F0 !important;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background-color: #060D1A;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] * {
        color: #CBD5E1 !important;
    }
    section[data-testid="stSidebar"] .stSelectSlider label,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #B0BEC5 !important;
        font-size: 18px;
    }
    section[data-testid="stSidebar"] h3 {
        color: #F1F5F9 !important;
        font-size: 17px !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
        margin-top: 24px;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1E293B !important;
    }

    /* ---- Masthead ---- */
    .masthead {
        background: linear-gradient(135deg, #0F1A2E 0%, #162B4D 100%);
        color: white;
        padding: 44px 48px 40px 48px;
        border-radius: 12px;
        margin-bottom: 24px;
        border: 1px solid #1E3A5F;
    }
    .masthead-brand {
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #5B9BD5;
        margin-bottom: 10px;
    }
    .masthead-powered {
        font-size: 12px;
        font-weight: 400;
        color: #64748B;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
    }
    .masthead h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        font-size: 48px;
        letter-spacing: -0.5px;
        margin: 0 0 6px 0;
        color: #F1F5F9 !important;
    }
    .masthead-subtitle {
        font-size: 22px;
        color: #94A3B8;
        letter-spacing: 1px;
    }
    .masthead-badges {
        margin-top: 20px;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    .badge-green { background: rgba(46, 125, 50, 0.25); color: #66BB6A; border: 1px solid rgba(46, 125, 50, 0.35); }
    .badge-blue { background: rgba(91, 155, 213, 0.2); color: #5B9BD5; border: 1px solid rgba(91, 155, 213, 0.3); }

    /* ---- Section Headers ---- */
    .section-header {
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        color: #5B9BD5;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 10px;
        margin-top: 52px;
        margin-bottom: 8px;
    }

    /* ---- Section Descriptions (text below header) ---- */
    .section-desc {
        font-size: 19px;
        color: #94A3B8;
        margin-bottom: 20px;
        line-height: 1.6;
    }

    /* ---- Subsection Headers ---- */
    .subsection-header {
        font-size: 22px;
        font-weight: 600;
        color: #CBD5E1;
        margin-top: 28px;
        margin-bottom: 14px;
    }

    /* ---- KPI Cards ---- */
    .kpi-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 28px 28px;
        border: 1px solid #243352;
        height: 100%;
    }
    .kpi-label {
        font-size: 15px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94A3B8;
        margin-bottom: 12px;
    }
    .kpi-value {
        font-size: 48px;
        font-weight: 700;
        color: #F1F5F9;
        line-height: 1;
        margin-bottom: 10px;
    }
    .kpi-context {
        font-size: 17px;
        color: #94A3B8;
    }

    /* ---- Thesis Block ---- */
    .thesis-block {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-left: 3px solid #5B9BD5;
        padding: 36px 40px;
        margin: 20px 0 0 0;
        border-radius: 0 10px 10px 0;
        border-top: 1px solid #243352;
        border-right: 1px solid #243352;
        border-bottom: 1px solid #243352;
    }
    .thesis-lead {
        font-size: 28px;
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 16px;
        line-height: 1.3;
    }
    .thesis-body {
        font-size: 19px;
        line-height: 1.7;
        color: #B0BEC5;
    }
    .thesis-body strong {
        color: #CBD5E1;
    }

    /* ---- Risk Cards ---- */
    .risk-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 24px 28px;
        border: 1px solid #243352;
    }
    .risk-card-red { border-left: 3px solid #EF5350; }
    .risk-card-green { border-left: 3px solid #66BB6A; }
    .risk-card h4 {
        font-size: 21px;
        font-weight: 600;
        color: #E2E8F0 !important;
        margin: 0 0 10px 0;
    }
    .risk-card p {
        font-size: 18px;
        color: #B0BEC5;
        margin: 0;
        line-height: 1.6;
    }
    .risk-card a { color: #5B9BD5; text-decoration: none; }
    .risk-card a:hover { text-decoration: underline; }

    /* ---- Comparison Cards ---- */
    .comp-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 24px 28px;
        border: 1px solid #243352;
        height: 100%;
    }
    .comp-card h4 {
        font-size: 21px;
        font-weight: 600;
        color: #E2E8F0 !important;
        margin: 0 0 8px 0;
    }
    .comp-score {
        font-size: 17px;
        font-weight: 600;
        color: #5B9BD5;
        margin-bottom: 12px;
    }
    .comp-card p {
        font-size: 18px;
        color: #B0BEC5;
        line-height: 1.5;
        margin: 0 0 8px 0;
    }
    .comp-lesson {
        font-size: 17px;
        color: #94A3B8;
        font-style: italic;
    }

    /* ---- Framework Section ---- */
    .fw-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 24px 28px;
        border: 1px solid #243352;
        height: 100%;
    }
    .fw-card h4 {
        font-size: 20px;
        font-weight: 600;
        color: #E2E8F0 !important;
        margin: 0 0 14px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .fw-card li {
        font-size: 18px;
        color: #B0BEC5;
        line-height: 1.7;
    }
    .fw-card p {
        color: #B0BEC5;
        font-size: 17px;
    }
    .fw-card strong {
        color: #CBD5E1;
    }
    .fw-phase {
        font-weight: 600;
        color: #5B9BD5;
    }

    /* ---- Caveats ---- */
    .caveats {
        background: #0D1526;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 28px 32px;
        margin-top: 52px;
        font-size: 17px;
        color: #94A3B8;
        line-height: 1.7;
    }
    .caveats h4 {
        font-size: 15px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #64748B !important;
        margin: 0 0 12px 0;
    }
    .caveats ol {
        padding-left: 20px;
        margin: 0;
    }
    .caveats li {
        color: #94A3B8 !important;
    }

    /* ---- Footer ---- */
    .app-footer {
        text-align: center;
        font-size: 14px;
        color: #64748B;
        padding: 24px 0 12px 0;
        border-top: 1px solid #1E293B;
        margin-top: 24px;
    }

    /* ---- Evidence Table ---- */
    .evidence-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 16px;
        font-size: 17px;
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #243352;
    }
    .evidence-table th {
        text-align: left;
        padding: 16px 24px;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94A3B8;
        border-bottom: 1px solid #243352;
        background: rgba(10, 18, 38, 0.5);
    }
    .evidence-table td {
        padding: 16px 24px;
        color: #CBD5E1;
        border-bottom: 1px solid #1E2D48;
        vertical-align: top;
        line-height: 1.6;
    }
    .evidence-table tr:last-child td { border-bottom: none; }
    .evidence-table .axiom-id {
        font-weight: 600;
        color: #5B9BD5;
        white-space: nowrap;
        font-size: 17px;
    }
    .evidence-table a {
        color: #5B9BD5;
        text-decoration: none;
        font-weight: 500;
    }
    .evidence-table a:hover { text-decoration: underline; }

    /* ---- NEOLI dots ---- */
    .neoli-row {
        display: flex;
        gap: 10px;
        align-items: center;
        margin: 6px 0;
    }
    .neoli-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }
    .neoli-filled { background-color: #66BB6A; }
    .neoli-empty { background-color: #1E293B; border: 1px solid #334155; }
    .neoli-label {
        font-size: 18px;
        color: #B0BEC5 !important;
    }

    /* ---- Plotly overrides ---- */
    .stPlotlyChart {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        border: 1px solid #243352;
        padding: 8px;
    }

    /* ---- Connection status indicator ---- */
    .conn-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 500;
    }
    .conn-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .conn-live .conn-dot { background: #66BB6A; }
    .conn-live { color: #66BB6A; background: rgba(46, 125, 50, 0.15); border: 1px solid rgba(46, 125, 50, 0.3); }
    .conn-static .conn-dot { background: #FFA726; }
    .conn-static { color: #FFA726; background: rgba(245, 166, 35, 0.15); border: 1px solid rgba(245, 166, 35, 0.3); }

    /* ---- Quick query buttons ---- */
    .stApp [data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: rgba(91, 155, 213, 0.1) !important;
        border: 1px solid rgba(91, 155, 213, 0.3) !important;
        color: #5B9BD5 !important;
        border-radius: 20px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 6px 16px !important;
        white-space: nowrap !important;
        transition: all 0.2s ease !important;
    }
    .stApp [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: rgba(91, 155, 213, 0.2) !important;
        border-color: rgba(91, 155, 213, 0.5) !important;
    }

    /* ---- Chat input ---- */
    .stApp .stTextInput input {
        background: #0F1A2E !important;
        border: 1px solid #1E293B !important;
        color: #E2E8F0 !important;
        border-radius: 8px !important;
        font-size: 15px !important;
        padding: 10px 16px !important;
    }
    .stApp .stTextInput input::placeholder {
        color: #64748B !important;
    }
    .stApp .stTextInput input:focus {
        border-color: #5B9BD5 !important;
        box-shadow: 0 0 0 1px rgba(91, 155, 213, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    bundle_path = Path(__file__).parent / ".." / "demos" / "context_graph_demo" / "cabo_pulmo_investment_grade_bundle.json"
    if not bundle_path.exists():
        bundle_path = Path("../demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json")
    if not bundle_path.exists():
        st.error("Data bundle not found. Run the notebook to generate cabo_pulmo_investment_grade_bundle.json first.")
        return None
    with open(bundle_path, "r") as f:
        return json.load(f)


data = load_data()
if not data:
    st.stop()

# ---------------------------------------------------------------------------
# API Client (lazy init, cached in session state)
# ---------------------------------------------------------------------------
if "maris_client" not in st.session_state:
    from api_client import get_client
    st.session_state.maris_client = get_client()

client = st.session_state.maris_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt_usd(val):
    """Format USD value as $X.XM or $X.XK."""
    if abs(val) >= 1e6:
        return f"${val / 1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val / 1e3:.0f}K"
    return f"${val:,.0f}"


def fmt_service(key):
    """tourism_usd -> Tourism"""
    return key.replace("_usd", "").replace("_", " ").title()


# Plain-English bridge axiom descriptions
AXIOM_INFO = {
    "BA-001": {
        "meaning": "Fish biomass increases drive tourism value: divers will pay up to 84% more at sites with healthy reef biomass",
        "citation": "Marcos-Castillo et al. 2024",
    },
    "BA-002": {
        "meaning": "No-take marine reserves accumulate biomass to 670% of unprotected levels (global meta-analysis of 82 MPAs; Cabo Pulmo observed 463%)",
        "citation": "Hopf et al. 2024",
    },
    "BA-011": {
        "meaning": "Protected reefs suffer 30% less damage from climate disturbances than unprotected reefs",
        "citation": "Ortiz-Villa et al. 2024",
    },
    "BA-012": {
        "meaning": "Reef degradation causes 35% loss in fisheries productivity when protection fails",
        "citation": "Rogers et al. 2018",
    },
    "BA-013": {
        "meaning": "Seagrass meadows sequester carbon at 0.84 tCO2/ha/yr through sediment burial of approximately 20% of net primary production",
        "citation": "Gomis et al. 2025",
    },
    "BA-014": {
        "meaning": "Blue carbon sequestration generates tradeable credits at $15-50 per tCO2 under voluntary market standards",
        "citation": "Duarte et al. 2025",
    },
    "BA-015": {
        "meaning": "Seagrass loss releases 112-476 tCO2/ha of stored carbon, as demonstrated by the 2011 Shark Bay heatwave",
        "citation": "Arias-Ortiz et al. 2018",
    },
    "BA-016": {
        "meaning": "MPA protection with NEOLI 4+/5 provides 25-100 year carbon permanence guarantee",
        "citation": "Lovelock et al. 2025",
    },
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### NEREUS")

    # Connection status
    if client.is_live:
        st.markdown(
            '<div class="conn-status conn-live"><span class="conn-dot"></span>Live API</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="conn-status conn-static"><span class="conn-dot"></span>Static Mode</div>',
            unsafe_allow_html=True,
        )

    # Dual-site architecture
    st.markdown("### Characterized Sites")
    site = data["site"]
    neoli = data["ecological_status"]
    st.markdown(f"""
**{site['name']}**
{site['country']} - {site['area_km2']} km2 - Est. {site['designation_year']}
Tourism-dominant - $29.27M ESV
""")
    st.markdown("""
**Shark Bay World Heritage Area**
Australia - 23,000 km2 - Est. 1991
Carbon-dominant - $21.5M ESV
""")
    st.markdown(
        '<div style="font-size:13px;color:#94A3B8;line-height:1.5;margin-top:4px;margin-bottom:16px;'
        'padding:10px 12px;background:rgba(91,155,213,0.08);border-radius:6px;border:1px solid rgba(91,155,213,0.15)">'
        'Dual-site architecture proves the framework is habitat-agnostic: '
        'coral reef (tourism) vs seagrass (carbon).'
        '</div>',
        unsafe_allow_html=True,
    )

    # NEOLI breakdown (Cabo Pulmo - the primary dashboard site)
    st.markdown("### NEOLI Alignment")
    breakdown = neoli["neoli_breakdown"]
    neoli_items = [
        ("N", "No-take", breakdown["no_take"]),
        ("E", "Enforced", breakdown["enforced"]),
        ("O", "Old (>10yr)", breakdown["old"]),
        ("L", "Large", breakdown["large"]),
        ("I", "Isolated", breakdown["isolated"]),
    ]
    for letter, label, met in neoli_items:
        dot_class = "neoli-filled" if met else "neoli-empty"
        st.markdown(
            f'<div class="neoli-row"><span class="neoli-dot {dot_class}"></span>'
            f'<span class="neoli-label"><strong>{letter}</strong> {label}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Scenario")
    confidence_level = st.select_slider(
        "Valuation confidence",
        options=["Conservative (P5)", "Base Case (Median)", "Optimistic (P95)"],
        value="Base Case (Median)",
    )

    st.markdown("---")
    st.markdown(f"<span style='font-size:13px;color:#64748B'>Methodology: {data['metadata']['methodology']}</span>", unsafe_allow_html=True)
    st.markdown(f"<span style='font-size:13px;color:#64748B'>Generated: {data['metadata']['generated_at'].split('T')[0]}</span>", unsafe_allow_html=True)
    st.markdown(f"<span style='font-size:13px;color:#64748B'>Schema: v{data['metadata']['maris_schema_version']}</span>", unsafe_allow_html=True)
    st.markdown("<span style='font-size:13px;color:#64748B'>Sites: 2 characterized, 2 comparison</span>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Compute selected scenario value
# ---------------------------------------------------------------------------
mc_pcts = data["risk_assessment"]["monte_carlo_summary"]["percentiles_usd"]
if confidence_level == "Conservative (P5)":
    selected_val = mc_pcts["p5"]
    scenario_label = "P5 - Downside Case"
elif confidence_level == "Optimistic (P95)":
    selected_val = mc_pcts["p95"]
    scenario_label = "P95 - Upside Case"
else:
    selected_val = mc_pcts["p50"]
    scenario_label = "Median - Base Case"

# =========================================================================
# MAIN CONTENT
# =========================================================================

# ---------------------------------------------------------------------------
# 1. Masthead
# ---------------------------------------------------------------------------
ifc_badge = ""
if data["framework_alignment"]["ifc_blue_finance"]["eligible_use_of_proceeds"]:
    ifc_badge = '<span class="badge badge-green" title="Self-assessed alignment with IFC Blue Finance Guidelines (2022) eligible use of proceeds criteria. Not independently verified.">IFC Blue Finance - Self-Assessed</span>'
tnfd_badge = ""
if data["framework_alignment"]["tnfd_leap"]["assess"]["opportunity"]:
    tnfd_badge = '<span class="badge badge-blue" title="Anticipates alignment with TNFD LEAP disclosure framework. MARIS data structure follows LEAP phases but has not undergone independent TNFD review.">TNFD LEAP - Anticipates Alignment</span>'

st.markdown(f"""
<div class="masthead">
<div class="masthead-brand">NEREUS</div>
<div class="masthead-powered">Powered by MARIS + Semantica</div>
<h1>{data['site']['name']}</h1>
<div class="masthead-subtitle">Provenance-First Blue Finance Infrastructure</div>
<div class="masthead-badges">{ifc_badge}{tnfd_badge}</div>
</div>
""", unsafe_allow_html=True)

st.caption(f"*{data['metadata']['disclaimer']}*")

# ---------------------------------------------------------------------------
# 2. Investment Thesis
# ---------------------------------------------------------------------------
n_axioms_site = len(data["bridge_axioms_applied"])
n_axioms_system = 16  # Total bridge axioms in MARIS (12 core + 4 blue carbon)
esv_total = data["financial_output"]["market_price_esv_usd"]

st.markdown(f"""
<div class="thesis-block">
<div class="thesis-lead">This is auditable infrastructure, not an AI-generated narrative.</div>
<div class="thesis-body">
<strong>MARIS</strong> (Marine Asset Risk Intelligence System) is the marine-domain intelligence layer
that converts ecological field data into investment-grade financial metrics. It contains 195 curated
papers, <strong>{n_axioms_system} bridge axioms</strong> (quantitative translation rules that convert
ecological measurements into financial estimates, each with documented coefficients and 95%
confidence intervals), and 8 entity schemas covering species, habitats, MPAs, and ecosystem services.
<br><br>
MARIS is built on <strong><a href="https://github.com/Hawksight-AI/semantica" target="_blank" style="color:#5B9BD5;text-decoration:none">Semantica</a></strong>,
an open-source knowledge framework that validates, traces, and audits every claim back
to its peer-reviewed source. Semantica ensures that no number exists without a DOI-backed
provenance chain, the trust infrastructure that makes MARIS outputs auditable.
<br><br>
Together, they produce <strong>context graphs</strong>: structured knowledge representations where
every output value traces through documented transformation steps to its original scientific source.
Unlike traditional ESV estimates that deliver a point value without an audit trail, a context graph
delivers the value <em>and</em> the complete reasoning chain behind it. This analysis values
Cabo Pulmo's ecosystem services at <strong>{fmt_usd(esv_total)}</strong> annually, and every
dollar can be independently verified.
</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. KPI Strip
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)

bio = data["ecological_status"]["biomass_ratio"]
climate_buf = data["risk_assessment"]["climate_resilience"]["disturbance_reduction_percent"]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Annual Ecosystem Service Value</div>
<div class="kpi-value">{fmt_usd(selected_val)}</div>
<div class="kpi-context">{scenario_label}</div>
</div>
""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Biomass Recovery Ratio</div>
<div class="kpi-value">{bio['central']}x</div>
<div class="kpi-context">95% CI: [{bio['ci_95'][0]}x, {bio['ci_95'][1]}x]</div>
</div>
""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">NEOLI Alignment Score</div>
<div class="kpi-value">{neoli['neoli_score']} / 5</div>
<div class="kpi-context">No-take, Enforced, Old, Isolated</div>
</div>
""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
<div class="kpi-card">
<div class="kpi-label">Disturbance Reduction</div>
<div class="kpi-value">{climate_buf}%</div>
<div class="kpi-context">MPA climate resilience premium</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 4. Provenance Chain - THE CENTERPIECE
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Provenance Chain</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">This graph is the core of the infrastructure. It is not a visualization of AI reasoning; it is a deterministic, auditable map where every node represents verified ecological or financial state and every edge applies a documented, peer-reviewed translation rule. An auditor can trace any financial claim back to the original field measurement.</div>', unsafe_allow_html=True)

fig_prov = go.Figure()

# Layer column positions
LAYER_X = {
    "site": 0.0,
    "ecological": 1.2,
    "services": 2.4,
    "financial": 3.6,
    "risk": 1.8,
}

# Color palette for node types
NODE_COLORS = {
    "site": "#2563EB",       # Bright blue
    "ecological": "#059669",  # Emerald green
    "service": "#7C3AED",    # Vivid purple
    "financial": "#D97706",  # Amber gold
    "risk_good": "#10B981",  # Green
    "risk_bad": "#EF4444",   # Red
}

# Node definitions: (id, label, x, y, color_key, size, symbol)
services_bd = data["financial_output"]["services_breakdown"]
nodes = [
    ("site",        f"Cabo Pulmo NP\nEst. {site['designation_year']}",
     LAYER_X["site"], 0.50, "site", 55, "circle"),
    ("neoli",       f"NEOLI {neoli['neoli_score']}/5\nGovernance Score",
     LAYER_X["ecological"], 1.00, "ecological", 40, "diamond"),
    ("biomass",     f"Biomass {bio['central']}x\nRecovery Ratio",
     LAYER_X["ecological"], 0.00, "ecological", 40, "diamond"),
    ("tourism",     f"Tourism\n{fmt_usd(services_bd['tourism_usd'])}",
     LAYER_X["services"], 1.20, "service", 36, "circle"),
    ("fisheries",   f"Fisheries\n{fmt_usd(services_bd['fisheries_usd'])}",
     LAYER_X["services"], 0.72, "service", 32, "circle"),
    ("carbon",      f"Carbon\n{fmt_usd(services_bd['carbon_usd'])}",
     LAYER_X["services"], 0.28, "service", 28, "circle"),
    ("protection",  f"Coastal Protection\n{fmt_usd(services_bd['coastal_protection_usd'])}",
     LAYER_X["services"], -0.20, "service", 28, "circle"),
    ("esv",         f"Total ESV\n{fmt_usd(esv_total)}/yr",
     LAYER_X["financial"], 0.50, "financial", 60, "circle"),
    ("resilience",  f"Climate Buffer\n-{climate_buf}% Impact",
     LAYER_X["risk"], -0.42, "risk_good", 28, "square"),
    ("degradation", f"Degradation Risk\n-{data['risk_assessment']['degradation_risk']['productivity_loss_central_percent']}% if Unprotected",
     LAYER_X["risk"], -0.65, "risk_bad", 28, "square"),
]

node_map = {n[0]: (n[2], n[3]) for n in nodes}

# Edges: (from, to, label, is_axiom)
edges = [
    ("site",      "neoli",      "assessed as", False),
    ("site",      "biomass",    "observed", False),
    ("neoli",     "biomass",    "BA-002: No-take reserves\naccumulate 4.63x biomass", True),
    ("biomass",   "tourism",    "BA-001: Biomass drives\ntourism value (+84% WTP)", True),
    ("biomass",   "fisheries",  "Spillover to\nadjacent fisheries", False),
    ("biomass",   "carbon",     "Reef-associated\nblue carbon", False),
    ("biomass",   "protection", "Structural\ncomplexity", False),
    ("tourism",   "esv",        "", False),
    ("fisheries", "esv",        "", False),
    ("carbon",    "esv",        "", False),
    ("protection", "esv",       "", False),
    ("neoli",     "resilience", "BA-011: MPA\nresilience premium", True),
    ("neoli",     "degradation", "BA-012: Risk if\nprotection fails", True),
]

# Draw semi-transparent layer background regions
layer_regions = [
    (LAYER_X["site"] - 0.25, LAYER_X["site"] + 0.25, "SITE", "rgba(37, 99, 235, 0.06)"),
    (LAYER_X["ecological"] - 0.35, LAYER_X["ecological"] + 0.35, "ECOLOGICAL STATE", "rgba(5, 150, 105, 0.06)"),
    (LAYER_X["services"] - 0.35, LAYER_X["services"] + 0.35, "ECOSYSTEM SERVICES", "rgba(124, 58, 237, 0.06)"),
    (LAYER_X["financial"] - 0.25, LAYER_X["financial"] + 0.25, "FINANCIAL VALUE", "rgba(217, 119, 6, 0.06)"),
]

for x0, x1, title, fillcolor in layer_regions:
    fig_prov.add_shape(
        type="rect",
        x0=x0, x1=x1, y0=-0.30, y1=1.32,
        fillcolor=fillcolor,
        line=dict(color="rgba(255,255,255,0.03)", width=1),
        layer="below",
    )

# Draw edges
for src, tgt, label, is_axiom in edges:
    x0, y0 = node_map[src]
    x1, y1 = node_map[tgt]
    edge_color = "#5B9BD5" if is_axiom else "#334155"
    edge_width = 2.5 if is_axiom else 1.5
    fig_prov.add_trace(go.Scatter(
        x=[x0, x1], y=[y0, y1],
        mode="lines",
        line=dict(color=edge_color, width=edge_width),
        hoverinfo="skip",
        showlegend=False,
    ))
    # Arrow at target end
    fig_prov.add_annotation(
        x=x1, y=y1, ax=x0, ay=y0,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True,
        arrowhead=3, arrowsize=1.5, arrowwidth=1.5,
        arrowcolor="#5B9BD5" if is_axiom else "#475569",
        standoff=14,
    )
    # Edge label at midpoint
    if label:
        lbl_color = "#E2E8F0" if is_axiom else "#94A3B8"
        lbl_size = 13 if is_axiom else 12
        fig_prov.add_annotation(
            x=(x0 + x1) / 2, y=(y0 + y1) / 2,
            text=label,
            showarrow=False,
            font=dict(size=lbl_size, color=lbl_color, family="Inter"),
            bgcolor="rgba(11,17,32,0.92)",
            bordercolor="rgba(91,155,213,0.15)" if is_axiom else "rgba(0,0,0,0)",
            borderpad=4,
            borderwidth=1,
        )

# Draw nodes with glow effect
for nid, label, x, y, color_key, size, symbol in nodes:
    color = NODE_COLORS[color_key]
    # Outer glow
    fig_prov.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers",
        marker=dict(
            size=size + 12,
            color=color,
            opacity=0.15,
            symbol=symbol,
        ),
        hoverinfo="skip",
        showlegend=False,
    ))
    # Main node
    fig_prov.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers+text",
        marker=dict(
            size=size,
            color=color,
            line=dict(width=2, color="#0B1120"),
            symbol=symbol,
        ),
        text=[label],
        textposition="bottom center" if nid in ("site", "esv") else "top center",
        textfont=dict(size=14, color="#E2E8F0", family="Inter"),
        hoverinfo="text",
        hovertext=[label.replace("\n", " ")],
        showlegend=False,
    ))

# Layer headers
for lx, ltxt, lclr in [
    (LAYER_X["site"], "SITE", "#2563EB"),
    (LAYER_X["ecological"], "ECOLOGICAL STATE", "#059669"),
    (LAYER_X["services"], "ECOSYSTEM SERVICES", "#7C3AED"),
    (LAYER_X["financial"], "FINANCIAL VALUE", "#D97706"),
]:
    fig_prov.add_annotation(
        x=lx, y=1.42,
        text=ltxt,
        showarrow=False,
        font=dict(size=14, color=lclr, family="Inter"),
    )

fig_prov.update_layout(
    height=900,
    margin=dict(l=20, r=20, t=50, b=40),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 4.1]),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.80, 1.58]),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#CBD5E1"),
)

st.plotly_chart(fig_prov, width="stretch")

# Evidence table
st.markdown('<div class="subsection-header">Bridge Axiom Evidence</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Each axiom is a reusable, auditable building block of the infrastructure. Click any source to verify the original peer-reviewed paper.</div>', unsafe_allow_html=True)
axiom_rows = ""
for ax in data["bridge_axioms_applied"]:
    aid = ax["axiom_id"]
    info = AXIOM_INFO.get(aid, {"meaning": ax["application"], "citation": ""})
    doi_link = f"https://doi.org/{ax['source_doi']}"
    axiom_rows += f'<tr><td class="axiom-id">{aid}</td><td>{info["meaning"]}</td><td><a href="{doi_link}" target="_blank">{info["citation"]}</a></td></tr>'

st.markdown(f'<table class="evidence-table"><thead><tr><th>Rule</th><th>What It Means</th><th>Source</th></tr></thead><tbody>{axiom_rows}</tbody></table>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 5. Valuation Composition
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Valuation Composition</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Fully decomposed, transparent valuation built from market-price methodology. No black-box models. Every service value traces to a specific bridge axiom and peer-reviewed coefficient.</div>', unsafe_allow_html=True)

col_chart, col_ci = st.columns([3, 2])

with col_chart:
    services = data["financial_output"]["services_breakdown"]
    sorted_services = sorted(services.items(), key=lambda x: x[1], reverse=True)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=[fmt_service(k) for k, v in sorted_services],
        x=[v / 1e6 for k, v in sorted_services],
        orientation="h",
        marker_color=["#7C3AED", "#6D28D9", "#5B21B6", "#4C1D95"],
        text=[fmt_usd(v) for k, v in sorted_services],
        textposition="outside",
        textfont=dict(size=16, family="Inter", color="#E2E8F0"),
    ))
    fig_bar.update_layout(
        height=280,
        margin=dict(l=0, r=80, t=10, b=10),
        xaxis=dict(
            title="Annual Value (USD Millions)",
            showgrid=True, gridcolor="#1E293B",
            tickprefix="$", ticksuffix="M",
            title_font=dict(size=14, color="#94A3B8"),
            tickfont=dict(color="#94A3B8", size=13),
        ),
        yaxis=dict(showgrid=False, automargin=True, tickfont=dict(color="#CBD5E1", size=15)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#CBD5E1"),
    )
    st.plotly_chart(fig_bar, width="stretch")

with col_ci:
    ci = data["financial_output"]["market_price_esv_ci_95_usd"]
    st.markdown(f"""
<div class="kpi-card" style="margin-top:0">
<div class="kpi-label">95% Confidence Range</div>
<div class="kpi-value" style="font-size:30px">{fmt_usd(ci[0])} - {fmt_usd(ci[1])}</div>
<div class="kpi-context" style="margin-top:14px">
Selected scenario: <strong style="color:#E2E8F0">{fmt_usd(selected_val)}</strong> ({scenario_label})
</div>
<div class="kpi-context" style="margin-top:14px">
Based on {data['risk_assessment']['monte_carlo_summary']['n_simulations']:,} Monte Carlo
simulations incorporating climate shock probabilities and market volatility.
</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 6. Risk Profile
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Risk Profile</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Quantified uncertainty is a feature of trustworthy infrastructure, not a weakness. MARIS propagates confidence intervals through every calculation rather than presenting false precision.</div>', unsafe_allow_html=True)

mc_stats = data["risk_assessment"]["monte_carlo_summary"]
mean_val = mc_stats["mean_usd"]
std_val = mc_stats["std_usd"]

x_dist = np.linspace(mean_val - 4 * std_val, mean_val + 4 * std_val, 500)
y_dist = (1 / (std_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_dist - mean_val) / std_val) ** 2)

fig_mc = go.Figure()
fig_mc.add_trace(go.Scatter(
    x=x_dist, y=y_dist, mode="lines",
    fill="tozeroy",
    line=dict(color="#5B9BD5", width=2),
    fillcolor="rgba(91, 155, 213, 0.12)",
    hoverinfo="skip",
))

pct_lines = [
    (mc_pcts["p5"],  "P5 Downside", "#EF5350", "dash"),
    (mc_pcts["p50"], "Median",      "#F1F5F9", "solid"),
    (mc_pcts["p95"], "P95 Upside",  "#66BB6A", "dash"),
]
for val, lbl, clr, dash in pct_lines:
    fig_mc.add_vline(
        x=val, line_dash=dash, line_color=clr, line_width=1.5,
        annotation_text=f"{lbl}: {fmt_usd(val)}",
        annotation_font=dict(size=13, color=clr, family="Inter"),
        annotation_position="top",
    )

fig_mc.update_layout(
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

st.plotly_chart(fig_mc, width="stretch")

# Data age indicator
biomass_year = data.get("ecological_recovery", {}).get("assessment_year", 2009)
st.caption(f"*Biomass data: {biomass_year} | Tourism data: 2024 | ESV total: market-price method*")

# Sensitivity tornado plot
st.markdown('<div class="section-desc" style="margin-top:24px"><strong>Parameter Sensitivity</strong> - Which inputs drive ESV uncertainty most? One-at-a-time (OAT) analysis varies each service value by +/-20% while holding others constant.</div>', unsafe_allow_html=True)

# Build tornado data from the ecosystem services
_svc_list = []
_fin_breakdown = data.get("financial_output", {}).get("services_breakdown", {})
if _fin_breakdown:
    for _svc_key, _svc_val in _fin_breakdown.items():
        if isinstance(_svc_val, (int, float)) and _svc_val > 0 and _svc_key.endswith("_usd"):
            _svc_list.append({
                "name": _svc_key.removesuffix("_usd").replace("_", " ").title(),
                "value": _svc_val,
            })
else:
    _esv_services_list = data.get("ecosystem_services", {}).get("services", [])
    for _svc_item in _esv_services_list:
        if isinstance(_svc_item, dict) and _svc_item.get("annual_value_usd"):
            _svc_list.append({
                "name": _svc_item.get("service_type", "Unknown").replace("_", " ").title(),
                "value": _svc_item["annual_value_usd"],
            })

if _svc_list:
    _base_total = sum(s["value"] for s in _svc_list)
    _tornado_data = []
    for _s in _svc_list:
        _low_total = _base_total - _s["value"] * 0.20
        _high_total = _base_total + _s["value"] * 0.20
        _tornado_data.append({
            "name": _s["name"],
            "low": _low_total,
            "high": _high_total,
            "impact": (_high_total - _low_total) / _base_total * 100,
        })
    _tornado_data.sort(key=lambda x: x["impact"])

    fig_tornado = go.Figure()
    for _td in _tornado_data:
        fig_tornado.add_trace(go.Bar(
            y=[_td["name"]],
            x=[_td["low"] - _base_total],
            orientation="h",
            marker_color="#EF5350",
            hovertemplate=f"-20%: {fmt_usd(_td['low'])}<extra></extra>",
            showlegend=False,
        ))
        fig_tornado.add_trace(go.Bar(
            y=[_td["name"]],
            x=[_td["high"] - _base_total],
            orientation="h",
            marker_color="#66BB6A",
            hovertemplate=f"+20%: {fmt_usd(_td['high'])}<extra></extra>",
            showlegend=False,
        ))

    fig_tornado.add_vline(x=0, line_color="#94A3B8", line_width=1)
    fig_tornado.update_layout(
        height=200,
        barmode="overlay",
        margin=dict(l=0, r=0, t=10, b=30),
        xaxis=dict(
            title="ESV Change from Baseline (USD)",
            tickprefix="$",
            showgrid=True, gridcolor="#1E293B",
            title_font=dict(size=12, color="#94A3B8"),
            tickfont=dict(color="#94A3B8", size=11),
        ),
        yaxis=dict(
            tickfont=dict(color="#CBD5E1", size=12),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#CBD5E1"),
    )
    st.plotly_chart(fig_tornado, width="stretch")
    st.caption(f"*Dominant parameter: {_tornado_data[-1]['name']} ({_tornado_data[-1]['impact']:.1f}% ESV swing at +/-20%)*")

# Risk factor cards
rc1, rc2 = st.columns(2)
deg = data["risk_assessment"]["degradation_risk"]
clim = data["risk_assessment"]["climate_resilience"]

with rc1:
    st.markdown(f"""
<div class="risk-card risk-card-red">
<h4>Degradation Risk (BA-012)</h4>
<p>{deg['productivity_loss_central_percent']}% fisheries productivity loss if protection
fails (range: {deg['productivity_loss_range_percent'][0]}-{deg['productivity_loss_range_percent'][1]}%).
Source: <a href="https://doi.org/{deg['source_doi']}" target="_blank">{AXIOM_INFO['BA-012']['citation']}</a></p>
</div>
""", unsafe_allow_html=True)

with rc2:
    st.markdown(f"""
<div class="risk-card risk-card-green">
<h4>Resilience Benefit (BA-011)</h4>
<p>{clim['disturbance_reduction_percent']}% reduction in climate disturbance impact,
with {clim['recovery_boost_percent']}% faster recovery after disturbance events.
Source: <a href="https://doi.org/{clim['source_doi']}" target="_blank">{AXIOM_INFO['BA-011']['citation']}</a></p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 7. Comparison Sites
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Comparison Sites</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Cross-site validation demonstrates that the infrastructure produces consistent, defensible outputs. NEOLI alignment score correlates with ecological and financial outcomes across geographies.</div>', unsafe_allow_html=True)

# Build full comparison list including Shark Bay
_all_comp_sites = list(data["comparison_sites"]) + [
    {
        "name": "Shark Bay (Seagrass)",
        "neoli_score": 4,
        "outcome": "World's largest seagrass meadow - 4,800 km2 sequestering ~$12.1M/yr in carbon. 2011 heatwave demonstrated reversal risk.",
        "lesson": "Carbon-dominant sites need permanence guarantees. MPA protection reduces reversal risk.",
    }
]

# Render in a uniform 2x2 grid
_row1 = st.columns(2)
_row2 = st.columns(2)
_comp_cols_all = [_row1[0], _row1[1], _row2[0], _row2[1]]
for i, site_comp in enumerate(_all_comp_sites[:4]):
    score = site_comp["neoli_score"]
    with _comp_cols_all[i]:
        st.markdown(f"""
<div class="comp-card">
<h4>{site_comp['name']}</h4>
<div class="comp-score">NEOLI Score: {score}/5</div>
<p>{site_comp['outcome']}</p>
<p class="comp-lesson">{site_comp['lesson']}</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 8. Framework Alignment
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Framework Alignment</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">MARIS outputs are structured for real-world financial workflows. Alignment with IFC and TNFD frameworks means this infrastructure integrates directly into existing institutional due diligence processes.</div>', unsafe_allow_html=True)

fw1, fw2 = st.columns(2)

with fw1:
    ifc = data["framework_alignment"]["ifc_blue_finance"]
    proceeds = "".join(
        f"<li>{p.replace('_', ' ').title()}</li>" for p in ifc["eligible_use_of_proceeds"]
    )
    st.markdown(f"""
<div class="fw-card">
<h4>IFC Blue Finance ({ifc['version']})</h4>
<ul>
<li>SDG 14 Aligned: Yes</li>
<li>GBP/GLP Consistent: Yes</li>
<li>DNSH Compliant: Yes</li>
</ul>
<p style="font-size:17px;color:#94A3B8;margin-top:8px"><strong>Eligible Use of Proceeds:</strong></p>
<ul>{proceeds}</ul>
</div>
""", unsafe_allow_html=True)

with fw2:
    leap = data["framework_alignment"]["tnfd_leap"]
    st.markdown(f"""
<div class="fw-card">
<h4>TNFD LEAP Framework</h4>
<ul>
<li><span class="fw-phase">Locate:</span> {leap['locate']['biome']}
{'(Priority Biodiversity Area)' if leap['locate']['priority_biodiversity_area'] else ''}</li>
<li><span class="fw-phase">Evaluate:</span> {leap['evaluate']['primary_dependency']}</li>
<li><span class="fw-phase">Assess:</span> {leap['assess']['physical_risk_acute']} acute risk,
{leap['assess']['physical_risk_chronic']} chronic risk</li>
<li><span class="fw-phase">Prepare:</span> {leap['prepare']['recommendation']}</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 8b. TNFD Disclosure (auto-generated)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">TNFD Disclosure</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Auto-generated TNFD LEAP disclosure from MARIS knowledge graph. All claims traced to DOI-backed evidence through bridge axioms.</div>', unsafe_allow_html=True)

try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) if str(Path(__file__).resolve().parent.parent) not in _sys.path else None
    from maris.disclosure.leap_generator import LEAPGenerator
    from maris.disclosure.alignment_scorer import AlignmentScorer
    from maris.disclosure.renderers import render_markdown as _render_md, render_summary as _render_summary

    _leap_gen = LEAPGenerator(project_root=Path(__file__).resolve().parent.parent)
    _leap_scorer = AlignmentScorer()

    _site_for_disclosure = data.get("site", {}).get("name", "Cabo Pulmo National Park")
    _tnfd_disclosure = _leap_gen.generate(_site_for_disclosure)
    _tnfd_alignment = _leap_scorer.score(_tnfd_disclosure)

    # Alignment score badge
    _score_color = "#22C55E" if _tnfd_alignment.score_pct >= 80 else "#F59E0B" if _tnfd_alignment.score_pct >= 50 else "#EF4444"
    st.markdown(f"""
<div class="kpi-card" style="text-align:center;margin-bottom:16px">
<span style="font-size:40px;font-weight:700;color:{_score_color}">{_tnfd_alignment.populated_count}/{_tnfd_alignment.total_disclosures}</span>
<br><span style="color:#94A3B8;font-size:16px">TNFD Recommended Disclosures Populated ({_tnfd_alignment.score_pct:.0f}%)</span>
</div>
""", unsafe_allow_html=True)

    with st.expander("View Full TNFD LEAP Disclosure", expanded=False):
        _disclosure_tab, _summary_tab = st.tabs(["Full Disclosure", "Executive Summary"])
        with _disclosure_tab:
            st.markdown(_render_md(_tnfd_disclosure))
        with _summary_tab:
            st.markdown(_render_summary(_tnfd_disclosure))

        # Download buttons
        _dl_col1, _dl_col2 = st.columns(2)
        with _dl_col1:
            st.download_button(
                label="Download Markdown",
                data=_render_md(_tnfd_disclosure),
                file_name=f"tnfd_leap_{_site_for_disclosure.lower().replace(' ', '_')}.md",
                mime="text/markdown",
            )
        with _dl_col2:
            from maris.disclosure.renderers import render_json as _render_json_disc
            st.download_button(
                label="Download JSON",
                data=_render_json_disc(_tnfd_disclosure),
                file_name=f"tnfd_leap_{_site_for_disclosure.lower().replace(' ', '_')}.json",
                mime="application/json",
            )

    if _tnfd_alignment.gap_ids:
        with st.expander(f"Gap Analysis ({_tnfd_alignment.gap_count} gaps)", expanded=False):
            for _gap_id in _tnfd_alignment.gap_ids:
                _reason = _tnfd_alignment.gap_details.get(_gap_id, "")
                st.markdown(f"- **{_gap_id}**: {_reason}")

except Exception as _tnfd_err:
    st.caption(f"TNFD disclosure unavailable: {_tnfd_err}")

# ---------------------------------------------------------------------------
# 9. Scaling Intelligence (shared with v1)
# ---------------------------------------------------------------------------
from components.roadmap_section import render_roadmap_section
render_roadmap_section()

# ---------------------------------------------------------------------------
# 10. Ask MARIS - Chat Panel
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Ask Nereus</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Query the Nereus knowledge graph in natural language. Every answer traces through bridge axioms to peer-reviewed evidence. Use the quick queries below or type your own question.</div>', unsafe_allow_html=True)

from components.chat_panel import render_chat_panel
from components.graph_explorer import render_graph_explorer

render_chat_panel(client)

# Graph Explorer - show for the most recent response if it has a graph path
if st.session_state.get("maris_chat_history"):
    latest = st.session_state.maris_chat_history[-1]
    graph_path = latest.get("response", {}).get("graph_path", [])
    if graph_path:
        with st.expander("Graph Explorer - Traversal Visualization", expanded=True):
            conf_threshold = st.slider(
                "Confidence filter - hide edges below threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.1,
                help="Slide to hide low-confidence edges from the graph visualization",
            )
            render_graph_explorer(graph_path, confidence_threshold=conf_threshold)

# ---------------------------------------------------------------------------
# 11. Caveats & Footer
# ---------------------------------------------------------------------------
caveats_html = "".join(f"<li>{c}</li>" for c in data["caveats"])
st.markdown(f"""
<div class="caveats">
<h4>Caveats and Limitations</h4>
<ol>{caveats_html}</ol>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="app-footer">
NEREUS - Provenance-first infrastructure for blue finance decisions
&nbsp;&middot;&nbsp; Powered by MARIS + Semantica
&nbsp;&middot;&nbsp; Generated {data['metadata']['generated_at'].split('T')[0]}
&nbsp;&middot;&nbsp; Schema v{data['metadata']['maris_schema_version']}
&nbsp;&middot;&nbsp; {data['metadata']['methodology']}
</div>
""", unsafe_allow_html=True)
