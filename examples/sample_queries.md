# Sample GraphRAG Queries for Semantica × MARIS POC

## Overview

These queries demonstrate the multi-hop reasoning capabilities that the knowledge graph should support. Each query involves traversing multiple entity types and relationships to produce an answer with full provenance.

---

## Query Category 1: Impact Assessment Queries

### Query 1.1: MPA Establishment Impact
```
QUERY: "If we establish a no-take marine reserve in a degraded coral reef,
        what ecosystem services will improve and by how much?"

REASONING PATH:
1. Match: degraded_coral_reef → Habitat entity
2. Lookup: BA-002 (no-take MPA biomass multiplier)
3. Traverse: NEOLI criteria → expected recovery trajectory
4. Traverse: Habitat → PROVIDES_SERVICE → EcosystemServices
5. Apply: BA-001 (biomass-tourism elasticity)
6. Apply: BA-004 (reef flood protection)
7. Apply: BA-012 (reef fisheries productivity)
8. Aggregate: service values with confidence intervals

EXPECTED OUTPUT:
{
  "answer": {
    "biomass_recovery": {
      "expected_increase_percent": 670,
      "confidence_interval": [450, 890],
      "timeline_years": 10,
      "source": "Hopf et al. 2024"
    },
    "ecosystem_services": [
      {
        "service": "Tourism revenue",
        "expected_change_percent": "+25-40%",
        "mechanism": "Biomass-tourism elasticity (0.346)",
        "source": "Wielgus et al. 2010"
      },
      {
        "service": "Coastal protection",
        "expected_change": "Reef structural recovery improves wave attenuation",
        "global_value_reference": "$272B annually from coral reefs",
        "source": "Beck et al. 2018"
      },
      {
        "service": "Fisheries productivity",
        "expected_change": "+35% with healthy reef structure",
        "source": "Rogers et al. 2018"
      }
    ],
    "confidence": "HIGH",
    "evidence_tier": "T1 (multiple peer-reviewed sources)"
  },
  "provenance": [
    {"doi": "10.1002/eap.3027", "claim": "670% biomass ratio"},
    {"doi": "10.1016/j.ecolecon.2010.01.008", "claim": "Tourism elasticity 0.346"},
    {"doi": "10.1038/s41467-018-04568-z", "claim": "Flood protection values"}
  ]
}
```

### Query 1.2: Species Loss Impact
```
QUERY: "What happens to kelp forest ecosystem services if sea otters
        are removed from the system?"

REASONING PATH:
1. Match: sea_otter (Enhydra lutris) → Species entity
2. Lookup: CONTROLS_VIA_CASCADE relationship to kelp_forest
3. Apply: BA-003 (sea otter-kelp carbon cascade)
4. Traverse: kelp_forest → PROVIDES_SERVICE → EcosystemServices
5. Calculate: service value changes

EXPECTED OUTPUT:
{
  "answer": {
    "trophic_cascade_effect": {
      "step_1": "Otter removal → Urchin populations increase 10-100x",
      "step_2": "Urchin overgrazing → Kelp biomass decreases 12x",
      "step_3": "Kelp loss → Service provision collapses",
      "source": "Wilmers et al. 2012, Estes et al. 2021"
    },
    "service_impacts": [
      {
        "service": "Carbon sequestration",
        "change": "-92% (NPP drops from 313-900 to 25-70 g C/m²/yr)",
        "value_loss_usd": "$205-408 million",
        "source": "Wilmers et al. 2012"
      },
      {
        "service": "Fisheries habitat",
        "change": "Loss of nursery and foraging habitat for commercial species",
        "affected_species": ["California spiny lobster", "Sheephead", "Rockfish"],
        "source": "Eger et al. 2023"
      },
      {
        "service": "Coastal protection",
        "change": "Reduced wave attenuation without kelp canopy",
        "source": "Literature inference"
      }
    ],
    "confidence": "HIGH",
    "cascade_documented": true
  }
}
```

---

## Query Category 2: Financial Structuring Queries

