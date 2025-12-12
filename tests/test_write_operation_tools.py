"""Unit tests for write operation tools.

This module tests the write operation tools including:
- Toggle firewall rule (enable/disable)
- Create firewall rule
- Update firewall rule
- Confirmation requirement enforcement
- Mock UniFi API write calls
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from unifi_mcp.tools.write_operations import (
    ToggleFirewallRuleTool,
    CreateFirewallRuleTool,
    UpdateFirewallRuleTool
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    return client


@pytest.fixture
def sample_firewall_rule():
    """Create a sample firewall rule for testing."""
    return {
        "_id": "test_rule_123",
        "name": "Test Rule",
        "enabled": True,
        "action": "accept",
        "protocol": "tcp",
        "logging": False,
        "src_address": "192.168.1.0/24",
        "dst_address": "10.0.0.0/8",
        "dst_port": "443",
        "ruleset": "WAN_IN",
        "rule_index": 1
    }


@pytest.fixture
def sample_firewall_rules(sample_firewall_rule):
    """Create a list of sample firewall rules."""
    return [
        sample_firewall_rule,
        {
            "_id": "test_rule_456",
            "name": "Another Rule",
            "enabled": False,
            "action": "drop",
            "protocol": "all",
            "logging": True,
            "ruleset": "WAN_IN",
            "rule_index": 2
        }
    ]


class TestToggleFirewallRuleTool:
    """Test the toggle firewall rule tool."""
    
    @pytest.mark.asyncio
    async def test_toggle_rule_enable(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test enabling a disabled firewall rule."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[1]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to enable disabled rule
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_456",
                "enabled": True,
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["rule_id"] == "test_rule_456"
        assert result["data"]["enabled"] is True
        assert result["data"]["changed"] is True
        assert result["data"]["previous_state"] is False
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_toggle_rule_disable(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test disabling an enabled firewall rule."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to disable enabled rule
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": False,
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["rule_id"] == "test_rule_123"
        assert result["data"]["enabled"] is False
        assert result["data"]["changed"] is True
        assert result["data"]["previous_state"] is True
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_toggle_rule_already_in_desired_state(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test toggling a rule that's already in the desired state."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to enable already-enabled rule
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": True,
                "confirm": True
            }
        )
        
        # Verify success but no change
        assert result["success"] is True
        assert result["data"]["rule_id"] == "test_rule_123"
        assert result["data"]["enabled"] is True
        assert result["data"]["changed"] is False
        
        # Verify only GET was called, not PUT
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_toggle_rule_not_found(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test toggling a non-existent rule."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        
        # Execute tool with non-existent rule ID
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "nonexistent_rule",
                "enabled": True,
                "confirm": True
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "RULE_NOT_FOUND"
        assert "nonexistent_rule" in result["error"]["message"]
        
        # Verify only GET was called
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_toggle_rule_without_confirmation(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test that toggle requires confirmation."""
        tool = ToggleFirewallRuleTool()
        
        # Execute tool without confirmation
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": False
            }
        )
        
        # Verify error response (schema validation catches missing required field)
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        # The details field contains the validation error mentioning 'confirm'
        assert "confirm" in result["error"]["details"].lower()
        
        # Verify no API calls were made
        mock_unifi_client.get.assert_not_called()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_toggle_rule_api_error(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test handling of API errors during toggle."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "meta": {"rc": "error", "msg": "Permission denied"}
        }
        
        # Execute tool
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": False,
                "confirm": True
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "UPDATE_FAILED"
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()


