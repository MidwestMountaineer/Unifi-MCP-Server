"""Unit tests for supporting resource tools.

Tests cover:
- ListSitesTool: Site listing via site-independent /v1/sites endpoint
- GetAppInfoTool: App info retrieval via site-independent /v1/info endpoint
- ListWANInterfacesTool: WAN interface listing
- ListVPNTunnelsTool: VPN tunnel listing
- ListVPNServersTool: VPN server listing
- GetNetworkReferencesTool: Network reference retrieval with 404 handling
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.resources import (
    ListSitesTool,
    GetAppInfoTool,
    ListWANInterfacesTool,
    ListVPNTunnelsTool,
    ListVPNServersTool,
    GetNetworkReferencesTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient, UniFiClientError


# Mock data simulating v1 API responses

MOCK_SITES = [
    {
        "id": "site11111-1111-1111-1111-111111111111",
        "name": "Default",
    },
    {
        "id": "site22222-2222-2222-2222-222222222222",
        "name": "Remote Office",
    },
]

MOCK_APP_INFO = {
    "version": "9.0.114",
    "name": "UniFi Network",
}

MOCK_WANS = [
    {
        "id": "wan11111-1111-1111-1111-111111111111",
        "name": "WAN 1",
    },
    {
        "id": "wan22222-2222-2222-2222-222222222222",
        "name": "WAN 2",
    },
]

MOCK_VPN_TUNNELS = [
    {
        "id": "tun11111-1111-1111-1111-111111111111",
        "name": "Office-to-Office Tunnel",
    },
]

MOCK_VPN_SERVERS = [
    {
        "id": "vpn11111-1111-1111-1111-111111111111",
        "name": "WireGuard Server",
    },
    {
        "id": "vpn22222-2222-2222-2222-222222222222",
        "name": "L2TP Server",
    },
]

MOCK_NETWORK_REFERENCES = [
    {
        "id": "ref11111-1111-1111-1111-111111111111",
        "type": "FIREWALL_ZONE",
        "name": "Internal",
    },
    {
        "id": "ref22222-2222-2222-2222-222222222222",
        "type": "FIREWALL_POLICY",
        "name": "Allow LAN to WAN",
    },
]


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get_v1 = AsyncMock()
    return client



class TestListSitesTool:
    """Test ListSitesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_sites(self, mock_unifi_client):
        """Test listing all sites via site-independent endpoint."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_SITES,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListSitesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("/v1/sites", params=None)

    @pytest.mark.asyncio
    async def test_site_summary_formatting(self, mock_unifi_client):
        """Test that site summaries contain id and name."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_SITES,
            "totalCount": 2,
        }

        tool = ListSitesTool()
        result = await tool.execute(mock_unifi_client)

        sites = result["data"]
        assert len(sites) == 2

        assert sites[0]["id"] == "site11111-1111-1111-1111-111111111111"
        assert sites[0]["name"] == "Default"
        assert sites[1]["id"] == "site22222-2222-2222-2222-222222222222"
        assert sites[1]["name"] == "Remote Office"

    @pytest.mark.asyncio
    async def test_empty_site_list(self, mock_unifi_client):
        """Test handling of empty site list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListSitesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListSitesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_site_with_missing_fields(self, mock_unifi_client):
        """Test formatting when site has missing optional fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": [{"id": "some-id"}],
            "totalCount": 1,
        }

        tool = ListSitesTool()
        result = await tool.execute(mock_unifi_client)

        site = result["data"][0]
        assert site["id"] == "some-id"
        assert site["name"] == ""


class TestGetAppInfoTool:
    """Test GetAppInfoTool functionality."""

    @pytest.mark.asyncio
    async def test_get_app_info(self, mock_unifi_client):
        """Test retrieving application info via site-independent endpoint."""
        mock_unifi_client.get_v1.return_value = MOCK_APP_INFO

        tool = GetAppInfoTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["type"] == "app_info"
        assert result["data"]["version"] == "9.0.114"
        assert result["data"]["name"] == "UniFi Network"

        mock_unifi_client.get_v1.assert_called_once_with("/v1/info")

    @pytest.mark.asyncio
    async def test_app_info_missing_fields(self, mock_unifi_client):
        """Test handling when info response has missing fields."""
        mock_unifi_client.get_v1.return_value = {}

        tool = GetAppInfoTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["data"]["version"] == ""
        assert result["data"]["name"] == ""

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetAppInfoTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"


