# MARIS POC Developer Guide

TIMELINE: Week 15 (Phase 7: Documentation)
IMPLEMENTATION PRIORITY: Medium - Developer documentation for extending the system

## Architecture Overview
MARIS POC follows a modular architecture with clear separation of concerns:
- Configuration: maris.config
- Integration: maris.semantica_integration
- Extraction: maris.entity_extractor, maris.relationship_extractor
- Inference: maris.bridge_axiom_engine
- Query: maris.query_engine
- Graph: maris.graph_builder
- Utilities: maris.utils, maris.provenance, maris.validators

## Development Setup
- Clone repository
- Install dependencies: `pip install -e ".[dev]"`
- Set up development environment
- Configure Semantica API access
- Run tests: `pytest tests/`

## Adding New Features

### Adding a New Entity Type
- Update schemas/entity_schema.json
- Update maris/schemas.py to load new type
- Update extraction logic in maris/entity_extractor.py
- Add tests in tests/test_entity_extraction.py

### Adding a New Bridge Axiom
- Add axiom to schemas/bridge_axiom_templates.json
- Update maris/bridge_axiom_engine.py to handle new axiom
- Add validation tests in tests/test_bridge_axioms.py
- Update documentation

### Adding a New Query Type
- Update maris/query_engine.py with new query handler
- Add query examples to examples/sample_queries.md
- Add tests in tests/test_query_engine.py
- Update user guide

## Testing
- Unit tests: Test individual modules
- Integration tests: Test end-to-end pipeline
- Validation tests: Test against Cabo Pulmo case study
- Performance tests: Test query latency and throughput

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
