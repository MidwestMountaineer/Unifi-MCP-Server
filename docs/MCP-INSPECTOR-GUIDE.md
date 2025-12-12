# MCP Inspector Integration Guide

This guide explains how to use the MCP Inspector to test and validate the UniFi MCP Server.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Testing Modes](#testing-modes)
- [Protocol Compliance](#protocol-compliance)
- [Tool Schema Validation](#tool-schema-validation)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The MCP Inspector is an official tool from Anthropic for testing Model Context Protocol servers. It provides:

- **Interactive Testing**: Launch a web-based UI to test tools interactively
- **Protocol Validation**: Verify that the server implements the MCP protocol correctly
- **Schema Testing**: Validate that all tool schemas are properly formatted
- **Request/Response Inspection**: See the raw JSON-RPC messages exchanged

Our wrapper scripts (`mcp_inspector.sh` for Linux/macOS, `mcp_inspector.ps1` for Windows) make it easy to use the inspector with the UniFi MCP Server.

## Prerequisites

### Required Software

1. **Python 3.11+**
   ```bash
   python3 --version  # Should show 3.11 or higher
   ```

2. **Node.js and npx**
   ```bash
   npx --version  # Should show version number
   ```
   
   If not installed:
   - **Windows**: Download from [nodejs.org](https://nodejs.org/)
   - **macOS**: `brew install node`
   - **Linux**: `sudo apt install nodejs npm` or equivalent

3. **UniFi MCP Server**
   ```bash
   # Install in development mode
   cd projects/unifi-mcp-server
   pip install -e .
   ```

4. **Environment Configuration**
   ```bash
   # Copy example and configure
   cp .env.example .env
   # Edit .env with your UniFi credentials
   ```

### Verify Prerequisites

The wrapper scripts will automatically check prerequisites:

```bash
# Linux/macOS
./devtools/mcp_inspector.sh validate

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode validate
```

## Quick Start

### Interactive Mode (Recommended for First-Time Users)

This launches a web-based UI where you can explore and test tools:

```bash
# Linux/macOS
cd projects/unifi-mcp-server
./devtools/mcp_inspector.sh

# Windows PowerShell
cd projects\unifi-mcp-server
.\devtools\mcp_inspector.ps1
```

The inspector will:
1. Start the UniFi MCP Server
2. Launch a web browser with the inspector UI
3. Allow you to list tools, invoke them, and inspect messages

**What you'll see:**
- A list of all available tools
- Input forms for tool arguments
- Real-time request/response messages
- Error messages if something goes wrong

### List All Tools

See what tools are available:

```bash
# Linux/macOS
./devtools/mcp_inspector.sh list-tools

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode list-tools
```

**Example Output:**
```
NETWORK_DISCOVERY:
  - unifi_list_devices
    List all UniFi devices (switches, APs, gateways)
  - unifi_get_device_details
    Get detailed information about a specific device
  ...

SECURITY:
  - unifi_list_firewall_rules
    List all firewall policies and rules
  ...

Total: 28 tools
```

## Testing Modes

### 1. Interactive Mode

**Purpose**: Explore tools and test them interactively

**Usage:**
```bash
# Linux/macOS
./devtools/mcp_inspector.sh interactive

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode interactive
```

**Best For:**
- First-time exploration
- Testing tools with different arguments
- Debugging tool behavior
- Understanding request/response format

**Tips:**
- Use the web UI to select tools from a dropdown
- Fill in arguments using the form
- Click "Invoke" to execute the tool
- Inspect the JSON-RPC messages in the right panel

### 2. Validate Mode

**Purpose**: Verify protocol compliance and schema validity

**Usage:**
```bash
# Linux/macOS
./devtools/mcp_inspector.sh validate

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode validate
```

**What It Checks:**
- ✓ Server initialization
- ✓ Tool listing endpoint
- ✓ All tools have required fields (name, description, inputSchema)
- ✓ Schemas are properly formatted

**Example Output:**
```
=== Validating Protocol Compliance ===
✓ Server initialization successful
✓ Tool listing successful (28 tools)
✓ All tool schemas valid

✓ Protocol compliance validation passed
```

### 3. List Tools Mode

**Purpose**: Quick overview of available tools

**Usage:**
```bash
# Linux/macOS
./devtools/mcp_inspector.sh list-tools

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode list-tools
```

**Output Format:**
- Tools grouped by category
- Tool name and description
- Total count

### 4. Test Tool Mode

**Purpose**: Test a specific tool with custom arguments

**Usage:**
```bash
# Linux/macOS
./devtools/mcp_inspector.sh test-tool unifi_list_devices
./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices
.\devtools\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices -ToolArgs '{"device_type": "switch"}'
```

**Example Output:**
```
=== Testing Tool: unifi_list_devices ===
Tool: unifi_list_devices
Arguments: {
  "device_type": "switch"
}

Result:
{
  "devices": [
    {
      "id": "abc123",
      "name": "Main Switch",
      "type": "switch",
      ...
    }
  ],
  "total": 1
}

✓ Tool invocation successful
```

### 5. Test All Mode

**Purpose**: Smoke test all tools that don't require arguments

**Usage:**
```bash
# Linux/macOS
./devtools/mcp_inspector.sh test-all

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode test-all
```

**What It Does:**
- Tests all tools that have no required parameters
- Skips tools that require arguments (e.g., device_id, mac_address)
- Reports pass/fail/skip for each tool

**Example Output:**
```
=== Testing All Tools ===
✓ unifi_list_devices
✓ unifi_list_clients
✓ unifi_list_networks
⊘ unifi_get_device_details (requires arguments: device_id)
✓ unifi_get_network_stats
...

Results: 15 passed, 0 failed, 13 skipped
```

## Protocol Compliance

### What Is Protocol Compliance?

The MCP protocol defines specific requirements for:
- **Initialization**: Handshake between client and server
- **Tool Discovery**: Listing available tools
- **Tool Invocation**: Calling tools with arguments
- **Error Handling**: Returning errors in the correct format

### Why It Matters

Protocol compliance ensures:
- ✓ Works with all MCP clients (Kiro, Claude Desktop, etc.)
- ✓ Tools are discoverable
- ✓ Errors are handled gracefully
- ✓ Future compatibility

### How to Validate

Run the validation mode:

```bash
# Linux/macOS
./devtools/mcp_inspector.sh validate

# Windows PowerShell
.\devtools\mcp_inspector.ps1 -Mode validate
```

### Common Issues

**Issue**: Server initialization failed
- **Cause**: Missing or invalid configuration
- **Fix**: Check .env file has all required variables

**Issue**: Tool missing name/description/inputSchema
- **Cause**: Tool definition incomplete
- **Fix**: Update tool class to include all required fields

**Issue**: Invalid schema format
- **Cause**: inputSchema not valid JSON Schema
- **Fix**: Validate schema against JSON Schema spec

## Tool Schema Validation

### Schema Requirements

Every tool must have:

1. **Name** (string): Unique identifier (e.g., `unifi_list_devices`)
2. **Description** (string): Brief description under 200 chars
3. **Input Schema** (object): JSON Schema defining parameters

### Example Valid Schema

```python
{
    "name": "unifi_list_devices",
    "description": "List all UniFi devices (switches, APs, gateways)",
    "inputSchema": {
        "type": "object",
        "properties": {
            "device_type": {
                "type": "string",
                "enum": ["all", "switch", "ap", "gateway"],
                "description": "Filter by device type",
                "default": "all"
            }
        },
        "required": []  # No required parameters
    }
}
```

### Testing Schemas

The validator checks:
- ✓ All required fields present
- ✓ Schema is valid JSON Schema
- ✓ Descriptions are clear and concise
- ✓ Enums are properly defined
- ✓ Required parameters are marked

### Common Schema Issues

**Issue**: Missing description
```python
# Bad
"device_type": {
    "type": "string"
}

# Good
"device_type": {
    "type": "string",
    "description": "Filter by device type"
}
```

**Issue**: Invalid enum
```python
# Bad
"device_type": {
    "type": "string",
    "enum": "switch"  # Should be array
}

# Good
"device_type": {
    "type": "string",
    "enum": ["switch", "ap", "gateway"]
}
```

## Troubleshooting

### Prerequisites Check Failed

**Symptom**: Script reports missing prerequisites

**Solutions:**

1. **Python not found or wrong version**
   ```bash
   # Check version
   python3 --version
   
   # Install Python 3.11+ if needed
   # Windows: Download from python.org
   # macOS: brew install python@3.11
   # Linux: sudo apt install python3.11
   ```

2. **npx not found**
   ```bash
   # Install Node.js (includes npx)
   # Windows: Download from nodejs.org
   # macOS: brew install node
   # Linux: sudo apt install nodejs npm
   ```

3. **UniFi MCP Server not installed**
   ```bash
   cd projects/unifi-mcp-server
   pip install -e .
   ```

4. **.env file missing**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

### Connection Failed

**Symptom**: "Failed to connect to UniFi controller"

**Solutions:**

1. **Check UniFi controller is reachable**
   ```bash
   ping 192.168.1.1  # Or your controller IP
   ```

2. **Verify credentials in .env**
   ```bash
   # Check these variables
   UNIFI_HOST=192.168.1.1
   UNIFI_API_KEY=your_api_key_here
   # OR
   UNIFI_USERNAME=admin
   UNIFI_PASSWORD=your_password
   ```

3. **Check SSL certificate settings**
   ```bash
   # If using self-signed certificate
   UNIFI_VERIFY_SSL=false
   ```

4. **Test with dev console first**
   ```bash
   python -m devtools.dev_console
   # Try: list
   ```

### Tool Invocation Failed

**Symptom**: Tool returns error when invoked

**Solutions:**

1. **Check required parameters**
   ```bash
   # List tools to see required parameters
   ./devtools/mcp_inspector.sh list-tools
   ```

2. **Validate JSON arguments**
   ```bash
   # Use a JSON validator
   echo '{"device_type": "switch"}' | python -m json.tool
   ```

3. **Check tool is enabled**
   ```bash
   # Verify in config.yaml
   cat src/unifi_mcp/config/config.yaml
   ```

4. **Test with simpler arguments**
   ```bash
   # Start with no arguments
   ./devtools/mcp_inspector.sh test-tool unifi_list_devices
   
   # Then add arguments
   ./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'
   ```

### Inspector Won't Start

**Symptom**: Interactive mode fails to launch

**Solutions:**

1. **Check port 3000 is available**
   ```bash
   # Windows
   netstat -ano | findstr :3000
   
   # Linux/macOS
   lsof -i :3000
   ```

2. **Try manual inspector launch**
   ```bash
   npx @modelcontextprotocol/inspector python3 -m unifi_mcp
   ```

3. **Check browser opens automatically**
   - If not, manually open: http://localhost:3000

4. **Check firewall settings**
   - Allow connections to localhost:3000

## Advanced Usage

### Custom Inspector Configuration

You can run the inspector manually with custom options:

```bash
# Specify custom port
npx @modelcontextprotocol/inspector --port 8080 python3 -m unifi_mcp

# Enable verbose logging
LOG_LEVEL=DEBUG npx @modelcontextprotocol/inspector python3 -m unifi_mcp

# Use custom config file
CONFIG_FILE=/path/to/config.yaml npx @modelcontextprotocol/inspector python3 -m unifi_mcp
```

### Testing Write Operations

Write operations require confirmation:

```bash
# Test firewall rule toggle
./devtools/mcp_inspector.sh test-tool unifi_toggle_firewall_rule \
  '{"rule_id": "abc123", "enabled": false, "confirm": true}'
```

**Important**: Write operations are disabled by default. Enable in `config.yaml`:

```yaml
tools:
  write_operations:
    enabled: true
```

### Batch Testing

Create a script to test multiple tools:

```bash
#!/bin/bash
# test_all_network_tools.sh

tools=(
  "unifi_list_devices"
  "unifi_list_clients"
  "unifi_list_networks"
  "unifi_list_wlans"
  "unifi_get_network_stats"
)

for tool in "${tools[@]}"; do
  echo "Testing $tool..."
  ./devtools/mcp_inspector.sh test-tool "$tool"
done
```

### Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Validate MCP Protocol
  run: |
    cd projects/unifi-mcp-server
    ./devtools/mcp_inspector.sh validate

- name: Test All Tools
  run: |
    cd projects/unifi-mcp-server
    ./devtools/mcp_inspector.sh test-all
```

### Debugging Protocol Issues

Enable verbose logging to see raw JSON-RPC messages:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Run inspector
./devtools/mcp_inspector.sh interactive
```

In the inspector UI:
1. Open browser developer tools (F12)
2. Go to Network tab
3. Invoke a tool
4. Inspect the WebSocket messages

## Best Practices

### 1. Start with Validation

Always validate protocol compliance first:

```bash
./devtools/mcp_inspector.sh validate
```

### 2. Test Tools Incrementally

Don't test all tools at once. Start with simple ones:

```bash
# Start simple
./devtools/mcp_inspector.sh test-tool unifi_list_devices

# Add complexity
./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'

# Test with real IDs
./devtools/mcp_inspector.sh test-tool unifi_get_device_details '{"device_id": "abc123"}'
```

### 3. Use Interactive Mode for Exploration

When learning or debugging:
- Use interactive mode to explore tools
- Try different arguments
- Inspect request/response messages
- Understand error formats

### 4. Automate Regression Testing

Add inspector tests to your workflow:

```bash
# Before committing changes
./devtools/mcp_inspector.sh validate
./devtools/mcp_inspector.sh test-all
```

### 5. Document Tool Behavior

Use inspector to document:
- Expected inputs
- Example outputs
- Error conditions
- Edge cases

## Related Documentation

- **[Dev Console Guide](DEV-CONSOLE-QUICK-START.md)**: Interactive Python console for testing
- **[All Tools Reference](ALL-TOOLS-REFERENCE.md)**: Complete tool documentation
- **[Kiro Setup Guide](KIRO-SETUP-GUIDE.md)**: Using with Kiro AI assistant
- **[MCP Protocol Spec](https://spec.modelcontextprotocol.io/)**: Official MCP specification

## Support

### Getting Help

1. **Check Prerequisites**: Run validation mode
2. **Review Logs**: Set `LOG_LEVEL=DEBUG`
3. **Test with Dev Console**: Simpler environment for debugging
4. **Check Documentation**: See related guides above

### Reporting Issues

When reporting issues, include:
- Operating system and version
- Python version (`python3 --version`)
- Node.js version (`node --version`)
- Error messages (full output)
- Steps to reproduce

### Contributing

Found a bug or have a suggestion? Contributions welcome!

1. Test your changes with the inspector
2. Ensure validation passes
3. Update documentation
4. Submit a pull request

---

**Last Updated**: October 9, 2025
**Version**: 0.1.0