### Query 2.1: Blue Bond KPI Design
```
QUERY: "What ecological KPIs should a $50M blue bond for mangrove
        restoration in Indonesia use?"

REASONING PATH:
1. Match: mangrove_restoration → Project type
2. Match: Indonesia → Geographic context
3. Lookup: Available metrics from literature
4. Apply: BA-007 (mangrove carbon stock) for carbon KPIs
5. Apply: BA-006 (mangrove fisheries) for livelihood KPIs
6. Apply: BA-005 (mangrove flood protection) for protection KPIs
7. Reference: TNFD/SBTN framework requirements
8. Compile: KPI recommendation with baselines and targets

EXPECTED OUTPUT:
{
  "answer": {
    "recommended_kpis": [
      {
        "kpi": "Mangrove extent (hectares)",
        "baseline_method": "Global Mangrove Watch v3 (Bunting et al. 2022)",
        "measurement_frequency": "Annual via satellite",
        "target_guidance": "+20% over project lifetime",
        "verification": "Remote sensing + ground truthing"
      },
      {
        "kpi": "Carbon stock (Mg C/ha)",
        "baseline_reference": "1,061 Mg C/ha for undisturbed (Murdiyarso 2023)",
        "measurement_method": "Sediment cores + allometric equations",
        "target_guidance": "Approach reference condition over 15 years",
        "verification": "Third-party carbon auditor"
      },
      {
        "kpi": "Juvenile fish density (ind/m²)",
        "baseline_method": "Field surveys at project sites",
        "target_guidance": "Match reference mangrove sites",
        "verification": "Standardized monitoring protocol",
        "source": "Carrasquilla-Henao et al. 2025"
      },
      {
        "kpi": "Community livelihood indicators",
        "metrics": ["Fishing income", "Aquaculture yield", "Tourism employment"],
        "baseline": "Pre-project household surveys",
        "target": "10% income increase for adjacent communities"
      }
    ],
    "verification_framework": "Verra VCS + CCB Standard",
    "expected_bcr": "6.35-15.0 (Zeng et al. 2025)",
    "permanence_risk_note": "85% of SE Asian mangroves face permanence risks (Lovelock 2025)"
  },
  "provenance": [
    {"doi": "10.3390/rs14153657", "claim": "Global Mangrove Watch methodology"},
    {"doi": "10.1186/s13021-023-00233-1", "claim": "Carbon stock reference values"},
    {"doi": "10.1038/s41467-025-56587-2", "claim": "BCR estimates"}
  ]
}
```

### Query 2.2: Carbon Credit Potential
```
QUERY: "How much carbon credit revenue could a 1,000 ha seagrass
        restoration project generate over 10 years?"

REASONING PATH:
1. Match: seagrass_restoration → Project type
2. Match: 1000_ha → Area parameter
3. Apply: BA-008 (seagrass carbon credit value)
4. Lookup: Net sequestration rate (Oreska et al. 2020)
5. Calculate: Total carbon credits
6. Apply: Carbon price range
7. Account: GHG emissions from restoration

EXPECTED OUTPUT:
{
  "answer": {
    "project_parameters": {
      "area_ha": 1000,
      "project_duration_years": 10,
      "ecosystem_type": "seagrass_meadow"
    },
    "carbon_calculations": {
      "gross_sequestration_t_co2_10yr": 9600,
      "ghg_emissions_t_co2e_10yr": 950,
      "net_sequestration_t_co2e_10yr": 8650,
      "net_rate_t_co2e_ha_yr": 0.42,
      "source": "Oreska et al. 2020"
    },
    "revenue_projections": {
      "low_scenario": {
        "carbon_price_usd": 20,
        "revenue_10yr_usd": 173000
      },
      "medium_scenario": {
        "carbon_price_usd": 50,
        "revenue_10yr_usd": 432500
      },
      "high_scenario": {
        "carbon_price_usd": 150,
        "revenue_10yr_usd": 1297500
      }
    },
    "literature_comparison": {
      "range_per_ha": "$198-$15,337 depending on project type",
      "source": "Duarte et al. 2025"
    },
    "caveats": [
      "CH4 and N2O emissions reduce net offset",
      "Success rate varies by region (~88% in Florida)",
      "Permanence monitoring required"
    ]
  }
}
```

