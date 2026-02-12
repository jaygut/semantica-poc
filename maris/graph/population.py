"""
Populate Neo4j graph from existing curated data assets.

Sources:
  1. .claude/registry/document_index.json          - 195 doc metadata
  2. data/semantica_export/entities.jsonld          - 14 entities
  3. data/semantica_export/relationships.json       - 15 curated relationships
  4. data/semantica_export/bridge_axioms.json       - axioms (export)
  5. schemas/bridge_axiom_templates.json            - axioms (full coefficients)
  6. examples/cabo_pulmo_case_study.json            - Full site data (Cabo Pulmo)
  7. examples/shark_bay_case_study.json             - Full site data (Shark Bay)

All operations use MERGE (idempotent).
"""

import json
from pathlib import Path

from maris.config import get_config
from maris.graph.connection import get_driver


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Document nodes (from registry)
# ---------------------------------------------------------------------------
def _populate_documents(session, cfg):
    """Create Document nodes from the document registry."""
    registry_path = cfg.registry_path
    if not registry_path.exists():
        print("  WARNING: document registry not found, skipping documents.")
        return 0

    registry = _load_json(registry_path)
    docs = registry.get("documents", {})
    count = 0
    for doc_id, doc in docs.items():
        doi = doc.get("doi")
        if not doi:
            continue
        session.run(
            """
            MERGE (d:Document {doi: $doi})
            SET d.title       = $title,
                d.year        = $year,
                d.source_tier = $tier,
                d.domain      = $domain,
                d.url         = $url,
                d.abstract    = $abstract,
                d.doc_id      = $doc_id
            """,
            {
                "doi": doi,
                "title": doc.get("title", ""),
                "year": doc.get("year"),
                "tier": doc.get("source_tier", "T1"),
                "domain": doc.get("domain", ""),
                "url": doc.get("url", ""),
                "abstract": doc.get("abstract", ""),
                "doc_id": doc_id,
            },
        )
        count += 1
    print(f"  Documents: {count} merged.")
    return count


# ---------------------------------------------------------------------------
# 2. Entity nodes (Species, MPA, Habitat, EcosystemService, etc.)
# ---------------------------------------------------------------------------
def _populate_entities(session, cfg):
    """Create entity nodes from entities.jsonld."""
    data = _load_json(cfg.export_dir / "entities.jsonld")
    entities = data.get("entities", [])
    counts = {}

    for ent in entities:
        etype = ent.get("@type", "")
        eid = ent.get("@id", "")

        if etype == "Species":
            worms_id = int(eid.split(":")[-1]) if ":" in eid else 0
            session.run(
                """
                MERGE (s:Species {worms_id: $worms_id})
                SET s.scientific_name    = $scientific_name,
                    s.common_name        = $common_name,
                    s.fishbase_id        = $fishbase_id,
                    s.trophic_level      = $trophic_level,
                    s.functional_group   = $functional_group,
                    s.conservation_status = $conservation_status,
                    s.commercial_importance = $commercial_importance
                """,
                {
                    "worms_id": worms_id,
                    "scientific_name": ent.get("scientific_name", ""),
                    "common_name": ent.get("common_name", ""),
                    "fishbase_id": ent.get("fishbase_id"),
                    "trophic_level": ent.get("trophic_level"),
                    "functional_group": ent.get("functional_group", ""),
                    "conservation_status": ent.get("conservation_status", ""),
                    "commercial_importance": ent.get("commercial_importance", ""),
                },
            )
            counts["Species"] = counts.get("Species", 0) + 1

        elif etype == "MarineProtectedArea":
            session.run(
                """
                MERGE (m:MPA {name: $name})
                SET m.country           = $country,
                    m.lat               = $lat,
                    m.lon               = $lon,
                    m.area_km2          = $area_km2,
                    m.designation_year  = $designation_year,
                    m.neoli_score       = $neoli_score,
                    m.protection_level  = $protection_level,
                    m.biomass_recovery_percent = $biomass_recovery_percent,
                    m.asset_rating      = $asset_rating
                """,
                {
                    "name": ent.get("name", ""),
                    "country": ent.get("country", ""),
                    "lat": ent.get("coordinates", {}).get("lat"),
                    "lon": ent.get("coordinates", {}).get("lon"),
                    "area_km2": ent.get("area_km2"),
                    "designation_year": ent.get("designation_year"),
                    "neoli_score": ent.get("neoli_score"),
                    "protection_level": ent.get("protection_level", ""),
                    "biomass_recovery_percent": ent.get("biomass_recovery_percent"),
                    "asset_rating": ent.get("reference_condition", ""),
                },
            )
            counts["MPA"] = counts.get("MPA", 0) + 1

        elif etype == "Habitat":
            habitat_id = eid.split(":")[-1] if ":" in eid else eid
            session.run(
                """
                MERGE (h:Habitat {habitat_id: $habitat_id})
                SET h.name                  = $name,
                    h.per_hectare_value_usd = $per_hectare_value_usd,
                    h.global_extent_km2     = $global_extent_km2
                """,
                {
                    "habitat_id": habitat_id,
                    "name": ent.get("name", ""),
                    "per_hectare_value_usd": ent.get("per_hectare_value_usd"),
                    "global_extent_km2": ent.get("global_extent_km2"),
                },
            )
            counts["Habitat"] = counts.get("Habitat", 0) + 1

        elif etype == "EcosystemService":
            service_id = eid.split(":")[-1] if ":" in eid else eid
            session.run(
                """
                MERGE (es:EcosystemService {service_id: $service_id})
                SET es.service_name  = $name,
                    es.category      = $category,
                    es.source        = $source
                """,
                {
                    "service_id": service_id,
                    "name": ent.get("name", ""),
                    "category": ent.get("category", ""),
                    "source": ent.get("source", ""),
                },
            )
            counts["EcosystemService"] = counts.get("EcosystemService", 0) + 1

        elif etype == "FinancialInstrument":
            instrument_id = eid.split(":")[-1] if ":" in eid else eid
            session.run(
                """
                MERGE (fi:FinancialInstrument {instrument_id: $instrument_id})
                SET fi.name       = $name,
                    fi.definition = $definition
                """,
                {
                    "instrument_id": instrument_id,
                    "name": ent.get("name", ""),
                    "definition": ent.get("definition", ""),
                },
            )
            counts["FinancialInstrument"] = counts.get("FinancialInstrument", 0) + 1

        elif etype == "Framework":
            framework_id = eid.replace(":", "_") if ":" in eid else eid
            session.run(
                """
                MERGE (fw:Framework {framework_id: $framework_id})
                SET fw.name       = $name,
                    fw.definition = $definition
                """,
                {
                    "framework_id": framework_id,
                    "name": ent.get("name", ""),
                    "definition": ent.get("definition", ""),
                },
            )
            counts["Framework"] = counts.get("Framework", 0) + 1

        elif etype == "Concept":
            session.run(
                """
                MERGE (c:Concept {name: $name})
                SET c.definition = $definition,
                    c.source     = $source
                """,
                {
                    "name": ent.get("name", ""),
                    "definition": ent.get("definition", ""),
                    "source": ent.get("source", ""),
                },
            )
            counts["Concept"] = counts.get("Concept", 0) + 1

    for label, n in counts.items():
        print(f"  {label}: {n} merged.")
    return sum(counts.values())


