# Tool Registration Fix

## Issue

Server connected successfully but showed **"0 tools available"**.

## Root Cause

The `ToolRegistry` was initialized but no tools were ever registered with it. The tool classes existed but were never instantiated or added to the registry.

## Solution

Added `_register_tools()` method to `UniFiMCPServer` that:
1. Imports all tool classes from `tools.network_discovery` and `tools.security`
2. Instantiates each tool
3. Registers them with the tool registry

## Tools Now Registered

### Network Discovery (8 tools)
1. `unifi_list_devices` - List all UniFi devices
2. `unifi_get_device_details` - Get device details
3. `unifi_list_clients` - List connected clients
4. `unifi_get_client_details` - Get client details
5. `unifi_list_networks` - List networks/VLANs
6. `unifi_get_network_details` - Get network details
7. `unifi_list_wlans` - List wireless networks
8. `unifi_get_wlan_details` - Get WLAN details

### Security (7 tools)
9. `unifi_list_firewall_rules` - List firewall rules
10. `unifi_get_firewall_rule_details` - Get firewall rule details
11. `unifi_list_traffic_routes` - List routing rules
12. `unifi_get_route_details` - Get route details
13. `unifi_list_port_forwards` - List port forwards
14. `unifi_get_port_forward_details` - Get port forward details
15. `unifi_get_ips_status` - Get IPS/IDS status

**Total: 15 tools**

## Files Modified

- `src/unifi_mcp/server.py`
  - Added `_register_tools()` method
  - Called `_register_tools()` in `__init__()`

## Testing

After reconnecting in Kiro, you should see:
- **"15 tools available"** (or similar)
- Tools should appear in the MCP tools list
- You can now use commands like "List all my UniFi devices"

## Next Steps

1. Reconnect the MCP server in Kiro
2. Verify tool count shows 15 tools
3. Test with a query like "List all devices"
