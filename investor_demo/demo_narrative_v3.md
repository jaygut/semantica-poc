# MARIS v3 - Investor Demo Narrative (12 Minutes)

## Subtitle: "GraphRAG Infrastructure for Blue Natural Capital"

## Pre-Demo Setup

- Open Streamlit dashboard at localhost:8501
- Verify green "LIVE" indicator in sidebar (or amber "STATIC" for fallback)
- Browser at 100% zoom, 1920x1080
- Have a second browser tab ready for DOI links (optional, for live provenance clicks)

---

## 0:00 - 1:30 | The Hook: Why This Is Not Another AI Wrapper

> "There are hundreds of AI-powered ESG tools on the market. Every one of them has the same problem: you get a number, but you can't audit it. The model made it up - or summarized something that was already wrong. 94% of nature-based carbon credits have been flagged as potentially fraudulent. The ocean has a $165 billion trust problem. And LLMs cannot solve it. But a knowledge graph can."

**Action:** Show dashboard masthead with MARIS | SEMANTICA branding. Pause to let the $165B number land.

> "What I'm about to show you isn't a chatbot that's been trained on climate reports. It's a structured knowledge graph - 893 nodes, 132 relationships, every single one traced to a peer-reviewed DOI. The AI doesn't generate answers. It reads from the graph. Let me show you exactly how."

---

## 1:30 - 3:30 | The Pipeline: How GraphRAG Actually Works

> "When you ask MARIS a question, here's what happens under the hood - and this is the key differentiator."

**Action:** Point to the Ask MARIS input box. Type slowly: **"What is Cabo Pulmo worth?"**

> "Step one: your question hits a classifier. Not an LLM - a rule engine. Pattern matching first, LLM fallback only if needed. This question triggers the 'site valuation' category."

> "Step two: that category maps to a specific Cypher query template. Not a free-text prompt - a parameterized database query. Think SQL for graph databases. The template says: find this MPA, follow the GENERATES edges to its ecosystem services, then follow TRANSLATES back through the bridge axioms, then follow EVIDENCED_BY to the source papers."

> "Step three: Neo4j executes the query and returns structured rows. Dollar amounts, confidence intervals, DOIs, evidence tiers. Raw data."

> "Step four - and only now - the LLM sees the data. But it sees ONLY the graph results. It's constrained by a system prompt that says: do not invent numbers, do not cite papers not in the context, report exactly what the graph returned. Then a validator cross-checks every dollar figure and every DOI in the response against the original graph data."

> "This is GraphRAG. The graph does the thinking. The LLM does the writing. And the validator makes sure they agree."

**Action:** Point to the response as it appears - confidence score, axiom tags, DOI citations.

---

## 3:30 - 5:00 | Act 1 - Depth: Cabo Pulmo (Coral Reef, Tourism-Dominant)

> "Let me show you what this produces. Cabo Pulmo National Park - the world's most successful marine protected area."

**Action:** Scroll through KPI cards: ESV $29.27M, Biomass 4.63x recovery, NEOLI 4/5, AAA rating.

> "$29.27 million per year. Four ecosystem services, individually valued. Tourism alone is $25 million - and that's market-price data from Marcos-Castillo 2024, not a model estimate."

> "But look at what else the system gives you."

**Action:** Point to bridge axiom tags on the response - BA-001, BA-002.

> "BA-001 is the axiom that converts fish biomass measurements into tourism willingness-to-pay. The coefficient comes from peer-reviewed dive tourism studies. BA-002 converts no-take protection status into expected biomass recovery - 4.63x over 10 years, confidence interval 3.8 to 5.5. Every translation rule is published, DOI-backed, and falsifiable."

---

## 5:00 - 6:30 | The Trust Moment: Evidence Drill-Down

> "Now let me ask the hardest question an investor can ask."

**Action:** Click: **"Why should I trust the ESV number?"**

> "Watch what happens. The system doesn't say 'trust me' - it shows you the entire reasoning chain."

