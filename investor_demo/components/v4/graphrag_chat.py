"""GraphRAG Chat - split-panel reasoning-transparent query interface for Nereus v4.

Adapted from v3. Key change: site detection uses dynamic site list instead
of hardcoded patterns.
"""

from __future__ import annotations

import html
import logging
import re
import time
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from investor_demo.components.v4.shared import (
    axiom_tag,
    confidence_badge,
    get_site_names,
    tier_badge,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COMPARISON_KEYWORDS = ("compare", "versus", "vs", "differ")
_MECHANISM_KEYWORDS = ("how does", "how do", "what is blue carbon")

_LAYER_ORDER = ["MPA", "Habitat", "EcosystemService", "BridgeAxiom", "Document"]
_LAYER_Y: dict[str, float] = {
    "MPA": 5.0, "Habitat": 3.8, "EcosystemService": 2.4,
    "BridgeAxiom": 1.0, "Document": -1.5,
}
_NODE_SIZES: dict[str, int] = {
    "MPA": 50, "EcosystemService": 40, "BridgeAxiom": 36,
    "Document": 22, "Habitat": 34,
}
_TYPE_COLORS: dict[str, str] = {
    "MPA": "#F1C40F", "Species": "#059669", "EcosystemService": "#1ABC9C",
    "BridgeAxiom": "#7C3AED", "Document": "#64748B", "Habitat": "#10B981",
    "FinancialInstrument": "#D97706",
}
_TIER_COLORS: dict[str, str] = {
    "T1": "#2ECC71", "T2": "#3498DB", "T3": "#E67E22", "T4": "#E74C3C",
}
_TYPE_LABELS: dict[str, str] = {
    "MPA": "Marine Protected Area", "EcosystemService": "Ecosystem Service",
    "BridgeAxiom": "Bridge Axiom", "Document": "Peer-Reviewed Source",
    "Habitat": "Habitat",
}
_DEFAULT_COLOR = "#5B9BD5"

# Explicit short-name -> canonical-name mapping for robust site resolution.
# Covers common abbreviations and partial names that users (and quick buttons)
# might produce. The dynamic site list in _detect_site handles full-name and
# first-two-word matching; this map catches additional aliases.
_SHORT_TO_CANONICAL: dict[str, str] = {
    "cabo pulmo": "Cabo Pulmo National Park",
    "shark bay": "Shark Bay World Heritage Area",
    "ningaloo": "Ningaloo Coast World Heritage Area",
    "ningaloo coast": "Ningaloo Coast World Heritage Area",
    "belize": "Belize Barrier Reef Reserve System",
    "belize barrier": "Belize Barrier Reef Reserve System",
    "belize barrier reef": "Belize Barrier Reef Reserve System",
    "galapagos": "Galapagos Marine Reserve",
    "galapagos marine": "Galapagos Marine Reserve",
    "raja ampat": "Raja Ampat Marine Park",
    "sundarbans": "Sundarbans Reserve Forest",
    "sundarbans reserve": "Sundarbans Reserve Forest",
    "aldabra": "Aldabra Atoll",
    "aldabra atoll": "Aldabra Atoll",
    "cispata": "Cispata Bay Mangrove Conservation Area",
    "cispata bay": "Cispata Bay Mangrove Conservation Area",
    "cispatá": "Cispata Bay Mangrove Conservation Area",
    "cispatá bay": "Cispata Bay Mangrove Conservation Area",
}

# Queries that are site-generic and should be contextualized to the active site
_GENERIC_QUERY_PATTERNS = (
    "what are the risks",
    "what evidence supports the valuation",
    "what evidence supports",
)

_LOW_CONFIDENCE_THRESHOLD = 0.35
_NORMALIZATION_NOTE = "Query normalized for deterministic GraphRAG execution"
_GOVERNANCE_SIGNAL_TERMS = (
    "governance",
    "unesco",
    "transboundary",
    "surveillance",
    "award",
    "methodology",
    "issuance",
    "partnership",
)
_DOI_STATUS_COLORS: dict[str, str] = {
    "verified": "#2ECC71",
    "unverified": "#F59E0B",
    "missing": "#64748B",
    "invalid_format": "#EF5350",
    "placeholder_blocked": "#8B5CF6",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_graphrag_chat(
    data: dict,
    site: str,
    mode: str,
    site_name: str | None = None,
    **kwargs: Any,
) -> None:
    """Render the GraphRAG Chat tab."""
    client = kwargs.get("client")
    if client is None:
        st.error("No API client provided. Cannot render GraphRAG Chat.")
        return

    # Derive context
    # If site_name is provided (from dynamic selection), use it.
    # Otherwise fallback to the raw 'site' key logic.
    if site_name:
        context_name = site_name
        parts = site_name.split()
        site_short = " ".join(parts[:2]) if len(parts) >= 2 else site_name
    else:
        context_name = site
        parts = site.split()
        site_short = " ".join(parts[:2]) if len(parts) >= 2 else site

    if "v4_chat_history" not in st.session_state:
        st.session_state.v4_chat_history = []

    st.markdown(
        f"""
        <div class="masthead">
            <div class="masthead-brand">NEREUS | ASK NEREUS</div>
            <h1 style="font-size: 42px; font-weight: 300; margin-top: 10px; margin-bottom: 5px;">{context_name}</h1>
            <div class="masthead-subtitle">GraphRAG-powered conversational intelligence with full provenance</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("How confidence is computed (full transparency)", expanded=False):
        st.markdown(_confidence_methodology_markdown())

    # Quick query buttons
    quick_queries = _build_quick_queries(site_short, context_name)
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#94A3B8;'
        'margin-bottom:10px;text-transform:uppercase;letter-spacing:1px">'
        "Quick queries</div>",
        unsafe_allow_html=True,
    )
    grid_cols = 2
    for row_start in range(0, len(quick_queries), grid_cols):
        row = st.columns(grid_cols)
        for col_idx, q in enumerate(quick_queries[row_start: row_start + grid_cols]):
            button_idx = row_start + col_idx
            with row[col_idx]:
                if st.button(q, key=f"v4_quick_{button_idx}", use_container_width=True):
                    _submit_query(client, q, mode)

    with st.form(key="v4_query_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ask Nereus anything",
            placeholder="e.g., What is the tourism elasticity coefficient?",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Ask Nereus", use_container_width=True)
        if submitted and user_input:
            _submit_query(client, user_input, mode)

    for idx, entry in enumerate(reversed(st.session_state.v4_chat_history)):
        _render_split_response(entry, idx, mode)


# ---------------------------------------------------------------------------
# Quick queries
# ---------------------------------------------------------------------------


def _build_quick_queries(site_short: str, full_name: str) -> list[str]:
    """Return 10 quick-query strings: 6 existing + 4 scenario queries."""
    defaults = [
        f"What is {site_short} worth?",
        "What evidence supports the valuation?",
        "How is NEOLI calculated?",
        "Compare sites in the portfolio",
        f"What are the risks for {site_short}?",
        "How does blue carbon sequestration work?",
        # v6 scenario quick-queries
        f"What would {site_short} be worth without protection?",
        f"What happens to {site_short} under SSP2-4.5 by 2050?",
        f"What blue carbon revenue could {site_short} generate at $45/tCO2?",
        f"How close is {site_short} to a tipping point?",
    ]

    # v6 scenario quick-queries (always appended)
    scenario_queries = [
        f"What would {site_short} be worth without protection?",
        f"What happens to {site_short} under SSP2-4.5 by 2050?",
        f"What blue carbon revenue could {site_short} generate at $45/tCO2?",
        f"How close is {site_short} to a tipping point?",
    ]

    # Try to load from case study JSON first
    from investor_demo.components.v4.shared import get_site_data
    site_data = get_site_data(full_name)
    if site_data:
        custom = site_data.get("demo_value", {}).get("quick_queries", [])
        if custom:
            return (custom + scenario_queries)[:10]

    # Fallback to hardcoded logic (legacy safety net)
    lower_name = full_name.lower()

    if "galapagos" in lower_name:
        return [
            "How does El Nino impact Galapagos?",
            "What is the value of hammerhead shark tourism?",
            "How does the NEOLI score explain recovery?",
            "Compare Galapagos to Cabo Pulmo",
            "What conflict exists with industrial fishing?",
            defaults[5],
        ] + scenario_queries
    elif "cabo pulmo" in lower_name:
        return [
            "What drove the 463% biomass recovery?",
            "What is the total ecosystem service value?",
            "How did community enforcement help?",
            "Compare to other Gulf of California sites",
            "What are the top 3 species recovering?",
            defaults[5],
        ] + scenario_queries
    elif "ningaloo" in lower_name:
        return [
            "What is the value of whale shark tourism?",
            "How does the Leeuwin Current affect biodiversity?",
            "What evidence supports the resilience rating?",
            "Compare tourism revenue to fisheries",
            "What are the threats from oil and gas?",
            defaults[5],
        ] + scenario_queries
    elif "belize" in lower_name:
        return [
            "What is the value of storm protection?",
            "How does coral bleaching risk affect value?",
            "What is the impact of mangrove loss?",
            "Compare coastal protection to tourism value",
            "What is the status of the barrier reef?",
            defaults[5],
        ] + scenario_queries

    return defaults


# ---------------------------------------------------------------------------
# Site detection - dynamic
# ---------------------------------------------------------------------------


def _detect_site(question: str) -> str | None:
    """Detect site from question text using dynamic site list + alias map."""
    q_lower = question.lower()
    if any(kw in q_lower for kw in _COMPARISON_KEYWORDS):
        return None
    if any(kw in q_lower for kw in _MECHANISM_KEYWORDS):
        return None

    # 1) Check canonical names (full and first-two-word match)
    for name in get_site_names():
        if name.lower() in q_lower:
            return name
        short = " ".join(name.split()[:2]).lower()
        if short in q_lower:
            return name

    # 2) Check explicit alias map (longest match first to avoid partial hits)
    for alias in sorted(_SHORT_TO_CANONICAL, key=len, reverse=True):
        if alias in q_lower:
            return _SHORT_TO_CANONICAL[alias]

    return None


# ---------------------------------------------------------------------------
# Query submission
# ---------------------------------------------------------------------------


def _run_classifier(question: str) -> dict:
    """Run the QueryClassifier client-side for pipeline transparency."""
    try:
        from maris.query.classifier import QueryClassifier

        classifier = QueryClassifier()
        start = time.monotonic()
        result = classifier.classify(question)
        elapsed_ms = (time.monotonic() - start) * 1000
        result["_classify_ms"] = round(elapsed_ms, 1)
        result["_method"] = "keyword" if result.get("confidence", 0) >= 0.6 else "LLM fallback"
        return result
    except ImportError:
        return {
            "category": "unknown", "site": None, "metrics": [],
            "confidence": 0.0, "caveats": ["Classifier not available"],
            "_classify_ms": 0.0, "_method": "unavailable",
        }
    except Exception:
        logger.exception("Classification failed")
        return {
            "category": "error", "site": None, "metrics": [],
            "confidence": 0.0, "caveats": ["Classification error"],
            "_classify_ms": 0.0, "_method": "error",
        }


def _contextualize_query(question: str, site: str | None) -> str:
    """Prepend the active site to generic queries for better matching.

    Generic queries like "What are the risks?" become
    "What are the risks for Cabo Pulmo National Park?" so the precomputed
    response matcher and the live API both resolve to the correct site.
    """
    if site is None:
        return question
    q_lower = question.lower().rstrip("?").strip()
    for pattern in _GENERIC_QUERY_PATTERNS:
        if q_lower == pattern or q_lower.startswith(pattern):
            # Already has a site suffix - skip
            if "for " in q_lower[len(pattern):]:
                return question
            return f"{question.rstrip('?')} for {site}?"
    return question


def _has_comparison_intent(question: str) -> bool:
    q_lower = question.lower()
    return any(kw in q_lower for kw in _COMPARISON_KEYWORDS)


def _normalize_query(
    effective_question: str,
    site: str | None,
    classification: dict,
) -> tuple[str, str | None]:
    """Normalize low-confidence/open-domain prompts into deterministic forms."""
    if not site:
        return effective_question, None

    q_lower = effective_question.lower()
    category = classification.get("category", "")
    confidence = float(classification.get("confidence", 0.0) or 0.0)
    sites = classification.get("sites") or []

    if _has_comparison_intent(effective_question) and len(sites) < 2:
        return (
            f"What is the total ecosystem service value of {site}?",
            "Comparison intent had fewer than two resolved sites.",
        )

    needs_normalization = category == "open_domain" or confidence < _LOW_CONFIDENCE_THRESHOLD
    if not needs_normalization:
        return effective_question, None

    if any(term in q_lower for term in _GOVERNANCE_SIGNAL_TERMS):
        return (
            f"What are the key governance and climate risks for {site}?",
            "Low-confidence governance prompt normalized to deterministic risk query.",
        )
    if any(term in q_lower for term in ("evidence", "doi", "source", "support")):
        return (
            f"What evidence supports the valuation of {site}?",
            "Low-confidence provenance prompt normalized to deterministic evidence query.",
        )

    return (
        f"What is the total ecosystem service value of {site}?",
        "Low-confidence prompt normalized to deterministic valuation query.",
    )


def _resolve_doi_status(item: dict) -> str:
    status = str(item.get("doi_verification_status") or "").strip().lower()
    if status in _DOI_STATUS_COLORS:
        return status

    doi = str(item.get("doi") or "").strip()
    if not doi:
        return "missing"

    doi_valid = item.get("doi_valid")
    if doi_valid is True:
        return "verified"
    if doi_valid is False:
        return "unverified"
    return "unverified"


def _doi_status_metrics(evidence: list[dict]) -> dict[str, int]:
    metrics = {"verified": 0, "unverified": 0, "missing_invalid": 0}
    for item in evidence:
        status = _resolve_doi_status(item)
        if status == "verified":
            metrics["verified"] += 1
        elif status == "unverified":
            metrics["unverified"] += 1
        else:
            metrics["missing_invalid"] += 1
    return metrics


def _doi_status_badge(status: str, reason: str | None = None) -> str:
    color = _DOI_STATUS_COLORS.get(status, _DOI_STATUS_COLORS["unverified"])
    label = status.replace("_", " ")
    title = _escape(reason or "")
    return (
        f'<span title="{title}" style="display:inline-block;padding:4px 8px;border-radius:999px;'
        f"font-size:11px;font-weight:600;letter-spacing:0.3px;text-transform:uppercase;"
        f'color:#E2E8F0;background:{color};opacity:0.95">{_escape(label)}</span>'
    )


def _submit_query(client: Any, question: str, mode: str) -> None:
    """Submit a query, run classification, and store results."""
    site = _detect_site(question)
    if site is None:
        site = st.session_state.get("v4_site")

    # Contextualize generic queries with the active site
    effective_question = _contextualize_query(question, site)

    classification = _run_classifier(effective_question) if mode == "live" else {}
    normalized_question = effective_question
    normalization_note: str | None = None
    if mode == "live" and classification:
        normalized_question, normalization_reason = _normalize_query(
            effective_question,
            site,
            classification,
        )
        if normalization_reason and normalized_question != effective_question:
            normalization_note = (
                f"{_NORMALIZATION_NOTE}: {normalization_reason}"
            )
            classification = _run_classifier(normalized_question)
            classification["normalization_note"] = normalization_note
            classification["normalized_from"] = effective_question

    try:
        start = time.monotonic()
        response = client.query(normalized_question, site=site)
        elapsed_ms = (time.monotonic() - start) * 1000
        response["_query_ms"] = round(elapsed_ms, 1)
    except Exception:
        logger.exception("API query failed for: %s", question)
        try:
            from pathlib import Path as _Path

            from investor_demo.api_client import StaticBundleClient

            _v4_path = _Path(__file__).resolve().parent.parent.parent / "precomputed_responses_v4.json"
            if _v4_path.exists():
                fallback_client = StaticBundleClient(precomputed_path=_v4_path)
            else:
                fallback_client = StaticBundleClient()
            response = fallback_client.query(normalized_question, site=site)
            if (
                response.get("confidence", 0) == 0.0
                and response.get("answer", "").startswith("I don't have")
            ):
                response = {
                    "answer": (
                        "This query could not be answered in demo mode. "
                        "Start the MARIS API for live responses, or try one "
                        "of the quick queries above."
                    ),
                    "confidence": 0.0, "evidence": [],
                    "axioms_used": [], "caveats": ["Demo mode - live API not available"],
                    "graph_path": [], "_query_ms": 0.0,
                }
            else:
                response["_query_ms"] = 0.0
                if "caveats" not in response:
                    response["caveats"] = []
                response["caveats"].append("Response from precomputed cache (API unavailable)")
        except Exception:
            response = {
                "answer": "The query service is temporarily unavailable.",
                "confidence": 0.0, "evidence": [], "axioms_used": [],
                "caveats": ["API error"], "graph_path": [], "_query_ms": 0.0,
            }

    if normalization_note:
        response.setdefault("caveats", [])
        if normalization_note not in response["caveats"]:
            response["caveats"].append(normalization_note)

    st.session_state.v4_chat_history.append({
        "question": question,
        "effective_question": effective_question,
        "normalized_question": normalized_question,
        "response": response,
        "classification": classification,
    })


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    return html.escape(str(text))


def _md_to_html(text: str) -> str:
    """Convert basic markdown to HTML."""
    text = _escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    lines = text.split("\n")
    result: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            if not in_list:
                result.append('<ul style="margin:8px 0;padding-left:22px">')
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped)
            result.append(f'<li style="color:#B0BEC5;font-size:16px;line-height:1.7;margin-bottom:4px">{item}</li>')
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            if stripped:
                result.append(f"<p>{stripped}</p>")
    if in_list:
        result.append("</ul>")
    return "\n".join(result)


def render_scenario_response(response: dict, container: Any = None) -> None:
    """Render a structured scenario response block.

    Used for responses with ``scenario_request`` field (scenario_analysis category).
    """
    target = container if container is not None else st

    if response.get("scenario_request") is None:
        return  # Not a scenario response; use existing render path

    # KPI strip: type-dependent metrics
    scenario_req = response.get("scenario_request") or {}
    scenario_type = scenario_req.get("scenario_type", "counterfactual")

    if scenario_type == "market":
        # Blue carbon revenue: show annual revenue and range
        annual_rev = response.get("annual_revenue_usd", 0)
        rev_range = response.get("revenue_range", {})
        col1, col2, col3 = target.columns(3)
        col1.metric("Annual Revenue", f"${annual_rev / 1e6:.2f}M/yr" if annual_rev else "See answer")
        col2.metric("Range Low", f"${rev_range.get('low', 0) / 1e6:.2f}M" if rev_range else "-")
        col3.metric("Range High", f"${rev_range.get('high', 0) / 1e6:.2f}M" if rev_range else "-")
    elif scenario_type == "tipping_point":
        # Tipping point: no ESV delta — skip KPI strip, info is in the answer text
        pass
    else:
        # Counterfactual / climate / intervention: show ESV delta
        baseline_esv = response.get("baseline_case", {}).get("total_esv_usd", 0)
        scenario_esv = response.get("scenario_case", {}).get("total_esv_usd", 0)
        if baseline_esv or scenario_esv:
            delta_pct = (scenario_esv - baseline_esv) / baseline_esv * 100 if baseline_esv else 0
            col1, col2, col3 = target.columns(3)
            col1.metric("Baseline ESV", f"${baseline_esv / 1e6:.1f}M")
            col2.metric("Scenario ESV", f"${scenario_esv / 1e6:.1f}M")
            col3.metric("Delta", f"{delta_pct:+.1f}%", delta=f"${abs(scenario_esv - baseline_esv) / 1e6:.1f}M")

    # Tipping point badge (if present)
    if response.get("tipping_point_proximity"):
        target.warning(f"Tipping Point Alert: {response['tipping_point_proximity']}")

    # Uncertainty band
    unc = response.get("uncertainty", {})
    if unc:
        target.caption(
            f"P5: ${unc.get('p5', 0) / 1e6:.1f}M | "
            f"P50: ${unc.get('p50', 0) / 1e6:.1f}M | "
            f"P95: ${unc.get('p95', 0) / 1e6:.1f}M"
        )

    # Propagation trace expander
    trace = response.get("propagation_trace", [])
    if trace:
        with target.expander("Propagation Trace (full axiom arc)"):
            for step in trace:
                st.markdown(f"**{step['axiom_id']}**: {step['description']}")
                st.caption(
                    f"{step['input_parameter']} {step['input_value']:.2f} -> "
                    f"{step['output_parameter']} {step['output_value']:.2f}"
                )

    # Confidence penalties expander
    penalties = response.get("confidence_penalties", [])
    if penalties:
        with target.expander("Confidence Penalties Applied"):
            for penalty in penalties:
                st.caption(f"{penalty['reason']}: {penalty['penalty']:+.2f}")


def _render_split_response(entry: dict, idx: int, mode: str) -> None:
    """Render a single query result as a split panel."""
    question = entry["question"]
    resp = entry["response"]
    classification = entry.get("classification", {})

    st.markdown(
        f'<div style="background:rgba(10,18,38,0.6);border:1px solid #1E293B;'
        f"border-radius:10px 10px 0 0;padding:14px 24px;margin-top:24px;"
        f'font-size:17px;color:#E2E8F0;font-weight:500">'
        f"{_escape(question)}</div>",
        unsafe_allow_html=True,
    )

    # Check if this is a scenario response
    if resp.get("scenario_request") is not None:
        render_scenario_response(resp)

    col_chat, col_pipeline = st.columns([3, 2])
    with col_chat:
        _render_chat_panel(resp, idx)
    with col_pipeline:
        _render_pipeline_panel(resp, classification, mode)

    graph_path = resp.get("graph_path", [])
    if graph_path:
        with st.expander("Show knowledge graph subgraph", expanded=False):
            _render_graph_explorer(graph_path, idx)


def _render_chat_panel(resp: dict, idx: int) -> None:
    """Render the left-side chat response panel."""
    answer = resp.get("answer", "No response available.")
    confidence = resp.get("confidence", 0.0)
    axioms = resp.get("axioms_used", [])
    caveats = resp.get("caveats", [])
    evidence = resp.get("evidence", [])
    evidence_count = int(resp.get("evidence_count", len(evidence)) or 0)
    doi_citation_count = int(
        resp.get("doi_citation_count", sum(1 for item in evidence if item.get("doi")))
        or 0
    )
    completeness = float(
        resp.get("evidence_completeness_score", 0.0 if evidence_count == 0 else 1.0)
        or 0.0
    )
    provenance_warnings = list(resp.get("provenance_warnings", []))
    provenance_risk = str(resp.get("provenance_risk", "high" if evidence_count == 0 else "low")).lower()

    badge_html = confidence_badge(confidence)
    tags_html = "".join(axiom_tag(ax) for ax in axioms) if axioms else ""

    st.markdown(
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;'
        f'margin-bottom:12px">{badge_html}{tags_html}</div>',
        unsafe_allow_html=True,
    )

    answer_html = _md_to_html(answer)
    st.markdown(
        f'<div style="font-size:17px;color:#B0BEC5;line-height:1.7;'
        f'padding:8px 0 16px 0">{answer_html}</div>',
        unsafe_allow_html=True,
    )

    risk_styles = {
        "low": ("#22C55E", "rgba(34,197,94,0.16)", "rgba(34,197,94,0.35)"),
        "medium": ("#F59E0B", "rgba(245,158,11,0.16)", "rgba(245,158,11,0.35)"),
        "high": ("#EF4444", "rgba(239,68,68,0.16)", "rgba(239,68,68,0.35)"),
    }
    risk_color, risk_bg, risk_border = risk_styles.get(
        provenance_risk,
        risk_styles["high"],
    )
    warnings_html = "".join(
        f'<li style="color:#FCA5A5;font-size:13px;line-height:1.5;margin-bottom:2px">{_escape(w)}</li>'
        for w in provenance_warnings
    )
    st.markdown(
        '<div style="background:#0B1220;border:1px solid #243352;border-radius:8px;'
        'padding:10px 12px;margin:6px 0 12px 0">'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px">'
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.4px;color:{risk_color};background:{risk_bg};border:1px solid {risk_border}">'
        f'Provenance risk: {_escape(provenance_risk)}</span>'
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:600;'
        'color:#CBD5E1;background:rgba(51,65,85,0.35);border:1px solid rgba(100,116,139,0.35)">'
        f'Evidence items: {evidence_count}</span>'
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:600;'
        'color:#CBD5E1;background:rgba(51,65,85,0.35);border:1px solid rgba(100,116,139,0.35)">'
        f'DOI citations: {doi_citation_count}</span>'
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:600;'
        'color:#CBD5E1;background:rgba(51,65,85,0.35);border:1px solid rgba(100,116,139,0.35)">'
        f'Completeness: {int(completeness * 100)}%</span>'
        '</div>'
        + (f'<ul style="margin:0;padding-left:18px">{warnings_html}</ul>' if warnings_html else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    if caveats:
        caveat_items = "".join(
            f'<li style="color:#94A3B8;font-size:14px;line-height:1.6;margin-bottom:2px">{_escape(c)}</li>'
            for c in caveats
        )
        st.markdown(
            f'<div style="background:#0D1526;border:1px solid #1E293B;border-radius:8px;padding:12px 16px;margin-bottom:12px">'
            f'<div style="font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;color:#64748B;margin-bottom:6px">Caveats</div>'
            f"<ul style='margin:0;padding-left:20px'>{caveat_items}</ul></div>",
            unsafe_allow_html=True,
        )

    if evidence:
        with st.expander("Show evidence chain", expanded=False):
            st.markdown(_evidence_table(evidence), unsafe_allow_html=True)

    confidence_breakdown = resp.get("confidence_breakdown")
    if confidence_breakdown and isinstance(confidence_breakdown, dict):
        with st.expander("Show confidence breakdown", expanded=False):
            st.markdown(
                _confidence_breakdown_html(confidence_breakdown),
                unsafe_allow_html=True,
            )


def _render_pipeline_panel(resp: dict, classification: dict, mode: str) -> None:
    """Render the right-side reasoning pipeline transparency panel."""
    st.markdown(
        '<div style="font-size:14px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:1.5px;color:#5B9BD5;margin-bottom:12px">'
        "Reasoning Pipeline</div>",
        unsafe_allow_html=True,
    )

    if mode == "demo" and not classification:
        _render_demo_pipeline(resp)
        return

    # Step 1: CLASSIFY
    category = classification.get("category", resp.get("category", "unknown"))
    classify_conf = classification.get("confidence", 0.0)
    classify_ms = classification.get("_classify_ms", 0.0)
    classify_method = classification.get("_method", "keyword")

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header"><span class="step-num">1</span> CLASSIFY</div>'
        '<div class="step-detail">'
        f"Category: <code>{_escape(category)}</code><br>"
        f"Confidence: {classify_conf:.2f} ({_escape(classify_method)})<br>"
        f"Latency: {classify_ms:.0f}ms"
        "</div></div>",
        unsafe_allow_html=True,
    )

    normalization_note = classification.get("normalization_note")
    if normalization_note:
        st.markdown(
            '<div class="pipeline-step complete">'
            '<div class="step-header"><span class="step-num">↻</span> NORMALIZE</div>'
            f'<div class="step-detail">{_escape(normalization_note)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Step 2: QUERY GRAPH
    graph_path = resp.get("graph_path", [])
    query_ms = resp.get("_query_ms", 0.0)
    template_map = {
        "site_valuation": "SITE_VALUATION_QUERY",
        "provenance_drilldown": "PROVENANCE_DRILLDOWN_QUERY",
        "axiom_explanation": "AXIOM_EXPLANATION_QUERY",
        "comparison": "COMPARISON_QUERY",
        "risk_assessment": "RISK_ASSESSMENT_QUERY",
    }
    template_name = template_map.get(category, "DEFAULT_QUERY")
    provenance_edges = sum(1 for e in graph_path if e.get("relationship") == "EVIDENCED_BY")

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header"><span class="step-num">2</span> QUERY GRAPH</div>'
        '<div class="step-detail">'
        f"Template: <code>{_escape(template_name)}</code><br>"
        f"Result edges: {len(graph_path)}<br>"
        f"Provenance edges: {provenance_edges}<br>"
        f"Total latency: {query_ms:.0f}ms"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 3: SYNTHESIZE
    evidence = resp.get("evidence", [])
    evidence_count = int(resp.get("evidence_count", len(evidence)) or 0)
    doi_count = int(resp.get("doi_citation_count", sum(1 for e in evidence if e.get("doi"))) or 0)
    completeness = float(
        resp.get("evidence_completeness_score", 0.0 if evidence_count == 0 else 1.0)
        or 0.0
    )
    provenance_risk = _escape(str(resp.get("provenance_risk", "high" if evidence_count == 0 else "low")))
    doi_metrics = _doi_status_metrics(evidence)
    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header"><span class="step-num">3</span> SYNTHESIZE</div>'
        '<div class="step-detail">'
        f"DOI citations: {doi_count}<br>"
        f"Verified DOI: {doi_metrics['verified']}<br>"
        f"Unverified DOI: {doi_metrics['unverified']}<br>"
        f"Missing/invalid DOI: {doi_metrics['missing_invalid']}<br>"
        f"Evidence items: {evidence_count}<br>"
        f"Completeness: {int(completeness * 100)}%<br>"
        f"Provenance risk: <code>{provenance_risk}</code><br>"
        f"Response length: {len(resp.get('answer', ''))} chars"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 4: VALIDATE
    confidence = resp.get("confidence", 0.0)
    conf_color = "#66BB6A" if confidence >= 0.8 else "#FFA726" if confidence >= 0.6 else "#EF5350"
    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header"><span class="step-num">4</span> VALIDATE</div>'
        '<div class="step-detail">'
        f'Composite confidence: <span style="color:{conf_color};font-weight:600">'
        f"{int(confidence * 100)}%</span><br>"
        f"Axioms used: {len(resp.get('axioms_used', []))}<br>"
        f"Caveats: {len(resp.get('caveats', []))}"
        "</div></div>",
        unsafe_allow_html=True,
    )


def _render_demo_pipeline(resp: dict) -> None:
    """Render pipeline panel for demo mode."""
    confidence = resp.get("confidence", 0.0)
    evidence = resp.get("evidence", [])
    has_real_data = confidence > 0.0 or evidence
    step_class = "complete" if has_real_data else "pending"

    for step_num, step_name in [(1, "CLASSIFY"), (2, "QUERY GRAPH"), (3, "SYNTHESIZE"), (4, "VALIDATE")]:
        st.markdown(
            f'<div class="pipeline-step {step_class}">'
            f'<div class="step-header"><span class="step-num">{step_num}</span> {step_name}</div>'
            f'<div class="step-detail"><span style="color:#64748B;font-style:italic">'
            f"Precomputed response (start API for live pipeline)</span></div></div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Evidence table
# ---------------------------------------------------------------------------


def _evidence_table(evidence: list[dict]) -> str:
    if not evidence:
        return ""
    rows = ""
    for item in evidence:
        tier = str(item.get("tier") or "N/A").upper()
        title = _escape(item.get("title", "Unknown"))
        doi = item.get("doi", "")
        doi_url = item.get("doi_url", "")
        year = item.get("year")
        year_label = _escape(str(year)) if year else "N/A"
        status = _resolve_doi_status(item)
        status_reason = item.get("doi_verification_reason")
        badge = tier_badge(tier)
        link = (
            f'<a href="{_escape(doi_url)}" target="_blank" style="color:#5B9BD5;text-decoration:none">{_escape(doi)}</a>'
            if doi_url and doi else (_escape(doi) if doi else "N/A")
        )
        status_badge = _doi_status_badge(status, status_reason)
        rows += (
            f"<tr>"
            f'<td style="padding:12px 16px;border-bottom:1px solid #1E2D48">{badge}</td>'
            f'<td style="padding:12px 16px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:15px">{title}</td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #1E2D48;font-size:14px">{link}</td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #1E2D48">{status_badge}</td>'
            f'<td style="padding:12px 16px;color:#94A3B8;border-bottom:1px solid #1E2D48;font-size:14px">{year_label}</td>'
            f"</tr>"
        )
    return (
        '<table class="evidence-table"><thead><tr>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Tier</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Title</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">DOI</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">DOI Status</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Year</th>'
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


# ---------------------------------------------------------------------------
# Confidence breakdown
# ---------------------------------------------------------------------------


def _confidence_methodology_markdown() -> str:
    """Explain confidence scoring in investor-facing plain language."""
    return (
        "### Confidence transparency (investor view)\n"
        "**What this score means**\n"
        "- Confidence measures how strongly the returned answer is supported by the visible citation-grade evidence.\n"
        "- It is **not** a direct probability that a site has an investable valuation number.\n\n"
        "**Computation used by the API**\n"
        "`composite = tier_base x path_discount x staleness_discount x sample_factor x evidence_quality_factor x citation_coverage_factor x completeness_factor`\n\n"
        "**Factor definitions**\n"
        "- `tier_base`: average source tier strength (T1 > T2 > T3 > T4).\n"
        "- `path_discount`: penalty for longer inference chains.\n"
        "- `staleness_discount`: penalty for older data.\n"
        "- `sample_factor`: boost for multiple independent sources.\n"
        "- `evidence_quality_factor`: share of evidence with known quality tiers.\n"
        "- `citation_coverage_factor`: share of evidence with DOI citations.\n"
        "- `completeness_factor`: metadata completeness (DOI + year + tier).\n\n"
        "**Fail-closed guardrails**\n"
        "- If no evidence items are returned, confidence is capped at **25%**.\n"
        "- If numeric claims have no DOI citations, confidence is capped at **35%**.\n\n"
        "**How to interpret this in investor conversations**\n"
        "- Read confidence together with **Provenance risk**, DOI status, and caveats.\n"
        "- A moderate/high confidence can still describe evidence support for a narrative, not a site-specific valuation figure.\n"
        "- Use the **Show confidence breakdown** expander on each answer to inspect the exact factors behind that score.\n"
    )


def _confidence_breakdown_html(breakdown: dict) -> str:
    """Render confidence breakdown as a mini-table with bar gauges."""
    factors = [
        ("Evidence Tier", "tier_base"),
        ("Path Length", "path_discount"),
        ("Data Freshness", "staleness_discount"),
        ("Source Coverage", "sample_factor"),
        ("Evidence Quality", "evidence_quality_factor"),
        ("Citation Coverage", "citation_coverage_factor"),
        ("Completeness", "completeness_factor"),
    ]
    rows = ""
    for label, key in factors:
        val = breakdown.get(key, 0.0)
        pct = int(val * 100)
        bar_color = (
            "#66BB6A" if val >= 0.8
            else "#FFA726" if val >= 0.6
            else "#EF5350"
        )
        rows += (
            f"<tr>"
            f'<td style="padding:6px 12px;color:#94A3B8;font-size:13px;'
            f'border-bottom:1px solid #1E2D48">{label}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #1E2D48">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<div style="flex:1;height:6px;background:#1E2D48;border-radius:3px;'
            f'overflow:hidden">'
            f'<div style="width:{pct}%;height:100%;background:{bar_color};'
            f'border-radius:3px"></div></div>'
            f'<span style="color:#CBD5E1;font-size:13px;font-weight:600;'
            f'min-width:35px">{pct}%</span>'
            f"</div></td></tr>"
        )

    explanation = _escape(breakdown.get("explanation", ""))
    composite = int(breakdown.get("composite", 0.0) * 100)

    return (
        f'<div style="margin-top:4px">'
        f'<div style="font-size:13px;font-weight:600;color:#94A3B8;margin-bottom:8px">'
        f"Composite: {composite}%</div>"
        f'<table style="width:100%;border-collapse:collapse;'
        f"background:rgba(15,26,46,0.6);border-radius:6px;overflow:hidden;"
        f'border:1px solid #1E2D48">{rows}</table>'
        f'<div style="margin-top:8px;font-size:13px;color:#64748B;font-style:italic">'
        f"{explanation}</div></div>"
    )


# ---------------------------------------------------------------------------
# Graph explorer (simplified from v3)
# ---------------------------------------------------------------------------


def _render_graph_explorer(graph_path: list[dict], idx: int = 0) -> None:
    """Render the Plotly network graph for a query's subgraph."""
    if not graph_path:
        st.info("No graph path available for this response.")
        return

    positions = _layout_nodes(graph_path)
    if not positions:
        return

    fig = go.Figure()

    # Draw edges
    for edge in graph_path:
        src = edge.get("from_node", "")
        tgt = edge.get("to_node", "")
        rel = edge.get("relationship", "")
        if src not in positions or tgt not in positions:
            continue
        is_evidence = rel == "EVIDENCED_BY"
        edge_color = "#475569" if is_evidence else "#5B9BD5"
        edge_width = 1.2 if is_evidence else 2.0
        x0, y0 = positions[src]["x"], positions[src]["y"]
        x1, y1 = positions[tgt]["x"], positions[tgt]["y"]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line={"color": edge_color, "width": edge_width},
            hoverinfo="skip", showlegend=False,
        ))

    # Draw nodes - Document labels rendered as rotated annotations below
    doc_annotations: list[dict] = []
    for name, info in positions.items():
        node_type = info["type"]
        color = _TYPE_COLORS.get(node_type, _DEFAULT_COLOR)
        size = _NODE_SIZES.get(node_type, 34)
        display_name = name[:35] + "..." if len(name) > 35 else name
        is_doc = node_type == "Document"
        fig.add_trace(go.Scatter(
            x=[info["x"]], y=[info["y"]],
            mode="markers" if is_doc else "markers+text",
            marker={"size": size, "color": color, "line": {"width": 2, "color": "#0B1120"}},
            text=[] if is_doc else [display_name],
            textposition="bottom center",
            textfont={"size": 14, "color": "#E2E8F0", "family": "Inter"},
            hoverinfo="text", hovertext=[f"<b>{name}</b><br>Type: {node_type}"],
            showlegend=False,
        ))
        if is_doc:
            doc_annotations.append({
                "x": info["x"], "y": info["y"],
                "xref": "x", "yref": "y",
                "text": display_name,
                "showarrow": False,
                "textangle": 90,
                "xanchor": "center",
                "yanchor": "top",
                "yshift": -16,
                "font": {"size": 10, "color": "#94A3B8", "family": "Inter"},
            })

    ys = [p["y"] for p in positions.values()]
    xs = [p["x"] for p in positions.values()]
    fig.update_layout(
        height=700,
        margin={"l": 10, "r": 10, "t": 30, "b": 120},
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False,
               "range": [min(xs) - 2, max(xs) + 2]},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False,
               "range": [min(ys) - 5, max(ys) + 1.5]},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter", "color": "#CBD5E1"},
        annotations=doc_annotations,
    )
    st.plotly_chart(fig, width="stretch", key=f"v4_graph_explorer_{idx}")


