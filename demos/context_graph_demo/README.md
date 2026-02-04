# Context Graph Demo: Cabo Pulmo Decision Trace

This demo demonstrates how MARIS bridge axioms create **auditable decision traces** from ecological data to financial outputs using Semantica's provenance tracking.

## Quick Start

```bash
# From project root
cd demos/context_graph_demo
../../.venv/bin/jupyter notebook cabo_pulmo_context_graph.ipynb
```

Or run in VS Code with the Jupyter extension.

## What This Demo Shows

1. **The Problem**: Cabo Pulmo achieved 463% biomass recovery—exceptional, but can we explain it in a way that's auditable for finance?

2. **The Solution**: Context graphs that trace every number back to its source DOI

3. **The Pipeline**:
   ```
   L1: Ecological Observation (463% biomass, DOI: 10.1371/journal.pone.0023601)
         │
         ▼
   L2: Bridge Axiom BA-002 (NEOLI → Biomass, DOI: 10.1002/eap.3027)
         │
         ▼
   L2: Bridge Axiom BA-001 (Biomass → Tourism WTP, DOI: 10.1038/s41598-024-83664-1)
         │
         ▼
   L3: Financial Output ($29.27M annual ESV)
   ```

## Files

| File | Description |
|------|-------------|
| `cabo_pulmo_context_graph.ipynb` | Main demo notebook |
| `cabo_pulmo_decision_trace.json` | Exported decision trace (generated on run) |
| `README.md` | This file |

## Requirements

- Python 3.11+
- Semantica >= 0.2.6 (installed in project .venv)
- Jupyter (optional, for interactive use)

## Key Concepts

### Bridge Axioms
Peer-reviewed translation rules with verified coefficients and DOI citations:
- **BA-001**: Biomass → Tourism WTP (up to 84% increase)
- **BA-002**: NEOLI criteria → Biomass multiplier (6.7×)

### Context Graphs
Decision traces that make AI outputs auditable:
- Every number has a source
- Every transformation has a rule
- Every rule has a citation

### Financial Applications
- Blue Bond KPI reporting
- TNFD marine dependency disclosure
- MPA effectiveness assessment
- Conservation ROI calculation

## Learn More

- [MARIS Project](../../README.md)
- [Semantica Framework](https://github.com/Hawksight-AI/semantica)
- [Bridge Axiom Schema](../../schemas/bridge_axiom_templates.json)
