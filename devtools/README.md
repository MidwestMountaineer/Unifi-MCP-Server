# Developer Tools

This directory contains tools for testing and debugging the UniFi MCP Server.

## Dev Console

The dev console provides an interactive command-line interface for testing MCP tools without needing a full MCP client.

### Usage

```bash
# From the project root
python -m devtools.dev_console
```

Or:

```bash
# From the devtools directory
cd devtools
python dev_console.py
```

### Features

- **List Tools**: View all available tools organized by category
- **Invoke Tools**: Execute tools with custom JSON arguments
- **View Results**: See formatted tool results
- **Test Authentication**: Verify UniFi controller connection
- **Load Credentials**: Automatically loads from .env file

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `list` | List all available tools | `list` |
| `list <category>` | List tools in a specific category | `list security` |
| `categories` | List all tool categories | `categories` |
| `invoke <tool> [args]` | Invoke a tool with JSON arguments | `invoke unifi_list_devices {"device_type": "switch"}` |
| `help` | Show help message | `help` |
| `exit` | Exit the console | `exit` |

### Examples

#### List all tools
```
> list
```

#### List tools in a category
```
> list network_discovery
```

#### Invoke a tool without arguments
```
> invoke unifi_list_devices
```

#### Invoke a tool with arguments
```
> invoke unifi_list_devices {"device_type": "switch"}
```

#### Get device details
```
> invoke unifi_get_device_details {"device_id": "abc123"}
```

#### Get client statistics
```
> invoke unifi_get_client_stats {"mac_address": "aa:bb:cc:dd:ee:ff"}
```

#### Test write operations (requires confirmation)
```
> invoke unifi_toggle_firewall_rule {"rule_id": "123", "enabled": false, "confirm": true}
```

### Prerequisites

1. **Configuration**: Ensure you have a `.env` file with your UniFi credentials:
   ```bash
   UNIFI_HOST=192.168.1.1
   UNIFI_API_KEY=your_api_key_here
   # OR
   UNIFI_USERNAME=admin
   UNIFI_PASSWORD=your_password
   ```

2. **Dependencies**: Install required packages:
   ```bash
   pip install -e .
   ```

3. **Network Access**: Ensure you can reach your UniFi controller from your development machine.

### Troubleshooting

#### Connection Failed
```
✗ Failed to connect to UniFi controller: Connection refused
```

**Solutions**:
- Verify UNIFI_HOST is correct
- Check network connectivity to controller
- Ensure controller is running
- Verify firewall rules allow access

#### Authentication Failed
```
✗ Failed to connect to UniFi controller: Authentication failed
```

**Solutions**:
- Verify UNIFI_API_KEY or UNIFI_USERNAME/UNIFI_PASSWORD are correct
- Check that the user has appropriate permissions
- Ensure API key hasn't expired

#### Tool Not Found
```
Unknown tool: unifi_list_device
```

**Solutions**:
- Use `list` to see available tools
- Check tool name spelling (e.g., `unifi_list_devices` not `unifi_list_device`)
- Verify tool is enabled in config.yaml

#### Invalid JSON Arguments
```
Invalid JSON arguments: Expecting property name enclosed in double quotes
```

**Solutions**:
- Use double quotes for JSON keys and string values
- Valid: `{"device_type": "switch"}`
- Invalid: `{device_type: 'switch'}`

### Tips

1. **Tab Completion**: Not available yet, but you can copy/paste tool names from `list` output

2. **JSON Formatting**: Use a JSON validator if you're having trouble with arguments

3. **Testing Write Operations**: 
   - Write operations are disabled by default
   - Enable in config.yaml: `write_operations.enabled: true`
   - Always include `"confirm": true` in arguments

4. **Debugging**: 
   - Set `LOG_LEVEL=DEBUG` in .env for verbose logging
   - Check logs for detailed error messages

5. **Quick Testing**:
   - Start with simple tools like `unifi_list_devices`
   - Test authentication before complex operations
   - Use `categories` to explore available tool groups

### Development

The dev console is designed to be simple and extensible. Key features:

- **Async Support**: Full async/await support for tool invocations
- **Error Handling**: Graceful error handling with helpful messages
- **Logging**: Integrates with server logging system
- **Configuration**: Uses same config as production server

### Future Enhancements

Potential improvements for the dev console:

- [ ] Command history (up/down arrows)
- [ ] Tab completion for tool names
- [ ] Argument templates for common tools
- [ ] Result export (JSON, CSV)
- [ ] Batch tool execution
- [ ] Performance timing
- [ ] Interactive argument builder
- [ ] Tool documentation viewer

### Related Tools

- **MCP Inspector**: For protocol-level testing (see below)
- **Example Scripts**: See `examples/` directory for usage examples
- **Unit Tests**: See `tests/` directory for test cases

## MCP Inspector

The MCP Inspector is an official tool for testing MCP protocol compliance and validating tool schemas. We provide wrapper scripts to make it easy to use.

### Quick Start

```bash
# Linux/macOS
./devtools/mcp_inspector.sh

# Windows PowerShell
.\devtools\mcp_inspector.ps1
```

This launches an interactive web-based UI where you can:
- Browse all available tools
- Test tools with custom arguments
- Inspect JSON-RPC messages
- Validate protocol compliance

### Testing Modes

| Mode | Description | Command |
|------|-------------|---------|
| **interactive** | Launch web UI (default) | `./mcp_inspector.sh` |
| **validate** | Validate protocol compliance | `./mcp_inspector.sh validate` |
| **list-tools** | List all available tools | `./mcp_inspector.sh list-tools` |
| **test-tool** | Test a specific tool | `./mcp_inspector.sh test-tool unifi_list_devices` |
| **test-all** | Test all tools | `./mcp_inspector.sh test-all` |

### Examples

```bash
# Validate protocol compliance
./devtools/mcp_inspector.sh validate

# List all tools
./devtools/mcp_inspector.sh list-tools

# Test a tool without arguments
./devtools/mcp_inspector.sh test-tool unifi_list_devices

# Test a tool with arguments
./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'

# Test all tools (smoke test)
./devtools/mcp_inspector.sh test-all
```

### Prerequisites

The inspector requires:
- Python 3.11+
- Node.js and npx
- UniFi MCP Server installed (`pip install -e .`)
- Valid `.env` file with credentials

The wrapper scripts will automatically check prerequisites and provide helpful error messages.

### Documentation

For comprehensive documentation, see:
- **[MCP Inspector Guide](../docs/MCP-INSPECTOR-GUIDE.md)**: Complete guide with troubleshooting
- **[MCP Protocol Spec](https://spec.modelcontextprotocol.io/)**: Official specification

### When to Use Inspector vs Dev Console

**Use MCP Inspector when:**
- Testing protocol compliance
- Validating tool schemas
- Debugging MCP client integration
- Inspecting raw JSON-RPC messages
- Testing with a web UI

**Use Dev Console when:**
- Quick tool testing during development
- Testing with Python directly
- Debugging tool logic
- Batch testing with scripts
- Command-line workflow
