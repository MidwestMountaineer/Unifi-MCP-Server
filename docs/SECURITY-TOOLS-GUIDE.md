# Security Tools Guide

Quick reference for using the UniFi MCP security tools.

## Available Tools

### 1. unifi_list_firewall_rules

List all firewall rules with optional filtering.

**Parameters**:
- `enabled_only` (boolean, optional): Show only enabled rules (default: false)
- `page` (integer, optional): Page number for pagination (default: 1)
- `page_size` (integer, optional): Number of rules per page (default: 50, max: 500)

**Example Prompts**:
- "List all firewall rules"
- "Show me enabled firewall rules"
- "What firewall rules are disabled?"
- "Show me the first 10 firewall rules"

**Example Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "rule1",
      "rule_index": 2000,
      "name": "Allow LAN to WAN",
      "enabled": true,
      "action": "ACCEPT",
      "protocol": "ALL",
      "source_zone": "LAN",
      "destination_zone": "WAN",
      "source_address": "group:LAN",
      "destination_address": "group:WAN",
      "destination_port": "any",
      "logging": false
    }
  ],
  "count": 5,
  "total": 5,
  "page": 1,
  "page_size": 50
}
```

### 2. unifi_get_firewall_rule_details

Get detailed information about a specific firewall rule.

**Parameters**:
- `rule_id` (string, required): Firewall rule ID

**Example Prompts**:
- "Show me details for firewall rule abc123"
- "What's the configuration of the IoT blocking rule?"
- "Get full information for rule 2001"

**Example Response**:
```json
{
  "success": true,
  "data": {
    "id": "rule2",
    "rule_index": 2001,
    "name": "Block IoT to Core",
    "enabled": true,
    "action": "DROP",
    "logging": true,
    "protocol": {
      "type": "all",
      "display": "ALL"
    },
    "source": {
      "address": "192.168.30.0/24",
      "network_id": "iot_network",
      "firewall_groups": [],
      "address_display": "192.168.30.0/24"
    },
    "destination": {
      "address": "192.168.10.0/24",
      "network_id": "core_network",
      "firewall_groups": [],
      "address_display": "192.168.10.0/24"
    },
    "state_new": true,
    "state_established": false
  },
  "type": "firewall_rule"
}
```

## Common Use Cases

### Security Analysis

**Scenario**: Analyze firewall configuration

```
Prompt: "List all firewall rules and tell me which ones are blocking traffic"

The AI will:
1. Call unifi_list_firewall_rules
2. Analyze rules with action="DROP" or action="REJECT"
3. Provide summary of blocking rules
```

### Troubleshooting

**Scenario**: Debug connectivity issue

```
Prompt: "Why can't my IoT device at 192.168.30.50 reach 192.168.10.1?"

The AI will:
1. Call unifi_list_firewall_rules
2. Look for rules affecting 192.168.30.0/24 → 192.168.10.0/24
3. Identify blocking rules
4. Explain the issue
```

### Documentation

**Scenario**: Document security posture

```
Prompt: "Create a summary of all firewall rules that affect the IoT VLAN"

The AI will:
1. Call unifi_list_firewall_rules
2. Filter rules with IoT addresses
3. Get details for relevant rules
4. Generate documentation
```

### Migration Planning

**Scenario**: Plan network migration

```
Prompt: "What firewall rules will need to change when I move from 192.168.30.0/24 to 192.168.35.0/24?"

The AI will:
1. Call unifi_list_firewall_rules
2. Identify rules with 192.168.30.0/24
3. Get details for each rule
4. Provide migration checklist
```

## Field Reference

### Rule Actions

- **ACCEPT**: Allow traffic
- **DROP**: Silently drop traffic (no response)
- **REJECT**: Drop traffic and send rejection response

### Protocol Types

- **ALL**: All protocols
- **TCP**: TCP only
- **UDP**: UDP only
- **TCP/UDP**: Both TCP and UDP
- **ICMP**: ICMP only

### Address Formats

- **IP Address**: `192.168.10.50`
- **CIDR**: `192.168.30.0/24`
- **Network Reference**: `network:iot_network`
- **Firewall Group**: `group:LAN`
- **Any**: `any`

### State Tracking

- **state_new**: Match new connections
- **state_established**: Match established connections
- **state_related**: Match related connections
- **state_invalid**: Match invalid connections

## Tips for AI Agents

1. **Start with List**: Always list rules first to get IDs
2. **Use Filtering**: Use `enabled_only=true` to focus on active rules
3. **Pagination**: Use pagination for large rule sets
4. **Get Details**: Use rule ID from list to get full details
5. **Check Logging**: Rules with `logging=true` generate logs

## Error Handling

### Rule Not Found
```json
{
  "error": {
    "code": "RULE_NOT_FOUND",
    "message": "Firewall rule not found: abc123",
    "actionable_steps": [
      "Verify the rule ID is correct",
      "Use unifi_list_firewall_rules to see available rules"
    ]
  }
}
```

### Validation Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input for tool 'unifi_list_firewall_rules'",
    "details": "Validation error at 'enabled_only': 'yes' is not of type 'boolean'"
  }
}
```

## Integration with Other Tools

### Combine with Network Discovery

```
Prompt: "Show me firewall rules that affect devices on the IoT network"

The AI will:
1. Call unifi_list_networks to find IoT network details
2. Call unifi_list_firewall_rules
3. Filter rules by IoT network addresses
4. Present results
```

### Combine with Statistics

```
Prompt: "Which firewall rules are most active?"

The AI will:
1. Call unifi_list_firewall_rules with logging=true
2. Call unifi_get_alerts to see rule hits
3. Correlate data
4. Present most active rules
```

## Performance Notes

- **Caching**: Rules are cached for 60 seconds
- **Pagination**: Use pagination for >50 rules
- **Filtering**: Server-side filtering is efficient
- **Response Time**: Typically <2 seconds

## Security Notes

- **Read-Only**: These tools cannot modify firewall rules
- **No Credentials**: Never exposes sensitive data
- **Audit Logging**: All operations are logged
- **Safe for AI**: No risk of accidental changes

---

**Next**: See [ROUTING-TOOLS-GUIDE.md](ROUTING-TOOLS-GUIDE.md) for routing and port forward tools (Task 15)
