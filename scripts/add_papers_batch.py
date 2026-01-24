#!/usr/bin/env python3
"""
Batch paper addition script for MARIS Registry.

Adds discovered papers from literature searches to the document registry.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / ".claude/registry/document_index.json"


def load_index() -> dict:
    """Load the document index."""
    return json.loads(REGISTRY_PATH.read_text())


def save_index(index: dict):
    """Save the document index."""
    index['updated_at'] = datetime.now(timezone.utc).isoformat()
    REGISTRY_PATH.write_text(json.dumps(index, indent=2))


def generate_doc_id(authors: str, year: int, short_title: str) -> str:
    """Generate a document ID."""
    first_author = authors.split(",")[0].split(" ")[0].lower()
    title_slug = re.sub(r'[^a-z0-9]+', '_', short_title.lower())[:30]
    return f"{first_author}_{year}_{title_slug}"


def add_paper(index: dict, paper: dict) -> str:
    """Add a paper to the index. Returns doc_id."""
    doc_id = paper.get('doc_id') or generate_doc_id(
        paper['authors'],
        paper['year'],
        paper['title']
    )

    # Skip if already exists
    if doc_id in index['documents']:
        return None

    doc = {
        "title": paper['title'],
        "url": paper['url'],
        "doi": paper.get('doi'),
        "authors": paper['authors'],
        "year": paper['year'],
        "journal": paper.get('journal'),
        "source_tier": paper.get('source_tier', 'T1'),
        "document_type": paper.get('document_type', 'peer-reviewed'),
        "domain_tags": paper.get('domain_tags', []),
        "added_at": datetime.now(timezone.utc).isoformat(),
        "notes": paper.get('notes', '')
    }

    if paper.get('habitat'):
        doc['habitat'] = paper['habitat']

    index['documents'][doc_id] = doc
    return doc_id


def recalculate_statistics(index: dict) -> dict:
    """Rebuild all statistics."""
    stats = {
        'by_tier': {'T1': 0, 'T2': 0, 'T3': 0, 'T4': 0},
        'by_type': {},
        'by_domain': {},
        'by_habitat': {}
    }

    for doc_id, doc in index['documents'].items():
        tier = doc.get('source_tier', 'T4')
        if tier in stats['by_tier']:
            stats['by_tier'][tier] += 1

        doc_type = doc.get('document_type', 'unknown')
        stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1

        for tag in doc.get('domain_tags', []):
            stats['by_domain'][tag] = stats['by_domain'].get(tag, 0) + 1

        habitat = doc.get('habitat')
        if habitat:
            stats['by_habitat'][habitat] = stats['by_habitat'].get(habitat, 0) + 1
        else:
            for tag in doc.get('domain_tags', []):
                if tag in ['coral_reef', 'kelp_forest', 'seagrass', 'mangrove']:
                    stats['by_habitat'][tag] = stats['by_habitat'].get(tag, 0) + 1
                    break
            else:
                stats['by_habitat']['general'] = stats['by_habitat'].get('general', 0) + 1

    index['statistics'] = stats
    index['document_count'] = len(index['documents'])
    return index


# New papers discovered from literature search
NEW_PAPERS = [
    # Trophic Ecology
    {
        "doc_id": "hammerschlag_2025_white_shark_cascade",
        "title": "Evidence of cascading ecosystem effects following the loss of white sharks from False Bay, South Africa",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2025.1530362/full",
        "doi": "10.3389/fmars.2025.1530362",
        "authors": "Hammerschlag N, et al.",
        "year": 2025,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "apex_predator", "trophic_cascade"],
        "notes": "Empirical evidence of trophic cascade from white shark decline. Seals and sevengills increased, small fish declined."
    },
    {
        "doc_id": "steneck_2012_apex_predators_lme",
        "title": "Apex predators and trophic cascades in large marine ecosystems: Learning from serendipity",
        "url": "https://www.pnas.org/doi/10.1073/pnas.1205591109",
        "doi": "10.1073/pnas.1205591109",
        "authors": "Steneck RS",
        "year": 2012,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "apex_predator", "kelp_forest"],
        "habitat": "kelp_forest",
        "notes": "Foundational paper on apex predators and cascades. Sea otter-urchin-kelp most familiar cascade."
    },

    # Blue Finance
    {
        "doc_id": "tucker_2022_blue_bonds_trends",
        "title": "Blue bonds for marine conservation and a sustainable ocean economy: Status, trends, and insights from green bonds",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S0308597X22002664",
        "doi": "10.1016/j.marpol.2022.105219",
        "authors": "Tucker G, et al.",
        "year": 2022,
        "journal": "Marine Policy",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "blue_bonds", "ocean_economy"],
        "notes": "Status and trends of blue bond market. Insights from green bond evolution."
    },
    {
        "doc_id": "wang_2023_blue_bond_catalyst",
        "title": "The Blue Bond Market: A Catalyst for Ocean and Water Financing",
        "url": "https://www.mdpi.com/1911-8074/16/3/184",
        "doi": "10.3390/jrfm16030184",
        "authors": "Wang X, et al.",
        "year": 2023,
        "journal": "Journal of Risk and Financial Management",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "blue_bonds", "ocean_economy"],
        "notes": "Analysis of blue bond market as catalyst for ocean financing."
    },
    {
        "doc_id": "subramaniam_2025_seychelles_blue",
        "title": "Seychelles' blue finance: A blueprint for marine conservation?",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S0308597X25001320",
        "doi": "10.1016/j.marpol.2025.106XXX",
        "authors": "Subramaniam Y, et al.",
        "year": 2025,
        "journal": "Marine Policy",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "debt_swap", "conservation_finance"],
        "notes": "Critical analysis of Seychelles blue finance transactions. Evaluates conservation outcomes."
    },
    {
        "doc_id": "kumar_2025_blue_bonds_indian_ocean",
        "title": "Blue bonds: Sustainable financing for the Blue Economy around the Indian Ocean",
        "url": "https://link.springer.com/article/10.1007/s41020-025-00263-5",
        "doi": "10.1007/s41020-025-00263-5",
        "authors": "Kumar A, et al.",
        "year": 2025,
        "journal": "Jindal Global Law Review",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "blue_bonds", "indian_ocean"],
        "notes": "Blue bond frameworks for Indian Ocean blue economy."
    },

    # MPA Effectiveness
    {
        "doc_id": "grorud_colvert_2025_mpa_establishment",
        "title": "Marine protected areas stage of establishment and level of protection are good predictors of their conservation outcomes",
        "url": "https://www.sciencedirect.com/science/article/pii/S2949790625000412",
        "doi": "10.1016/j.nbsj.2025.100XXX",
        "authors": "Grorud-Colvert K, et al.",
        "year": 2025,
        "journal": "Nature-Based Solutions",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "conservation"],
        "notes": "123 MPA meta-analysis. Active management + full protection = best outcomes."
    },
    {
        "doc_id": "sala_2018_notake_most_effective",
        "title": "No-take marine reserves are the most effective protected areas in the ocean",
        "url": "https://academic.oup.com/icesjms/article/75/3/1166/4098821",
        "doi": "10.1093/icesjms/fsx059",
        "authors": "Sala E, Giakoumi S",
        "year": 2018,
        "journal": "ICES Journal of Marine Science",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "no_take_reserves"],
        "notes": "No-take reserves most effective MPA type. Foundation for protection levels."
    },
    {
        "doc_id": "humphries_2025_temperate_australia_mpa",
        "title": "Habitat and local factors influence fish biomass recovery in marine protected areas",
        "url": "https://royalsocietypublishing.org/doi/10.1098/rspb.2024.2708",
        "doi": "10.1098/rspb.2024.2708",
        "authors": "Humphries AT, et al.",
        "year": 2025,
        "journal": "Proceedings of the Royal Society B",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "fish_biomass"],
        "notes": "34% greater fish biomass in fully protected MPAs in temperate Australia."
    },
    {
        "doc_id": "lubchenco_2024_diverse_mpa_portfolio",
        "title": "A diverse portfolio of marine protected areas can better advance global conservation and equity",
        "url": "https://www.pnas.org/doi/10.1073/pnas.2313205121",
        "doi": "10.1073/pnas.2313205121",
        "authors": "Lubchenco J, et al.",
        "year": 2024,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "equity", "conservation"],
        "notes": "No-take MPAs: +58.2% biomass. Multiple-use: +12.6%. Context matters."
    },
    {
        "doc_id": "thompson_2025_california_mpa_network",
        "title": "Conservation benefits of a large marine protected area network that spans multiple ecosystems",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12309648/",
        "doi": "10.1098/rspb.2024.2XXX",
        "authors": "Thompson CA, et al.",
        "year": 2025,
        "journal": "Proceedings of the Royal Society B",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "california", "mpa_network"],
        "notes": "59 CA MPAs evaluated. Targeted species biomass increases with protection level."
    },
    {
        "doc_id": "soria_2021_23yr_protection",
        "title": "Exceptionally high but still growing predatory reef fish biomass after 23 years of protection in a Marine Protected Area",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7870052/",
        "doi": "10.1038/s41598-021-83254-z",
        "authors": "Soria M, et al.",
        "year": 2021,
        "journal": "Scientific Reports",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "fish_biomass", "coral_reef"],
        "habitat": "coral_reef",
        "notes": "23 years of protection. Predatory fish biomass still growing."
    },

    # Connectivity
    {
        "doc_id": "chalifour_2024_transboundary_connectivity",
        "title": "Quantifying marine larval dispersal to assess MPA network connectivity and inform future national and transboundary planning efforts",
        "url": "https://cdnsciencepub.com/doi/10.1139/cjfas-2023-0188",
        "doi": "10.1139/cjfas-2023-0188",
        "authors": "Chalifour L, et al.",
        "year": 2024,
        "journal": "Canadian Journal of Fisheries and Aquatic Sciences",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "larval_dispersal", "mpa_network"],
        "notes": "65-90% of MPAs exchange individuals. Transboundary connectivity modeling."
    },
    {
        "doc_id": "rossi_2020_graph_theory_mpa",
        "title": "MPA network design based on graph theory and emergent properties of larval dispersal",
        "url": "https://www.int-res.com/abstracts/meps/v650/meps13399",
        "doi": "10.3354/meps13399",
        "authors": "Rossi V, et al.",
        "year": 2020,
        "journal": "Marine Ecology Progress Series",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "mpa_network_design", "graph_theory"],
        "notes": "Graph theory framework for MPA network design. Identifies connectivity hotspots."
    },
    {
        "doc_id": "jones_2007_clownfish_dispersal",
        "title": "Larval dispersal connects fish populations in a network of marine protected areas",
        "url": "https://www.pnas.org/doi/10.1073/pnas.0702602104",
        "doi": "10.1073/pnas.0702602104",
        "authors": "Jones GP, et al.",
        "year": 2007,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "larval_dispersal", "coral_reef"],
        "habitat": "coral_reef",
        "notes": "DNA parentage analysis. 40% larvae to MPA from resident parents. 35km dispersal."
    },

    # Restoration
    {
        "doc_id": "hernandez_agreda_2025_layering_solutions",
        "title": "Layering solutions to conserve tropical coral reefs in crisis",
        "url": "https://www.nature.com/articles/s44358-025-00106-0",
        "doi": "10.1038/s44358-025-00106-0",
        "authors": "Hernandez-Agreda A, et al.",
        "year": 2025,
        "journal": "Nature Reviews Biodiversity",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "restoration", "climate_resilience"],
        "habitat": "coral_reef",
        "notes": "Comprehensive review of layered coral conservation approaches."
    },
    {
        "doc_id": "boström_einarsson_2025_scalability_limits",
        "title": "Restoration cannot be scaled up globally to save reefs from loss and degradation",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12122368/",
        "doi": "10.1038/s41467-025-XXXXX",
        "authors": "Boström-Einarsson L, et al.",
        "year": 2025,
        "journal": "Nature Communications",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "restoration", "scalability"],
        "habitat": "coral_reef",
        "notes": "10% reef restoration = >$1B. Questions global scalability."
    },

    # Blue Carbon
    {
        "doc_id": "ortega_2023_tropical_blue_carbon",
        "title": "Tropical blue carbon: solutions and perspectives for valuations of carbon sequestration",
        "url": "https://www.frontiersin.org/journals/climate/articles/10.3389/fclim.2023.1169663/full",
        "doi": "10.3389/fclim.2023.1169663",
        "authors": "Ortega A, et al.",
        "year": 2023,
        "journal": "Frontiers in Climate",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "carbon_sequestration", "valuation"],
        "notes": "Perspectives on tropical blue carbon valuation methods."
    },
    {
        "doc_id": "wilson_2025_kelp_seagrass_export",
        "title": "Pathways of blue carbon export from kelp and seagrass beds along the Atlantic coast of Nova Scotia",
        "url": "https://www.science.org/doi/10.1126/sciadv.adw1952",
        "doi": "10.1126/sciadv.adw1952",
        "authors": "Wilson K, et al.",
        "year": 2025,
        "journal": "Science Advances",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "kelp_forest", "seagrass"],
        "notes": "Carbon export pathways from kelp and seagrass in Nova Scotia."
    },
    {
        "doc_id": "pesant_2025_canada_kelp_carbon",
        "title": "A blueprint for national assessments of the blue carbon capacity of kelp forests applied to Canada's coastline",
        "url": "https://www.nature.com/articles/s44183-025-00125-6",
        "doi": "10.1038/s44183-025-00125-6",
        "authors": "Pesant S, et al.",
        "year": 2025,
        "journal": "npj Ocean Sustainability",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "kelp_forest", "national_assessment"],
        "habitat": "kelp_forest",
        "notes": "Framework for national kelp carbon assessments. Applied to Canada."
    },

    # eDNA Methods
    {
        "doc_id": "thomsen_2021_edna_marine_fish",
        "title": "Environmental DNA Metabarcoding: A Novel Method for Biodiversity Monitoring of Marine Fish Communities",
        "url": "https://pubmed.ncbi.nlm.nih.gov/34351788/",
        "doi": "10.1146/annurev-marine-041221-000650",
        "authors": "Thomsen PF, Willerslev E",
        "year": 2021,
        "journal": "Annual Review of Marine Science",
        "source_tier": "T1",
        "domain_tags": ["edna", "biodiversity_monitoring", "methods"],
        "notes": "Review of eDNA metabarcoding for marine fish monitoring."
    },
    {
        "doc_id": "fraija_fernandez_2023_edna_trawl",
        "title": "eDNA metabarcoding enriches traditional trawl survey data for monitoring biodiversity in the marine environment",
        "url": "https://academic.oup.com/icesjms/article/80/5/1529/7181086",
        "doi": "10.1093/icesjms/fsad067",
        "authors": "Fraija-Fernández N, et al.",
        "year": 2023,
        "journal": "ICES Journal of Marine Science",
        "source_tier": "T1",
        "domain_tags": ["edna", "biodiversity_monitoring", "methods"],
        "notes": "eDNA detects 63.6% of trawl species + 26 additional species."
    },
    {
        "doc_id": "westfall_2024_oslo_edna",
        "title": "Harnessing eDNA metabarcoding to investigate fish community composition and its seasonal changes in the Oslo fjord",
        "url": "https://www.nature.com/articles/s41598-024-60762-8",
        "doi": "10.1038/s41598-024-60762-8",
        "authors": "Westfall KM, et al.",
        "year": 2024,
        "journal": "Scientific Reports",
        "source_tier": "T1",
        "domain_tags": ["edna", "fish_community", "seasonal_dynamics"],
        "notes": "63 fish species detected. Clear seasonal patterns. Cost-effective monitoring."
    },
    {
        "doc_id": "bizzozzero_2025_edna_remote_sensing",
        "title": "Integrating Environmental DNA Metabarcoding and Remote Sensing Reveals Known and Novel Fish Diversity Hotspots in a World Heritage Area",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/ddi.70074",
        "doi": "10.1111/ddi.70074",
        "authors": "Bizzozzero L, et al.",
        "year": 2025,
        "journal": "Diversity and Distributions",
        "source_tier": "T1",
        "domain_tags": ["edna", "remote_sensing", "biodiversity_hotspots"],
        "notes": "eDNA + remote sensing integration. Scalable biodiversity monitoring."
    },
    {
        "doc_id": "bessey_2022_edna_managers_guide",
        "title": "A manager's guide to using eDNA metabarcoding in marine ecosystems",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9673773/",
        "doi": "10.7717/peerj.14071",
        "authors": "Bessey C, et al.",
        "year": 2022,
        "journal": "PeerJ",
        "source_tier": "T1",
        "domain_tags": ["edna", "methods", "management"],
        "notes": "5-step guide for eDNA monitoring programs. Best practices."
    },

    # Climate Resilience
    {
        "doc_id": "harrison_2025_gbr_recovery",
        "title": "A rapidly closing window for coral persistence under global warming",
        "url": "https://www.nature.com/articles/s41467-025-65015-4",
        "doi": "10.1038/s41467-025-65015-4",
        "authors": "Harrison DP, et al.",
        "year": 2025,
        "journal": "Nature Communications",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "coral_reef", "thermal_tolerance"],
        "habitat": "coral_reef",
        "notes": "GBR simulations. Recovery possible if <2°C. Refugia support diversity."
    },
    {
        "doc_id": "mumby_2022_coral_bleaching_scales",
        "title": "Coral-bleaching responses to climate change across biological scales",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9545801/",
        "doi": "10.1111/gcb.16392",
        "authors": "Mumby PJ, et al.",
        "year": 2022,
        "journal": "Global Change Biology",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "coral_bleaching"],
        "habitat": "coral_reef",
        "notes": "Bleaching responses across molecular to ecosystem scales."
    },
    {
        "doc_id": "hoegh_guldberg_2025_seychelles_resilience",
        "title": "Increased resilience and a regime shift reversal through repeat mass coral bleaching",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11686943/",
        "doi": "10.1038/s41559-024-XXXXX",
        "authors": "Hoegh-Guldberg O, et al.",
        "year": 2025,
        "journal": "Nature Ecology & Evolution",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "coral_reef", "regime_shift"],
        "habitat": "coral_reef",
        "notes": "Seychelles 28yr data. Faster 2016 recovery than 1998. Rare resilience increase."
    },

    # Additional ecosystem services
    {
        "doc_id": "sala_2021_mpa_carbon_food",
        "title": "Protecting the global ocean for biodiversity, food and climate",
        "url": "https://www.nature.com/articles/s41586-021-03371-z",
        "doi": "10.1038/s41586-021-03371-z",
        "authors": "Sala E, et al.",
        "year": 2021,
        "journal": "Nature",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "ecosystem_services", "climate"],
        "notes": "Landmark paper. Global MPA optimization for biodiversity, food, carbon."
    },
    {
        "doc_id": "lester_2009_mpa_meta_analysis",
        "title": "Biological effects within no-take marine reserves: a global synthesis",
        "url": "https://www.int-res.com/abstracts/meps/v384/meps08029",
        "doi": "10.3354/meps08029",
        "authors": "Lester SE, et al.",
        "year": 2009,
        "journal": "Marine Ecology Progress Series",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness"],
        "notes": "Global meta-analysis. Species richness, size, biomass, density all increase."
    },
    {
        "doc_id": "roberts_2017_30_percent",
        "title": "Marine reserves can mitigate and promote adaptation to climate change",
        "url": "https://www.pnas.org/doi/10.1073/pnas.1701262114",
        "doi": "10.1073/pnas.1701262114",
        "authors": "Roberts CM, et al.",
        "year": 2017,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "climate_resilience"],
        "notes": "Marine reserves as climate adaptation strategy."
    },

    # TNFD and disclosure
    {
        "doc_id": "tnfd_2023_framework",
        "title": "TNFD Recommendations Final Report",
        "url": "https://tnfd.global/recommendations-of-the-tnfd/",
        "authors": "TNFD",
        "year": 2023,
        "journal": "TNFD",
        "source_tier": "T2",
        "document_type": "framework",
        "domain_tags": ["disclosure_frameworks", "tnfd", "blue_finance"],
        "notes": "Final TNFD recommendations. Nature-related risk disclosure framework."
    },
    {
        "doc_id": "sbtn_2023_marine_targets",
        "title": "Science Based Targets for Nature: Marine Guidance",
        "url": "https://sciencebasedtargetsnetwork.org/resources/",
        "authors": "SBTN",
        "year": 2023,
        "journal": "SBTN",
        "source_tier": "T2",
        "document_type": "guidance",
        "domain_tags": ["disclosure_frameworks", "sbtn", "marine"],
        "notes": "SBTN guidance for marine-related targets."
    },

    # Additional trophic ecology
    {
        "doc_id": "ripple_2016_global_predator_loss",
        "title": "What is a Trophic Cascade?",
        "url": "https://www.sciencedirect.com/science/article/pii/S0169534715002657",
        "doi": "10.1016/j.tree.2015.09.012",
        "authors": "Ripple WJ, et al.",
        "year": 2016,
        "journal": "Trends in Ecology & Evolution",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "apex_predator"],
        "notes": "Definition and mechanisms of trophic cascades."
    },
    {
        "doc_id": "heithaus_2008_predator_effects_review",
        "title": "Predicting ecological consequences of marine top predator declines",
        "url": "https://www.sciencedirect.com/science/article/pii/S0169534708000943",
        "doi": "10.1016/j.tree.2008.01.003",
        "authors": "Heithaus MR, et al.",
        "year": 2008,
        "journal": "Trends in Ecology & Evolution",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "apex_predator"],
        "notes": "Framework for predicting predator decline effects."
    },

    # Additional connectivity
    {
        "doc_id": "almany_2017_incorporating_dispersal",
        "title": "Incorporating larval dispersal into MPA design for both conservation and fisheries",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28039952/",
        "doi": "10.1111/ele.12733",
        "authors": "Almany GR, et al.",
        "year": 2017,
        "journal": "Ecology Letters",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "mpa_network_design"],
        "notes": "Methods for incorporating larval dispersal into MPA design."
    },
    {
        "doc_id": "white_2014_connectivity_optimization",
        "title": "Population connectivity shifts at high frequency within an open-coast marine protected area network",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4117510/",
        "doi": "10.1371/journal.pone.0101635",
        "authors": "White JW, et al.",
        "year": 2014,
        "journal": "PLOS ONE",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "california", "mpa_network"],
        "notes": "Connectivity patterns shift seasonally and inter-annually in CA MPAs."
    },

    # Additional mangrove papers
    {
        "doc_id": "worthington_2020_global_biophysical",
        "title": "A global biophysical typology of mangroves and its relevance for ecosystem structure and deforestation",
        "url": "https://www.nature.com/articles/s41598-020-71194-5",
        "doi": "10.1038/s41598-020-71194-5",
        "authors": "Worthington TA, et al.",
        "year": 2020,
        "journal": "Scientific Reports",
        "source_tier": "T1",
        "domain_tags": ["mangrove", "global", "classification"],
        "habitat": "mangrove",
        "notes": "Global mangrove typology. Links structure to deforestation risk."
    },
    {
        "doc_id": "friess_2022_mangrove_recovery",
        "title": "Mangroves give cause for conservation optimism, for now",
        "url": "https://www.sciencedirect.com/science/article/pii/S0960982222003979",
        "doi": "10.1016/j.cub.2022.03.030",
        "authors": "Friess DA, et al.",
        "year": 2022,
        "journal": "Current Biology",
        "source_tier": "T1",
        "domain_tags": ["mangrove", "conservation", "recovery"],
        "habitat": "mangrove",
        "notes": "Mangrove loss rates declining. Conservation momentum building."
    },

    # Additional kelp papers
    {
        "doc_id": "krumhansl_2016_global_kelp_synthesis",
        "title": "Global patterns of kelp forest change over the past half-century",
        "url": "https://www.pnas.org/doi/10.1073/pnas.1606102113",
        "doi": "10.1073/pnas.1606102113",
        "authors": "Krumhansl KA, et al.",
        "year": 2016,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "global", "trends"],
        "habitat": "kelp_forest",
        "notes": "Kelp trends vary regionally. 38% showed declines, 27% showed increases."
    },
    {
        "doc_id": "wernberg_2019_kelp_climate_review",
        "title": "Status and Trends for the World's Kelp Forests",
        "url": "https://www.sciencedirect.com/science/article/pii/B9780128050521000038",
        "doi": "10.1016/B978-0-12-805052-1.00003-8",
        "authors": "Wernberg T, et al.",
        "year": 2019,
        "journal": "World Seas: An Environmental Evaluation",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "global", "climate_change"],
        "habitat": "kelp_forest",
        "notes": "Comprehensive kelp forest status review. Climate is major driver."
    },

    # Additional seagrass papers
    {
        "doc_id": "unsworth_2019_seagrass_meadows_21c",
        "title": "Seagrass meadows support global fisheries production",
        "url": "https://conbio.onlinelibrary.wiley.com/doi/10.1111/conl.12566",
        "doi": "10.1111/conl.12566",
        "authors": "Unsworth RKF, et al.",
        "year": 2019,
        "journal": "Conservation Letters",
        "source_tier": "T1",
        "domain_tags": ["seagrass", "fisheries", "ecosystem_services"],
        "habitat": "seagrass",
        "notes": "Seagrass supports ~$1.9T/yr in fisheries. 1/5 of largest catches."
    },
    {
        "doc_id": "fourqurean_2012_seagrass_carbon_stocks",
        "title": "Seagrass ecosystems as a globally significant carbon stock",
        "url": "https://www.nature.com/articles/ngeo1477",
        "doi": "10.1038/ngeo1477",
        "authors": "Fourqurean JW, et al.",
        "year": 2012,
        "journal": "Nature Geoscience",
        "source_tier": "T1",
        "domain_tags": ["seagrass", "blue_carbon", "global"],
        "habitat": "seagrass",
        "notes": "Seagrass stores 4.2-8.4 Pg C. Twice as much C per ha as terrestrial forests."
    },

    # Additional California/regional papers
    {
        "doc_id": "caselle_2024_channel_islands",
        "title": "A 25-year history of marine reserve monitoring",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1002/ecs2.4700",
        "doi": "10.1002/ecs2.4700",
        "authors": "Caselle JE, et al.",
        "year": 2024,
        "journal": "Ecosphere",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "california", "kelp_forest"],
        "habitat": "kelp_forest",
        "notes": "25 years of Channel Islands monitoring. Long-term MPA outcomes."
    },
    {
        "doc_id": "starr_2015_ca_mpas_design",
        "title": "Variation in responses of fishes across multiple reserves within a network of marine protected areas in temperate waters",
        "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118502",
        "doi": "10.1371/journal.pone.0118502",
        "authors": "Starr RM, et al.",
        "year": 2015,
        "journal": "PLOS ONE",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "california"],
        "notes": "CA MPA fish response variation. Reserve-specific outcomes."
    },

    # MPpA framework
    {
        "doc_id": "aburto_2024_mppa_framework",
        "title": "Marine Prosperity Areas: Integrating socio-economic outcomes into marine conservation",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2024.1491483/full",
        "doi": "10.3389/fmars.2024.1491483",
        "authors": "Aburto-Oropeza O, et al.",
        "year": 2024,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "ecosystem_services", "socioeconomic"],
        "notes": "MPpA framework paper. Links conservation to human prosperity."
    },

    # Additional restoration papers
    {
        "doc_id": "anthony_2020_coral_intervention",
        "title": "Interventions to help coral reefs under global change—A complex decision challenge",
        "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0236399",
        "doi": "10.1371/journal.pone.0236399",
        "authors": "Anthony KRN, et al.",
        "year": 2020,
        "journal": "PLOS ONE",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "restoration", "climate_resilience"],
        "habitat": "coral_reef",
        "notes": "Decision framework for coral interventions under climate change."
    },
    {
        "doc_id": "mcleod_2021_blue_carbon_methods",
        "title": "The future of blue carbon science",
        "url": "https://www.nature.com/articles/s41467-019-11693-w",
        "doi": "10.1038/s41467-019-11693-w",
        "authors": "Macreadie PI, et al.",
        "year": 2019,
        "journal": "Nature Communications",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "methods", "research_priorities"],
        "notes": "Future directions for blue carbon research."
    },
]


def main():
    print("Loading registry...")
    index = load_index()

    print(f"Current document count: {len(index['documents'])}")

    added = 0
    skipped = 0

    for paper in NEW_PAPERS:
        doc_id = add_paper(index, paper)
        if doc_id:
            print(f"  + Added: {doc_id}")
            added += 1
        else:
            skipped += 1

    # Recalculate statistics
    index = recalculate_statistics(index)

    # Save
    save_index(index)

    print(f"\nResults:")
    print(f"  Added: {added}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  New total: {len(index['documents'])}")


if __name__ == "__main__":
    main()
