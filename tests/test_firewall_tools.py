"""Unit tests for firewall zone tools.

Tests cover:
- ListFirewallZonesTool: zone listing with v1 API
- GetFirewallZoneTool: zone detail retrieval with 404 handling
- Data formatting for AI consumption
- Origin mapping (SYSTEM_DEFINED → system-defined, USER_DEFINED → user-defined)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.firewall import (
    ListFirewallZonesTool,
    GetFirewallZoneTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient, UniFiClientError


# Mock zone data (simulating v1 API responses)

MOCK_ZONES = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "Internal",
        "networkIds": [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ],
        "metadata": {"origin": "SYSTEM_DEFINED"},
    },
    {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "External",
        "networkIds": [],
        "metadata": {"origin": "SYSTEM_DEFINED"},
    },
    {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "name": "Gateway",
        "networkIds": [],
        "metadata": {"origin": "SYSTEM_DEFINED"},
    },
    {
        "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "name": "My Custom Zone",
        "networkIds": ["33333333-3333-3333-3333-333333333333"],
        "metadata": {"origin": "USER_DEFINED"},
    },
]


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get_v1 = AsyncMock()
    return client


class TestListFirewallZonesTool:
    """Test ListFirewallZonesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_zones(self, mock_unifi_client):
        """Test listing all firewall zones."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_ZONES,
            "offset": 0,
            "limit": 25,
            "count": 4,
            "totalCount": 4,
        }

        tool = ListFirewallZonesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 4
        assert result["total"] == 4

        mock_unifi_client.get_v1.assert_called_once_with("firewall/zones", params=None)

    @pytest.mark.asyncio
    async def test_zone_summary_formatting(self, mock_unifi_client):
        """Test that zone summaries contain required fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_ZONES,
            "totalCount": 4,
        }

        tool = ListFirewallZonesTool()
        result = await tool.execute(mock_unifi_client)

        zones = result["data"]
        assert len(zones) == 4

        # Check system-defined zone
        internal = zones[0]
        assert internal["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert internal["name"] == "Internal"
        assert len(internal["networkIds"]) == 2
        assert internal["origin"] == "system-defined"

        # Check user-defined zone
        custom = zones[3]
        assert custom["name"] == "My Custom Zone"
        assert custom["origin"] == "user-defined"

    @pytest.mark.asyncio
    async def test_empty_zone_list(self, mock_unifi_client):
        """Test handling of empty zone list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListFirewallZonesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListFirewallZonesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in str(exc_info.value.details)


class TestGetFirewallZoneTool:
    """Test GetFirewallZoneTool functionality."""

    @pytest.mark.asyncio
    async def test_get_zone_details(self, mock_unifi_client):
        """Test retrieving a specific zone's details."""
        zone_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_unifi_client.get_v1.return_value = MOCK_ZONES[0]

        tool = GetFirewallZoneTool()
        result = await tool.execute(mock_unifi_client, zone_id=zone_id)

        assert result["success"] is True
        assert result["type"] == "firewall_zone"
        assert result["data"]["id"] == zone_id
        assert result["data"]["name"] == "Internal"
        assert result["data"]["origin"] == "system-defined"
        assert "metadata" in result["data"]

        mock_unifi_client.get_v1.assert_called_once_with(f"firewall/zones/{zone_id}")

    @pytest.mark.asyncio
    async def test_get_zone_with_data_wrapper(self, mock_unifi_client):
        """Test handling when v1 response wraps single item in data array."""
        zone_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_ZONES[0]],
        }

        tool = GetFirewallZoneTool()
        result = await tool.execute(mock_unifi_client, zone_id=zone_id)

        assert result["success"] is True
        assert result["data"]["name"] == "Internal"

    @pytest.mark.asyncio
    async def test_zone_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        zone_id = "nonexistent-zone-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: firewall/zones/{zone_id}"
        )

        tool = GetFirewallZoneTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, zone_id=zone_id)

        assert exc_info.value.code == "ZONE_NOT_FOUND"
        assert zone_id in exc_info.value.message
        assert "unifi_list_firewall_zones" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_zone_not_found_empty_data(self, mock_unifi_client):
        """Test handling when API returns empty data list for a zone."""
        zone_id = "nonexistent-zone-id"
        mock_unifi_client.get_v1.return_value = {"data": []}

        tool = GetFirewallZoneTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, zone_id=zone_id)

        assert exc_info.value.code == "ZONE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_defined_zone_details(self, mock_unifi_client):
        """Test that user-defined zones format correctly."""
        zone_id = "d4e5f6a7-b8c9-0123-defa-234567890123"
        mock_unifi_client.get_v1.return_value = MOCK_ZONES[3]

        tool = GetFirewallZoneTool()
        result = await tool.execute(mock_unifi_client, zone_id=zone_id)

        assert result["data"]["origin"] == "user-defined"
        assert result["data"]["name"] == "My Custom Zone"
        assert len(result["data"]["networkIds"]) == 1

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetFirewallZoneTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, zone_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            "Connection refused"
        )

        tool = GetFirewallZoneTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, zone_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestToolMetadata:
    """Test tool metadata and schema definitions."""

    def test_list_tool_name(self):
        tool = ListFirewallZonesTool()
        assert tool.name == "unifi_list_firewall_zones"

    def test_list_tool_category(self):
        tool = ListFirewallZonesTool()
        assert tool.category == "firewall"

    def test_get_tool_name(self):
        tool = GetFirewallZoneTool()
        assert tool.name == "unifi_get_firewall_zone"

    def test_get_tool_requires_zone_id(self):
        tool = GetFirewallZoneTool()
        assert "zone_id" in tool.input_schema["properties"]
        assert "zone_id" in tool.input_schema["required"]


