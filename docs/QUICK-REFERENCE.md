# UniFi MCP Server - Quick Reference Guide

## Overview

The homelab has a **UniFi MCP Server** with **25 production-ready tools** for real-time network monitoring and management. These tools provide live data instead of static documentation.

**Status**: ✅ Production Ready | **Location**: `tools/MCP/unifi-mcp-server/`

## Tool Categories (25 Total)

### 🔍 Network Discovery (8 tools)
- Device and client discovery
- Network and WLAN configuration
- Real-time status information

### 🔒 Security Tools (7 tools)
- Firewall rules and routing
- Port forwarding
- IPS status and alerts

### 📊 Statistics & Monitoring (7 tools)
- Network and system health
- Bandwidth monitoring
- Application usage (DPI)

### 🔧 Migration Support (3 tools)
- DHCP status
- VLAN connectivity testing
- Configuration backup

## Available Tools (Phase 4 Complete)

### Device Discovery

#### List Devices
```python
unifi_list_devices(
    device_type="all",  # all, switch, ap, gateway
    page=1,
    page_size=50
)
```
**Returns**: List of devices with summary info (ID, name, type, IP, status)

#### Get Device Details
```python
unifi_get_device_details(
    device_id="device123"  # or MAC address or name
)
```
**Returns**: Detailed device info (ports, radios, CPU, memory, uptime)

---

### Client Discovery

#### List Clients
```python
unifi_list_clients(
    connection_type="all",  # all, wired, wireless
    page=1,
    page_size=50
)
```
**Returns**: List of clients with summary info (MAC, IP, connection type, bandwidth)

#### Get Client Details
```python
unifi_get_client_details(
    mac_address="aa:bb:cc:dd:ee:ff"  # with or without colons
)
```
**Returns**: Detailed client info (signal, SSID, device info, statistics)

---

### Network Configuration

#### List Networks
```python
unifi_list_networks()
```
**Returns**: List of networks with summary info (name, VLAN, subnet, DHCP)

#### Get Network Details
```python
unifi_get_network_details(
    network_id="network123"  # or network name
)
```
**Returns**: Detailed network config (VLAN, IP, DHCP, DNS, IPv6)

---

### Wireless Networks

#### List WLANs
```python
unifi_list_wlans()
```
**Returns**: List of WLANs with summary info (SSID, security, VLAN)

#### Get WLAN Details
```python
unifi_get_wlan_details(
    wlan_id="wlan123"  # or WLAN name
)
```
**Returns**: Detailed WLAN config (security, radio, guest portal, advanced)

---

## Common Patterns

### Natural Language Queries

**"List all devices"**
```python
unifi_list_devices(device_type="all")
```

**"Show me wireless clients"**
```python
unifi_list_clients(connection_type="wireless")
```

**"What VLANs are configured?"**
```python
unifi_list_networks()
# Filter results where vlan_enabled=true
```

**"Get details for the IoT network"**
```python
unifi_get_network_details(network_id="IoT")
# Case-insensitive name lookup
```

---

## Response Format

### List Response
```json
{
  "success": true,
  "data": [...],
  "count": 10,
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

### Detail Response
```json
{
  "success": true,
  "data": {...},
  "type": "device"
}
```

### Error Response
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Device not found",
    "details": "No device with ID 'xyz'",
    "actionable_steps": [
      "Verify the device ID",
      "Use unifi_list_devices to see available devices"
    ]
  }
}
```

---

## Filtering & Pagination

### Device Filtering
- `device_type="switch"` - Only switches
- `device_type="ap"` - Only access points
- `device_type="gateway"` - Only gateways

### Client Filtering
- `connection_type="wired"` - Only wired clients
- `connection_type="wireless"` - Only wireless clients

### Pagination
- `page=1` - First page (1-indexed)
- `page_size=50` - Items per page (1-500)
- Check `total` in response for total count

---

## Lookup Methods

### By ID (Exact)
```python
unifi_get_device_details(device_id="5f8a1b2c3d4e5f6g7h8i9j0k")
```

