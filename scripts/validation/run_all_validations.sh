#!/bin/bash
# MARIS Validation Suite Runner
# Runs all validation tests for Semantica integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "========================================"
echo "MARIS Validation Suite"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo ""

# Check Python
echo "Checking Python..."
python3 --version

# Check if Semantica is installed
echo ""
echo "Checking Semantica installation..."
if python3 -c "import semantica; print(f'Semantica {semantica.__version__} installed')" 2>/dev/null; then
    SEMANTICA_INSTALLED=true
else
    echo "WARNING: Semantica not installed"
    echo "Install with: pip install semantica>=0.2.6"
    SEMANTICA_INSTALLED=false
fi

echo ""
echo "========================================"
echo "Test 1: Bridge Axiom Validation"
echo "========================================"
python3 "$SCRIPT_DIR/test_semantica_bridge_axioms.py"

echo ""
echo "========================================"
echo "Test 2: Cabo Pulmo Chain Validation"
echo "========================================"
python3 "$SCRIPT_DIR/test_cabo_pulmo_chain.py"

echo ""
echo "========================================"
echo "Test 3: Semantica Provenance Integration"
echo "========================================"
python3 "$SCRIPT_DIR/test_semantica_provenance_integration.py"

echo ""
echo "========================================"
echo "Validation Complete"
echo "========================================"
echo "Results saved to:"
echo "  - $SCRIPT_DIR/validation_results.json"
echo "  - $SCRIPT_DIR/cabo_pulmo_chain_results.json"
echo "  - $SCRIPT_DIR/semantica_integration_results.json"