# --- Firewall Policy Tool Tests ---

from unifi_mcp.tools.firewall import (
    ListFirewallPoliciesTool,
    GetFirewallPolicyTool,
    GetFirewallPolicyOrderingTool,
)


# Mock policy data (simulating v1 API responses)

MOCK_POLICIES = [
    {
        "id": "p1111111-1111-1111-1111-111111111111",
        "enabled": True,
        "name": "Allow Internal to External",
        "description": "Allow all traffic from Internal to External zone",
        "index": 0,
        "action": {"type": "ALLOW", "allowReturnTraffic": True},
        "source": {
            "zoneId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "trafficFilter": {},
        },
        "destination": {
            "zoneId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "trafficFilter": {},
        },
        "ipProtocolScope": {"ipVersion": "IPv4_IPv6", "protocolFilter": {}},
        "connectionStateFilter": ["NEW", "ESTABLISHED", "RELATED"],
        "ipsecFilter": None,
        "loggingEnabled": False,
        "schedule": {},
        "metadata": {"origin": "SYSTEM_DEFINED"},
    },
    {
        "id": "p2222222-2222-2222-2222-222222222222",
        "enabled": True,
        "name": "Block IoT to Internal",
        "description": "Block IoT devices from reaching internal network",
        "index": 1,
        "action": {"type": "BLOCK", "allowReturnTraffic": False},
        "source": {
            "zoneId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "trafficFilter": {"networkId": "44444444-4444-4444-4444-444444444444"},
        },
        "destination": {
            "zoneId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "trafficFilter": {},
        },
        "ipProtocolScope": {"ipVersion": "IPv4", "protocolFilter": {"protocol": "TCP"}},
        "connectionStateFilter": ["NEW"],
        "ipsecFilter": None,
        "loggingEnabled": True,
        "schedule": {"timeRange": {"start": "08:00", "end": "22:00"}},
        "metadata": {"origin": "USER_DEFINED"},
    },
]

