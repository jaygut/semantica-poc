"""Shared CSS, color constants, formatters, and utilities for v3 components."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------
COLORS: dict[str, str] = {
    "bg_app": "#0B1120",
    "bg_sidebar": "#060D1A",
    "bg_card": "linear-gradient(145deg, #162039 0%, #1A2744 100%)",
    "border_subtle": "#243352",
    "border_section": "#1E293B",
    "text_heading": "#E2E8F0",
    "text_body": "#B0BEC5",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "accent_blue": "#5B9BD5",
    "accent_purple": "#7C3AED",
    "accent_teal": "#1ABC9C",
    "accent_amber": "#D97706",
    "success": "#66BB6A",
    "danger": "#EF5350",
    "warning": "#FFA726",
    # Evidence tiers
    "tier_t1": "#2ECC71",
    "tier_t2": "#3498DB",
    "tier_t3": "#E67E22",
    "tier_t4": "#E74C3C",
    # Node types (for graph viz)
    "node_mpa": "#F1C40F",
    "node_species": "#059669",
    "node_service": "#1ABC9C",
    "node_axiom": "#7C3AED",
    "node_habitat": "#10B981",
    "node_document": "#3498DB",
}

# ---------------------------------------------------------------------------
# CSS - reuse v2 dark-mode palette, add v3 classes
# ---------------------------------------------------------------------------
V3_CSS = """
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
    .section-desc {
        font-size: 19px;
        color: #94A3B8;
        margin-bottom: 20px;
        line-height: 1.6;
    }
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
    .thesis-body strong { color: #CBD5E1; }

    /* ---- Risk Cards ---- */
    .risk-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 24px 28px;
        border: 1px solid #243352;
    }
    .risk-card-red { border-left: 3px solid #EF5350; }
    .risk-card-green { border-left: 3px solid #66BB6A; }
    .risk-card h4 { font-size: 21px; font-weight: 600; color: #E2E8F0 !important; margin: 0 0 10px 0; }
    .risk-card p { font-size: 18px; color: #B0BEC5; margin: 0; line-height: 1.6; }
    .risk-card a { color: #5B9BD5; text-decoration: none; }
    .risk-card a:hover { text-decoration: underline; }

    /* ---- Framework Cards ---- */
    .fw-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        padding: 24px 28px;
        border: 1px solid #243352;
        height: 100%;
    }
    .fw-card h4 { font-size: 20px; font-weight: 600; color: #E2E8F0 !important; margin: 0 0 14px 0; text-transform: uppercase; letter-spacing: 1px; }
    .fw-card li { font-size: 18px; color: #B0BEC5; line-height: 1.7; }
    .fw-card p { color: #B0BEC5; font-size: 17px; }
    .fw-card strong { color: #CBD5E1; }
    .fw-phase { font-weight: 600; color: #5B9BD5; }

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
        text-align: left; padding: 16px 24px; font-size: 14px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 1.5px; color: #94A3B8;
        border-bottom: 1px solid #243352; background: rgba(10, 18, 38, 0.5);
    }
    .evidence-table td {
        padding: 16px 24px; color: #CBD5E1; border-bottom: 1px solid #1E2D48;
        vertical-align: top; line-height: 1.6;
    }
    .evidence-table tr:last-child td { border-bottom: none; }
    .evidence-table .axiom-id { font-weight: 600; color: #5B9BD5; white-space: nowrap; font-size: 17px; }
    .evidence-table a { color: #5B9BD5; text-decoration: none; font-weight: 500; }
    .evidence-table a:hover { text-decoration: underline; }

    /* ---- Caveats ---- */
    .caveats {
        background: #0D1526; border: 1px solid #1E293B; border-radius: 10px;
        padding: 28px 32px; margin-top: 52px; font-size: 17px;
        color: #94A3B8; line-height: 1.7;
    }
    .caveats h4 { font-size: 15px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #64748B !important; margin: 0 0 12px 0; }
    .caveats ol { padding-left: 20px; margin: 0; }
    .caveats li { color: #94A3B8 !important; }

    /* ---- Footer ---- */
    .app-footer {
        text-align: center; font-size: 14px; color: #64748B;
        padding: 24px 0 12px 0; border-top: 1px solid #1E293B; margin-top: 24px;
    }

    /* ---- Connection status ---- */
    .conn-status {
        display: inline-flex; align-items: center; gap: 6px; font-size: 13px;
        padding: 4px 12px; border-radius: 4px; font-weight: 500;
    }
    .conn-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .conn-live .conn-dot { background: #66BB6A; }
    .conn-live { color: #66BB6A; background: rgba(46, 125, 50, 0.15); border: 1px solid rgba(46, 125, 50, 0.3); }
    .conn-static .conn-dot { background: #FFA726; }
    .conn-static { color: #FFA726; background: rgba(245, 166, 35, 0.15); border: 1px solid rgba(245, 166, 35, 0.3); }

    /* ---- Plotly overrides ---- */
    .stPlotlyChart {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px; border: 1px solid #243352; padding: 8px;
    }

    /* ---- Quick query buttons ---- */
    .stApp [data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: rgba(91, 155, 213, 0.1) !important;
        border: 1px solid rgba(91, 155, 213, 0.3) !important;
        color: #5B9BD5 !important;
        border-radius: 20px !important; font-size: 13px !important;
        font-weight: 500 !important; padding: 6px 16px !important;
        white-space: nowrap !important; transition: all 0.2s ease !important;
    }
    .stApp [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: rgba(91, 155, 213, 0.2) !important;
        border-color: rgba(91, 155, 213, 0.5) !important;
    }

    /* ---- Chat input ---- */
    .stApp .stTextInput input {
        background: #0F1A2E !important; border: 1px solid #1E293B !important;
        color: #E2E8F0 !important; border-radius: 8px !important;
        font-size: 15px !important; padding: 10px 16px !important;
    }
    .stApp .stTextInput input::placeholder { color: #64748B !important; }
    .stApp .stTextInput input:focus {
        border-color: #5B9BD5 !important;
        box-shadow: 0 0 0 1px rgba(91, 155, 213, 0.3) !important;
    }

    /* ---- v3 NEW: Pipeline steps ---- */
    .pipeline-step {
        background: linear-gradient(145deg, #0F1A2E 0%, #162039 100%);
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #94A3B8;
        transition: border-color 0.3s ease;
    }
    .pipeline-step .step-header {
        display: flex; align-items: center; gap: 10px;
        font-weight: 600; color: #CBD5E1; font-size: 14px;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }
    .pipeline-step .step-num {
        width: 24px; height: 24px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 700;
    }
    .pipeline-step.complete { border-color: #22C55E; }
    .pipeline-step.complete .step-num { background: rgba(34, 197, 94, 0.2); color: #22C55E; }
    .pipeline-step.active { border-color: #5B9BD5; }
    .pipeline-step.active .step-num { background: rgba(91, 155, 213, 0.2); color: #5B9BD5; }
    .pipeline-step.pending { border-color: #1E293B; }
    .pipeline-step.pending .step-num { background: rgba(100, 116, 139, 0.2); color: #64748B; }
    .pipeline-step .step-detail {
        font-size: 13px; color: #94A3B8; line-height: 1.6;
        padding-left: 34px;
    }
    .pipeline-step .step-detail code {
        background: rgba(91, 155, 213, 0.1); color: #5B9BD5;
        padding: 2px 6px; border-radius: 3px; font-size: 12px;
    }

    /* ---- v3 NEW: Split panel ---- */
    .split-panel { display: flex; gap: 20px; }

    /* ---- v3 NEW: Cypher block ---- */
    .cypher-block {
        background: #0A0F1C; border: 1px solid #1E293B; border-radius: 6px;
        padding: 12px 16px; font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 12px; color: #5B9BD5; overflow-x: auto;
        line-height: 1.5; white-space: pre-wrap; word-break: break-word;
    }

    /* ---- v3 NEW: Confidence gauge ---- */
    .confidence-gauge {
        display: inline-flex; align-items: center; gap: 8px;
    }
    .confidence-gauge .gauge-bar {
        height: 8px; border-radius: 4px; background: #1E293B; width: 120px; overflow: hidden;
    }
    .confidence-gauge .gauge-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }

    /* ---- v3 NEW: Parameter impact ---- */
    .parameter-impact {
        font-weight: 600; font-size: 16px; display: inline-block;
        padding: 2px 8px; border-radius: 4px;
    }
    .parameter-impact.positive { color: #22C55E; background: rgba(34, 197, 94, 0.1); }
    .parameter-impact.negative { color: #EF4444; background: rgba(239, 68, 68, 0.1); }
    .parameter-impact.neutral { color: #94A3B8; background: rgba(148, 163, 184, 0.1); }

    /* ---- v3 NEW: Tab container ---- */
    .tab-container { padding: 0 4px; }

    /* ---- v3 NEW: NEOLI dots ---- */
    .neoli-row { display: flex; gap: 10px; align-items: center; margin: 6px 0; }
    .neoli-dot { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
    .neoli-filled { background-color: #66BB6A; }
    .neoli-empty { background-color: #1E293B; border: 1px solid #334155; }
    .neoli-label { font-size: 18px; color: #B0BEC5 !important; }

    /* ---- v3 NEW: Comparison Cards ---- */
    .comp-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px; padding: 24px 28px; border: 1px solid #243352; height: 100%;
    }
    .comp-card h4 { font-size: 21px; font-weight: 600; color: #E2E8F0 !important; margin: 0 0 8px 0; }
    .comp-score { font-size: 17px; font-weight: 600; color: #5B9BD5; margin-bottom: 12px; }
    .comp-card p { font-size: 18px; color: #B0BEC5; line-height: 1.5; margin: 0 0 8px 0; }

    /* ---- v3 NEW: Pillar progress bars ---- */
    .pillar-bar {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px; padding: 18px 22px; border: 1px solid #243352;
        text-align: center;
    }
    .pillar-bar .pillar-name {
        font-size: 13px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 1px; color: #94A3B8; margin-bottom: 8px;
    }
    .pillar-bar .pillar-score {
        font-size: 24px; font-weight: 700; color: #E2E8F0; margin-bottom: 6px;
    }
    .pillar-bar .pillar-fill-bg {
        height: 6px; border-radius: 3px; background: #1E293B; overflow: hidden;
    }
    .pillar-bar .pillar-fill {
        height: 100%; border-radius: 3px; transition: width 0.4s ease;
    }
</style>
"""

# ---------------------------------------------------------------------------
# Formatting utilities
# ---------------------------------------------------------------------------


def fmt_usd(val: float | int) -> str:
    """Format USD value as $X.XM or $X.XK."""
    if abs(val) >= 1e6:
        return f"${val / 1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val / 1e3:.0f}K"
    return f"${val:,.0f}"


def fmt_pct(val: float) -> str:
    """Format a decimal as a percentage string."""
    return f"{val * 100:.1f}%"


def confidence_badge(score: float) -> str:
    """Return HTML for a color-coded confidence badge."""
    if score >= 0.8:
        color, bg, border = "#66BB6A", "rgba(46,125,50,0.2)", "rgba(46,125,50,0.35)"
    elif score >= 0.6:
        color, bg, border = "#FFA726", "rgba(245,166,35,0.2)", "rgba(245,166,35,0.35)"
    else:
        color, bg, border = "#EF5350", "rgba(239,83,80,0.2)", "rgba(239,83,80,0.35)"
    pct = int(score * 100)
    return (
        f'<span style="display:inline-block;padding:5px 14px;border-radius:4px;'
        f"font-size:14px;font-weight:600;letter-spacing:0.5px;"
        f"color:{color};background:{bg};border:1px solid {border};"
        f'text-transform:uppercase">'
        f"Confidence: {pct}%</span>"
    )


def tier_badge(tier: str) -> str:
    """Return HTML for an evidence tier badge."""
    tier_colors = {
        "T1": ("#2ECC71", "rgba(46,204,113,0.15)"),
        "T2": ("#3498DB", "rgba(52,152,219,0.15)"),
        "T3": ("#E67E22", "rgba(230,126,34,0.15)"),
        "T4": ("#E74C3C", "rgba(231,76,60,0.15)"),
    }
    color, bg = tier_colors.get(tier, ("#94A3B8", "rgba(148,163,184,0.15)"))
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:4px;'
        f"font-size:12px;font-weight:600;color:{color};background:{bg};"
        f'border:1px solid {color}40">{tier}</span>'
    )


def axiom_tag(axiom_id: str) -> str:
    """Return HTML for an axiom pill tag."""
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
        f"font-size:13px;font-weight:600;margin-right:6px;margin-bottom:4px;"
        f"color:#5B9BD5;background:rgba(91,155,213,0.15);"
        f'border:1px solid rgba(91,155,213,0.3)">{axiom_id}</span>'
    )


def render_service_health(status: dict[str, bool]) -> str:
    """Return sidebar health indicator HTML."""
    items = ""
    labels = {"neo4j": "Neo4j", "llm": "LLM API", "api": "MARIS API"}
    for key, label in labels.items():
        ok = status.get(key, False)
        dot_color = "#66BB6A" if ok else "#EF5350"
        text = "Connected" if ok else "Unavailable"
        items += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{dot_color};'
            f'display:inline-block"></span>'
            f'<span style="font-size:13px;color:#94A3B8">{label}: {text}</span></div>'
        )
    return f'<div style="margin:8px 0">{items}</div>'


# ---------------------------------------------------------------------------
# Service health checker
# ---------------------------------------------------------------------------


def check_services(api_base: str = "http://localhost:8000") -> dict[str, bool]:
    """Check Neo4j, LLM, and API connectivity. Returns status dict."""
    result = {"neo4j": False, "llm": False, "api": False}
    try:
        import requests

        resp = requests.get(f"{api_base}/api/health", timeout=3)
        if resp.status_code == 200:
            result["api"] = True
            data = resp.json()
            result["neo4j"] = data.get("neo4j_connected", False)
            result["llm"] = data.get("llm_available", False)
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Data loading utilities
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_CASE_STUDY_MAP: dict[str, str] = {
    "Cabo Pulmo National Park": "examples/cabo_pulmo_case_study.json",
    "Shark Bay World Heritage Area": "examples/shark_bay_case_study.json",
}


def get_case_study_path(site_name: str) -> Path | None:
    """Resolve canonical site name to case study JSON path."""
    rel = _CASE_STUDY_MAP.get(site_name)
    if rel is None:
        return None
    return _PROJECT_ROOT / rel


def get_site_data(site_name: str, bundle_data: dict[str, Any]) -> dict[str, Any]:
    """Extract site-specific data from bundle or case study JSON.

    For Cabo Pulmo, the static bundle is preferred (richer structure).
    For other sites, loads from case study JSON on disk.
    """
    if site_name == "Cabo Pulmo National Park":
        return bundle_data

    case_path = get_case_study_path(site_name)
    if case_path and case_path.exists():
        try:
            with open(case_path) as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to load case study for %s", site_name)

    return bundle_data
