"""Interactive graph traversal visualization using Plotly."""

import plotly.graph_objects as go
import streamlit as st

# Node colors by entity type - evidence-tier aware
TYPE_COLORS = {
    "MPA": "#F1C40F",           # Gold
    "Species": "#059669",
    "EcosystemService": "#1ABC9C",  # Teal
    "BridgeAxiom": "#7C3AED",   # Purple
    "Document": "#64748B",      # Default for docs without tier
    "Habitat": "#10B981",       # Emerald
    "GovernanceScore": "#059669",
    "EcologicalState": "#10B981",
    "FinancialValue": "#D97706",
    "RiskOutcome": "#EF4444",
    "ResilienceBenefit": "#10B981",
    "Parameter": "#94A3B8",
}

# Evidence tier colors for Document nodes
TIER_COLORS = {
    "T1": "#2ECC71",   # Green - peer-reviewed
    "T2": "#3498DB",   # Blue - institutional
    "T3": "#E67E22",   # Orange - data repository
    "T4": "#E74C3C",   # Red - preprints/grey lit
}

# Friendly labels for the legend and layer headers
TYPE_LABELS = {
    "MPA": "Marine Protected Area",
    "EcosystemService": "Ecosystem Service",
    "BridgeAxiom": "Bridge Axiom",
    "Document": "Peer-Reviewed Source",
    "Habitat": "Habitat",
}

DEFAULT_COLOR = "#5B9BD5"

# Semantic layer ordering (top to bottom)
_LAYER_ORDER = ["MPA", "Habitat", "EcosystemService", "BridgeAxiom", "Document"]
_LAYER_Y = {
    "MPA": 5.0,
    "Habitat": 3.8,
    "EcosystemService": 2.4,
    "BridgeAxiom": 1.0,
    "Document": -1.0,
}

# Node marker sizes by type
_NODE_SIZES = {
    "MPA": 50,
    "EcosystemService": 40,
    "BridgeAxiom": 36,
    "Document": 22,
    "Habitat": 34,
}


def _truncate(text: str, max_len: int = 35) -> str:
    """Truncate text with ellipsis for display labels."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _doc_label(text: str, max_len: int = 40) -> str:
    """Shorter label for documents (rotated, needs to be compact)."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _layout_nodes(graph_path: list[dict]) -> dict:
    """Build a layout dict mapping node names to (x, y) positions.

    Arranges nodes in semantic layers: MPA at top, then Habitats,
    EcosystemServices, BridgeAxioms, and Documents at the bottom.
    """
    # Collect unique nodes with their types
    seen = set()
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

    # Use wider spacing for documents (rotated labels need horizontal room)
    x_spacing_default = 2.2
    x_spacing_doc = 1.6

    positions = {}

    for ntype in _LAYER_ORDER:
        names = nodes_by_type.get(ntype, [])
        if not names:
            continue

        y = _LAYER_Y.get(ntype, 0.0)
        n = len(names)
        x_sp = x_spacing_doc if ntype == "Document" else x_spacing_default
        total_width = (n - 1) * x_sp
        x_start = -total_width / 2

        for i, name in enumerate(names):
            positions[name] = {
                "x": x_start + i * x_sp,
                "y": y,
                "type": ntype,
            }

    # Handle any types not in _LAYER_ORDER (fallback row)
    for ntype, names in nodes_by_type.items():
        if ntype not in _LAYER_ORDER:
            y = -3.0
            n = len(names)
            total_width = (n - 1) * x_spacing_default
            x_start = -total_width / 2
            for i, name in enumerate(names):
                if name not in positions:
                    positions[name] = {
                        "x": x_start + i * x_spacing_default,
                        "y": y,
                        "type": ntype,
                    }

    return positions


