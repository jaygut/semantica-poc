"""Ask MARIS chat panel - Streamlit component for natural language queries."""

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
        f'<span style="display:inline-block;padding:4px 12px;border-radius:4px;'
        f"font-size:13px;font-weight:600;letter-spacing:0.5px;"
        f"color:{color};background:{bg};border:1px solid {border};"
        f'text-transform:uppercase">'
        f"Confidence: {pct}%</span>"
    )


def _axiom_tags(axioms: list[str]) -> str:
    """Render axiom IDs as pill tags."""
    tags = ""
    for ax in axioms:
        tags += (
            f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
            f"font-size:12px;font-weight:600;margin-right:6px;margin-bottom:4px;"
            f"color:#5B9BD5;background:rgba(91,155,213,0.15);"
            f'border:1px solid rgba(91,155,213,0.3)">'
            f"{ax}</span>"
        )
    return tags


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
            f'<td style="padding:10px 14px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:13px">{tier_html}</td>'
            f'<td style="padding:10px 14px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:14px">{title}</td>'
            f'<td style="padding:10px 14px;color:#CBD5E1;border-bottom:1px solid #1E2D48;font-size:13px">{link}</td>'
            f'<td style="padding:10px 14px;color:#94A3B8;border-bottom:1px solid #1E2D48;font-size:13px">{year}</td>'
            f"</tr>"
        )

    return (
        '<table style="width:100%;border-collapse:collapse;margin-top:8px;'
        "background:linear-gradient(145deg,#162039 0%,#1A2744 100%);"
        'border-radius:8px;overflow:hidden;border:1px solid #243352">'
        "<thead><tr>"
        '<th style="text-align:left;padding:10px 14px;font-size:12px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">Tier</th>'
        '<th style="text-align:left;padding:10px 14px;font-size:12px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">Title</th>'
        '<th style="text-align:left;padding:10px 14px;font-size:12px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#94A3B8;border-bottom:1px solid #243352;'
        'background:rgba(10,18,38,0.5)">DOI</th>'
        '<th style="text-align:left;padding:10px 14px;font-size:12px;font-weight:600;'
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

    # Custom text input
    user_input = st.text_input(
        "Ask MARIS anything about this site",
        placeholder="e.g., What is the tourism elasticity coefficient?",
        key="maris_chat_input",
        label_visibility="collapsed",
    )
    if user_input:
        _submit_query(client, user_input)
        # Clear input by rerunning (Streamlit pattern)
        st.rerun()

    # Render chat history (newest first)
    for i, entry in enumerate(reversed(st.session_state.maris_chat_history)):
        _render_response(entry, i)


def _submit_query(client, question: str):
    """Submit a query and store the result in session state."""
    response = client.query(question, site="Cabo Pulmo National Park")
    st.session_state.maris_chat_history.append(
        {"question": question, "response": response}
    )


def _render_response(entry: dict, idx: int):
    """Render a single question/response pair."""
    question = entry["question"]
    resp = entry["response"]

    # Question
    st.markdown(
        f'<div style="background:#1A2744;border-radius:8px;padding:12px 18px;'
        f"margin-top:20px;margin-bottom:8px;border:1px solid #243352;"
        f'font-size:16px;color:#E2E8F0;font-weight:500">'
        f"{question}</div>",
        unsafe_allow_html=True,
    )

    # Answer card
    answer = resp.get("answer", "No response available.")
    confidence = resp.get("confidence", 0.0)
    axioms = resp.get("axioms_used", [])
    caveats = resp.get("caveats", [])
    evidence = resp.get("evidence", [])
    graph_path = resp.get("graph_path", [])

    # Confidence badge + axiom tags
    badge = _confidence_badge(confidence)
    tags = _axiom_tags(axioms) if axioms else ""

    st.markdown(
        f'<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px">'
        f"{badge}{tags}</div>",
        unsafe_allow_html=True,
    )

    # Answer text
    st.markdown(
        f'<div style="background:linear-gradient(145deg,#0F1A2E 0%,#162039 100%);'
        f"border-radius:10px;padding:20px 24px;border:1px solid #1E293B;"
        f'font-size:16px;color:#B0BEC5;line-height:1.7;white-space:pre-wrap">'
        f"{answer}</div>",
        unsafe_allow_html=True,
    )

    # Caveats
    if caveats:
        caveat_items = "".join(
            f'<li style="color:#94A3B8;font-size:14px;line-height:1.6">{c}</li>'
            for c in caveats
        )
        st.markdown(
            f'<div style="margin-top:8px;padding:10px 16px;background:#0D1526;'
            f'border-radius:6px;border:1px solid #1E293B">'
            f'<div style="font-size:12px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:1px;color:#64748B;margin-bottom:4px">Caveats</div>'
            f"<ul style='margin:0;padding-left:18px'>{caveat_items}</ul></div>",
            unsafe_allow_html=True,
        )

    # Evidence chain expander
    if evidence:
        with st.expander("Show evidence chain", expanded=False):
            st.markdown(_evidence_table(evidence), unsafe_allow_html=True)

    # Graph path - stored for graph explorer
    if graph_path:
        st.session_state[f"graph_path_{idx}"] = graph_path
        return graph_path

    return None
