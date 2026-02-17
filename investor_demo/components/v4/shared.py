"""Shared CSS, color constants, formatters, and utilities for v4 components.

Key difference from v3: all site lists are discovered dynamically from
``examples/*_case_study.json``. No hardcoded site maps.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color constants (identical to v3)
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
# Habitat display helpers
# ---------------------------------------------------------------------------
_HABITAT_DISPLAY: dict[str, str] = {
    "coral_reef": "Coral Reef",
    "seagrass_meadow": "Seagrass",
    "mangrove_forest": "Mangrove",
    "kelp_forest": "Kelp Forest",
    "mixed": "Mixed",
}

_HABITAT_COLORS: dict[str, str] = {
    "coral_reef": "#F59E0B",
    "seagrass_meadow": "#10B981",
    "mangrove_forest": "#059669",
    "kelp_forest": "#6366F1",
    "mixed": "#8B5CF6",
}

# ---------------------------------------------------------------------------
# CSS - reuse v3 dark-mode palette, add v4 portfolio classes
# ---------------------------------------------------------------------------
V4_CSS = """
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
    .masthead-powered {
        font-size: 12px;
        font-weight: 400;
        color: #64748B;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
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
        display: inline-flex; align-items: center; gap: 6px; font-size: 14px;
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
        border-radius: 20px !important; font-size: 14px !important;
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

    /* ---- Pipeline steps ---- */
    .pipeline-step {
        background: linear-gradient(145deg, #0F1A2E 0%, #162039 100%);
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
        font-size: 15px;
        color: #94A3B8;
        transition: border-color 0.3s ease;
    }
    .pipeline-step .step-header {
        display: flex; align-items: center; gap: 10px;
        font-weight: 600; color: #CBD5E1; font-size: 15px;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }
    .pipeline-step .step-num {
        width: 24px; height: 24px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 13px; font-weight: 700;
    }
    .pipeline-step.complete { border-color: #22C55E; }
    .pipeline-step.complete .step-num { background: rgba(34, 197, 94, 0.2); color: #22C55E; }
    .pipeline-step.active { border-color: #5B9BD5; }
    .pipeline-step.active .step-num { background: rgba(91, 155, 213, 0.2); color: #5B9BD5; }
    .pipeline-step.pending { border-color: #1E293B; }
    .pipeline-step.pending .step-num { background: rgba(100, 116, 139, 0.2); color: #64748B; }
    .pipeline-step .step-detail {
        font-size: 14px; color: #94A3B8; line-height: 1.6;
        padding-left: 34px;
    }
    .pipeline-step .step-detail code {
        background: rgba(91, 155, 213, 0.1); color: #5B9BD5;
        padding: 2px 6px; border-radius: 3px; font-size: 13px;
    }

    /* ---- Split panel ---- */
    .split-panel { display: flex; gap: 20px; }

    /* ---- Cypher block ---- */
    .cypher-block {
        background: #0A0F1C; border: 1px solid #1E293B; border-radius: 6px;
        padding: 12px 16px; font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 13px; color: #5B9BD5; overflow-x: auto;
        line-height: 1.5; white-space: pre-wrap; word-break: break-word;
    }

    /* ---- Confidence gauge ---- */
    .confidence-gauge {
        display: inline-flex; align-items: center; gap: 8px;
    }
    .confidence-gauge .gauge-bar {
        height: 8px; border-radius: 4px; background: #1E293B; width: 120px; overflow: hidden;
    }
    .confidence-gauge .gauge-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }

    /* ---- Parameter impact ---- */
    .parameter-impact {
        font-weight: 600; font-size: 16px; display: inline-block;
        padding: 2px 8px; border-radius: 4px;
    }
    .parameter-impact.positive { color: #22C55E; background: rgba(34, 197, 94, 0.1); }
    .parameter-impact.negative { color: #EF4444; background: rgba(239, 68, 68, 0.1); }
    .parameter-impact.neutral { color: #94A3B8; background: rgba(148, 163, 184, 0.1); }

    /* ---- Tab container ---- */
    .tab-container { padding: 0 4px; }

    /* ---- NEOLI dots ---- */
    .neoli-row { display: flex; gap: 10px; align-items: center; margin: 6px 0; }
    .neoli-dot { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
    .neoli-filled { background-color: #66BB6A; }
    .neoli-empty { background-color: #1E293B; border: 1px solid #334155; }
    .neoli-label { font-size: 18px; color: #B0BEC5 !important; }

    /* ---- Comparison Cards ---- */
    .comp-card {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px; padding: 24px 28px; border: 1px solid #243352; height: 100%;
    }
    .comp-card h4 { font-size: 21px; font-weight: 600; color: #E2E8F0 !important; margin: 0 0 8px 0; }
    .comp-score { font-size: 17px; font-weight: 600; color: #5B9BD5; margin-bottom: 12px; }
    .comp-card p { font-size: 18px; color: #B0BEC5; line-height: 1.5; margin: 0 0 8px 0; }

    /* ---- Pillar progress bars ---- */
    .pillar-bar {
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px; padding: 18px 22px; border: 1px solid #243352;
        text-align: center;
    }
    .pillar-bar .pillar-name {
        font-size: 14px; font-weight: 600; text-transform: uppercase;
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

    /* ---- v4 NEW: Portfolio table ---- */
    .portfolio-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 16px;
        background: linear-gradient(145deg, #162039 0%, #1A2744 100%);
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #243352;
    }
    .portfolio-table th {
        text-align: left; padding: 16px 20px; font-size: 13px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 1.5px; color: #94A3B8;
        border-bottom: 1px solid #243352; background: rgba(10, 18, 38, 0.5);
    }
    .portfolio-table td {
        padding: 14px 20px; color: #CBD5E1; border-bottom: 1px solid #1E2D48;
        vertical-align: middle;
    }
    .portfolio-table tr:last-child td { border-bottom: none; }
    .portfolio-table tr:hover td { background: rgba(91, 155, 213, 0.05); }

    /* ---- v4 NEW: Tier badge (table) ---- */
    .tier-gold { color: #F59E0B; font-weight: 600; }
    .tier-silver { color: #94A3B8; font-weight: 600; }
    .tier-bronze { color: #A0522D; font-weight: 600; }

    /* ---- v4 NEW: Habitat pill ---- */
    .habitat-pill {
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 13px; font-weight: 600; margin-right: 4px;
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


def confidence_badge(score: float | None) -> str:
    """Return HTML for a color-coded confidence badge."""
    if score is None or score == 0.0:
        return (
            '<span style="display:inline-block;padding:4px 14px;border-radius:4px;'
            'font-size:14px;font-weight:600;letter-spacing:0.8px;text-transform:uppercase;'
            'background:rgba(100,116,139,0.2);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)">'
            "DEMO MODE</span>"
        )
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
        f"font-size:13px;font-weight:600;color:{color};background:{bg};"
        f'border:1px solid {color}40">{tier}</span>'
    )


def axiom_tag(axiom_id: str) -> str:
    """Return HTML for an axiom pill tag."""
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
        f"font-size:14px;font-weight:600;margin-right:6px;margin-bottom:4px;"
        f"color:#5B9BD5;background:rgba(91,155,213,0.15);"
        f'border:1px solid rgba(91,155,213,0.3)">{axiom_id}</span>'
    )


def valuation_method_badge(method: str) -> str:
    """Return HTML for a color-coded ESV valuation method badge.

    Colors indicate evidence strength:
    - Green (#00C853) for market_price (strongest evidence)
    - Yellow (#FFD600) for avoided_cost (moderate)
    - Orange (#FF6D00) for regional_analogue_estimate (weakest)
    """
    _METHOD_DISPLAY = {
        "market_price": "Market Price",
        "avoided_cost": "Avoided Cost",
        "regional_analogue_estimate": "Regional Analogue",
        "expenditure_method": "Expenditure Method",
    }
    _METHOD_COLORS = {
        "market_price": "#00C853",
        "avoided_cost": "#FFD600",
        "regional_analogue_estimate": "#FF6D00",
        "expenditure_method": "#FFD600",
    }
    label = _METHOD_DISPLAY.get(method, method.replace("_", " ").title())
    color = _METHOD_COLORS.get(method, "#94A3B8")
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f"font-size:12px;font-weight:600;color:{color};"
        f'background:rgba({_hex_to_rgb(color)},0.15);'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.3)">{label}</span>'
    )


def esv_quality_ratio(services: list[dict]) -> dict[str, float]:
    """Compute the proportion of ESV from each valuation method.

    Returns a dict mapping method names to their share of total ESV.
    """
    totals: dict[str, float] = {}
    grand_total = 0.0
    for svc in services:
        method = svc.get("valuation_method", "unknown")
        value = svc.get("annual_value_usd", 0)
        totals[method] = totals.get(method, 0) + value
        grand_total += value
    if grand_total <= 0:
        return {}
    return {k: v / grand_total for k, v in totals.items()}


def habitat_pill(habitat_id: str) -> str:
    """Return HTML for a habitat type pill."""
    label = _HABITAT_DISPLAY.get(habitat_id, habitat_id.replace("_", " ").title())
    color = _HABITAT_COLORS.get(habitat_id, "#5B9BD5")
    return (
        f'<span class="habitat-pill" style="color:{color};'
        f'background:rgba({_hex_to_rgb(color)},0.15);'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.3)">{label}</span>'
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'r,g,b' string for rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def render_service_health(status: dict[str, bool]) -> str:
    """Return sidebar health indicator HTML."""
    items = ""
    api_up = status.get("api", False)
    labels = {"neo4j": "Neo4j", "llm": "LLM API", "api": "MARIS API"}
    for key, label in labels.items():
        ok = status.get(key, False)
        if ok and api_up:
            dot_color, text = "#66BB6A", "Connected"
        elif ok and not api_up:
            dot_color, text = "#66BB6A", "Ready"
        elif key == "api":
            dot_color, text = "#EF5350", "Not running"
        else:
            dot_color, text = "#EF5350", "Unavailable"
        items += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{dot_color};'
            f'display:inline-block"></span>'
            f'<span style="font-size:14px;color:#94A3B8">{label}: {text}</span></div>'
        )
    return f'<div style="margin:8px 0">{items}</div>'


# ---------------------------------------------------------------------------
# Service health checker
# ---------------------------------------------------------------------------


def _check_neo4j_direct() -> bool:
    """Check Neo4j connectivity directly via bolt driver."""
    try:
        import os

        from neo4j import GraphDatabase

        uri = os.environ.get("MARIS_NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("MARIS_NEO4J_USER", "neo4j")
        password = os.environ.get("MARIS_NEO4J_PASSWORD", "")
        if not password:
            return False
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


def _check_llm_direct() -> bool:
    """Check if an LLM API key is configured."""
    import os

    key = os.environ.get("MARIS_LLM_API_KEY", "")
    return bool(key and len(key) > 8)


def check_services(api_base: str = "http://localhost:8000") -> dict[str, bool]:
    """Check Neo4j, LLM, and API connectivity independently."""
    result: dict[str, bool] = {"neo4j": False, "llm": False, "api": False}
    try:
        import requests

        resp = requests.get(f"{api_base}/api/health", timeout=3)
        if resp.status_code == 200:
            result["api"] = True
            data = resp.json()
            result["neo4j"] = data.get("neo4j_connected", False)
            result["llm"] = data.get("llm_available", False)
            return result
    except Exception:
        pass

    result["neo4j"] = _check_neo4j_direct()
    result["llm"] = _check_llm_direct()
    return result


# ---------------------------------------------------------------------------
# Dynamic site discovery
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"


def _discover_case_studies() -> list[Path]:
    """Scan examples/ for all *_case_study.json files."""
    if not _EXAMPLES_DIR.is_dir():
        return []
    return sorted(_EXAMPLES_DIR.glob("*_case_study.json"))


def _load_case_study_json(path: Path) -> dict[str, Any] | None:
    """Load and return a case study JSON, or None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        logger.warning("Failed to load case study: %s", path)
        return None


def _extract_site_meta(data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Extract summary metadata from a case study JSON for the portfolio."""
    site = data.get("site", {})
    eco = data.get("ecological_status", {})
    esv_block = data.get("ecosystem_services", {})
    rating = data.get("asset_quality_rating", {})
    neoli = data.get("neoli_assessment", {})
    fin = data.get("financial_output", {})

    # Determine primary habitat
    primary_habitat = eco.get("primary_habitat", "")
    if not primary_habitat:
        # Infer from ecosystem services or site data
        svc_types = [
            s.get("service_type", "") for s in esv_block.get("services", [])
        ]
        if "carbon_sequestration" in svc_types:
            primary_habitat = "seagrass_meadow"
        elif any("reef" in site.get("name", "").lower() for _ in [1]):
            primary_habitat = "coral_reef"

    # Determine total ESV
    total_esv = fin.get("market_price_esv_usd", 0)
    if not total_esv:
        total_esv = esv_block.get("total_annual_value_usd", 0)

    # Determine tier (Gold if rich data, Silver if less)
    has_trophic = bool(data.get("trophic_network"))
    has_recovery = bool(data.get("ecological_recovery"))
    has_risk = bool(data.get("risk_assessment"))
    if has_trophic or has_recovery or has_risk:
        tier = "Gold"
    elif esv_block.get("services"):
        tier = "Silver"
    else:
        tier = "Bronze"

    return {
        "name": site.get("name", path.stem.replace("_case_study", "").replace("_", " ").title()),
        "country": site.get("country", "Unknown"),
        "region": site.get("region", ""),
        "area_km2": site.get("area_km2", 0),
        "designation_year": site.get("designation_year", 0),
        "primary_habitat": primary_habitat,
        "total_esv": total_esv,
        "asset_rating": rating.get("rating", ""),
        "composite_score": rating.get("composite_score", 0.0),
        "neoli_score": neoli.get("neoli_score", eco.get("neoli_score", 0)),
        "tier": tier,
        "path": str(path),
        "n_services": len(esv_block.get("services", [])),
        "n_services": len(esv_block.get("services", [])),
        "dominant_species": eco.get("dominant_species", ""),
        "latitude": site.get("coordinates", {}).get("latitude"),
        "longitude": site.get("coordinates", {}).get("longitude"),
    }


def get_all_sites() -> list[dict[str, Any]]:
    """Discover and return metadata for all available case study sites.

    Scans ``examples/*_case_study.json`` and returns a list of site
    metadata dicts sorted by total ESV (descending).
    """
    sites: list[dict[str, Any]] = []
    for path in _discover_case_studies():
        data = _load_case_study_json(path)
        if data is None:
            continue
        meta = _extract_site_meta(data, path)
        sites.append(meta)
    return sorted(sites, key=lambda s: s["total_esv"], reverse=True)


def get_site_names() -> list[str]:
    """Return canonical site names from all discovered case studies."""
    return [s["name"] for s in get_all_sites()]


def get_site_data(
    site_name: str,
    bundle_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Load site-specific data by canonical name.

    For Cabo Pulmo, the static bundle is preferred (richer structure)
    when available. For all other sites, loads from case study JSON.
    """
    if site_name == "Cabo Pulmo National Park" and bundle_data:
        return bundle_data

    # Dynamic lookup from examples/
    for path in _discover_case_studies():
        data = _load_case_study_json(path)
        if data is None:
            continue
        name = data.get("site", {}).get("name", "")
        if name == site_name:
            return data

    return None


def get_site_summary(site_name: str) -> str:
    """Generate a sidebar summary string from site data."""
    for path in _discover_case_studies():
        data = _load_case_study_json(path)
        if data is None:
            continue
        name = data.get("site", {}).get("name", "")
        if name != site_name:
            continue
        meta = _extract_site_meta(data, path)
        habitat_label = _HABITAT_DISPLAY.get(
            meta["primary_habitat"],
            meta["primary_habitat"].replace("_", " ").title(),
        )
        area = meta["area_km2"]
        area_str = f"{area:,.0f} km2" if area else "N/A"
        year = meta["designation_year"]
        year_str = f"Est. {year}" if year else ""
        esv_str = fmt_usd(meta["total_esv"]) if meta["total_esv"] else "N/A"
        parts = [f"**{meta['country']}**"]
        if area_str != "N/A":
            parts.append(area_str)
        if year_str:
            parts.append(year_str)
        line1 = " - ".join(parts)
        line2 = f"{habitat_label} - {esv_str} ESV"
        return f"{line1}\n{line2}"
    return ""


# ---------------------------------------------------------------------------
# Tier-aware rendering helpers
# ---------------------------------------------------------------------------

# Data quality tiers determine which dashboard features are available
TIER_FEATURES: dict[str, dict[str, bool]] = {
    "Gold": {
        "intelligence_brief": True,
        "graphrag_chat": True,
        "scenario_lab": True,
        "tnfd_compliance": True,
        "portfolio": True,
    },
    "Silver": {
        "intelligence_brief": True,
        "graphrag_chat": True,
        "scenario_lab": True,
        "tnfd_compliance": True,
        "portfolio": True,
    },
    "Bronze": {
        "intelligence_brief": False,
        "graphrag_chat": False,
        "scenario_lab": False,
        "tnfd_compliance": False,
        "portfolio": True,
    },
}


def is_feature_available(tier: str, feature: str) -> bool:
    """Check if a dashboard feature is available for a given data tier."""
    return TIER_FEATURES.get(tier, TIER_FEATURES["Bronze"]).get(feature, False)


def get_site_tier(site_name: str) -> str:
    """Look up the data quality tier for a site."""
    for site in get_all_sites():
        if site["name"] == site_name:
            return site["tier"]
    return "Bronze"
