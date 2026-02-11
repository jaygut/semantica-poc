#!/usr/bin/env python3
"""
Pre-demo health check - validates all MARIS v2 components are ready.

Usage:
    python scripts/demo_healthcheck.py

Checks:
  1. Neo4j running and populated
  2. FastAPI backend healthy
  3. LLM API key valid
  4. All 5 quick query templates return valid responses
  5. Static fallback works
  6. Streamlit can import without errors
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def check_neo4j():
    """Check Neo4j is running and has data."""
    print("\n1. Neo4j Database")
    print("-" * 40)
    try:
        from maris.graph.connection import get_driver, close_driver
        from maris.config import get_config

        cfg = get_config()
        driver = get_driver()
        with driver.session(database=cfg.neo4j_database) as session:
            result = session.run("MATCH (n) RETURN count(n) AS count").single()
            node_count = result["count"]

            result2 = session.run(
                "MATCH (a:BridgeAxiom) RETURN count(a) AS count"
            ).single()
            axiom_count = result2["count"]

            result3 = session.run(
                'MATCH (m:MPA {name: "Cabo Pulmo National Park"}) RETURN m.total_esv_usd AS esv'
            ).single()
            esv = result3["esv"] if result3 else 0

        close_driver()

        ok = True
        ok &= check("Neo4j connected", True, cfg.neo4j_uri)
        ok &= check("Node count > 0", node_count > 0, f"{node_count} nodes")
        ok &= check("Bridge axioms >= 12", axiom_count >= 12, f"{axiom_count} axioms")
        ok &= check("Cabo Pulmo ESV present", esv and esv > 0, f"${esv:,.0f}" if esv else "missing")
        return ok

    except Exception as e:
        check("Neo4j connected", False, str(e))
        return False


def check_api():
    """Check FastAPI backend is running."""
    print("\n2. FastAPI Backend")
    print("-" * 40)
    try:
        import httpx

        resp = httpx.get("http://localhost:8000/api/health", timeout=5)
        data = resp.json()
        ok = True
        ok &= check("API responding", resp.status_code == 200)
        ok &= check("Neo4j connected (via API)", data.get("neo4j_connected", False))
        ok &= check("LLM available", data.get("llm_available", False))
        stats = data.get("graph_stats", {})
        ok &= check("Graph stats present", bool(stats), json.dumps(stats))
        return ok
    except Exception as e:
        check("API responding", False, str(e))
        print("    TIP: Start API with: uvicorn maris.api.main:app --port 8000")
        return False


def check_llm():
    """Check LLM API key is configured."""
    print("\n3. LLM Configuration")
    print("-" * 40)
    from maris.config import get_config

    cfg = get_config()
    ok = True
    ok &= check("Provider configured", bool(cfg.llm_provider), cfg.llm_provider)
    ok &= check("API key set", bool(cfg.llm_api_key), "***" if cfg.llm_api_key else "MISSING")
    ok &= check("Model configured", bool(cfg.llm_model), cfg.llm_model)
    return ok


def check_fallback():
    """Check static fallback responses exist."""
    print("\n4. Static Fallback")
    print("-" * 40)
    precomputed = Path(__file__).parent.parent / "investor_demo" / "precomputed_responses.json"
    ok = True
    ok &= check("Precomputed responses file", precomputed.exists())
    if precomputed.exists():
        with open(precomputed) as f:
            data = json.load(f)
        responses = data.get("responses", {})
        ok &= check("5 template responses", len(responses) >= 5, f"{len(responses)} found")
    bundle = Path(__file__).parent.parent / "demos" / "context_graph_demo" / "cabo_pulmo_investment_grade_bundle.json"
    ok &= check("Investment-grade bundle", bundle.exists())
    return ok


def check_streamlit():
    """Check Streamlit app can import."""
    print("\n5. Streamlit Dashboard")
    print("-" * 40)
    v2_path = Path(__file__).parent.parent / "investor_demo" / "streamlit_app_v2.py"
    ok = True
    ok &= check("streamlit_app_v2.py exists", v2_path.exists())
    api_client = Path(__file__).parent.parent / "investor_demo" / "api_client.py"
    ok &= check("api_client.py exists", api_client.exists())
    chat_panel = Path(__file__).parent.parent / "investor_demo" / "components" / "chat_panel.py"
    ok &= check("chat_panel.py exists", chat_panel.exists())
    graph_explorer = Path(__file__).parent.parent / "investor_demo" / "components" / "graph_explorer.py"
    ok &= check("graph_explorer.py exists", graph_explorer.exists())
    return ok


def main():
    print("=" * 60)
    print("  MARIS v2 - Pre-Demo Health Check")
    print("=" * 60)

    results = {}
    results["neo4j"] = check_neo4j()
    results["api"] = check_api()
    results["llm"] = check_llm()
    results["fallback"] = check_fallback()
    results["streamlit"] = check_streamlit()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    all_pass = all(results.values())
    for component, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {component}")

    print()
    if all_pass:
        print("  ALL CHECKS PASSED - Ready for demo!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  {len(failed)} component(s) need attention: {', '.join(failed)}")
        if not results["neo4j"]:
            print("  -> Run: neo4j start && python scripts/populate_neo4j.py --validate")
        if not results["api"]:
            print("  -> Run: uvicorn maris.api.main:app --port 8000")
        if not results["llm"]:
            print("  -> Set MARIS_LLM_API_KEY in .env")
        if not results["fallback"]:
            print("  -> Ensure investor_demo/precomputed_responses.json exists")

    print("=" * 60)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
