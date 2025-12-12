# Adding UniFi MCP Server to Kiro - Setup Guide

## TL;DR - You Can Use It NOW! 🚀

**Yes, you can add the UniFi MCP server to Kiro right now!** The server has been functional since Phase 3 (Task 8), and you already have 16 working tools across multiple categories.

## What's Already Working

### ✅ Phase 3: Core Infrastructure (Complete)
- MCP server implementation
- UniFi API client with authentication
- Tool registry system
- Error handling and logging

### ✅ Phase 4: Network Discovery (Complete)
**8 Tools Available:**
1. `unifi_list_devices` - List all devices (switches, APs, gateways)
2. `unifi_get_device_details` - Get device details by ID/MAC/name
3. `unifi_list_clients` - List connected clients (wired/wireless)
4. `unifi_get_client_details` - Get client details by MAC/name
5. `unifi_list_networks` - List all networks and VLANs
6. `unifi_get_network_details` - Get network details by ID/name
7. `unifi_list_wlans` - List wireless networks
8. `unifi_get_wlan_details` - Get WLAN details by ID/name

### ✅ Phase 5: Security Tools (Complete)
**8 Tools Available:**
9. `unifi_list_firewall_rules` - List firewall rules with filtering
10. `unifi_get_firewall_rule_details` - Get firewall rule details
11. `unifi_list_traffic_routes` - List routing rules
12. `unifi_get_route_details` - Get route details
13. `unifi_list_port_forwards` - List port forwarding rules
14. `unifi_get_port_forward_details` - Get port forward details
15. `unifi_get_ips_status` - Get IPS/IDS status and alerts

**Total: 16 working tools!**

## Setup Steps

### 1. Install the Package

From the project directory:

```bash
cd projects/unifi-mcp-server
pip install -e .
```

This installs the package in "editable" mode so changes are immediately available.

### 2. Configure Authentication

The UniFi MCP server supports **two authentication methods**:

#### Option A: API Key (Recommended for UniFi OS)

For UniFi OS devices (Dream Machine, Cloud Gateway, uNAS Pro):

