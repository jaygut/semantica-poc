"""GraphRAG Chat - split-panel reasoning-transparent query interface for MARIS v3.

This is the hero feature of the v3 Intelligence Platform. It combines a chat
interface (left panel, 60%) with a real-time reasoning pipeline transparency
panel (right panel, 40%). Below both panels, a Plotly graph explorer renders
the subgraph used to answer the most recent query.

The module supports two modes:
- live: runs the QueryClassifier client-side for transparency, then calls
  the MARIS API for the full answer.
- demo: uses StaticBundleClient with 63 precomputed responses and shows
  classification metadata from the precomputed payload.
"""

from __future__ import annotations

import html
import logging
import re
import time
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from investor_demo.components.v3.shared import (
    axiom_tag,
    confidence_badge,
    tier_badge,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SITE_SHORT_MAP: dict[str, str] = {
    "Cabo Pulmo National Park": "Cabo Pulmo",
    "Shark Bay World Heritage Area": "Shark Bay",
}

_COMPARISON_KEYWORDS = ("compare", "versus", "vs", "differ")
_MECHANISM_KEYWORDS = ("how does", "how do", "what is blue carbon")

_SITE_DETECT: list[tuple[str, str]] = [
    ("cabo pulmo", "Cabo Pulmo National Park"),
    ("shark bay", "Shark Bay World Heritage Area"),
    ("great barrier reef", "Great Barrier Reef Marine Park"),
]

# Graph layout - semantic layer ordering (top to bottom)
_LAYER_ORDER = ["MPA", "Habitat", "EcosystemService", "BridgeAxiom", "Document"]
_LAYER_Y: dict[str, float] = {
    "MPA": 5.0,
    "Habitat": 3.8,
    "EcosystemService": 2.4,
    "BridgeAxiom": 1.0,
    "Document": -1.0,
}
_NODE_SIZES: dict[str, int] = {
    "MPA": 50,
    "EcosystemService": 40,
    "BridgeAxiom": 36,
    "Document": 22,
    "Habitat": 34,
}

_TYPE_COLORS: dict[str, str] = {
    "MPA": "#F1C40F",
    "Species": "#059669",
    "EcosystemService": "#1ABC9C",
    "BridgeAxiom": "#7C3AED",
    "Document": "#64748B",
    "Habitat": "#10B981",
    "FinancialInstrument": "#D97706",
}
_TIER_COLORS: dict[str, str] = {
    "T1": "#2ECC71",
    "T2": "#3498DB",
    "T3": "#E67E22",
    "T4": "#E74C3C",
}
_TYPE_LABELS: dict[str, str] = {
    "MPA": "Marine Protected Area",
    "EcosystemService": "Ecosystem Service",
    "BridgeAxiom": "Bridge Axiom",
    "Document": "Peer-Reviewed Source",
    "Habitat": "Habitat",
}
_DEFAULT_COLOR = "#5B9BD5"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_graphrag_chat(
    data: dict,
    site: str,
    mode: str,
    **kwargs: Any,
) -> None:
    """Render the GraphRAG Chat tab inside the v3 dashboard.

    Parameters
    ----------
    data : dict
        Static bundle dict (Cabo Pulmo format or case study JSON).
    site : str
        Canonical site name, e.g. "Cabo Pulmo National Park".
    mode : str
        "live" or "demo".
    **kwargs
        Must include ``client`` - a LiveAPIClient or StaticBundleClient.
    """
    client = kwargs.get("client")
    if client is None:
        st.error("No API client provided. Cannot render GraphRAG Chat.")
        return

    # Resolve short site name for display
    site_short = _SITE_SHORT_MAP.get(site, site.split()[0] if site else "site")

    # Session state for chat history
    if "v3_chat_history" not in st.session_state:
        st.session_state.v3_chat_history = []

    # Section header
    st.markdown(
        '<div class="section-header">ASK MARIS - GRAPHRAG INTELLIGENCE</div>'
        '<div class="section-desc">'
        "Natural-language queries with full reasoning pipeline transparency. "
        "Every answer traces back to DOI-backed evidence through the knowledge graph."
        "</div>",
        unsafe_allow_html=True,
    )

    # Quick query buttons
    quick_queries = _build_quick_queries(site_short)
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#94A3B8;'
        'margin-bottom:10px;text-transform:uppercase;letter-spacing:1px">'
        "Quick queries</div>",
        unsafe_allow_html=True,
    )
    row1 = st.columns(3)
    for i, q in enumerate(quick_queries[:3]):
        with row1[i]:
            if st.button(q, key=f"v3_quick_{i}", width="stretch"):
                _submit_query(client, q, mode)
    row2 = st.columns(3)
    for i, q in enumerate(quick_queries[3:]):
        with row2[i]:
            if st.button(q, key=f"v3_quick_{i + 3}", width="stretch"):
                _submit_query(client, q, mode)

    # Custom text input
    with st.form(key="v3_query_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ask MARIS anything",
            placeholder="e.g., What is the tourism elasticity coefficient?",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Ask MARIS", width="stretch")
        if submitted and user_input:
            _submit_query(client, user_input, mode)

    # Render history (newest first)
    for idx, entry in enumerate(reversed(st.session_state.v3_chat_history)):
        _render_split_response(entry, idx, mode)


# ---------------------------------------------------------------------------
# Quick queries
# ---------------------------------------------------------------------------


def _build_quick_queries(site_short: str) -> list[str]:
    """Return 6 quick-query strings, personalized to the active site."""
    return [
        f"What is {site_short} worth?",
        "What evidence supports the valuation?",
        "How does BA-001 work?",
        "Compare Cabo Pulmo and Shark Bay",
        "What are the risks?",
        "How does seagrass sequester carbon?",
    ]


# ---------------------------------------------------------------------------
# Query submission
# ---------------------------------------------------------------------------


def _detect_site(question: str) -> str | None:
    """Detect site from question text. Returns None for comparison/mechanism queries."""
    q_lower = question.lower()
    if any(kw in q_lower for kw in _COMPARISON_KEYWORDS):
        return None
    if any(kw in q_lower for kw in _MECHANISM_KEYWORDS):
        sites_found = sum(1 for pat, _ in _SITE_DETECT if pat in q_lower)
        if sites_found == 0:
            return None
    for pattern, canonical in _SITE_DETECT:
        if pattern in q_lower:
            return canonical
    return None


def _run_classifier(question: str) -> dict:
    """Run the QueryClassifier client-side for pipeline transparency.

    Falls back gracefully if the classifier module is not importable (e.g.
    when running outside the maris package environment).
    """
    try:
        from maris.query.classifier import QueryClassifier

        classifier = QueryClassifier()  # No LLM needed - keyword only
        start = time.monotonic()
        result = classifier.classify(question)
        elapsed_ms = (time.monotonic() - start) * 1000
        result["_classify_ms"] = round(elapsed_ms, 1)
        result["_method"] = "keyword" if result.get("confidence", 0) >= 0.6 else "LLM fallback"
        return result
    except ImportError:
        logger.warning("QueryClassifier not available - returning stub classification")
        return {
            "category": "unknown",
            "site": None,
            "metrics": [],
            "confidence": 0.0,
            "caveats": ["Classifier not available in this environment"],
            "_classify_ms": 0.0,
            "_method": "unavailable",
        }
    except Exception:
        logger.exception("Classification failed")
        return {
            "category": "error",
            "site": None,
            "metrics": [],
            "confidence": 0.0,
            "caveats": ["Classification error"],
            "_classify_ms": 0.0,
            "_method": "error",
        }


def _submit_query(client: Any, question: str, mode: str) -> None:
    """Submit a query, run classification, and store results in session state."""
    # Client-side classification (live mode only runs the real classifier)
    classification = _run_classifier(question) if mode == "live" else {}

    # Detect site for API call
    site = _detect_site(question)

    # Call the API / static client
    try:
        start = time.monotonic()
        response = client.query(question, site=site)
        elapsed_ms = (time.monotonic() - start) * 1000
        response["_query_ms"] = round(elapsed_ms, 1)
    except Exception:
        logger.exception("API query failed for: %s", question)
        # Fall back to precomputed responses instead of showing 0% confidence
        try:
            from investor_demo.api_client import StaticBundleClient

            fallback_client = StaticBundleClient()
            response = fallback_client.query(question, site=site)
            if (
                response.get("confidence", 0) == 0.0
                and response.get("answer", "").startswith("I don't have")
            ):
                # Even precomputed didn't match - show a nicer message
                response = {
                    "answer": (
                        "This query could not be answered in demo mode. "
                        "Start the MARIS API for live responses, or try one "
                        "of the quick queries above."
                    ),
                    "confidence": 0.0,
                    "evidence": [],
                    "axioms_used": [],
                    "caveats": ["Demo mode - live API not available"],
                    "graph_path": [],
                    "_query_ms": 0.0,
                }
            else:
                response["_query_ms"] = 0.0
                if "caveats" not in response:
                    response["caveats"] = []
                response["caveats"].append(
                    "Response from precomputed cache (API unavailable)"
                )
        except Exception:
            response = {
                "answer": (
                    "The query service is temporarily unavailable. "
                    "Please try again or use a different query."
                ),
                "confidence": 0.0,
                "evidence": [],
                "axioms_used": [],
                "caveats": ["API error - response generated from fallback"],
                "graph_path": [],
                "_query_ms": 0.0,
            }

    st.session_state.v3_chat_history.append({
        "question": question,
        "response": response,
        "classification": classification,
    })


# ---------------------------------------------------------------------------
# Split-panel response rendering
# ---------------------------------------------------------------------------


def _render_split_response(entry: dict, idx: int, mode: str) -> None:
    """Render a single query result as a split panel: chat left, pipeline right."""
    question = entry["question"]
    resp = entry["response"]
    classification = entry.get("classification", {})

    # Question header bar
    st.markdown(
        f'<div style="background:rgba(10,18,38,0.6);border:1px solid #1E293B;'
        f"border-radius:10px 10px 0 0;padding:14px 24px;margin-top:24px;"
        f'font-size:17px;color:#E2E8F0;font-weight:500">'
        f"{_escape(question)}</div>",
        unsafe_allow_html=True,
    )

    # Split columns: 60% chat, 40% pipeline
    col_chat, col_pipeline = st.columns([3, 2])

    with col_chat:
        _render_chat_panel(resp, idx)

    with col_pipeline:
        _render_pipeline_panel(resp, classification, mode)

    # Graph explorer below the split panel
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
    confidence_breakdown = resp.get("confidence_breakdown")

    # Confidence badge + axiom tags
    badge_html = confidence_badge(confidence)
    tags_html = "".join(axiom_tag(ax) for ax in axioms) if axioms else ""

    st.markdown(
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;'
        f'margin-bottom:12px">{badge_html}{tags_html}</div>',
        unsafe_allow_html=True,
    )

    # Answer body
    answer_html = _md_to_html(answer)
    st.markdown(
        f'<div style="font-size:17px;color:#B0BEC5;line-height:1.7;'
        f'padding:8px 0 16px 0">{answer_html}</div>',
        unsafe_allow_html=True,
    )

    # Caveats
    if caveats:
        caveat_items = "".join(
            f'<li style="color:#94A3B8;font-size:14px;line-height:1.6;'
            f'margin-bottom:2px">{_escape(c)}</li>'
            for c in caveats
        )
        st.markdown(
            f'<div style="background:#0D1526;border:1px solid #1E293B;'
            f'border-radius:8px;padding:12px 16px;margin-bottom:12px">'
            f'<div style="font-size:13px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:1.5px;color:#64748B;margin-bottom:6px">Caveats</div>'
            f"<ul style='margin:0;padding-left:20px'>{caveat_items}</ul></div>",
            unsafe_allow_html=True,
        )

    # Evidence chain expander
    if evidence:
        with st.expander("Show evidence chain", expanded=False):
            st.markdown(_evidence_table(evidence), unsafe_allow_html=True)

    # Confidence breakdown expander
    if confidence_breakdown and isinstance(confidence_breakdown, dict):
        with st.expander("Show confidence breakdown", expanded=False):
            st.markdown(
                _confidence_breakdown_html(confidence_breakdown),
                unsafe_allow_html=True,
            )


def _render_pipeline_panel(
    resp: dict, classification: dict, mode: str
) -> None:
    """Render the right-side reasoning pipeline transparency panel."""
    st.markdown(
        '<div style="font-size:14px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:1.5px;color:#5B9BD5;margin-bottom:12px">'
        "Reasoning Pipeline</div>",
        unsafe_allow_html=True,
    )

    if mode == "demo" and not classification:
        # Demo mode - show what we can from the response
        _render_demo_pipeline(resp)
        return

    # Step 1: CLASSIFY
    category = classification.get("category", resp.get("category", "unknown"))
    classify_site = classification.get("site", "")
    classify_conf = classification.get("confidence", 0.0)
    classify_ms = classification.get("_classify_ms", 0.0)
    classify_method = classification.get("_method", "keyword")
    classify_metrics = classification.get("metrics", [])

    site_display = classify_site or "Not detected"
    metrics_display = ", ".join(classify_metrics) if classify_metrics else "none"

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header">'
        '<span class="step-num">1</span> CLASSIFY'
        "</div>"
        '<div class="step-detail">'
        f"Category: <code>{_escape(category)}</code><br>"
        f"Site: {_escape(site_display)}<br>"
        f"Metrics: {_escape(metrics_display)}<br>"
        f"Confidence: {classify_conf:.2f} ({_escape(classify_method)})<br>"
        f"Latency: {classify_ms:.0f}ms"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 2: QUERY GRAPH
    graph_path = resp.get("graph_path", [])
    result_count = len(graph_path)
    query_ms = resp.get("_query_ms", 0.0)

    # Extract template name from category
    template_map: dict[str, str] = {
        "site_valuation": "SITE_VALUATION_QUERY",
        "provenance_drilldown": "PROVENANCE_DRILLDOWN_QUERY",
        "axiom_explanation": "AXIOM_EXPLANATION_QUERY",
        "comparison": "COMPARISON_QUERY",
        "risk_assessment": "RISK_ASSESSMENT_QUERY",
    }
    template_name = template_map.get(category, "DEFAULT_QUERY")

    # Count provenance edges
    provenance_edges = sum(
        1 for edge in graph_path if edge.get("relationship") == "EVIDENCED_BY"
    )

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header">'
        '<span class="step-num">2</span> QUERY GRAPH'
        "</div>"
        '<div class="step-detail">'
        f"Template: <code>{_escape(template_name)}</code><br>"
        f"Result edges: {result_count}<br>"
        f"Provenance edges: {provenance_edges}<br>"
        f"Total latency: {query_ms:.0f}ms"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 3: SYNTHESIZE
    evidence = resp.get("evidence", [])
    doi_count = sum(1 for e in evidence if e.get("doi"))
    answer_len = len(resp.get("answer", ""))

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header">'
        '<span class="step-num">3</span> SYNTHESIZE'
        "</div>"
        '<div class="step-detail">'
        f"DOI citations: {doi_count}<br>"
        f"Evidence items: {len(evidence)}<br>"
        f"Response length: {answer_len} chars"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 4: VALIDATE
    confidence = resp.get("confidence", 0.0)
    tier_dist = _compute_tier_distribution(evidence)
    caveat_count = len(resp.get("caveats", []))
    axiom_count = len(resp.get("axioms_used", []))

    tier_display = ", ".join(
        f"{tier}: {count}" for tier, count in sorted(tier_dist.items())
    ) if tier_dist else "N/A"

    conf_color = "#66BB6A" if confidence >= 0.8 else "#FFA726" if confidence >= 0.6 else "#EF5350"
    conf_pct = int(confidence * 100)

    st.markdown(
        '<div class="pipeline-step complete">'
        '<div class="step-header">'
        '<span class="step-num">4</span> VALIDATE'
        "</div>"
        '<div class="step-detail">'
        f'Composite confidence: <span style="color:{conf_color};font-weight:600">'
        f"{conf_pct}%</span><br>"
        f"Tier distribution: {_escape(tier_display)}<br>"
        f"Axioms used: {axiom_count}<br>"
        f"Caveats: {caveat_count}"
        "</div></div>",
        unsafe_allow_html=True,
    )


def _render_demo_pipeline(resp: dict) -> None:
    """Render a meaningful pipeline panel for demo mode.

    Shows all four pipeline stages with the data available from the
    precomputed response, plus a note explaining what each step does
    in live mode.
    """
    confidence = resp.get("confidence", 0.0)
    evidence = resp.get("evidence", [])
    axioms = resp.get("axioms_used", [])
    caveats = resp.get("caveats", [])
    graph_path = resp.get("graph_path", [])

    has_real_data = confidence > 0.0 or evidence or axioms

    # Determine step style based on whether we have real precomputed data
    step_class = "complete" if has_real_data else "pending"

    # Step 1: CLASSIFY
    # Infer category from response content if available
    answer_lower = resp.get("answer", "").lower()
    inferred_category = "unknown"
    if any(kw in answer_lower for kw in ("worth", "valuation", "esv", "$")):
        inferred_category = "site_valuation"
    elif any(kw in answer_lower for kw in ("evidence", "doi", "source", "provenance")):
        inferred_category = "provenance_drilldown"
    elif any(kw in answer_lower for kw in ("axiom", "coefficient", "ba-")):
        inferred_category = "axiom_explanation"
    elif any(kw in answer_lower for kw in ("compare", "versus", "both sites")):
        inferred_category = "comparison"
    elif any(kw in answer_lower for kw in ("risk", "threat", "degradation")):
        inferred_category = "risk_assessment"

    st.markdown(
        f'<div class="pipeline-step {step_class}">'
        '<div class="step-header">'
        '<span class="step-num">1</span> CLASSIFY'
        "</div>"
        '<div class="step-detail">'
        f"Category: <code>{_escape(inferred_category)}</code><br>"
        "Method: precomputed (keyword classifier in live mode)<br>"
        '<span style="color:#64748B;font-style:italic">'
        "Live mode runs the QueryClassifier with regex + LLM fallback"
        "</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Step 2: QUERY GRAPH
    result_count = len(graph_path)
    provenance_edges = sum(
        1 for edge in graph_path if edge.get("relationship") == "EVIDENCED_BY"
    )
    template_map: dict[str, str] = {
        "site_valuation": "SITE_VALUATION_QUERY",
        "provenance_drilldown": "PROVENANCE_DRILLDOWN_QUERY",
        "axiom_explanation": "AXIOM_EXPLANATION_QUERY",
        "comparison": "COMPARISON_QUERY",
        "risk_assessment": "RISK_ASSESSMENT_QUERY",
    }
    template_name = template_map.get(inferred_category, "DEFAULT_QUERY")

    graph_detail = (
        f"Template: <code>{_escape(template_name)}</code><br>"
        f"Result edges: {result_count}<br>"
        f"Provenance edges: {provenance_edges}<br>"
    )
    if not graph_path:
        graph_detail += (
            '<span style="color:#64748B;font-style:italic">'
            "Graph traversal runs against Neo4j (893 nodes) in live mode"
            "</span>"
        )

    st.markdown(
        f'<div class="pipeline-step {step_class}">'
        '<div class="step-header">'
        '<span class="step-num">2</span> QUERY GRAPH'
        "</div>"
        f'<div class="step-detail">{graph_detail}</div></div>',
        unsafe_allow_html=True,
    )

    # Step 3: SYNTHESIZE
    doi_count = sum(1 for e in evidence if e.get("doi"))
    answer_len = len(resp.get("answer", ""))

    synth_detail = (
        f"DOI citations: {doi_count}<br>"
        f"Evidence items: {len(evidence)}<br>"
        f"Response length: {answer_len} chars<br>"
    )
    if not evidence:
        synth_detail += (
            '<span style="color:#64748B;font-style:italic">'
            "LLM grounds graph results into narrative with DOI citations in live mode"
            "</span>"
        )

    st.markdown(
        f'<div class="pipeline-step {step_class}">'
        '<div class="step-header">'
        '<span class="step-num">3</span> SYNTHESIZE'
        "</div>"
        f'<div class="step-detail">{synth_detail}</div></div>',
        unsafe_allow_html=True,
    )

    # Step 4: VALIDATE
    tier_dist = _compute_tier_distribution(evidence)
    tier_display = ", ".join(
        f"{tier}: {count}" for tier, count in sorted(tier_dist.items())
    ) if tier_dist else "N/A"

    if confidence > 0.0:
        conf_color = (
            "#66BB6A" if confidence >= 0.8
            else "#FFA726" if confidence >= 0.6
            else "#EF5350"
        )
        conf_pct = int(confidence * 100)
        conf_html = (
            f'Composite confidence: <span style="color:{conf_color};font-weight:600">'
            f"{conf_pct}%</span><br>"
        )
    else:
        conf_html = (
            'Composite confidence: <span style="color:#94A3B8;font-weight:600">'
            "N/A</span> (demo mode)<br>"
        )

    validate_detail = (
        f"{conf_html}"
        f"Tier distribution: {_escape(tier_display)}<br>"
        f"Axioms used: {len(axioms)}<br>"
        f"Caveats: {len(caveats)}"
    )

    st.markdown(
        f'<div class="pipeline-step {step_class}">'
        '<div class="step-header">'
        '<span class="step-num">4</span> VALIDATE'
        "</div>"
        f'<div class="step-detail">{validate_detail}</div></div>',
        unsafe_allow_html=True,
    )

    # Demo mode note
    st.markdown(
        '<div style="font-size:13px;color:#475569;font-style:italic;'
        'margin-top:8px;padding:8px 12px;background:rgba(15,26,46,0.4);'
        'border-radius:6px;border:1px solid #1E293B">'
        "Showing precomputed response. Start the MARIS API for full "
        "pipeline transparency with real-time classification, graph "
        "traversal, and LLM synthesis."
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Markdown / HTML helpers
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text))


def _md_to_html(text: str) -> str:
    """Convert basic markdown to HTML for rendering inside styled divs.

    Handles **bold**, bullet lists (- or *), and line breaks.
    """
    text = _escape(text)

    # Bold: **text**
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
            result.append(
                f'<li style="color:#B0BEC5;font-size:16px;line-height:1.7;'
                f'margin-bottom:4px">{item}</li>'
            )
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            if stripped:
                result.append(f"<p>{stripped}</p>")

    if in_list:
        result.append("</ul>")

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Evidence table
# ---------------------------------------------------------------------------


def _evidence_table(evidence: list[dict]) -> str:
    """Render evidence items as a styled HTML table."""
    if not evidence:
        return ""

    rows = ""
    for item in evidence:
        tier = item.get("tier", "")
        title = _escape(item.get("title", "Unknown"))
        doi = item.get("doi", "")
        doi_url = item.get("doi_url", "")
        year = item.get("year", "")

        badge = tier_badge(tier) if tier else ""
        link = (
            f'<a href="{_escape(doi_url)}" target="_blank" '
            f'style="color:#5B9BD5;text-decoration:none">{_escape(doi)}</a>'
            if doi_url
            else _escape(doi)
        )

        rows += (
            f"<tr>"
            f'<td style="padding:12px 16px;border-bottom:1px solid #1E2D48">{badge}</td>'
            f'<td style="padding:12px 16px;color:#CBD5E1;border-bottom:1px solid #1E2D48;'
            f'font-size:15px">{title}</td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #1E2D48;'
            f'font-size:14px">{link}</td>'
            f'<td style="padding:12px 16px;color:#94A3B8;border-bottom:1px solid #1E2D48;'
            f'font-size:14px">{year}</td>'
            f"</tr>"
        )

    return (
        '<table class="evidence-table">'
        "<thead><tr>"
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;'
        'border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Tier</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;'
        'border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Title</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;'
        'border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">DOI</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;'
        'border-bottom:1px solid #243352;background:rgba(10,18,38,0.5)">Year</th>'
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


# ---------------------------------------------------------------------------
# Confidence breakdown
# ---------------------------------------------------------------------------


def _confidence_breakdown_html(breakdown: dict) -> str:
    """Render confidence breakdown as a mini-table with bar gauges."""
    factors = [
        ("Evidence Tier", "tier_base"),
        ("Path Length", "path_discount"),
        ("Data Freshness", "staleness_discount"),
        ("Source Coverage", "sample_factor"),
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
# Tier distribution helper
# ---------------------------------------------------------------------------


def _compute_tier_distribution(evidence: list[dict]) -> dict[str, int]:
    """Count evidence items by tier."""
    dist: dict[str, int] = {}
    for item in evidence:
        tier = item.get("tier", "")
        if tier:
            dist[tier] = dist.get(tier, 0) + 1
    return dist


# ---------------------------------------------------------------------------
# Graph explorer (adapted from graph_explorer.py)
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int = 35) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _layout_nodes(graph_path: list[dict]) -> dict[str, dict]:
    """Build a layout mapping node names to (x, y, type) positions.

    Arranges nodes in semantic layers: MPA at top, Documents at bottom.
    """
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

    x_spacing_default = 2.2
    x_spacing_doc = 1.6
    positions: dict[str, dict] = {}

    for ntype in _LAYER_ORDER:
        names = nodes_by_type.get(ntype, [])
        if not names:
            continue
        y = _LAYER_Y.get(ntype, 0.0)
        x_sp = x_spacing_doc if ntype == "Document" else x_spacing_default
        total_width = (len(names) - 1) * x_sp
        x_start = -total_width / 2
        for i, name in enumerate(names):
            positions[name] = {"x": x_start + i * x_sp, "y": y, "type": ntype}

    # Fallback row for types not in _LAYER_ORDER
    for ntype, names in nodes_by_type.items():
        if ntype not in _LAYER_ORDER:
            y = -3.0
            total_width = (len(names) - 1) * x_spacing_default
            x_start = -total_width / 2
            for i, name in enumerate(names):
                if name not in positions:
                    positions[name] = {
                        "x": x_start + i * x_spacing_default,
                        "y": y,
                        "type": ntype,
                    }

    return positions


def _get_node_color(name: str, node_type: str, node_metadata: dict) -> str:
    """Get node color, using tier colors for Document nodes."""
    if node_type == "Document":
        tier = node_metadata.get(name, {}).get("tier", "")
        return _TIER_COLORS.get(tier, _TYPE_COLORS.get("Document", _DEFAULT_COLOR))
    return _TYPE_COLORS.get(node_type, _DEFAULT_COLOR)


def _extract_node_metadata(graph_path: list[dict]) -> dict[str, dict]:
    """Extract metadata from graph path edges for tooltips."""
    metadata: dict[str, dict] = {}
    for edge in graph_path:
        for node_key, type_key in [("from_node", "from_type"), ("to_node", "to_type")]:
            name = edge.get(node_key, "")
            ntype = edge.get(type_key, "")
            if not name:
                continue
            if name not in metadata:
                metadata[name] = {}
            if "tier" in edge and ntype == "Document":
                metadata[name]["tier"] = edge["tier"]
            if "year" in edge and ntype == "Document":
                metadata[name]["year"] = edge["year"]
            if "doi" in edge and ntype == "Document":
                metadata[name]["doi"] = edge["doi"]
            # Default documents to T1 (MARIS library is 92% T1)
            if ntype == "Document" and "tier" not in metadata[name]:
                metadata[name]["tier"] = "T1"
    return metadata


def _build_hover(name: str, node_type: str, node_metadata: dict) -> str:
    """Build hover tooltip text."""
    meta = node_metadata.get(name, {})
    label = _TYPE_LABELS.get(node_type, node_type)
    parts = [f"<b>{name}</b>", f"Type: {label}"]
    tier = meta.get("tier", "")
    if tier:
        parts.append(f"Evidence tier: {tier}")
    year = meta.get("year", "")
    if year:
        parts.append(f"Year: {year}")
    doi = meta.get("doi", "")
    if doi:
        parts.append(f"DOI: {doi}")
    return "<br>".join(parts)


def _render_graph_explorer(graph_path: list[dict], idx: int = 0) -> None:
    """Render the Plotly network graph for a query's subgraph."""
    if not graph_path:
        st.info("No graph path available for this response.")
        return

    positions = _layout_nodes(graph_path)
    if not positions:
        return

    node_metadata = _extract_node_metadata(graph_path)
    fig = go.Figure()

    # Collect present types for layer headers
    types_present = {info["type"] for info in positions.values()}

    # Axis range
    xs = [p["x"] for p in positions.values()]
    x_min, x_max = min(xs) - 2.0, max(xs) + 2.0

    layer_colors: dict[str, str] = {
        "MPA": "rgba(241, 196, 15, 0.05)",
        "Habitat": "rgba(16, 185, 129, 0.04)",
        "EcosystemService": "rgba(26, 188, 156, 0.05)",
        "BridgeAxiom": "rgba(124, 58, 237, 0.05)",
        "Document": "rgba(100, 116, 139, 0.04)",
    }

    # Draw layer bands and headers
    for ntype in _LAYER_ORDER:
        if ntype not in types_present:
            continue
        y = _LAYER_Y[ntype]
        band_h = 0.55 if ntype != "Document" else 0.5
        fig.add_shape(
            type="rect",
            x0=x_min, x1=x_max, y0=y - band_h, y1=y + band_h,
            fillcolor=layer_colors.get(ntype, "rgba(0,0,0,0)"),
            line={"color": "rgba(255,255,255,0.02)", "width": 0},
            layer="below",
        )
        label = _TYPE_LABELS.get(ntype, ntype)
        header_color = _TYPE_COLORS.get(ntype, _DEFAULT_COLOR)
        fig.add_annotation(
            x=x_min + 0.15, y=y + band_h - 0.12,
            text=label.upper(), showarrow=False,
            font={"size": 13, "color": header_color, "family": "Inter"},
            xanchor="left", opacity=0.7,
        )

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

        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.3,
            arrowwidth=1.5, arrowcolor=edge_color, standoff=18,
        )

        # Edge label (skip EVIDENCED_BY to reduce clutter)
        if rel and not is_evidence:
            fig.add_annotation(
                x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                text=rel.replace("_", " "), showarrow=False,
                font={"size": 13, "color": "#CBD5E1", "family": "Inter"},
                bgcolor="rgba(11,17,32,0.92)",
                bordercolor="rgba(91,155,213,0.12)",
                borderpad=4, borderwidth=1,
            )

    # Draw nodes
    for name, info in positions.items():
        node_type = info["type"]
        color = _get_node_color(name, node_type, node_metadata)
        size = _NODE_SIZES.get(node_type, 34)
        hover = _build_hover(name, node_type, node_metadata)

        # Outer glow
        fig.add_trace(go.Scatter(
            x=[info["x"]], y=[info["y"]], mode="markers",
            marker={"size": size + 14, "color": color, "opacity": 0.13},
            hoverinfo="skip", showlegend=False,
        ))

        if node_type == "Document":
            meta = node_metadata.get(name, {})
            doi = meta.get("doi", "")
            doc_hover = hover
            if doi:
                doc_hover += f"<br><br>https://doi.org/{doi}"
            fig.add_trace(go.Scatter(
                x=[info["x"]], y=[info["y"]], mode="markers",
                marker={"size": size, "color": color, "line": {"width": 2, "color": "#0B1120"}},
                hoverinfo="text", hovertext=[doc_hover], showlegend=False,
            ))
            fig.add_annotation(
                x=info["x"], y=info["y"] - 0.35,
                text=_truncate(name, 45), showarrow=False,
                font={"size": 12, "color": "#94A3B8", "family": "Inter"},
                textangle=90, xanchor="center", yanchor="top",
            )
        else:
            display_name = _truncate(name)
            fig.add_trace(go.Scatter(
                x=[info["x"]], y=[info["y"]], mode="markers+text",
                marker={"size": size, "color": color, "line": {"width": 2, "color": "#0B1120"}},
                text=[display_name], textposition="bottom center",
                textfont={"size": 15, "color": "#E2E8F0", "family": "Inter"},
                hoverinfo="text", hovertext=[hover], showlegend=False,
            ))

    # Layout
    ys = [p["y"] for p in positions.values()]
    fig.update_layout(
        height=750,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        xaxis={
            "showgrid": False, "zeroline": False, "showticklabels": False,
            "range": [x_min - 0.3, x_max + 0.3],
        },
        yaxis={
            "showgrid": False, "zeroline": False, "showticklabels": False,
            "range": [min(ys) - 3.5, max(ys) + 1.2],
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter", "color": "#CBD5E1"},
    )

    st.plotly_chart(fig, width="stretch", key=f"v3_graph_explorer_{idx}")

    # Legend
    _render_graph_legend(graph_path)


def _render_graph_legend(graph_path: list[dict]) -> None:
    """Render node type and evidence tier legend below the graph."""
    legend_items: set[str] = set()
    for edge in graph_path:
        for key in ("from_type", "to_type"):
            t = edge.get(key, "")
            if t:
                legend_items.add(t)

    node_legend = ""
    for t in _LAYER_ORDER:
        if t not in legend_items:
            continue
        c = _TYPE_COLORS.get(t, _DEFAULT_COLOR)
        label = _TYPE_LABELS.get(t, t)
        node_legend += (
            f'<span style="display:inline-flex;align-items:center;'
            f'margin-right:18px;margin-bottom:4px">'
            f'<span style="width:10px;height:10px;border-radius:50%;'
            f'background:{c};display:inline-block;margin-right:6px"></span>'
            f'<span style="font-size:13px;color:#B0BEC5">{label}</span></span>'
        )

    tier_legend = ""
    if "Document" in legend_items:
        tier_labels = {
            "T1": "T1 Peer-reviewed",
            "T2": "T2 Institutional",
            "T3": "T3 Data repository",
            "T4": "T4 Grey literature",
        }
        for tier, color in _TIER_COLORS.items():
            tier_legend += (
                f'<span style="display:inline-flex;align-items:center;'
                f'margin-right:18px;margin-bottom:4px">'
                f'<span style="width:10px;height:10px;border-radius:50%;'
                f'background:{color};display:inline-block;margin-right:6px"></span>'
                f'<span style="font-size:13px;color:#B0BEC5">'
                f"{tier_labels.get(tier, tier)}</span></span>"
            )

    parts = []
    if node_legend:
        parts.append(
            f'<div style="margin-bottom:6px">'
            f'<span style="font-size:13px;font-weight:600;color:#64748B;'
            f'text-transform:uppercase;letter-spacing:1px;margin-right:10px">'
            f"Nodes</span>{node_legend}</div>"
        )
    if tier_legend:
        parts.append(
            f'<div style="margin-bottom:6px">'
            f'<span style="font-size:13px;font-weight:600;color:#64748B;'
            f'text-transform:uppercase;letter-spacing:1px;margin-right:10px">'
            f"Evidence Tier</span>{tier_legend}</div>"
        )

    if parts:
        st.markdown(
            f'<div style="padding:8px 0">{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )
