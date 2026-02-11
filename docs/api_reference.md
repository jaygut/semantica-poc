# MARIS API Reference

## Overview

The MARIS API is a FastAPI server that exposes the Neo4j knowledge graph through a natural-language query pipeline. All endpoints are prefixed with `/api`.

**Base URL:** `http://localhost:8000`

## Endpoints

### Health

#### `GET /api/health`

Returns system status including Neo4j connectivity, LLM availability, and graph statistics.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "llm_available": true,
  "graph_stats": {
    "node_count": 878,
    "edge_count": 101,
    "node_types": {"MPA": 3, "EcosystemService": 12, "BridgeAxiom": 12, ...}
  }
}
```

### Query

#### `POST /api/query`

Classify a natural-language question, execute the appropriate Cypher template, and return a grounded answer with provenance.

**Request body:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `question` | string | required | Natural-language question |
| `site` | string | null | Optional site name override (auto-extracted from question if omitted) |
| `include_graph_path` | bool | false | Include structured provenance edges for graph visualization |
| `max_evidence_sources` | int | 5 | Maximum evidence items to return |

**Example:**
```json
{
  "question": "What is Cabo Pulmo worth?",
  "site": "Cabo Pulmo National Park",
  "include_graph_path": true,
  "max_evidence_sources": 3
}
```

**Response:**
```json
{
  "answer": "Cabo Pulmo National Park generates an estimated $29.27M...",
  "confidence": 0.85,
  "evidence": [
    {
      "doi": "10.1371/journal.pone.0023601",
      "title": "Large Recovery of Fish Biomass...",
      "year": 2011,
      "tier": "T1",
      "page_ref": null,
      "quote": null
    }
  ],
  "axioms_used": ["BA-001", "BA-002"],
  "graph_path": [
    {
      "from_node": "Cabo Pulmo National Park",
      "from_type": "MPA",
      "relationship": "GENERATES",
      "to_node": "Tourism",
      "to_type": "EcosystemService"
    }
  ],
  "caveats": ["Single-site study..."],
  "query_metadata": {
    "category": "site_valuation",
    "classification_confidence": 0.75,
    "template_used": "site_valuation",
    "response_time_ms": 2340
  }
}
```

### Site

#### `GET /api/site/{site_name}`

Retrieve structured data for a specific MPA.

**Response (`SiteResponse`):**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Site name |
| `area_km2` | float | Protected area size |
| `designation_year` | int | Year of MPA designation |
| `esv_usd` | float | Annual ecosystem service value |
| `biomass_ratio` | float | Biomass recovery ratio |
| `neoli_score` | int | NEOLI alignment score (0-5) |
| `asset_rating` | string | Investment rating (e.g. "AA") |
| `services` | list | Ecosystem service breakdown |

### Axiom

#### `GET /api/axiom/{axiom_id}`

Retrieve details for a specific bridge axiom.

**Response (`AxiomResponse`):**
| Field | Type | Description |
|-------|------|-------------|
| `axiom_id` | string | Axiom identifier (e.g. "BA-001") |
| `name` | string | Human-readable name |
| `category` | string | Domain category |
| `description` | string | Plain-English explanation |
| `coefficients` | dict | Translation coefficients |
| `evidence` | list | Supporting DOI citations |
| `applicable_sites` | list | Sites where this axiom applies |

### Compare

#### `POST /api/compare`

Compare multiple MPA sites side by side.

**Request body:**
```json
{
  "site_names": ["Cabo Pulmo National Park", "Papahanaumokuakea"]
}
```

**Response (`CompareResponse`):**
```json
{
  "sites": [
    {"name": "Cabo Pulmo National Park", "esv_usd": 29270000, "biomass_ratio": 4.63, "neoli_score": 4},
    {"name": "Papahanaumokuakea", "esv_usd": null, "biomass_ratio": null, "neoli_score": 5}
  ]
}
```

### Graph Traversal

#### `POST /api/graph/traverse`

Traverse the knowledge graph from a starting node.

**Request body:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `start_name` | string | required | Name of the starting node |
| `max_hops` | int | 3 | Maximum traversal depth |
| `result_limit` | int | 50 | Maximum paths to return |

#### `GET /api/graph/node/{element_id}`

Retrieve properties and relationships for a specific node by its Neo4j element ID.

## Query Categories

The classifier maps natural-language questions into one of five categories, each backed by a Cypher template:

| Category | Triggers | What It Returns |
|----------|----------|-----------------|
| `site_valuation` | "value", "worth", "ESV", "asset rating" | MPA metadata, services, axioms, evidence |
| `provenance_drilldown` | "evidence", "provenance", "DOI", "source" | Documentation chain from MPA to sources (1-4 hops) |
| `axiom_explanation` | "bridge axiom", "BA-001", "coefficient" | Axiom details, evidence, applicable sites, translated services |
| `comparison` | "compare", "versus", "rank", "benchmark" | Side-by-side MPA metrics (ESV, biomass, NEOLI) |
| `risk_assessment` | "risk", "degradation", "climate", "threat" | Ecological-to-service axioms, risk factors |

## Graph Schema

### Node Labels

| Label | Key Properties | Description |
|-------|----------------|-------------|
| `MPA` | name, area_km2, designation_year, neoli_score, esv_usd | Marine Protected Area |
| `EcosystemService` | service_name, value_usd, method | Valued ecosystem service |
| `BridgeAxiom` | axiom_id, name, category, description | Ecological-to-financial translation rule |
| `Document` | doi, title, year, tier | Peer-reviewed evidence source |
| `Habitat` | name, condition | Marine habitat type |
| `Species` | name, common_name, role | Marine species |

### Relationship Types

| Relationship | From | To | Description |
|-------------|------|----|-------------|
| `GENERATES` | MPA | EcosystemService | MPA produces this service |
| `APPLIES_TO` | BridgeAxiom | MPA | Axiom is relevant to this site |
| `TRANSLATES` | BridgeAxiom | EcosystemService | Axiom converts ecology to this service value |
| `EVIDENCED_BY` | BridgeAxiom | Document | Axiom is backed by this citation |
| `HAS_HABITAT` | MPA | Habitat | MPA contains this habitat type |

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (e.g. missing required site name) |
| 500 | Internal error (e.g. Neo4j unreachable, Cypher execution failed) |

Error responses include a `detail` field with a human-readable message.

## Configuration

The API reads all settings from environment variables. See `.env.example` for the full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIS_API_HOST` | 0.0.0.0 | API bind address |
| `MARIS_API_PORT` | 8000 | API port |
| `MARIS_NEO4J_URI` | bolt://localhost:7687 | Neo4j connection URI |
| `MARIS_LLM_PROVIDER` | deepseek | LLM provider (deepseek, anthropic, openai) |
| `MARIS_LLM_API_KEY` | - | LLM API key (required) |
| `MARIS_DEMO_MODE` | false | Use precomputed responses instead of live LLM |