# ---------------------------------------------------------------------------
# 3. Cabo Pulmo enrichment (species, services, trophic network)
# ---------------------------------------------------------------------------
def _populate_cabo_pulmo(session, cfg):
    """Enrich Cabo Pulmo MPA node with case study data and create service/species nodes."""
    cs = _load_json(cfg.case_study_path)
    count = 0

    # Enrich MPA node with full assessment data
    site = cs.get("site", {})
    neoli = cs.get("neoli_assessment", {})
    recovery = cs.get("ecological_recovery", {}).get("metrics", {}).get("fish_biomass", {})
    rating = cs.get("asset_quality_rating", {})

    # Compute data freshness status from measurement year
    measurement_year = cs.get("ecological_recovery", {}).get("assessment_year", 2009)
    import datetime as _dt
    _current_year = _dt.datetime.now().year
    _data_age = _current_year - measurement_year
    if _data_age <= 5:
        data_freshness = "current"
    elif _data_age <= 10:
        data_freshness = "aging"
    else:
        data_freshness = "stale"

    session.run(
        """
        MERGE (m:MPA {name: $name})
        SET m.country          = $country,
            m.lat              = $lat,
            m.lon              = $lon,
            m.area_km2         = $area_km2,
            m.designation_year = $designation_year,
            m.neoli_score      = $neoli_score,
            m.neoli_no_take    = $no_take,
            m.neoli_enforced   = $enforced,
            m.neoli_old        = $old,
            m.neoli_large      = $large,
            m.neoli_isolated   = $isolated,
            m.biomass_ratio    = $biomass_ratio,
            m.biomass_ci_low   = $ci_low,
            m.biomass_ci_high  = $ci_high,
            m.biomass_measurement_year = $measurement_year,
            m.asset_rating     = $asset_rating,
            m.asset_score      = $asset_score,
            m.total_esv_usd    = $total_esv,
            m.data_freshness_status = $freshness,
            m.last_validated_date   = $validated_date
        """,
        {
            "name": "Cabo Pulmo National Park",
            "country": site.get("country", "Mexico"),
            "lat": site.get("coordinates", {}).get("latitude", 23.42),
            "lon": site.get("coordinates", {}).get("longitude", -109.42),
            "area_km2": site.get("area_km2", 71.11),
            "designation_year": site.get("designation_year", 1995),
            "neoli_score": neoli.get("neoli_score", 4),
            "no_take": neoli.get("criteria", {}).get("no_take", {}).get("value", True),
            "enforced": neoli.get("criteria", {}).get("enforced", {}).get("value", True),
            "old": neoli.get("criteria", {}).get("old", {}).get("value", True),
            "large": neoli.get("criteria", {}).get("large", {}).get("value", False),
            "isolated": neoli.get("criteria", {}).get("isolated", {}).get("value", True),
            "biomass_ratio": recovery.get("recovery_ratio", 4.63),
            "ci_low": recovery.get("confidence_interval_95", [3.8])[0],
            "ci_high": recovery.get("confidence_interval_95", [None, 5.5])[1],
            "measurement_year": measurement_year,
            "asset_rating": rating.get("rating", "AAA"),
            "asset_score": rating.get("composite_score", 0.90),
            "total_esv": cs.get("ecosystem_services", {}).get("total_annual_value_usd", 29270000),
            "freshness": data_freshness,
            "validated_date": cs.get("ecological_recovery", {}).get("last_validated_date", ""),
        },
    )
    count += 1

    # Create EcosystemService nodes from case study services
    services = cs.get("ecosystem_services", {}).get("services", [])
    for svc in services:
        svc_type = svc.get("service_type", "")
        service_id = f"cabo_pulmo_{svc_type}"
        session.run(
            """
            MERGE (es:EcosystemService {service_id: $service_id})
            SET es.service_name     = $name,
                es.service_type     = $svc_type,
                es.category         = $category,
                es.annual_value_usd = $value,
                es.valuation_method = $method
            """,
            {
                "service_id": service_id,
                "name": svc_type.replace("_", " ").title(),
                "svc_type": svc_type,
                "category": svc.get("service_category", ""),
                "value": svc.get("annual_value_usd"),
                "method": svc.get("valuation_method", ""),
            },
        )
        # Link MPA -> GENERATES -> EcosystemService
        session.run(
            """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})
            MATCH (es:EcosystemService {service_id: $service_id})
            MERGE (m)-[g:GENERATES]->(es)
            SET g.total_usd_yr = $value,
                g.method       = $method
            """,
            {
                "service_id": service_id,
                "value": svc.get("annual_value_usd"),
                "method": svc.get("valuation_method", ""),
            },
        )
        count += 1

    # Create additional species from case study
    for sp in cs.get("key_species", []):
        worms_id = sp.get("worms_aphia_id", 0)
        if worms_id:
            session.run(
                """
                MERGE (s:Species {worms_id: $worms_id})
                SET s.scientific_name      = $scientific_name,
                    s.common_name          = $common_name,
                    s.fishbase_id          = $fishbase_id,
                    s.trophic_level        = $trophic_level,
                    s.functional_group     = $functional_group,
                    s.commercial_importance = $commercial_importance,
                    s.role_in_ecosystem    = $role
                """,
                {
                    "worms_id": worms_id,
                    "scientific_name": sp.get("scientific_name", ""),
                    "common_name": sp.get("common_name", ""),
                    "fishbase_id": sp.get("fishbase_spec_code"),
                    "trophic_level": sp.get("trophic_level"),
                    "functional_group": sp.get("functional_group", ""),
                    "commercial_importance": sp.get("commercial_importance", ""),
                    "role": sp.get("role_in_ecosystem", ""),
                },
            )
            # Link Species -[:LOCATED_IN]-> MPA
            session.run(
                """
                MATCH (s:Species {worms_id: $worms_id})
                MATCH (m:MPA {name: "Cabo Pulmo National Park"})
                MERGE (s)-[:LOCATED_IN]->(m)
                """,
                {"worms_id": worms_id},
            )
            count += 1

    # Trophic network: use TrophicLevel nodes with correct PREYS_ON direction
    # In the case study JSON, edges go from prey to predator (energy flow).
    # PREYS_ON direction: predator -[:PREYS_ON]-> prey
    trophic = cs.get("trophic_network", {})
    trophic_nodes = {n["id"]: n for n in trophic.get("nodes", [])}
    for node_id, node in trophic_nodes.items():
        session.run(
            """
            MERGE (t:TrophicLevel {node_id: $node_id})
            SET t.trophic_level    = $trophic_level,
                t.functional_group = $functional_group
            """,
            {
                "node_id": node_id,
                "trophic_level": node.get("trophic_level"),
                "functional_group": node.get("functional_group", ""),
            },
        )
    for edge in trophic.get("edges", []):
        # "from" = prey, "to" = predator (energy flow direction in JSON)
        # So predator PREYS_ON prey: (to)-[:PREYS_ON]->(from)
        session.run(
            """
            MATCH (predator:TrophicLevel {node_id: $predator_id})
            MATCH (prey:TrophicLevel {node_id: $prey_id})
            MERGE (predator)-[:PREYS_ON]->(prey)
            """,
            {"predator_id": edge.get("to", ""), "prey_id": edge.get("from", "")},
        )

    # Link trophic levels to Cabo Pulmo MPA
    session.run(
        """
        MATCH (t:TrophicLevel)
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MERGE (t)-[:PART_OF_FOODWEB]->(m)
        """
    )

    print(f"  Cabo Pulmo enrichment: {count} nodes/edges merged + trophic network.")
    return count


