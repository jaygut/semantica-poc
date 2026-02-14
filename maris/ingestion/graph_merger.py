"""Deduplication, reconciliation, and Neo4j merge for extracted entities and relationships."""

import logging

from maris.config import MARISConfig
from maris.graph.connection import run_write

logger = logging.getLogger(__name__)

# Cypher templates for MERGE-based idempotent upserts.
# Each extracted entity gets a DERIVED_FROM edge to its source Document.

_MERGE_SPECIES = """
MERGE (s:Species {scientific_name: $scientific_name})
SET s.common_name      = coalesce($common_name, s.common_name),
    s.trophic_level    = coalesce($trophic_level, s.trophic_level),
    s.functional_group = coalesce($functional_group, s.functional_group),
    s.worms_id         = coalesce($worms_id, s.worms_id)
WITH s
MERGE (d:Document {doi: $source_doi})
MERGE (s)-[r:DERIVED_FROM]->(d)
SET r.page_ref         = $page_ref,
    r.supporting_quote = $supporting_quote,
    r.confidence       = $confidence
"""

_MERGE_HABITAT = """
MERGE (h:Habitat {habitat_id: $habitat_id})
SET h.habitat_type = coalesce($habitat_type, h.habitat_type),
    h.extent       = coalesce($extent, h.extent),
    h.condition    = coalesce($condition, h.condition),
    h.name         = coalesce($name, h.name)
WITH h
MERGE (d:Document {doi: $source_doi})
MERGE (h)-[r:DERIVED_FROM]->(d)
SET r.page_ref         = $page_ref,
    r.supporting_quote = $supporting_quote,
    r.confidence       = $confidence
"""

_MERGE_MPA = """
MERGE (m:MPA {name: $name})
SET m.country          = coalesce($country, m.country),
    m.area_km2         = coalesce($area_km2, m.area_km2),
    m.designation_year = coalesce($designation_year, m.designation_year),
    m.protection_level = coalesce($protection_level, m.protection_level)
WITH m
MERGE (d:Document {doi: $source_doi})
MERGE (m)-[r:DERIVED_FROM]->(d)
SET r.page_ref         = $page_ref,
    r.supporting_quote = $supporting_quote,
    r.confidence       = $confidence
"""

_MERGE_ECOSYSTEM_SERVICE = """
MERGE (es:EcosystemService {service_id: $service_id})
SET es.service_type     = coalesce($service_type, es.service_type),
    es.service_name     = coalesce($service_name, es.service_name),
    es.annual_value_usd = coalesce($value_usd, es.annual_value_usd),
    es.valuation_method = coalesce($valuation_method, es.valuation_method)
WITH es
MERGE (d:Document {doi: $source_doi})
MERGE (es)-[r:DERIVED_FROM]->(d)
SET r.page_ref         = $page_ref,
    r.supporting_quote = $supporting_quote,
    r.confidence       = $confidence
"""

_MERGE_MEASUREMENT = """
MERGE (meas:Measurement {measurement_id: $measurement_id})
SET meas.metric_name         = $metric_name,
    meas.value               = $value,
    meas.unit                = $unit,
    meas.confidence_interval = $confidence_interval,
    meas.year                = $year
WITH meas
MERGE (d:Document {doi: $source_doi})
MERGE (meas)-[r:DERIVED_FROM]->(d)
SET r.page_ref         = $page_ref,
    r.supporting_quote = $supporting_quote,
    r.confidence       = $confidence
"""

# Valid relationship types for merge
_VALID_REL_TYPES = {
    "INHABITS", "LOCATED_IN", "GENERATES", "PREYS_ON",
    "COMPETES_WITH", "MEASURED_AT", "PROTECTS", "DERIVED_FROM",
}


def _normalize_name(name: str) -> str:
    """Normalize entity names for deduplication."""
    return name.strip().lower().replace("  ", " ")


def _build_habitat_id(ent: dict) -> str:
    """Generate a stable habitat_id from entity attributes."""
    htype = ent.get("habitat_type", "unknown")
    name = ent.get("name", ent.get("habitat_type", "unknown"))
    return _normalize_name(f"{htype}_{name}").replace(" ", "_")


def _build_service_id(ent: dict) -> str:
    """Generate a stable service_id from entity attributes."""
    stype = ent.get("service_type", "unknown")
    return _normalize_name(stype).replace(" ", "_")


def _build_measurement_id(ent: dict) -> str:
    """Generate a stable measurement_id from entity attributes."""
    metric = ent.get("metric_name", "unknown")
    year = ent.get("year", "")
    return _normalize_name(f"{metric}_{year}").replace(" ", "_")


