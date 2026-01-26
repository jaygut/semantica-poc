"""
Configuration management for MARIS POC
"""

import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseSettings, Field


# Load environment variables
load_dotenv()


class Config(BaseSettings):
    """MARIS configuration settings"""
    
    # Semantica Framework Settings
    semantica_api_url: str = Field(
        default=os.getenv("SEMANTICA_API_URL", "http://localhost:8000"),
        description="Semantica API endpoint URL"
    )
    semantica_api_key: Optional[str] = Field(
        default=os.getenv("SEMANTICA_API_KEY"),
        description="Semantica API key for authentication"
    )
    
    # Graph Database Settings
    graph_db_url: str = Field(
        default=os.getenv("GRAPH_DB_URL", "bolt://localhost:7687"),
        description="Graph database connection URL"
    )
    graph_db_user: str = Field(
        default=os.getenv("GRAPH_DB_USER", "neo4j"),
        description="Graph database username"
    )
    graph_db_password: str = Field(
        default=os.getenv("GRAPH_DB_PASSWORD", "password"),
        description="Graph database password"
    )
    graph_db_type: str = Field(
        default=os.getenv("GRAPH_DB_TYPE", "neo4j"),
        description="Graph database type (neo4j, semantica)"
    )
    
    # Data Paths
    project_root: Path = Field(
        default=Path(__file__).parent.parent,
        description="Project root directory"
    )
    schemas_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "schemas",
        description="Schema files directory"
    )
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data",
        description="Data directory"
    )
    export_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data" / "semantica_export",
        description="Semantica export bundle directory"
    )
    registry_path: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / ".claude" / "registry" / "document_index.json",
        description="Document registry path"
    )
    
    # Entity Extraction Settings
    extraction_batch_size: int = Field(
        default=10,
        description="Batch size for entity extraction"
    )
    extraction_timeout: int = Field(
        default=300,
        description="Timeout for extraction requests (seconds)"
    )
    extraction_accuracy_target: float = Field(
        default=0.85,
        description="Target extraction accuracy threshold"
    )
    
    # Bridge Axiom Settings
    axiom_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence threshold for axiom application"
    )
    uncertainty_propagation_enabled: bool = Field(
        default=True,
        description="Enable uncertainty propagation through axiom chains"
    )
    
    # Query Engine Settings
    max_query_hops: int = Field(
        default=4,
        description="Maximum number of hops for multi-hop reasoning"
    )
    query_timeout: int = Field(
        default=5,
        description="Query timeout in seconds"
    )
    include_provenance: bool = Field(
        default=True,
        description="Include provenance chains in query responses"
    )
    include_confidence: bool = Field(
        default=True,
        description="Include confidence scores in query responses"
    )
    
    # Validation Settings
    cabo_pulmo_tolerance: float = Field(
        default=0.20,
        description="Tolerance for Cabo Pulmo validation (±20%)"
    )
    
    # Logging Settings
    log_level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (optional)"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        # Try to load from config.yaml first
        config_file = Path(__file__).parent.parent / "config" / "config.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                yaml_config = yaml.safe_load(f)
                _config = Config(**yaml_config)
        else:
            _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from files"""
    global _config
    _config = None
    return get_config()
