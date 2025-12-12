# UniFi API Client

The UniFi API client provides an async HTTP client for interacting with the UniFi Network Controller API. It handles authentication, session management, SSL certificate validation, and provides a clean interface for making API requests.

## Features

- **Async HTTP Client**: Built on aiohttp for efficient async operations
- **Automatic Authentication**: Handles login and session cookie management
- **SSL Support**: Works with both valid and self-signed certificates
- **Session Management**: Maintains persistent sessions with automatic cookie handling
- **Structured Logging**: Comprehensive logging with sensitive data redaction
- **Context Manager**: Supports async context manager for automatic cleanup
- **Error Handling**: Clear error messages for common failure scenarios

## Architecture

```
UniFiClient
├── Connection Management
│   ├── aiohttp ClientSession
│   ├── SSL Context Configuration
│   └── Cookie Jar for Session Persistence
├── Authentication
│   ├── Login Endpoint Call
│   ├── Credential Validation
│   └── Session Cookie Storage
├── Request Methods
│   ├── GET (read operations)
│   └── POST (write operations)
└── Logging
    ├── Structured Logging
    ├── Sensitive Data Redaction
    └── Correlation ID Tracking
```

## Usage

### Basic Usage

```python
from unifi_mcp.config.loader import load_config, UniFiConfig
from unifi_mcp.unifi_client import UniFiClient

# Load configuration from environment
config = load_config()

# Create client
client = UniFiClient(config.unifi)

# Connect and authenticate
await client.connect()

# Make API requests
devices = await client.get("/api/s/{site}/stat/device")
print(f"Found {len(devices['data'])} devices")

# Close connection
await client.close()
```

### Using Context Manager (Recommended)

```python
from unifi_mcp.config.loader import load_config
from unifi_mcp.unifi_client import UniFiClient

config = load_config()

# Context manager handles connect/close automatically
async with UniFiClient(config.unifi) as client:
    devices = await client.get("/api/s/{site}/stat/device")
    print(f"Found {len(devices['data'])} devices")
```

### Manual Configuration

```python
from unifi_mcp.config.loader import UniFiConfig
from unifi_mcp.unifi_client import UniFiClient

# Create configuration manually
config = UniFiConfig(
    host="192.168.1.1",
    port=443,
    username="admin",
    password="your-password",
    site="default",
    verify_ssl=False,  # Set to True for valid certificates
    retry={}
)

client = UniFiClient(config)
await client.connect()
```

## API Methods

### `connect()`

Initialize HTTP session and authenticate with the controller.

```python
await client.connect()
```

**Raises:**
- `ConnectionError`: If connection to controller fails
- `AuthenticationError`: If authentication fails

### `close()`

Close the HTTP session and clean up resources.

```python
await client.close()
```

### `get(endpoint, params=None)`

Make GET request to UniFi API.

```python
# List all devices
devices = await client.get("/api/s/{site}/stat/device")

# List devices with filter
switches = await client.get("/api/s/{site}/stat/device", params={"type": "usw"})
```

**Parameters:**
- `endpoint` (str): API endpoint (use `{site}` placeholder for site name)
- `params` (dict, optional): Query parameters

**Returns:**
- `dict`: JSON response data

**Raises:**
- `UniFiClientError`: If request fails

### `post(endpoint, data=None, json=None)`

Make POST request to UniFi API.

```python
# Update firewall rule
result = await client.post(
    "/api/s/{site}/rest/firewallrule/123",
    json={"enabled": True}
)
```

**Parameters:**
- `endpoint` (str): API endpoint
- `data` (dict, optional): Form data
- `json` (dict, optional): JSON data

**Returns:**
- `dict`: JSON response data

**Raises:**
- `UniFiClientError`: If request fails

## Configuration

The client requires the following configuration:

```yaml
unifi:
  host: "${UNIFI_HOST}"              # Controller hostname or IP
  port: "${UNIFI_PORT:443}"          # Controller port (default: 443)
  username: "${UNIFI_USERNAME}"      # Admin username
  password: "${UNIFI_PASSWORD}"      # Admin password
  site: "${UNIFI_SITE:default}"      # Site name (default: default)
  verify_ssl: "${UNIFI_VERIFY_SSL:false}"  # SSL verification
```

### Environment Variables

Set these environment variables or create a `.env` file:

```bash
UNIFI_HOST=192.168.1.1
UNIFI_PORT=443
UNIFI_USERNAME=admin
UNIFI_PASSWORD=your-password
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
```

## SSL Certificate Handling

### Self-Signed Certificates

By default, the client accepts self-signed certificates (common for UniFi controllers):

```python
config = UniFiConfig(
    host="192.168.1.1",
    verify_ssl=False  # Accept self-signed certificates
)
```

**Warning:** A warning will be logged when SSL verification is disabled.

### Valid Certificates

For controllers with valid SSL certificates:

```python
config = UniFiConfig(
    host="unifi.example.com",
    verify_ssl=True  # Verify SSL certificates
)
```

## Error Handling

The client provides specific exception types for different error scenarios:

### `UniFiClientError`

Base exception for all client errors.

```python
try:
    await client.get("/api/s/{site}/stat/device")
except UniFiClientError as e:
    print(f"Client error: {e}")
```

### `AuthenticationError`

Raised when authentication fails.

```python
try:
    await client.connect()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Check credentials and try again
```