def _get_edge_style(edge: dict, confidence_threshold: float = 0.0) -> dict | None:
    """Determine edge styling based on confidence level.

    Returns None if the edge should be hidden (below threshold).
    """
    confidence = edge.get("confidence", None)
    rel = edge.get("relationship", "")
    is_evidence = rel == "EVIDENCED_BY"

    # If confidence is provided, use it for styling
    if confidence is not None:
        if confidence < confidence_threshold:
            return None
        if confidence > 0.8:
            return {"color": "#5B9BD5", "width": 3.0, "dash": "solid"}
        elif confidence >= 0.5:
            return {"color": "#5B9BD5", "width": 2.0, "dash": "solid"}
        else:
            return {"color": "#475569", "width": 1.0, "dash": "dash"}

    # Default styling based on relationship type
    if is_evidence:
        return {"color": "#475569", "width": 1.2, "dash": "solid"}
    return {"color": "#5B9BD5", "width": 2.0, "dash": "solid"}


def _get_node_color(name: str, node_type: str, node_metadata: dict) -> str:
    """Get node color based on type and evidence tier for documents."""
    if node_type == "Document":
        tier = node_metadata.get(name, {}).get("tier", "")
        return TIER_COLORS.get(tier, TYPE_COLORS.get("Document", DEFAULT_COLOR))
    return TYPE_COLORS.get(node_type, DEFAULT_COLOR)


def _build_hover_text(name: str, node_type: str, node_metadata: dict) -> str:
    """Build enhanced hover tooltip with entity type, key metric, tier, and year."""
    meta = node_metadata.get(name, {})
    label = TYPE_LABELS.get(node_type, node_type)
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

    metric = meta.get("metric", "")
    if metric:
        parts.append(f"Metric: {metric}")

    return "<br>".join(parts)


def _extract_node_metadata(graph_path: list[dict]) -> dict:
    """Extract metadata from graph path edges for enhanced tooltips."""
    metadata: dict[str, dict] = {}
    for edge in graph_path:
        for node_key, type_key in [("from_node", "from_type"), ("to_node", "to_type")]:
            name = edge.get(node_key, "")
            ntype = edge.get(type_key, "")
            if not name:
                continue
            if name not in metadata:
                metadata[name] = {}
            # Extract tier from edge metadata if present
            if "tier" in edge and ntype == "Document":
                metadata[name]["tier"] = edge["tier"]
            if "year" in edge and ntype == "Document":
                metadata[name]["year"] = edge["year"]
            if "doi" in edge and ntype == "Document":
                metadata[name]["doi"] = edge["doi"]
            # Infer tier from Document node naming conventions
            if ntype == "Document" and "tier" not in metadata[name]:
                # Default documents to T1 since MARIS library is 92% T1
                metadata[name]["tier"] = "T1"
    return metadata


