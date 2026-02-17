"""Nereus v4 Intelligence Platform - Global Scaling Dashboard.

Registry-driven, multi-site dashboard. All site lists are discovered
dynamically from ``examples/*_case_study.json`` - no hardcoded site names.
Runs on port 8504 by default.

Usage:
    cd investor_demo
    streamlit run streamlit_app_v4.py --server.port 8504
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load .env from project root so MARIS_* vars are available
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from investor_demo.components.v4.shared import (  # noqa: E402
    V4_CSS,
    check_services,
    get_all_sites,
    get_site_data,
    get_site_summary,
    get_site_tier,
    is_feature_available,
    render_service_health,
)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Nereus Intelligence Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
st.markdown(V4_CSS, unsafe_allow_html=True)

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


bundle_data = _load_bundle()

# ---------------------------------------------------------------------------
# Dynamic Site Discovery
# ---------------------------------------------------------------------------
all_sites = get_all_sites()
site_names = [s["name"] for s in all_sites]

if not site_names:
    st.error(
        "No case study files found in examples/. "
        "Add *_case_study.json files to populate the portfolio."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "v4_mode" not in st.session_state:
    st.session_state.v4_mode = "demo"
if "v4_site" not in st.session_state:
    st.session_state.v4_site = site_names[0]
if "v4_chat_history" not in st.session_state:
    st.session_state.v4_chat_history = []
if "v4_scenario" not in st.session_state:
    st.session_state.v4_scenario = "p50"
if "v4_neo4j_ok" not in st.session_state:
    st.session_state.v4_neo4j_ok = False
if "v4_llm_ok" not in st.session_state:
    st.session_state.v4_llm_ok = False

# ---------------------------------------------------------------------------
# API Client (lazy init based on mode)
# ---------------------------------------------------------------------------
_V4_PRECOMPUTED = Path(__file__).parent / "precomputed_responses_v4.json"

if "v4_client" not in st.session_state:
    from api_client import get_client, StaticBundleClient as _SBC
    _client = get_client()
    # If static fallback, prefer the v4-specific precomputed file
    if not _client.is_live and _V4_PRECOMPUTED.exists():
        _client = _SBC(precomputed_path=_V4_PRECOMPUTED)
    st.session_state.v4_client = _client

client = st.session_state.v4_client

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### NEREUS")

    # Mode toggle
    live_mode = st.toggle(
        "Live Intelligence Mode",
        value=st.session_state.v4_mode == "live",
        help="Switch between live (Neo4j + LLM) and demo (precomputed) modes",
        key="v4_live_toggle",
    )
    new_mode = "live" if live_mode else "demo"
    if new_mode != st.session_state.v4_mode:
        st.session_state.v4_mode = new_mode
        if new_mode == "live":
            from api_client import LiveAPIClient
            st.session_state.v4_client = LiveAPIClient(
                api_key=os.environ.get("MARIS_API_KEY", "")
            )
        else:
            from api_client import StaticBundleClient
            st.session_state.v4_client = StaticBundleClient(
                precomputed_path=_V4_PRECOMPUTED
            )
        client = st.session_state.v4_client

    # Service health panel
    if st.session_state.v4_mode == "live":
        status = check_services()
        st.session_state.v4_neo4j_ok = status["neo4j"]
        st.session_state.v4_llm_ok = status["llm"]
        st.markdown(render_service_health(status), unsafe_allow_html=True)
        if not status["api"]:
            if status["neo4j"] and status["llm"]:
                st.info(
                    "Neo4j and LLM are ready. Start the API server to unlock live queries:\n\n"
                    "```\nMARIS_DEMO_MODE=true uvicorn maris.api.main:app --port 8000\n```"
                )
            elif status["neo4j"]:
                st.info(
                    "Neo4j is running. Start the API server:\n\n"
                    "```\nMARIS_DEMO_MODE=true uvicorn maris.api.main:app --port 8000\n```"
                )
            else:
                st.warning(
                    "MARIS API not running. Start it with:\n\n"
                    "```\nMARIS_DEMO_MODE=true uvicorn maris.api.main:app --port 8000\n```"
                )
            st.caption("Queries will use precomputed fallback until the API is started.")
    else:
        st.markdown(
            '<div class="conn-status conn-static">'
            '<span class="conn-dot"></span>Demo Mode - Precomputed</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Site selector - dynamic from discovered sites
    st.markdown("### Site Selection")
    selected_site = st.selectbox(
        "Select MPA site",
        site_names,
        index=site_names.index(st.session_state.v4_site)
        if st.session_state.v4_site in site_names
        else 0,
        label_visibility="collapsed",
        key="v4_site_select",
    )
    if selected_site != st.session_state.v4_site:
        st.session_state.v4_site = selected_site

    # Dynamic site summary
    summary = get_site_summary(selected_site)
    if summary:
        st.markdown(summary)

    # Tier indicator
    tier = get_site_tier(selected_site)
    tier_colors = {"Gold": "#F59E0B", "Silver": "#94A3B8", "Bronze": "#A0522D"}
    st.markdown(
        f'<span style="font-size:13px;font-weight:600;color:{tier_colors.get(tier, "#94A3B8")}">'
        f"Data Tier: {tier}</span>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Scenario selector
    st.markdown("### Scenario")
    scenario_choice = st.select_slider(
        "Valuation confidence",
        options=["Conservative (P5)", "Base Case (Median)", "Optimistic (P95)"],
        value="Base Case (Median)",
        key="v4_scenario_slider",
    )
    if "Conservative" in scenario_choice:
        st.session_state.v4_scenario = "p5"
    elif "Optimistic" in scenario_choice:
        st.session_state.v4_scenario = "p95"
    else:
        st.session_state.v4_scenario = "p50"

    st.markdown("---")

    # System metadata footer - dynamic counts
    n_sites = len(all_sites)
    st.markdown(
        f"<span style='font-size:13px;color:#64748B'>Sites: {n_sites} discovered</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span style='font-size:13px;color:#64748B'>Bridge Axioms: 16</span>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Load site-specific data
# ---------------------------------------------------------------------------
site = st.session_state.v4_site
mode = st.session_state.v4_mode
data = get_site_data(site, bundle_data)

if data is None:
    st.error(f"Failed to load data for {site}.")
    st.stop()

# ---------------------------------------------------------------------------
# Tab Structure (6 tabs - Portfolio Overview is new)
# ---------------------------------------------------------------------------
tab_names = [
    "Portfolio",
    "Intelligence Brief",
    "Ask Nereus",
    "Scenario Lab",
    "Site Intelligence",
    "TNFD Compliance",
]
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

tier = get_site_tier(site)

with tab0:
    from investor_demo.components.v4.portfolio_overview import render_portfolio_overview
    render_portfolio_overview()

with tab1:
    if is_feature_available(tier, "intelligence_brief"):
        from investor_demo.components.v4.intelligence_brief import render_intelligence_brief
        render_intelligence_brief(data, site, mode, scenario=st.session_state.v4_scenario)
    else:
        st.info(
            f"{site} has Bronze-tier data. Intelligence Brief requires Silver or Gold data quality. "
            "Add ecosystem service valuations to the case study JSON to unlock this tab."
        )

with tab2:
    if is_feature_available(tier, "graphrag_chat"):
        from investor_demo.components.v4.graphrag_chat import render_graphrag_chat
        render_graphrag_chat(data, site, mode, client=client)
    else:
        st.info(
            f"{site} has Bronze-tier data. Ask Nereus requires Silver or Gold data quality."
        )

with tab3:
    if is_feature_available(tier, "scenario_lab"):
        from investor_demo.components.v4.scenario_engine import render_scenario_engine
        render_scenario_engine(data, site, mode)
    else:
        st.info(
            f"{site} has Bronze-tier data. Scenario Lab requires Silver or Gold data quality."
        )

with tab4:
    from investor_demo.components.v4.site_intelligence import render_site_intelligence
    render_site_intelligence()

with tab5:
    if is_feature_available(tier, "tnfd_compliance"):
        from investor_demo.components.v4.tnfd_compliance import render_tnfd_compliance
        render_tnfd_compliance(data, site, mode)
    else:
        st.info(
            f"{site} has Bronze-tier data. TNFD Compliance requires Silver or Gold data quality."
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">'
    "NEREUS - Provenance-first infrastructure for blue finance decisions"
    " &middot; Powered by MARIS + Semantica"
    "</div>",
    unsafe_allow_html=True,
)