### By MAC Address
```python
unifi_get_device_details(device_id="aa:bb:cc:dd:ee:ff")
# or
unifi_get_device_details(device_id="aabbccddeeff")
```

### By Name (Case-Insensitive)
```python
unifi_get_network_details(network_id="iot")
# Matches "IoT", "IOT", "iot", etc.
```

---

## Data Formatting

### Uptime
- Raw: `86400` seconds
- Formatted: `"1d"` (1 day)
- Formatted: `"2d 5h 30m"` (2 days, 5 hours, 30 minutes)

### Bandwidth
- Raw: `5368709120` bytes
- Formatted: `"5.00 GB"`

### Signal Strength
- Value: `-45` dBm (excellent)
- Value: `-62` dBm (good)
- Value: `-75` dBm (fair)

---

## Error Codes

- `VALIDATION_ERROR` - Invalid input parameters
- `API_ERROR` - UniFi controller communication error
- `DEVICE_NOT_FOUND` - Device doesn't exist
- `CLIENT_NOT_FOUND` - Client doesn't exist
- `NETWORK_NOT_FOUND` - Network doesn't exist
- `WLAN_NOT_FOUND` - WLAN doesn't exist

---

## Examples

### Find Offline Devices
```python
# List all devices
result = unifi_list_devices()

# Filter offline devices
offline = [d for d in result["data"] if d["status"] == "offline"]
```

### Monitor Wireless Signal
```python
# Get client details
result = unifi_get_client_details(mac_address="aa:bb:cc:dd:ee:ff")

# Check signal strength
signal = result["data"]["signal"]
if signal < -70:
    print("Weak signal!")
```

### Audit VLAN Configuration
```python
# List all networks
networks = unifi_list_networks()

# Find VLAN-enabled networks
vlans = [n for n in networks["data"] if n["vlan_enabled"]]

# Get details for each VLAN
for vlan in vlans:
    details = unifi_get_network_details(network_id=vlan["id"])
    print(f"VLAN {vlan['vlan']}: {vlan['name']}")
```

### Check Guest Network Security
```python
# List all WLANs
wlans = unifi_list_wlans()

# Find guest networks
guest_wlans = [w for w in wlans["data"] if w["is_guest"]]

# Check security settings
for wlan in guest_wlans:
    details = unifi_get_wlan_details(wlan_id=wlan["id"])
    print(f"{wlan['name']}: {details['data']['security']}")
```

---

## Tips & Best Practices

### For AI Agents
1. Use summary views (list tools) for overview
2. Use detail views only when needed
3. Leverage pagination for large datasets
4. Use filtering to reduce noise
5. Check error codes for actionable feedback

### For Developers
1. Always validate input before calling tools
2. Handle errors gracefully
3. Cache results when appropriate
4. Use mock data for testing
5. Follow established patterns

### For Network Admins
1. Start with list tools to get overview
2. Use detail tools for troubleshooting
3. Combine tools for complex queries
4. Export data for documentation
5. Monitor regularly for changes

---

## Testing

### Run All Tests
```bash
python -m pytest tests/test_network_discovery.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/test_network_discovery.py::TestListDevicesTool -v
```

### Run Demo
```bash
python examples/phase4_interactive_demo.py
```

---

## Documentation

- **Implementation**: `docs/TASK-11-SUMMARY.md`, `docs/TASK-12-SUMMARY.md`, `docs/TASK-13-SUMMARY.md`
- **Phase Summary**: `docs/PHASE-4-COMPLETE.md`
- **Server Setup**: `docs/MCP-SERVER.md`
- **Quick Reference**: This document

---

## Support

For issues or questions:
1. Check error messages for actionable steps
2. Review documentation in `docs/`
3. Run demo scripts in `examples/`
4. Check test cases in `tests/`

---

**Last Updated**: October 9, 2025  
**Version**: Phase 4 Complete  
**Status**: Production Ready ✅


---

## Complete Tool Reference

