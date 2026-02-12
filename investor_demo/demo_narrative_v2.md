# MARIS v2 - Investor Demo Narrative (10 Minutes)

## Pre-Demo Setup

- Open Streamlit dashboard at localhost:8501
- Verify green "LIVE" indicator in sidebar (or amber "STATIC" is fine for fallback)
- Browser at 100% zoom, 1920x1080

---

## 0:00 - 1:00 | The Hook

> "The ocean generates $2.5 trillion in economic value annually. But here's the problem - 94% of nature-based carbon credits have been flagged as potentially fraudulent, and ESG rating providers can't even agree with each other. The ocean has a $165 billion trust problem."

**Action:** Show dashboard masthead with MARIS | SEMANTICA branding.

---

## 1:00 - 2:30 | The Problem, Then the Solution

> "Every number you see on this dashboard traces to a peer-reviewed DOI. This isn't a model output - it's a knowledge graph built from 195 scientific papers."

**Action:** Scroll through KPI cards (ESV $29.27M, biomass 4.63x, NEOLI 4/5, AAA rating). Point to provenance chain section showing DOI links.

---

## 2:30 - 4:00 | Ask MARIS (Scripted Query)

> "But a dashboard is passive. Let me show you something different. Let me ask the system directly."

**Action:** Scroll to "Ask MARIS" section. Click the quick query button: **"What is this site worth?"**

Watch MARIS generate a real-time, sourced response:
- $29.27M total with confidence interval
- Four service categories with individual DOI citations
- Confidence score and axioms used

> "Every claim in that answer came from the knowledge graph. The system can't invent numbers - it can only report what the peer-reviewed literature supports."

---

## 4:00 - 5:30 | Evidence Drill-Down (The Trust Moment)

> "But don't take the system's word for it. Let me show you the evidence chain."

**Action:** Click **"Show evidence chain"** expander. The graph explorer renders showing the traversal path: MPA -> GENERATES -> Services -> TRANSLATES -> Axioms -> EVIDENCED_BY -> Documents.

> "You can trace any number back to the original paper. Click any DOI link - it takes you to the published study. This is what verifiable natural capital intelligence looks like."

---

## 5:30 - 6:30 | The Trust Test

> "Now let me ask the hardest question an investor can ask."

**Action:** Click: **"Why should I trust the ESV number?"**

Watch MARIS trace the full provenance chain - every bridge axiom, every coefficient, every source paper.

> "This is the difference. Other platforms give you a number. We give you the entire reasoning chain."

---

## 6:30 - 7:30 | Risk Scenario

> "But what about downside risk?"

**Action:** Move the scenario slider to P5 (pessimistic). Then click: **"What if protection fails?"**

Watch risk axioms activate - BA-011 (climate resilience), BA-012 (reef degradation fisheries loss).

> "The system doesn't just value assets - it models degradation scenarios using the same peer-reviewed coefficients."

---

## 7:30 - 8:30 | Comparison & Market Context

> "Cabo Pulmo is our reference site - the gold standard. But the platform is designed to scale."

**Action:** Click **"Compare to other sites"** - see Great Barrier Reef and Papahanaumokuakea comparisons with NEOLI scores.

Then scroll to framework alignment section:
> "620 organizations representing $20 trillion in AUM have committed to TNFD disclosure. They need exactly this kind of verified, auditable data."

---

## 8:30 - 9:30 | The Differentiator

> "What you've seen today isn't another LLM wrapper putting a chat interface on unstructured data. The intelligence comes from the knowledge graph - 16 bridge axioms that translate ecological states to financial values, each backed by multiple peer-reviewed studies."

**Action:** Show bridge axiom cards if time permits.

---

## 9:30 - 10:00 | The Ask

> "We're building the evidence layer for blue finance. Every number traces to a DOI. Every translation rule is published and falsifiable. The system shows its reasoning, not just its conclusions."

> "In a market where trust is the scarcest resource, verifiability is the only competitive advantage."

---

## Failure Recovery

| If this happens... | Do this... |
|---|---|
| Chat response slow (>5s) | "The system is querying the live graph..." - response will appear |
| Chat not responding | Switch to precomputed: click another quick query |
| Graph viz doesn't render | "Let me show you the evidence table instead" - expand evidence section |
| Neo4j down | Dashboard still works on static bundle. Skip live chat, use provenance table |
| Tough question from audience | "Great question. Let me ask MARIS directly." Type it in the chat. If low confidence, say "The system is transparent about what it doesn't know." |
