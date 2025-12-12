# DPI and Alerts Tools Guide

This guide covers the Deep Packet Inspection (DPI) statistics and system alerts tools added in Task 19.

## Overview

These tools provide visibility into network traffic patterns and system events:

- **GetDPIStatsTool**: Analyze application-level traffic using deep packet inspection
- **GetAlertsTool**: Monitor system alerts and events

## GetDPIStatsTool

### Purpose

The DPI statistics tool provides insights into what applications and services are consuming bandwidth on your network. It uses UniFi's deep packet inspection capabilities to categorize traffic by application and protocol.

### Tool Definition

```python
name: "unifi_get_dpi_stats"
description: "Get deep packet inspection statistics"
category: "statistics"
```

### Input Schema

```json
{
  "type": "object",
  "properties": {}
}
```

No parameters required - returns all DPI statistics.

### Output Format

```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "category": "Streaming",
        "application": "Netflix",
        "tx_bytes": 5000000000,
        "rx_bytes": 50000000000,
        "total_bytes": 55000000000,
        "tx_bytes_formatted": "4.66 GB",
        "rx_bytes_formatted": "46.57 GB",
        "total_bytes_formatted": "51.22 GB"
      }
    ],
    "top_applications": [
      // Top 10 applications by total traffic
    ],
    "total_traffic": {
      "tx_bytes": 6500000000,
      "rx_bytes": 62000000000,
      "total_bytes": 68500000000,
      "tx_bytes_formatted": "6.05 GB",
      "rx_bytes_formatted": "57.73 GB",
      "total_bytes_formatted": "63.78 GB"
    },
    "summary": "66 applications tracked, 63.78 GB total traffic"
  },
  "message": "DPI statistics retrieved successfully"
}
```

### Key Features

1. **Application Categorization**: Traffic is grouped by application and category
2. **Bandwidth Breakdown**: Shows both upload (TX) and download (RX) for each application
3. **Human-Readable Formatting**: Byte values are formatted (B, KB, MB, GB, TB)
4. **Sorted by Traffic**: Applications are sorted by total traffic descending
5. **Top 10 List**: Provides a quick view of the biggest bandwidth consumers

### Use Cases

1. **Bandwidth Analysis**: Identify which applications are using the most bandwidth
2. **Network Planning**: Understand traffic patterns for capacity planning
3. **Policy Enforcement**: Identify applications that may need QoS rules
4. **Troubleshooting**: Find bandwidth hogs causing network congestion
5. **Security Monitoring**: Detect unusual application usage patterns

### Example Prompts

```
"What applications are using the most bandwidth?"
"Show me DPI statistics"
"What's the traffic breakdown by category?"
"Which protocols are most active?"
"Is Netflix consuming a lot of bandwidth?"
```

### API Endpoint

```
GET /api/s/{site}/stat/dpi
```

### Notes

- DPI must be enabled on the UniFi controller for this tool to return data
- Statistics are cumulative since the last controller restart or statistics reset
- Some encrypted traffic may not be categorized accurately
- VPN traffic may appear as generic encrypted traffic

## GetAlertsTool

### Purpose

The alerts tool retrieves recent system alerts and events from the UniFi controller, including device status changes, security events, and configuration changes.

### Tool Definition

```python
name: "unifi_get_alerts"
description: "Get recent system alerts and events"
category: "statistics"
```

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "description": "Number of alerts to return (default: 50, max: 500)",
      "default": 50,
      "minimum": 1,
      "maximum": 500
    }
  }
}
```

### Output Format

```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "key": "EVT_GW_WANTransition",
        "message": "WAN connection restored",
        "timestamp": "2025-10-09T10:00:00Z",
        "time": 1728468000,
        "archived": false,
        "handled": false,
        "subsystem": "wan",
        "device_mac": "aa:bb:cc:dd:ee:ff",
        "device_name": "Gateway",
        "client_mac": "11:22:33:44:55:66",
        "client_name": "Laptop"
      }
    ],
    "summary": {
      "total_available": 150,
      "returned": 50,
      "archived": 10,
      "unarchived": 40,
      "alert_types": {
        "EVT_GW_WANTransition": 5,
        "EVT_AP_Disconnected": 3,
        "EVT_AP_Connected": 3
      }
    },
    "message": "Retrieved 50 of 150 total alerts"
  },
  "message": "Retrieved 50 alerts successfully"
}
```

### Key Features

1. **Flexible Limiting**: Control how many alerts to retrieve (1-500)
2. **Alert Categorization**: Alerts are grouped by type in the summary
3. **Archive Status**: Shows which alerts have been archived
4. **Device/Client Context**: Includes device and client information when relevant
5. **Summary Statistics**: Provides counts of archived vs unarchived alerts

### Alert Types

Common alert types include:

- **EVT_GW_WANTransition**: WAN connection status changes
- **EVT_AP_Disconnected**: Access point disconnected
- **EVT_AP_Connected**: Access point connected
- **EVT_SW_Disconnected**: Switch disconnected
- **EVT_SW_Connected**: Switch connected
- **EVT_IPS_IpsAlert**: Intrusion prevention system alert
- **EVT_AD_Login**: Admin login event
- **EVT_GW_Upgraded**: Gateway firmware upgraded

### Use Cases

1. **System Monitoring**: Track device status changes and system events
2. **Security Auditing**: Review security-related alerts (IPS, login attempts)
3. **Troubleshooting**: Identify recent issues or changes
4. **Compliance**: Maintain audit trail of system events
5. **Proactive Maintenance**: Catch issues before they become problems

### Example Prompts

```
"Show me recent alerts"
"What are the latest system events?"
"Are there any security alerts?"
"Show me the last 20 alerts"
"What alerts are unarchived?"
"Have any devices disconnected recently?"
```

### API Endpoint

```
GET /api/s/{site}/stat/alarm
```

### Notes

- Alerts are returned in reverse chronological order (newest first)
- Archived alerts are included in the results
- The `handled` flag indicates if the alert has been acknowledged
- Device and client information is only included when relevant to the alert
- Alert retention depends on controller configuration

## Testing

Both tools have comprehensive unit tests in `tests/test_statistics_tools.py`:

### DPI Tests

```bash
# Run DPI tool tests
python -m pytest tests/test_statistics_tools.py::TestGetDPIStatsTool -v