MOCK_ORDERING = {
    "orderedFirewallPolicyIds": {
        "beforeSystemDefined": [
            "p2222222-2222-2222-2222-222222222222",
        ],
        "afterSystemDefined": [
            "p1111111-1111-1111-1111-111111111111",
        ],
    },
}


class TestListFirewallPoliciesTool:
    """Test ListFirewallPoliciesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_policies(self, mock_unifi_client):
        """Test listing all firewall policies."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_POLICIES,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListFirewallPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("firewall/policies", params=None)

    @pytest.mark.asyncio
    async def test_policy_summary_formatting(self, mock_unifi_client):
        """Test that policy summaries contain required fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_POLICIES,
            "totalCount": 2,
        }

        tool = ListFirewallPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        policies = result["data"]
        assert len(policies) == 2

        # Check first policy
        allow_policy = policies[0]
        assert allow_policy["id"] == "p1111111-1111-1111-1111-111111111111"
        assert allow_policy["name"] == "Allow Internal to External"
        assert allow_policy["enabled"] is True
        assert allow_policy["actionType"] == "ALLOW"
        assert allow_policy["sourceZoneId"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert allow_policy["destinationZoneId"] == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert "protocolScope" in allow_policy

        # Check second policy
        block_policy = policies[1]
        assert block_policy["actionType"] == "BLOCK"
        assert block_policy["enabled"] is True

    @pytest.mark.asyncio
    async def test_empty_policy_list(self, mock_unifi_client):
        """Test handling of empty policy list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListFirewallPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListFirewallPoliciesTool()
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

        tool = ListFirewallPoliciesTool()
        result = await tool.execute(mock_unifi_client)

        policy = result["data"][0]
        assert policy["id"] == "sparse-id"
        assert policy["name"] == "Sparse Policy"
        assert policy["enabled"] is False
        assert policy["actionType"] == "UNKNOWN"
        assert policy["sourceZoneId"] == ""
        assert policy["destinationZoneId"] == ""


