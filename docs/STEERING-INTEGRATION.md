# Steering Document Integration

**Date**: October 10, 2025  
**Status**: ✅ Complete

## Overview

The homelab steering documents have been updated to use **live UniFi MCP tools** instead of static network data. This ensures that Kiro always has access to current, real-time network information.

## Changes Made

### 1. Created New MCP Tools Reference

**File**: `.kiro/steering/unifi-mcp-tools.md`
- **Inclusion**: Always loaded
- **Purpose**: Quick reference for all 25 UniFi MCP tools
- **Content**:
  - Tool categories and descriptions
  - Common use cases with examples
  - Network IDs and device MACs
  - Integration guidance
  - Troubleshooting tips

### 2. Updated Network Topology Document

**File**: `.kiro/steering/network-topology.md`

**Sections Updated**:
- ✅ Network Overview - Added MCP tool callouts
- ✅ VLAN Configuration - Replaced static data with tool references
- ✅ WiFi Networks - Added WLAN IDs and tool examples
- ✅ Firewall Configuration - Added security tool references
- ✅ DHCP Servers - Replaced lease counts with tool calls
- ✅ Network Monitoring - Added monitoring tool examples
- ✅ Device Inventory - Replaced static lists with tool queries
- ✅ Security Implementation - Added live security data tools

**Key Improvements**:
- Live device status instead of static lists
- Current DHCP lease information
- Real-time bandwidth and performance data
- Up-to-date firewall and security status
- Dynamic client and device inventories

### 3. Updated UniFi Ecosystem Document

**File**: `.kiro/steering/unifi-ecosystem.md`

**Sections Updated**:
- ✅ uNAS Pro Device Information - Added device detail tools
- ✅ System Resources - Replaced static metrics with tool calls

**Key Improvements**:
- Live device statistics
- Current firmware versions
- Real-time resource usage
- Dynamic system health

### 4. Updated Steering README

**File**: `.kiro/steering/README.md`

**Changes**:
- ✅ Added MCP tools to "Always Included" section
- ✅ Updated Quick Reference with MCP tool examples
- ✅ Noted which documents now use live data
- ✅ Added comprehensive tool usage examples

## Benefits

### For Kiro AI Assistant

1. **Always Current Data**
   - No outdated device lists
   - Real-time network status
   - Current bandwidth usage
   - Live security alerts

2. **Better Troubleshooting**
   - Can check actual device status
   - Verify connectivity in real-time
   - Monitor performance metrics
   - Identify issues immediately

3. **Accurate Recommendations**
   - Based on current network state
   - Considers actual device status
   - Uses real bandwidth data
   - Reflects current security posture

### For Users

1. **Reduced Maintenance**
   - No need to update static device lists
   - Automatic network discovery
   - Self-documenting infrastructure
   - Always accurate information

2. **Better Insights**
   - Real-time network visibility
   - Performance monitoring
   - Security status
   - Bandwidth analysis

3. **Easier Troubleshooting**
   - Quick device status checks
   - Connectivity verification
   - Performance analysis
   - Alert monitoring

## MCP Tools Available

### Network Discovery (8 tools)
- `unifi_list_devices` - List all network devices
- `unifi_get_device_details` - Get device details
- `unifi_list_clients` - List connected clients
- `unifi_get_client_details` - Get client details
- `unifi_list_networks` - List all VLANs
- `unifi_get_network_details` - Get network config
- `unifi_list_wlans` - List WiFi networks
- `unifi_get_wlan_details` - Get WLAN config

### Security Tools (7 tools)
- `unifi_list_firewall_rules` - List firewall rules
- `unifi_get_firewall_rule_details` - Get rule details
- `unifi_list_traffic_routes` - List routing rules
- `unifi_get_route_details` - Get route details
- `unifi_list_port_forwards` - List port forwards
- `unifi_get_port_forward_details` - Get forward details
- `unifi_get_ips_status` - Get IPS status

### Statistics & Monitoring (7 tools)
- `unifi_get_network_stats` - Overall network stats
- `unifi_get_system_health` - System health
- `unifi_get_client_stats` - Client bandwidth
- `unifi_get_device_stats` - Device statistics
- `unifi_get_top_clients` - Top bandwidth users
- `unifi_get_dpi_stats` - Application usage
- `unifi_get_alerts` - Recent alerts