# Tests include:
# - Tool metadata validation
# - Successful DPI stats retrieval
# - Empty data handling
# - API error handling
# - Byte formatting
```

### Alerts Tests

```bash
# Run alerts tool tests
python -m pytest tests/test_statistics_tools.py::TestGetAlertsTool -v

# Tests include:
# - Tool metadata validation
# - Successful alerts retrieval
# - Limit parameter handling
# - Limit validation (min/max)
# - Empty data handling
# - API error handling
# - Summary statistics calculation
```

## Demo Script

Run the demo script to see these tools in action:

```bash
cd projects/unifi-mcp-server
python examples/dpi_alerts_demo.py
```

The demo shows:
1. DPI statistics with top applications
2. System alerts with filtering
3. Full JSON responses for reference

## Integration with MCP

These tools are automatically registered with the MCP server and available to AI agents:

```python
# In server.py
from .tools.statistics import GetDPIStatsTool, GetAlertsTool

tools_to_register = [
    # ... other tools ...
    GetDPIStatsTool(),
    GetAlertsTool(),
]
```

## Performance Considerations

### DPI Statistics

- **Cache TTL**: 30 seconds (configurable)
- **Response Time**: Typically < 1 second
- **Data Size**: Varies based on number of applications (typically 10-100 KB)

### Alerts

- **Cache TTL**: 10 seconds (configurable)
- **Response Time**: Typically < 1 second
- **Data Size**: Varies based on limit parameter (1-50 KB for 50 alerts)

## Error Handling

Both tools implement robust error handling:

```python
try:
    result = await tool.execute(client)
except ToolError as e:
    # Handle tool-specific errors
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")
    print(f"Details: {e.details}")
    print(f"Steps: {e.actionable_steps}")
```

Common error codes:
- `API_ERROR`: Failed to communicate with UniFi controller
- `VALIDATION_ERROR`: Invalid input parameters

## Best Practices

### DPI Statistics

1. **Regular Monitoring**: Check DPI stats regularly to understand baseline traffic
2. **Trend Analysis**: Compare stats over time to identify changes
3. **Capacity Planning**: Use traffic data to plan network upgrades
4. **Policy Creation**: Create QoS policies based on application usage

### Alerts

1. **Set Appropriate Limits**: Use smaller limits for quick checks, larger for analysis
2. **Archive Old Alerts**: Keep the alert list manageable by archiving resolved issues
3. **Monitor Unarchived**: Focus on unarchived alerts for active issues
4. **Correlate Events**: Look for patterns in alert types and timing

## Requirements Satisfied

These tools satisfy the following requirements from the design document:

- **Requirement 6.5**: DPI statistics retrieval
- **Requirement 6.6**: System alerts and events
- **Requirement 12.1**: Unit tests for core functionality
- **Requirement 12.3**: Test data formatting

## Next Steps

With DPI and alerts tools complete, the next phase focuses on:

1. **Migration Support Tools** (Task 20):
   - DHCP status monitoring
   - VLAN connectivity verification
   - Configuration export

2. **Write Operations Framework** (Task 21):
   - Safety controls for write operations
   - Confirmation requirements
   - Audit logging

## Related Documentation

- [Statistics Tools Guide](STATISTICS-TOOLS-GUIDE.md) - Overview of all statistics tools
- [Client/Device Stats Guide](CLIENT-DEVICE-STATS-GUIDE.md) - Client and device statistics
- [Quick Reference](QUICK-REFERENCE.md) - All available tools
- [Task 19 Summary](TASK-19-SUMMARY.md) - Implementation details

## Support

For issues or questions:
1. Check the demo script for usage examples
2. Review the unit tests for expected behavior
3. Check server logs for detailed error messages
4. Verify DPI is enabled on the UniFi controller (for DPI stats)