def _layout_nodes(graph_path: list[dict]) -> dict[str, dict]:
    """Build layout mapping for nodes in semantic layers."""
    seen: set[str] = set()
    nodes_by_type: dict[str, list[str]] = {}
    for edge in graph_path:
        for key, type_key in [("from_node", "from_type"), ("to_node", "to_type")]:
            name = edge.get(key, "")
            ntype = edge.get(type_key, "")
            if name and name not in seen:
                seen.add(name)
                nodes_by_type.setdefault(ntype, []).append(name)
    if not seen:
        return {}
    positions: dict[str, dict] = {}
    for ntype in _LAYER_ORDER:
        names = nodes_by_type.get(ntype, [])
        if not names:
            continue
        y = _LAYER_Y.get(ntype, 0.0)
        x_sp = 1.6 if ntype == "Document" else 2.2
        total_width = (len(names) - 1) * x_sp
        x_start = -total_width / 2
        for i, name in enumerate(names):
            positions[name] = {"x": x_start + i * x_sp, "y": y, "type": ntype}
    for ntype, names in nodes_by_type.items():
        if ntype not in _LAYER_ORDER:
            y = -3.0
            total_width = (len(names) - 1) * 2.2
            x_start = -total_width / 2
            for i, name in enumerate(names):
                if name not in positions:
                    positions[name] = {"x": x_start + i * 2.2, "y": y, "type": ntype}
    return positions
