"""MARIS Configuration Settings using Pydantic.

Replaces legacy config.py/config_v4.py with robust validation.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MARISSettings(BaseSettings):
    """Central configuration for MARIS application."""
    
    model_config = SettingsConfigDict(
        env_prefix="MARIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- Project Paths ---
    @computed_field
    @property
    def project_root(self) -> Path:
        """Root directory of the project."""
        return Path(__file__).parent.parent

    # --- Neo4j Configuration ---
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="")
    neo4j_database: str = Field(default="neo4j")
    
    # v4 Specific Neo4j (Optional)
    neo4j_uri_v4: str | None = None
    neo4j_database_v4: str | None = None

    # --- LLM Configuration ---
    llm_provider: Literal["deepseek", "openai", "anthropic"] = "deepseek"
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="https://api.deepseek.com/v1")
    llm_model: str = Field(default="deepseek-chat")
    llm_reasoning_model: str = Field(default="deepseek-reasoner")
    llm_timeout: int = 30
    llm_max_tokens: int = 4096

    # --- Extraction Settings ---
    extraction_confidence_threshold: float = 0.7
    extraction_chunk_size: int = 1500
    extraction_chunk_overlap: int = 200

    # --- API Settings ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = Field(default="")
    cors_origins: str = "http://localhost:8501"  # Comma-separated string

    # --- Provenance ---
    provenance_db: str = "provenance.db"

    # --- Feature Flags ---
    enable_live_graph: bool = True
    enable_chat: bool = True
    demo_mode: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Path Helpers ---
    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def papers_dir(self) -> Path:
        return self.data_dir / "papers"

    @property
    def schemas_dir(self) -> Path:
        return self.project_root / "schemas"
        
    @property
    def export_dir(self) -> Path:
        return self.data_dir / "semantica_export"

    @property
    def examples_dir(self) -> Path:
        return self.project_root / "examples"

    @property
    def case_study_path(self) -> Path:
        return self.examples_dir / "cabo_pulmo_case_study.json"

    @property
    def shark_bay_case_study_path(self) -> Path:
        return self.examples_dir / "shark_bay_case_study.json"

    @property
    def case_study_paths(self) -> list[Path]:
        """All case study files for multi-site population."""
        return [self.case_study_path, self.shark_bay_case_study_path]

    @property
    def bundle_path(self) -> Path:
        return self.project_root / "demos" / "context_graph_demo" / "cabo_pulmo_investment_grade_bundle.json"

    @property
    def registry_path(self) -> Path:
        return self.project_root / ".claude" / "registry" / "document_index.json"


# Singleton instance
settings = MARISSettings()
