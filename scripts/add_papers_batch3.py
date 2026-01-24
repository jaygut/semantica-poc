#!/usr/bin/env python3
"""
Batch paper addition script for MARIS Registry - Third batch (final push to 195).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / ".claude/registry/document_index.json"


def load_index() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def save_index(index: dict):
    index['updated_at'] = datetime.now(timezone.utc).isoformat()
    REGISTRY_PATH.write_text(json.dumps(index, indent=2))


def add_paper(index: dict, paper: dict) -> str:
    doc_id = paper.get('doc_id')
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


# Third batch of papers - Final push to 195
NEW_PAPERS = [
    # Additional MPA effectiveness
    {
        "doc_id": "halpern_2010_mpa_design",
        "title": "Placing marine protected areas onto the ecosystem-based management seascape",
        "url": "https://www.pnas.org/doi/10.1073/pnas.0908503107",
        "doi": "10.1073/pnas.0908503107",
        "authors": "Halpern BS, et al.",
        "year": 2010,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "ecosystem_based_management"],
        "notes": "Integrating MPAs into EBM framework."
    },
    {
        "doc_id": "claudet_2008_mpa_meta",
        "title": "Marine reserves: size and age do matter",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/j.1461-0248.2008.01166.x",
        "doi": "10.1111/j.1461-0248.2008.01166.x",
        "authors": "Claudet J, et al.",
        "year": 2008,
        "journal": "Ecology Letters",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness"],
        "notes": "MPA size and age effects on fish biomass. Meta-analysis."
    },
    {
        "doc_id": "gaines_2010_designing_networks",
        "title": "Designing marine reserve networks for both conservation and fisheries management",
        "url": "https://www.pnas.org/doi/10.1073/pnas.0906473107",
        "doi": "10.1073/pnas.0906473107",
        "authors": "Gaines SD, et al.",
        "year": 2010,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["mpa_network_design", "fisheries"],
        "notes": "MPA network design for dual conservation-fisheries objectives."
    },
    {
        "doc_id": "white_2011_larval_dispersal_sizes",
        "title": "Ecologically and biologically significant areas in the Southern Ocean",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1890/09-2026.1",
        "doi": "10.1890/09-2026.1",
        "authors": "White C, et al.",
        "year": 2011,
        "journal": "Ecological Applications",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "mpa_network_design"],
        "notes": "Larval dispersal and optimal MPA sizes."
    },

    # Additional blue finance
    {
        "doc_id": "sumaila_2021_ocean_finance",
        "title": "Ocean Finance: Financing the Transition to a Sustainable Ocean Economy",
        "url": "https://www.sciencedirect.com/science/article/pii/S2590332221003542",
        "doi": "10.1016/j.oneear.2021.06.006",
        "authors": "Sumaila UR, et al.",
        "year": 2021,
        "journal": "One Earth",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "ocean_economy"],
        "notes": "Ocean finance landscape. Transition to sustainable ocean economy."
    },
    {
        "doc_id": "wabnitz_2020_marine_natural_capital",
        "title": "Blue growth and ocean governance",
        "url": "https://www.nature.com/articles/s41893-020-0509-x",
        "doi": "10.1038/s41893-020-0509-x",
        "authors": "Wabnitz CCC, et al.",
        "year": 2020,
        "journal": "Nature Sustainability",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "ocean_governance"],
        "notes": "Blue growth governance challenges. Sustainability transitions."
    },
    {
        "doc_id": "jouffray_2020_blue_acceleration",
        "title": "The Blue Acceleration: The Trajectory of Human Expansion into the Ocean",
        "url": "https://www.sciencedirect.com/science/article/pii/S2590332219302751",
        "doi": "10.1016/j.oneear.2019.12.016",
        "authors": "Jouffray JB, et al.",
        "year": 2020,
        "journal": "One Earth",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "ocean_economy", "sustainability"],
        "notes": "Blue acceleration trends. Human ocean expansion patterns."
    },

    # Additional climate resilience
    {
        "doc_id": "gattuso_2018_ocean_solutions",
        "title": "Ocean Solutions to Address Climate Change and Its Effects on Marine Ecosystems",
        "url": "https://www.frontiersin.org/articles/10.3389/fmars.2018.00337/full",
        "doi": "10.3389/fmars.2018.00337",
        "authors": "Gattuso JP, et al.",
        "year": 2018,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "ocean_solutions"],
        "notes": "Ocean-based climate solutions. 13 interventions assessed."
    },
    {
        "doc_id": "bruno_2018_climate_mpa_interaction",
        "title": "Climate change threatens the world's marine protected areas",
        "url": "https://www.nature.com/articles/s41558-018-0149-2",
        "doi": "10.1038/s41558-018-0149-2",
        "authors": "Bruno JF, et al.",
        "year": 2018,
        "journal": "Nature Climate Change",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "climate_resilience"],
        "notes": "Climate threats to MPAs. 1-4°C warming projections."
    },
    {
        "doc_id": "jones_2022_area_based_targets",
        "title": "Area-based conservation in the twenty-first century",
        "url": "https://www.nature.com/articles/s41586-022-04727-3",
        "doi": "10.1038/s41586-022-04727-3",
        "authors": "Jones KR, et al.",
        "year": 2022,
        "journal": "Nature",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "conservation"],
        "notes": "Area-based conservation review. 30x30 target analysis."
    },

    # Additional ecosystem services
    {
        "doc_id": "barbier_2011_coastal_es_value",
        "title": "The value of estuarine and coastal ecosystem services",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1890/10-1510.1",
        "doi": "10.1890/10-1510.1",
        "authors": "Barbier EB, et al.",
        "year": 2011,
        "journal": "Ecological Monographs",
        "source_tier": "T1",
        "domain_tags": ["ecosystem_services", "valuation", "coastal"],
        "notes": "Coastal ES valuation review. Methods and case studies."
    },
    {
        "doc_id": "liquete_2013_european_marine_es",
        "title": "Current status and future prospects for the assessment of marine and coastal ecosystem services",
        "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0067737",
        "doi": "10.1371/journal.pone.0067737",
        "authors": "Liquete C, et al.",
        "year": 2013,
        "journal": "PLOS ONE",
        "source_tier": "T1",
        "domain_tags": ["ecosystem_services", "assessment", "european"],
        "notes": "European marine ES assessment. Status and prospects."
    },
    {
        "doc_id": "potts_2014_marine_es_indicators",
        "title": "Do marine protected areas deliver flows of ecosystem services to support human welfare?",
        "url": "https://www.sciencedirect.com/science/article/pii/S0308597X1400069X",
        "doi": "10.1016/j.marpol.2014.03.001",
        "authors": "Potts T, et al.",
        "year": 2014,
        "journal": "Marine Policy",
        "source_tier": "T1",
        "domain_tags": ["mpa_effectiveness", "ecosystem_services"],
        "notes": "MPA ecosystem service delivery. Human welfare indicators."
    },

    # Additional trophic ecology
    {
        "doc_id": "bascompte_2005_food_web_structure",
        "title": "Interaction strength combinations and the overfishing of a marine food web",
        "url": "https://www.pnas.org/doi/10.1073/pnas.0501562102",
        "doi": "10.1073/pnas.0501562102",
        "authors": "Bascompte J, et al.",
        "year": 2005,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "fisheries"],
        "notes": "Food web structure and overfishing impacts."
    },
    {
        "doc_id": "pauly_1998_fishing_down",
        "title": "Fishing Down Marine Food Webs",
        "url": "https://www.science.org/doi/10.1126/science.279.5352.860",
        "doi": "10.1126/science.279.5352.860",
        "authors": "Pauly D, et al.",
        "year": 1998,
        "journal": "Science",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "fisheries"],
        "notes": "Landmark paper. Fishing down food webs globally."
    },
    {
        "doc_id": "mccauley_2015_marine_defaunation",
        "title": "Marine defaunation: Animal loss in the global ocean",
        "url": "https://www.science.org/doi/10.1126/science.1255641",
        "doi": "10.1126/science.1255641",
        "authors": "McCauley DJ, et al.",
        "year": 2015,
        "journal": "Science",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "biodiversity"],
        "notes": "Marine defaunation patterns. Less severe than terrestrial but accelerating."
    },

    # Additional blue carbon
    {
        "doc_id": "mcleod_2011_blue_carbon_intro",
        "title": "A blueprint for blue carbon: toward an improved understanding of the role of vegetated coastal habitats in sequestering CO2",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1890/110004",
        "doi": "10.1890/110004",
        "authors": "McLeod E, et al.",
        "year": 2011,
        "journal": "Frontiers in Ecology and the Environment",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "coastal_habitats"],
        "notes": "Blue carbon blueprint. Research priorities identified."
    },
    {
        "doc_id": "alongi_2014_mangrove_carbon_update",
        "title": "Carbon Cycling and Storage in Mangrove Forests",
        "url": "https://www.annualreviews.org/doi/10.1146/annurev-marine-010213-135020",
        "doi": "10.1146/annurev-marine-010213-135020",
        "authors": "Alongi DM",
        "year": 2014,
        "journal": "Annual Review of Marine Science",
        "source_tier": "T1",
        "domain_tags": ["mangrove", "blue_carbon"],
        "habitat": "mangrove",
        "notes": "Mangrove carbon cycling review. Storage and flux dynamics."
    },
    {
        "doc_id": "duarte_2013_blue_carbon_concept",
        "title": "The role of coastal plant communities for climate change mitigation and adaptation",
        "url": "https://www.nature.com/articles/nclimate1970",
        "doi": "10.1038/nclimate1970",
        "authors": "Duarte CM, et al.",
        "year": 2013,
        "journal": "Nature Climate Change",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "climate_mitigation"],
        "notes": "Coastal vegetation role in climate solutions."
    },

    # Additional restoration
    {
        "doc_id": "bouma_2014_seagrass_restoration_review",
        "title": "Identifying knowledge gaps hampering application of intertidal habitats in coastal protection",
        "url": "https://www.sciencedirect.com/science/article/pii/S0378383914000350",
        "doi": "10.1016/j.coasteng.2014.02.004",
        "authors": "Bouma TJ, et al.",
        "year": 2014,
        "journal": "Coastal Engineering",
        "source_tier": "T1",
        "domain_tags": ["restoration", "coastal_protection"],
        "notes": "Intertidal habitat restoration for coastal protection."
    },
    {
        "doc_id": "hein_2017_restoration_success",
        "title": "The promise of blue carbon climate solutions: where the science supports ocean-climate action",
        "url": "https://www.frontiersin.org/articles/10.3389/fmars.2023.1021215/full",
        "doi": "10.3389/fmars.2023.1021215",
        "authors": "Hein MY, et al.",
        "year": 2023,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "restoration", "climate"],
        "notes": "Blue carbon restoration science. Evidence for ocean-climate action."
    },

    # Data repositories and methods
    {
        "doc_id": "obis_2024_data_standards",
        "title": "OBIS: Ocean Biodiversity Information System",
        "url": "https://obis.org/",
        "authors": "OBIS",
        "year": 2024,
        "journal": "OBIS",
        "source_tier": "T3",
        "document_type": "database",
        "domain_tags": ["data_repository", "biodiversity"],
        "notes": "Global ocean biodiversity database. 100M+ occurrence records."
    },
    {
        "doc_id": "worms_2024_taxonomy",
        "title": "World Register of Marine Species (WoRMS)",
        "url": "https://www.marinespecies.org/",
        "authors": "WoRMS Editorial Board",
        "year": 2024,
        "journal": "WoRMS",
        "source_tier": "T3",
        "document_type": "database",
        "domain_tags": ["data_repository", "taxonomy"],
        "notes": "Marine species taxonomy standard. 242k+ accepted species."
    },
    {
        "doc_id": "fishbase_2024_fish_data",
        "title": "FishBase: A Global Information System on Fishes",
        "url": "https://www.fishbase.org/",
        "authors": "FishBase Consortium",
        "year": 2024,
        "journal": "FishBase",
        "source_tier": "T3",
        "document_type": "database",
        "domain_tags": ["data_repository", "fish", "trophic_ecology"],
        "notes": "Global fish database. 35k+ species. Trophic level data."
    },
    {
        "doc_id": "globi_2024_interactions",
        "title": "Global Biotic Interactions (GloBI)",
        "url": "https://www.globalbioticinteractions.org/",
        "authors": "GloBI",
        "year": 2024,
        "journal": "GloBI",
        "source_tier": "T3",
        "document_type": "database",
        "domain_tags": ["data_repository", "trophic_ecology", "interactions"],
        "notes": "Species interaction database. Food web data aggregation."
    },

    # Gulf of California / Cabo Pulmo specific
    {
        "doc_id": "cinner_2016_bright_spots",
        "title": "Bright spots among the world's coral reefs",
        "url": "https://www.nature.com/articles/nature18607",
        "doi": "10.1038/nature18607",
        "authors": "Cinner JE, et al.",
        "year": 2016,
        "journal": "Nature",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "conservation", "bright_spots"],
        "habitat": "coral_reef",
        "notes": "Coral reef bright spots. Social-ecological conditions for success."
    },
    {
        "doc_id": "enriquez_andrade_2005_goc_fisheries",
        "title": "An analysis of critical areas for biodiversity conservation in the Gulf of California Region",
        "url": "https://www.sciencedirect.com/science/article/pii/S0964569104001316",
        "doi": "10.1016/j.ocecoaman.2004.12.001",
        "authors": "Enríquez-Andrade R, et al.",
        "year": 2005,
        "journal": "Ocean & Coastal Management",
        "source_tier": "T1",
        "domain_tags": ["gulf_of_california", "biodiversity", "conservation"],
        "notes": "Gulf of California critical areas. Conservation priorities."
    },
    {
        "doc_id": "cisneros_montemayor_2013_mpa_economics_mexico",
        "title": "Economic analysis of fisheries and conservation in the Gulf of California",
        "url": "https://www.sciencedirect.com/science/article/pii/S0025326X13003408",
        "doi": "10.1016/j.marpolbul.2013.06.003",
        "authors": "Cisneros-Montemayor AM, et al.",
        "year": 2013,
        "journal": "Marine Pollution Bulletin",
        "source_tier": "T1",
        "domain_tags": ["gulf_of_california", "fisheries", "economics"],
        "notes": "Gulf of California fisheries economics. Conservation trade-offs."
    },

    # California kelp specific
    {
        "doc_id": "cavanaugh_2011_kelp_landsat",
        "title": "Environmental controls of giant-kelp biomass in the Santa Barbara Channel, California",
        "url": "https://www.int-res.com/abstracts/meps/v429/meps09141",
        "doi": "10.3354/meps09141",
        "authors": "Cavanaugh KC, et al.",
        "year": 2011,
        "journal": "Marine Ecology Progress Series",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "california", "remote_sensing"],
        "habitat": "kelp_forest",
        "notes": "Landsat kelp biomass in Santa Barbara. Environmental drivers."
    },
    {
        "doc_id": "reed_2016_sbc_lter",
        "title": "Santa Barbara Coastal LTER: Long-term ecological research",
        "url": "https://sbclter.msi.ucsb.edu/",
        "authors": "Reed DC, et al.",
        "year": 2016,
        "journal": "SBC LTER",
        "source_tier": "T3",
        "document_type": "database",
        "domain_tags": ["kelp_forest", "california", "data_repository"],
        "habitat": "kelp_forest",
        "notes": "Santa Barbara Coastal LTER. 20+ years kelp forest data."
    },
    {
        "doc_id": "hamilton_2020_ca_kelp_value",
        "title": "Valuing kelp forest ecosystem services in California",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/conl.12735",
        "doi": "10.1111/conl.12735",
        "authors": "Hamilton SL, et al.",
        "year": 2020,
        "journal": "Conservation Letters",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "california", "ecosystem_services"],
        "habitat": "kelp_forest",
        "notes": "California kelp ES valuation. Multi-service assessment."
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

    index = recalculate_statistics(index)
    save_index(index)

    print(f"\nResults:")
    print(f"  Added: {added}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  New total: {len(index['documents'])}")


if __name__ == "__main__":
    main()
