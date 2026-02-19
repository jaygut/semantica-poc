"""Regression tests for WS3-P2 bridge axiom DOI hardening."""

import json
from pathlib import Path

from maris.provenance.doi_verifier import DoiVerifier


_PROJECT_ROOT = Path(__file__).parent.parent


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _get_axiom(axioms: list[dict], axiom_id: str) -> dict:
    for axiom in axioms:
        if axiom.get("axiom_id") == axiom_id:
            return axiom
    raise AssertionError(f"Axiom not found: {axiom_id}")


def _collect_dois(obj: object) -> list[str]:
    dois: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"doi", "source_doi"} and isinstance(value, str):
                dois.append(value)
            else:
                dois.extend(_collect_dois(value))
    elif isinstance(obj, list):
        for item in obj:
            dois.extend(_collect_dois(item))
    return dois


class TestBridgeAxiomProvenanceHardening:
    def test_no_placeholder_doi_in_templates(self):
        data = _load_json(_PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json")
        dois = _collect_dois(data)
        assert not any("xxx" in doi.lower() for doi in dois)

    def test_no_placeholder_doi_in_export(self):
        data = _load_json(_PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json")
        dois = _collect_dois(data)
        assert not any("xxx" in doi.lower() for doi in dois)

    def test_ba025_export_uses_registry_doc_ids(self):
        data = _load_json(_PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json")
        ba_025 = _get_axiom(data.get("bridge_axioms", []), "BA-025")
        by_doi = {
            src.get("doi"): src.get("doc_id")
            for src in ba_025.get("evidence_sources", [])
        }
        assert by_doi.get("10.3389/fmars.2025.1620592") == "ondiviela_2025_wave_attenuation"
        assert by_doi.get("10.1007/s10750-023-05244-0") == "nordlund_2023_seagrass_services_review"

    def test_ba031_export_uses_resolvable_primary_doi(self):
        data = _load_json(_PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json")
        ba_031 = _get_axiom(data.get("bridge_axioms", []), "BA-031")

        coeff_dois = {
            val.get("source_doi")
            for val in ba_031.get("coefficients", {}).values()
            if isinstance(val, dict)
        }
        coeff_dois.discard(None)
        assert coeff_dois == {"10.3389/fmars.2023.899256"}

        primary_doi = ba_031.get("evidence_sources", [])[0].get("doi", "")
        verification = DoiVerifier(enable_live_checks=False).verify(primary_doi)
        assert verification.doi_valid is True
        assert verification.normalized_doi == "10.3389/fmars.2023.899256"

    def test_ba031_templates_primary_source_is_resolvable(self):
        data = _load_json(_PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json")
        ba_031 = _get_axiom(data.get("axioms", []), "BA-031")

        source = ba_031.get("sources", [])[0]
        assert source.get("doi") == "10.3389/fmars.2023.899256"
        assert "Booth" in source.get("citation", "")

        verification = DoiVerifier(enable_live_checks=False).verify(source.get("doi", ""))
        assert verification.doi_valid is True
