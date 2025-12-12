# Client and Device Statistics Tools Guide

This guide covers the client and device statistics tools for detailed performance monitoring and bandwidth analysis.

## Tools Overview

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `unifi_get_client_stats` | Get detailed stats for a specific client | MAC address | Client identity, connection, bandwidth, device info |
| `unifi_get_device_stats` | Get detailed stats for a specific device | Device ID or MAC | Device identity, status, system health, port/wireless stats |
| `unifi_get_top_clients` | List top bandwidth consumers | Limit (optional) | Sorted list of clients by bandwidth usage |

## Tool Details

### unifi_get_client_stats

Get comprehensive statistics for a specific client.

**Input Schema**:
```json
{
  "mac_address": "aa:bb:cc:dd:ee:ff"  // Required: Client MAC address
}
```

**Output Structure**:
```json
{
  "success": true,
  "data": {
    "identity": {
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "name": "Desktop PC",
      "hostname": "desktop-pc",
      "ip_address": "192.168.10.100"
    },
    "connection": {
      "type": "wired",  // or "wireless"
      "network": "Core",
      "vlan": 10,
      "uptime": 86400,
      "uptime_formatted": "1 days, 0 hours"
    },
    "bandwidth": {
      "tx_bytes": 1073741824,
      "rx_bytes": 2147483648,
      "tx_bytes_formatted": "1.00 GB",
      "rx_bytes_formatted": "2.00 GB",
      "tx_rate": 1000000,
      "rx_rate": 1000000,
      "tx_rate_formatted": "1000.00 Mbps",
      "rx_rate_formatted": "1000.00 Mbps"
    },
    "device_info": {
      "manufacturer": "Dell Inc.",
      "os_name": "Windows",
      "os_class": "Windows",
      "device_name": "Desktop PC"
    },
    "wireless": {  // Only for wireless clients
      "signal": -45,
      "noise": -95,
      "rssi": 50,
      "channel": 36,
      "essid": "HomeNetwork",
      "radio": "ng",
      "radio_proto": "ax"
    },
    "session": {
      "first_seen": 1696800000,
      "last_seen": 1696886400,
      "latest_assoc_time": 1696800000
    }
  },
  "message": "Client statistics retrieved successfully for aa:bb:cc:dd:ee:ff"
}
```

**Example Prompts**:
- "Show me stats for client aa:bb:cc:dd:ee:ff"
- "What's the bandwidth usage for my laptop?"
- "How long has this device been connected?"
- "What's the signal strength for this wireless client?"

**Features**:
- MAC address normalization (handles various formats: with/without colons, uppercase/lowercase)
- Separate wireless statistics for wireless clients
- Human-readable formatting for bytes and uptime
- Session tracking information

---

### unifi_get_device_stats

Get comprehensive statistics for a specific UniFi device.

**Input Schema**:
```json
{
  "device_id": "device123"  // Required: Device ID or MAC address
}
```

**Output Structure**:
```json
{
  "success": true,
  "data": {
    "identity": {
      "id": "device123",
      "mac_address": "11:22:33:44:55:66",
      "name": "Core Switch",
      "model": "US-24-250W",
      "type": "usw",
      "version": "6.5.59"
    },
    "status": {
      "state": "online",  // or "offline"
      "adopted": true,
      "uptime": 172800,
      "uptime_formatted": "2 days, 0 hours",
      "last_seen": 1696886400
    },
    "network": {
      "ip_address": "192.168.10.2",
      "uplink": {
        "type": "wire",
        "speed": 10000,
        "full_duplex": true
      }
    },
    "statistics": {
      "tx_bytes": 10737418240,
      "rx_bytes": 21474836480,
      "tx_bytes_formatted": "10.00 GB",
      "rx_bytes_formatted": "20.00 GB"
    },
    "system": {  // If available
      "cpu_usage": 15,
      "memory_usage": 30,
      "uptime": 172800,
      "temperatures": {
        "Board (CPU)": 45,
        "PHY": 50
      }
    },
    "ports": {  // For switches
      "total": 24,
      "active": 18,
      "details": [
        {
          "port_idx": 1,
          "name": "Port 1",
          "up": true,
          "speed": 1000,
          "full_duplex": true,
          "tx_bytes": 1073741824,
          "rx_bytes": 2147483648
        }
        // ... more ports (limited to first 10)
      ]
    },
    "wireless": {  // For access points
      "num_sta": 5,
      "user-num_sta": 4,
      "guest-num_sta": 1,
      "radios": [
        {
          "name": "wifi0",
          "radio": "ng",
          "channel": 6,
          "tx_power": 20,
          "num_sta": 3
        }
        // ... more radios
      ]
    }
  },
  "message": "Device statistics retrieved successfully for device123"
}
```

**Example Prompts**:
- "Show me stats for device abc123"
- "What's the CPU usage on my switch?"
- "Check the temperature of my access point"
- "How much traffic is going through this device?"

**Features**:
- Lookup by device ID or MAC address
- Device-type-specific data:
  - Switches: Port statistics with per-port traffic
  - Access Points: Wireless client counts and radio details
  - Gateways: Standard network statistics
- System health metrics (CPU, memory, temperature)
- Human-readable formatting

---

### unifi_get_top_clients

List clients sorted by total bandwidth usage.

**Input Schema**:
```json
{
  "limit": 10  // Optional: Number of clients to return (default: 10, max: 100)
}
```

