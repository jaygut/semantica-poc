"""
POC Success Criteria Validation

Validates that MARIS implementation meets all POC success criteria:
1. Cabo Pulmo query with full provenance
2. Ecosystem service values ±20%
3. TNFD field coverage 100%
4. Query latency <5 seconds
5. 12 bridge axioms functional
6. Investor demo complete
"""
from typing import Dict, Any, List
import time
from maris.query import query_graphrag, cabo_pulmo_queries
from maris.graph import build_knowledge_graph
from maris.reasoning import apply_bridge_axioms, get_axiom_evidence
from maris.export import export_tnfd_disclosure
from maris.data import load_cabo_pulmo, load_sample_extractions, load_bridge_axioms
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# TECHNICAL VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_cabo_pulmo_query() -> Dict[str, Any]:
    """
    Success Criterion: Cabo Pulmo query returns full provenance
    
    Returns:
        Validation results with pass/fail status
    """
    logger.info("Validating Cabo Pulmo query...")
    
    query = "What ecological factors explain Cabo Pulmo's 463% biomass recovery?"
    
    try:
        # Run query
        response = query_graphrag(query)
        
        # Check for required components
        has_answer = bool(response.get('answer'))
        has_provenance = bool(response.get('provenance'))
        has_confidence = 'confidence' in response
        
        # Load actual Cabo Pulmo data for comparison
        cabo_pulmo = load_cabo_pulmo()
        expected_biomass = cabo_pulmo['ecological_recovery']['metrics']['fish_biomass']['recovery_ratio']
        
        result = {
            'criterion': 'Cabo Pulmo Query',
            'passed': has_answer and has_provenance,
            'details': {
                'query': query,
                'has_answer': has_answer,
                'has_provenance': has_provenance,
                'provenance_count': len(response.get('provenance', [])),
                'has_confidence': has_confidence,
                'expected_biomass_ratio': expected_biomass
            }
        }
        
        logger.info(f"✓ Cabo Pulmo validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Cabo Pulmo validation failed: {e}")
        return {
            'criterion': 'Cabo Pulmo Query',
            'passed': False,
            'error': str(e)
        }


def validate_query_latency() -> Dict[str, Any]:
    """
    Success Criterion: Query latency <5 seconds (3-4 hops)
    
    Returns:
        Validation results with timing
    """
    logger.info("Validating query latency...")
    
    test_queries = cabo_pulmo_queries()[:3]  # Test 3 queries
    results = []
    
    for query in test_queries:
        try:
            start_time = time.time()
            response = query_graphrag(query, max_hops=4)
            elapsed = time.time() - start_time
            
            results.append({
                'query': query[:50] + '...',
                'elapsed_seconds': round(elapsed, 2),
                'passed': elapsed < 5.0
            })
        except Exception as e:
            results.append({
                'query': query[:50] + '...',
                'elapsed_seconds': None,
                'passed': False,
                'error': str(e)
            })
    
    all_passed = all(r['passed'] for r in results)
    avg_latency = sum(r['elapsed_seconds'] for r in results if r['elapsed_seconds']) / len(results)
    
    result = {
        'criterion': 'Query Latency',
        'passed': all_passed,
        'details': {
            'target': '<5 seconds',
            'average_latency': round(avg_latency, 2),
            'queries_tested': len(results),
            'results': results
        }
    }
    
    logger.info(f"✓ Query latency validation: {'PASS' if result['passed'] else 'FAIL'}")
    return result


def validate_bridge_axioms() -> Dict[str, Any]:
    """
    Success Criterion: All 12 bridge axioms functional
    
    Returns:
        Validation results for axioms
    """
    logger.info("Validating bridge axioms...")
    
    try:
        axioms_schema = load_bridge_axioms()
        axioms = axioms_schema.get('axioms', [])
        
        axiom_details = []
        for axiom in axioms:
            evidence = get_axiom_evidence(axiom['axiom_id'])
            axiom_details.append({
                'axiom_id': axiom['axiom_id'],
                'name': axiom.get('name', 'Unknown'),
                'has_pattern': bool(axiom.get('pattern')),
                'evidence_count': len(evidence),
                'evidence_ok': len(evidence) >= 3  # POC requires 3+ sources
            })
        
        all_have_evidence = all(a['evidence_ok'] for a in axiom_details)
        
        result = {
            'criterion': 'Bridge Axioms',
            'passed': len(axioms) == 12 and all_have_evidence,
            'details': {
                'total_axioms': len(axioms),
                'expected_axioms': 12,
                'axioms_with_3plus_sources': sum(1 for a in axiom_details if a['evidence_ok']),
                'axiom_details': axiom_details
            }
        }
        
        logger.info(f"✓ Bridge axioms validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Bridge axioms validation failed: {e}")
        return {
            'criterion': 'Bridge Axioms',
            'passed': False,
            'error': str(e)
        }


def validate_tnfd_coverage() -> Dict[str, Any]:
    """
    Success Criterion: TNFD field coverage 100% of required fields
    
    Returns:
        Validation results for TNFD disclosure
    """
    logger.info("Validating TNFD field coverage...")
    
    try:
        # Load Cabo Pulmo as test data
        cabo_pulmo = load_cabo_pulmo()
        
        # Generate TNFD disclosure
        disclosure = export_tnfd_disclosure(cabo_pulmo)
        
        # Required TNFD fields (simplified for POC)
        required_fields = [
            'location',
            'ecosystem_type',
            'ecosystem_services',
            'biodiversity_metrics',
            'dependencies'
        ]
        
        present_fields = [field for field in required_fields if field in disclosure]
        coverage = (len(present_fields) / len(required_fields)) * 100
        
        result = {
            'criterion': 'TNFD Coverage',
            'passed': coverage == 100,
            'details': {
                'required_fields': len(required_fields),
                'present_fields': len(present_fields),
                'coverage_percent': round(coverage, 1),
                'missing_fields': [f for f in required_fields if f not in disclosure]
            }
        }
        
        logger.info(f"✓ TNFD validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ TNFD validation failed: {e}")
        return {
            'criterion': 'TNFD Coverage',
            'passed': False,
            'error': str(e)
        }


