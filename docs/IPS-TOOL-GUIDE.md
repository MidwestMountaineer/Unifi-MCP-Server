# UniFi IPS Status Tool Guide

## Overview

The `GetIPSStatusTool` provides comprehensive visibility into the UniFi Intrusion Prevention System (IPS/IDS), including configuration status, threat detection statistics, and recent security alerts.

## Tool Information

**Tool Name**: `unifi_get_ips_status`  
**Category**: Security  
**Type**: Read-only  
**Requirements**: Requirement 5.7

## Features

### 1. IPS Configuration Status
- Enabled/disabled state
- Suppression settings
- Signature version tracking
- Last update timestamp

### 2. Threat Detection Statistics
- Total events detected
- Blocked events count
- Alerted events count
- Category breakdown (malware, exploits, policy violations, etc.)

### 3. Security Alerts
- Recent IPS-related alerts
- Configurable alert limit (1-100)
- Detailed alert information:
  - Alert ID and key
  - Message and severity
  - Timestamp
  - Source and destination IPs
  - Signature ID and category

## Usage

### Basic Usage

```python
from unifi_mcp.tools.security import GetIPSStatusTool

# Create tool instance
ips_tool = GetIPSStatusTool()

# Get IPS status with alerts (default)
result = await ips_tool.execute(
    unifi_client=client,
    include_alerts=True,
    alert_limit=20
)
```

### Get Status Only (No Alerts)

```python
# Get IPS status without alerts (faster, smaller response)
result = await ips_tool.execute(
    unifi_client=client,
    include_alerts=False
)
```

### Get Limited Alerts

```python
# Get IPS status with only 5 most recent alerts
result = await ips_tool.execute(
    unifi_client=client,
    include_alerts=True,
    alert_limit=5
)
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_alerts` | boolean | No | `true` | Include recent IPS alerts in response |
| `alert_limit` | integer | No | `20` | Maximum number of alerts to return (1-100) |

## Response Format

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "key": "ips",
    "suppression_enabled": false,
    "suppression_mode": "",
    "threat_statistics": {
      "total_events": 1234,
      "blocked_events": 890,
      "alerted_events": 344,
      "categories": {
        "malware": 450,
        "exploit": 340,
        "policy-violation": 444
      }
    },
    "signature_version": "2024.10.01",
    "last_signature_update": "2024-10-01T12:00:00Z",
    "recent_alerts": [
      {
        "id": "abc123",
        "key": "EVT_IPS_Alert",
        "message": "Potential exploit detected",
        "timestamp": 1696176000,
        "datetime": "2024-10-01T14:30:00Z",
        "severity": "high",
        "source_ip": "192.168.1.100",
        "destination_ip": "8.8.8.8",
        "signature_id": "2024001",
        "category": "exploit"
      }
    ],
    "total_alerts": 15
  },
  "item_type": "ips_status"
}
```

## AI Agent Prompts

The tool responds to natural language queries:

### Status Queries
- "What's the IPS status?"
- "Is intrusion prevention enabled?"
- "Show me the IPS configuration"

### Threat Queries
- "What threats has IPS detected?"
- "How many attacks were blocked?"
- "Show me threat statistics"
- "What categories of threats are being detected?"

### Alert Queries
- "Show me IPS alerts"
- "What are the recent security alerts?"
- "Show me the last 5 IPS alerts"
- "Are there any intrusion attempts?"

## UniFi API Endpoints

The tool uses three UniFi API endpoints:

### 1. IPS Settings
**Endpoint**: `/api/s/{site}/rest/setting/ips`  
**Purpose**: Retrieve IPS configuration and enabled status

### 2. IPS Statistics
**Endpoint**: `/api/s/{site}/stat/ips/event`  
**Purpose**: Retrieve threat detection event statistics

### 3. System Alerts
**Endpoint**: `/api/s/{site}/rest/alarm`  
**Purpose**: Retrieve recent system alerts (filtered for IPS-related)

## Alert Filtering

The tool automatically filters alerts to include only IPS-related events by checking for these keywords in the alert key:
- `ips`, `ids`
- `intrusion`
- `threat`, `attack`
- `malware`, `exploit`

## Error Handling

### Common Errors

#### API Connection Error
```json
{
  "error": {
    "code": "API_ERROR",
    "message": "Failed to retrieve IPS status",
    "details": "Connection timeout",
    "actionable_steps": [
      "Check UniFi controller is accessible",
      "Verify IPS/IDS is configured on the controller",
      "Check server logs for details"
    ]
  }
}
```

### Troubleshooting

1. **IPS Not Configured**: If IPS is not configured on the controller, the tool will return default values with `enabled: false`

2. **No Statistics**: If no IPS events have been recorded, threat statistics will show zero counts

3. **No Alerts**: If there are no IPS-related alerts, the `recent_alerts` array will be empty

## Performance Considerations

### Response Time
- **Typical**: <1 second
- **With Alerts**: 1-2 seconds (depends on alert count)
- **Without Alerts**: <1 second

### Data Volume
- **Status Only**: ~500 bytes
- **With 20 Alerts**: ~10KB
- **With 100 Alerts**: ~50KB

### Caching Recommendations
- Cache IPS status for 30-60 seconds
- Cache threat statistics for 10-30 seconds
- Don't cache alerts (real-time data)

## Security Considerations

### Read-Only Operation
- Tool only reads IPS status and alerts
- No configuration changes possible
- Safe for AI agent use

### Data Sensitivity
- Alert details may contain internal IP addresses
- Signature IDs are non-sensitive
- Threat statistics are aggregated and safe to share

### Logging
- All IPS status requests are logged
- Alert counts logged for monitoring
- No sensitive data in logs (IPs are redacted)

## Integration Examples

### With MCP Server

```python
# Register tool with MCP server
from unifi_mcp.tools.security import GetIPSStatusTool

