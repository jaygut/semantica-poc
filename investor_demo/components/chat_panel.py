"""Ask MARIS chat panel - Streamlit component for natural language queries."""

import re
import streamlit as st


QUICK_QUERIES = [
    "What is this site worth?",
    "Why should I trust the ESV number?",
    "How does biomass translate to tourism?",
    "What if protection fails?",
    "Compare to other sites",
]


def _confidence_badge(confidence: float) -> str:
    """Return an HTML badge colored by confidence level."""
    if confidence >= 0.8:
        color = "#66BB6A"
        bg = "rgba(46, 125, 50, 0.2)"
        border = "rgba(46, 125, 50, 0.35)"
    elif confidence >= 0.6:
        color = "#FFA726"
        bg = "rgba(245, 166, 35, 0.2)"
        border = "rgba(245, 166, 35, 0.35)"
    else:
        color = "#EF5350"
        bg = "rgba(239, 83, 80, 0.2)"
        border = "rgba(239, 83, 80, 0.35)"

    pct = int(confidence * 100)
    return (
        f'<span style="display:inline-block;padding:5px 14px;border-radius:4px;'
        f"font-size:14px;font-weight:600;letter-spacing:0.5px;"
        f"color:{color};background:{bg};border:1px solid {border};"
        f'text-transform:uppercase">'
        f"Confidence: {pct}%</span>"
    )


def _axiom_tags(axioms: list[str]) -> str:
    """Render axiom IDs as pill tags."""
    tags = ""
    for ax in axioms:
        tags += (
            f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
            f"font-size:13px;font-weight:600;margin-right:6px;margin-bottom:4px;"
            f"color:#5B9BD5;background:rgba(91,155,213,0.15);"
            f'border:1px solid rgba(91,155,213,0.3)">'
            f"{ax}</span>"
        )
    return tags


def _md_to_html(text: str) -> str:
    """Convert basic markdown patterns to HTML for display inside styled divs.

    Handles: **bold**, bullet lists (- or *), and line breaks.
    """
    # Escape HTML entities first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # Convert bullet lines (starting with - or *) to list items
    lines = text.split("\n")
    result = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            if not in_list:
                result.append('<ul style="margin:8px 0;padding-left:22px">')
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped)
            result.append(
                f'<li style="color:#B0BEC5;font-size:17px;line-height:1.7;margin-bottom:4px">{item}</li>'
            )
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            if stripped:
                result.append(f"<p>{stripped}</p>")
            else:
                result.append("")

    if in_list:
        result.append("</ul>")

    return "\n".join(result)


