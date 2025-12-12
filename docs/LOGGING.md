# Logging System Documentation

## Overview

The UniFi MCP Server includes a comprehensive logging system with automatic sensitive data redaction, correlation ID tracking, and flexible configuration options.

## Features

### 1. Sensitive Data Redaction

The logging system automatically redacts sensitive information from logs, including:
- Passwords (`password`, `passwd`, `pwd`)
- API keys (`api_key`, `apikey`, `api-key`)
- Tokens (`token`, `authorization`)
- Secrets (`secret`)
- Private keys (`private_key`, `privatekey`)
- Access keys (`access_key`)
- Session data (`session`, `cookie`)
- CSRF tokens (`x-csrf-token`)

Redaction works recursively through nested dictionaries and lists.

### 2. Correlation ID Tracking

Each request can be assigned a unique correlation ID that appears in all related log entries, making it easy to trace a request through the system.

### 3. Configurable Log Levels

Supports standard Python log levels:
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

### 4. Multiple Output Destinations

- **Console (stdout)** - Always enabled
- **File logging** - Optional, with automatic directory creation

### 5. Structured Logging

Logs include:
- Timestamp
- Log level
- Correlation ID (optional)
- Logger name
- Message

## Usage

### Basic Setup

```python
from unifi_mcp.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(log_level="INFO")

# Get a logger for your module
logger = get_logger(__name__)

# Log messages
logger.info("Server started")
logger.warning("Connection timeout")
logger.error("Failed to authenticate")
```

### With File Logging

```python
from pathlib import Path
from unifi_mcp.utils.logging import setup_logging, get_logger

# Setup with file output
setup_logging(
    log_level="DEBUG",
    log_to_file=True,
    log_file_path="/var/log/unifi-mcp-server.log"
)

logger = get_logger(__name__)
logger.info("This goes to both console and file")
```

### With Correlation ID Tracking

```python
from unifi_mcp.utils.logging import (
    setup_logging,
    get_logger,
    set_correlation_id,
    clear_correlation_id
)

# Setup with correlation ID support
setup_logging(log_level="INFO", include_correlation_id=True)
logger = get_logger(__name__)

# Set correlation ID for a request
correlation_id = set_correlation_id()  # Auto-generates UUID

logger.info("Processing request")
logger.info("Connecting to controller")
logger.info("Request complete")

# Clear when done
clear_correlation_id()
```

### Logging with Automatic Redaction

```python
from unifi_mcp.utils.logging import get_logger, log_with_redaction

logger = get_logger(__name__)

# This will automatically redact sensitive fields
log_with_redaction(
    logger,
    "info",
    "User authentication",
    {
        "username": "admin",
        "password": "secret123",  # Will be redacted
        "ip_address": "192.168.1.100"
    }
)
# Output: User authentication {'username': 'admin', 'password': '[REDACTED]', 'ip_address': '192.168.1.100'}
```

### Manual Redaction

```python
from unifi_mcp.utils.logging import redact_sensitive_data

data = {
    "username": "admin",
    "password": "secret123",
    "api_key": "abc123xyz"
}

redacted = redact_sensitive_data(data)
# Result: {'username': 'admin', 'password': '[REDACTED]', 'api_key': '[REDACTED]'}
```

## Configuration

The logging system is configured through the `config.yaml` file:

```yaml
server:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  logging:
    log_to_file: false
    log_file_path: "/var/log/unifi-mcp-server.log"
    correlation_ids: true
```

## Best Practices

1. **Use structured logging** - Pass data as dictionaries to `log_with_redaction()` rather than formatting strings manually
2. **Set correlation IDs** - Use correlation IDs for all request processing to enable tracing
3. **Choose appropriate log levels**:
   - `DEBUG` - Development and troubleshooting
   - `INFO` - Production normal operations
   - `WARNING` - Production with detailed warnings
   - `ERROR` - Production minimal logging
4. **Never log sensitive data directly** - Use `log_with_redaction()` when logging data that might contain credentials
5. **Clear correlation IDs** - Always clear correlation IDs when request processing is complete

## Security Considerations

- Sensitive data is redacted using pattern matching on field names
- Redaction is case-insensitive
- Redaction works recursively through nested structures
- The redaction list can be extended by modifying `SENSITIVE_PATTERNS` in `logging.py`
- Log files should have restricted permissions (600 or 640)
- Log rotation should be configured for production deployments

## Examples

See `examples/logging_demo.py` for comprehensive examples of all logging features.

## Testing

The logging system includes comprehensive unit tests in `tests/test_logging.py`:

```bash
pytest tests/test_logging.py -v
```

All tests verify:
- Correlation ID generation and tracking
- Sensitive data redaction (various patterns)
- Log level filtering
- File logging
- Structured logging with redaction

## Requirements Satisfied

This implementation satisfies the following requirements:

- **1.7** - Logging operations for debugging and monitoring
- **3.3** - Redact sensitive information in logs
- **3.4** - Never include credentials in responses (applies to logs)
- **3.5** - Don't expose credentials in error messages
- **16.1** - Log all tool invocations with timestamps
- **16.2** - Log all UniFi API calls with timing information
- **16.5** - Support configurable log levels
- **16.6** - Write logs to stdout and optional log files
- **16.7** - Include correlation IDs for tracing requests