server.register_tool(GetIPSStatusTool())
```

### With Kiro

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-mcp-server"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password"
      }
    }
  }
}
```

Then use natural language:
```
"Show me the IPS status and recent alerts"
```

## Demo Script

Run the demo script to test the tool:

```bash
cd projects/unifi-mcp-server
python examples/ips_demo.py
```

The demo script tests:
1. Get IPS status with alerts (default limit)
2. Get IPS status without alerts
3. Get IPS status with limited alerts (5)

## Related Tools

- **List Firewall Rules**: `unifi_list_firewall_rules`
- **Get Alerts**: `unifi_get_alerts` (all system alerts)
- **Get System Health**: `unifi_get_system_health`

## Best Practices

### 1. Use Alert Limits
Always specify an appropriate `alert_limit` to control response size:
- For quick checks: `alert_limit=5`
- For detailed analysis: `alert_limit=20`
- For comprehensive review: `alert_limit=50`

### 2. Disable Alerts When Not Needed
If you only need status information, set `include_alerts=false` for faster responses.

### 3. Monitor Threat Statistics
Regularly check threat statistics to understand your security posture:
- Increasing blocked events = IPS is working
- High alerted events = potential threats to investigate
- Category breakdown = types of threats targeting your network

### 4. Investigate Alerts
When alerts are present:
1. Check source and destination IPs
2. Review signature ID and category
3. Correlate with firewall rules
4. Take action if needed (block IPs, update rules)

## Limitations

1. **No Historical Data**: Tool only shows current status and recent alerts
2. **No Alert Details**: Full alert details require separate API calls
3. **No Configuration**: Tool is read-only, cannot enable/disable IPS
4. **Alert Filtering**: Keyword-based filtering may miss some IPS alerts

## Future Enhancements

Potential improvements for future versions:
1. Historical threat statistics (daily, weekly, monthly)
2. Alert trend analysis
3. Top threat sources (IP addresses)
4. Signature effectiveness metrics
5. IPS performance impact metrics

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Verify UniFi controller is accessible
3. Ensure IPS is configured on the controller
4. Review the task summary: `docs/TASK-16-SUMMARY.md`

---

**Last Updated**: October 9, 2025  
**Version**: 1.0  
**Status**: Production Ready
