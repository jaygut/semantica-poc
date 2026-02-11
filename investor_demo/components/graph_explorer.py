"""Interactive graph traversal visualization using Plotly."""

import math

import plotly.graph_objects as go
import streamlit as st

# Node colors by entity type
TYPE_COLORS = {
    "MPA": "#2563EB",
    "Species": "#059669",
    "EcosystemService": "#D97706",
    "BridgeAxiom": "#7C3AED",
    "Document": "#64748B",
    "GovernanceScore": "#059669",
    "EcologicalState": "#10B981",
    "FinancialValue": "#D97706",
    "RiskOutcome": "#EF4444",
    "ResilienceBenefit": "#10B981",
    "Parameter": "#94A3B8",
}

DEFAULT_COLOR = "#5B9BD5"


def _layout_nodes(graph_path: list[dict]) -> dict:
    """Build a layout dict mapping node names to (x, y) positions.

    Arranges nodes in layers from left to right based on traversal order.
    """
    # Collect unique nodes in traversal order
    ordered = []
    seen = set()
    for edge in graph_path:
        for key in ("from_node", "to_node"):
            name = edge.get(key, "")
            if name and name not in seen:
                ordered.append(
                    {"name": name, "type": edge.get(f"{key.split('_')[0]}_type", "")}
                )
                seen.add(name)

    if not ordered:
        return {}

    # Assign x based on order, spread y to avoid overlap
    n = len(ordered)
    positions = {}
    cols = max(1, math.ceil(math.sqrt(n)))

    for i, node in enumerate(ordered):
        col = i % cols
        row = i // cols
        x = col * 1.5
        y = -row * 1.2
        positions[node["name"]] = {
            "x": x,
            "y": y,
            "type": node["type"],
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

    # Draw edges
    for edge in graph_path:
        src = edge.get("from_node", "")
        tgt = edge.get("to_node", "")
        rel = edge.get("relationship", "")

        if src not in positions or tgt not in positions:
            continue

        x0, y0 = positions[src]["x"], positions[src]["y"]
        x1, y1 = positions[tgt]["x"], positions[tgt]["y"]

        # Edge line
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color="#334155", width=1.5),
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
            arrowsize=1.2,
            arrowwidth=1.5,
            arrowcolor="#475569",
            standoff=20,
        )

        # Edge label at midpoint
        if rel:
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=rel,
                showarrow=False,
                font=dict(size=11, color="#94A3B8", family="Inter"),
                bgcolor="rgba(11,17,32,0.92)",
                borderpad=3,
            )

    # Draw nodes
    for name, info in positions.items():
        node_type = info["type"]
        color = TYPE_COLORS.get(node_type, DEFAULT_COLOR)

        # Glow
        fig.add_trace(
            go.Scatter(
                x=[info["x"]],
                y=[info["y"]],
                mode="markers",
                marker=dict(size=48, color=color, opacity=0.12),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Node
        fig.add_trace(
            go.Scatter(
                x=[info["x"]],
                y=[info["y"]],
                mode="markers+text",
                marker=dict(
                    size=36,
                    color=color,
                    line=dict(width=2, color="#0B1120"),
                ),
                text=[name],
                textposition="bottom center",
                textfont=dict(size=12, color="#E2E8F0", family="Inter"),
                hoverinfo="text",
                hovertext=[f"{name} ({node_type})"],
                showlegend=False,
            )
        )

    # Compute axis ranges from positions
    xs = [p["x"] for p in positions.values()]
    ys = [p["y"] for p in positions.values()]
    x_pad = 1.0
    y_pad = 1.0

    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=20, b=20),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min(xs) - x_pad, max(xs) + x_pad],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min(ys) - y_pad, max(ys) + y_pad],
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#CBD5E1"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend
    legend_items = set()
    for edge in graph_path:
        for key in ("from_type", "to_type"):
            t = edge.get(key, "")
            if t:
                legend_items.add(t)

    legend_html = ""
    for t in sorted(legend_items):
        c = TYPE_COLORS.get(t, DEFAULT_COLOR)
        legend_html += (
            f'<span style="display:inline-flex;align-items:center;margin-right:16px;margin-bottom:4px">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{c};'
            f'display:inline-block;margin-right:6px"></span>'
            f'<span style="font-size:13px;color:#94A3B8">{t}</span></span>'
        )

    if legend_html:
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">{legend_html}</div>',
            unsafe_allow_html=True,
        )
