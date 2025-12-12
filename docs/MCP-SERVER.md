# MCP Server Implementation

## Overview

The UniFi MCP Server implements the Model Context Protocol (MCP) using the official Python SDK. It provides a bridge between AI agents and the UniFi Network Controller, exposing network management capabilities through a well-designed tool interface.

## Architecture

### Core Components

1. **UniFiMCPServer** (`server.py`)
   - Main server class implementing MCP protocol
   - Handles tool registration and discovery
   - Routes tool invocations to handlers
   - Manages UniFi client lifecycle

2. **MCP Protocol Handlers**
   - `tools/list`: Returns available tools
   - `tools/call`: Executes tool invocations

3. **Entry Point** (`__main__.py`)
   - Configuration loading
   - Logging setup
   - Server initialization
   - Graceful shutdown handling

## MCP Protocol Implementation

### Stdio Transport

The server uses stdio transport for communication with MCP clients:
- **Input**: JSON-RPC requests via stdin
- **Output**: JSON-RPC responses via stdout
- **Protocol**: MCP specification

### Handshake and Initialization

The server handles the MCP handshake automatically through the SDK:

```python
async with stdio_server() as (read_stream, write_stream):
    await self.server.run(
        read_stream,
        write_stream,
        self.server.create_initialization_options()
    )
```

### Tool Discovery (tools/list)

The `tools/list` endpoint returns all available tools:

```python
@self.server.list_tools()
async def list_tools() -> List[Tool]:
    """Return list of available tools."""
    return self._get_available_tools()
```

Tools are filtered based on configuration:
- Disabled tool categories are excluded
- Write operations can be globally disabled
- Individual tools can be enabled/disabled

### Tool Invocation (tools/call)

The `tools/call` endpoint routes tool invocations:

```python
@self.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute tool and return results."""
    # Validate tool exists
    # Execute handler
    # Format response
    # Handle errors
```

## Tool Registration

Tools are registered with the server using the `register_tool` method:

```python
server.register_tool(
    name="unifi_list_devices",
    description="List all UniFi devices",
    input_schema={
        "type": "object",
        "properties": {
            "device_type": {
                "type": "string",
                "enum": ["all", "switch", "ap", "gateway"]
            }
        }
    },
    handler=list_devices_handler
)
```

### Tool Handler Signature

Tool handlers must be async functions with this signature:

```python
async def tool_handler(
    client: UniFiClient,
    **kwargs
) -> Any:
    """Tool handler.
    
    Args:
        client: UniFi API client
        **kwargs: Tool-specific parameters
    
    Returns:
        Tool result (will be converted to string)
    """
    pass
```

## Error Handling

### Error Types

1. **Configuration Errors**
   - Missing credentials
   - Invalid configuration values
   - Fail fast on startup

2. **Connection Errors**
   - UniFi controller unreachable
   - Authentication failures
   - Network timeouts

3. **Tool Invocation Errors**
   - Unknown tool
   - Invalid arguments
   - Execution failures

### Error Response Format

Errors are returned as TextContent with descriptive messages:

```python
return [TextContent(
    type="text",
    text=f"Error: {error_message}"
)]
```

## Logging

The server uses structured logging with:
- Correlation IDs for request tracing
- Sensitive data redaction
- Configurable log levels
- Optional file logging

Example log output:

```
2025-10-08 10:30:15 INFO [server] Initializing UniFi MCP Server
  server_name: unifi-network-mcp
  unifi_host: 192.168.1.1
  unifi_site: default

2025-10-08 10:30:16 INFO [server] Handling tool invocation
  tool_name: unifi_list_devices
  arguments: {"device_type": "switch"}

2025-10-08 10:30:17 INFO [server] Tool invocation successful
  tool_name: unifi_list_devices
```

## Server Lifecycle

### Startup Sequence

1. Load configuration from YAML and environment variables
2. Setup logging
3. Create UniFiMCPServer instance
4. Register MCP protocol handlers
5. Connect to UniFi controller
6. Start stdio transport
7. Begin processing requests

### Shutdown Sequence

1. Receive shutdown signal (Ctrl+C or client disconnect)
2. Stop accepting new requests
3. Disconnect from UniFi controller
4. Clean up resources
5. Exit gracefully

## Running the Server

### Command Line

```bash
# Run directly
python -m unifi_mcp

# Run via uvx (for MCP clients)
uvx unifi-mcp-server
```

### Environment Variables

Required:
- `UNIFI_HOST`: UniFi controller hostname/IP
- `UNIFI_USERNAME`: Username (if not using API key)
- `UNIFI_PASSWORD`: Password (if not using API key)
- `UNIFI_API_KEY`: API key (alternative to username/password)

Optional:
- `UNIFI_PORT`: Controller port (default: 443)
- `UNIFI_SITE`: Site name (default: default)
- `UNIFI_VERIFY_SSL`: Verify SSL certificates (default: false)

### Configuration File

See `config/config.yaml` for full configuration options.

## Integration with MCP Clients

### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-mcp-server"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password"
      }
    }
  }
}
```

### Claude Desktop

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-mcp-server"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Testing

### Unit Tests

Run unit tests:

```bash
pytest tests/test_server.py -v
```

### Integration Tests

Test with MCP Inspector:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python -m unifi_mcp
```

### Manual Testing

Use the demo script:

```bash
python examples/server_demo.py
```

## Performance Considerations

### Memory Usage

- Target: <100MB at idle
- Connection pooling reduces overhead
- Caching minimizes API calls

### Response Times

- Target: <2 seconds for read operations
- Caching improves response times
- Concurrent request limiting prevents overload

### Startup Time

- Target: <5 seconds
- Lazy loading of tool modules
- Parallel initialization where possible

## Security

### Credential Management

- Never log credentials
- Never include credentials in responses
- Support environment variables and .env files
- Validate credentials on startup

### Write Operations

- Disabled by default
- Require explicit confirmation
- Full operation logging
- Clear error messages

### Network Security

- HTTPS by default
- Support for self-signed certificates
- Connection timeouts
- SSL certificate validation

## Future Enhancements

### Planned Features

1. **Tool Registry System** (Task 9)
   - Dynamic tool discovery
   - Tool categories/groups
   - Tool filtering

2. **Base Tool Class** (Task 10)
   - Input validation
   - Output formatting
   - Error handling

3. **Network Discovery Tools** (Task 11-13)
   - Device listing and details
   - Client listing and details
   - Network and WLAN information

4. **Security Tools** (Task 14-16)
   - Firewall rules
   - Routing and port forwards
   - IPS status

5. **Statistics Tools** (Task 17-19)
   - Network and system stats
   - Client and device stats
   - DPI and alerts

### Extensibility

The server is designed for easy extension:
- Simple tool registration API
- Consistent handler pattern
- Modular tool organization
- Configuration-based tool filtering

## Troubleshooting

### Server Won't Start

Check:
- Configuration file exists and is valid
- Required environment variables are set
- UniFi controller is reachable
- Credentials are correct

### Tools Not Appearing

Check:
- Tool category is enabled in config
- Tool is registered in server
- No errors in logs

### Tool Invocation Fails

Check:
- Tool arguments are valid
- UniFi controller is responding
- Network connectivity
- Logs for detailed error messages

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)

## Related Documentation

- [Configuration Guide](CONFIGURATION.md)
- [UniFi Client](UNIFI-CLIENT.md)
- [Logging](LOGGING.md)
- [Retry Logic](RETRY-LOGIC.md)