### 🔍 Network Discovery Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `unifi_list_devices` | List all network devices | `unifi_list_devices(device_type="switch")` |
| `unifi_get_device_details` | Get device details | `unifi_get_device_details(device_id="94:2a:6f:96:22:1d")` |
| `unifi_list_clients` | List connected clients | `unifi_list_clients(connection_type="wireless")` |
| `unifi_get_client_details` | Get client details | `unifi_get_client_details(mac_address="48:21:0b:71:86:a6")` |
| `unifi_list_networks` | List all VLANs | `unifi_list_networks()` |
| `unifi_get_network_details` | Get network config | `unifi_get_network_details(network_id="6816fc1bdc69f330b3e6f501")` |
| `unifi_list_wlans` | List WiFi networks | `unifi_list_wlans()` |
| `unifi_get_wlan_details` | Get WLAN config | `unifi_get_wlan_details(wlan_id="67c51e0295f61a681eccb177")` |

### 🔒 Security Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `unifi_list_firewall_rules` | List firewall rules | `unifi_list_firewall_rules(enabled_only=true)` |
| `unifi_get_firewall_rule_details` | Get rule details | `unifi_get_firewall_rule_details(rule_id="<id>")` |
| `unifi_list_traffic_routes` | List routing rules | `unifi_list_traffic_routes()` |
| `unifi_get_route_details` | Get route details | `unifi_get_route_details(route_id="<id>")` |
| `unifi_list_port_forwards` | List port forwards | `unifi_list_port_forwards()` |
| `unifi_get_port_forward_details` | Get forward details | `unifi_get_port_forward_details(forward_id="<id>")` |
| `unifi_get_ips_status` | Get IPS status | `unifi_get_ips_status(include_alerts=true)` |

### 📊 Statistics & Monitoring Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `unifi_get_network_stats` | Overall network stats | `unifi_get_network_stats()` |
| `unifi_get_system_health` | System health | `unifi_get_system_health()` |
| `unifi_get_client_stats` | Client bandwidth | `unifi_get_client_stats(mac_address="<mac>")` |
| `unifi_get_device_stats` | Device statistics | `unifi_get_device_stats(device_id="<mac>")` |
| `unifi_get_top_clients` | Top bandwidth users | `unifi_get_top_clients(limit=10)` |
| `unifi_get_dpi_stats` | Application usage | `unifi_get_dpi_stats()` |
| `unifi_get_alerts` | Recent alerts | `unifi_get_alerts(limit=50)` |

### 🔧 Migration Support Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `unifi_get_dhcp_status` | DHCP leases | `unifi_get_dhcp_status()` |
| `unifi_verify_vlan_connectivity` | Test VLAN routing | `unifi_verify_vlan_connectivity(source_vlan="Core", destination_vlan="IoT")` |
| `unifi_export_configuration` | Backup config | `unifi_export_configuration(include_credentials=false)` |

---

## Common Use Cases

### Check Network Health
```bash
# Get overall health
unifi_get_system_health

# Check for alerts
unifi_get_alerts limit=20

# Get IPS status
unifi_get_ips_status include_alerts=true
```

### Monitor Bandwidth
```bash
# Top bandwidth consumers
unifi_get_top_clients limit=10

# Specific client stats
unifi_get_client_stats mac_address=48:21:0b:71:86:a6

# Network-wide stats
unifi_get_network_stats
```

### Troubleshoot Connectivity
```bash
# List all clients
unifi_list_clients

# Check specific client
unifi_get_client_details mac_address=<mac>

# Verify VLAN connectivity
unifi_verify_vlan_connectivity source_vlan=Core destination_vlan=IoT

# Check DHCP leases
unifi_get_dhcp_status
```

### Device Management
```bash
# List all devices
unifi_list_devices

# Get switch details
unifi_get_device_details device_id=94:2a:6f:96:22:1d

# Get device stats
unifi_get_device_stats device_id=94:2a:6f:96:22:1d
```

