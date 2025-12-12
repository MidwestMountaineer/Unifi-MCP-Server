# Configuration System Documentation

## Overview

The UniFi MCP Server uses a hybrid configuration approach that combines YAML configuration files with environment variables. This provides flexibility while maintaining security for sensitive credentials.

## Configuration Architecture

### Configuration Layers

1. **YAML Configuration** (`src/unifi_mcp/config/config.yaml`)
   - Default values and structure
   - Tool enablement settings
   - Performance tuning parameters
   - Non-sensitive configuration

2. **Environment Variables**
   - Sensitive credentials (host, username, password)
   - Runtime overrides
   - Deployment-specific settings

3. **Validation Layer**
   - Required field validation
   - Type conversion and validation
   - Fail-fast behavior for missing credentials

### Configuration Loading Process

```
1. Load .env file (if present)
   ↓
2. Load YAML configuration
   ↓
3. Expand environment variables (${VAR_NAME} syntax)
   ↓
4. Convert string types (booleans, integers, floats)
   ↓
5. Validate required fields
   ↓
6. Validate configuration values
   ↓
7. Return structured Config object
```

## Configuration Reference

### Server Configuration

```yaml
server:
  name: "unifi-network-mcp"
  log_level: "${LOG_LEVEL:INFO}"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  
  diagnostics:
    enabled: false
    log_tool_args: true
    log_tool_results: true
    max_payload_chars: 2000
  
  performance:
    cache_ttl: 30  # seconds
    max_concurrent_requests: 10
    request_timeout: 30  # seconds
    connection_timeout: 10  # seconds
  
  logging:
    log_to_file: false
    log_file_path: "/var/log/unifi-mcp-server.log"
    correlation_ids: true
```

### UniFi Controller Configuration

```yaml
unifi:
  host: "${UNIFI_HOST}"  # REQUIRED
  port: "${UNIFI_PORT:443}"
  username: "${UNIFI_USERNAME}"  # REQUIRED
  password: "${UNIFI_PASSWORD}"  # REQUIRED
  site: "${UNIFI_SITE:default}"
  verify_ssl: "${UNIFI_VERIFY_SSL:false}"
  
  retry:
    max_attempts: 3
    backoff_factor: 2
    max_backoff: 30
```

### Tools Configuration

```yaml
tools:
  network_discovery:
    enabled: true
    tools:
      - list_devices
      - get_device_details
      - list_clients
      - get_client_details
      - list_networks
      - get_network_details
      - list_wlans
      - get_wlan_details
  
  security:
    enabled: true
    tools:
      - list_firewall_rules
      - get_firewall_rule_details
      - list_traffic_routes
      - get_route_details
      - list_port_forwards
      - get_port_forward_details
      - get_ips_status
  
  statistics:
    enabled: true
    tools:
      - get_network_stats
      - get_client_stats
      - get_device_stats
      - get_top_clients
      - get_dpi_stats
      - get_alerts
      - get_system_health
  
  migration:
    enabled: true
    tools:
      - get_dhcp_status
      - verify_vlan_connectivity
      - export_configuration
  
  write_operations:
    enabled: false  # Disabled by default for safety
    require_confirmation: true
    tools:
      - toggle_firewall_rule
      - create_firewall_rule
      - update_firewall_rule
```

## Environment Variables

### Required Variables

These MUST be set for the server to start:

- `UNIFI_HOST` - UniFi controller hostname or IP address
- `UNIFI_USERNAME` - UniFi controller username
- `UNIFI_PASSWORD` - UniFi controller password

### Optional Variables

- `UNIFI_PORT` - Controller port (default: 443)
- `UNIFI_SITE` - Site name (default: "default")
- `UNIFI_VERIFY_SSL` - Verify SSL certificates (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)

### Environment Variable Syntax

The configuration system supports two syntaxes for environment variables in YAML:

1. **Required variable**: `${VAR_NAME}`
   - Must be set in environment
   - No default value
   - Example: `${UNIFI_HOST}`

2. **Optional variable with default**: `${VAR_NAME:default_value}`
   - Uses environment value if set
   - Falls back to default if not set
   - Example: `${UNIFI_PORT:443}`

## Configuration Examples

### Development Setup

Create `.env` file:

```bash
UNIFI_HOST=192.168.1.1
UNIFI_PORT=443
UNIFI_USERNAME=admin
UNIFI_PASSWORD=your-password
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
LOG_LEVEL=DEBUG
```

### Production Setup

Use environment variables directly (no .env file):

```bash
export UNIFI_HOST=unifi.example.com
export UNIFI_PORT=443
export UNIFI_USERNAME=mcp-service
export UNIFI_PASSWORD=secure-password
export UNIFI_SITE=default
export UNIFI_VERIFY_SSL=true
export LOG_LEVEL=INFO
```

