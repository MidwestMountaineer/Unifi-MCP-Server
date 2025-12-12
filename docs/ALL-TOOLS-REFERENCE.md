# UniFi MCP Server - Complete Tool Reference

## Overview

The UniFi MCP Server provides **25 tools** for managing and monitoring UniFi network infrastructure through the Model Context Protocol (MCP).

**Last Updated**: October 9, 2025

---

## Network Discovery Tools (8 tools)

### Device Management

1. **`unifi_list_devices`** - List all UniFi devices (switches, APs, gateways)
   - Filter by device type (all, switch, ap, gateway)
   - Pagination support
   - Returns device summary (name, model, IP, status, uptime)

2. **`unifi_get_device_details`** - Get detailed information about a specific device
   - Requires device ID or MAC address
   - Returns full device configuration and status

### Client Management

3. **`unifi_list_clients`** - List all connected clients
   - Filter by connection type (all, wired, wireless)
   - Pagination support
   - Returns client summary (hostname, IP, MAC, connection info)

4. **`unifi_get_client_details`** - Get detailed information about a specific client
   - Requires MAC address
   - Returns full client information and statistics

### Network Configuration

5. **`unifi_list_networks`** - List all configured networks and VLANs
   - Returns network summary (name, VLAN, subnet, purpose)

6. **`unifi_get_network_details`** - Get detailed information about a specific network
   - Requires network ID
   - Returns full network configuration (DHCP, DNS, etc.)

### Wireless Networks

7. **`unifi_list_wlans`** - List all configured wireless networks (WLANs)
   - Returns WLAN summary (SSID, security, enabled status)

8. **`unifi_get_wlan_details`** - Get detailed information about a specific WLAN
   - Requires WLAN ID
   - Returns full WLAN configuration

---

## Security Tools (7 tools)

### Firewall Rules

9. **`unifi_list_firewall_rules`** - List all firewall policies and rules
   - Filter by enabled/disabled status
   - Pagination support
   - Returns rule summary (name, action, source, destination)

10. **`unifi_get_firewall_rule_details`** - Get detailed information about a specific firewall rule
    - Requires rule ID
    - Returns full rule configuration

### Traffic Routing

11. **`unifi_list_traffic_routes`** - List all traffic routing rules
    - Filter by enabled/disabled status
    - Pagination support
    - Returns route summary (destination, next hop, interface)

12. **`unifi_get_route_details`** - Get detailed information about a specific route
    - Requires route ID
    - Returns full route configuration

### Port Forwarding

13. **`unifi_list_port_forwards`** - List all port forwarding rules
    - Filter by enabled/disabled status
    - Pagination support
    - Returns forward summary (name, protocol, ports, destination)

14. **`unifi_get_port_forward_details`** - Get detailed information about a specific port forward
    - Requires forward ID
    - Returns full port forward configuration

### Intrusion Prevention

15. **`unifi_get_ips_status`** - Get intrusion prevention system (IPS) status and alerts
    - Option to include recent alerts
    - Configurable alert limit
    - Returns IPS status and threat information

---

## Statistics Tools (7 tools)

### System Statistics

16. **`unifi_get_network_stats`** - Get overall network statistics and health
    - Returns bandwidth usage, client counts, device status

17. **`unifi_get_system_health`** - Get overall system health metrics
    - Returns controller status, uptime, resource usage

### Client & Device Statistics

18. **`unifi_get_client_stats`** - Get statistics for a specific client
    - Requires MAC address
    - Returns bandwidth, latency, signal strength

19. **`unifi_get_device_stats`** - Get statistics for a specific device
    - Requires device ID or MAC address
    - Returns port statistics, CPU, memory, temperature

20. **`unifi_get_top_clients`** - List clients by bandwidth usage
    - Configurable limit (top N clients)
    - Returns sorted list with bandwidth metrics

### Deep Packet Inspection & Alerts

21. **`unifi_get_dpi_stats`** - Get deep packet inspection statistics
    - Returns application/category breakdown
    - Bandwidth usage by application