class TestCreateFirewallRuleTool:
    """Test the create firewall rule tool."""
    
    @pytest.mark.asyncio
    async def test_create_rule_basic(
        self,
        mock_unifi_client
    ):
        """Test creating a basic firewall rule."""
        tool = CreateFirewallRuleTool()
        
        # Mock API response
        mock_unifi_client.post.return_value = {
            "data": [{
                "_id": "new_rule_789",
                "name": "New Test Rule",
                "action": "drop",
                "protocol": "tcp",
                "enabled": True,
                "logging": False
            }],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool
        result = await tool.invoke(
            mock_unifi_client,
            {
                "name": "New Test Rule",
                "action": "drop",
                "protocol": "tcp",
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["rule_id"] == "new_rule_789"
        assert result["data"]["rule_name"] == "New Test Rule"
        assert result["data"]["action"] == "drop"
        assert result["data"]["protocol"] == "tcp"
        assert result["data"]["enabled"] is True
        
        # Verify API call
        mock_unifi_client.post.assert_called_once()
        call_args = mock_unifi_client.post.call_args
        assert "New Test Rule" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_create_rule_with_addresses_and_ports(
        self,
        mock_unifi_client
    ):
        """Test creating a rule with source/destination addresses and ports."""
        tool = CreateFirewallRuleTool()
        
        # Mock API response
        mock_unifi_client.post.return_value = {
            "data": [{
                "_id": "new_rule_890",
                "name": "Detailed Rule",
                "action": "accept",
                "protocol": "tcp",
                "enabled": True,
                "logging": True,
                "src_address": "192.168.1.0/24",
                "dst_address": "10.0.0.5",
                "dst_port": "443"
            }],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool
        result = await tool.invoke(
            mock_unifi_client,
            {
                "name": "Detailed Rule",
                "action": "accept",
                "protocol": "tcp",
                "enabled": True,
                "logging": True,
                "src_address": "192.168.1.0/24",
                "dst_address": "10.0.0.5",
                "dst_port": "443",
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["src_address"] == "192.168.1.0/24"
        assert result["data"]["dst_address"] == "10.0.0.5"
        assert result["data"]["dst_port"] == "443"
        assert result["data"]["logging"] is True
        
        # Verify API call includes all fields
        call_args = mock_unifi_client.post.call_args
        call_data = call_args[1]["data"]
        assert call_data["src_address"] == "192.168.1.0/24"
        assert call_data["dst_address"] == "10.0.0.5"
        assert call_data["dst_port"] == "443"
    
    @pytest.mark.asyncio
    async def test_create_rule_without_confirmation(
        self,
        mock_unifi_client
    ):
        """Test that create requires confirmation."""
        tool = CreateFirewallRuleTool()
        
        # Execute tool without confirmation
        result = await tool.invoke(
            mock_unifi_client,
            {
                "name": "Test Rule",
                "action": "drop"
            }
        )
        
        # Verify error response (schema validation catches missing required field)
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        # The details field contains the validation error mentioning 'confirm'
        assert "confirm" in result["error"]["details"].lower()
        
        # Verify no API calls were made
        mock_unifi_client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_rule_api_error(
        self,
        mock_unifi_client
    ):
        """Test handling of API errors during creation."""
        tool = CreateFirewallRuleTool()
        
        # Mock API error response
        mock_unifi_client.post.return_value = {
            "meta": {"rc": "error", "msg": "Invalid configuration"}
        }
        
        # Execute tool
        result = await tool.invoke(
            mock_unifi_client,
            {
                "name": "Test Rule",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "CREATE_FAILED"
        
        # Verify API call was made
        mock_unifi_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_rule_defaults(
        self,
        mock_unifi_client
    ):
        """Test that default values are applied correctly."""
        tool = CreateFirewallRuleTool()
        
        # Mock API response
        mock_unifi_client.post.return_value = {
            "data": [{
                "_id": "new_rule_999",
                "name": "Minimal Rule",
                "action": "accept",
                "protocol": "all",
                "enabled": True,
                "logging": False
            }],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool with minimal parameters
        result = await tool.invoke(
            mock_unifi_client,
            {
                "name": "Minimal Rule",
                "action": "accept",
                "confirm": True
            }
        )
        
        # Verify defaults were applied
        assert result["success"] is True
        assert result["data"]["protocol"] == "all"
        assert result["data"]["enabled"] is True
        assert result["data"]["logging"] is False
        assert result["data"]["src_address"] == "any"
        assert result["data"]["dst_address"] == "any"
        assert result["data"]["dst_port"] == "any"


class TestUpdateFirewallRuleTool:
    """Test the update firewall rule tool."""
    
    @pytest.mark.asyncio
    async def test_update_rule_single_field(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test updating a single field of a firewall rule."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to update action
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["rule_id"] == "test_rule_123"
        assert result["data"]["changed"] is True
        assert "action" in result["data"]["changes"]
        assert result["data"]["changes"]["action"]["old"] == "accept"
        assert result["data"]["changes"]["action"]["new"] == "drop"
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_rule_multiple_fields(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test updating multiple fields of a firewall rule."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to update multiple fields
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "name": "Updated Rule Name",
                "action": "reject",
                "logging": True,
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["changed"] is True
        assert len(result["data"]["changes"]) == 3
        assert "name" in result["data"]["changes"]
        assert "action" in result["data"]["changes"]
        assert "logging" in result["data"]["changes"]
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_rule_no_changes(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test updating a rule with no actual changes."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        
        # Execute tool with same values as current
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "action": "accept",  # Same as current
                "protocol": "tcp",   # Same as current
                "confirm": True
            }
        )
        
        # Verify success but no changes
        assert result["success"] is True
        assert result["data"]["changed"] is False
        
        # Verify only GET was called, not PUT
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_rule_not_found(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test updating a non-existent rule."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        
        # Execute tool with non-existent rule ID
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "nonexistent_rule",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "RULE_NOT_FOUND"
        
        # Verify only GET was called
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_rule_without_confirmation(
        self,
        mock_unifi_client
    ):
        """Test that update requires confirmation."""
        tool = UpdateFirewallRuleTool()
        
        # Execute tool without confirmation
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "action": "drop"
            }
        )
        
        # Verify error response (schema validation catches missing required field)
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        # The details field contains the validation error mentioning 'confirm'
        assert "confirm" in result["error"]["details"].lower()
        
        # Verify no API calls were made
        mock_unifi_client.get.assert_not_called()
        mock_unifi_client.put.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_rule_api_error(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test handling of API errors during update."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "meta": {"rc": "error", "msg": "Validation failed"}
        }
        
        # Execute tool
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "UPDATE_FAILED"
        
        # Verify API calls
        mock_unifi_client.get.assert_called_once()
        mock_unifi_client.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_rule_addresses_and_ports(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test updating addresses and ports."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool to update addresses and ports
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "src_address": "172.16.0.0/16",
                "dst_address": "8.8.8.8",
                "dst_port": "53",
                "confirm": True
            }
        )
        
        # Verify success
        assert result["success"] is True
        assert result["data"]["changed"] is True
        assert "src_address" in result["data"]["changes"]
        assert "dst_address" in result["data"]["changes"]
        assert "dst_port" in result["data"]["changes"]


class TestConfirmationRequirement:
    """Test confirmation requirement across all write operation tools."""
    
    @pytest.mark.asyncio
    async def test_all_write_tools_require_confirmation(
        self,
        mock_unifi_client
    ):
        """Test that all write operation tools require confirmation."""
        tools = [
            ToggleFirewallRuleTool(),
            CreateFirewallRuleTool(),
            UpdateFirewallRuleTool()
        ]
        
        for tool in tools:
            # Verify requires_confirmation flag is set
            assert tool.requires_confirmation is True
            
            # Verify category is write_operations
            assert tool.category == "write_operations"
            
            # Verify confirm parameter is in schema
            assert "confirm" in tool.input_schema["properties"]
            assert tool.input_schema["properties"]["confirm"]["type"] == "boolean"
    
    @pytest.mark.asyncio
    async def test_confirmation_false_is_rejected(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test that confirm=False is rejected."""
        tool = ToggleFirewallRuleTool()
        
        # Execute with confirm=False
        result = await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": False,
                "confirm": False
            }
        )
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "CONFIRMATION_REQUIRED"


class TestMockUniFiAPICalls:
    """Test that UniFi API calls are properly mocked."""
    
    @pytest.mark.asyncio
    async def test_toggle_calls_correct_endpoints(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test that toggle calls the correct API endpoints."""
        tool = ToggleFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool
        await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "enabled": False,
                "confirm": True
            }
        )
        
        # Verify GET was called for listing rules
        assert mock_unifi_client.get.called
        get_call = mock_unifi_client.get.call_args[0][0]
        assert "firewallrule" in get_call
        
        # Verify PUT was called for updating rule
        assert mock_unifi_client.put.called
        put_call = mock_unifi_client.put.call_args[0][0]
        assert "firewallrule" in put_call
        assert "test_rule_123" in put_call
    
    @pytest.mark.asyncio
    async def test_create_calls_correct_endpoint(
        self,
        mock_unifi_client
    ):
        """Test that create calls the correct API endpoint."""
        tool = CreateFirewallRuleTool()
        
        # Mock API response
        mock_unifi_client.post.return_value = {
            "data": [{"_id": "new_rule", "name": "Test"}],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool
        await tool.invoke(
            mock_unifi_client,
            {
                "name": "Test Rule",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify POST was called
        assert mock_unifi_client.post.called
        post_call = mock_unifi_client.post.call_args[0][0]
        assert "firewallrule" in post_call
        
        # Verify data was passed
        assert "data" in mock_unifi_client.post.call_args[1]
    
    @pytest.mark.asyncio
    async def test_update_calls_correct_endpoints(
        self,
        mock_unifi_client,
        sample_firewall_rules
    ):
        """Test that update calls the correct API endpoints."""
        tool = UpdateFirewallRuleTool()
        
        # Mock API responses
        mock_unifi_client.get.return_value = {
            "data": sample_firewall_rules,
            "meta": {"rc": "ok"}
        }
        mock_unifi_client.put.return_value = {
            "data": [sample_firewall_rules[0]],
            "meta": {"rc": "ok"}
        }
        
        # Execute tool
        await tool.invoke(
            mock_unifi_client,
            {
                "rule_id": "test_rule_123",
                "action": "drop",
                "confirm": True
            }
        )
        
        # Verify GET was called
        assert mock_unifi_client.get.called
        
        # Verify PUT was called with rule ID
        assert mock_unifi_client.put.called
        put_call = mock_unifi_client.put.call_args[0][0]
        assert "test_rule_123" in put_call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
