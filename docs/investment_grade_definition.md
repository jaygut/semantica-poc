# Investment-Grade Definition for Nereus

## Purpose

This document defines what "investment-grade" means in the Nereus platform context. It provides an operational definition grounded in IFC Blue Finance Guidelines, TNFD LEAP framework requirements, and academic ESV standards. This definition replaces informal usage of the term throughout Nereus documentation.

## What "Investment-Grade" Means in Nereus

Nereus defines "investment-grade" as meeting seven quantitative criteria for scientific rigor, provenance transparency, and financial applicability. These criteria are informed by:

- **IFC Blue Finance Guidelines** (2022): Eligible use of proceeds, alignment with SDG 14, external review recommendations
- **TNFD LEAP Framework** (2023): Process-based disclosure with transparent data quality reporting
- **SEEA Ecosystem Accounting** (UN): Consistent monetary valuation methodology
- **Academic best practice**: Benefit transfer precision standards, uncertainty quantification norms

The term is NOT borrowed from credit rating terminology (Moody's/S&P investment-grade = BBB-/Baa3 or above). No credit rating agency has established criteria for rating natural capital-backed instruments based on ESV quality. MARIS uses the term operationally to mean "rigorous enough to inform, though not independently verify, institutional investment decisions."

## Seven Quantitative Criteria

### Criterion 1: ESV Accuracy
**Requirement**: Total ESV estimate within +/-20% of published independent valuations.
**Rationale**: Meta-analytic ESV transfer functions explain 18-44% of variance (Brander et al.); +/-20% represents the upper precision achievable through careful benefit transfer.

### Criterion 2: Peer-Reviewed Evidence Base
**Requirement**: Minimum 3 peer-reviewed sources (evidence tier T1) per bridge axiom.
**Rationale**: IFC recommends external review; TNFD requires documented evidence sources. Three independent studies reduce the risk of single-study bias.

### Criterion 3: Uncertainty Quantification
**Requirement**: Every coefficient must report: value, ci_low, ci_high, distribution type, and source DOI.
**Rationale**: False precision undermines credibility. IPCC, GRADE, and TEEB all require explicit uncertainty reporting. Triangular distribution is the minimum acceptable parameterization.

### Criterion 4: Provenance Chain Completeness
**Requirement**: Every financial metric traces to at least one DOI within 4 hops in the knowledge graph.
**Rationale**: The core Nereus value proposition is auditability. A financial metric without a traceable evidence chain is not investment-grade, regardless of its accuracy.

### Criterion 5: Confidence Interval Width
**Requirement**: 95% CI width must be less than 60% of the point estimate for primary metrics.
**Rationale**: A CI wider than 60% of the estimate indicates the measurement is too uncertain for financial use. This threshold balances the inherent uncertainty of ecological measurements with investor requirements for bounded estimates.

### Criterion 6: Data Freshness
**Requirement**: Primary measurement data must be less than 10 years old. Warning at 5 years.
**Rationale**: Ecosystems change. A 17-year-old biomass measurement (as in the current Cabo Pulmo data) introduces unquantified risk that the ecosystem state has changed. The 5-year warning and 10-year threshold ensure timely updates.

### Criterion 7: Framework Alignment
**Requirement**: Data structure must support at least one of: IFC Blue Finance eligible use of proceeds, TNFD LEAP disclosure phases, or SEEA ecosystem accounting.
**Rationale**: Institutional investors operate within established frameworks. Nereus outputs must integrate with at least one recognized due diligence process.

## Compliance Checklist: Cabo Pulmo National Park

| # | Criterion | Target | Cabo Pulmo Status | Met? |
|---|-----------|--------|-------------------|------|
| 1 | ESV Accuracy | Within +/-20% of published | $29.27M - consistent with available tourism ($25M) + spillover ($3.2M) + carbon ($0.18M) + coastal ($0.89M) estimates | Yes |
| 2 | Peer-Reviewed Evidence | >=3 T1 sources per axiom | BA-001: 2 sources, BA-002: 2 sources. Some axioms have only 1-2. | Partial |
| 3 | Uncertainty Quantification | CI + distribution on all coefficients | Added in v1.2 of bridge_axiom_templates.json. BA-001 through BA-004 research-grounded; BA-005-012 estimated. | Partial |
| 4 | Provenance Chain | DOI within 4 hops | All services trace to DOI-backed axioms and source documents. | Yes |
| 5 | CI Width | <60% of point estimate | Biomass CI [3.8, 5.5] on 4.63x = 37% width. Tourism WTP CI [40%, 84%] on 84% = 52% width. | Yes |
| 6 | Data Freshness | <10 years | Biomass data from 2009 (17 years old). Tourism data from 2024 (current). | No |
| 7 | Framework Alignment | >=1 framework supported | IFC Blue Finance (self-assessed), TNFD LEAP (anticipates alignment), SEEA EA (methodology aligned) | Yes |

**Overall Assessment**: 5 of 7 criteria met. Two gaps:
- Data freshness: Biomass measurement exceeds 10-year threshold (17 years old)
- Evidence base: Some axioms have fewer than 3 peer-reviewed sources

## What Nereus Does NOT Claim

1. **Not a credit rating.** The "AAA" internal rating is a composite ecological-governance-financial score used for relative comparison within the Nereus system. It is not a Moody's, S&P, or Fitch credit rating and should never be presented as one.

2. **Not independently audited.** All assessments are self-assessed by the Nereus system. Framework alignment badges (IFC Blue Finance, TNFD LEAP) indicate self-assessed alignment, not certification by those bodies.

3. **Not a financial recommendation.** Nereus provides decision-support infrastructure. It does not make buy/sell/hold recommendations and is not a substitute for independent due diligence.

4. **Single reference site.** The system is fully characterized for one site (Cabo Pulmo National Park). Comparison sites (GBR, Papahanaumokuakea) have governance metadata only. Generalizability to other sites has not been demonstrated.

5. **POC status.** This is a proof-of-concept system. Production deployment requires: independent technical audit, expanded site coverage, updated biomass data, and formal framework alignment review.

## Recommended Disclosure Language

Instead of:
> "Nereus produces investment-grade financial metrics."

Use:
> "Nereus produces DOI-backed financial metrics that meet 5 of 7 internal quality criteria for institutional decision support. See docs/investment_grade_definition.md for the full methodology and compliance checklist."

Instead of:
> "IFC Blue Finance Eligible"

Use:
> "Self-assessed alignment with IFC Blue Finance Guidelines (2022) eligible use of proceeds criteria."

Instead of:
> "TNFD LEAP Aligned"

Use:
> "Anticipates alignment with TNFD LEAP disclosure framework. Nereus data structure follows LEAP phases but has not undergone independent TNFD review."

## References

- IFC Guidelines for Blue Finance (2022). https://www.icmagroup.org/assets/documents/Sustainable-finance/Learning-resources/IFC-Blue-Finance-Guidance-Document_January-2022-270122.pdf
- TNFD LEAP Approach Guidance (2023). https://tnfd.global/publication/additional-guidance-on-assessment-of-nature-related-issues-the-leap-approach/
- SEEA Ecosystem Accounting Monetary Valuation Technical Report (2022). https://seea.un.org/sites/seea.un.org/files/techreportvaluationv15_final_21072022.pdf
- TEEB Valuation Database Manual (2013). https://www.teebweb.org/wp-content/uploads/2014/03/TEEB-Database-and-Valuation-Manual_2013.pdf
