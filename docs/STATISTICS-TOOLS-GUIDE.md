# Statistics Tools Guide

## Overview

The statistics tools provide comprehensive monitoring capabilities for your UniFi network infrastructure. These tools are read-only and designed for AI agent consumption.

## Available Tools

### 1. Get Network Statistics (`unifi_get_network_stats`)

Retrieves overall network statistics and health metrics.

**Use Cases:**
- Monitor overall network health
- Track connected client counts
- View bandwidth usage
- Check subsystem status

**Input Parameters:**
None required.

**Example Prompts:**
- "What's the overall network status?"
- "How many clients are connected?"
- "Show me network statistics"
- "What's the current bandwidth usage?"

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_clients": 15,
      "wired_clients": 5,
      "wireless_clients": 10,
      "total_devices": 8,
      "online_devices": 7,
      "offline_devices": 1
    },
    "bandwidth": {
      "total_tx_bytes": 1500000000,
      "total_rx_bytes": 3500000000,
      "total_tx_bytes_formatted": "1.40 GB",
      "total_rx_bytes_formatted": "3.26 GB"
    },
    "health": {
      "wan_status": "ok",
      "lan_status": "ok",
      "vpn_status": "ok",
      "www_status": "ok"
    },
    "uptime": {
      "gateway_uptime": 86400,
      "gateway_uptime_formatted": "1 days, 0 hours"
    }
  },
  "message": "Network statistics retrieved successfully"
}
```

**Key Metrics:**
- **Total Clients**: Number of connected devices (wired + wireless)
- **Device Status**: Online/offline device counts
- **Bandwidth**: Total transmitted and received bytes
- **Health Status**: Status of WAN, LAN, VPN, and WWW subsystems
- **Uptime**: Gateway uptime in seconds and human-readable format

---

### 2. Get System Health (`unifi_get_system_health`)

Retrieves system health metrics for the UniFi controller and devices.

**Use Cases:**
- Monitor controller health
- Check device CPU/memory/temperature
- View system alerts
- Assess overall infrastructure health

**Input Parameters:**
None required.

**Example Prompts:**
- "What's the system health?"
- "Show me controller status"
- "Are there any system alerts?"
- "Check device health"
- "What's the overall infrastructure status?"

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "controller": {
      "version": "7.5.176",
      "hostname": "unifi-controller",
      "uptime": 172800,
      "uptime_formatted": "2 days, 0 hours"
    },
    "subsystems": [
      {
        "name": "wan",
        "status": "ok",
        "uptime": 86400,
        "latency": 15,
        "drops": 0,
        "tx_bytes": 1000000,
        "rx_bytes": 2000000
      },
      {
        "name": "lan",
        "status": "ok",
        "uptime": 86400,
        "latency": 1,
        "drops": 0,
        "tx_bytes": 500000,
        "rx_bytes": 1500000
      }
    ],
    "devices": [
      {
        "name": "Switch 1",
        "type": "usw",
        "model": "US-24-250W",
        "state": "online",
        "uptime": 86400,
        "cpu_usage": 15,
        "memory_usage": 30,
        "temperature": 45
      },
      {
        "name": "AP 1",
        "type": "uap",
        "model": "U6-Pro",
        "state": "online",
        "uptime": 43200,
        "cpu_usage": 10,
        "memory_usage": 25,
        "temperature": 40
      }
    ],
    "alerts": {
      "total": 2,
      "recent": [
        {
          "key": "EVT_GW_WANTransition",
          "message": "WAN connection restored",
          "timestamp": "2025-10-09T10:00:00Z",
          "archived": false
        }
      ]
    },
    "overall_status": "healthy"
  },
  "message": "System health retrieved successfully"
}
```

**Key Metrics:**
- **Controller**: Version, hostname, and uptime
- **Subsystems**: Health status for WAN, LAN, VPN, WWW
- **Devices**: CPU, memory, temperature for each device
- **Alerts**: Recent system alerts and warnings
- **Overall Status**: Calculated health status (healthy/warning/critical)

**Overall Status Calculation:**
- **Healthy**: All subsystems OK, all devices online, no unarchived alerts
- **Warning**: Some devices offline OR unarchived alerts present
- **Critical**: Subsystem errors OR >50% devices offline

---

## Common Use Cases

### 1. Network Health Check

**Prompt**: "What's the overall network health?"

**Tools Used**: 
1. `unifi_get_network_stats` - Get client/device counts and bandwidth
2. `unifi_get_system_health` - Get subsystem status and alerts

**Expected Response**:
- Client count and breakdown
- Device online/offline status
- Bandwidth usage
- Subsystem health
- Any active alerts

