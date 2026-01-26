# MARIS POC User Guide

TIMELINE: Week 15 (Phase 7: Documentation)
IMPLEMENTATION PRIORITY: Medium - User documentation for completed system

## Overview
This guide explains how to use the MARIS POC system for marine ecological knowledge graph queries.

## Installation
- Install Python dependencies from pyproject.toml
- Configure Semantica API connection in config/config.yaml or .env
- Set up graph database (Neo4j or Semantica native)

## Quick Start
1. Initialize system: `maris setup`
2. Load data: `maris load-data`
3. Index documents: `maris index-docs`
4. Extract entities: `maris extract-entities`
5. Build graph: `maris build-graph`
6. Query: `maris query "What explains Cabo Pulmo's recovery?"`

## Common Workflows

### Full Pipeline Setup
- Step 1: Load Semantica export bundle
- Step 2: Index document corpus
- Step 3: Extract entities from documents
- Step 4: Extract relationships
- Step 5: Apply bridge axioms
- Step 6: Build knowledge graph
- Step 7: Execute queries

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

## Troubleshooting
- Check Semantica API connection
- Verify graph database connectivity
- Review logs for error messages
- Validate data integrity
