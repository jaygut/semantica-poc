"""
Populate Neo4j graph from existing curated data assets.

Sources:
  1. data/semantica_export/entities.jsonld        - 14 entities
  2. data/semantica_export/relationships.json      - 15 relationships
  3. data/semantica_export/bridge_axioms.json      - 12 axioms
  4. data/semantica_export/document_corpus.json    - 195 doc metadata
  5. examples/cabo_pulmo_case_study.json           - Full site data
  6. schemas/bridge_axiom_templates.json           - Axiom coefficients

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
# 1. Document nodes (from registry + corpus)
# ---------------------------------------------------------------------------
def _populate_documents(session, cfg):
    """Create Document nodes from the document registry."""
    registry_path = cfg.registry_path
    if not registry_path.exists():
        print("  WARNING: document registry not found, skipping documents.")
        return 0

    registry = _load_json(registry_path)
    docs = registry.get("documents", [])
    count = 0
    for doc in docs:
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
                "doc_id": doc.get("id", ""),
            },
        )
        count += 1
    print(f"  Documents: {count} merged.")
    return count


# ---------------------------------------------------------------------------
# 2. Species, Habitat, Framework, Concept, FinancialInstrument nodes
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
            m.total_esv_usd    = $total_esv
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
            "measurement_year": cs.get("ecological_recovery", {}).get("assessment_year", 2009),
            "asset_rating": rating.get("rating", "AAA"),
            "asset_score": rating.get("composite_score", 0.90),
            "total_esv": cs.get("ecosystem_services", {}).get("total_annual_value_usd", 29270000),
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

    # Create trophic links from food web
    trophic = cs.get("trophic_network", {})
    for edge in trophic.get("edges", []):
        session.run(
            """
            MERGE (a:TrophicNode {node_id: $from_id})
            MERGE (b:TrophicNode {node_id: $to_id})
            MERGE (a)-[:PREYS_ON]->(b)
            """,
            {"from_id": edge.get("from", ""), "to_id": edge.get("to", "")},
        )

    print(f"  Cabo Pulmo enrichment: {count} nodes/edges merged.")
    return count


# ---------------------------------------------------------------------------
# 4. Bridge Axiom nodes
# ---------------------------------------------------------------------------
def _populate_bridge_axioms(session, cfg):
    """Create BridgeAxiom nodes from templates + export, link to evidence Documents."""
    templates = _load_json(cfg.schemas_dir / "bridge_axiom_templates.json")
    export = _load_json(cfg.export_dir / "bridge_axioms.json")

    # Build a lookup from export for extra fields
    export_lookup = {a["axiom_id"]: a for a in export.get("bridge_axioms", [])}
    count = 0

    for axiom in templates.get("axioms", []):
        aid = axiom["axiom_id"]
        export_ax = export_lookup.get(aid, {})

        # Serialize coefficients as JSON string for storage
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
                a.confidence          = $confidence
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
            },
        )
        count += 1

        # Link axiom -> EVIDENCED_BY -> Document (by DOI)
        sources = axiom.get("sources", [])
        for src in sources:
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

        # Link axiom -> APPLIES_TO -> MPA (Cabo Pulmo for applicable axioms)
        if aid in ("BA-001", "BA-002", "BA-004", "BA-011", "BA-012"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $axiom_id})
                MATCH (m:MPA {name: "Cabo Pulmo National Park"})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"axiom_id": aid},
            )

        # Link axiom -> TRANSLATES -> EcosystemService (where applicable)
        svc_map = {
            "BA-001": "cabo_pulmo_tourism",
            "BA-002": None,
            "BA-004": "cabo_pulmo_coastal_protection",
            "BA-006": "cabo_pulmo_fisheries_spillover",
            "BA-008": "cabo_pulmo_carbon_sequestration",
            "BA-012": "cabo_pulmo_fisheries_spillover",
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

    print(f"  BridgeAxioms: {count} merged with evidence links.")
    return count


# ---------------------------------------------------------------------------
# 5. Comparison MPA sites (lightweight)
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
# 6. Provenance edges from case study
# ---------------------------------------------------------------------------
def _populate_provenance(session, cfg):
    """Create DERIVED_FROM edges linking MPA to source documents."""
    cs = _load_json(cfg.case_study_path)
    count = 0
    for src in cs.get("provenance", {}).get("data_sources", []):
        doi = src.get("doi", "")
        if doi:
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
        total += _populate_bridge_axioms(session, cfg)
        total += _populate_comparison_sites(session)
        total += _populate_provenance(session, cfg)

    print("=" * 60)
    print(f"Population complete. ~{total} operations executed.")
    return total
