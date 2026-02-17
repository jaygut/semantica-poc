"""Service for loading Concept JSONs into Neo4j."""

import json
from pathlib import Path

from neo4j import Session

from maris.settings import settings
from maris.services.ingestion.case_study_loader import HABITAT_IDS


class ConceptsLoader:
    """Service to load domain concepts into the Graph."""

    def __init__(self, session: Session):
        self.session = session

    def load_concepts(self) -> int:
        """Populate Concept nodes and their relationships from concepts.json.
        
        Returns:
            Number of operations/nodes merged.
        """
        concepts_path = settings.export_dir / "concepts.json"
        if not concepts_path.exists():
            print("  WARNING: concepts.json not found, skipping concept population.")
            return 0

        try:
            with open(concepts_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading {concepts_path}: {e}")
            return 0

        count = 0
        for concept in data.get("concepts", []):
            concept_id = concept.get("concept_id", "")
            if not concept_id:
                continue

            # Merge Concept node
            self.session.run(
                """
                MERGE (c:Concept {concept_id: $concept_id})
                SET c.name = $name,
                    c.description = $description,
                    c.domain = $domain,
                    c.applicable_habitats = $habitats
                """,
                {
                    "concept_id": concept_id,
                    "name": concept.get("name", ""),
                    "description": concept.get("description", ""),
                    "domain": concept.get("domain", ""),
                    "habitats": concept.get("applicable_habitats", []),
                },
            )
            count += 1

            # INVOLVES_AXIOM edges
            for axiom_id in concept.get("involved_axiom_ids", []):
                self.session.run(
                    """
                    MATCH (c:Concept {concept_id: $concept_id})
                    MATCH (ba:BridgeAxiom {axiom_id: $axiom_id})
                    MERGE (c)-[:INVOLVES_AXIOM]->(ba)
                    """,
                    {"concept_id": concept_id, "axiom_id": axiom_id},
                )
                count += 1

            # RELEVANT_TO habitat edges
            for habitat in concept.get("applicable_habitats", []):
                hab_id = HABITAT_IDS.get(habitat, habitat)
                self.session.run(
                    """
                    MATCH (c:Concept {concept_id: $concept_id})
                    MATCH (h:Habitat {habitat_id: $hab_id})
                    MERGE (c)-[:RELEVANT_TO]->(h)
                    """,
                    {"concept_id": concept_id, "hab_id": hab_id},
                )
                count += 1

            # DOCUMENTED_BY edges
            for doi in concept.get("key_document_dois", []):
                if doi:
                    self.session.run(
                        """
                        MATCH (c:Concept {concept_id: $concept_id})
                        MATCH (d:Document {doi: $doi})
                        MERGE (c)-[:DOCUMENTED_BY]->(d)
                        """,
                        {"concept_id": concept_id, "doi": doi},
                    )
                    count += 1

        print(f"  Concepts: {count} nodes/edges merged.")
        return count
