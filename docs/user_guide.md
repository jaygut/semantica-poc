# MARIS POC User Guide

TIMELINE: Week 8 (Phase 4: Integration, Testing & Demo via Semantica)
IMPLEMENTATION PRIORITY: Medium - User documentation for completed system

## Overview
This guide explains how to use the MARIS POC system for marine ecological knowledge graph queries. The system is built on **Semantica** for entity extraction, relationship extraction, graph construction, and GraphRAG query execution.

## Installation
- Install Python dependencies from pyproject.toml
- Configure Semantica API connection in config/config.yaml or .env
- Set up graph database (Semantica native graph database recommended, or Neo4j integration)

## Quick Start
1. Initialize system: `maris setup`
2. Load Semantica export bundle: `maris load-data` (ingests entities, relationships, bridge axioms via Semantica API)
3. Index documents in Semantica: `maris index-docs`
4. Extract entities via Semantica: `maris extract-entities`
5. Extract relationships via Semantica: `maris extract-relationships`
6. Build graph in Semantica: `maris build-graph`
7. Query via Semantica GraphRAG: `maris query "What explains Cabo Pulmo's recovery?"`

## Common Workflows

### Full Pipeline Setup (All via Semantica)
- Step 1: Load Semantica export bundle (entities.jsonld, relationships.json, bridge_axioms.json)
- Step 2: Index document corpus in Semantica
- Step 3: Extract entities from documents using Semantica API
- Step 4: Extract relationships using Semantica API
- Step 5: Register bridge axioms as Semantica inference rules
- Step 6: Build knowledge graph in Semantica's native graph database
- Step 7: Execute queries via Semantica GraphRAG interface

### Query Examples
- Impact assessment: "What happens if we establish a no-take MPA?"
- Financial structuring: "What KPIs should a blue bond use?"
- Site comparison: "Compare Cabo Pulmo vs Great Barrier Reef"
- Mechanistic: "How does sea otter presence affect kelp carbon?"

### Validation
- Run Cabo Pulmo validation: `maris validate --cabo-pulmo`
- Check extraction accuracy: `maris validate --extraction`
- Full validation: `maris validate`

## Configuration
- Edit config/config.yaml for default settings
- Use .env file for sensitive credentials
- Override with environment variables

## Semantica Integration

All core operations use Semantica:
- **Entity Extraction**: Uses Semantica API for extraction from documents
- **Relationship Extraction**: Uses Semantica API for relationship identification
- **Graph Construction**: Uses Semantica's native graph database
- **Query Execution**: Uses Semantica GraphRAG interface for multi-hop reasoning
- **Bridge Axioms**: Registered as Semantica inference rules

## Troubleshooting
- Check Semantica API connection: `maris status --semantica`
- Verify Semantica graph database connectivity
- Review logs for Semantica API errors
- Validate data integrity in Semantica
- Check Semantica API rate limits and quotas