---

## Query Category 3: Site Comparison Queries

### Query 3.1: Site Rating Prediction
```
QUERY: "Based on its characteristics, what asset quality rating would
        Site X receive and why?"

INPUT PARAMETERS:
{
  "site_name": "Proposed Baja California MPA",
  "habitat_type": "rocky_reef",
  "area_km2": 45,
  "protection_level": "no_take_proposed",
  "enforcement_capacity": "moderate",
  "years_protected": 0,
  "connectivity": "high",
  "climate_vulnerability": "moderate"
}

REASONING PATH:
1. Apply: NEOLI criteria assessment
2. Compare: To reference sites (Cabo Pulmo = AAA)
3. Lookup: Recovery trajectories for similar sites
4. Assess: Risk factors
5. Calculate: Composite rating

EXPECTED OUTPUT:
{
  "answer": {
    "predicted_rating": "BBB",
    "confidence": "MEDIUM",
    "rationale": {
      "strengths": [
        "Proposed no-take status (+2 NEOLI)",
        "High connectivity to source populations",
        "Suitable habitat type"
      ],
      "weaknesses": [
        "Not yet established (0 years protected)",
        "Moderate enforcement capacity",
        "Below 100 km² threshold"
      ],
      "projected_neoli_score": 2,
      "comparison_to_reference": "Cabo Pulmo achieved AAA with NEOLI=4 after 10+ years"
    },
    "upgrade_pathway": {
      "to_A_rating": [
        "Strengthen enforcement to meet 'enforced' criterion",
        "Maintain protection for 10+ years",
        "Monitor and document recovery"
      ],
      "projected_timeline_to_A": "8-12 years with strong governance"
    },
    "risk_factors": {
      "climate": "Marine heatwave exposure (reference: Rogers-Bennett 2019)",
      "governance": "Enforcement sustainability uncertain",
      "development": "Coastal development pressure moderate"
    }
  }
}
```

### Query 3.2: Portfolio Optimization
```
QUERY: "Given a $100M conservation investment budget, which combination
        of habitats provides the best return on ecosystem services?"

REASONING PATH:
1. Lookup: Value per hectare by habitat type
2. Lookup: Cost per hectare for protection/restoration
3. Calculate: BCR by habitat
4. Optimize: Portfolio allocation
5. Consider: Risk diversification

EXPECTED OUTPUT:
{
  "answer": {
    "recommended_allocation": {
      "mangrove_restoration": {
        "allocation_usd": 35000000,
        "expected_area_ha": 8750,
        "bcr": 10.5,
        "primary_services": ["Coastal protection", "Carbon", "Fisheries"],
        "source": "Zeng et al. 2025"
      },
      "coral_reef_protection": {
        "allocation_usd": 30000000,
        "expected_area_ha": 150,
        "bcr": 6.2,
        "primary_services": ["Coastal protection", "Tourism", "Fisheries"],
        "source": "Beck et al. 2018"
      },
      "seagrass_restoration": {
        "allocation_usd": 20000000,
        "expected_area_ha": 4000,
        "bcr": 4.8,
        "primary_services": ["Carbon", "Nursery habitat"],
        "source": "Duarte et al. 2025"
      },
      "kelp_restoration": {
        "allocation_usd": 15000000,
        "expected_area_ha": 300,
        "bcr": 7.1,
        "primary_services": ["Fisheries", "Carbon", "Coastal protection"],
        "source": "Eger et al. 2023"
      }
    },
    "portfolio_metrics": {
      "weighted_avg_bcr": 7.8,
      "total_carbon_sequestered_t_yr": 45000,
      "total_people_protected": 125000,
      "geographic_diversification": "recommended across 3+ regions"
    },
    "risk_considerations": [
      "Mangrove permanence risks in SE Asia (Lovelock 2025)",
      "Coral reef climate vulnerability (bleaching events)",
      "Kelp forest marine heatwave sensitivity"
    ]
  }
}
```