**Action:** Expand the evidence section. Point to the graph traversal path: MPA -> GENERATES -> Services -> TRANSLATES -> Axioms -> EVIDENCED_BY -> Documents.

> "You can trace any number back to the original paper. Click any DOI link - it takes you to the published study on the journal's website. This is four hops from a dollar figure to a peer-reviewed source. The graph stores every hop."

> "This is what verifiable natural capital intelligence looks like. Not a summary. A provenance chain."

---

## 6:30 - 8:00 | Act 2 - Breadth: Shark Bay (Seagrass, Carbon-Dominant)

> "Cabo Pulmo demonstrates depth. Now let me show you breadth. Same infrastructure, completely different investment thesis."

**Action:** Ask MARIS: **"What is Shark Bay worth?"**

> "Shark Bay, Western Australia. The world's largest seagrass meadow - 4,800 square kilometers. UNESCO World Heritage since 1991."

> "Look at the service breakdown. Where Cabo Pulmo was 85% tourism, Shark Bay is 56% carbon sequestration - $12.1 million per year in blue carbon credit potential. The seagrass sequesters 0.84 tonnes of CO2 per hectare per year through sediment burial - Gomis et al. 2025, Nature Communications."

**Action:** Point to the carbon-dominant ESV profile. Note the different bridge axioms: BA-013, BA-014.

> "Different axioms activated. BA-013 converts seagrass extent to carbon sequestration rate - from Gomis 2025, published in Nature Communications. BA-014 converts sequestration to voluntary carbon credit value at $15-50 per tonne."

> "Same graph infrastructure. Same provenance standards. Completely different financial product - this one feeds into Verra VCS carbon credits, not dive tourism."

---

## 8:00 - 9:30 | The Risk Story: What the 2011 Heatwave Proves

> "But here's what separates this from optimistic carbon accounting."

**Action:** Ask MARIS: **"What happens if seagrass is lost at Shark Bay?"**

> "In 2011, a marine heatwave hit Shark Bay. 36% of the seagrass died. The system knows this - it's in the graph as a documented climate event. And it models the financial consequence: 2 to 9 teragrams of stored CO2 released back into the atmosphere."

> "BA-015 - the risk axiom - converts seagrass loss to carbon emission. 112 to 476 tonnes of CO2 per hectare released. That's Arias-Ortiz et al. 2018, published in Nature Climate Change."

**Action:** Point to the confidence interval and the risk assessment section.

> "This is why permanence is the hardest problem in blue carbon markets. The system doesn't hide this - it quantifies it. And BA-016 shows that MPA protection with NEOLI 4+ provides a 25-100 year permanence buffer that reduces reversal risk."

> "Every carbon credit buyer asks: 'What's your permanence story?' We answer with a peer-reviewed risk model, not a promise."

---

## 9:30 - 10:30 | The Infrastructure Argument

> "Let me zoom out. You've now seen two sites through the same system."

**Action:** Show comparison table: Cabo Pulmo vs. Shark Bay vs. GBR vs. Papahanaumokuakea.

> "Cabo Pulmo: coral reef, tourism-dominant, $29.27 million, AAA rated. Shark Bay: seagrass, carbon-dominant, $21.5 million, AA rated - lower because the 2011 heatwave proved vulnerability. Great Barrier Reef and Papahanaumokuakea: governance metadata only, ready for full characterization."

> "The thesis is simple: this is infrastructure, not analysis. The same 16 bridge axioms, the same provenance graph, the same validation pipeline produces different investment products for different sites. Add a new site, the system automatically generates its financial profile."

> "620 organizations representing $20 trillion in AUM have committed to TNFD disclosure. They need exactly this kind of verified, auditable data. And they need it for hundreds of sites."

---

## 10:30 - 11:30 | The Differentiator

> "What you've seen today is fundamentally different from three things."

> "It's not a chatbot. The intelligence comes from the knowledge graph, not from an LLM. The AI is constrained to report what the graph contains - it cannot hallucinate a number because the validator catches it."

