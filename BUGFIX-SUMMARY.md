# Bug Fixes for MCP Server Startup

## Issues Found and Fixed

### Issue 1: Wrong Module Entry Point
**Error**: `RuntimeWarning: 'unifi_mcp.server' found in sys.modules`

**Cause**: Circular import when running `python -m unifi_mcp.server`

**Fix**: Changed command from `python -m unifi_mcp.server` to `python -m unifi_mcp`

**Files Updated**:
- `docs/KIRO-SETUP-GUIDE.md`
- `docs/API-KEY-SETUP.md`

### Issue 2: Wrong Parameter Name in setup_logging()
**Error**: `TypeError: setup_logging() got an unexpected keyword argument 'level'`

**Cause**: Function call used `level=` but function parameter is `log_level=`

**Fix**: Changed `level=config.server.log_level` to `log_level=config.server.log_level`

**Files Updated**:
- `src/unifi_mcp/__main__.py` (line 39)

## Current Status

✅ Both bugs fixed
✅ Code passes diagnostics
✅ Ready to test

## Testing

The server should now start successfully. To verify:

```powershell
$env:UNIFI_HOST="192.168.1.1"
$env:UNIFI_API_KEY="your_key_here"
$env:UNIFI_VERIFY_SSL="false"
cd projects/unifi-mcp-server
python -m unifi_mcp
```

Expected output:
```
INFO - Starting UniFi MCP Server
INFO - Connecting to UniFi controller
INFO - Successfully connected to UniFi controller
INFO - MCP server running
```

## Kiro Configuration

Your `.kiro/settings/mcp.json` should now work with:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your_actual_api_key_here",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false
    }
  }
}
```

## Next Steps

1. Ensure your Kiro config has the correct command: `["-m", "unifi_mcp"]`
2. Ensure you have a valid API key in the `env` section
3. Reconnect the MCP server in Kiro
4. Test with: "List all my UniFi devices"
