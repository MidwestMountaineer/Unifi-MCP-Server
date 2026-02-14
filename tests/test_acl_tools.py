"""Unit tests for ACL rule tools.

Tests cover:
- ListACLRulesTool: ACL rule listing with v1 API
- GetACLRuleTool: ACL rule detail retrieval with 404 handling
- GetACLRuleOrderingTool: ACL rule ordering retrieval
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.acl import (
    ListACLRulesTool,
    GetACLRuleTool,
    GetACLRuleOrderingTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient, UniFiClientError


# Mock ACL rule data (simulating v1 API responses)

MOCK_ACL_RULES = [
    {
        "id": "acl11111-1111-1111-1111-111111111111",
        "type": "IPV4",
        "enabled": True,
        "name": "Block IoT to Core",
        "description": "Prevent IoT devices from reaching core network",
        "action": "BLOCK",
        "enforcingDeviceFilter": {"type": "ALL_SWITCHES"},
        "index": 0,
        "sourceFilter": {"networkId": "iot-network-uuid"},
        "destinationFilter": {"networkId": "core-network-uuid"},
        "protocolFilter": ["TCP", "UDP"],
        "metadata": {"origin": "USER_DEFINED"},
    },
    {
        "id": "acl22222-2222-2222-2222-222222222222",
        "type": "MAC",
        "enabled": False,
        "name": "Allow Printer Access",
        "description": "Allow specific MAC to access printer VLAN",
        "action": "ALLOW",
        "enforcingDeviceFilter": {"type": "SPECIFIC", "deviceIds": ["switch-uuid-1"]},
        "index": 1,
        "sourceFilter": {"macAddress": "AA:BB:CC:DD:EE:FF"},
        "destinationFilter": None,
        "protocolFilter": [],
        "metadata": {"origin": "USER_DEFINED"},
    },
]

MOCK_ACL_ORDERING = {
    "orderedAclRuleIds": [
        "acl11111-1111-1111-1111-111111111111",
        "acl22222-2222-2222-2222-222222222222",
    ],
}


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get_v1 = AsyncMock()
    return client


class TestListACLRulesTool:
    """Test ListACLRulesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_rules(self, mock_unifi_client):
        """Test listing all ACL rules."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_ACL_RULES,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListACLRulesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("acl-rules", params=None)

    @pytest.mark.asyncio
    async def test_rule_summary_formatting(self, mock_unifi_client):
        """Test that rule summaries contain required fields: name, type, enabled, action, index."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_ACL_RULES,
            "totalCount": 2,
        }

        tool = ListACLRulesTool()
        result = await tool.execute(mock_unifi_client)

        rules = result["data"]
        assert len(rules) == 2

        # Check IPv4 rule
        ipv4_rule = rules[0]
        assert ipv4_rule["id"] == "acl11111-1111-1111-1111-111111111111"
        assert ipv4_rule["name"] == "Block IoT to Core"
        assert ipv4_rule["type"] == "IPV4"
        assert ipv4_rule["enabled"] is True
        assert ipv4_rule["action"] == "BLOCK"
        assert ipv4_rule["index"] == 0

        # Check MAC rule
        mac_rule = rules[1]
        assert mac_rule["name"] == "Allow Printer Access"
        assert mac_rule["type"] == "MAC"
        assert mac_rule["enabled"] is False
        assert mac_rule["action"] == "ALLOW"
        assert mac_rule["index"] == 1

    @pytest.mark.asyncio
    async def test_empty_rule_list(self, mock_unifi_client):
        """Test handling of empty ACL rule list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListACLRulesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListACLRulesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_rule_with_missing_fields(self, mock_unifi_client):
        """Test formatting when rule has missing optional fields."""
        sparse_rule = {
            "id": "sparse-id",
            "name": "Sparse Rule",
        }
        mock_unifi_client.get_v1.return_value = {
            "data": [sparse_rule],
            "totalCount": 1,
        }

        tool = ListACLRulesTool()
        result = await tool.execute(mock_unifi_client)

        rule = result["data"][0]
        assert rule["id"] == "sparse-id"
        assert rule["name"] == "Sparse Rule"
        assert rule["type"] == "UNKNOWN"
        assert rule["enabled"] is False
        assert rule["action"] == "UNKNOWN"
        assert rule["index"] == 0


class TestGetACLRuleTool:
    """Test GetACLRuleTool functionality."""

    @pytest.mark.asyncio
    async def test_get_rule_details(self, mock_unifi_client):
        """Test retrieving a specific ACL rule's details."""
        rule_id = "acl11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = MOCK_ACL_RULES[0]

        tool = GetACLRuleTool()
        result = await tool.execute(mock_unifi_client, rule_id=rule_id)

        assert result["success"] is True
        assert result["type"] == "acl_rule"
        data = result["data"]
        assert data["id"] == rule_id
        assert data["name"] == "Block IoT to Core"
        assert data["type"] == "IPV4"
        assert data["enabled"] is True
        assert data["action"] == "BLOCK"
        assert data["index"] == 0
        assert data["enforcingDeviceFilter"] == {"type": "ALL_SWITCHES"}
        assert data["sourceFilter"] == {"networkId": "iot-network-uuid"}
        assert data["destinationFilter"] == {"networkId": "core-network-uuid"}
        assert data["protocolFilter"] == ["TCP", "UDP"]
        assert data["metadata"] == {"origin": "USER_DEFINED"}

        mock_unifi_client.get_v1.assert_called_once_with(f"acl-rules/{rule_id}")

    @pytest.mark.asyncio
    async def test_get_rule_with_data_wrapper(self, mock_unifi_client):
        """Test handling when v1 response wraps single item in data array."""
        rule_id = "acl11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_ACL_RULES[0]],
        }

        tool = GetACLRuleTool()
        result = await tool.execute(mock_unifi_client, rule_id=rule_id)

        assert result["success"] is True
        assert result["data"]["name"] == "Block IoT to Core"

    @pytest.mark.asyncio
    async def test_get_rule_with_null_filters(self, mock_unifi_client):
        """Test that null source/destination filters are preserved."""
        rule_id = "acl22222-2222-2222-2222-222222222222"
        mock_unifi_client.get_v1.return_value = MOCK_ACL_RULES[1]

        tool = GetACLRuleTool()
        result = await tool.execute(mock_unifi_client, rule_id=rule_id)

        data = result["data"]
        assert data["destinationFilter"] is None
        assert data["protocolFilter"] == []

    @pytest.mark.asyncio
    async def test_rule_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        rule_id = "nonexistent-rule-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: acl-rules/{rule_id}"
        )

        tool = GetACLRuleTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id=rule_id)

        assert exc_info.value.code == "ACL_RULE_NOT_FOUND"
        assert rule_id in exc_info.value.message
        assert "unifi_list_acl_rules" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_rule_not_found_empty_data(self, mock_unifi_client):
        """Test handling when API returns empty data list for a rule."""
        rule_id = "nonexistent-rule-id"
        mock_unifi_client.get_v1.return_value = {"data": []}

        tool = GetACLRuleTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id=rule_id)

        assert exc_info.value.code == "ACL_RULE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetACLRuleTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetACLRuleTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestGetACLRuleOrderingTool:
    """Test GetACLRuleOrderingTool functionality."""

    @pytest.mark.asyncio
    async def test_get_ordering(self, mock_unifi_client):
        """Test retrieving ACL rule ordering."""
        mock_unifi_client.get_v1.return_value = MOCK_ACL_ORDERING

        tool = GetACLRuleOrderingTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["type"] == "acl_rule_ordering"
        data = result["data"]
        assert data["orderedAclRuleIds"] == [
            "acl11111-1111-1111-1111-111111111111",
            "acl22222-2222-2222-2222-222222222222",
        ]

        mock_unifi_client.get_v1.assert_called_once_with("acl-rules/ordering")

    @pytest.mark.asyncio
    async def test_empty_ordering(self, mock_unifi_client):
        """Test handling of empty ordering response."""
        mock_unifi_client.get_v1.return_value = {
            "orderedAclRuleIds": [],
        }

        tool = GetACLRuleOrderingTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        data = result["data"]
        assert data["orderedAclRuleIds"] == []

    @pytest.mark.asyncio
    async def test_ordering_missing_fields(self, mock_unifi_client):
        """Test handling when ordering response has missing fields."""
        mock_unifi_client.get_v1.return_value = {}

        tool = GetACLRuleOrderingTool()
        result = await tool.execute(mock_unifi_client)

        data = result["data"]
        assert data["orderedAclRuleIds"] == []

    @pytest.mark.asyncio
    async def test_client_error(self, mock_unifi_client):
        """Test UniFiClientError handling."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetACLRuleOrderingTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetACLRuleOrderingTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"


class TestACLToolMetadata:
    """Test ACL tool metadata and schema definitions."""

    def test_list_tool_name(self):
        tool = ListACLRulesTool()
        assert tool.name == "unifi_list_acl_rules"

    def test_list_tool_category(self):
        tool = ListACLRulesTool()
        assert tool.category == "acl"

    def test_get_tool_name(self):
        tool = GetACLRuleTool()
        assert tool.name == "unifi_get_acl_rule"

    def test_get_tool_requires_rule_id(self):
        tool = GetACLRuleTool()
        assert "rule_id" in tool.input_schema["properties"]
        assert "rule_id" in tool.input_schema["required"]

    def test_ordering_tool_name(self):
        tool = GetACLRuleOrderingTool()
        assert tool.name == "unifi_get_acl_rule_ordering"

    def test_ordering_tool_no_required_params(self):
        """Ordering tool takes no input params (unlike firewall ordering)."""
        tool = GetACLRuleOrderingTool()
        assert tool.input_schema["properties"] == {}