> "It's not a database. The bridge axiom layer translates raw ecological measurements into financial metrics using published, DOI-backed coefficients. 16 axioms, each backed by 2-3 peer-reviewed studies."

> "It's not a model. There are no black-box projections. Every number traces from a dollar figure through a translation rule to an original study in 4 hops or less. The entire chain is transparent and falsifiable."

---

## 11:30 - 12:00 | The Ask

> "We're building the evidence layer for blue natural capital finance. The ocean generates $2.5 trillion in value annually. The market for verified, auditable data on that value is emerging right now - TNFD, blue bonds, carbon credits."

> "Our edge is simple: every number traces to a DOI. Every translation rule is published. The system shows its reasoning, not just its conclusions."

> "In a market where trust is the scarcest resource, verifiability is the only competitive advantage."

---

## Quick Reference: Scripted Queries

| Query | What It Demonstrates | Key Axioms |
|-------|---------------------|------------|
| "What is Cabo Pulmo worth?" | Full ESV with confidence intervals | BA-001, BA-002 |
| "Why should I trust the ESV number?" | Provenance chain drill-down | All applicable |
| "What is Shark Bay worth?" | Carbon-dominant investment thesis | BA-013, BA-014 |
| "What happens if seagrass is lost at Shark Bay?" | Risk quantification with 2011 heatwave data | BA-015, BA-016 |
| "Compare Cabo Pulmo and Shark Bay" | Infrastructure argument - same system, different thesis | All |
| "What financial instruments apply to blue carbon?" | Market positioning (Verra VCS, blue bonds) | BA-014, BA-016 |

## Failure Recovery

| If this happens... | Do this... |
|---|---|
| Chat response slow (>5s) | "The system is querying the live graph..." - response will appear |
| Chat not responding | Switch to precomputed: click another quick query |
| Graph viz doesn't render | "Let me show you the evidence table instead" - expand evidence section |
| Neo4j down | Dashboard still works on static bundle. Skip live chat, use provenance table |
| Shark Bay query fails | Fall back to Cabo Pulmo queries. Say: "The second site is in the pipeline" |
| Tough question from audience | "Great question. Let me ask MARIS directly." Type it in the chat. If low confidence, say "The system is transparent about what it doesn't know - that's the point." |
| "Where does the carbon price come from?" | "$15-50 range from Verra VCS voluntary market data. We use the mid-price with uncertainty bounds, not a point estimate." |
| "Is this investment advice?" | "No. MARIS provides decision-support infrastructure with full provenance. It does not make buy/sell/hold recommendations." |

## Key Numbers to Have Ready

| Metric | Value | Source |
|--------|-------|--------|
| Cabo Pulmo total ESV | $29.27M/yr | Market-price aggregation |
| Cabo Pulmo tourism | $25.0M | Marcos-Castillo et al. 2024 |
| Cabo Pulmo biomass recovery | 4.63x (CI: 3.8-5.5) | Aburto-Oropeza et al. 2011 |
| Shark Bay total ESV | ~$21.5M/yr | Market-price + carbon credit |
| Shark Bay carbon value | ~$12.1M/yr | 480K ha x 0.84 tCO2/ha/yr x $30 |
| Shark Bay seagrass extent | 4,800 km2 | UNESCO/Strydom 2023 |
| Carbon sequestration rate | 0.84 tCO2/ha/yr | Gomis et al. 2025 |
| 2011 heatwave seagrass loss | 36% | Arias-Ortiz et al. 2018 |
| CO2 emission from loss | 2-9 Tg CO2 | Arias-Ortiz et al. 2018 |
| Carbon credit price range | $15-50/tCO2 | Verra VCS voluntary market |
| Bridge axioms in system | 16 (12 original + 4 carbon) | Internal |
| TNFD committed AUM | $20T+ | TNFD 2024 |
| Knowledge graph | 893 nodes, 132 edges | Neo4j |
| Document library | 195 papers, 92% peer-reviewed | Registry |
