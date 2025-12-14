# UniFi Network Security Guide

Comprehensive security workflows for firewall auditing, IPS management, and network security best practices.

## When to Use This Guide

- Performing security audits of your network
- Reviewing and analyzing firewall rules
- Checking IPS (Intrusion Prevention System) status and alerts
- Auditing port forwarding rules for security risks
- Implementing network security best practices
- Investigating security incidents

## Prerequisites

- UniFi Power activated with valid API key
- API key with **Full Management** permissions (required for security endpoints)
- Access to UniFi controller (Dream Machine or traditional)

---

## Complete Security Audit Workflow

A comprehensive multi-step security assessment covering IPS, firewall rules, port forwards, and alerts.

### Step 1: Check IPS Status and Threats

**Tool:** `unifi_get_ips_status(include_alerts=true)`

**What it provides:**
- IPS enabled/disabled status
- Protection mode (IDS vs IPS)
- Threat categories enabled
- Recent threat detections

**Example prompt:** "Check my intrusion prevention status and recent threats"

### Step 2: Review Firewall Rules

**Tool:** `unifi_list_firewall_rules(enabled_only=true)`

**What it provides:**
- All active firewall policies
- Rule order (priority)
- Source/destination networks
- Action (allow/deny/reject)

**Example prompt:** "Show me all enabled firewall rules"

### Step 3: Audit Port Forwards

**Tool:** `unifi_list_port_forwards(enabled_only=true)`

**What it provides:**
- All port forwarding rules
- External ports exposed
- Internal destinations
- Source restrictions (if any)

**Example prompt:** "List all port forwarding rules"

**High-risk ports to flag:**
- **22 (SSH):** Brute force target - use VPN instead
- **3389 (RDP):** Ransomware vector - never expose directly
- **445 (SMB):** Worm propagation - block from internet

### Step 4: Review Recent Security Alerts

**Tool:** `unifi_get_alerts(limit=100)`

**Filter for security-relevant alerts:**
- `EVT_IPS_Alert` - Intrusion prevention triggered
- `EVT_AD_Login` - Admin login events
- `EVT_AD_LoginFailed` - Failed login attempts

---

## Security Best Practices Checklist

### Network Segmentation
- [ ] IoT devices on separate VLAN from trusted devices
- [ ] Guest network isolated with internet-only access
- [ ] Management VLAN restricted to admin devices
- [ ] Inter-VLAN traffic explicitly controlled

### Firewall Configuration
- [ ] Default deny rule at end of each chain
- [ ] No "allow all" rules between VLANs
- [ ] Egress filtering for IoT devices
- [ ] Rules documented with clear descriptions

### IPS Configuration
- [ ] IPS enabled (not just IDS)
- [ ] All threat categories enabled
- [ ] Signature updates automatic
- [ ] Alert notifications configured

### Port Forwarding
- [ ] Minimal port forwards (prefer VPN)
- [ ] No direct SSH/RDP exposure
- [ ] Source IP restrictions where possible
- [ ] Regular audit of active forwards

---

## Firewall Rule Analysis Guidance

### Understanding Rule Structure

**Tool:** `unifi_get_firewall_rule_details(rule_id="...")`

**Rule components:**
| Field | Description |
|-------|-------------|
| `name` | Rule description |
| `action` | allow/deny/reject |
| `protocol` | TCP/UDP/ICMP/all |
| `src_address` | Source network/IP |
| `dst_address` | Destination network/IP |
| `index` | Rule order/priority |

### Common Firewall Patterns

**Pattern 1: IoT Isolation**
```
1. Allow IoT → Internet (DNS, NTP, HTTPS)
2. Allow Core → IoT (management ports)
3. Deny IoT → Core (all)
4. Deny IoT → Management (all)
```

**Pattern 2: Guest Network**
```
1. Allow Guest → Internet (HTTP, HTTPS, DNS)
2. Deny Guest → LAN (all)
3. Deny Guest → Guest (client isolation)
```

---

## IPS Review Section

### Understanding IPS vs IDS

| Mode | Behavior | Use Case |
|------|----------|----------|
| **IDS** | Alerts only, no blocking | Testing |
| **IPS** | Actively blocks threats | Production |

**Recommendation:** Always use IPS mode for internet-facing networks.

### Threat Categories

| Category | Description | Recommendation |
|----------|-------------|----------------|
| **Malware** | Viruses, trojans, ransomware | Always enable |
| **Exploits** | Vulnerability exploitation | Always enable |
| **Botnet** | Command & control traffic | Always enable |
| **Scan** | Port scanning | Enable (may be noisy) |
| **DoS** | Denial of service attacks | Enable for WAN |

### Common Threat Patterns

**Pattern: Malware Communication**
- Outbound traffic to known bad IPs
- C2 (command & control) signatures
- Internal device as source
- **Response:** Isolate source device immediately

**Pattern: Brute Force**
- Repeated alerts for same service (SSH, RDP)
- Same destination port
- **Response:** Ensure service not exposed

---

## Next Steps

- **Performance issues?** Load `monitoring.md` for health checks
- **Connectivity problems?** Load `troubleshooting.md` for diagnostics
- **VLAN design questions?** Load `vlan.md` for segmentation guidance
