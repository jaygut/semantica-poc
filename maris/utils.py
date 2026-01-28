"""
Utility functions for MARIS POC

Provides retry logic, ID generation, logging, and common helpers
"""

import hashlib
import logging
import time
import json
from functools import wraps
from typing import Any, Callable, Optional
from pathlib import Path
import uuid
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure logging for MARIS"""
    level = getattr(logging, log_level.upper())
    
    handlers = [logging.StreamHandler()]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for module"""
    return logging.getLogger(name)


# ═══════════════════════════════════════════════════════════════════
# RETRY LOGIC
# ═══════════════════════════════════════════════════════════════════

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logging.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
            
            raise last_exception
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# ID GENERATION
# ═══════════════════════════════════════════════════════════════════

def generate_entity_id(entity: dict) -> str:
    """Generate deterministic ID for entity"""
    entity_type = entity.get("type", "unknown")
    name = entity.get("name") or entity.get("scientific_name") or str(uuid.uuid4())
    
    id_string = f"{entity_type}:{name}"
    return hashlib.md5(id_string.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════
# DOI/URL NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

def normalize_doi(doi: str) -> str:
    """Normalize DOI to standard format"""
    if not doi:
        return ""
    
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://dx.doi.org/", "")
    doi = doi.replace("doi:", "")
    
    return doi.strip()


def validate_doi(doi: str) -> bool:
    """Validate DOI format"""
    if not doi:
        return False
    normalized = normalize_doi(doi)
    return normalized.startswith("10.") and "/" in normalized


# ═══════════════════════════════════════════════════════════════════
# FILE HASH CALCULATION
# ═══════════════════════════════════════════════════════════════════

def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 checksum of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_string_hash(content: str) -> str:
    """Compute SHA-256 hash of string"""
    return hashlib.sha256(content.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# FILE I/O
# ═══════════════════════════════════════════════════════════════════

def read_json(file_path: str | Path) -> dict:
    """Read JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(data: dict, file_path: str | Path, indent: int = 2) -> None:
    """Write JSON file"""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# DIRECTORY UTILITIES
# ═══════════════════════════════════════════════════════════════════

def ensure_dir(path: str | Path) -> Path:
    """Ensure directory exists"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════════

def chunk_list(items: list, chunk_size: int) -> list[list]:
    """Split list into chunks"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


# ═══════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════

class MARISError(Exception):
    """Base exception for MARIS"""
    pass


class SchemaValidationError(MARISError):
    """Schema validation error"""
    pass


class ExtractionError(MARISError):
    """Entity/relationship extraction error"""
    pass


class AxiomApplicationError(MARISError):
    """Bridge axiom application error"""
    pass


class QueryError(MARISError):
    """Query execution error"""
    pass


class DataLoadError(MARISError):
    """Data loading error"""
    pass
