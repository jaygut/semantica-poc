# MARIS POC Developer Guide

TIMELINE: Week 8 (Phase 4: Integration, Testing & Demo via Semantica)
IMPLEMENTATION PRIORITY: Medium - Developer documentation for extending the system

## Architecture Overview
MARIS POC follows a modular architecture with **Semantica integration** at its core:
- Configuration: maris.config
- **Semantica Integration: maris.semantica_integration** (CRITICAL - Used by all modules)
- Extraction: maris.entity_extractor, maris.relationship_extractor (both use Semantica API)
- Inference: maris.bridge_axiom_engine (uses Semantica inference rules)
- Query: maris.query_engine (uses Semantica GraphRAG)
- Graph: maris.graph_builder (uses Semantica graph database)
- Utilities: maris.utils, maris.provenance, maris.validators

**All core operations route through Semantica:**
- Entity extraction → Semantica API
- Relationship extraction → Semantica API
- Graph construction → Semantica graph database
- Query execution → Semantica GraphRAG
- Bridge axioms → Semantica inference rules

## Development Setup
- Clone repository
- Install dependencies: `pip install -e ".[dev]"`
- Set up development environment
- **Configure Semantica API access** (required for all operations)
  - Set SEMANTICA_API_URL in config/config.yaml or .env
  - Set SEMANTICA_API_KEY in .env
  - Test connection: `maris status --semantica`
- Run tests: `pytest tests/`

## Adding New Features

### Adding a New Entity Type
- Update schemas/entity_schema.json
- Update maris/schemas.py to load new type
- Update extraction logic in maris/entity_extractor.py (uses Semantica API)
- Ensure Semantica schema validation passes
- Add tests in tests/test_entity_extraction.py

### Adding a New Bridge Axiom
- Add axiom to schemas/bridge_axiom_templates.json
- Update maris/bridge_axiom_engine.py to register as Semantica inference rule
- Register axiom via Semantica API: `semantica_client.add_inference_rule()`
- Add validation tests in tests/test_bridge_axioms.py
- Test inference via Semantica
- Update documentation

### Adding a New Query Type
- Update maris/query_engine.py with new query handler (uses Semantica GraphRAG)
- Ensure query routes through Semantica GraphRAG interface
- Add query examples to examples/sample_queries.md
- Add tests in tests/test_query_engine.py
- Test multi-hop reasoning via Semantica
- Update user guide

## Testing
- Unit tests: Test individual modules (mock Semantica API calls)
- Integration tests: Test end-to-end pipeline with Semantica
- Validation tests: Test against Cabo Pulmo case study via Semantica queries
- Performance tests: Test query latency and throughput (Semantica GraphRAG)
- Semantica API tests: Test all Semantica integration points

## Code Style
- Follow PEP 8
- Use type hints
- Document all public functions
- Write docstrings for all modules and classes

## Contributing
- Create feature branches
- Write tests for new features
- Update documentation
- Submit pull requests