class GraphMerger:
    """Merge extracted entities and relationships into Neo4j."""

    def __init__(self, config: MARISConfig):
        self.config = config
        self._entity_counts: dict[str, int] = {}
        self._rel_count: int = 0

    def _provenance_params(self, ent: dict) -> dict:
        """Extract common provenance parameters from an entity."""
        page_start = ent.get("_page_start", ent.get("page_ref", ""))
        page_end = ent.get("_page_end", "")
        page_ref = f"{page_start}-{page_end}" if page_end else str(page_start)
        return {
            "source_doi": ent.get("_source_doi", ""),
            "page_ref": page_ref,
            "supporting_quote": ent.get("supporting_quote", "")[:200],
            "confidence": float(ent.get("confidence", 0)),
        }

    def merge_entities(self, entities: list[dict]) -> dict[str, int]:
        """MERGE each entity into Neo4j by type, with DERIVED_FROM provenance.

        Returns:
            Dict of {entity_type: count} merged.
        """
        counts: dict[str, int] = {}

        for ent in entities:
            etype = self._detect_entity_type(ent)
            if not etype:
                logger.warning("Could not determine entity type: %s", ent)
                continue

            try:
                self._merge_entity(etype, ent)
                counts[etype] = counts.get(etype, 0) + 1
            except Exception as e:
                logger.error("Failed to merge %s entity: %s", etype, e)

        self._entity_counts = counts
        return counts

    def merge_relationships(self, relationships: list[dict]) -> int:
        """MERGE relationship edges into Neo4j.

        Returns:
            Number of relationships merged.
        """
        count = 0
        for rel in relationships:
            rel_type = rel.get("relationship_type", "").upper().replace(" ", "_")
            if rel_type not in _VALID_REL_TYPES:
                logger.warning("Skipping invalid relationship type: %s", rel_type)
                continue

            source = rel.get("source", "")
            target = rel.get("target", "")
            if not source or not target:
                continue

            confidence = float(rel.get("confidence", 0))
            quote = rel.get("supporting_quote", "")[:200]
            source_doi = rel.get("_source_doi", "")

            # Use a generic merge pattern: match nodes by name/scientific_name
            # and create the typed relationship
            cypher = f"""
            OPTIONAL MATCH (a) WHERE a.name = $source OR a.scientific_name = $source
              OR a.service_id = $source OR a.habitat_id = $source OR a.metric_name = $source
            WITH a WHERE a IS NOT NULL
            LIMIT 1
            OPTIONAL MATCH (b) WHERE b.name = $target OR b.scientific_name = $target
              OR b.service_id = $target OR b.habitat_id = $target OR b.metric_name = $target
            WITH a, b WHERE b IS NOT NULL
            LIMIT 1
            MERGE (a)-[r:{rel_type}]->(b)
            SET r.confidence       = $confidence,
                r.supporting_quote = $quote,
                r.source_doi       = $source_doi
            """

            try:
                run_write(cypher, {
                    "source": source,
                    "target": target,
                    "confidence": confidence,
                    "quote": quote,
                    "source_doi": source_doi,
                })
                count += 1
            except Exception as e:
                logger.error("Failed to merge relationship %s->%s (%s): %s", source, target, rel_type, e)

        self._rel_count = count
        return count

    def _detect_entity_type(self, ent: dict) -> str | None:
        """Detect entity type from extracted dict keys."""
        # Explicit type field
        etype = ent.get("type", ent.get("entity_type", ""))
        if etype:
            return etype

        # Heuristic detection
        if "scientific_name" in ent:
            return "Species"
        if "habitat_type" in ent:
            return "Habitat"
        if "protection_level" in ent or ("name" in ent and "area_km2" in ent):
            return "MPA"
        if "service_type" in ent:
            return "EcosystemService"
        if "metric_name" in ent:
            return "Measurement"
        return None

    def _merge_entity(self, etype: str, ent: dict) -> None:
        """Dispatch to the correct MERGE Cypher based on entity type."""
        prov = self._provenance_params(ent)

        if etype == "Species":
            run_write(_MERGE_SPECIES, {
                "scientific_name": ent.get("scientific_name", "Unknown"),
                "common_name": ent.get("common_name"),
                "trophic_level": ent.get("trophic_level"),
                "functional_group": ent.get("functional_group"),
                "worms_id": ent.get("worms_id"),
                **prov,
            })

        elif etype == "Habitat":
            run_write(_MERGE_HABITAT, {
                "habitat_id": _build_habitat_id(ent),
                "habitat_type": ent.get("habitat_type"),
                "extent": ent.get("extent"),
                "condition": ent.get("condition"),
                "name": ent.get("name", ent.get("habitat_type", "")),
                **prov,
            })

        elif etype == "MPA":
            run_write(_MERGE_MPA, {
                "name": ent.get("name", "Unknown MPA"),
                "country": ent.get("country"),
                "area_km2": ent.get("area_km2"),
                "designation_year": ent.get("designation_year"),
                "protection_level": ent.get("protection_level"),
                **prov,
            })

        elif etype == "EcosystemService":
            run_write(_MERGE_ECOSYSTEM_SERVICE, {
                "service_id": _build_service_id(ent),
                "service_type": ent.get("service_type"),
                "service_name": ent.get("service_type", "").replace("_", " ").title(),
                "value_usd": ent.get("value_usd"),
                "valuation_method": ent.get("valuation_method"),
                **prov,
            })

        elif etype == "Measurement":
            run_write(_MERGE_MEASUREMENT, {
                "measurement_id": _build_measurement_id(ent),
                "metric_name": ent.get("metric_name"),
                "value": ent.get("value"),
                "unit": ent.get("unit"),
                "confidence_interval": ent.get("confidence_interval"),
                "year": ent.get("year"),
                **prov,
            })

        else:
            logger.warning("Unknown entity type: %s", etype)

    @property
    def summary(self) -> dict:
        """Return a summary of the last merge operation."""
        return {
            "entities": self._entity_counts,
            "relationships": self._rel_count,
            "total_entities": sum(self._entity_counts.values()),
        }
