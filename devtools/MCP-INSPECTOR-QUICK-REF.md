# MCP Inspector Quick Reference

## Quick Start

```bash
# Interactive mode (web UI)
./devtools/mcp_inspector.sh

# Windows
.\devtools\mcp_inspector.ps1
```

## Common Commands

### Validate Protocol Compliance
```bash
# Linux/macOS
./devtools/mcp_inspector.sh validate

# Windows
.\devtools\mcp_inspector.ps1 -Mode validate
```

### List All Tools
```bash
# Linux/macOS
./devtools/mcp_inspector.sh list-tools

# Windows
.\devtools\mcp_inspector.ps1 -Mode list-tools
```

### Test a Specific Tool
```bash
# Linux/macOS
./devtools/mcp_inspector.sh test-tool unifi_list_devices
./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'

# Windows
.\devtools\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices
.\devtools\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices -ToolArgs '{"device_type": "switch"}'
```

### Test All Tools (Smoke Test)
```bash
# Linux/macOS
./devtools/mcp_inspector.sh test-all

# Windows
.\devtools\mcp_inspector.ps1 -Mode test-all
```

## Prerequisites

- ✅ Python 3.11+
- ✅ Node.js and npx
- ✅ UniFi MCP Server installed (`pip install -e .`)
- ✅ Valid `.env` file

## Troubleshooting

### Prerequisites Check Failed
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check npx
npx --version

# Install server
pip install -e .

# Create .env file
cp .env.example .env
# Edit .env with your credentials
```

### PowerShell Execution Policy Error
```powershell
# Run with bypass
powershell -ExecutionPolicy Bypass -File .\devtools\mcp_inspector.ps1 -Mode validate
```

### Connection Failed
```bash
# Verify .env has correct values
cat .env | grep UNIFI_

# Test connectivity
ping 192.168.1.1  # Your controller IP
```

## What Each Mode Does

| Mode | Purpose | When to Use |
|------|---------|-------------|
| **interactive** | Web UI for testing | Exploring tools, debugging |
| **validate** | Check protocol compliance | Before committing code |
| **list-tools** | Show all available tools | Quick reference |
| **test-tool** | Test one tool | Testing specific functionality |
| **test-all** | Smoke test all tools | Regression testing |

## Output Indicators

- ✓ **Green**: Success
- ✗ **Red**: Error/Failure
- ⊘ **Yellow**: Skipped
- ℹ **Cyan**: Information

## Exit Codes

- `0`: Success
- `1`: Failure
- `2`: Fatal error

## Full Documentation

See [MCP-INSPECTOR-GUIDE.md](../docs/MCP-INSPECTOR-GUIDE.md) for comprehensive documentation.

## Quick Tips

1. **Start with validation**: Always run `validate` mode first
2. **Use interactive for exploration**: Best way to learn the tools
3. **Test incrementally**: Test simple tools before complex ones
4. **Check logs**: Set `LOG_LEVEL=DEBUG` for verbose output
5. **Automate testing**: Add to CI/CD pipeline

## Example Workflow

```bash
# 1. Validate everything works
./devtools/mcp_inspector.sh validate

# 2. List available tools
./devtools/mcp_inspector.sh list-tools

# 3. Test a simple tool
./devtools/mcp_inspector.sh test-tool unifi_list_devices

# 4. Test with arguments
./devtools/mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'

# 5. Run smoke tests
./devtools/mcp_inspector.sh test-all

# 6. Explore interactively
./devtools/mcp_inspector.sh
```

## CI/CD Integration

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

## Related Tools

- **Dev Console**: `python -m devtools.dev_console` - Python-based testing
- **Unit Tests**: `pytest tests/` - Automated unit tests
- **Example Scripts**: `python examples/*.py` - Usage examples

---

**Quick Help**: Run `./devtools/mcp_inspector.sh --help` for usage information
