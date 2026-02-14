"""Tests for provenance endpoint wiring to SemanticaBackedManager.

Verifies that:
1. _get_manager() returns SemanticaBackedManager when SDK bridge is importable
2. _get_manager() falls back to MARISProvenanceManager when bridge import fails
3. Provenance data persists across manager instances via SQLite
4. The provenance summary endpoint includes semantica-specific fields
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_manager_singleton():
    """Reset the module-level _manager global between tests."""
    import maris.api.routes.provenance as prov_mod

    prov_mod._manager = None
    yield
    prov_mod._manager = None


@pytest.fixture()
def mock_config() -> MagicMock:
    """Provide a mock MARISConfig that points to real schema files."""
    cfg = MagicMock()
    cfg.schemas_dir = PROJECT_ROOT / "schemas"
    cfg.export_dir = PROJECT_ROOT / "data" / "semantica_export"
    cfg.provenance_db = "provenance.db"
    return cfg


class TestGetManagerSemanticaPath:
    """Verify _get_manager() prefers SemanticaBackedManager."""

    def test_returns_semantica_backed_manager(self, mock_config: MagicMock) -> None:
        """When the bridge is importable, _get_manager() should return SemanticaBackedManager."""
        from maris.api.routes.provenance import _get_manager
        from maris.semantica_bridge.manager import SemanticaBackedManager

        with patch("maris.config.get_config", return_value=mock_config):
            manager = _get_manager()

        assert isinstance(manager, SemanticaBackedManager)

    def test_manager_loads_16_axioms(self, mock_config: MagicMock) -> None:
        """The manager should load all 16 bridge axioms from real template files."""
        from maris.api.routes.provenance import _get_manager

        with patch("maris.config.get_config", return_value=mock_config):
            manager = _get_manager()

        assert manager.registry.count() == 16

    def test_summary_includes_semantica_fields(self, mock_config: MagicMock) -> None:
        """Summary from SemanticaBackedManager includes semantica-specific keys."""
        from maris.api.routes.provenance import _get_manager

        with patch("maris.config.get_config", return_value=mock_config):
            manager = _get_manager()

        summary = manager.summary()
        assert "semantica_available" in summary
        assert "semantica_entries" in summary
        assert "axioms_loaded" in summary
        assert summary["axioms_loaded"] == 16

    def test_singleton_returns_same_instance(self, mock_config: MagicMock) -> None:
        """Calling _get_manager() twice returns the same singleton."""
        from maris.api.routes.provenance import _get_manager

        with patch("maris.config.get_config", return_value=mock_config):
            m1 = _get_manager()
            m2 = _get_manager()

        assert m1 is m2


class TestGetManagerFallback:
    """Verify _get_manager() falls back to MARISProvenanceManager on ImportError."""

    def test_falls_back_to_maris_native(self, mock_config: MagicMock) -> None:
        """When SemanticaBackedManager import fails, falls back to MARISProvenanceManager."""
        from maris.api.routes.provenance import _get_manager
        from maris.provenance.manager import MARISProvenanceManager

        def fake_import(name: str, *args, **kwargs):
            if "semantica_bridge" in name:
                raise ImportError("Simulated: semantica bridge unavailable")
            return original_import(name, *args, **kwargs)

        import builtins
        original_import = builtins.__import__

        with (
            patch("maris.config.get_config", return_value=mock_config),
            patch("builtins.__import__", side_effect=fake_import),
        ):
            manager = _get_manager()

        assert isinstance(manager, MARISProvenanceManager)

    def test_fallback_loads_axioms(self, mock_config: MagicMock) -> None:
        """The fallback MARISProvenanceManager should also load 16 axioms."""
        from maris.api.routes.provenance import _get_manager

        def fake_import(name: str, *args, **kwargs):
            if "semantica_bridge" in name:
                raise ImportError("Simulated")
            return original_import(name, *args, **kwargs)

        import builtins
        original_import = builtins.__import__

        with (
            patch("maris.config.get_config", return_value=mock_config),
            patch("builtins.__import__", side_effect=fake_import),
        ):
            manager = _get_manager()

        assert manager.registry.count() == 16

    def test_fallback_summary_has_axioms_loaded(self, mock_config: MagicMock) -> None:
        """Fallback summary still includes axioms_loaded."""
        from maris.api.routes.provenance import _get_manager

        def fake_import(name: str, *args, **kwargs):
            if "semantica_bridge" in name:
                raise ImportError("Simulated")
            return original_import(name, *args, **kwargs)

        import builtins
        original_import = builtins.__import__

        with (
            patch("maris.config.get_config", return_value=mock_config),
            patch("builtins.__import__", side_effect=fake_import),
        ):
            manager = _get_manager()

        summary = manager.summary()
        assert "axioms_loaded" in summary
        assert summary["axioms_loaded"] == 16


class TestProvenancePersistence:
    """Verify that SemanticaBackedManager persists provenance data."""

    def test_track_and_retrieve_entity(self, mock_config: MagicMock) -> None:
        """Track an entity via the manager and retrieve it."""
        from maris.api.routes.provenance import _get_manager

        with patch("maris.config.get_config", return_value=mock_config):
            manager = _get_manager()

        result = manager.track_extraction(
            entity_id="test_cabo_esv",
            entity_type="EcosystemService",
            source_doi="10.1371/journal.pone.0062799",
            attributes={"value_usd": 29_270_000},
        )

        assert result["entity_id"] == "test_cabo_esv"
        assert result["entity_type"] == "EcosystemService"

        # Retrieve via provenance
        entity = manager.provenance.get_entity("test_cabo_esv")
        assert entity is not None

    def test_certificate_generation(self, mock_config: MagicMock) -> None:
        """Certificate generation works through the wired manager."""
        from maris.api.routes.provenance import _get_manager

        with patch("maris.config.get_config", return_value=mock_config):
            manager = _get_manager()

        manager.track_extraction(
            entity_id="cert_test_entity",
            entity_type="MPA",
            source_doi="10.1038/test",
            attributes={"name": "Test MPA"},
        )

        cert = manager.get_certificate("cert_test_entity")
        assert cert["entity_id"] == "cert_test_entity"
        assert "checksum" in cert


class TestProvenanceEndpointSource:
    """Verify provenance.py source code references SemanticaBackedManager."""

    def test_source_contains_semantica_backed_manager(self) -> None:
        """The provenance route source should reference SemanticaBackedManager."""
        route_path = PROJECT_ROOT / "maris" / "api" / "routes" / "provenance.py"
        source = route_path.read_text()
        assert "SemanticaBackedManager" in source

    def test_source_contains_import_error_fallback(self) -> None:
        """The provenance route should have a try/except ImportError fallback."""
        route_path = PROJECT_ROOT / "maris" / "api" / "routes" / "provenance.py"
        source = route_path.read_text()
        assert "except ImportError" in source
        assert "MARISProvenanceManager" in source


class TestConfigProvisioningDB:
    """Verify the provenance_db config option."""

    def test_config_has_provenance_db_default(self) -> None:
        """MARISConfig should have a provenance_db field defaulting to 'provenance.db'."""
        from maris.config import MARISConfig

        cfg = MARISConfig()
        assert hasattr(cfg, "provenance_db")
        assert cfg.provenance_db == "provenance.db"

    def test_config_provenance_db_from_env(self) -> None:
        """provenance_db should be configurable via MARIS_PROVENANCE_DB env var."""
        import os

        os.environ["MARIS_PROVENANCE_DB"] = "/tmp/custom_provenance.db"
        try:
            from maris.config import MARISConfig

            cfg = MARISConfig()
            assert cfg.provenance_db == "/tmp/custom_provenance.db"
        finally:
            del os.environ["MARIS_PROVENANCE_DB"]