def _evidence_table(evidence: list[dict]) -> str:
    """Render evidence items as an HTML table."""
    if not evidence:
        return ""
    rows = ""
    for e in evidence:
        tier = e.get("tier", "")
        title = e.get("title", "Unknown")
        doi = e.get("doi", "")
        doi_url = e.get("doi_url", "")
        year = e.get("year", "")

        tier_html = (
            f'<span style="font-weight:600;color:#66BB6A">{tier}</span>'
            if tier == "T1"
            else f'<span style="font-weight:600;color:#FFA726">{tier}</span>'
        )

        link = (
            f'<a href="{doi_url}" target="_blank" style="color:#5B9BD5;text-decoration:none">{doi}</a>'
            if doi_url
            else doi
        )

        rows += (
            f"<tr>"
            f'<td style="padding:12px 16px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:14px">{tier_html}</td>'
            f'<td style="padding:12px 16px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:15px">{title}</td>'
            f'<td style="padding:12px 16px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:14px">{link}</td>'
            f'<td style="padding:12px 16px;color:#94A3B8;border-bottom:1px solid #1E2D48;font-size:14px">{year}</td>'
            f"</tr>"
        )

    return (
        '<table style="width:100%;border-collapse:collapse;margin-top:8px;'
        "background:linear-gradient(145deg,#162039 0%,#1A2744 100%);"
        'border-radius:8px;overflow:hidden;border:1px solid #243352">'
        "<thead><tr>"
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">Tier</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">Title</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">DOI</th>'
        '<th style="text-align:left;padding:12px 16px;font-size:13px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">Year</th>'
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def render_chat_panel(client):
    """Render the Ask MARIS chat panel.

    Parameters
    ----------
    client : LiveAPIClient | StaticBundleClient
        The API client (live or static fallback).
    """
    # Initialize chat history
    if "maris_chat_history" not in st.session_state:
        st.session_state.maris_chat_history = []

    # Quick query buttons
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#94A3B8;margin-bottom:12px">'
        "Quick queries</div>",
        unsafe_allow_html=True,
    )

    # Render quick query buttons in a row
    cols = st.columns(len(QUICK_QUERIES))
    for i, q in enumerate(QUICK_QUERIES):
        with cols[i]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                _submit_query(client, q)

    # Custom text input (using form to clear on submit and avoid rerun loop)
    with st.form(key="maris_query_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ask MARIS anything about this site",
            placeholder="e.g., What is the tourism elasticity coefficient?",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Ask MARIS", use_container_width=True)
        if submitted and user_input:
            _submit_query(client, user_input)

    # Render chat history (newest first)
    for i, entry in enumerate(reversed(st.session_state.maris_chat_history)):
        _render_response(entry, i)


def _submit_query(client, question: str):
    """Submit a query and store the result in session state."""
    response = client.query(question, site="Cabo Pulmo National Park")
    st.session_state.maris_chat_history.append(
        {"question": question, "response": response}
    )


def _confidence_breakdown_html(breakdown: dict) -> str:
    """Render confidence breakdown as an HTML mini-table."""
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
        bar_color = "#66BB6A" if val >= 0.8 else "#FFA726" if val >= 0.5 else "#EF5350"
        rows += (
            f"<tr>"
            f'<td style="padding:6px 12px;color:#94A3B8;font-size:13px;border-bottom:1px solid #1E2D48">{label}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #1E2D48">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<div style="flex:1;height:6px;background:#1E2D48;border-radius:3px;overflow:hidden">'
            f'<div style="width:{pct}%;height:100%;background:{bar_color};border-radius:3px"></div></div>'
            f'<span style="color:#CBD5E1;font-size:13px;font-weight:600;min-width:35px">{pct}%</span>'
            f"</div></td></tr>"
        )

    explanation = breakdown.get("explanation", "")
    composite = int(breakdown.get("composite", 0.0) * 100)

    return (
        f'<div style="margin-top:4px">'
        f'<div style="font-size:13px;font-weight:600;color:#94A3B8;margin-bottom:8px">'
        f"Composite: {composite}%</div>"
        f'<table style="width:100%;border-collapse:collapse;background:rgba(15,26,46,0.6);'
        f'border-radius:6px;overflow:hidden;border:1px solid #1E2D48">'
        f"{rows}</table>"
        f'<div style="margin-top:8px;font-size:12px;color:#64748B;font-style:italic">'
        f"{explanation}</div></div>"
    )


def _render_response(entry: dict, idx: int):
    """Render a single question/response pair."""
    question = entry["question"]
    resp = entry["response"]

    answer = resp.get("answer", "No response available.")
    confidence = resp.get("confidence", 0.0)
    axioms = resp.get("axioms_used", [])
    caveats = resp.get("caveats", [])
    evidence = resp.get("evidence", [])
    graph_path = resp.get("graph_path", [])
    confidence_breakdown = resp.get("confidence_breakdown")

    # Outer card wrapping the entire response
    st.markdown(
        f'<div style="background:linear-gradient(145deg,#0F1A2E 0%,#162039 100%);'
        f"border-radius:10px;border:1px solid #1E293B;overflow:hidden;"
        f'margin-top:20px">'
        # Question bar at top of card
        f'<div style="padding:16px 24px;background:rgba(10,18,38,0.6);'
        f'border-bottom:1px solid #1E293B">'
        f'<span style="font-size:17px;color:#E2E8F0;font-weight:500">{question}</span>'
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Confidence badge + axiom tags row
    badge = _confidence_badge(confidence)
    tags = _axiom_tags(axioms) if axioms else ""

    st.markdown(
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;'
        f'padding:14px 24px 0 24px;background:linear-gradient(145deg,#0F1A2E 0%,#162039 100%);'
        f'border-left:1px solid #1E293B;border-right:1px solid #1E293B">'
        f"{badge}{tags}</div>",
        unsafe_allow_html=True,
    )

    # Answer body - convert markdown to HTML for proper rendering
    answer_html = _md_to_html(answer)

    st.markdown(
        f'<div class="maris-answer" style="padding:16px 24px 20px 24px;'
        f"background:linear-gradient(145deg,#0F1A2E 0%,#162039 100%);"
        f"border-left:1px solid #1E293B;border-right:1px solid #1E293B;"
        f'font-size:17px;color:#B0BEC5;line-height:1.7">'
        f"{answer_html}</div>",
        unsafe_allow_html=True,
    )

    # Caveats - integrated into the card
    if caveats:
        caveat_items = "".join(
            f'<li style="color:#94A3B8;font-size:15px;line-height:1.6;margin-bottom:2px">{c}</li>'
            for c in caveats
        )
        st.markdown(
            f'<div style="padding:14px 24px 16px 24px;margin:0;'
            f"background:#0D1526;"
            f"border-left:1px solid #1E293B;border-right:1px solid #1E293B;"
            f'border-bottom:1px solid #1E293B;border-radius:0 0 10px 10px">'
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

    # Graph path - stored for graph explorer
    if graph_path:
        st.session_state[f"graph_path_{idx}"] = graph_path
        return graph_path

    return None
