# UniFi Network Troubleshooting Guide

Detailed troubleshooting for connection issues, authentication problems, and common errors.

## When to Use This Guide

- MCP server fails to connect to UniFi controller
- Tools return timeout or connection refused errors
- Authentication failures or empty results
- VLAN connectivity issues

## Prerequisites

- Access to UniFi controller web UI
- Network access to controller IP
- MCP server configuration file (mcp.json)

---

## Connection Error Diagnostic Workflow

### Step 1: Identify the Symptom

**Run a simple test command:**
```
unifi_list_devices
```

**Categorize the error:**

| Error Message | Solution |
|---------------|----------|
| "Connection refused" | Check controller IP and port |
| "Connection timed out" | Verify network connectivity |
| "SSL certificate error" | Set `UNIFI_VERIFY_SSL=false` |
| "401 Unauthorized" | Regenerate API key |
| "Empty results" | Check site name and permissions |
| "Tool not found" | Reconnect MCP server in Kiro |

### Step 2: Verify Network Connectivity

```bash
# Test basic connectivity
ping YOUR_CONTROLLER_IP

# Test HTTPS port
curl -k -I https://YOUR_CONTROLLER_IP
```

### Step 3: Verify SSL Configuration

For self-signed certificates (common in homelabs):
```json
{
  "env": {
    "UNIFI_VERIFY_SSL": "false"
  }
}
```

---

## Authentication Troubleshooting

### Problem: API Key Not Working

**Common issues:**
- Extra whitespace in API key
- API key revoked or expired
- Insufficient permissions

**Resolution:**
1. Log into Dream Machine web UI
2. Go to **Settings** → **System** → **Advanced** → **API**
3. Delete old key, create new with **Full Management** permissions
4. Update mcp.json with new key
5. Restart MCP server

### Permission Levels

| Permission | Devices | Firewall | IPS |
|------------|---------|----------|-----|
| View Only | ✅ | ❌ | ❌ |
| Full Management | ✅ | ✅ | ✅ |

**Recommendation:** Use "Full Management" for comprehensive monitoring.

---

## VLAN Connectivity Troubleshooting

### Using unifi_verify_vlan_connectivity

**Basic usage:**
```
unifi_verify_vlan_connectivity(source_vlan="IoT", destination_vlan="Core")
```

### Common Scenarios

**Scenario: IoT Device Can't Reach Server**
```
unifi_verify_vlan_connectivity(source_vlan="IoT", destination_vlan="Core")
```

**If blocked:** Create specific allow rule for required ports.

**Scenario: Bidirectional Communication Needed**
```
# Check both directions
unifi_verify_vlan_connectivity(source_vlan="Core", destination_vlan="IoT")
unifi_verify_vlan_connectivity(source_vlan="IoT", destination_vlan="Core")
```

---

## Error Codes Reference

| Error | Cause | Solution |
|-------|-------|----------|
| VALIDATION_ERROR | Invalid parameters | Check parameter types |
| API_ERROR | Controller unreachable | Verify connectivity |
| UNAUTHORIZED | Invalid credentials | Regenerate API key |
| DEVICE_NOT_FOUND | Wrong identifier | Use list tool to find ID |

---

## Debug Mode

Enable detailed logging:
```json
{
  "env": {
    "LOG_LEVEL": "DEBUG"
  }
}
```

---

## Next Steps

- **Security concerns?** Load `security.md` for audit workflows
- **Performance issues?** Load `monitoring.md` for health checks
- **VLAN design?** Load `vlan.md` for segmentation guidance
