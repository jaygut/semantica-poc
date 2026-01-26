"""
Utility functions for MARIS POC

TIMELINE: Week 1 (Phase 1: Foundation)
IMPLEMENTATION PRIORITY: High - Required by all other modules

This module provides common utility functions used across the MARIS system.

FILE I/O UTILITIES:
• read_json(file_path: Path) -> dict
  - Read JSON file and return parsed dictionary
  - Handle file not found errors gracefully
  - Validate JSON syntax
  - Return empty dict on error (with logging)

• write_json(data: dict, file_path: Path, indent: int = 2) -> None
  - Write dictionary to JSON file
  - Create parent directories if needed
  - Pretty-print with indentation
  - Handle write errors with exceptions

• read_jsonld(file_path: Path) -> dict
  - Read JSON-LD file with context resolution
  - Preserve @context metadata
  - Return parsed JSON-LD structure

• read_text_file(file_path: Path, encoding: str = "utf-8") -> str
  - Read text file content
  - Handle encoding errors
  - Return file content as string

• write_text_file(content: str, file_path: Path) -> None
  - Write text content to file
  - Create parent directories if needed

PATH RESOLUTION:
• resolve_data_path(relative_path: str) -> Path
  - Resolve relative path against project data directory
  - Handle both relative and absolute paths
  - Return Path object

• ensure_dir_exists(dir_path: Path) -> None
  - Create directory if it doesn't exist
  - Create parent directories recursively
  - Handle permission errors

• get_project_root() -> Path
  - Return project root directory path
  - Based on maris package location

LOGGING UTILITIES:
• setup_logging(log_level: str, log_file: Optional[Path] = None) -> logging.Logger
  - Configure Python logging module
  - Set log level (DEBUG, INFO, WARNING, ERROR)
  - Add file handler if log_file specified
  - Add console handler with colored output
  - Return configured logger instance

• get_logger(name: str) -> logging.Logger
  - Get logger instance for module
  - Use module name as logger name
  - Return logger with appropriate level

ERROR HANDLING:
• MARISError: Base exception class for all MARIS errors
• SchemaValidationError(MARISError): Raised on schema validation failures
• ExtractionError(MARISError): Raised on entity/relationship extraction failures
• AxiomApplicationError(MARISError): Raised on bridge axiom application failures
• QueryError(MARISError): Raised on query execution failures
• DataLoadError(MARISError): Raised on data loading failures

DATA TRANSFORMATION:
• jsonld_to_dict(jsonld_data: dict) -> dict
  - Convert JSON-LD structure to plain dictionary
  - Flatten @context references
  - Remove JSON-LD specific keys if needed

• dict_to_jsonld(data: dict, context: dict) -> dict
  - Convert dictionary to JSON-LD format
  - Add @context metadata
  - Return JSON-LD structure

• normalize_entity_id(entity_id: str) -> str
  - Normalize entity IDs to consistent format
  - Handle different ID formats (URLs, URIs, local IDs)
  - Return normalized ID string

DATE/TIME UTILITIES:
• format_timestamp(dt: datetime) -> str
  - Format datetime to ISO 8601 string
  - Include timezone information
  - Return formatted timestamp

• parse_timestamp(timestamp_str: str) -> datetime
  - Parse ISO 8601 timestamp string
  - Handle timezone-aware and naive datetimes
  - Return datetime object

HASH CALCULATION:
• calculate_file_hash(file_path: Path) -> str
  - Calculate SHA-256 hash of file content
  - Return hex digest string
  - Used for document provenance tracking

• calculate_string_hash(content: str) -> str
  - Calculate SHA-256 hash of string content
  - Return hex digest string
  - Used for content integrity checks

URL/DOI VALIDATION:
• validate_doi(doi: str) -> bool
  - Validate DOI format (10.xxxx/xxxx)
  - Check DOI structure
  - Return True if valid

• normalize_doi(doi: str) -> str
  - Normalize DOI to standard format
  - Remove whitespace, convert to lowercase
  - Return normalized DOI

• validate_url(url: str) -> bool
  - Validate URL format
  - Check URL scheme (http, https)
  - Return True if valid

• normalize_url(url: str) -> str
  - Normalize URL format
  - Remove trailing slashes
  - Return normalized URL

TEXT PROCESSING:
• extract_quotes(text: str, max_length: int = 200) -> list[str]
  - Extract quoted text from document
  - Handle single and double quotes
  - Limit quote length
  - Return list of extracted quotes

• parse_page_reference(ref_str: str) -> dict
  - Parse page reference strings ("p. 123", "pp. 123-125", "Figure 2")
  - Extract page numbers, figure numbers, table numbers
  - Return structured dict with page info

• clean_text(text: str) -> str
  - Remove extra whitespace
  - Normalize line breaks
  - Remove special characters if needed
  - Return cleaned text

BATCH PROCESSING:
• batch_process(items: list, batch_size: int, processor: callable) -> list
  - Process items in batches
  - Apply processor function to each batch
  - Collect results
  - Return list of processed results

• chunk_list(items: list, chunk_size: int) -> list[list]
  - Split list into chunks of specified size
  - Return list of chunks
  - Useful for batch API calls

RETRY LOGIC:
• retry_with_backoff(func: callable, max_retries: int = 3, initial_delay: float = 1.0) -> Any
  - Execute function with exponential backoff retry
  - Retry on transient errors (network, timeout)
  - Exponential delay: 1s, 2s, 4s, etc.
  - Return function result or raise exception after max retries

• is_retryable_error(error: Exception) -> bool
  - Check if error is retryable
  - Network errors, timeouts are retryable
  - Validation errors are not retryable
  - Return True if error should be retried

PROGRESS TRACKING:
• ProgressTracker class
  - Track progress of long-running operations
  - Display progress bar
  - Calculate ETA
  - Update progress percentage

• create_progress_bar(total: int, desc: str = "") -> ProgressTracker
  - Create progress tracker instance
  - Initialize with total count
  - Return tracker object

MEMORY-EFFICIENT FILE READING:
• read_file_chunks(file_path: Path, chunk_size: int = 8192) -> Generator[str]
  - Read large file in chunks
  - Yield chunks as strings
  - Memory-efficient for large files
  - Generator pattern

CONFIGURATION VALIDATION:
• validate_config(config: dict, schema: dict) -> bool
  - Validate configuration against schema
  - Check required fields
  - Validate field types
  - Return True if valid

TYPE CONVERSION:
• to_path(value: Union[str, Path]) -> Path
  - Convert string or Path to Path object
  - Handle both types
  - Return Path object

• to_str_list(value: Union[str, list]) -> list[str]
  - Convert string or list to list of strings
  - Handle comma-separated strings
  - Return list of strings

INTEGRATION POINTS:
• Used by: All MARIS modules for common operations
• Configuration: Uses maris.config.Config for paths and settings
• Logging: Integrates with Python logging module
"""