### Migration Support (3 tools)
- `unifi_get_dhcp_status` - DHCP leases
- `unifi_verify_vlan_connectivity` - Test VLAN routing
- `unifi_export_configuration` - Backup config

## Example Usage

### Check Network Health

```bash
# Get overall system health
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
```

### Get Device Information

```bash
# List all devices
unifi_list_devices

# Get switch details
unifi_get_device_details device_id=94:2a:6f:96:22:1d

# Get device stats
unifi_get_device_stats device_id=94:2a:6f:96:22:1d
```

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

### Key Devices
- **HalfRack DM**: `9c:05:d6:b6:96:46`
- **USW Pro HD Switch**: `94:2a:6f:96:22:1d`
- **Upstairs AP**: `9c:05:d6:ca:ad:57`
- **Downstairs AP**: `9c:05:d6:ce:4b:e9`
- **uNAS Pro**: `0c:ea:14:ea:1f:df`
- **DeskPC**: `48:21:0b:71:86:a6`
- **pikvm**: `dc:a6:32:21:f8:ff`

## Migration Strategy

### Phase 1: Add MCP Tool References ✅
- Created comprehensive MCP tools reference document
- Added tool callouts to existing steering documents
- Preserved static data for reference

### Phase 2: Update Steering Documents ✅
- Updated network-topology.md with live data tools
- Updated unifi-ecosystem.md with device tools
- Updated README with tool examples

### Phase 3: User Adoption (Ongoing)
- Users can now ask Kiro for live network data
- Kiro will use MCP tools automatically
- Static data remains as fallback

### Phase 4: Deprecate Static Data (Future)
- Once MCP tools are proven reliable
- Remove static device lists
- Keep only reference information

## Best Practices

### For Kiro
1. **Prefer MCP tools** over static data when available
2. **Cache results** if querying frequently
3. **Handle errors gracefully** with fallback to static data
4. **Use appropriate tools** (list vs detail)

### For Users
1. **Keep MCP server running** for best experience
2. **Update network IDs** if networks change
3. **Monitor MCP server health** regularly
4. **Report issues** if tools return unexpected data

## Troubleshooting

### MCP Tools Not Working

**Check MCP Server Status**:
1. Open Kiro MCP Servers panel
2. Verify "unifi" server is connected
3. Check for error messages

**Verify Configuration**:
```bash
# Check MCP config
cat .kiro/settings/mcp.json

# Check environment variables
cat projects/unifi-mcp-server/.env
```

**Test Connection**:
```bash
# Simple health check
unifi_get_system_health
```

### No Data Returned

**Verify Network Connectivity**:
```bash
# Ping UniFi controller
ping 192.168.1.1
```

**Check Credentials**:
- Verify API key or username/password in `.env`
- Test credentials in UniFi web UI

**Enable Debug Logging**:
- Set `LOG_LEVEL=DEBUG` in MCP config
- Check logs for errors

## Future Enhancements

### Short Term
1. Add more example queries to steering documents
2. Create troubleshooting playbooks using MCP tools
3. Add automation scripts using MCP tools

### Medium Term
1. Real-time monitoring dashboards
2. Automated network documentation
3. Alert integration with monitoring systems

### Long Term
1. Automated remediation using write operations
2. Network topology visualization
3. Predictive analytics and recommendations

## Documentation

### Related Documents
- **MCP Tools Reference**: `.kiro/steering/unifi-mcp-tools.md`
- **Network Topology**: `.kiro/steering/network-topology.md`
- **UniFi Ecosystem**: `.kiro/steering/unifi-ecosystem.md`
- **Project README**: `projects/unifi-mcp-server/README.md`
- **All Tools Reference**: `projects/unifi-mcp-server/docs/ALL-TOOLS-REFERENCE.md`

### External Resources
- [MCP Documentation](https://modelcontextprotocol.io/)
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)
- [Project Repository](projects/unifi-mcp-server/)

## Conclusion

The integration of UniFi MCP tools into steering documents provides:

✅ **Real-time network visibility**  
✅ **Reduced documentation maintenance**  
✅ **Better troubleshooting capabilities**  
✅ **More accurate AI recommendations**  
✅ **Self-documenting infrastructure**

The homelab now has a **production-ready MCP server** with **25 tools** providing live network data to Kiro, making it easier to manage and monitor the network infrastructure.

---

**Status**: ✅ Complete  
**Last Updated**: October 10, 2025  
**MCP Server Version**: 1.0.0  
**Total Tools**: 25 (all read-only)