# ---------------------------------------------------------------------------
# 3b. Shark Bay enrichment (seagrass, carbon, services, species)
# ---------------------------------------------------------------------------
def _populate_shark_bay(session, cfg):
    """Enrich Shark Bay MPA node with case study data and create service/species nodes."""
    sb_path = cfg.shark_bay_case_study_path
    if not sb_path.exists():
        print("  WARNING: shark_bay_case_study.json not found, skipping Shark Bay.")
        return 0

    cs = _load_json(sb_path)
    count = 0

    site = cs.get("site", {})
    neoli = cs.get("neoli_assessment", {})
    eco = cs.get("ecological_status", {})
    rating = cs.get("asset_quality_rating", {})

    # Compute data freshness status
    measurement_year = eco.get("assessment_year", 2018)
    import datetime as _dt
    _current_year = _dt.datetime.now().year
    _data_age = _current_year - measurement_year
    if _data_age <= 5:
        data_freshness = "current"
    elif _data_age <= 10:
        data_freshness = "aging"
    else:
        data_freshness = "stale"

    session.run(
        """
        MERGE (m:MPA {name: $name})
        SET m.country          = $country,
            m.lat              = $lat,
            m.lon              = $lon,
            m.area_km2         = $area_km2,
            m.seagrass_extent_km2 = $seagrass_extent,
            m.designation_year = $designation_year,
            m.neoli_score      = $neoli_score,
            m.neoli_no_take    = $no_take,
            m.neoli_enforced   = $enforced,
            m.neoli_old        = $old,
            m.neoli_large      = $large,
            m.neoli_isolated   = $isolated,
            m.primary_habitat  = $primary_habitat,
            m.dominant_species = $dominant_species,
            m.carbon_stock_tCO2_per_ha = $carbon_stock,
            m.sequestration_rate_tCO2_per_ha_yr = $seq_rate,
            m.heatwave_loss_percent = $heatwave_loss,
            m.asset_rating     = $asset_rating,
            m.asset_score      = $asset_score,
            m.total_esv_usd    = $total_esv,
            m.data_freshness_status = $freshness,
            m.last_validated_date   = $validated_date
        """,
        {
            "name": "Shark Bay World Heritage Area",
            "country": site.get("country", "Australia"),
            "lat": site.get("coordinates", {}).get("latitude", -25.97),
            "lon": site.get("coordinates", {}).get("longitude", 113.86),
            "area_km2": site.get("area_km2", 23000),
            "seagrass_extent": site.get("seagrass_extent_km2", 4800),
            "designation_year": site.get("designation_year", 1991),
            "neoli_score": neoli.get("neoli_score", 4),
            "no_take": neoli.get("criteria", {}).get("no_take", {}).get("value", True),
            "enforced": neoli.get("criteria", {}).get("enforced", {}).get("value", True),
            "old": neoli.get("criteria", {}).get("old", {}).get("value", True),
            "large": neoli.get("criteria", {}).get("large", {}).get("value", True),
            "isolated": neoli.get("criteria", {}).get("isolated", {}).get("value", False),
            "primary_habitat": eco.get("primary_habitat", "seagrass_meadow"),
            "dominant_species": eco.get("dominant_species", "Posidonia australis"),
            "carbon_stock": eco.get("metrics", {}).get("carbon_stock", {}).get("stock_tCO2_per_ha", 294),
            "seq_rate": eco.get("metrics", {}).get("sequestration", {}).get("rate_tCO2_per_ha_yr", 0.84),
            "heatwave_loss": eco.get("metrics", {}).get("heatwave_impact", {}).get("seagrass_loss_percent", 36),
            "asset_rating": rating.get("rating", "AA"),
            "asset_score": rating.get("composite_score", 0.81),
            "total_esv": cs.get("ecosystem_services", {}).get("total_annual_value_usd", 21500000),
            "freshness": data_freshness,
            "validated_date": eco.get("last_validated_date", ""),
        },
    )
    count += 1

    # Create EcosystemService nodes from case study services
    services = cs.get("ecosystem_services", {}).get("services", [])
    for svc in services:
        svc_type = svc.get("service_type", "")
        service_id = f"shark_bay_{svc_type}"
        session.run(
            """
            MERGE (es:EcosystemService {service_id: $service_id})
            SET es.service_name     = $name,
                es.service_type     = $svc_type,
                es.category         = $category,
                es.annual_value_usd = $value,
                es.valuation_method = $method
            """,
            {
                "service_id": service_id,
                "name": svc_type.replace("_", " ").title(),
                "svc_type": svc_type,
                "category": svc.get("service_category", ""),
                "value": svc.get("annual_value_usd"),
                "method": svc.get("valuation_method", ""),
            },
        )
        # Link MPA -> GENERATES -> EcosystemService
        session.run(
            """
            MATCH (m:MPA {name: "Shark Bay World Heritage Area"})
            MATCH (es:EcosystemService {service_id: $service_id})
            MERGE (m)-[g:GENERATES]->(es)
            SET g.total_usd_yr = $value,
                g.method       = $method
            """,
            {
                "service_id": service_id,
                "value": svc.get("annual_value_usd"),
                "method": svc.get("valuation_method", ""),
            },
        )
        count += 1

    # Link Shark Bay to seagrass habitat
    session.run(
        """
        MATCH (m:MPA {name: "Shark Bay World Heritage Area"})
        MATCH (h:Habitat {habitat_id: "seagrass_meadow"})
        MERGE (m)-[:HAS_HABITAT]->(h)
        """
    )
    count += 1

    # Create provenance edges
    for src in cs.get("provenance", {}).get("data_sources", []):
        doi = src.get("doi", "")
        if not doi or "xxxx" in doi:
            continue
        session.run(
            """
            MATCH (m:MPA {name: "Shark Bay World Heritage Area"})
            MERGE (d:Document {doi: $doi})
            MERGE (m)-[r:DERIVED_FROM]->(d)
            SET r.data_type   = $data_type,
                r.access_date = $access_date
            """,
            {
                "doi": doi,
                "data_type": src.get("data_type", ""),
                "access_date": src.get("access_date", ""),
            },
        )
        count += 1

    print(f"  Shark Bay enrichment: {count} nodes/edges merged.")
    return count