---

## Query Category 4: Mechanistic Queries

### Query 4.1: Trophic Cascade Mechanism
```
QUERY: "Explain the mechanism by which sheephead protect kelp forests
        in California."

REASONING PATH:
1. Match: California sheephead (Semicossyphus pulcher)
2. Traverse: PREYS_ON relationships
3. Follow: Cascade pathway to kelp
4. Retrieve: Quantitative parameters
5. Cite: Primary sources

EXPECTED OUTPUT:
{
  "answer": {
    "species": {
      "predator": "Semicossyphus pulcher (California sheephead)",
      "prey": "Strongylocentrotus purpuratus (Purple sea urchin)",
      "habitat": "Kelp forest (Macrocystis pyrifera)"
    },
    "mechanism": {
      "step_1": {
        "description": "Sheephead prey on sea urchins",
        "quantification": "Removal of sheephead → 26%/year urchin increase",
        "source": "Cowen 1983"
      },
      "step_2": {
        "description": "Urchin density affects grazing pressure on kelp",
        "quantification": "High sheephead density (200-500/ha) → no exposed urchins",
        "source": "Cowen 1983"
      },
      "step_3": {
        "description": "Reduced urchin grazing allows kelp persistence",
        "outcome": "Kelp forests maintained vs. urchin barrens",
        "source": "Caselle & Hamilton 2015"
      }
    },
    "size_dependency": {
      "finding": "Larger sheephead eat bigger urchins and more of them",
      "implication": "Fishing pressure removes large individuals, weakening cascade",
      "source": "Caselle & Hamilton 2015"
    },
    "management_implication": "MPAs that protect sheephead from fishing help maintain kelp forest resilience",
    "additional_predators": [
      "California spiny lobster (Panulirus interruptus) - Eurich et al. 2014",
      "Sunflower sea star (Pycnopodia helianthoides) - Burt et al. 2023"
    ]
  }
}
```

---

## Query Category 5: Validation Queries

### Query 5.1: Reference Site Validation
```
QUERY: "Does Cabo Pulmo's observed tourism revenue match the prediction
        from the biomass-tourism elasticity model?"

REASONING PATH:
1. Retrieve: Cabo Pulmo biomass data
2. Apply: BA-001 model prediction
3. Compare: To observed tourism revenue
4. Assess: Model accuracy

EXPECTED OUTPUT:
{
  "answer": {
    "model_application": {
      "axiom": "BA-001 (biomass-tourism elasticity)",
      "elasticity": 0.346,
      "biomass_increase": "463%",
      "predicted_tourism_increase": "160%"
    },
    "observed_values": {
      "baseline_tourism_usd": "~$5 million (estimated 1999)",
      "current_tourism_usd": "$25 million (2024)",
      "observed_increase": "400%"
    },
    "model_evaluation": {
      "prediction_vs_observed": "Model underestimates by factor of 2.5",
      "explanation": [
        "Reputation effects not captured in model",
        "Cabo Pulmo became globally famous for recovery",
        "Word-of-mouth and media coverage amplified effect",
        "Premium pricing for 'pristine' dive experience"
      ],
      "model_validity": "Conservative baseline - actual returns often exceed model"
    },
    "implication_for_investors": "Biomass-tourism elasticity provides floor estimate; marketing and reputation can significantly amplify returns"
  }
}
```

---

## Implementation Notes

### For Semantica Team

1. **Index Structure**: Queries traverse entity types in this order:
   - Species/Habitat → EcosystemService → Financial metric

2. **Confidence Propagation**: When chaining axioms, multiply confidence intervals

3. **Provenance Display**: Every numeric claim should link to source DOI

4. **Disambiguation**: Use external IDs (WoRMS, FishBase) to resolve species names

5. **Uncertainty Handling**: Always return ranges, not point estimates

### Performance Targets

- Single-hop queries: <1 second
- Multi-hop queries (3-4 hops): <5 seconds
- Portfolio optimization queries: <30 seconds