### 2. Troubleshooting Connectivity Issues

**Prompt**: "Why is my network slow?"

**Tools Used**:
1. `unifi_get_network_stats` - Check bandwidth usage
2. `unifi_get_system_health` - Check device CPU/memory

**Expected Response**:
- High bandwidth usage indicators
- Device resource utilization
- Subsystem latency/drops
- Potential bottlenecks

### 3. Infrastructure Monitoring

**Prompt**: "Show me the status of all network devices"

**Tools Used**:
1. `unifi_get_system_health` - Get device health metrics

**Expected Response**:
- List of all devices with status
- CPU, memory, temperature for each
- Uptime information
- Overall health assessment

### 4. Alert Investigation

**Prompt**: "Are there any system alerts?"

**Tools Used**:
1. `unifi_get_system_health` - Get recent alerts

**Expected Response**:
- List of recent alerts
- Alert timestamps
- Archived vs active alerts
- Alert severity/type

---

## Error Handling

Both tools implement graceful error handling:

### Partial Data Support

If individual API calls fail, the tools return partial data rather than failing completely:

```json
{
  "success": true,
  "data": {
    "summary": {
      "total_clients": 0,  // Failed to retrieve
      "total_devices": 5   // Successfully retrieved
    }
  }
}
```

### Empty Data

When no data is available, tools return empty/default values:

```json
{
  "success": true,
  "data": {
    "summary": {
      "total_clients": 0,
      "wired_clients": 0,
      "wireless_clients": 0
    },
    "health": {
      "wan_status": "unknown"
    }
  }
}
```

---

## Performance Considerations

### Response Times

- **Network Stats**: ~1-2 seconds (3 API calls)
- **System Health**: ~2-3 seconds (4 API calls)

### API Calls

**Network Stats**:
- `/api/s/{site}/stat/health` - Site health
- `/api/s/{site}/stat/device` - Device status
- `/api/s/{site}/stat/sta` - Client status

**System Health**:
- `/api/s/{site}/stat/health` - Subsystem health
- `/api/s/{site}/stat/device` - Device metrics
- `/api/s/{site}/stat/sysinfo` - Controller info
- `/api/s/{site}/stat/alarm` - System alerts

### Optimization Tips

1. **Caching**: Results can be cached for 30-60 seconds
2. **Selective Queries**: Use specific tools rather than both
3. **Off-Peak**: Run monitoring during off-peak hours

---

## Integration Examples

### With Kiro

```
User: "What's my network status?"

Kiro: [Calls unifi_get_network_stats]
      "Your network has 15 connected clients (5 wired, 10 wireless) 
       across 7 online devices. Bandwidth usage is 1.4 GB transmitted 
       and 3.3 GB received. All subsystems are healthy."
```

### With Claude Desktop

```
User: "Check system health"

Claude: [Calls unifi_get_system_health]
        "System health is HEALTHY. Controller version 7.5.176 has been 
         running for 2 days. All 7 devices are online with normal CPU 
         and temperature. No active alerts."
```

---

## Troubleshooting

### Issue: Empty Data Returned

**Possible Causes:**
- API authentication issues
- Network connectivity problems
- UniFi controller unreachable

**Solutions:**
1. Check UNIFI_HOST environment variable
2. Verify API key or credentials
3. Test controller accessibility
4. Check server logs for details

### Issue: Partial Data Returned

**Possible Causes:**
- Some API endpoints failing
- Transient network issues
- Controller under load

**Solutions:**
1. Retry the request
2. Check controller performance
3. Review server logs for specific failures

### Issue: "Unknown" Status Values

**Possible Causes:**
- API response format changed
- Missing data in controller
- Unsupported controller version

**Solutions:**
1. Check controller version compatibility
2. Review API response format
3. Update tool implementation if needed

---

## Best Practices

1. **Regular Monitoring**: Check network stats every 5-10 minutes
2. **Alert Investigation**: Review system health when alerts occur
3. **Baseline Establishment**: Track normal values for comparison
4. **Trend Analysis**: Monitor changes over time
5. **Proactive Maintenance**: Address warnings before they become critical

---

## Related Tools

- **Network Discovery**: List devices and clients
- **Security Tools**: View firewall rules and IPS status
- **Client/Device Stats**: Detailed per-entity statistics (coming soon)

---

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Review API endpoint documentation
3. Test with demo script: `python examples/statistics_demo.py`
4. Verify UniFi controller accessibility

---

**Last Updated**: October 9, 2025
**Version**: 1.0
**Status**: Production Ready
