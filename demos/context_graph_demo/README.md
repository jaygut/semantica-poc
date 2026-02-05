# Context Graph Demo: Cabo Pulmo Decision Trace

This demo demonstrates how MARIS bridge axioms create **auditable decision traces** from ecological data to financial outputs using Semantica's provenance tracking.

## Notebooks

### 1. Basic Demo: `cabo_pulmo_context_graph.ipynb`
Introduction to context graphs and bridge axiom application.

### 2. Investment-Grade Demo: `cabo_pulmo_investment_grade.ipynb` ⭐ NEW
**Presentation-ready analysis for blue finance professionals.** Addresses critical methodological issues:

| Issue | Resolution |
|-------|------------|
| 463% claim contested | 95% CI [3.8×, 5.5×] with caveats |
| WTP hypothetical bias | NOAA ÷2 adjustment |
| No framework alignment | IFC Blue Finance v1.0, TNFD LEAP |
| No risk quantification | BA-011/BA-012 + Monte Carlo |
| Single case study | 3 comparison sites (NEOLI 1-5) |
| No confidence propagation | Multiplicative CI chain |

**7 Professional Visualizations** (matplotlib + seaborn):
1. Monte Carlo ESV Distribution — KDE density with percentile markers
2. WTP Adjustment Comparison — Horizontal bar with NOAA recommendation
3. Ecosystem Services Breakdown — Raw vs adjusted with composition
4. Confidence Propagation Waterfall — Uncertainty compounding visualization
5. NEOLI vs Outcome Scatter — Bubble plot with investment threshold
6. Risk Scenarios Dashboard — 3-panel climate/degradation/protection
7. SDG 14 Funding Gap — Log-scale market opportunity chart

**Target audiences:** Blue bond underwriters, TNFD working groups, marine ecologists, conservation investors

## Quick Start

```bash
# From project root
cd demos/context_graph_demo
../../.venv/bin/jupyter notebook cabo_pulmo_investment_grade.ipynb
```

Or run in VS Code with the Jupyter extension.

## What These Demos Show

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
   L3: Financial Output ($14.6M NOAA-adjusted ESV)
   ```

## Files

| File | Description |
|------|-------------|
| `cabo_pulmo_context_graph.ipynb` | Basic demo notebook |
| `cabo_pulmo_investment_grade.ipynb` | Investment-grade analysis (recommended) |
| `cabo_pulmo_decision_trace.json` | Exported decision trace (generated on run) |
| `cabo_pulmo_investment_grade_bundle.json` | Full investment bundle (generated on run) |
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
