# Write Operations Safety Framework - Developer Guide

## Overview

The write operation safety framework provides multiple layers of protection for tools that modify network configuration. This guide explains how to create write operation tools and how the safety mechanisms work.

## Quick Start

### Creating a Write Operation Tool

```python
from unifi_mcp.tools.base import BaseTool
from unifi_mcp.unifi_client import UniFiClient
from typing import Any, Dict

class ToggleFirewallRuleTool(BaseTool):
    """Toggle a firewall rule on/off."""
    
    name = "unifi_toggle_firewall_rule"
    description = "Enable or disable a firewall rule"
    
    # IMPORTANT: Set requires_confirmation = True for write operations
    requires_confirmation = True
    category = "write_operations"
    
    input_schema = {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "Firewall rule ID"
            },
            "enabled": {
                "type": "boolean",
                "description": "Enable (true) or disable (false) the rule"
            },
            "confirm": {
                "type": "boolean",
                "description": "Confirm the write operation (required)"
            }
        },
        "required": ["rule_id", "enabled"]
    }
    
    async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
        """Execute the write operation."""
        rule_id = kwargs["rule_id"]
        enabled = kwargs["enabled"]
        
        # Perform the write operation
        result = await unifi_client.put(
            f"/api/s/default/rest/firewallrule/{rule_id}",
            {"enabled": enabled}
        )
        
        # Return success with details
        return self.format_success(
            {
                "rule_id": rule_id,
                "enabled": enabled,
                "previous_state": result.get("previous_state")
            },
            message=f"Firewall rule {'enabled' if enabled else 'disabled'} successfully"
        )
```

### Key Requirements for Write Operation Tools

1. **Set `requires_confirmation = True`**
   - This enables all safety mechanisms
   - Automatic confirmation validation
   - Comprehensive logging
   - Configuration-based filtering

2. **Set `category = "write_operations"`**
   - Groups write tools together
   - Enables configuration-based filtering
   - Improves organization

3. **Include `confirm` parameter in schema**
   - Not required in schema (framework handles it)
   - But good practice to document it
   - Helps AI agents understand the requirement

4. **Provide detailed success responses**
   - Include what changed
   - Include previous state (for rollback)
   - Include confirmation message

## Safety Mechanisms

### 1. Confirmation Requirement

**How it works**:
- Tools with `requires_confirmation = True` require `confirm: true` in arguments
- Framework automatically validates confirmation before execution
- Missing or false confirmation returns clear error

**Example**:
```python
# ❌ This will fail
await tool.invoke(client, {"rule_id": "abc123", "enabled": False})
# Returns: {"error": {"code": "CONFIRMATION_REQUIRED", ...}}

# ✅ This will succeed
await tool.invoke(client, {"rule_id": "abc123", "enabled": False, "confirm": True})
# Executes the operation
```

### 2. Configuration-Based Filtering

**How it works**:
- Write operations controlled by `write_operations.enabled` in config
- When disabled, write tools are filtered from tool list
- Attempting to invoke disabled write tool raises clear error

**Configuration** (`config.yaml`):
```yaml
tools:
  write_operations:
    enabled: false  # Disabled by default
    require_confirmation: true
    tools:
      - toggle_firewall_rule
      - create_firewall_rule
      - update_firewall_rule
```

**Behavior**:
```python
# When write_operations.enabled = False
tools = registry.get_tool_list()
# Write tools NOT included

# Attempting to invoke raises error
await registry.invoke("unifi_toggle_firewall_rule", client, {...})
# Raises: ValueError("Write operation tool ... is disabled. Set 'write_operations.enabled: true' ...")
```

### 3. Comprehensive Logging

**How it works**:
- All write operations automatically logged with WARNING level
- Logs include operation details, arguments, and outcomes
- Sensitive data automatically redacted
- Provides complete audit trail

**Log Levels**:
- **WARNING**: Write operation initiation and completion
- **ERROR**: Write operation failures
- **WARNING**: Blocked operations (no confirmation)

**Example Logs**:
```
2025-10-09 14:30:15 [WARNING] [abc-123] unifi_mcp.tools.base: WRITE OPERATION INITIATED: unifi_toggle_firewall_rule
2025-10-09 14:30:16 [WARNING] [abc-123] unifi_mcp.tools.base: WRITE OPERATION COMPLETED: unifi_toggle_firewall_rule
```

**Log Details**:
```python
{
    "tool_name": "unifi_toggle_firewall_rule",
    "category": "write_operations",
    "operation_type": "write",
    "confirmed": True,
    "arguments": {
        "rule_id": "abc123",
        "enabled": False,
        "password": "[REDACTED]"  # Sensitive data redacted
    }
}
```

