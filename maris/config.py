"""
Configuration management for MARIS POC

Loads settings from:
1. config/config.yaml
2. Environment variables (.env)
3. Default values
"""

import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


# Load environment variables
load_dotenv()


class Config(BaseSettings):
    """MARIS configuration settings - minimal and focused"""
    
    # Project paths
    project_root: Path = Path(__file__).parent.parent
    
    # Groq LLM settings
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_model: str = Field(default="llama3-70b-8192", env="GROQ_MODEL")
    groq_temperature: float = 0.1
    
    # FalkorDB settings
    falkordb_host: str = Field(default="localhost", env="FALKORDB_HOST")
    falkordb_port: int = Field(default=6379, env="FALKORDB_PORT")
    falkordb_graph_name: str = Field(default="maris_kg", env="FALKORDB_GRAPH_NAME")
    
    # Extraction settings
    extraction_batch_size: int = 10
    extraction_max_retries: int = 3
    extraction_confidence_threshold: float = 0.7
    
    # GraphRAG settings
    graphrag_max_hops: int = 4
    graphrag_include_provenance: bool = True
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @classmethod
    def from_yaml(cls, yaml_path: str | Path = "config/config.yaml") -> "Config":
        """Load configuration from YAML file"""
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            return cls()
        
        with open(yaml_path) as f:
            config_data = yaml.safe_load(f) or {}
        
        return cls(**config_data)
    
    def validate_api_keys(self) -> None:
        """Validate required API keys"""
        if not self.groq_api_key or self.groq_api_key == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY is required. Set it in .env file.")


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_yaml()
    return _config


def reload_config(yaml_path: Optional[str | Path] = None) -> Config:
    """Reload configuration from file"""
    global _config
    _config = Config.from_yaml(yaml_path) if yaml_path else Config.from_yaml()
    return _config
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