def render_graph_explorer(graph_path: list[dict], confidence_threshold: float = 0.0):
    """Render an interactive network visualization from a QueryResponse graph_path.

    Parameters
    ----------
    graph_path : list[dict]
        Each dict has from_node, from_type, relationship, to_node, to_type.
    confidence_threshold : float
        Hide edges with confidence below this value (0.0 = show all).
    """
    if not graph_path:
        st.info("No graph path available for this response.")
        return

    positions = _layout_nodes(graph_path)
    if not positions:
        return

    node_metadata = _extract_node_metadata(graph_path)

    fig = go.Figure()

    # Collect types present for layer headers
    types_present = set()
    for info in positions.values():
        types_present.add(info["type"])

    # Draw layer background bands
    xs = [p["x"] for p in positions.values()]
    x_min, x_max = min(xs) - 2.0, max(xs) + 2.0

    layer_colors = {
        "MPA": "rgba(241, 196, 15, 0.05)",
        "Habitat": "rgba(16, 185, 129, 0.04)",
        "EcosystemService": "rgba(26, 188, 156, 0.05)",
        "BridgeAxiom": "rgba(124, 58, 237, 0.05)",
        "Document": "rgba(100, 116, 139, 0.04)",
    }

    band_heights = {
        "MPA": 0.55,
        "Habitat": 0.55,
        "EcosystemService": 0.55,
        "BridgeAxiom": 0.55,
        "Document": 0.5,
    }

    for ntype in _LAYER_ORDER:
        if ntype not in types_present:
            continue
        y = _LAYER_Y[ntype]
        band_h = band_heights.get(ntype, 0.55)
        fig.add_shape(
            type="rect",
            x0=x_min,
            x1=x_max,
            y0=y - band_h,
            y1=y + band_h,
            fillcolor=layer_colors.get(ntype, "rgba(0,0,0,0)"),
            line=dict(color="rgba(255,255,255,0.02)", width=0),
            layer="below",
        )
        # Layer header on the left
        label = TYPE_LABELS.get(ntype, ntype)
        header_color = TYPE_COLORS.get(ntype, DEFAULT_COLOR)
        fig.add_annotation(
            x=x_min + 0.15,
            y=y + band_h - 0.12,
            text=label.upper(),
            showarrow=False,
            font=dict(size=12, color=header_color, family="Inter"),
            xanchor="left",
            opacity=0.7,
        )

    # Draw edges with confidence-based styling
    for edge in graph_path:
        src = edge.get("from_node", "")
        tgt = edge.get("to_node", "")
        rel = edge.get("relationship", "")

        if src not in positions or tgt not in positions:
            continue

        style = _get_edge_style(edge, confidence_threshold)
        if style is None:
            continue

        x0, y0 = positions[src]["x"], positions[src]["y"]
        x1, y1 = positions[tgt]["x"], positions[tgt]["y"]

        # Edge line
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(
                    color=style["color"],
                    width=style["width"],
                    dash=style["dash"],
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Arrow annotation
        fig.add_annotation(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.3,
            arrowwidth=1.5,
            arrowcolor=style["color"],
            standoff=18,
        )

        # Edge label at midpoint (skip for EVIDENCED_BY to reduce clutter)
        is_evidence = rel == "EVIDENCED_BY"
        if rel and not is_evidence:
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=rel.replace("_", " "),
                showarrow=False,
                font=dict(size=13, color="#CBD5E1", family="Inter"),
                bgcolor="rgba(11,17,32,0.92)",
                bordercolor="rgba(91,155,213,0.12)",
                borderpad=4,
                borderwidth=1,
            )

    # Draw nodes with tier-aware coloring and enhanced tooltips
    for name, info in positions.items():
        node_type = info["type"]
        color = _get_node_color(name, node_type, node_metadata)
        size = _NODE_SIZES.get(node_type, 34)
        hover = _build_hover_text(name, node_type, node_metadata)

        # Outer glow
        fig.add_trace(
            go.Scatter(
                x=[info["x"]],
                y=[info["y"]],
                mode="markers",
                marker=dict(size=size + 14, color=color, opacity=0.13),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        if node_type == "Document":
            # Document nodes: marker only, label as rotated annotation below
            # Show DOI in hover tooltip as clickable-style text
            meta = node_metadata.get(name, {})
            doi = meta.get("doi", "")
            doc_hover = hover
            if doi:
                doc_hover += f"<br><br>https://doi.org/{doi}"

            fig.add_trace(
                go.Scatter(
                    x=[info["x"]],
                    y=[info["y"]],
                    mode="markers",
                    marker=dict(
                        size=size,
                        color=color,
                        line=dict(width=2, color="#0B1120"),
                    ),
                    hoverinfo="text",
                    hovertext=[doc_hover],
                    showlegend=False,
                )
            )
            # Rotated label below the document node
            fig.add_annotation(
                x=info["x"],
                y=info["y"] - 0.35,
                text=_doc_label(name, 45),
                showarrow=False,
                font=dict(size=11, color="#94A3B8", family="Inter"),
                textangle=90,
                xanchor="center",
                yanchor="top",
            )
        else:
            # Non-document nodes: marker + text label below
            display_name = _truncate(name)
            fig.add_trace(
                go.Scatter(
                    x=[info["x"]],
                    y=[info["y"]],
                    mode="markers+text",
                    marker=dict(
                        size=size,
                        color=color,
                        line=dict(width=2, color="#0B1120"),
                    ),
                    text=[display_name],
                    textposition="bottom center",
                    textfont=dict(size=15, color="#E2E8F0", family="Inter"),
                    hoverinfo="text",
                    hovertext=[hover],
                    showlegend=False,
                )
            )

    # Compute axis ranges
    ys = [p["y"] for p in positions.values()]
    y_pad_top = 1.2
    y_pad_bottom = 3.5  # extra room for rotated document labels

    fig.update_layout(
        height=950,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[x_min - 0.3, x_max + 0.3],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min(ys) - y_pad_bottom, max(ys) + y_pad_top],
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#CBD5E1"),
    )

    st.plotly_chart(fig, width="stretch")

    # Legend - node types
    legend_items = set()
    for edge in graph_path:
        for key in ("from_type", "to_type"):
            t = edge.get(key, "")
            if t:
                legend_items.add(t)

    node_legend_html = ""
    for t in _LAYER_ORDER:
        if t not in legend_items:
            continue
        c = TYPE_COLORS.get(t, DEFAULT_COLOR)
        label = TYPE_LABELS.get(t, t)
        node_legend_html += (
            f'<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{c};'
            f'display:inline-block;margin-right:8px"></span>'
            f'<span style="font-size:15px;color:#B0BEC5">{label}</span></span>'
        )

    # Evidence tier legend (if Document nodes present)
    tier_legend_html = ""
    if "Document" in legend_items:
        for tier, color in TIER_COLORS.items():
            tier_labels = {
                "T1": "T1 Peer-reviewed",
                "T2": "T2 Institutional",
                "T3": "T3 Data repository",
                "T4": "T4 Grey literature",
            }
            tier_legend_html += (
                f'<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
                f'<span style="width:12px;height:12px;border-radius:50%;background:{color};'
                f'display:inline-block;margin-right:8px"></span>'
                f'<span style="font-size:15px;color:#B0BEC5">{tier_labels.get(tier, tier)}</span></span>'
            )

    # Edge confidence legend
    edge_legend_html = (
        '<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
        '<span style="width:24px;height:3px;background:#5B9BD5;display:inline-block;margin-right:8px"></span>'
        '<span style="font-size:15px;color:#B0BEC5">High confidence</span></span>'
        '<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
        '<span style="width:24px;height:2px;background:#5B9BD5;display:inline-block;margin-right:8px"></span>'
        '<span style="font-size:15px;color:#B0BEC5">Medium confidence</span></span>'
        '<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
        '<span style="width:24px;height:1px;background:#475569;display:inline-block;margin-right:8px;'
        'border-top:1px dashed #475569"></span>'
        '<span style="font-size:15px;color:#B0BEC5">Low confidence</span></span>'
    )

    legend_html = ""
    if node_legend_html:
        legend_html += (
            f'<div style="margin-bottom:8px">'
            f'<span style="font-size:13px;font-weight:600;color:#64748B;text-transform:uppercase;'
            f'letter-spacing:1px;margin-right:12px">Nodes</span>'
            f'{node_legend_html}</div>'
        )
    if tier_legend_html:
        legend_html += (
            f'<div style="margin-bottom:8px">'
            f'<span style="font-size:13px;font-weight:600;color:#64748B;text-transform:uppercase;'
            f'letter-spacing:1px;margin-right:12px">Evidence Tier</span>'
            f'{tier_legend_html}</div>'
        )
    legend_html += (
        f'<div>'
        f'<span style="font-size:13px;font-weight:600;color:#64748B;text-transform:uppercase;'
        f'letter-spacing:1px;margin-right:12px">Edges</span>'
        f'{edge_legend_html}</div>'
    )

    st.markdown(
        f'<div style="display:flex;flex-direction:column;gap:4px;margin-top:8px;padding:12px 0">{legend_html}</div>',
        unsafe_allow_html=True,
    )