### 4. Error Handling

**How it works**:
- Write operation errors include rollback information
- Clear error messages explain what went wrong
- Actionable steps guide recovery

**Example Error Response**:
```json
{
  "error": {
    "code": "EXECUTION_ERROR",
    "message": "Tool execution failed: unifi_toggle_firewall_rule",
    "details": "API call failed: Connection timeout",
    "actionable_steps": [
      "Check the UniFi controller is accessible",
      "Verify your credentials are correct",
      "Check the server logs for more details"
    ]
  }
}
```

## Best Practices

### 1. Always Include Previous State

Return the previous state in success responses to enable rollback:

```python
async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
    rule_id = kwargs["rule_id"]
    
    # Get current state before modifying
    current_rule = await unifi_client.get(f"/api/s/default/rest/firewallrule/{rule_id}")
    previous_enabled = current_rule.get("enabled")
    
    # Perform modification
    result = await unifi_client.put(
        f"/api/s/default/rest/firewallrule/{rule_id}",
        {"enabled": kwargs["enabled"]}
    )
    
    # Return with previous state
    return self.format_success(
        {
            "rule_id": rule_id,
            "enabled": kwargs["enabled"],
            "previous_enabled": previous_enabled  # For rollback
        },
        message="Rule updated successfully"
    )
```

### 2. Validate Before Modifying

Validate that the operation is safe before making changes:

```python
async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
    rule_id = kwargs["rule_id"]
    
    # Validate rule exists
    try:
        rule = await unifi_client.get(f"/api/s/default/rest/firewallrule/{rule_id}")
    except Exception:
        raise ToolError(
            code="RULE_NOT_FOUND",
            message=f"Firewall rule '{rule_id}' not found",
            actionable_steps=["Verify the rule ID is correct"]
        )
    
    # Validate operation is safe
    if rule.get("system_rule"):
        raise ToolError(
            code="CANNOT_MODIFY_SYSTEM_RULE",
            message="Cannot modify system firewall rules",
            actionable_steps=["Only user-created rules can be modified"]
        )
    
    # Proceed with modification
    # ...
```

### 3. Provide Detailed Success Messages

Help users understand what changed:

```python
return self.format_success(
    {
        "rule_id": rule_id,
        "rule_name": rule.get("name"),
        "enabled": enabled,
        "previous_enabled": previous_enabled,
        "affected_networks": rule.get("networks", [])
    },
    message=f"Firewall rule '{rule.get('name')}' {'enabled' if enabled else 'disabled'}"
)
```

### 4. Handle Partial Failures

If an operation affects multiple items, handle partial failures gracefully:

```python
async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
    rule_ids = kwargs["rule_ids"]
    
    successes = []
    failures = []
    
    for rule_id in rule_ids:
        try:
            result = await unifi_client.put(
                f"/api/s/default/rest/firewallrule/{rule_id}",
                {"enabled": kwargs["enabled"]}
            )
            successes.append(rule_id)
        except Exception as e:
            failures.append({"rule_id": rule_id, "error": str(e)})
    
    return self.format_success(
        {
            "successes": successes,
            "failures": failures,
            "total": len(rule_ids),
            "success_count": len(successes),
            "failure_count": len(failures)
        },
        message=f"Updated {len(successes)}/{len(rule_ids)} rules"
    )
```

## Testing Write Operation Tools

### Unit Test Template

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock()
    client.put = AsyncMock(return_value={"enabled": True})
    return client

@pytest.mark.asyncio
async def test_write_operation_requires_confirmation(mock_unifi_client):
    """Test that write operation requires confirmation."""
    tool = ToggleFirewallRuleTool()
    
    # Without confirmation - should fail
    result = await tool.invoke(
        mock_unifi_client,
        {"rule_id": "abc123", "enabled": False}
    )
    
    assert "error" in result
    assert result["error"]["code"] == "CONFIRMATION_REQUIRED"

@pytest.mark.asyncio
async def test_write_operation_with_confirmation_succeeds(mock_unifi_client):
    """Test that write operation with confirmation succeeds."""
    tool = ToggleFirewallRuleTool()
    
    # With confirmation - should succeed
    result = await tool.invoke(
        mock_unifi_client,
        {"rule_id": "abc123", "enabled": False, "confirm": True}
    )
    
    assert result["success"] is True
    assert mock_unifi_client.put.called

