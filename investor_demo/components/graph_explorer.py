"""Interactive graph traversal visualization using Plotly."""

import plotly.graph_objects as go
import streamlit as st

# Node colors by entity type
TYPE_COLORS = {
    "MPA": "#2563EB",
    "Species": "#059669",
    "EcosystemService": "#D97706",
    "BridgeAxiom": "#7C3AED",
    "Document": "#64748B",
    "Habitat": "#10B981",
    "GovernanceScore": "#059669",
    "EcologicalState": "#10B981",
    "FinancialValue": "#D97706",
    "RiskOutcome": "#EF4444",
    "ResilienceBenefit": "#10B981",
    "Parameter": "#94A3B8",
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


def render_graph_explorer(graph_path: list[dict]):
    """Render an interactive network visualization from a QueryResponse graph_path.

    Parameters
    ----------
    graph_path : list[dict]
        Each dict has from_node, from_type, relationship, to_node, to_type.
    """
    if not graph_path:
        st.info("No graph path available for this response.")
        return

    positions = _layout_nodes(graph_path)
    if not positions:
        return

    fig = go.Figure()

    # Collect types present for layer headers
    types_present = set()
    for info in positions.values():
        types_present.add(info["type"])

    # Draw layer background bands
    xs = [p["x"] for p in positions.values()]
    x_min, x_max = min(xs) - 2.0, max(xs) + 2.0

    layer_colors = {
        "MPA": "rgba(37, 99, 235, 0.05)",
        "Habitat": "rgba(16, 185, 129, 0.04)",
        "EcosystemService": "rgba(217, 119, 6, 0.05)",
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

    # Draw edges
    for edge in graph_path:
        src = edge.get("from_node", "")
        tgt = edge.get("to_node", "")
        rel = edge.get("relationship", "")

        if src not in positions or tgt not in positions:
            continue

        x0, y0 = positions[src]["x"], positions[src]["y"]
        x1, y1 = positions[tgt]["x"], positions[tgt]["y"]

        is_evidence = rel == "EVIDENCED_BY"
        edge_color = "#5B9BD5" if not is_evidence else "#475569"
        edge_width = 2.0 if not is_evidence else 1.2

        # Edge line
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=edge_color, width=edge_width),
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
            arrowcolor=edge_color,
            standoff=18,
        )

        # Edge label at midpoint (skip for EVIDENCED_BY to reduce clutter)
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

    # Draw nodes
    for name, info in positions.items():
        node_type = info["type"]
        color = TYPE_COLORS.get(node_type, DEFAULT_COLOR)
        size = _NODE_SIZES.get(node_type, 34)

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
                    hovertext=[f"{name} ({TYPE_LABELS.get(node_type, node_type)})"],
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
                    hovertext=[
                        f"{name} ({TYPE_LABELS.get(node_type, node_type)})"
                    ],
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

    # Legend
    legend_items = set()
    for edge in graph_path:
        for key in ("from_type", "to_type"):
            t = edge.get(key, "")
            if t:
                legend_items.add(t)

    legend_html = ""
    for t in _LAYER_ORDER:
        if t not in legend_items:
            continue
        c = TYPE_COLORS.get(t, DEFAULT_COLOR)
        label = TYPE_LABELS.get(t, t)
        legend_html += (
            f'<span style="display:inline-flex;align-items:center;margin-right:20px;margin-bottom:6px">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{c};'
            f'display:inline-block;margin-right:8px"></span>'
            f'<span style="font-size:16px;color:#B0BEC5">{label}</span></span>'
        )

    if legend_html:
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;padding:12px 0">{legend_html}</div>',
            unsafe_allow_html=True,
        )