class TestGetFirewallPolicyTool:
    """Test GetFirewallPolicyTool functionality."""

    @pytest.mark.asyncio
    async def test_get_policy_details(self, mock_unifi_client):
        """Test retrieving a specific policy's details."""
        policy_id = "p1111111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = MOCK_POLICIES[0]

        tool = GetFirewallPolicyTool()
        result = await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert result["success"] is True
        assert result["type"] == "firewall_policy"
        data = result["data"]
        assert data["id"] == policy_id
        assert data["name"] == "Allow Internal to External"
        assert data["enabled"] is True
        assert data["action"]["type"] == "ALLOW"
        assert data["source"]["zoneId"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert data["destination"]["zoneId"] == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert data["connectionStateFilter"] == ["NEW", "ESTABLISHED", "RELATED"]
        assert data["loggingEnabled"] is False
        assert data["metadata"]["origin"] == "SYSTEM_DEFINED"

        mock_unifi_client.get_v1.assert_called_once_with(f"firewall/policies/{policy_id}")

    @pytest.mark.asyncio
    async def test_get_policy_full_details(self, mock_unifi_client):
        """Test that full details include all expected fields."""
        policy_id = "p2222222-2222-2222-2222-222222222222"
        mock_unifi_client.get_v1.return_value = MOCK_POLICIES[1]

        tool = GetFirewallPolicyTool()
        result = await tool.execute(mock_unifi_client, policy_id=policy_id)

        data = result["data"]
        assert data["description"] == "Block IoT devices from reaching internal network"
        assert data["index"] == 1
        assert data["action"]["type"] == "BLOCK"
        assert data["loggingEnabled"] is True
        assert data["schedule"] == {"timeRange": {"start": "08:00", "end": "22:00"}}
        assert data["ipProtocolScope"]["protocolFilter"]["protocol"] == "TCP"
        assert data["ipsecFilter"] is None

    @pytest.mark.asyncio
    async def test_get_policy_with_data_wrapper(self, mock_unifi_client):
        """Test handling when v1 response wraps single item in data array."""
        policy_id = "p1111111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_POLICIES[0]],
        }

        tool = GetFirewallPolicyTool()
        result = await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert result["success"] is True
        assert result["data"]["name"] == "Allow Internal to External"

    @pytest.mark.asyncio
    async def test_policy_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        policy_id = "nonexistent-policy-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: firewall/policies/{policy_id}"
        )

        tool = GetFirewallPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert exc_info.value.code == "POLICY_NOT_FOUND"
        assert policy_id in exc_info.value.message
        assert "unifi_list_firewall_rules" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_policy_not_found_empty_data(self, mock_unifi_client):
        """Test handling when API returns empty data list for a policy."""
        policy_id = "nonexistent-policy-id"
        mock_unifi_client.get_v1.return_value = {"data": []}

        tool = GetFirewallPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id=policy_id)

        assert exc_info.value.code == "POLICY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetFirewallPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetFirewallPolicyTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, policy_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestGetFirewallPolicyOrderingTool:
    """Test GetFirewallPolicyOrderingTool functionality."""

    @pytest.mark.asyncio
    async def test_get_ordering(self, mock_unifi_client):
        """Test retrieving policy ordering for a zone pair."""
        src_zone = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        dst_zone = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        mock_unifi_client.get_v1.return_value = MOCK_ORDERING

        tool = GetFirewallPolicyOrderingTool()
        result = await tool.execute(
            mock_unifi_client,
            source_zone_id=src_zone,
            destination_zone_id=dst_zone,
        )

        assert result["success"] is True
        assert result["type"] == "firewall_policy_ordering"
        data = result["data"]
        assert data["sourceZoneId"] == src_zone
        assert data["destinationZoneId"] == dst_zone
        assert data["beforeSystemDefined"] == ["p2222222-2222-2222-2222-222222222222"]
        assert data["afterSystemDefined"] == ["p1111111-1111-1111-1111-111111111111"]

        mock_unifi_client.get_v1.assert_called_once_with(
            "firewall/policies/ordering",
            params={
                "sourceFirewallZoneId": src_zone,
                "destinationFirewallZoneId": dst_zone,
            },
        )

    @pytest.mark.asyncio
    async def test_empty_ordering(self, mock_unifi_client):
        """Test handling of empty ordering response."""
        mock_unifi_client.get_v1.return_value = {
            "orderedFirewallPolicyIds": {
                "beforeSystemDefined": [],
                "afterSystemDefined": [],
            },
        }

        tool = GetFirewallPolicyOrderingTool()
        result = await tool.execute(
            mock_unifi_client,
            source_zone_id="zone-a",
            destination_zone_id="zone-b",
        )

        assert result["success"] is True
        data = result["data"]
        assert data["beforeSystemDefined"] == []
        assert data["afterSystemDefined"] == []

    @pytest.mark.asyncio
    async def test_ordering_not_found_404(self, mock_unifi_client):
        """Test 404 handling for ordering endpoint."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            "Resource not found: firewall/policies/ordering"
        )

        tool = GetFirewallPolicyOrderingTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                mock_unifi_client,
                source_zone_id="bad-zone-a",
                destination_zone_id="bad-zone-b",
            )

        assert exc_info.value.code == "ORDERING_NOT_FOUND"
        assert "bad-zone-a" in exc_info.value.message
        assert "bad-zone-b" in exc_info.value.message
        assert "unifi_list_firewall_zones" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetFirewallPolicyOrderingTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                mock_unifi_client,
                source_zone_id="zone-a",
                destination_zone_id="zone-b",
            )

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetFirewallPolicyOrderingTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                mock_unifi_client,
                source_zone_id="zone-a",
                destination_zone_id="zone-b",
            )

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_ordering_missing_fields(self, mock_unifi_client):
        """Test handling when ordering response has missing fields."""
        mock_unifi_client.get_v1.return_value = {}

        tool = GetFirewallPolicyOrderingTool()
        result = await tool.execute(
            mock_unifi_client,
            source_zone_id="zone-a",
            destination_zone_id="zone-b",
        )

        data = result["data"]
        assert data["beforeSystemDefined"] == []
        assert data["afterSystemDefined"] == []


class TestPolicyToolMetadata:
    """Test policy tool metadata and schema definitions."""

    def test_list_policy_tool_name(self):
        tool = ListFirewallPoliciesTool()
        assert tool.name == "unifi_list_firewall_rules"

    def test_list_policy_tool_category(self):
        tool = ListFirewallPoliciesTool()
        assert tool.category == "firewall"

    def test_get_policy_tool_name(self):
        tool = GetFirewallPolicyTool()
        assert tool.name == "unifi_get_firewall_rule_details"

    def test_get_policy_requires_policy_id(self):
        tool = GetFirewallPolicyTool()
        assert "policy_id" in tool.input_schema["properties"]
        assert "policy_id" in tool.input_schema["required"]

    def test_ordering_tool_name(self):
        tool = GetFirewallPolicyOrderingTool()
        assert tool.name == "unifi_get_firewall_policy_ordering"

    def test_ordering_requires_both_zone_ids(self):
        tool = GetFirewallPolicyOrderingTool()
        assert "source_zone_id" in tool.input_schema["properties"]
        assert "destination_zone_id" in tool.input_schema["properties"]
        assert "source_zone_id" in tool.input_schema["required"]
        assert "destination_zone_id" in tool.input_schema["required"]


# --- Traffic Matching List Tool Tests ---

from unifi_mcp.tools.firewall import (
    ListTrafficMatchingListsTool,
    GetTrafficMatchingListTool,
)


# Mock traffic matching list data (simulating v1 API responses)

MOCK_TRAFFIC_LISTS = [
    {
        "id": "t1111111-1111-1111-1111-111111111111",
        "name": "Blocked Countries",
        "type": "REGION",
        "description": "Geographic regions to block",
        "metadata": {"origin": "USER_DEFINED"},
    },
    {
        "id": "t2222222-2222-2222-2222-222222222222",
        "name": "Gaming Ports",
        "type": "PORT",
        "description": "Common gaming port ranges",
        "metadata": {"origin": "USER_DEFINED"},
    },
    {
        "id": "t3333333-3333-3333-3333-333333333333",
        "name": "Internal Servers",
        "type": "IP_ADDRESS",
        "description": "Internal server IP addresses",
        "metadata": {"origin": "SYSTEM_DEFINED"},
    },
]


class TestListTrafficMatchingListsTool:
    """Test ListTrafficMatchingListsTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_traffic_matching_lists(self, mock_unifi_client):
        """Test listing all traffic matching lists."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_TRAFFIC_LISTS,
            "offset": 0,
            "limit": 25,
            "count": 3,
            "totalCount": 3,
        }

        tool = ListTrafficMatchingListsTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 3
        assert result["total"] == 3

        mock_unifi_client.get_v1.assert_called_once_with("traffic-matching-lists", params=None)

    @pytest.mark.asyncio
    async def test_traffic_list_summary_formatting(self, mock_unifi_client):
        """Test that list summaries contain required fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_TRAFFIC_LISTS,
            "totalCount": 3,
        }

        tool = ListTrafficMatchingListsTool()
        result = await tool.execute(mock_unifi_client)

        items = result["data"]
        assert len(items) == 3

        # Check first item
        blocked = items[0]
        assert blocked["id"] == "t1111111-1111-1111-1111-111111111111"
        assert blocked["name"] == "Blocked Countries"
        assert blocked["type"] == "REGION"

        # Check second item
        gaming = items[1]
        assert gaming["id"] == "t2222222-2222-2222-2222-222222222222"
        assert gaming["name"] == "Gaming Ports"
        assert gaming["type"] == "PORT"

    @pytest.mark.asyncio
    async def test_empty_traffic_list(self, mock_unifi_client):
        """Test handling of empty traffic matching list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListTrafficMatchingListsTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListTrafficMatchingListsTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_traffic_list_with_missing_fields(self, mock_unifi_client):
        """Test formatting when list item has missing optional fields."""
        sparse_item = {
            "id": "sparse-id",
            "name": "Sparse List",
        }
        mock_unifi_client.get_v1.return_value = {
            "data": [sparse_item],
            "totalCount": 1,
        }

        tool = ListTrafficMatchingListsTool()
        result = await tool.execute(mock_unifi_client)

        item = result["data"][0]
        assert item["id"] == "sparse-id"
        assert item["name"] == "Sparse List"
        assert item["type"] == ""


class TestGetTrafficMatchingListTool:
    """Test GetTrafficMatchingListTool functionality."""

    @pytest.mark.asyncio
    async def test_get_traffic_list_details(self, mock_unifi_client):
        """Test retrieving a specific traffic matching list's details."""
        list_id = "t1111111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = MOCK_TRAFFIC_LISTS[0]

        tool = GetTrafficMatchingListTool()
        result = await tool.execute(mock_unifi_client, list_id=list_id)

        assert result["success"] is True
        assert result["type"] == "traffic_matching_list"
        data = result["data"]
        assert data["id"] == list_id
        assert data["name"] == "Blocked Countries"
        assert data["type"] == "REGION"
        assert data["description"] == "Geographic regions to block"
        assert data["metadata"] == {"origin": "USER_DEFINED"}

        mock_unifi_client.get_v1.assert_called_once_with(f"traffic-matching-lists/{list_id}")

    @pytest.mark.asyncio
    async def test_get_traffic_list_with_data_wrapper(self, mock_unifi_client):
        """Test handling when v1 response wraps single item in data array."""
        list_id = "t1111111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_TRAFFIC_LISTS[0]],
        }

        tool = GetTrafficMatchingListTool()
        result = await tool.execute(mock_unifi_client, list_id=list_id)

        assert result["success"] is True
        assert result["data"]["name"] == "Blocked Countries"

    @pytest.mark.asyncio
    async def test_traffic_list_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        list_id = "nonexistent-list-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: traffic-matching-lists/{list_id}"
        )

        tool = GetTrafficMatchingListTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, list_id=list_id)

        assert exc_info.value.code == "TRAFFIC_LIST_NOT_FOUND"
        assert list_id in exc_info.value.message
        assert "unifi_list_traffic_matching_lists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_traffic_list_not_found_empty_data(self, mock_unifi_client):
        """Test handling when API returns empty data list."""
        list_id = "nonexistent-list-id"
        mock_unifi_client.get_v1.return_value = {"data": []}

        tool = GetTrafficMatchingListTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, list_id=list_id)

        assert exc_info.value.code == "TRAFFIC_LIST_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetTrafficMatchingListTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, list_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetTrafficMatchingListTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, list_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestTrafficMatchingListToolMetadata:
    """Test traffic matching list tool metadata and schema definitions."""

    def test_list_tool_name(self):
        tool = ListTrafficMatchingListsTool()
        assert tool.name == "unifi_list_traffic_matching_lists"

    def test_list_tool_category(self):
        tool = ListTrafficMatchingListsTool()
        assert tool.category == "firewall"

    def test_get_tool_name(self):
        tool = GetTrafficMatchingListTool()
        assert tool.name == "unifi_get_traffic_matching_list"

    def test_get_tool_category(self):
        tool = GetTrafficMatchingListTool()
        assert tool.category == "firewall"

    def test_get_tool_requires_list_id(self):
        tool = GetTrafficMatchingListTool()
        assert "list_id" in tool.input_schema["properties"]
        assert "list_id" in tool.input_schema["required"]