@pytest.mark.asyncio
async def test_write_operation_handles_errors(mock_unifi_client):
    """Test that write operation handles errors properly."""
    tool = ToggleFirewallRuleTool()
    
    # Make API call fail
    mock_unifi_client.put.side_effect = Exception("API error")
    
    # Should return error response
    result = await tool.invoke(
        mock_unifi_client,
        {"rule_id": "abc123", "enabled": False, "confirm": True}
    )
    
    assert "error" in result
    assert result["error"]["code"] == "EXECUTION_ERROR"
```

## Configuration Examples

### Development (Write Operations Enabled)

```yaml
tools:
  write_operations:
    enabled: true  # Enable for development/testing
    require_confirmation: true
    tools:
      - toggle_firewall_rule
      - create_firewall_rule
      - update_firewall_rule
```

### Production (Write Operations Disabled)

```yaml
tools:
  write_operations:
    enabled: false  # Disabled for safety
    require_confirmation: true
    tools:
      - toggle_firewall_rule
      - create_firewall_rule
      - update_firewall_rule
```

### Selective Enablement

```yaml
tools:
  write_operations:
    enabled: true
    require_confirmation: true
    tools:
      - toggle_firewall_rule  # Only enable specific tools
      # create_firewall_rule - Not enabled
      # update_firewall_rule - Not enabled
```

## Common Patterns

### Pattern 1: Toggle Operation

```python
class ToggleTool(BaseTool):
    requires_confirmation = True
    
    async def execute(self, unifi_client, **kwargs):
        item_id = kwargs["item_id"]
        enabled = kwargs["enabled"]
        
        # Get current state
        current = await unifi_client.get(f"/api/s/default/rest/item/{item_id}")
        
        # Update
        await unifi_client.put(
            f"/api/s/default/rest/item/{item_id}",
            {"enabled": enabled}
        )
        
        return self.format_success({
            "item_id": item_id,
            "enabled": enabled,
            "previous_enabled": current.get("enabled")
        })
```

### Pattern 2: Create Operation

```python
class CreateTool(BaseTool):
    requires_confirmation = True
    
    async def execute(self, unifi_client, **kwargs):
        # Validate doesn't already exist
        existing = await unifi_client.get("/api/s/default/rest/items")
        if any(item["name"] == kwargs["name"] for item in existing):
            raise ToolError(
                code="ALREADY_EXISTS",
                message=f"Item '{kwargs['name']}' already exists"
            )
        
        # Create
        result = await unifi_client.post(
            "/api/s/default/rest/item",
            kwargs
        )
        
        return self.format_success({
            "item_id": result["_id"],
            "name": kwargs["name"]
        }, message="Item created successfully")
```

### Pattern 3: Update Operation

```python
class UpdateTool(BaseTool):
    requires_confirmation = True
    
    async def execute(self, unifi_client, **kwargs):
        item_id = kwargs["item_id"]
        
        # Get current state
        current = await unifi_client.get(f"/api/s/default/rest/item/{item_id}")
        
        # Build update payload (only changed fields)
        updates = {
            k: v for k, v in kwargs.items()
            if k != "item_id" and k != "confirm" and v != current.get(k)
        }
        
        if not updates:
            return self.format_success({
                "item_id": item_id,
                "changed": False
            }, message="No changes needed")
        
        # Update
        await unifi_client.put(
            f"/api/s/default/rest/item/{item_id}",
            updates
        )
        
        return self.format_success({
            "item_id": item_id,
            "changed": True,
            "updates": updates,
            "previous_values": {k: current.get(k) for k in updates.keys()}
        }, message="Item updated successfully")
```

## Troubleshooting

### Issue: Write operation blocked

**Symptom**: Error "Write operation tool ... is disabled"

**Solution**: Enable write operations in config:
```yaml
tools:
  write_operations:
    enabled: true
```

### Issue: Confirmation required error

**Symptom**: Error "Tool ... requires explicit confirmation"

**Solution**: Add `confirm: true` to arguments:
```python
await tool.invoke(client, {..., "confirm": True})
```

### Issue: Write operations not logging

**Symptom**: No write operation logs appearing

**Solution**: Check log level is INFO or DEBUG:
```yaml
server:
  log_level: "INFO"
```

### Issue: Sensitive data in logs

**Symptom**: Passwords or tokens visible in logs

**Solution**: Framework automatically redacts sensitive data. If you see sensitive data:
1. Check field names match redaction patterns (password, token, api_key, etc.)
2. Report as a bug - redaction should be automatic

## Summary

The write operation safety framework provides:
- ✅ Automatic confirmation validation
- ✅ Comprehensive audit logging
- ✅ Configuration-based filtering
- ✅ Clear error messages
- ✅ Sensitive data redaction
- ✅ Fail-safe defaults

Follow the patterns in this guide to create safe, well-tested write operation tools!
