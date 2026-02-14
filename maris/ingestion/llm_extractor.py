"""LLM-powered entity and relationship extraction using OpenAI-compatible API."""

import json
import logging
import re

from openai import OpenAI

from maris.config import MARISConfig

logger = logging.getLogger(__name__)

ENTITY_PROMPT = """You are a marine ecology knowledge extraction system. Extract structured entities from the following scientific text passage.

PASSAGE (from "{paper_title}", DOI: {doi}, page {page_num}):
---
{chunk_text}
---

Extract entities matching these types ONLY if clearly stated in the text:
1. Species: scientific_name, common_name, trophic_level, functional_group
2. Habitat: habitat_type (coral_reef|mangrove|seagrass|kelp_forest|rocky_reef|pelagic), extent, condition
3. MPA: name, country, area_km2, designation_year, protection_level
4. EcosystemService: service_type (tourism|fisheries|carbon|protection|cultural), value_usd, valuation_method
5. Measurement: metric_name, value, unit, confidence_interval, year

For each entity, provide:
- "confidence": 0.0-1.0 (how certain is this extraction?)
- "page_ref": exact page reference
- "supporting_quote": verbatim quote from text (max 200 chars)

Return ONLY a JSON array. Do NOT infer or hallucinate values not in the text. If no entities are found, return []."""

RELATIONSHIP_PROMPT = """You are a marine ecology knowledge extraction system. Given the following entities extracted from a scientific text passage, identify relationships between them.

PASSAGE (from "{paper_title}", DOI: {doi}, page {page_num}):
---
{chunk_text}
---

EXTRACTED ENTITIES:
{entities_json}

Identify relationships of these types ONLY if clearly supported by the text:
1. INHABITS: Species -> Habitat
2. LOCATED_IN: Species/Habitat -> MPA
3. GENERATES: MPA/Habitat -> EcosystemService
4. PREYS_ON: Species -> Species
5. COMPETES_WITH: Species -> Species
6. MEASURED_AT: Measurement -> MPA/Habitat/Species
7. PROTECTS: MPA -> Habitat/Species
8. DERIVED_FROM: any -> Document (provenance)

For each relationship, provide:
- "source": entity identifier (name or scientific_name)
- "target": entity identifier
- "relationship_type": one of the types above
- "confidence": 0.0-1.0
- "supporting_quote": verbatim quote from text (max 200 chars)
- "properties": dict of any additional edge attributes

Return ONLY a JSON array. Do NOT infer relationships not clearly stated. If none found, return []."""


def _parse_json_from_response(text: str) -> list[dict]:
    """Extract a JSON array from an LLM response, handling markdown fences."""
    text = text.strip()

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find the outermost JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM JSON response: %s", e)
        return []


class LLMExtractor:
    """Extract entities and relationships from text chunks using an LLM."""

    def __init__(self, config: MARISConfig, provenance_manager=None):
        self.config = config
        self.client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )
        self.model = config.llm_model
        self.threshold = config.extraction_confidence_threshold
        self._provenance = provenance_manager

    def extract_entities(self, chunk: dict, paper_meta: dict) -> list[dict]:
        """Extract entities from a single chunk.

        Args:
            chunk: Dict with "text", "page_start", "page_end" from chunk_pages().
            paper_meta: Dict with "title", "doi".

        Returns:
            List of entity dicts that pass the confidence threshold.
        """
        prompt = ENTITY_PROMPT.format(
            paper_title=paper_meta.get("title", "Unknown"),
            doi=paper_meta.get("doi", "Unknown"),
            page_num=f"{chunk['page_start']}-{chunk['page_end']}",
            chunk_text=chunk["text"],
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=self.config.llm_max_tokens,
                timeout=self.config.llm_timeout,
            )
            raw = response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM entity extraction failed for chunk %s: %s", chunk.get("chunk_id"), e)
            return []

        entities = _parse_json_from_response(raw)

        # Filter by confidence and attach provenance
        results = []
        for ent in entities:
            confidence = float(ent.get("confidence", 0))
            if confidence < self.threshold:
                continue
            ent["_source_doi"] = paper_meta.get("doi", "")
            ent["_source_title"] = paper_meta.get("title", "")
            ent["_chunk_id"] = chunk.get("chunk_id")
            ent["_page_start"] = chunk["page_start"]
            ent["_page_end"] = chunk["page_end"]
            results.append(ent)

            # Track in provenance system if available
            if self._provenance is not None:
                ent_name = ent.get("scientific_name") or ent.get("name") or ent.get("metric_name") or "unknown"
                ent_type = ent.get("type", "Entity")
                entity_id = f"extracted:{ent_type}:{ent_name}:{chunk.get('chunk_id', '')}"
                self._provenance.track_extraction(
                    entity_id=entity_id,
                    entity_type=ent_type,
                    source_doi=paper_meta.get("doi", ""),
                    attributes={
                        "name": ent_name,
                        "confidence": confidence,
                        "page_start": chunk["page_start"],
                        "page_end": chunk["page_end"],
                    },
                )

        return results

    def extract_relationships(
        self, entities: list[dict], chunk: dict, paper_meta: dict
    ) -> list[dict]:
        """Extract relationships given entities and the source chunk.

        Args:
            entities: Entities previously extracted from this chunk.
            chunk: The source chunk dict.
            paper_meta: Dict with "title", "doi".

        Returns:
            List of relationship dicts that pass the confidence threshold.
        """
        if not entities:
            return []

        # Build a compact representation of entities for the prompt
        entities_summary = []
        for ent in entities:
            summary = {k: v for k, v in ent.items() if not k.startswith("_")}
            entities_summary.append(summary)

        prompt = RELATIONSHIP_PROMPT.format(
            paper_title=paper_meta.get("title", "Unknown"),
            doi=paper_meta.get("doi", "Unknown"),
            page_num=f"{chunk['page_start']}-{chunk['page_end']}",
            chunk_text=chunk["text"],
            entities_json=json.dumps(entities_summary, indent=2),
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=self.config.llm_max_tokens,
                timeout=self.config.llm_timeout,
            )
            raw = response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM relationship extraction failed for chunk %s: %s", chunk.get("chunk_id"), e)
            return []

        relationships = _parse_json_from_response(raw)

        # Filter by confidence and attach provenance
        results = []
        for rel in relationships:
            confidence = float(rel.get("confidence", 0))
            if confidence < self.threshold:
                continue
            rel["_source_doi"] = paper_meta.get("doi", "")
            rel["_source_title"] = paper_meta.get("title", "")
            rel["_chunk_id"] = chunk.get("chunk_id")
            results.append(rel)

        return results
