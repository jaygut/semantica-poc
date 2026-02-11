"""Neo4j schema definitions - constraints, indexes, and vector indexes."""

from maris.graph.connection import get_driver, get_config

# Each statement is executed individually (Neo4j requires separate transactions for DDL).
SCHEMA_STATEMENTS = [
    # ===== NODE CONSTRAINTS =====
    "CREATE CONSTRAINT species_worms_id IF NOT EXISTS FOR (s:Species) REQUIRE s.worms_id IS UNIQUE",
    "CREATE CONSTRAINT document_doi IF NOT EXISTS FOR (d:Document) REQUIRE d.doi IS UNIQUE",
    "CREATE CONSTRAINT mpa_name IF NOT EXISTS FOR (m:MPA) REQUIRE m.name IS UNIQUE",
    "CREATE CONSTRAINT axiom_id IF NOT EXISTS FOR (a:BridgeAxiom) REQUIRE a.axiom_id IS UNIQUE",
    "CREATE CONSTRAINT habitat_id IF NOT EXISTS FOR (h:Habitat) REQUIRE h.habitat_id IS UNIQUE",
    "CREATE CONSTRAINT service_id IF NOT EXISTS FOR (es:EcosystemService) REQUIRE es.service_id IS UNIQUE",
    "CREATE CONSTRAINT instrument_id IF NOT EXISTS FOR (fi:FinancialInstrument) REQUIRE fi.instrument_id IS UNIQUE",
    "CREATE CONSTRAINT framework_id IF NOT EXISTS FOR (fw:Framework) REQUIRE fw.framework_id IS UNIQUE",

    # ===== INDEXES =====
    "CREATE INDEX document_tier IF NOT EXISTS FOR (d:Document) ON (d.source_tier)",
    "CREATE INDEX species_name IF NOT EXISTS FOR (s:Species) ON (s.scientific_name)",
    "CREATE INDEX mpa_neoli IF NOT EXISTS FOR (m:MPA) ON (m.neoli_score)",

    # ===== FULLTEXT INDEX =====
    "CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.abstract, d.title]",
]


def ensure_schema():
    """Create all constraints and indexes (idempotent)."""
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        for stmt in SCHEMA_STATEMENTS:
            try:
                session.run(stmt)
            except Exception as e:
                # Some older Neo4j versions may not support IF NOT EXISTS for all types
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    continue
                raise
    print(f"Schema applied: {len(SCHEMA_STATEMENTS)} statements executed.")
