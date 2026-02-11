"""
MARIS v2 Configuration - Environment-based configuration for all components.
"""

from dataclasses import dataclass, field
from os import getenv
from pathlib import Path


@dataclass
class MARISConfig:
    """Central configuration for MARIS v2 system."""

    # Neo4j
    neo4j_uri: str = field(default_factory=lambda: getenv("MARIS_NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: getenv("MARIS_NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: getenv("MARIS_NEO4J_PASSWORD", "maris-dev"))
    neo4j_database: str = field(default_factory=lambda: getenv("MARIS_NEO4J_DATABASE", "neo4j"))

    # LLM (model-agnostic via OpenAI-compatible API)
    llm_provider: str = field(default_factory=lambda: getenv("MARIS_LLM_PROVIDER", "deepseek"))
    llm_api_key: str = field(default_factory=lambda: getenv("MARIS_LLM_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: getenv("MARIS_LLM_BASE_URL", "https://api.deepseek.com/v1"))
    llm_model: str = field(default_factory=lambda: getenv("MARIS_LLM_MODEL", "deepseek-chat"))
    llm_reasoning_model: str = field(default_factory=lambda: getenv("MARIS_LLM_REASONING_MODEL", "deepseek-reasoner"))
    llm_timeout: int = field(default_factory=lambda: int(getenv("MARIS_LLM_TIMEOUT", "30")))
    llm_max_tokens: int = field(default_factory=lambda: int(getenv("MARIS_LLM_MAX_TOKENS", "4096")))

    # Extraction
    extraction_confidence_threshold: float = 0.7
    extraction_chunk_size: int = 1500
    extraction_chunk_overlap: int = 200

    # API
    api_host: str = field(default_factory=lambda: getenv("MARIS_API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(getenv("MARIS_API_PORT", "8000")))

    # Paths (resolved relative to project root)
    project_root: str = field(default_factory=lambda: str(Path(__file__).parent.parent))

    @property
    def papers_dir(self) -> Path:
        return Path(self.project_root) / "data" / "papers"

    @property
    def schemas_dir(self) -> Path:
        return Path(self.project_root) / "schemas"

    @property
    def export_dir(self) -> Path:
        return Path(self.project_root) / "data" / "semantica_export"

    @property
    def bundle_path(self) -> Path:
        return Path(self.project_root) / "demos" / "context_graph_demo" / "cabo_pulmo_investment_grade_bundle.json"

    @property
    def case_study_path(self) -> Path:
        return Path(self.project_root) / "examples" / "cabo_pulmo_case_study.json"

    @property
    def registry_path(self) -> Path:
        return Path(self.project_root) / ".claude" / "registry" / "document_index.json"

    # Feature flags
    enable_live_graph: bool = field(default_factory=lambda: getenv("MARIS_ENABLE_LIVE_GRAPH", "true").lower() == "true")
    enable_chat: bool = field(default_factory=lambda: getenv("MARIS_ENABLE_CHAT", "true").lower() == "true")
    demo_mode: bool = field(default_factory=lambda: getenv("MARIS_DEMO_MODE", "false").lower() == "true")


# Singleton
_config: MARISConfig | None = None


def get_config() -> MARISConfig:
    global _config
    if _config is None:
        _config = MARISConfig()
    return _config
