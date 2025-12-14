# UniFi VLAN Configuration Guide

Comprehensive guidance for VLAN design, inter-VLAN routing, and network segmentation best practices.

## When to Use This Guide

- Designing a new VLAN architecture
- Implementing IoT device isolation
- Setting up guest network segmentation
- Creating management VLAN for network equipment
- Troubleshooting inter-VLAN connectivity

## Prerequisites

- UniFi Power activated with valid API key
- API key with **Full Management** permissions
- Understanding of your network topology

---

## VLAN Design Patterns

### Pattern 1: IoT Isolation

**Purpose:** Isolate smart home devices from trusted computers and sensitive data.

**VLAN Configuration:**

| VLAN | Name | Subnet | Purpose |
|------|------|--------|---------|
| 10 | Core | 192.168.10.0/24 | Trusted devices, full access |
| 30 | IoT | 192.168.30.0/24 | Smart devices, restricted |
| 20 | Guest | 192.168.20.0/24 | Visitors, internet only |

**Firewall Rules:**
```
1. Allow Core → IoT (management ports only)
2. Deny IoT → Core (all)
3. Deny Guest → Core (all)
4. Allow all → Internet
```

**Tools to verify:**
- `unifi_list_networks()` - View current VLAN configuration
- `unifi_verify_vlan_connectivity(source_vlan="IoT", destination_vlan="Core")` - Verify isolation

### Pattern 2: Guest Network Isolation

**Purpose:** Provide internet access to visitors without exposing internal resources.

**Key Features:**
- Client isolation: Guests cannot see each other
- Bandwidth limiting: Prevent saturation
- Internet only access

**Firewall Rules:**
```
1. Allow Guest → Internet (HTTP, HTTPS, DNS)
2. Deny Guest → Private (all)
3. Enable client isolation on Guest WLAN
```

### Pattern 3: Management VLAN

**Purpose:** Isolate network infrastructure management from user traffic.

**Benefits:**
- Prevents users from accessing switch/AP management
- Reduces attack surface
- Enables network monitoring without user interference

---

## Inter-VLAN Routing Guidance

### Understanding Inter-VLAN Traffic

By default, VLANs are isolated. The gateway routes between VLANs based on firewall rules.

### Common Routing Scenarios

**Scenario 1: Allow specific service access**
```
# Allow IoT devices to reach Home Assistant on Core
Source: IoT VLAN
Destination: Core VLAN
Port: 8123
Action: Allow
```

**Scenario 2: Allow management access**
```
# Allow Core to manage IoT devices
Source: Core VLAN
Destination: IoT VLAN
Ports: 22, 80, 443
Action: Allow
```

**Scenario 3: Block all except specific**
```
# Order matters - specific allows first
1. Allow IoT → NAS (port 445)
2. Allow IoT → Home Assistant (port 8123)
3. Block IoT → Core (all)
```

### Verifying Connectivity

```
# Check if traffic is allowed
unifi_verify_vlan_connectivity(source_vlan="IoT", destination_vlan="Core")

# Check both directions for bidirectional needs
unifi_verify_vlan_connectivity(source_vlan="Core", destination_vlan="IoT")
```

---

## Segmentation Best Practices

### Security Recommendations

1. **Default Deny**: Block all inter-VLAN traffic by default
2. **Explicit Allow**: Only allow required traffic
3. **Least Privilege**: Minimum necessary access
4. **Document Rules**: Clear descriptions for all rules

### VLAN Assignment Guidelines

| Device Type | Recommended VLAN | Reason |
|-------------|------------------|--------|
| Workstations | Core/Trusted | Full network access needed |
| Servers/NAS | Core/Trusted | Accessed by trusted devices |
| Smart TVs | IoT | Limited trust, internet access |
| Cameras | IoT or Dedicated | Isolated, may need NVR access |
| Smart Speakers | IoT | Limited trust |
| Guests | Guest | Internet only |
| Network Equipment | Management | Admin access only |

### Monitoring Your VLANs

```
# List all networks
unifi_list_networks()

# Check specific network details
unifi_get_network_details(network_id="...")

# Review firewall rules
unifi_list_firewall_rules()
```

---

## Next Steps

- **Security audit?** Load `security.md` for firewall review
- **Performance issues?** Load `monitoring.md` for health checks
- **Connectivity problems?** Load `troubleshooting.md` for diagnostics