1. **Generate an API Key** in UniFi OS:
   - Log into your Dream Machine web UI (https://192.168.1.1)
   - Go to **Settings** → **System** → **Advanced**
   - Scroll to **API** section
   - Click **Create New API Key**
   - Give it a name (e.g., "Kiro MCP Server")
   - Copy the generated key (you won't see it again!)

2. **Set environment variable**:
```bash
# UniFi Controller Settings (API Key Method)
UNIFI_HOST=192.168.1.1          # Your Dream Machine IP
UNIFI_PORT=443                   # HTTPS port (default: 443)
UNIFI_API_KEY=your_api_key_here # API key from UniFi OS
UNIFI_SITE=default              # Site name (usually "default")
UNIFI_VERIFY_SSL=false          # Set to false for self-signed certs

# Optional: Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

#### Option B: Username/Password (Legacy Controllers)

For traditional UniFi Controllers (not UniFi OS):

```bash
# UniFi Controller Settings (Username/Password Method)
UNIFI_HOST=192.168.1.1          # Your controller IP
UNIFI_PORT=443                   # HTTPS port (default: 443)
UNIFI_USERNAME=your_username     # Local admin account
UNIFI_PASSWORD=your_password     # Account password
UNIFI_SITE=default              # Site name (usually "default")
UNIFI_VERIFY_SSL=false          # Set to false for self-signed certs

# Optional: Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

**Security Note**: API key authentication is more secure and recommended for UniFi OS devices. Username/password is supported for backward compatibility with traditional controllers.

### 3. Add to Kiro MCP Configuration

#### Option A: Workspace-Level Config (Recommended)

Edit `.kiro/settings/mcp.json` in your workspace:

**Using API Key (Recommended):**
```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": [
        "-m",
        "unifi_mcp"
      ],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_PORT": "443",
        "UNIFI_API_KEY": "your_api_key_here",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false",
        "LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "unifi_list_*",
        "unifi_get_*"
      ]
    }
  }
}
```

**Using Username/Password (Legacy):**
```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": [
        "-m",
        "unifi_mcp"
      ],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_PORT": "443",
        "UNIFI_USERNAME": "your_username",
        "UNIFI_PASSWORD": "your_password",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false",
        "LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "unifi_list_*",
        "unifi_get_*"
      ]
    }
  }
}
```

#### Option B: User-Level Config (Global)

Edit `~/.kiro/settings/mcp.json`:

**Using API Key (Recommended):**
```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": [
        "-m",
        "unifi_mcp"
      ],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your_api_key_here",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false
    }
  }
}
```

### 4. Restart or Reconnect MCP Server

In Kiro:
1. Open the **MCP Server** view in the Kiro feature panel
2. Find the "unifi" server
3. Click **Reconnect** (or restart Kiro)

### 5. Verify It's Working

In Kiro chat, try:
- "List all my UniFi devices"
- "Show me connected clients"
- "What VLANs are configured?"
- "Show me firewall rules"
- "What's the IPS status?"

## What You Can Do Right Now

### Network Discovery
```
"List all devices on my network"
"Show me wireless clients"
"What's the status of my living room AP?"
"Which clients are on the IoT VLAN?"
"Show me all configured networks"
```

### Security Monitoring
```
"List all firewall rules"
"Show me the firewall rule blocking IoT to Core"
"What port forwards are configured?"
"What's the IPS status?"
"Show me recent IPS alerts"
```

### Troubleshooting
```
"Why is device X offline?"
"What's the signal strength for my laptop?"
"Show me clients with poor signal"
"What's the uptime of my main switch?"
```

### Configuration Audit
```
"Export all network configurations"
"What security is used on the guest WiFi?"
"Show me all VLAN assignments"
"List all routing rules"
```

## What's Coming Next

### Phase 6: Statistics and Monitoring (In Progress)
- Network statistics
- Client statistics  
- DPI (Deep Packet Inspection) data
- System health metrics

### Phase 7: System Management
- Site settings
- System information
- Backup/restore
- Firmware management

### Phase 8: Advanced Features
- Event streaming
- Webhooks
- Custom dashboards

## Testing Without Kiro

You can test the server directly:

```bash
# Run the demo
python examples/phase4_interactive_demo.py

# Or test individual tools
python -c "
from unifi_mcp import UniFiMCPServer
import asyncio

async def test():
    server = UniFiMCPServer()
    # Test a tool
    result = await server.call_tool('unifi_list_devices', {})
    print(result)

asyncio.run(test())
"
```

## Troubleshooting

### Connection Issues

**Problem**: "Failed to connect to UniFi controller"

**Solutions**:
1. Verify `UNIFI_HOST` is correct (your Dream Machine IP)
2. Check `UNIFI_VERIFY_SSL=false` for self-signed certs
3. Ensure credentials are correct
4. Test connectivity: `ping 192.168.1.1`

### Authentication Issues

**Problem**: "Authentication failed"

**Solutions**:
1. Verify username/password are correct
2. Check if account has admin privileges
3. Try logging into UniFi web UI with same credentials
4. Check if 2FA is enabled (not supported yet)

### Tool Not Found

**Problem**: "Tool 'unifi_xxx' not found"

**Solutions**:
1. Check the tool is implemented (see list above)
2. Verify server is running: Check MCP Server view in Kiro
3. Reconnect the server
4. Check logs: `LOG_LEVEL=DEBUG`

### No Data Returned

**Problem**: Tool returns empty results

**Solutions**:
1. Verify you have devices/clients/networks configured
2. Check the site name: `UNIFI_SITE=default`
3. Try the UniFi web UI to confirm data exists
4. Check logs for API errors

## Security Considerations

### For Testing (Homelab)
- Using your main admin account is fine
- Self-signed certs are okay (`UNIFI_VERIFY_SSL=false`)
- Storing credentials in config is acceptable

### For Production (Future)
- Create a dedicated read-only account
- Use proper SSL certificates
- Store credentials in a secrets manager
- Enable audit logging
- Restrict network access

## Performance Tips

### Reduce Token Usage
- Use list tools for overviews (summary views)
- Use detail tools only when needed (full data)
- Use filtering to reduce results
- Use pagination for large datasets

### Improve Response Time
- Keep `LOG_LEVEL=INFO` (not DEBUG) in production
- Use caching for frequently accessed data (future)
- Filter at the API level when possible

## Next Steps

1. **Install and configure** the MCP server (steps above)
2. **Test basic queries** to verify it's working
3. **Explore the tools** - try different queries
4. **Provide feedback** - what works, what doesn't
5. **Continue development** - implement remaining phases

## Need Help?

- Check `docs/MCP-SERVER.md` for detailed server documentation
- See `docs/QUICK-REFERENCE.md` for tool usage examples
- Review `examples/` directory for code samples
- Check logs with `LOG_LEVEL=DEBUG` for troubleshooting

---

**Ready to go?** Install the package, configure your credentials, add to Kiro, and start querying your network! 🎉

**Current Status**: 16 tools ready, Phases 3-5 complete, Phase 6 in progress
