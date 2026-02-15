"""MARIS v3 Intelligence Platform - Multi-tab dashboard.

A live intelligence platform that makes the P0-P4 infrastructure visible
and interactive. Every feature has dual-mode operation: LIVE (Neo4j + LLM)
and DEMO (precomputed + static bundle).
"""

import json
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from investor_demo.components.v3.shared import (  # noqa: E402
    V3_CSS,
    check_services,
    get_site_data,
    render_service_health,
)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MARIS Intelligence Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
st.markdown(V3_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data Loading (cached)
# ---------------------------------------------------------------------------


@st.cache_data
def _load_bundle() -> dict | None:
    """Load the static Cabo Pulmo bundle as fallback data."""
    bundle_path = (
        Path(__file__).parent / ".." / "demos" / "context_graph_demo"
        / "cabo_pulmo_investment_grade_bundle.json"
    )
    if not bundle_path.exists():
        bundle_path = Path(
            "../demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json"
        )
    if not bundle_path.exists():
        return None
    with open(bundle_path) as f:
        return json.load(f)


@st.cache_data
def _load_case_study(path_str: str) -> dict | None:
    """Load a case study JSON by path string."""
    p = Path(path_str)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


bundle_data = _load_bundle()
if not bundle_data:
    st.error(
        "Data bundle not found. Run the notebook to generate "
        "cabo_pulmo_investment_grade_bundle.json first."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "v3_mode" not in st.session_state:
    st.session_state.v3_mode = "demo"
if "v3_site" not in st.session_state:
    st.session_state.v3_site = "Cabo Pulmo National Park"
if "v3_chat_history" not in st.session_state:
    st.session_state.v3_chat_history = []
if "v3_scenario" not in st.session_state:
    st.session_state.v3_scenario = "p50"
if "v3_neo4j_ok" not in st.session_state:
    st.session_state.v3_neo4j_ok = False
if "v3_llm_ok" not in st.session_state:
    st.session_state.v3_llm_ok = False

# ---------------------------------------------------------------------------
# API Client (lazy init based on mode)
# ---------------------------------------------------------------------------
if "v3_client" not in st.session_state:
    from api_client import get_client
    st.session_state.v3_client = get_client()

client = st.session_state.v3_client

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### MARIS | Intelligence Platform")

    # Mode toggle
    live_mode = st.toggle(
        "Live Intelligence Mode",
        value=st.session_state.v3_mode == "live",
        help="Switch between live (Neo4j + LLM) and demo (precomputed) modes",
    )
    new_mode = "live" if live_mode else "demo"
    if new_mode != st.session_state.v3_mode:
        st.session_state.v3_mode = new_mode
        # Re-initialize client on mode change
        if new_mode == "live":
            from api_client import LiveAPIClient
            import os
            st.session_state.v3_client = LiveAPIClient(
                api_key=os.environ.get("MARIS_API_KEY", "")
            )
        else:
            from api_client import StaticBundleClient
            st.session_state.v3_client = StaticBundleClient()
        client = st.session_state.v3_client

    # Service health panel
    if st.session_state.v3_mode == "live":
        status = check_services()
        st.session_state.v3_neo4j_ok = status["neo4j"]
        st.session_state.v3_llm_ok = status["llm"]
        st.markdown(render_service_health(status), unsafe_allow_html=True)
        if not status["api"]:
            st.warning("MARIS API not reachable. Queries will use precomputed fallback.")
    else:
        st.markdown(
            '<div class="conn-status conn-static">'
            '<span class="conn-dot"></span>Demo Mode - Precomputed</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Site selector
    st.markdown("### Site Selection")
    site_options = ["Cabo Pulmo National Park", "Shark Bay World Heritage Area"]
    selected_site = st.selectbox(
        "Select MPA site",
        site_options,
        index=site_options.index(st.session_state.v3_site)
        if st.session_state.v3_site in site_options
        else 0,
        label_visibility="collapsed",
    )
    if selected_site != st.session_state.v3_site:
        st.session_state.v3_site = selected_site

    # Site summary
    if selected_site == "Cabo Pulmo National Park":
        st.markdown(
            "**Mexico** - 71 km2 - Est. 1995\n"
            "Coral reef - Tourism-dominant - $29.27M ESV"
        )
    else:
        st.markdown(
            "**Australia** - 23,000 km2 - Est. 1991\n"
            "Seagrass - Carbon-dominant - $21.5M ESV"
        )

    st.markdown("---")

    # Scenario selector
    st.markdown("### Scenario")
    scenario_choice = st.select_slider(
        "Valuation confidence",
        options=["Conservative (P5)", "Base Case (Median)", "Optimistic (P95)"],
        value="Base Case (Median)",
    )
    if "Conservative" in scenario_choice:
        st.session_state.v3_scenario = "p5"
    elif "Optimistic" in scenario_choice:
        st.session_state.v3_scenario = "p95"
    else:
        st.session_state.v3_scenario = "p50"

    st.markdown("---")

    # System metadata footer
    st.markdown(
        f"<span style='font-size:13px;color:#64748B'>"
        f"Schema: v{bundle_data['metadata']['maris_schema_version']}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span style='font-size:13px;color:#64748B'>Sites: 2 characterized, 2 comparison</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span style='font-size:13px;color:#64748B'>Bridge Axioms: 16</span>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Load site-specific data
# ---------------------------------------------------------------------------
site = st.session_state.v3_site
mode = st.session_state.v3_mode
data = get_site_data(site, bundle_data)

# ---------------------------------------------------------------------------
# Tab Structure
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Intelligence Brief",
    "Ask MARIS",
    "Scenario Lab",
    "Site Scout",
    "TNFD Compliance",
])

with tab1:
    from investor_demo.components.v3.intelligence_brief import render_intelligence_brief
    render_intelligence_brief(data, site, mode)

with tab2:
    from investor_demo.components.v3.graphrag_chat import render_graphrag_chat
    render_graphrag_chat(data, site, mode, client=client)

with tab3:
    from investor_demo.components.v3.scenario_engine import render_scenario_engine
    render_scenario_engine(data, site, mode)

with tab4:
    # DEFERRED - placeholder only
    st.markdown("### Site Scout")
    st.info(
        "Live MPA characterization coming soon. The auto-characterization pipeline "
        "(OBIS/WoRMS/Marine Regions) is built and tested - integration into v3 "
        "dashboard is planned for the next release."
    )
    st.markdown(
        '<div class="thesis-block">'
        '<div class="thesis-lead">Pipeline Ready, Dashboard Pending</div>'
        '<div class="thesis-body">'
        "The <strong>SiteCharacterizer</strong> can characterize any MPA on Earth "
        "using OBIS, WoRMS, and Marine Regions APIs. It performs a 5-step pipeline: "
        "Locate, Populate, Characterize (Bronze/Silver/Gold), Estimate ESV, and Score. "
        "28 unit tests verify the pipeline. Dashboard integration is deferred to reduce "
        "demo risk from flaky external APIs."
        "</div></div>",
        unsafe_allow_html=True,
    )

with tab5:
    from investor_demo.components.v3.tnfd_compliance import render_tnfd_compliance
    render_tnfd_compliance(data, site, mode)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">'
    "MARIS Intelligence Platform | SEMANTICA - Provenance-first infrastructure "
    "for blue finance decisions"
    "</div>",
    unsafe_allow_html=True,
)
