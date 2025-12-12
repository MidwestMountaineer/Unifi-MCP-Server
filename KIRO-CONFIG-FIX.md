# Fix for Kiro MCP Configuration

## The Problem

The error occurs because of how the module is being invoked. The command:
```
python -m unifi_mcp.server
```

Causes a circular import issue because `__init__.py` imports from `server.py`.

## The Solution

Change the command in your Kiro config from:
```json
"args": ["-m", "unifi_mcp.server"]
```

To:
```json
"args": ["-m", "unifi_mcp"]
```

## Complete Fixed Configuration

Update your `.kiro/settings/mcp.json` to:

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
        "UNIFI_VERIFY_SSL": "false",
        "LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": ["unifi_list_*", "unifi_get_*"]
    }
  }
}
```

## Why This Works

- `python -m unifi_mcp` runs the `__main__.py` file directly
- `python -m unifi_mcp.server` tries to run `server.py` as a module, but it's already imported by `__init__.py`
- The `__main__.py` file is designed to be the entry point and handles imports correctly

## After Making the Change

1. Save the updated `mcp.json` file
2. In Kiro, go to the MCP Server view
3. Click **Reconnect** on the "unifi" server
4. Check the logs - you should see "Successfully connected to UniFi controller"

## Testing Locally

You can test this works by running:

```powershell
$env:UNIFI_HOST="192.168.1.1"
$env:UNIFI_API_KEY="your_key_here"
$env:UNIFI_VERIFY_SSL="false"
cd projects/unifi-mcp-server
python -m unifi_mcp
```

You should see:
```
INFO - Starting UniFi MCP Server
INFO - Connecting to UniFi controller
INFO - Successfully connected to UniFi controller
INFO - MCP server running
```

Press Ctrl+C to stop.