# ---------------------------------------------------------------------------
# 4. Bridge Axiom nodes with comprehensive links
# ---------------------------------------------------------------------------
def _populate_bridge_axioms(session, cfg):
    """Create BridgeAxiom nodes from templates + export, link to evidence, services, habitats."""
    templates = _load_json(cfg.schemas_dir / "bridge_axiom_templates.json")
    export = _load_json(cfg.export_dir / "bridge_axioms.json")

    export_lookup = {a["axiom_id"]: a for a in export.get("bridge_axioms", [])}
    count = 0

    for axiom in templates.get("axioms", []):
        aid = axiom["axiom_id"]
        export_ax = export_lookup.get(aid, {})

        coefficients_json = json.dumps(axiom.get("coefficients", {}))
        caveats = axiom.get("caveats", [])

        session.run(
            """
            MERGE (a:BridgeAxiom {axiom_id: $axiom_id})
            SET a.name                = $name,
                a.category            = $category,
                a.description         = $description,
                a.pattern             = $pattern,
                a.coefficients_json   = $coefficients_json,
                a.applicable_habitats = $habitats,
                a.evidence_tier       = $tier,
                a.caveats             = $caveats,
                a.version             = "1.1",
                a.confidence          = $confidence,
                a.domain_from         = $domain_from,
                a.domain_to           = $domain_to
            """,
            {
                "axiom_id": aid,
                "name": axiom.get("name", ""),
                "category": axiom.get("category", ""),
                "description": axiom.get("description", ""),
                "pattern": axiom.get("pattern", ""),
                "coefficients_json": coefficients_json,
                "habitats": axiom.get("applicable_habitats", []),
                "tier": axiom.get("evidence_tier", "T1"),
                "caveats": caveats,
                "confidence": export_ax.get("confidence", "high"),
                "domain_from": export_ax.get("domain_from", ""),
                "domain_to": export_ax.get("domain_to", ""),
            },
        )
        count += 1

        # Link axiom -> EVIDENCED_BY -> Document (by DOI)
        for src in axiom.get("sources", []):
            doi = src.get("doi", "")
            if doi:
                session.run(
                    """
                    MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                    MERGE (d:Document {doi: $doi})
                    ON CREATE SET d.title = $title
                    MERGE (a)-[e:EVIDENCED_BY]->(d)
                    SET e.finding = $finding
                    """,
                    {
                        "axiom_id": aid,
                        "doi": doi,
                        "title": src.get("citation", ""),
                        "finding": src.get("finding", ""),
                    },
                )

        # Link axiom -> APPLIES_TO_HABITAT -> Habitat (from applicable_habitats)
        habitat_map = {
            "coral_reef": "coral_reef",
            "kelp_forest": "kelp_forest",
            "mangrove_forest": "mangrove_forest",
            "seagrass_meadow": "seagrass_meadow",
        }
        for hab_name in axiom.get("applicable_habitats", []):
            hab_id = habitat_map.get(hab_name)
            if hab_id:
                session.run(
                    """
                    MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                    MATCH (h:Habitat {habitat_id: $hab_id})
                    MERGE (a)-[:APPLIES_TO_HABITAT]->(h)
                    """,
                    {"axiom_id": aid, "hab_id": hab_id},
                )

        # Link axiom -> APPLIES_TO -> MPA (Cabo Pulmo for relevant axioms)
        # BA-001 (tourism), BA-002 (biomass), BA-004 (coastal protection),
        # BA-011 (climate resilience), BA-012 (reef fisheries loss)
        # are all directly applicable to Cabo Pulmo's coral reef ecosystem
        if aid in ("BA-001", "BA-002", "BA-004", "BA-011", "BA-012"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                MATCH (m:MPA {name: "Cabo Pulmo National Park"})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"axiom_id": aid},
            )

        # Link blue carbon axioms -> APPLIES_TO -> Shark Bay
        # BA-013 (seagrass carbon stock), BA-014 (seagrass nursery),
        # BA-015 (heatwave permanence risk), BA-016 (seagrass coastal protection)
        if aid in ("BA-013", "BA-014", "BA-015", "BA-016"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                MATCH (m:MPA {name: "Shark Bay World Heritage Area"})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"axiom_id": aid},
            )

        # Link axiom -> TRANSLATES -> EcosystemService
        svc_map = {
            "BA-001": "cabo_pulmo_tourism",
            "BA-004": "cabo_pulmo_coastal_protection",
            "BA-006": "cabo_pulmo_fisheries_spillover",
            "BA-008": "cabo_pulmo_carbon_sequestration",
            "BA-012": "cabo_pulmo_fisheries_spillover",
            "BA-013": "shark_bay_carbon_sequestration",
            "BA-014": "shark_bay_fisheries",
            "BA-016": "shark_bay_coastal_protection",
        }
        svc_id = svc_map.get(aid)
        if svc_id:
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                MATCH (es:EcosystemService {service_id: $svc_id})
                MERGE (a)-[:TRANSLATES]->(es)
                """,
                {"axiom_id": aid, "svc_id": svc_id},
            )

    print(f"  BridgeAxioms: {count} merged with evidence + habitat + service links.")
    return count


# ---------------------------------------------------------------------------
# 5. Curated relationships from relationships.json
# ---------------------------------------------------------------------------
def _populate_relationships(session, cfg):
    """Load the 15 curated cross-domain relationships from the export."""
    data = _load_json(cfg.export_dir / "relationships.json")
    rels = data.get("relationships", [])
    count = 0

    # Map relationship subject/object IDs to graph match patterns
    # These are the @id values from entities.jsonld
    node_lookup = {
        "maris:neoli_criteria": ("Concept", "name", "NEOLI Criteria"),
        "maris:cabo_pulmo_np": ("MPA", "name", "Cabo Pulmo National Park"),
        "maris:coral_reef": ("Habitat", "habitat_id", "coral_reef"),
        "maris:kelp_forest": ("Habitat", "habitat_id", "kelp_forest"),
        "maris:seagrass_meadow": ("Habitat", "habitat_id", "seagrass_meadow"),
        "maris:mangrove_forest": ("Habitat", "habitat_id", "mangrove_forest"),
        "maris:flood_protection_coral": ("EcosystemService", "service_id", "flood_protection_coral"),
        "maris:coastal_wetland_services": ("EcosystemService", "service_id", "coastal_wetland_services"),
        "maris:blue_bond": ("FinancialInstrument", "instrument_id", "blue_bond"),
        "maris:parametric_reef_insurance": ("FinancialInstrument", "instrument_id", "parametric_reef_insurance"),
        "tnfd:leap": ("Framework", "framework_id", "tnfd_leap"),
        "seea:ecosystem_accounting": ("Framework", "framework_id", "seea_ecosystem_accounting"),
        "worms:281326": ("Species", "worms_id", 281326),
        "worms:275789": ("Species", "worms_id", 275789),
    }

    for rel in rels:
        subj_id = rel.get("subject", "")
        obj_id = rel.get("object", "")
        rel_type = rel.get("type", "RELATED_TO")
        strength = rel.get("strength", "")
        quantification = rel.get("quantification", "")
        mechanism = rel.get("mechanism", "")
        confidence = rel.get("confidence", "")

        subj_info = node_lookup.get(subj_id)
        obj_info = node_lookup.get(obj_id)

        if subj_info and obj_info:
            # Both sides are known entities - create typed relationship
            s_label, s_key, s_val = subj_info
            o_label, o_key, o_val = obj_info
            session.run(
                f"""
                MATCH (s:{s_label} {{{s_key}: $s_val}})
                MATCH (o:{o_label} {{{o_key}: $o_val}})
                MERGE (s)-[r:{rel_type}]->(o)
                SET r.quantification = $quant,
                    r.mechanism      = $mechanism,
                    r.confidence     = $confidence,
                    r.strength       = $strength,
                    r.rel_id         = $rel_id
                """,
                {
                    "s_val": s_val,
                    "o_val": o_val,
                    "quant": quantification,
                    "mechanism": mechanism if isinstance(mechanism, str) else json.dumps(mechanism),
                    "confidence": confidence,
                    "strength": strength,
                    "rel_id": rel.get("id", ""),
                },
            )
            count += 1
        elif subj_info:
            # Subject is known, object is an abstract concept - store as property
            s_label, s_key, s_val = subj_info
            session.run(
                f"""
                MATCH (s:{s_label} {{{s_key}: $s_val}})
                MERGE (c:Concept {{name: $obj_name}})
                MERGE (s)-[r:{rel_type}]->(c)
                SET r.quantification = $quant,
                    r.mechanism      = $mechanism,
                    r.confidence     = $confidence,
                    r.rel_id         = $rel_id
                """,
                {
                    "s_val": s_val,
                    "obj_name": obj_id.replace("_", " ").title() if "maris:" not in obj_id else obj_id,
                    "quant": quantification,
                    "mechanism": mechanism if isinstance(mechanism, str) else json.dumps(mechanism),
                    "confidence": confidence,
                    "rel_id": rel.get("id", ""),
                },
            )
            count += 1

        # Link relationship to source documents
        sources = rel.get("sources", [])
        if isinstance(rel.get("source"), str):
            sources = [rel["source"]]
        for source_id in sources:
            # Try to match by doc_id pattern
            session.run(
                """
                MATCH (d:Document)
                WHERE d.doc_id STARTS WITH $source_prefix
                WITH d LIMIT 1
                MATCH (c:Concept {name: $concept_name})
                MERGE (c)-[:CITED_IN]->(d)
                """,
                {
                    "source_prefix": source_id.split("_")[0] if "_" in source_id else source_id,
                    "concept_name": rel.get("object", "").replace("_", " ").title(),
                },
            )

    print(f"  Curated relationships: {count} merged.")
    return count


# ---------------------------------------------------------------------------
# 6. Cross-domain links (habitat-MPA, habitat-service, framework-MPA, etc.)
# ---------------------------------------------------------------------------
def _populate_cross_domain_links(session):
    """Create the structural relationships that connect entity types."""
    count = 0

    # Cabo Pulmo HAS_HABITAT coral_reef (primary habitat)
    session.run(
        """
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MATCH (h:Habitat {habitat_id: "coral_reef"})
        MERGE (m)-[:HAS_HABITAT]->(h)
        """
    )
    count += 1

    # Habitats PROVIDES ecosystem services (global relationships)
    habitat_service_links = [
        ("coral_reef", "flood_protection_coral", "Wave energy dissipation at reef crest (97%)"),
        ("coral_reef", "cabo_pulmo_tourism", "Reef biodiversity drives dive tourism"),
        ("coral_reef", "cabo_pulmo_coastal_protection", "Reef structure attenuates wave energy"),
    ]
    for hab_id, svc_id, mechanism in habitat_service_links:
        session.run(
            """
            MATCH (h:Habitat {habitat_id: $hab_id})
            MATCH (es:EcosystemService {service_id: $svc_id})
            MERGE (h)-[r:PROVIDES]->(es)
            SET r.mechanism = $mechanism
            """,
            {"hab_id": hab_id, "svc_id": svc_id, "mechanism": mechanism},
        )
        count += 1

    # Species INHABITS Habitat
    session.run(
        """
        MATCH (s:Species)
        MATCH (h:Habitat {habitat_id: "coral_reef"})
        MERGE (s)-[:INHABITS]->(h)
        """
    )
    count += 1

    # NEOLI Concept DETERMINES MPA effectiveness
    session.run(
        """
        MATCH (c:Concept {name: "NEOLI Criteria"})
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MERGE (c)-[r:ASSESSED_BY]->(m)
        SET r.score = 4,
            r.rating = "4/5 criteria met"
        """
    )
    count += 1

    # Framework APPLICABLE_TO MPA assessments
    session.run(
        """
        MATCH (fw:Framework {framework_id: "tnfd_leap"})
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MERGE (fw)-[r:APPLICABLE_TO]->(m)
        SET r.alignment = "anticipates alignment with TNFD LEAP"
        """
    )
    count += 1

    session.run(
        """
        MATCH (fw:Framework {framework_id: "seea_ecosystem_accounting"})
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MERGE (fw)-[r:APPLICABLE_TO]->(m)
        SET r.alignment = "ESV methodology aligned with SEEA EA"
        """
    )
    count += 1

    # Financial instruments APPLICABLE_TO marine conservation
    session.run(
        """
        MATCH (fi:FinancialInstrument {instrument_id: "blue_bond"})
        MATCH (m:MPA {name: "Cabo Pulmo National Park"})
        MERGE (fi)-[r:APPLICABLE_TO]->(m)
        SET r.mechanism = "Debt instrument for marine sustainability projects"
        """
    )
    count += 1

    session.run(
        """
        MATCH (fi:FinancialInstrument {instrument_id: "parametric_reef_insurance"})
        MATCH (h:Habitat {habitat_id: "coral_reef"})
        MERGE (fi)-[r:PROTECTS]->(h)
        SET r.mechanism = "Wind speed triggered insurance for rapid reef restoration"
        """
    )
    count += 1

    # Framework GOVERNS FinancialInstrument
    session.run(
        """
        MATCH (fw:Framework {framework_id: "tnfd_leap"})
        MATCH (fi:FinancialInstrument {instrument_id: "blue_bond"})
        MERGE (fw)-[r:GOVERNS]->(fi)
        SET r.mechanism = "TNFD disclosure framework for blue finance instruments"
        """
    )
    count += 1

    # Link comparison MPAs to habitats
    session.run(
        """
        MATCH (m:MPA {name: "Great Barrier Reef Marine Park"})
        MATCH (h:Habitat {habitat_id: "coral_reef"})
        MERGE (m)-[:HAS_HABITAT]->(h)
        """
    )
    count += 1

    print(f"  Cross-domain links: {count} merged.")
    return count


# ---------------------------------------------------------------------------
# 7. Comparison MPA sites
# ---------------------------------------------------------------------------
def _populate_comparison_sites(session):
    """Add comparison MPA sites for the demo."""
    sites = [
        {
            "name": "Great Barrier Reef Marine Park",
            "country": "Australia",
            "area_km2": 344400,
            "designation_year": 1975,
            "neoli_score": 3,
            "biomass_ratio": 1.8,
            "asset_rating": "A",
        },
        {
            "name": "Papah\u0101naumoku\u0101kea Marine National Monument",
            "country": "United States",
            "area_km2": 1510000,
            "designation_year": 2006,
            "neoli_score": 5,
            "biomass_ratio": 3.2,
            "asset_rating": "AA",
        },
    ]
    for s in sites:
        session.run(
            """
            MERGE (m:MPA {name: $name})
            SET m.country          = $country,
                m.area_km2         = $area_km2,
                m.designation_year = $designation_year,
                m.neoli_score      = $neoli_score,
                m.biomass_ratio    = $biomass_ratio,
                m.asset_rating     = $asset_rating
            """,
            s,
        )
    print(f"  Comparison sites: {len(sites)} merged.")
    return len(sites)


# ---------------------------------------------------------------------------
# 8. Provenance edges from case study
# ---------------------------------------------------------------------------
def _populate_provenance(session, cfg):
    """Create DERIVED_FROM edges linking MPA to source documents."""
    cs = _load_json(cfg.case_study_path)
    count = 0
    for src in cs.get("provenance", {}).get("data_sources", []):
        doi = src.get("doi", "")
        # Skip placeholder DOIs
        if not doi or "xxxx" in doi:
            continue
        session.run(
            """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})
            MERGE (d:Document {doi: $doi})
            MERGE (m)-[r:DERIVED_FROM]->(d)
            SET r.data_type   = $data_type,
                r.access_date = $access_date
            """,
            {
                "doi": doi,
                "data_type": src.get("data_type", ""),
                "access_date": src.get("access_date", ""),
            },
        )
        count += 1

    # Also link to key provenance documents from case study sources
    neoli_doi = cs.get("neoli_assessment", {}).get("source", {}).get("doi", "")
    if neoli_doi:
        session.run(
            """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})
            MERGE (d:Document {doi: $doi})
            MERGE (m)-[r:DERIVED_FROM]->(d)
            SET r.data_type = "NEOLI assessment"
            """,
            {"doi": neoli_doi},
        )
        count += 1

    recovery_doi = cs.get("ecological_recovery", {}).get("source", {}).get("doi", "")
    if recovery_doi:
        session.run(
            """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})
            MERGE (d:Document {doi: $doi})
            MERGE (m)-[r:DERIVED_FROM]->(d)
            SET r.data_type = "Recovery field data"
            """,
            {"doi": recovery_doi},
        )
        count += 1

    print(f"  Provenance edges: {count} merged.")
    return count


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def populate_graph():
    """Run the full population pipeline. Idempotent via MERGE."""
    cfg = get_config()
    driver = get_driver()

    print("Populating Neo4j graph from curated data assets...")
    print("=" * 60)

    with driver.session(database=cfg.neo4j_database) as session:
        total = 0
        total += _populate_documents(session, cfg)
        total += _populate_entities(session, cfg)
        total += _populate_cabo_pulmo(session, cfg)
        total += _populate_shark_bay(session, cfg)
        total += _populate_bridge_axioms(session, cfg)
        total += _populate_comparison_sites(session)
        total += _populate_relationships(session, cfg)
        total += _populate_cross_domain_links(session)
        total += _populate_provenance(session, cfg)

    print("=" * 60)
    print(f"Population complete. ~{total} operations executed.")
    return total