class TestListWANInterfacesTool:
    """Test ListWANInterfacesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_wans(self, mock_unifi_client):
        """Test listing all WAN interfaces."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_WANS,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListWANInterfacesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("wans", params=None)

    @pytest.mark.asyncio
    async def test_wan_summary_formatting(self, mock_unifi_client):
        """Test that WAN summaries contain id and name."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_WANS,
            "totalCount": 2,
        }

        tool = ListWANInterfacesTool()
        result = await tool.execute(mock_unifi_client)

        wans = result["data"]
        assert len(wans) == 2
        assert wans[0]["id"] == "wan11111-1111-1111-1111-111111111111"
        assert wans[0]["name"] == "WAN 1"
        assert wans[1]["name"] == "WAN 2"

    @pytest.mark.asyncio
    async def test_empty_wan_list(self, mock_unifi_client):
        """Test handling of empty WAN list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListWANInterfacesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListWANInterfacesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"


class TestListVPNTunnelsTool:
    """Test ListVPNTunnelsTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_tunnels(self, mock_unifi_client):
        """Test listing all VPN tunnels."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_VPN_TUNNELS,
            "offset": 0,
            "limit": 25,
            "count": 1,
            "totalCount": 1,
        }

        tool = ListVPNTunnelsTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["total"] == 1

        mock_unifi_client.get_v1.assert_called_once_with("vpn/site-to-site-tunnels", params=None)

    @pytest.mark.asyncio
    async def test_tunnel_summary_formatting(self, mock_unifi_client):
        """Test that tunnel summaries contain id and name."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_VPN_TUNNELS,
            "totalCount": 1,
        }

        tool = ListVPNTunnelsTool()
        result = await tool.execute(mock_unifi_client)

        tunnels = result["data"]
        assert len(tunnels) == 1
        assert tunnels[0]["id"] == "tun11111-1111-1111-1111-111111111111"
        assert tunnels[0]["name"] == "Office-to-Office Tunnel"

    @pytest.mark.asyncio
    async def test_empty_tunnel_list(self, mock_unifi_client):
        """Test handling of empty VPN tunnel list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListVPNTunnelsTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = ListVPNTunnelsTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"


