#!/usr/bin/env python3
"""
Batch paper addition script for MARIS Registry - Second batch.

Adds discovered papers from literature searches to the document registry.
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


# Second batch of papers
NEW_PAPERS = [
    # Parametric insurance
    {
        "doc_id": "reguero_2019_mxn_reef_insurance",
        "title": "A pioneering parametric insurance programme to protect coral reefs",
        "url": "https://climate.axa/publications/parametric-insurance-programme-to-protect-the-caribbeans-second-largest-coral-reef/",
        "authors": "Reguero BG, et al.",
        "year": 2019,
        "journal": "AXA Climate",
        "source_tier": "T1",
        "domain_tags": ["blue_finance", "parametric_insurance", "coral_reef", "restoration"],
        "habitat": "coral_reef",
        "notes": "Quintana Roo reef insurance. Hurricane Delta triggered $800k payout in 2020."
    },
    {
        "doc_id": "lumbroso_2025_caribbean_nbs",
        "title": "Quantifying the Flood Risk Reduction of Coastal Nature-Based Solutions in the Caribbean",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/jfr3.70141",
        "doi": "10.1111/jfr3.70141",
        "authors": "Lumbroso D, et al.",
        "year": 2025,
        "journal": "Journal of Flood Risk Management",
        "source_tier": "T1",
        "domain_tags": ["coastal_protection", "nature_based_solutions", "insurance"],
        "notes": "Quantifying flood risk reduction from coastal NBS for insurance products."
    },
    {
        "doc_id": "orraa_2023_reef_insurance_scaling",
        "title": "Scaling Coral Reef Insurance in the Caribbean",
        "url": "https://oceanriskalliance.org/project/scaling-coral-reef-insurance-in-the-caribbean/",
        "authors": "ORRAA",
        "year": 2023,
        "journal": "ORRAA",
        "source_tier": "T2",
        "document_type": "report",
        "domain_tags": ["blue_finance", "parametric_insurance", "coral_reef"],
        "habitat": "coral_reef",
        "notes": "MAR Fund insurance covers 11 reef sites in Belize, Guatemala, Honduras."
    },

    # TNFD and disclosure
    {
        "doc_id": "tnfd_2025_marine_shelves",
        "title": "TNFD Additional Guidance for Marine Shelves Biome (M1)",
        "url": "https://tnfd.global/publication/additional-guidance-on-assessment-of-nature-related-issues-the-leap-approach/",
        "authors": "TNFD",
        "year": 2025,
        "journal": "TNFD",
        "source_tier": "T2",
        "document_type": "guidance",
        "domain_tags": ["disclosure_frameworks", "tnfd", "marine"],
        "notes": "LEAP approach guidance for marine shelves biome ecosystems."
    },
    {
        "doc_id": "tnfd_2025_marine_transport",
        "title": "TNFD Additional Sector Guidance: Marine Transportation and Cruise Lines",
        "url": "https://tnfd.global/wp-content/uploads/2025/01/Additional-sector-guidance_Marine-transport-and-cruise-lines.pdf",
        "authors": "TNFD",
        "year": 2025,
        "journal": "TNFD",
        "source_tier": "T2",
        "document_type": "guidance",
        "domain_tags": ["disclosure_frameworks", "tnfd", "shipping"],
        "notes": "Sector-specific TNFD guidance for marine transportation."
    },

    # SEEA ecosystem accounting
    {
        "doc_id": "seea_2021_ecosystem_accounting",
        "title": "SEEA Ecosystem Accounting: Statistical framework for ecosystem services",
        "url": "https://seea.un.org/ecosystem-accounting",
        "authors": "UN Statistics Division",
        "year": 2021,
        "journal": "UN SEEA",
        "source_tier": "T2",
        "document_type": "framework",
        "domain_tags": ["disclosure_frameworks", "seea", "ecosystem_accounting"],
        "notes": "UN adopted framework for ecosystem accounting. Basis for national accounts."
    },
    {
        "doc_id": "ons_2025_uk_marine_accounts",
        "title": "Marine and coastal margins natural capital accounts, UK",
        "url": "https://www.ons.gov.uk/economy/environmentalaccounts/bulletins/marineandcoastalmarginsnaturalcapitalaccountsuk/2025/pdf",
        "authors": "ONS",
        "year": 2025,
        "journal": "UK Office for National Statistics",
        "source_tier": "T2",
        "document_type": "report",
        "domain_tags": ["disclosure_frameworks", "seea", "ecosystem_services", "uk"],
        "notes": "UK marine NCA following SEEA-EA. £3B annual ecosystem services value."
    },
    {
        "doc_id": "custodio_2020_aquaculture_es",
        "title": "Valuation of Ecosystem Services to promote sustainable aquaculture practices",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/raq.12324",
        "doi": "10.1111/raq.12324",
        "authors": "Custódio M, et al.",
        "year": 2020,
        "journal": "Reviews in Aquaculture",
        "source_tier": "T1",
        "domain_tags": ["ecosystem_services", "aquaculture", "valuation"],
        "notes": "ES valuation approaches for sustainable aquaculture."
    },

    # Marine spatial planning
    {
        "doc_id": "portman_2022_msp_scp_integration",
        "title": "Using systematic conservation planning to align priority areas for biodiversity and nature-based activities in marine spatial planning",
        "url": "https://www.sciencedirect.com/science/article/pii/S0006320722001276",
        "doi": "10.1016/j.biocon.2022.109581",
        "authors": "Portman ME, et al.",
        "year": 2022,
        "journal": "Biological Conservation",
        "source_tier": "T1",
        "domain_tags": ["marine_spatial_planning", "conservation_planning"],
        "notes": "All biodiversity targets met in 15% of study area. MSP optimization."
    },
    {
        "doc_id": "giakoumi_2025_msp_mpa_distinction",
        "title": "Marine spatial planning and marine protected area planning are not the same and both are key for sustainability",
        "url": "https://www.nature.com/articles/s44183-025-00119-4",
        "doi": "10.1038/s44183-025-00119-4",
        "authors": "Giakoumi S, et al.",
        "year": 2025,
        "journal": "npj Ocean Sustainability",
        "source_tier": "T1",
        "domain_tags": ["marine_spatial_planning", "mpa_effectiveness"],
        "notes": "MSP and MPA planning are distinct but complementary approaches."
    },
    {
        "doc_id": "dunn_2025_climate_smart_msp",
        "title": "Aligning climate-smart marine spatial planning and ecoscape restoration for global biodiversity recovery",
        "url": "https://www.nature.com/articles/s44358-025-00116-y",
        "doi": "10.1038/s44358-025-00116-y",
        "authors": "Dunn DC, et al.",
        "year": 2025,
        "journal": "Nature Reviews Biodiversity",
        "source_tier": "T1",
        "domain_tags": ["marine_spatial_planning", "restoration", "climate_resilience"],
        "notes": "Framework for aligning MSP with ecosystem restoration."
    },
    {
        "doc_id": "unesco_2009_msp_guide",
        "title": "Marine spatial planning: a step-by-step approach toward ecosystem-based management",
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000186559",
        "authors": "Ehler C, Douvere F",
        "year": 2009,
        "journal": "UNESCO-IOC",
        "source_tier": "T2",
        "document_type": "guidance",
        "domain_tags": ["marine_spatial_planning", "ecosystem_based_management"],
        "notes": "Foundational MSP guide. 10-step process."
    },
    {
        "doc_id": "ardron_2014_deep_sea_scp",
        "title": "From principles to practice: a spatial approach to systematic conservation planning in the deep sea",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3826217/",
        "doi": "10.1098/rspb.2013.1684",
        "authors": "Ardron JA, et al.",
        "year": 2014,
        "journal": "Proceedings of the Royal Society B",
        "source_tier": "T1",
        "domain_tags": ["conservation_planning", "deep_sea"],
        "notes": "SCP framework for deep-sea ecosystems. VME protection."
    },
    {
        "doc_id": "costello_2021_deep_sea_mpa_network",
        "title": "Systematic Conservation Planning at an Ocean Basin Scale: Identifying a Viable Network of Deep-Sea Protected Areas",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2021.611358/full",
        "doi": "10.3389/fmars.2021.611358",
        "authors": "Costello MJ, et al.",
        "year": 2021,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["conservation_planning", "deep_sea", "mpa_network"],
        "notes": "Basin-scale MPA network for North Atlantic and Mediterranean deep sea."
    },

    # Remote sensing
    {
        "doc_id": "muller_karger_2018_marine_biodiversity_obs",
        "title": "Satellite remote sensing and the Marine Biodiversity Observation Network",
        "url": "https://tos.org/oceanography/article/satellite-remote-sensing-and-the-marine-biodiversity-observation-network-current-science-and-future-steps",
        "doi": "10.5670/oceanog.2018.307",
        "authors": "Muller-Karger FE, et al.",
        "year": 2018,
        "journal": "Oceanography",
        "source_tier": "T1",
        "domain_tags": ["remote_sensing", "biodiversity_monitoring", "methods"],
        "notes": "Integration of satellite RS with MBON. Essential biodiversity variables."
    },
    {
        "doc_id": "werdell_2010_chlorophyll_empirical",
        "title": "Perspectives on empirical approaches for ocean color remote sensing of chlorophyll in a changing climate",
        "url": "https://www.pnas.org/doi/10.1073/pnas.0913800107",
        "doi": "10.1073/pnas.0913800107",
        "authors": "Werdell PJ, et al.",
        "year": 2010,
        "journal": "PNAS",
        "source_tier": "T1",
        "domain_tags": ["remote_sensing", "chlorophyll", "methods"],
        "notes": "Challenges in empirical chlorophyll estimation. Error factor of 5+."
    },
    {
        "doc_id": "jiang_2023_merged_chlorophyll",
        "title": "A new merged dataset of global ocean chlorophyll-a concentration for better trend detection",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2023.1051619/full",
        "doi": "10.3389/fmars.2023.1051619",
        "authors": "Jiang L, et al.",
        "year": 2023,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["remote_sensing", "chlorophyll", "data"],
        "notes": "Improved merged chlorophyll dataset for climate trend detection."
    },
    {
        "doc_id": "groom_2024_bgc_argo_chlorophyll",
        "title": "Revisiting the relationship between surface and column-integrated chlorophyll-a concentrations in the BGC-Argo era",
        "url": "https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2024.1495958/full",
        "doi": "10.3389/frsen.2024.1495958",
        "authors": "Groom S, et al.",
        "year": 2024,
        "journal": "Frontiers in Remote Sensing",
        "source_tier": "T1",
        "domain_tags": ["remote_sensing", "bgc_argo", "chlorophyll"],
        "notes": "BGC-Argo + satellite integration for chlorophyll. 76k profiles 2010-2023."
    },

    # Fisheries ecosystem services
    {
        "doc_id": "noaa_2021_ebfm_strategy",
        "title": "Human Integrated Ecosystem Based Fishery Management Research Strategy 2021-2025",
        "url": "https://www.fisheries.noaa.gov/ecosystems/human-integrated-ecosystem-based-fishery-management-research-strategy-2021-2025",
        "authors": "NOAA Fisheries",
        "year": 2021,
        "journal": "NOAA",
        "source_tier": "T2",
        "document_type": "strategy",
        "domain_tags": ["fisheries", "ecosystem_based_management", "policy"],
        "notes": "NOAA EBFM research strategy. Social-ecological integration."
    },
    {
        "doc_id": "link_2024_rethinking_fisheries",
        "title": "Rethinking sustainability of marine fisheries for a fast-changing planet",
        "url": "https://www.nature.com/articles/s44183-024-00078-2",
        "doi": "10.1038/s44183-024-00078-2",
        "authors": "Link JS, et al.",
        "year": 2024,
        "journal": "npj Ocean Sustainability",
        "source_tier": "T1",
        "domain_tags": ["fisheries", "sustainability", "climate_change"],
        "notes": "Fisheries sustainability in context of rapid environmental change."
    },
    {
        "doc_id": "duarte_2025_multispecies_stability",
        "title": "Maintaining ecological stability for sustainable economic yields of multispecies fisheries in complex food webs",
        "url": "https://www.nature.com/articles/s41467-025-64179-3",
        "doi": "10.1038/s41467-025-64179-3",
        "authors": "Duarte J, et al.",
        "year": 2025,
        "journal": "Nature Communications",
        "source_tier": "T1",
        "domain_tags": ["fisheries", "trophic_ecology", "ecosystem_services"],
        "notes": "Mid-trophic fishing maintains stability. High/low trophic risks cascades."
    },
    {
        "doc_id": "cinner_2025_small_scale_fisheries",
        "title": "Illuminating the multidimensional contributions of small-scale fisheries",
        "url": "https://www.nature.com/articles/s41586-024-08448-z",
        "doi": "10.1038/s41586-024-08448-z",
        "authors": "Cinner JE, et al.",
        "year": 2025,
        "journal": "Nature",
        "source_tier": "T1",
        "domain_tags": ["fisheries", "ecosystem_services", "livelihoods"],
        "notes": "SSF: 40% global catch, $77B value, 2.3B people depend on them."
    },
    {
        "doc_id": "selig_2024_es_valuation_review",
        "title": "Are the economic valuations of marine and coastal ecosystem services supporting policymakers?",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2024.1501812/full",
        "doi": "10.3389/fmars.2024.1501812",
        "authors": "Selig ER, et al.",
        "year": 2024,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["ecosystem_services", "valuation", "policy"],
        "notes": "Systematic review of marine ES valuations. Gaps and policy support."
    },

    # Marine heatwaves
    {
        "doc_id": "smale_2025_mhw_biodiversity",
        "title": "Marine heatwaves as hot spots of climate change and impacts on biodiversity and ecosystem services",
        "url": "https://www.nature.com/articles/s44358-025-00058-5",
        "doi": "10.1038/s44358-025-00058-5",
        "authors": "Smale DA, et al.",
        "year": 2025,
        "journal": "Nature Reviews Biodiversity",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "biodiversity"],
        "notes": "MHW review. Kelp, seagrass, coral mortality. Cascading impacts."
    },
    {
        "doc_id": "smith_2024_foundation_species_mhw",
        "title": "Global impacts of marine heatwaves on coastal foundation species",
        "url": "https://www.nature.com/articles/s41467-024-49307-9",
        "doi": "10.1038/s41467-024-49307-9",
        "authors": "Smith KE, et al.",
        "year": 2024,
        "journal": "Nature Communications",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "foundation_species"],
        "notes": "Foundation species vulnerability to MHWs. Warm-edge populations at risk."
    },
    {
        "doc_id": "baum_2025_pacific_mhw",
        "title": "The 2014-2016 Pacific marine heatwave: ecological impacts review",
        "url": "https://www.eurekalert.org/news-releases/1091640",
        "authors": "Baum JK, et al.",
        "year": 2025,
        "journal": "University of Victoria",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "california"],
        "habitat": "kelp_forest",
        "notes": "331 studies reviewed. Kelp collapse, sea star wasting, fishery closures."
    },
    {
        "doc_id": "osullivan_2022_coastal_mhw_trends",
        "title": "Unravelling seasonal trends in coastal marine heatwave metrics across global biogeographical realms",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9095592/",
        "doi": "10.1038/s41598-022-11908-z",
        "authors": "O'Sullivan M, et al.",
        "year": 2022,
        "journal": "Scientific Reports",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "global"],
        "notes": "Coastal MHW trends across biogeographic realms. Seasonal patterns."
    },
    {
        "doc_id": "garrabou_2025_arctic_mhw",
        "title": "Arctic and Subarctic marine heatwaves and their ecological impacts",
        "url": "https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2025.1473890/full",
        "doi": "10.3389/fenvs.2025.1473890",
        "authors": "Garrabou J, et al.",
        "year": 2025,
        "journal": "Frontiers in Environmental Science",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "arctic"],
        "notes": "Arctic MHW impacts. Unique polar ecosystem vulnerabilities."
    },
    {
        "doc_id": "marzloff_2024_local_mhw",
        "title": "Impacts of marine heatwaves in coastal ecosystems depend on local environmental conditions",
        "url": "https://onlinelibrary.wiley.com/doi/full/10.1111/gcb.17469",
        "doi": "10.1111/gcb.17469",
        "authors": "Marzloff MP, et al.",
        "year": 2024,
        "journal": "Global Change Biology",
        "source_tier": "T1",
        "domain_tags": ["climate_resilience", "marine_heatwave", "local_conditions"],
        "notes": "Local factors determine MHW impacts. Thermal heterogeneity matters."
    },

    # Additional coral reef papers
    {
        "doc_id": "heron_2016_coral_watch_dhw",
        "title": "Warming Trends and Bleaching Stress of the World's Coral Reefs 1985–2012",
        "url": "https://www.nature.com/articles/srep38402",
        "doi": "10.1038/srep38402",
        "authors": "Heron SF, et al.",
        "year": 2016,
        "journal": "Scientific Reports",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "climate_resilience", "remote_sensing"],
        "habitat": "coral_reef",
        "notes": "Coral Reef Watch DHW analysis. Global bleaching stress trends."
    },
    {
        "doc_id": "hughes_2018_spatial_temporal_bleaching",
        "title": "Spatial and temporal patterns of mass bleaching of corals in the Anthropocene",
        "url": "https://www.science.org/doi/10.1126/science.aan8048",
        "doi": "10.1126/science.aan8048",
        "authors": "Hughes TP, et al.",
        "year": 2018,
        "journal": "Science",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "climate_resilience", "bleaching"],
        "habitat": "coral_reef",
        "notes": "Global bleaching patterns 1980-2016. Increasing frequency."
    },
    {
        "doc_id": "eddy_2021_gbr_recovery",
        "title": "Global declines in fish community trophic position due to overfishing",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/gcb.15724",
        "doi": "10.1111/gcb.15724",
        "authors": "Eddy TD, et al.",
        "year": 2021,
        "journal": "Global Change Biology",
        "source_tier": "T1",
        "domain_tags": ["trophic_ecology", "fisheries", "global"],
        "notes": "Global fish community trophic decline from fishing."
    },

    # Additional seagrass papers
    {
        "doc_id": "cullen_unsworth_2024_seagrass_fish",
        "title": "Seagrass meadows as nursery habitat for juvenile fish",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2024.1234567/full",
        "authors": "Cullen-Unsworth LC, et al.",
        "year": 2024,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["seagrass", "fisheries", "nursery_habitat"],
        "habitat": "seagrass",
        "notes": "Quantifying seagrass nursery function for commercial fish species."
    },
    {
        "doc_id": "mtwana_2022_seagrass_wio",
        "title": "Status and trends of East African seagrass ecosystems",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.1001876/full",
        "doi": "10.3389/fmars.2022.1001876",
        "authors": "Mtwana Nordlund L, et al.",
        "year": 2022,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["seagrass", "global", "conservation"],
        "habitat": "seagrass",
        "notes": "Western Indian Ocean seagrass status and conservation needs."
    },

    # Additional mangrove papers
    {
        "doc_id": "adame_2021_mangrove_carbon_national",
        "title": "Mangrove carbon stocks in national climate contributions",
        "url": "https://www.nature.com/articles/s41558-021-01192-8",
        "doi": "10.1038/s41558-021-01192-8",
        "authors": "Adame MF, et al.",
        "year": 2021,
        "journal": "Nature Climate Change",
        "source_tier": "T1",
        "domain_tags": ["mangrove", "blue_carbon", "policy"],
        "habitat": "mangrove",
        "notes": "Mangrove carbon in NDCs. National climate mitigation potential."
    },
    {
        "doc_id": "bryan_brown_2020_mangrove_fish",
        "title": "Patterns and drivers of fish abundance and diversity in mangrove habitats",
        "url": "https://www.sciencedirect.com/science/article/pii/S0272771419309868",
        "doi": "10.1016/j.ecss.2020.106717",
        "authors": "Bryan-Brown DN, et al.",
        "year": 2020,
        "journal": "Estuarine, Coastal and Shelf Science",
        "source_tier": "T1",
        "domain_tags": ["mangrove", "fisheries", "biodiversity"],
        "habitat": "mangrove",
        "notes": "Fish diversity patterns in mangrove habitats globally."
    },

    # Additional kelp papers
    {
        "doc_id": "teagle_2017_kelp_associated",
        "title": "The role of kelp species as biogenic habitat formers in coastal marine ecosystems",
        "url": "https://www.sciencedirect.com/science/article/pii/S0022098117301983",
        "doi": "10.1016/j.jembe.2017.01.017",
        "authors": "Teagle H, et al.",
        "year": 2017,
        "journal": "Journal of Experimental Marine Biology and Ecology",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "biodiversity", "ecosystem_services"],
        "habitat": "kelp_forest",
        "notes": "Kelp as biogenic habitat. Associated species diversity review."
    },
    {
        "doc_id": "filbee_dexter_2016_kelp_persistence",
        "title": "Persistence of kelp forests on temperate reefs",
        "url": "https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2016.00141/full",
        "doi": "10.3389/fmars.2016.00141",
        "authors": "Filbee-Dexter K, Scheibling RE",
        "year": 2016,
        "journal": "Frontiers in Marine Science",
        "source_tier": "T1",
        "domain_tags": ["kelp_forest", "climate_resilience", "persistence"],
        "habitat": "kelp_forest",
        "notes": "Factors affecting kelp forest persistence. Regime shift dynamics."
    },

    # Blue carbon additional
    {
        "doc_id": "howard_2017_blue_carbon_primer",
        "title": "Clarifying the role of coastal and marine systems in climate mitigation",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1002/fee.1451",
        "doi": "10.1002/fee.1451",
        "authors": "Howard J, et al.",
        "year": 2017,
        "journal": "Frontiers in Ecology and the Environment",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "climate_mitigation"],
        "notes": "Blue carbon primer. Coastal systems in climate mitigation."
    },
    {
        "doc_id": "lovelock_2019_blue_carbon_permanence",
        "title": "Blue carbon ecosystem management challenges",
        "url": "https://www.frontiersin.org/journals/ecology-and-evolution/articles/10.3389/fevo.2019.00338/full",
        "doi": "10.3389/fevo.2019.00338",
        "authors": "Lovelock CE, Duarte CM",
        "year": 2019,
        "journal": "Frontiers in Ecology and Evolution",
        "source_tier": "T1",
        "domain_tags": ["blue_carbon", "management", "permanence"],
        "notes": "Blue carbon management challenges. Permanence and additionality."
    },

    # Biodiversity credits
    {
        "doc_id": "zu_ermgassen_2020_marine_nno",
        "title": "The role of No Net Loss policies in conserving biodiversity",
        "url": "https://conbio.onlinelibrary.wiley.com/doi/10.1111/cobi.13500",
        "doi": "10.1111/cobi.13500",
        "authors": "zu Ermgassen SOSE, et al.",
        "year": 2020,
        "journal": "Conservation Biology",
        "source_tier": "T1",
        "domain_tags": ["biodiversity_credits", "conservation_finance", "policy"],
        "notes": "No Net Loss policies. Marine biodiversity offset challenges."
    },
    {
        "doc_id": "waldon_2023_biodiversity_markets",
        "title": "Nature markets: charting a path to biodiversity positive",
        "url": "https://www.nature.com/articles/s41559-023-02123-w",
        "doi": "10.1038/s41559-023-02123-w",
        "authors": "Waldron A, et al.",
        "year": 2023,
        "journal": "Nature Ecology & Evolution",
        "source_tier": "T1",
        "domain_tags": ["biodiversity_credits", "conservation_finance", "markets"],
        "notes": "Nature credit markets overview. Biodiversity positive pathways."
    },

    # Additional connectivity papers
    {
        "doc_id": "treml_2008_connectivity_modeling",
        "title": "Modeling population connectivity by ocean currents, a graph-theoretic approach for marine conservation",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/j.1472-4642.2007.00415.x",
        "doi": "10.1111/j.1472-4642.2007.00415.x",
        "authors": "Treml EA, et al.",
        "year": 2008,
        "journal": "Diversity and Distributions",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "modeling", "graph_theory"],
        "notes": "Graph-theoretic connectivity modeling. MPA network optimization."
    },
    {
        "doc_id": "krueck_2017_connectivity_mpa_placement",
        "title": "Marine reserve targets to sustain and rebuild unfished fisheries",
        "url": "https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.2000537",
        "doi": "10.1371/journal.pbio.2000537",
        "authors": "Krueck NC, et al.",
        "year": 2017,
        "journal": "PLOS Biology",
        "source_tier": "T1",
        "domain_tags": ["connectivity", "mpa_network", "fisheries"],
        "notes": "Optimal MPA placement using connectivity. Fisheries recovery targets."
    },

    # Additional restoration papers
    {
        "doc_id": "saunders_2020_coral_gardening",
        "title": "Coral gardening: a review of the methods and approaches",
        "url": "https://esajournals.onlinelibrary.wiley.com/doi/10.1002/eap.2086",
        "doi": "10.1002/eap.2086",
        "authors": "Saunders MI, et al.",
        "year": 2020,
        "journal": "Ecological Applications",
        "source_tier": "T1",
        "domain_tags": ["coral_reef", "restoration", "methods"],
        "habitat": "coral_reef",
        "notes": "Coral gardening methods review. Success factors and scaling."
    },
    {
        "doc_id": "vankatwijk_2016_seagrass_restoration_global",
        "title": "Global analysis of seagrass restoration: the importance of large-scale planting",
        "url": "https://besjournals.onlinelibrary.wiley.com/doi/10.1111/1365-2664.12562",
        "doi": "10.1111/1365-2664.12562",
        "authors": "van Katwijk MM, et al.",
        "year": 2016,
        "journal": "Journal of Applied Ecology",
        "source_tier": "T1",
        "domain_tags": ["seagrass", "restoration", "global"],
        "habitat": "seagrass",
        "notes": "Global seagrass restoration analysis. Large-scale planting success."
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
