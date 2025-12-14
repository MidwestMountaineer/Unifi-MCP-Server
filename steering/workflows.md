# UniFi Network Workflows

Multi-step workflows for network documentation, configuration backup, and automation recipes.

## When to Use This Guide

- Generating comprehensive network documentation
- Creating configuration backups for disaster recovery
- Automating common multi-tool operations
- Performing complex multi-step network tasks

## Prerequisites

- UniFi Power activated with valid API key
- Access to UniFi controller (Dream Machine or traditional)
- Appropriate permissions for all endpoints

---

## Network Documentation Generation Workflow

Generate complete network documentation including device inventory, VLAN architecture, and security configuration.

### Step 1: Gather Device Inventory

**Tool:** `unifi_list_devices(response_format="detailed")`

**What to document:**
- All network devices (switches, APs, gateways)
- Device names, models, and MAC addresses
- IP addresses and firmware versions

**Example prompt:** "List all UniFi devices with full details"

### Step 2: Document VLAN Architecture

**Tool:** `unifi_list_networks`

**What to document:**
- All configured VLANs and their IDs
- IP address ranges (CIDR notation)
- DHCP settings and gateway addresses

**Example prompt:** "Show all networks and VLANs"

### Step 3: Document Security Configuration

**Tools:**
- `unifi_list_firewall_rules(enabled_only=true)` - Firewall rules
- `unifi_get_ips_status()` - IPS configuration
- `unifi_list_port_forwards()` - Port forwarding

### Step 4: Document WiFi Networks

**Tool:** `unifi_list_wlans`

**What to document:**
- SSID names and security settings
- Associated VLANs
- Band steering and client isolation settings

---

## Configuration Backup Workflow

Create a complete configuration backup for disaster recovery.

### Step 1: Export Full Configuration

**Tool:** `unifi_export_configuration(include_credentials=false)`

**What it exports:**
- Network configurations
- Firewall rules
- Port forwards
- Routing rules
- WLAN configurations

**Example prompt:** "Export my network configuration for backup"

### Step 2: Save the Export

Save the JSON output to a file with timestamp:
```
unifi-backup-YYYY-MM-DD.json
```

### Step 3: Verify Export Contents

Check that all sections are present:
- [ ] Networks/VLANs
- [ ] Firewall rules
- [ ] Port forwards
- [ ] WLANs

### Best Practices

- **Frequency:** Weekly backups minimum
- **Storage:** Keep backups in version control or secure storage
- **Retention:** Keep at least 4 weeks of backups
- **Testing:** Periodically verify backup completeness

---

## Automation Recipes

### Recipe 1: Daily Health Check

**Purpose:** Quick daily network health verification

**Steps:**
```
1. unifi_get_system_health
2. unifi_list_devices (check for offline)
3. unifi_get_alerts(limit=20)
```

**Expected output:** All systems healthy, no offline devices, no critical alerts.

### Recipe 2: Security Audit

**Purpose:** Comprehensive security review

**Steps:**
```
1. unifi_get_ips_status(include_alerts=true)
2. unifi_list_firewall_rules(enabled_only=true)
3. unifi_list_port_forwards
4. unifi_get_alerts(limit=100)
```

**Review for:** IPS enabled, no overly permissive rules, minimal port forwards.

### Recipe 3: Bandwidth Investigation

**Purpose:** Find bandwidth hogs

**Steps:**
```
1. unifi_get_network_stats
2. unifi_get_top_clients(limit=10)
3. unifi_get_dpi_stats
```

**Identify:** Top consumers, application breakdown, unusual patterns.

### Recipe 4: New Device Onboarding

**Purpose:** Verify new device is properly configured

**Steps:**
```
1. unifi_list_clients (find new device)
2. unifi_get_client_details(mac_address="...")
3. unifi_verify_vlan_connectivity (if on specific VLAN)
```

**Verify:** Correct VLAN, IP assignment, connectivity.

### Recipe 5: Troubleshoot Connectivity

**Purpose:** Diagnose why device can't reach destination

**Steps:**
```
1. unifi_list_clients (find source device)
2. unifi_verify_vlan_connectivity(source_vlan="X", destination_vlan="Y")
3. unifi_list_firewall_rules (find blocking rule)
```

**Identify:** VLAN assignment, blocking rules, routing issues.

---

## Next Steps

- **Security concerns?** Load `security.md` for detailed audit
- **Performance issues?** Load `monitoring.md` for health checks
- **VLAN questions?** Load `vlan.md` for design patterns
- **Connection problems?** Load `troubleshooting.md` for diagnostics