**Output Structure**:
```json
{
  "success": true,
  "data": {
    "clients": [
      {
        "mac_address": "aa:bb:cc:dd:ee:01",
        "name": "Desktop PC",
        "hostname": "desktop-pc",
        "ip_address": "192.168.10.100",
        "connection_type": "wired",
        "network": "Core",
        "tx_bytes": 1073741824,
        "rx_bytes": 2147483648,
        "total_bytes": 3221225472,
        "tx_bytes_formatted": "1.00 GB",
        "rx_bytes_formatted": "2.00 GB",
        "total_bytes_formatted": "3.00 GB",
        "uptime": 86400,
        "uptime_formatted": "1 days, 0 hours"
      }
      // ... more clients (sorted by total_bytes descending)
    ],
    "summary": {
      "total_clients": 25,
      "top_clients_count": 10,
      "total_bandwidth": 10737418240,
      "total_bandwidth_formatted": "10.00 GB",
      "top_bandwidth": 8589934592,
      "top_bandwidth_formatted": "8.00 GB",
      "top_percentage": 80.0
    }
  },
  "message": "Top 10 clients by bandwidth retrieved successfully"
}
```

**Example Prompts**:
- "Who are the top bandwidth users?"
- "Show me the top 5 clients by bandwidth"
- "Which devices are using the most data?"
- "List bandwidth hogs on my network"

**Features**:
- Sorts by total bandwidth (TX + RX)
- Configurable result limit
- Summary statistics showing percentage of total bandwidth
- Useful for identifying bandwidth hogs and capacity planning

## Common Use Cases

### 1. Troubleshooting Slow Network Performance

```
User: "My network feels slow. Who's using all the bandwidth?"
AI: Uses unifi_get_top_clients to identify top consumers
AI: Uses unifi_get_client_stats on top clients to see what they're doing
```

### 2. Monitoring Specific Client

```
User: "Check the connection quality for my laptop (MAC: aa:bb:cc:dd:ee:ff)"
AI: Uses unifi_get_client_stats to get signal strength, bandwidth, uptime
AI: Reports signal strength, connection type, and any issues
```

### 3. Device Health Check

```
User: "Is my core switch running hot?"
AI: Uses unifi_get_device_stats to check temperature and CPU usage
AI: Reports system health metrics and any concerns
```

### 4. Port Status Check

```
User: "Which ports are active on my switch?"
AI: Uses unifi_get_device_stats to get port statistics
AI: Lists active ports with speed and traffic information
```

### 5. Wireless Client Analysis

```
User: "Why is my phone's WiFi connection slow?"
AI: Uses unifi_get_client_stats to check signal strength and channel
AI: Analyzes wireless metrics and suggests improvements
```

## Error Handling

### Client Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Client not found: aa:bb:cc:dd:ee:ff",
    "details": "No client with MAC address aa:bb:cc:dd:ee:ff is currently connected",
    "actionable_steps": [
      "Verify the MAC address is correct",
      "Check if the client is currently connected",
      "Use unifi_list_clients to see all connected clients"
    ]
  }
}
```

### Device Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Device not found: device123",
    "details": "No device with ID or MAC address device123 found",
    "actionable_steps": [
      "Verify the device ID or MAC address is correct",
      "Use unifi_list_devices to see all devices"
    ]
  }
}
```

## Performance Considerations

- **Caching**: Client and device data is cached for 30 seconds at the UniFi client level
- **Response Time**: Typically <1 second for individual client/device stats
- **Top Clients**: Sorting is done in-memory, very fast even with 100+ clients
- **Port Details**: Limited to first 10 ports for switches to avoid large responses

## Tips for AI Agents

1. **Use Top Clients First**: When investigating bandwidth issues, start with `unifi_get_top_clients` to identify suspects, then drill down with `unifi_get_client_stats`.

2. **MAC Address Formats**: The tools handle various MAC address formats, so don't worry about normalizing them first.

3. **Device Type Detection**: Check the device type in the response to know what additional data is available (ports for switches, wireless for APs).

4. **Human-Readable Values**: Use the `_formatted` fields for displaying to users, but use the raw values for calculations.

5. **Wireless Troubleshooting**: For wireless clients, check signal strength (>-70 dBm is good), RSSI (>30 is good), and channel congestion.

6. **System Health**: For devices, CPU >80% or temperature >70°C may indicate issues.

## Integration with Other Tools

These tools work well with:
- `unifi_list_clients` - Get all clients, then drill down with `unifi_get_client_stats`
- `unifi_list_devices` - Get all devices, then drill down with `unifi_get_device_stats`
- `unifi_get_network_stats` - Compare individual stats to overall network stats
- `unifi_get_alerts` - Correlate performance issues with system alerts

## Example Workflow

```
1. User: "My network is slow"
2. AI: unifi_get_top_clients(limit=5)
   → Identifies top 5 bandwidth consumers
3. AI: unifi_get_client_stats(mac_address=top_client_mac)
   → Gets detailed stats for top consumer
4. AI: Reports findings and suggests actions
```

## Conclusion

These tools provide granular visibility into client and device performance, enabling detailed network analysis and troubleshooting. Use them to:
- Identify bandwidth hogs
- Monitor client connection quality
- Check device health
- Troubleshoot performance issues
- Plan capacity upgrades