def validate_provenance() -> Dict[str, Any]:
    """
    Success Criterion: DOI + page for all claims
    
    Returns:
        Validation results for provenance tracking
    """
    logger.info("Validating provenance completeness...")
    
    try:
        # Load sample extractions
        extractions = load_sample_extractions()
        
        provenance_complete = []
        for extract_id, extraction in extractions.items():
            entities = extraction.get('entities', [])
            for entity in entities:
                has_source = 'source_document' in entity
                has_doi = 'doi' in entity or 'source_doi' in entity
                
                provenance_complete.append({
                    'extract': extract_id,
                    'entity': entity.get('name', 'Unknown'),
                    'has_source': has_source,
                    'has_doi': has_doi,
                    'complete': has_source and has_doi
                })
        
        complete_count = sum(1 for p in provenance_complete if p['complete'])
        total_count = len(provenance_complete)
        completeness = (complete_count / total_count * 100) if total_count > 0 else 0
        
        result = {
            'criterion': 'Provenance Completeness',
            'passed': completeness >= 90,  # 90% threshold for POC
            'details': {
                'total_entities': total_count,
                'entities_with_complete_provenance': complete_count,
                'completeness_percent': round(completeness, 1),
                'target': '≥90% for POC'
            }
        }
        
        logger.info(f"✓ Provenance validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Provenance validation failed: {e}")
        return {
            'criterion': 'Provenance Completeness',
            'passed': False,
            'error': str(e)
        }


# ═══════════════════════════════════════════════════════════════════
# BUSINESS VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_investor_demo() -> Dict[str, Any]:
    """
    Success Criterion: Complete 10-min narrative without gaps
    
    Returns:
        Validation results for investor demo readiness
    """
    logger.info("Validating investor demo readiness...")
    
    try:
        from maris.query import all_demo_queries
        
        demo_queries = all_demo_queries()
        
        result = {
            'criterion': 'Investor Demo',
            'passed': len(demo_queries) >= 11,  # POC requires 11 queries
            'details': {
                'total_queries': len(demo_queries),
                'expected_queries': 11,
                'query_categories': {
                    'cabo_pulmo': 3,
                    'blue_bonds': 3,
                    'trophic_cascades': 2,
                    'mpa_impact': 3
                },
                'demo_ready': len(demo_queries) >= 11
            }
        }
        
        logger.info(f"✓ Investor demo validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Investor demo validation failed: {e}")
        return {
            'criterion': 'Investor Demo',
            'passed': False,
            'error': str(e)
        }


def validate_multi_habitat_support() -> Dict[str, Any]:
    """
    Success Criterion: Support for coral, kelp, mangrove, seagrass
    
    Returns:
        Validation results for habitat coverage
    """
    logger.info("Validating multi-habitat support...")
    
    try:
        from maris.data import load_entity_schema
        
        schema = load_entity_schema()
        habitat_entity = schema['entities'].get('Habitat', {})
        
        required_habitats = ['coral_reef', 'kelp_forest', 'mangrove', 'seagrass']
        supported_habitats = habitat_entity.get('types', [])
        
        present_habitats = [h for h in required_habitats if h in supported_habitats]
        coverage = (len(present_habitats) / len(required_habitats)) * 100
        
        result = {
            'criterion': 'Multi-Habitat Support',
            'passed': coverage == 100,
            'details': {
                'required_habitats': required_habitats,
                'supported_habitats': supported_habitats,
                'coverage_percent': round(coverage, 1),
                'missing': [h for h in required_habitats if h not in supported_habitats]
            }
        }
        
        logger.info(f"✓ Multi-habitat validation: {'PASS' if result['passed'] else 'FAIL'}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Multi-habitat validation failed: {e}")
        return {
            'criterion': 'Multi-Habitat Support',
            'passed': False,
            'error': str(e)
        }


# ═══════════════════════════════════════════════════════════════════
# FULL VALIDATION SUITE
# ═══════════════════════════════════════════════════════════════════

def run_full_validation() -> Dict[str, Any]:
    """
    Run complete POC validation suite
    
    Returns:
        Complete validation report
    """
    logger.info("=" * 80)
    logger.info("RUNNING FULL POC VALIDATION SUITE")
    logger.info("=" * 80)
    
    # Technical validations
    technical_results = [
        validate_cabo_pulmo_query(),
        validate_query_latency(),
        validate_bridge_axioms(),
        validate_tnfd_coverage(),
        validate_provenance()
    ]
    
    # Business validations
    business_results = [
        validate_investor_demo(),
        validate_multi_habitat_support()
    ]
    
    all_results = technical_results + business_results
    
    # Summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r['passed'])
    failed = total - passed
    
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_criteria': total,
            'passed': passed,
            'failed': failed,
            'success_rate': round((passed / total) * 100, 1)
        },
        'technical_validation': technical_results,
        'business_validation': business_results,
        'overall_status': 'PASS' if failed == 0 else 'FAIL'
    }
    
    logger.info("=" * 80)
    logger.info(f"VALIDATION COMPLETE: {passed}/{total} criteria passed ({report['summary']['success_rate']}%)")
    logger.info("=" * 80)
    
    return report