### Docker Setup

Pass environment variables to container:

```bash
docker run -e UNIFI_HOST=192.168.1.1 \
           -e UNIFI_USERNAME=admin \
           -e UNIFI_PASSWORD=password \
           unifi-mcp-server
```

## Validation

### Required Field Validation

The configuration system validates that all required fields are present and non-empty:

- `unifi.host` (via `UNIFI_HOST`)
- `unifi.username` (via `UNIFI_USERNAME`)
- `unifi.password` (via `UNIFI_PASSWORD`)

If any required field is missing, the server will fail to start with a clear error message:

```
ConfigurationError: Missing required configuration fields:
  - unifi.host (set via UNIFI_HOST environment variable)
  - unifi.username (set via UNIFI_USERNAME environment variable)
  - unifi.password (set via UNIFI_PASSWORD environment variable)

Please ensure all required environment variables are set.
See .env.example for reference.
```

### Value Validation

The configuration system validates that values are within acceptable ranges:

- **log_level**: Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL
- **port**: Must be between 1 and 65535
- **cache_ttl**: Must be a positive number
- **max_concurrent_requests**: Must be a positive integer
- **request_timeout**: Must be at least 1 second
- **connection_timeout**: Must be at least 1 second
- **retry.max_attempts**: Must be a positive integer
- **retry.backoff_factor**: Must be at least 1

### Type Conversion

The configuration system automatically converts string values to appropriate types:

- **Booleans**: "true", "yes", "1" → True; "false", "no", "0" → False
- **Integers**: "443" → 443
- **Floats**: "30.5" → 30.5

## Programmatic Usage

### Loading Configuration

```python
from unifi_mcp.config import load_config, ConfigurationError

try:
    config = load_config()
    print(f"Connected to {config.unifi.host}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

### Accessing Configuration

```python
# Server configuration
print(config.server.name)
print(config.server.log_level)
print(config.server.diagnostics['enabled'])

# UniFi configuration
print(config.unifi.host)
print(config.unifi.port)
print(config.unifi.username)

# Tools configuration
if config.tools.network_discovery['enabled']:
    print("Network discovery tools enabled")
```

### Custom Configuration Path

```python
from pathlib import Path

config = load_config(config_path=Path("/etc/unifi-mcp/config.yaml"))
```

### Skip .env Loading

```python
# Useful for testing or when environment is already set
config = load_config(load_env=False)
```

## Security Considerations

### Credential Storage

- **Never commit credentials to version control**
- `.env` file is in `.gitignore` by default
- Use environment variables in production
- Consider using secrets management systems (Vault, AWS Secrets Manager, etc.)

### Credential Redaction

The configuration system does NOT automatically redact credentials in logs. This is handled by the logging system (see `utils/logging.py`).

### SSL Certificate Verification

- Set `UNIFI_VERIFY_SSL=true` in production
- Use `false` only for development with self-signed certificates
- Consider using proper SSL certificates in production

## Testing Configuration

### Test Configuration Loading

```bash
python examples/test_config_loading.py
```

This script will:
1. Check for required environment variables
2. Load configuration
3. Display all configuration values (with password redacted)
4. Validate configuration

### Unit Tests

```bash
pytest tests/test_config.py -v
```

Tests cover:
- Missing credentials (fail-fast behavior)
- Environment variable expansion
- Default values
- Boolean conversion
- Invalid port validation
- Invalid log level validation
- Configuration structure

## Troubleshooting

### Error: Missing required configuration fields

**Cause**: Required environment variables are not set.

**Solution**: 
1. Create `.env` file from `.env.example`
2. Fill in your UniFi controller credentials
3. Ensure `.env` is in the project root

### Error: Invalid port

**Cause**: Port value is outside valid range (1-65535).

**Solution**: Check `UNIFI_PORT` environment variable or YAML configuration.

### Error: Invalid log_level

**Cause**: Log level is not one of the valid options.

**Solution**: Set `LOG_LEVEL` to one of: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Configuration not loading from .env

**Cause**: `.env` file is not in the correct location or has syntax errors.

**Solution**:
1. Ensure `.env` is in project root
2. Check for syntax errors (no spaces around `=`)
3. Verify file is named exactly `.env` (not `.env.txt`)

## Future Enhancements

- [ ] Support for multiple UniFi controllers
- [ ] Configuration hot-reloading
- [ ] Configuration validation schema (JSON Schema)
- [ ] Configuration file encryption
- [ ] Configuration profiles (dev, staging, prod)
- [ ] Configuration via command-line arguments
- [ ] Configuration via web UI

## References

- [python-dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [UniFi Controller API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)