**Common causes:**
- Invalid username or password
- Incorrect controller URL
- Network connectivity issues

### `ConnectionError`

Raised when connection to controller fails.

```python
try:
    await client.connect()
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Check network connectivity and controller URL
```

**Common causes:**
- Controller is offline
- Incorrect host or port
- Firewall blocking connection
- DNS resolution failure

## Logging

The client uses structured logging with automatic sensitive data redaction.

### Enable Logging

```python
from unifi_mcp.utils.logging import setup_logging

# Set up logging
setup_logging(
    log_level="INFO",
    include_correlation_id=True
)
```

### Log Levels

- **DEBUG**: Detailed request/response information
- **INFO**: Connection status, authentication, high-level operations
- **WARNING**: SSL verification disabled, retry attempts
- **ERROR**: Request failures, authentication errors

### Sensitive Data Redaction

The client automatically redacts sensitive information from logs:
- Passwords
- Tokens
- API keys
- Session cookies

```python
# This will log with password redacted
await client.connect()
# Log output: "Attempting authentication {'username': 'admin', 'password': '[REDACTED]'}"
```

## Common API Endpoints

### Device Management

```python
# List all devices
devices = await client.get("/api/s/{site}/stat/device")

# Get specific device
device = await client.get("/api/s/{site}/stat/device/MAC_ADDRESS")
```

### Client Management

```python
# List all clients
clients = await client.get("/api/s/{site}/stat/sta")

# Get specific client
client_info = await client.get("/api/s/{site}/stat/user/MAC_ADDRESS")
```

### Network Configuration

```python
# List networks
networks = await client.get("/api/s/{site}/rest/networkconf")

# List WLANs
wlans = await client.get("/api/s/{site}/rest/wlanconf")
```

### Firewall Rules

```python
# List firewall rules
rules = await client.get("/api/s/{site}/rest/firewallrule")

# Update firewall rule
result = await client.post(
    "/api/s/{site}/rest/firewallrule/RULE_ID",
    json={"enabled": False}
)
```

## Best Practices

### 1. Use Context Manager

Always use the async context manager to ensure proper cleanup:

```python
async with UniFiClient(config.unifi) as client:
    # Your code here
    pass
# Connection automatically closed
```

### 2. Handle Errors Gracefully

Catch specific exceptions for better error handling:

```python
try:
    async with UniFiClient(config.unifi) as client:
        devices = await client.get("/api/s/{site}/stat/device")
except AuthenticationError:
    print("Invalid credentials")
except ConnectionError:
    print("Controller unreachable")
except UniFiClientError as e:
    print(f"Request failed: {e}")
```

### 3. Enable Logging for Debugging

Use DEBUG level logging during development:

```python
setup_logging(log_level="DEBUG")
```

### 4. Secure Credentials

Never hardcode credentials. Use environment variables or .env files:

```python
# Good
config = load_config()  # Loads from environment

# Bad
config = UniFiConfig(password="hardcoded-password")
```

### 5. Use Site Placeholder

Use the `{site}` placeholder in endpoints for automatic site substitution:

```python
# Good
await client.get("/api/s/{site}/stat/device")

# Also works, but less flexible
await client.get("/api/s/default/stat/device")
```

## Testing

The client includes comprehensive unit tests. Run them with:

```bash
pytest tests/test_unifi_client.py -v
```

### Test Coverage

- Initialization and configuration
- SSL context creation
- Connection and authentication
- Session management
- GET and POST requests
- Error handling
- Logging and redaction
- Context manager support

## Troubleshooting

### Authentication Fails

**Symptom:** `AuthenticationError: Invalid username or password`

**Solutions:**
1. Verify credentials in environment variables
2. Check that controller is accessible
3. Ensure user has admin privileges
4. Try logging in via web interface to verify credentials

### Connection Timeout

**Symptom:** `ConnectionError: Failed to connect to https://...`

**Solutions:**
1. Verify controller IP address and port
2. Check network connectivity
3. Ensure controller is running
4. Check firewall rules

### SSL Certificate Error

**Symptom:** SSL verification errors

**Solutions:**
1. Set `verify_ssl=False` for self-signed certificates
2. Install valid SSL certificate on controller
3. Add controller certificate to system trust store

### Session Expires

**Symptom:** Requests fail after some time

**Solutions:**
1. The client handles session expiry automatically
2. If issues persist, reconnect the client
3. Check controller session timeout settings

## Performance Considerations

### Connection Pooling

The client reuses the HTTP session for all requests, providing connection pooling benefits:
- Reduced connection overhead
- Keep-alive connections
- Better performance for multiple requests

### Memory Usage

The client is lightweight:
- Minimal memory footprint
- Efficient async operations
- Automatic resource cleanup

### Concurrent Requests

The client supports concurrent requests:

```python
async with UniFiClient(config.unifi) as client:
    # Make concurrent requests
    devices, clients = await asyncio.gather(
        client.get("/api/s/{site}/stat/device"),
        client.get("/api/s/{site}/stat/sta")
    )
```

## Related Documentation

- [Configuration Guide](CONFIGURATION.md)
- [Logging Guide](LOGGING.md)
- [API Reference](../README.md)
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)

## Examples

See the `examples/` directory for complete working examples:
- `unifi_client_demo.py`: Basic usage demonstration
- More examples coming soon

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the test suite for usage examples
3. Check UniFi controller logs
4. Consult UniFi API documentation
