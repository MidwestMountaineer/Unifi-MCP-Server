# UniFi Network Monitoring Guide

Comprehensive monitoring workflows for network health checks, bandwidth analysis, and proactive issue detection.

## When to Use This Guide

- Performing routine network health checks
- Investigating bandwidth usage or performance issues
- Monitoring device status and alerts
- Analyzing traffic patterns with DPI
- Proactive network maintenance

## Prerequisites

- UniFi Power activated with valid API key
- Access to UniFi controller (Dream Machine or traditional)
- Appropriate permissions for monitoring endpoints

---

## Health Check Workflow

A complete network health assessment using system health, device status, and alerts.

### Step 1: Get System Health Overview

**Tool:** `unifi_get_system_health`

**What it provides:**
- Overall system status (healthy/degraded/critical)
- Subsystem health (network, storage, memory, CPU)
- Controller uptime and version
- Site-level health metrics

**Example prompt:** "Check my network system health"

**Interpreting Results:**

| Status | Meaning | Action |
|--------|---------|--------|
| `healthy` | All systems operating normally | No action needed |
| `degraded` | Some issues detected | Review specific subsystems |
| `critical` | Major issues present | Immediate investigation required |

### Step 2: Check Device Status

**Tool:** `unifi_list_devices`

**What it provides:**
- All network devices (switches, APs, gateways)
- Connection status (online/offline/pending)
- Firmware versions
- Uptime and load metrics

**Example prompt:** "List all my UniFi devices and their status"

### Step 3: Review Recent Alerts

**Tool:** `unifi_get_alerts(limit=50)`

**What it provides:**
- Recent system alerts and events
- Severity levels (info, warning, critical)
- Timestamps and affected devices

**Example prompt:** "Show me recent network alerts"

---

## Bandwidth Analysis Workflow

Identify bandwidth hogs, analyze traffic patterns, and optimize network performance.

### Step 1: Get Network Statistics Overview

**Tool:** `unifi_get_network_stats`

**What it provides:**
- Total bandwidth usage (upload/download)
- Active client count
- Traffic by network/VLAN
- Historical usage trends

**Example prompt:** "Show me network bandwidth statistics"

### Step 2: Identify Top Bandwidth Consumers

**Tool:** `unifi_get_top_clients(limit=10)`

**What it provides:**
- Clients ranked by bandwidth usage
- Upload and download totals per client
- Connection type (wired/wireless)
- Device names and MAC addresses

**Example prompt:** "Show me the top 10 bandwidth users"

### Step 3: Analyze Traffic by Application (DPI)

**Tool:** `unifi_get_dpi_stats`

**What it provides:**
- Traffic categorized by application type
- Bandwidth per application category
- Top applications by usage

**Example prompt:** "Show me deep packet inspection statistics"

---

## Common Issues and Solutions

### Issue: Device Shows Offline But Network Works

**Diagnostic tools:**
- `unifi_list_devices` - Check device state
- `unifi_get_device_details(device_id="...")` - Get detailed status

**Solutions:**
1. Verify device can ping controller IP
2. Check firewall rules allow inform traffic (port 8080)
3. Factory reset and re-adopt if needed

### Issue: High CPU/Memory on Gateway

**Diagnostic tools:**
- `unifi_get_system_health` - Check resource usage
- `unifi_get_device_stats(device_id="gateway_mac")` - Detailed metrics

**Common causes:**
- IPS/IDS enabled (reduce sensitivity or disable)
- DPI enabled (disable if not needed)
- Too many clients (segment with VLANs)

### Issue: Wireless Client Poor Performance

**Diagnostic tools:**
- `unifi_list_clients(connection_type="wireless")` - List WiFi clients
- `unifi_get_client_details(mac_address="...")` - Check signal strength

**Signal strength interpretation:**
| RSSI | Quality |
|------|---------|
| > -50 dBm | Excellent |
| -50 to -60 | Good |
| -60 to -70 | Fair |
| -70 to -80 | Poor |
| < -80 dBm | Unusable |

---

## Monitoring Best Practices

### Daily Checks
- Review critical alerts
- Check device online status
- Verify system health green

### Weekly Checks
- Review bandwidth trends
- Check top consumers
- Verify firmware is current

### Monthly Checks
- Full health report
- Capacity planning review
- Configuration backup

---

## Next Steps

- **Security concerns?** Load `security.md` for audit workflows
- **Connectivity issues?** Load `troubleshooting.md` for diagnostics
- **VLAN questions?** Load `vlan.md` for network design