### VLAN Information
```bash
# List all networks
unifi_list_networks

# Get Core VLAN details
unifi_get_network_details network_id=6816fc1bdc69f330b3e6f501

# Get IoT VLAN details
unifi_get_network_details network_id=67c520c195f61a681eccb1e0

# Check DHCP status
unifi_get_dhcp_status network_id=6816fc1bdc69f330b3e6f501
```

### WiFi Management
```bash
# List all wireless networks
unifi_list_wlans

# Get MaxCore WiFi details
unifi_get_wlan_details wlan_id=67c51e0295f61a681eccb177

# List wireless clients
unifi_list_clients connection_type=wireless
```

### Security Monitoring
```bash
# Check IPS status
unifi_get_ips_status include_alerts=true alert_limit=20

# List firewall rules
unifi_list_firewall_rules enabled_only=true

# Get recent alerts
unifi_get_alerts limit=50

# List port forwards
unifi_list_port_forwards
```

### Configuration Backup
```bash
# Export full configuration (no credentials)
unifi_export_configuration include_credentials=false

# Export with specific components
unifi_export_configuration include_networks=true include_firewall_rules=true include_wlans=true
```

---

## Network IDs Reference

### VLANs
- **Default**: `67c51c7395f61a681eccb121`
- **Core (VLAN 10)**: `6816fc1bdc69f330b3e6f501`
- **IoT (VLAN 20)**: `67c520c195f61a681eccb1e0`
- **Guest (VLAN 30)**: `67c5212295f61a681eccb1e4`
- **Management (VLAN 40)**: `6817167cdc69f330b3e6f92d`

### WLANs
- **MaxCore**: `67c51e0295f61a681eccb177`
- **MaxIOT**: `67c5217f95f61a681eccb1f8`
- **MaxGuest**: `67c5220095f61a681eccb20a`
- **MaxDumbIoT**: `681806c0714b664c0268062f` (disabled)

### Devices
- **HalfRack DM**: `9c:05:d6:b6:96:46`
- **USW Pro HD Switch**: `94:2a:6f:96:22:1d`
- **Upstairs AP**: `9c:05:d6:ca:ad:57`
- **Downstairs AP**: `9c:05:d6:ce:4b:e9`
- **uNAS Pro**: `0c:ea:14:ea:1f:df`

---

## Tool Features

### All Tools Provide
- ✅ Real-time data (no caching delays)
- ✅ Structured JSON responses
- ✅ Error handling and validation
- ✅ Pagination support (where applicable)
- ✅ Filtering options
- ✅ Read-only operations (safe for AI agents)

### Security Features
- ✅ Credentials stored in environment variables
- ✅ All sensitive data redacted from logs
- ✅ API keys never exposed in responses
- ✅ Read-only operations only
- ✅ No risk of accidental changes

---

## Performance

- **Startup Time**: ~0.1s
- **Memory Usage**: ~68MB
- **Response Time**: <0.02s average
- **Concurrent Requests**: 10+ supported

---

## Best Practices

1. **Use list tools for overviews** - Faster and less data
2. **Use detail tools when needed** - More comprehensive but slower
3. **Filter results** - Use pagination and filtering options
4. **Cache results** - If querying frequently, cache in your application
5. **Monitor performance** - Use `unifi_get_system_health` regularly
6. **Backup configuration** - Use `unifi_export_configuration` weekly

---

## Troubleshooting

### Tool Not Working
```bash
# Check MCP server status in Kiro
# View: MCP Servers panel

# Check configuration
cat .kiro/settings/mcp.json

# Test connection
unifi_get_system_health
```

### No Data Returned
```bash
# Verify network connectivity
ping 192.168.1.1

# Check credentials in .env
cat tools/MCP/unifi-mcp-server/.env

# Enable debug logging
# Set LOG_LEVEL=DEBUG in MCP config
```

### Slow Response
```bash
# Check network latency
ping 192.168.1.1

# Use list tools instead of detail tools
unifi_list_devices  # Faster
unifi_get_device_details  # Slower (more data)
```

---

**Last Updated**: October 25, 2025  
**MCP Server Version**: 1.0.0 (Production Ready)  
**Total Tools**: 25 (all read-only)