class TestListVPNServersTool:
    """Test ListVPNServersTool functionality."""

    @pytest.mark.asyncio
    async def test_list_all_servers(self, mock_unifi_client):
        """Test listing all VPN servers."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_VPN_SERVERS,
            "offset": 0,
            "limit": 25,
            "count": 2,
            "totalCount": 2,
        }

        tool = ListVPNServersTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with("vpn/servers", params=None)

    @pytest.mark.asyncio
    async def test_server_summary_formatting(self, mock_unifi_client):
        """Test that server summaries contain id and name."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_VPN_SERVERS,
            "totalCount": 2,
        }

        tool = ListVPNServersTool()
        result = await tool.execute(mock_unifi_client)

        servers = result["data"]
        assert len(servers) == 2
        assert servers[0]["id"] == "vpn11111-1111-1111-1111-111111111111"
        assert servers[0]["name"] == "WireGuard Server"
        assert servers[1]["name"] == "L2TP Server"

    @pytest.mark.asyncio
    async def test_empty_server_list(self, mock_unifi_client):
        """Test handling of empty VPN server list."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = ListVPNServersTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test that API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListVPNServersTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"



class TestGetNetworkReferencesTool:
    """Test GetNetworkReferencesTool functionality."""

    @pytest.mark.asyncio
    async def test_get_references(self, mock_unifi_client):
        """Test retrieving network references."""
        network_id = "net11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_NETWORK_REFERENCES,
            "totalCount": 2,
        }

        tool = GetNetworkReferencesTool()
        result = await tool.execute(mock_unifi_client, network_id=network_id)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        mock_unifi_client.get_v1.assert_called_once_with(f"networks/{network_id}/references")

    @pytest.mark.asyncio
    async def test_reference_formatting(self, mock_unifi_client):
        """Test that references contain id, type, and name."""
        network_id = "net11111-1111-1111-1111-111111111111"
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_NETWORK_REFERENCES,
            "totalCount": 2,
        }

        tool = GetNetworkReferencesTool()
        result = await tool.execute(mock_unifi_client, network_id=network_id)

        refs = result["data"]
        assert len(refs) == 2
        assert refs[0]["id"] == "ref11111-1111-1111-1111-111111111111"
        assert refs[0]["type"] == "FIREWALL_ZONE"
        assert refs[0]["name"] == "Internal"
        assert refs[1]["type"] == "FIREWALL_POLICY"
        assert refs[1]["name"] == "Allow LAN to WAN"

    @pytest.mark.asyncio
    async def test_empty_references(self, mock_unifi_client):
        """Test handling of network with no references."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
        }

        tool = GetNetworkReferencesTool()
        result = await tool.execute(mock_unifi_client, network_id="some-id")

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_network_not_found_404(self, mock_unifi_client):
        """Test 404 handling with descriptive error message."""
        network_id = "nonexistent-network-id"
        mock_unifi_client.get_v1.side_effect = UniFiClientError(
            f"Resource not found: networks/{network_id}/references"
        )

        tool = GetNetworkReferencesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, network_id=network_id)

        assert exc_info.value.code == "NETWORK_NOT_FOUND"
        assert network_id in exc_info.value.message
        assert "unifi_list_networks" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_non_404_client_error(self, mock_unifi_client):
        """Test UniFiClientError that isn't a 404."""
        mock_unifi_client.get_v1.side_effect = UniFiClientError("Connection refused")

        tool = GetNetworkReferencesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, network_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_unifi_client):
        """Test generic exception handling."""
        mock_unifi_client.get_v1.side_effect = Exception("Timeout")

        tool = GetNetworkReferencesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, network_id="some-id")

        assert exc_info.value.code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_reference_with_missing_fields(self, mock_unifi_client):
        """Test formatting when reference has missing optional fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": [{"id": "ref-id"}],
            "totalCount": 1,
        }

        tool = GetNetworkReferencesTool()
        result = await tool.execute(mock_unifi_client, network_id="some-id")

        ref = result["data"][0]
        assert ref["id"] == "ref-id"
        assert ref["type"] == ""
        assert ref["name"] == ""


class TestResourceToolMetadata:
    """Test resource tool metadata and schema definitions."""

    def test_list_sites_tool_name(self):
        tool = ListSitesTool()
        assert tool.name == "unifi_list_sites"

    def test_list_sites_tool_category(self):
        tool = ListSitesTool()
        assert tool.category == "resources"

    def test_get_app_info_tool_name(self):
        tool = GetAppInfoTool()
        assert tool.name == "unifi_get_app_info"

    def test_get_app_info_tool_category(self):
        tool = GetAppInfoTool()
        assert tool.category == "resources"

    def test_list_wan_tool_name(self):
        tool = ListWANInterfacesTool()
        assert tool.name == "unifi_list_wan_interfaces"

    def test_list_wan_tool_category(self):
        tool = ListWANInterfacesTool()
        assert tool.category == "resources"

    def test_list_vpn_tunnels_tool_name(self):
        tool = ListVPNTunnelsTool()
        assert tool.name == "unifi_list_vpn_tunnels"

    def test_list_vpn_tunnels_tool_category(self):
        tool = ListVPNTunnelsTool()
        assert tool.category == "resources"

    def test_list_vpn_servers_tool_name(self):
        tool = ListVPNServersTool()
        assert tool.name == "unifi_list_vpn_servers"

    def test_list_vpn_servers_tool_category(self):
        tool = ListVPNServersTool()
        assert tool.category == "resources"

    def test_get_network_references_tool_name(self):
        tool = GetNetworkReferencesTool()
        assert tool.name == "unifi_get_network_references"

    def test_get_network_references_tool_category(self):
        tool = GetNetworkReferencesTool()
        assert tool.category == "resources"

    def test_get_network_references_requires_network_id(self):
        tool = GetNetworkReferencesTool()
        assert "network_id" in tool.input_schema["properties"]
        assert "network_id" in tool.input_schema["required"]

    def test_list_tools_have_no_required_params(self):
        """All list tools should have no required parameters (pagination params are optional)."""
        for ToolClass in [ListSitesTool, GetAppInfoTool, ListWANInterfacesTool,
                          ListVPNTunnelsTool, ListVPNServersTool]:
            tool = ToolClass()
            assert "required" not in tool.input_schema or tool.input_schema.get("required") == [], \
                f"{tool.name} should have no required parameters"
