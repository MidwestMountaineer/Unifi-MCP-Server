---
name: "unifi-network"
displayName: "UniFi Network"
description: "Monitor and manage UniFi network infrastructure through 25 production-ready MCP tools. Perform security audits, troubleshoot connectivity, analyze bandwidth, and export configurations using natural language."
keywords: ["unifi", "ubiquiti", "network", "firewall", "vlan", "dream-machine", "homelab"]
author: "Austin"
---

# UniFi Network Power

## Overview

Complete end-to-end network management workflows - from initial setup through ongoing monitoring, security auditing, and troubleshooting - all without leaving the IDE.

**Supported Hardware:** UniFi Dream Machine, Cloud Gateway, traditional controllers, switches, and access points

## What Can You Do?

### Complete Security Audit
**"Perform a security audit of my network"**
- Check IPS status and recent threats → Review firewall rules for gaps → Analyze port forwards for risks → Generate security report with actionable recommendations

### Troubleshoot Connectivity Issues  
**"My laptop can't reach the NAS on the Core VLAN"**
- Find device location and VLAN → Test inter-VLAN connectivity → Identify blocking firewall rules → Provide specific resolution steps

### Network Health Assessment
**"Check my network health and performance"**
- System health overview → Device status check → Bandwidth analysis → Alert review → Performance recommendations

### Generate Network Documentation
**"Create documentation for my network setup"**
- Device inventory → VLAN architecture → Security configuration → WiFi networks → Export backup configuration

### Bandwidth Analysis
**"Who's using all my bandwidth?"**
- Top clients by usage → Application breakdown → Device statistics → Performance bottleneck identification

## Available Steering Files

| File | Description | Load When You Need |
|------|-------------|-------------------|
| **monitoring.md** | Health checks, device status, alerts, bandwidth analysis | "health check", "status", "alerts", "bandwidth", "performance" |
| **security.md** | Firewall rules, IPS, security auditing, port forwards, best practices | "security", "firewall", "audit", "IPS", "port forward" |
| **troubleshooting.md** | Connection errors, authentication issues, diagnostics, recovery | "error", "not working", "can't connect", "offline", "problem" |
| **vlan.md** | VLAN design, inter-VLAN routing, segmentation patterns | "VLAN", "segmentation", "routing", "network design" |
| **workflows.md** | Multi-step scenarios, automation recipes, common tasks | "workflow", "automate", "recipe", "how do I" |

## Quick Setup

Choose your controller type below:

### Option A: Dream Machine / UniFi OS (Recommended)

**Step 1: Generate API Key**
1. Open Dream Machine web UI (https://YOUR_CONTROLLER_IP)
2. Go to **Settings** → **System** → **Advanced** → **API**
3. Click **Create New API Key**, name it "Kiro MCP"
4. Select **Read Only** for security
5. Copy the key (shown only once!)

**Step 2: Install as Kiro Power (Recommended)**

1. Open Kiro's Powers panel
2. Click "Add Custom Power" → "Import from local folder"
3. Point to your local clone of this repository
4. The power will auto-configure with your credentials

**Alternative: Manual MCP Configuration**

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "/path/to/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your-api-key-here",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false,
      "autoApprove": ["unifi_list_*", "unifi_get_*"]
    }
  }
}
```

**Configuration Options:**
| Variable | Description | Default |
|----------|-------------|---------|
| `UNIFI_HOST` | Controller IP address | (required) |
| `UNIFI_PORT` | Controller port | `443` |
| `UNIFI_API_KEY` | API key from step 1 | (required) |
| `UNIFI_SITE` | Site name | `default` |
| `UNIFI_VERIFY_SSL` | Verify SSL certs | `false` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

### Option B: Traditional Controller (Self-Hosted)

For standalone UniFi Controller software (not UniFi OS):

**Step 1: Get Admin Credentials**
Use your existing admin username and password for the controller.

**Step 2: Configure MCP Server**

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "/path/to/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.100",
        "UNIFI_PORT": "8443",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "your-password-here",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false,
      "autoApprove": ["unifi_list_*", "unifi_get_*"]
    }
  }
}
```

**Key Differences from Dream Machine:**
| Setting | Dream Machine | Traditional |
|---------|---------------|-------------|
| Port | `443` | `8443` |
| Auth | API Key | Username/Password |
| SSL | Usually self-signed | Usually self-signed |

---

### Step 3: Test Connection

Try: "List all my UniFi devices" or "Show network health"

**Troubleshooting:**
- **Connection refused**: Check UNIFI_HOST and UNIFI_PORT
- **401 Unauthorized**: Verify API key or credentials
- **SSL errors**: Set `UNIFI_VERIFY_SSL` to `false`
- **Site not found**: Check UNIFI_SITE matches your site name

## Tool Quick Reference

| Task | Tool | Example Prompt |
|------|------|----------------|
| **Discovery** | | |
| List all devices | `unifi_list_devices` | "Show my network devices" |
| Device details | `unifi_get_device_details` | "Get details for switch ABC123" |
| List clients | `unifi_list_clients` | "Show connected wireless clients" |
| Client details | `unifi_get_client_details` | "Get details for device aa:bb:cc:dd:ee:ff" |
| List VLANs | `unifi_list_networks` | "Show all configured networks" |
| VLAN details | `unifi_get_network_details` | "Get IoT VLAN configuration" |
| List WiFi | `unifi_list_wlans` | "Show wireless networks" |
| WiFi details | `unifi_get_wlan_details` | "Get Guest WiFi settings" |
| **Security** | | |
| Security audit | `unifi_list_firewall_rules` + `unifi_get_ips_status` | "Audit my network security" |
| Firewall rules | `unifi_list_firewall_rules` | "Show firewall rules" |
| IPS status | `unifi_get_ips_status` | "Check intrusion prevention" |
| Port forwards | `unifi_list_port_forwards` | "List port forwarding rules" |
| Traffic routes | `unifi_list_traffic_routes` | "Show routing configuration" |
| **Statistics** | | |
| Network health | `unifi_get_system_health` | "Check network health" |
| Network stats | `unifi_get_network_stats` | "Show network statistics" |
| Top users | `unifi_get_top_clients` | "Who's using most bandwidth?" |
| App usage | `unifi_get_dpi_stats` | "Show application usage" |
| Recent alerts | `unifi_get_alerts` | "Show recent network alerts" |
| **Migration** | | |
| DHCP status | `unifi_get_dhcp_status` | "Show DHCP leases" |
| Test connectivity | `unifi_verify_vlan_connectivity` | "Test IoT to Core connectivity" |
| Backup config | `unifi_export_configuration` | "Export network configuration" |

## Best Practices

- Use **list tools** for overviews (faster)
- Use **detail tools** when you need specifics
- Check **system health** regularly with `unifi_get_system_health`
- **Export configuration** weekly with `unifi_export_configuration`
- All 25 tools are **read-only** and safe to use

---

**25 Production-Ready Tools** | **Read-Only & Safe** | **Works with Dream Machine & Traditional Controllers**
