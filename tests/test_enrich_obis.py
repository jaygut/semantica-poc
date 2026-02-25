"""Unit tests for scripts/enrich_obis.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock


def _load_module():
    """Load enrich_obis.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "enrich_obis",
        Path(__file__).parent.parent / "scripts" / "enrich_obis.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load_module()
_derive_wkt_bbox = _mod._derive_wkt_bbox
_enrich_site = _mod._enrich_site


def _parse_wkt_coords(wkt: str) -> list[tuple[float, float]]:
    """Extract coordinate pairs from a WKT POLYGON string."""
    # "POLYGON((-109.46 23.38, -109.38 23.38, ...))"
    inner = wkt.replace("POLYGON((", "").replace("))", "")
    pairs = inner.split(", ")
    return [(float(p.split()[0]), float(p.split()[1])) for p in pairs]


def _make_mock_client(
    stats=None, redlist=None, composition=None, qc_stats=None, env_stats=None,
):
    """Create a mock OBISClient with configurable return values."""
    client = MagicMock()
    client.get_statistics.return_value = stats or {}
    client.get_checklist_redlist.return_value = redlist or []
    client.get_statistics_composition.return_value = composition or {}
    client.get_statistics_qc.return_value = qc_stats or {}
    client.get_statistics_env.return_value = env_stats or {}
    return client


def _make_case_study(path: Path, extra: dict | None = None) -> Path:
    """Write a minimal case study JSON and return its path."""
    cs = {
        "site": {
            "name": "Test Site",
            "coordinates": {"latitude": 23.0, "longitude": -109.0},
            "area_km2": 71.0,
        },
        "ecosystem_services": {"total_annual_value_usd": 0},
    }
    if extra:
        cs.update(extra)
    cs_path = path / "test_case_study.json"
    cs_path.write_text(json.dumps(cs, indent=2))
    return cs_path


# ---------------------------------------------------------------------------
# Tests for _derive_wkt_bbox
# ---------------------------------------------------------------------------


def test_bbox_small_site():
    """Small site (Cabo Pulmo, 71 km2) should produce a tight bbox, not capped."""
    wkt = _derive_wkt_bbox(23.42, -109.42, 71.11)
    assert wkt.startswith("POLYGON((")

    coords = _parse_wkt_coords(wkt)
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    half_lat = (max(lats) - min(lats)) / 2
    half_lon = (max(lons) - min(lons)) / 2

    # sqrt(71.11)/2 = 4.22 km -> delta_lat = 4.22/111.0 ~ 0.038 deg
    # Should be well below the 4.0 degree cap
    assert half_lat < 0.5, f"Half-lat {half_lat} should be < 0.5 for small site"
    assert half_lon < 0.5, f"Half-lon {half_lon} should be < 0.5 for small site"


def test_bbox_large_site_capped():
    """Very large site (1,000,000 km2) should be capped at cap_degrees/2 = 4.0."""
    wkt = _derive_wkt_bbox(0.0, 0.0, 1_000_000)
    coords = _parse_wkt_coords(wkt)
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    half_lat = (max(lats) - min(lats)) / 2
    half_lon = (max(lons) - min(lons)) / 2

    assert abs(half_lat - 4.0) < 0.01, f"Half-lat {half_lat} should be capped at 4.0"
    assert abs(half_lon - 4.0) < 0.01, f"Half-lon {half_lon} should be capped at 4.0"


def test_bbox_high_latitude():
    """High-latitude site should have wider longitude span than latitude span."""
    wkt = _derive_wkt_bbox(80.0, 0.0, 10_000)
    coords = _parse_wkt_coords(wkt)
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)

    # cos(80) ~ 0.174, so longitude delta should be much larger
    assert lon_span > lat_span, (
        f"Longitude span ({lon_span}) should exceed latitude span ({lat_span}) "
        f"at high latitude"
    )


# ---------------------------------------------------------------------------
# Tests for _enrich_site
# ---------------------------------------------------------------------------


def test_enrich_site_writes_keys(tmp_path):
    """Enrichment should inject biodiversity_metrics and observation_quality."""
    cs_path = _make_case_study(tmp_path)
    stats = {
        "records": 1000, "species": 50, "datasets": 5,
        "yearmin": 2010, "yearmax": 2020,
    }
    client = _make_mock_client(
        stats=stats,
        redlist=[{"category": "EN"}, {"category": "VU"}],
        qc_stats={"total": 1000, "on_land": 10, "no_depth": 20},
    )

    result = _enrich_site(
        cs_path, client, stats, portfolio_max_records=10_000,
    )

    assert result is not None
    assert result["species"] == 50
    assert result["iucn_threatened"] == 2

    # Reload JSON and verify keys
    data = json.loads(cs_path.read_text())
    assert "biodiversity_metrics" in data
    assert "observation_quality" in data
    assert "environmental_baselines" in data
    assert data["biodiversity_metrics"]["species_richness"] == 50
    assert data["biodiversity_metrics"]["iucn_threatened_count"] == 2
    assert "obis_fetched_at" in data["biodiversity_metrics"]


def test_force_flag(tmp_path):
    """Without --force, already-enriched sites should be skipped."""
    cs_path = _make_case_study(tmp_path, extra={
        "biodiversity_metrics": {
            "obis_fetched_at": "2025-01-01T00:00:00+00:00",
            "species_richness": 10,
        },
    })
    stats = {"records": 500, "species": 25, "datasets": 3}
    client = _make_mock_client(stats=stats)

    # Without force: should skip
    result_no_force = _enrich_site(
        cs_path, client, stats, portfolio_max_records=10_000,
        force=False,
    )
    assert result_no_force is None

    # With force: should enrich
    result_force = _enrich_site(
        cs_path, client, stats, portfolio_max_records=10_000,
        force=True,
    )
    assert result_force is not None
    assert result_force["species"] == 25


def test_graceful_empty_response(tmp_path):
    """Empty OBIS responses should not crash; metrics should be zero."""
    cs_path = _make_case_study(tmp_path)
    stats = {}
    client = _make_mock_client()  # all methods return empty

    result = _enrich_site(
        cs_path, client, stats, portfolio_max_records=10_000,
    )

    assert result is not None

    data = json.loads(cs_path.read_text())
    assert data["biodiversity_metrics"]["species_richness"] == 0
    assert data["biodiversity_metrics"]["iucn_threatened_count"] == 0
    assert data["observation_quality"]["composite_quality_score"] >= 0
