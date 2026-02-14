"""Unit tests for DNS policy tools.

Tests cover:
- ListDNSPoliciesTool: DNS policy listing with v1 API
- GetDNSPolicyTool: DNS policy detail retrieval with 404 handling
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.dns import (
    ListDNSPoliciesTool,
    GetDNSPolicyTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient, UniFiClientError


# Mock DNS policy data (simulating v1 API responses)

MOCK_DNS_POLICIES = [
    {
        "id": "dns11111-1111-1111-1111-111111111111",
        "name": "Block Malware Domains",
        "enabled": True,
        "description": "Block known malware and phishing domains",
        "metadata": {"origin": "USER_DEFINED"},
    },
    {
        "id": "dns22222-2222-2222-2222-222222222222",
        "name": "Kids Safe Browsing",
        "enabled": False,
        "description": "Filter adult content for kids network",
        "metadata": {"origin": "USER_DEFINED"},
    },
]


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get_v1 = AsyncMock()
    return client


class TestListDNSPoliciesTool:
    """Test ListDNSPoliciesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_policies(self, mock_unifi_client):
        """Test listing all DNS policies."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_DNS_POLICIES,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListDNSPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("dns/policies", params=None)

    @pytest.mark.asyncio
    async def test_policy_summary_formatting(self, mock_unifi_client):
        """Test that policy summaries contain required fields: id, name, enabled."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_DNS_POLICIES,
            "totalCount": 2,
        }

        tool = ListDNSPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        policies = result["data"]
        assert len(policies) == 2

        # Check first policy
        policy1 = policies[0]
        assert policy1["id"] == "dns11111-1111-1111-1111-111111111111"
        assert policy1["name"] == "Block Malware Domains"
        assert policy1["enabled"] is True

        # Check second policy
        policy2 = policies[1]
        assert policy2["id"] == "dns22222-2222-2222-2222-222222222222"
        assert policy2["name"] == "Kids Safe Browsing"
        assert policy2["enabled"] is False

    @pytest.mark.asyncio
    async def test_empty_policy_list(self, mock_unifi_client):
        """Test handling of empty DNS policy list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListDNSPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListDNSPoliciesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_policy_with_missing_fields(self, mock_unifi_client):
        """Test formatting when policy has missing optional fields."""
        sparse_policy = {
            "id": "sparse-id",
            "name": "Sparse Policy",
        }
        mock_unifi_client.get_v1.return_value = {
            "data": [sparse_policy],
            "totalCount": 1,
        }

        tool = ListDNSPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        policy = result["data"][0]
        assert policy["id"] == "sparse-id"
        assert policy["name"] == "Sparse Policy"
        assert policy["enabled"] is False


class TestGetDNSPolicyTool:
    """Test GetDNSPolicyTool functionality."""

    @pytest.mark.asyncio
    async def test_get_policy_details(self, mock_unifi_client):
        """Test retrieving a specific DNS policy's details."""
        policy_id = "dns11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = MOCK_DNS_POLICIES[0]

        tool = GetDNSPolicyTool()
        result = await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert result["success"] is True
        assert result["type"] == "dns_policy"
        data = result["data"]
        assert data["id"] == policy_id
        assert data["name"] == "Block Malware Domains"
        assert data["enabled"] is True
        assert data["description"] == "Block known malware and phishing domains"
        assert data["metadata"] == {"origin": "USER_DEFINED"}

        mock_unifi_client.get_v1.assert_called_once_with(f"dns/policies/{policy_id}")

    @pytest.mark.asyncio
    async def test_get_policy_with_data_wrapper(self, mock_unifi_client):
        """Test handling when v1 response wraps single item in data array."""
        policy_id = "dns11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_DNS_POLICIES[0]],
        }

        tool = GetDNSPolicyTool()
        result = await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert result["success"] is True
        assert result["data"]["name"] == "Block Malware Domains"

    @pytest.mark.asyncio
    async def test_policy_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        policy_id = "nonexistent-policy-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: dns/policies/{policy_id}"
        )

        tool = GetDNSPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert exc_info.value.code == "DNS_POLICY_NOT_FOUND"
        assert policy_id in exc_info.value.message
        assert "unifi_list_dns_policies" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_policy_not_found_empty_data(self, mock_unifi_client):
        """Test handling when API returns empty data list for a policy."""
        policy_id = "nonexistent-policy-id"
        mock_unifi_client.get_v1.return_value = {"data": []}

        tool = GetDNSPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert exc_info.value.code == "DNS_POLICY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetDNSPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetDNSPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestDNSToolMetadata:
    """Test DNS tool metadata and schema definitions."""

    def test_list_tool_name(self):
        tool = ListDNSPoliciesTool()
        assert tool.name == "unifi_list_dns_policies"

    def test_list_tool_category(self):
        tool = ListDNSPoliciesTool()
        assert tool.category == "dns"

    def test_get_tool_name(self):
        tool = GetDNSPolicyTool()
        assert tool.name == "unifi_get_dns_policy"

    def test_get_tool_category(self):
        tool = GetDNSPolicyTool()
        assert tool.category == "dns"

    def test_get_tool_requires_policy_id(self):
        tool = GetDNSPolicyTool()
        assert "policy_id" in tool.input_schema["properties"]
        assert "policy_id" in tool.input_schema["required"]