22. **`unifi_get_alerts`** - Get recent system alerts and events
    - Configurable limit
    - Returns alerts with severity and timestamps

---

## Migration Tools (3 tools)

### DHCP Management

23. **`unifi_get_dhcp_status`** - Get DHCP server status and lease information
    - Optional network ID filter
    - Returns DHCP configuration and active leases
    - Useful for IP address planning

### Connectivity Verification

24. **`unifi_verify_vlan_connectivity`** - Verify connectivity across VLANs
    - Requires source and destination VLAN (ID or name)
    - Analyzes firewall rules
    - Returns connectivity status and relevant rules
    - Configuration-based check (not actual ping)

### Configuration Backup

25. **`unifi_export_configuration`** - Export network configuration for backup
    - Credentials excluded by default (security)
    - Selective export (choose sections)
    - Includes: networks, firewall rules, routing, port forwards, WLANs
    - Returns timestamped configuration export

---

## Tool Categories Summary

| Category | Tool Count | Purpose |
|----------|------------|---------|
| Network Discovery | 8 | Device, client, network, and WLAN management |
| Security | 7 | Firewall, routing, port forwarding, IPS |
| Statistics | 7 | Performance monitoring and analytics |
| Migration | 3 | Network migration planning and validation |
| **TOTAL** | **25** | Complete UniFi network management |

---

## Common Use Cases

### Network Monitoring
- List all devices and their status
- Monitor client connections
- Check system health
- View bandwidth usage

### Security Management
- Review firewall rules
- Check IPS alerts
- Verify port forwarding configuration
- Audit routing rules

### Troubleshooting
- Get detailed device/client information
- Check connectivity between VLANs
- Review DHCP leases
- Analyze DPI statistics

### Migration & Planning
- Export configuration for backup
- Verify VLAN connectivity
- Check DHCP status
- Plan IP address assignments

### Performance Analysis
- Identify top bandwidth consumers
- Monitor device statistics
- Track application usage (DPI)
- Review system alerts

---

## Tool Naming Convention

All tools follow the naming pattern: `unifi_<action>_<resource>`

**Actions**:
- `list` - Get multiple items with optional filtering/pagination
- `get` - Get detailed information about a single item
- `verify` - Check configuration or connectivity
- `export` - Export configuration data

**Resources**:
- `devices`, `clients`, `networks`, `wlans`
- `firewall_rules`, `traffic_routes`, `port_forwards`
- `network_stats`, `system_health`, `client_stats`, `device_stats`
- `dhcp_status`, `vlan_connectivity`, `configuration`

---

## Security Considerations

### Read-Only Tools (25 tools)
All currently implemented tools are **read-only** and safe for AI agents to use without risk of making changes to the network.

### Write Operations (Coming Soon)
Future write operation tools will require:
- Explicit confirmation parameter
- Safety framework validation
- Rollback capabilities
- Audit logging

### Credential Protection
- ExportConfigurationTool excludes credentials by default
- Sensitive data redacted in logs
- API keys never exposed in responses

---

## Next Steps

### Phase 8: Write Operations Framework (Tasks 21-22)
- Implement write operation safety framework
- Add write operation tools (create, update, delete)
- Implement confirmation and rollback mechanisms

### Future Enhancements
- Real-time monitoring tools
- Automated remediation tools
- Advanced analytics tools
- Bulk operation tools

---

## Documentation

For detailed information about specific tools, see:
- [Network Discovery Tools Guide](QUICK-REFERENCE.md)
- [Security Tools Guide](SECURITY-TOOLS-GUIDE.md)
- [Statistics Tools Guide](STATISTICS-TOOLS-GUIDE.md)
- [IPS Tool Guide](IPS-TOOL-GUIDE.md)
- [Client/Device Stats Guide](CLIENT-DEVICE-STATS-GUIDE.md)
- [DPI & Alerts Guide](DPI-ALERTS-GUIDE.md)
- [Task 20 Summary](TASK-20-SUMMARY.md) - Migration tools

---

**UniFi MCP Server** - Bringing AI-powered network management to your homelab
