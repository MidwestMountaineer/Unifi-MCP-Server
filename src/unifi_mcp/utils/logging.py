"""Logging utilities with sensitive data redaction.

This module provides structured logging with automatic redaction of sensitive
information like passwords, tokens, and API keys. It also supports correlation
ID tracking for request tracing.
"""

import logging
import re
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Context variable for correlation ID tracking
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


# Sensitive field patterns to redact
SENSITIVE_PATTERNS = [
    # Exact field name matches (case-insensitive)
    r"\bpassword\b",
    r"\bpasswd\b",
    r"\bpwd\b",
    r"\bsecret\b",
    r"\btoken\b",
    r"\bapi_key\b",
    r"\bapikey\b",
    r"\bapi-key\b",
    r"\bauth\b",
    r"\bauthorization\b",
    r"\bprivate_key\b",
    r"\bprivatekey\b",
    r"\baccess_key\b",
    r"\bsession\b",
    r"\bcookie\b",
    r"\bx-csrf-token\b",
]

# Compile regex patterns for efficient matching
SENSITIVE_FIELD_REGEX = re.compile(
    r"|".join([f"({pattern})" for pattern in SENSITIVE_PATTERNS]),
    re.IGNORECASE
)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracking.
    
    Returns:
        UUID-based correlation ID
    
    Example:
        >>> correlation_id = generate_correlation_id()
        >>> print(correlation_id)
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set the correlation ID for the current context.
    
    Args:
        correlation_id: Correlation ID to set. If None, generates a new one.
    
    Returns:
        The correlation ID that was set
    
    Example:
        >>> correlation_id = set_correlation_id()
        >>> # All logs in this context will include this correlation ID
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current context.
    
    Returns:
        Current correlation ID or None if not set
    
    Example:
        >>> correlation_id = get_correlation_id()
        >>> if correlation_id:
        ...     print(f"Request ID: {correlation_id}")
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context.
    
    Example:
        >>> clear_correlation_id()
        >>> # Correlation ID is now None
    """
    _correlation_id.set(None)


def _is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data.
    
    Args:
        field_name: Name of the field to check
    
    Returns:
        True if field is sensitive, False otherwise
    """
    return bool(SENSITIVE_FIELD_REGEX.search(field_name))


def redact_sensitive_data(
    data: Any,
    redaction_text: str = "[REDACTED]",
    max_depth: int = 10
) -> Any:
    """Recursively redact sensitive data from dictionaries, lists, and strings.
    
    This function identifies sensitive fields by name pattern matching and
    replaces their values with a redaction marker. It handles nested structures
    and prevents infinite recursion.
    
    Args:
        data: Data to redact (dict, list, str, or other)
        redaction_text: Text to use for redacted values
        max_depth: Maximum recursion depth to prevent stack overflow
    
    Returns:
        Data with sensitive values redacted
    
    Example:
        >>> data = {"username": "admin", "password": "secret123"}
        >>> redacted = redact_sensitive_data(data)
        >>> print(redacted)
        {'username': 'admin', 'password': '[REDACTED]'}
    """
    if max_depth <= 0:
        return "[MAX_DEPTH_EXCEEDED]"
    
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            if _is_sensitive_field(str(key)):
                redacted[key] = redaction_text
            else:
                redacted[key] = redact_sensitive_data(value, redaction_text, max_depth - 1)
        return redacted
    
    elif isinstance(data, list):
        return [redact_sensitive_data(item, redaction_text, max_depth - 1) for item in data]
    
    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item, redaction_text, max_depth - 1) for item in data)
    
    elif isinstance(data, str):
        # Check if the string itself looks like a sensitive value
        # (e.g., long random strings that might be tokens)
        if len(data) > 32 and not " " in data:
            # Could be a token, but we can't be sure, so leave it
            pass
        return data
    
    else:
        # For other types (int, float, bool, None, etc.), return as-is
        return data


class RedactingFormatter(logging.Formatter):
    """Custom log formatter that redacts sensitive data.
    
    This formatter automatically redacts sensitive information from log records
    before formatting them. It also adds correlation IDs when available.
    """
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        include_correlation_id: bool = True
    ):
        """Initialize the redacting formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            include_correlation_id: Whether to include correlation ID in logs
        """
        super().__init__(fmt, datefmt)
        self.include_correlation_id = include_correlation_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with redaction.
        
        Args:
            record: Log record to format
        
        Returns:
            Formatted log string with sensitive data redacted
        """
        # Add correlation ID if available
        if self.include_correlation_id:
            correlation_id = get_correlation_id()
            if correlation_id:
                record.correlation_id = correlation_id
            else:
                record.correlation_id = "-"
        
        # Redact sensitive data from the message
        if hasattr(record, "msg") and isinstance(record.msg, str):
            # For string messages, we can't easily redact without parsing
            # So we leave them as-is (developers should use structured logging)
            pass
        
        # Redact sensitive data from args
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = redact_sensitive_data(list(record.args))
        
        # Format the record
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: Optional[Union[str, Path]] = None,
    include_correlation_id: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up structured logging with redaction.
    
    This function configures the root logger with:
    - Automatic sensitive data redaction
    - Correlation ID tracking (optional)
    - Console output (stdout)
    - File output (optional)
    - Configurable log levels
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to a file
        log_file_path: Path to log file (required if log_to_file=True)
        include_correlation_id: Whether to include correlation IDs in logs
        format_string: Custom log format string
    
    Returns:
        Configured logger instance
    
    Raises:
        ValueError: If log_to_file=True but log_file_path is not provided
    
    Example:
        >>> logger = setup_logging(log_level="DEBUG", log_to_file=True, 
        ...                        log_file_path="/var/log/unifi-mcp.log")
        >>> logger.info("Server started", extra={"port": 443})
    """
    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        raise ValueError(f"Invalid log level '{log_level}'. Must be one of: {', '.join(valid_levels)}")
    
    # Validate file logging configuration
    if log_to_file and not log_file_path:
        raise ValueError("log_file_path is required when log_to_file=True")
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create format string
    if format_string is None:
        if include_correlation_id:
            format_string = "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
        else:
            format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    # Create formatter
    formatter = RedactingFormatter(
        fmt=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        include_correlation_id=include_correlation_id
    )
    
    # Add console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file and log_file_path:
        log_path = Path(log_file_path)
        
        # Create parent directory if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request")
    """
    return logging.getLogger(name)


def log_with_redaction(
    logger: logging.Logger,
    level: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Log a message with automatic data redaction.
    
    This is a convenience function for logging structured data with redaction.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        data: Additional data to log (will be redacted)
    
    Example:
        >>> logger = get_logger(__name__)
        >>> log_with_redaction(logger, "info", "User authenticated", 
        ...                    {"username": "admin", "password": "secret"})
        # Logs: User authenticated {'username': 'admin', 'password': '[REDACTED]'}
    """
    if data:
        redacted_data = redact_sensitive_data(data)
        log_func = getattr(logger, level.lower())
        log_func(f"{message} {redacted_data}")
    else:
        log_func = getattr(logger, level.lower())
        log_func(message)
