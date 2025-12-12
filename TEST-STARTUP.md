# Testing UniFi MCP Server Startup

## The Issue

The error "Connection closed" means the MCP server is failing to start. This happens because the server requires authentication credentials to connect to your UniFi controller.

## Required Environment Variables

You **must** set these environment variables before the server can start:

### Minimum Required (API Key Method)
```bash
UNIFI_HOST=192.168.1.1
UNIFI_API_KEY=your_api_key_here
```

### OR Minimum Required (Username/Password Method)
```bash
UNIFI_HOST=192.168.1.1
UNIFI_USERNAME=your_username
UNIFI_PASSWORD=your_password
```

### Optional but Recommended
```bash
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
LOG_LEVEL=INFO
```

## How to Fix in Kiro

Your `.kiro/settings/mcp.json` needs the `env` section with credentials:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp.server"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "YOUR_ACTUAL_API_KEY_HERE",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false
    }
  }
}
```

## Testing Locally

Before configuring in Kiro, test that the server can start:

```powershell
# Set environment variables
$env:UNIFI_HOST="192.168.1.1"
$env:UNIFI_API_KEY="your_api_key_here"
$env:UNIFI_VERIFY_SSL="false"

# Try to start the server (it will wait for stdin)
cd projects/unifi-mcp-server
python -m unifi_mcp.server
```

If it starts successfully, you'll see:
```
INFO - Starting UniFi MCP Server
INFO - Connecting to UniFi controller
INFO - Successfully connected to UniFi controller
INFO - MCP server running
```

Press Ctrl+C to stop it.

If it fails, you'll see an error message about missing credentials or connection failure.

## Next Steps

1. **Generate an API Key** (see `docs/API-KEY-SETUP.md`)
   - Go to https://192.168.1.1
   - Settings → System → Advanced → API
   - Create New API Key
   - Copy the key

2. **Update your Kiro config** with the actual API key

3. **Restart the MCP server** in Kiro (or restart Kiro)

4. **Test it** by asking: "List all my UniFi devices"
