"""Unit tests for routing and port forward tools.

Tests the routing and port forward tools with v2 API support:
- ListTrafficRoutesTool
- GetRouteDetailsTool
- ListPortForwardsTool
- GetPortForwardDetailsTool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.security import (
    ListTrafficRoutesTool,
    GetRouteDetailsTool,
    ListPortForwardsTool,
    GetPortForwardDetailsTool,
)
from unifi_mcp.tools.base import ToolError


def create_routes_response(routes, api_version="v1", controller_type="traditional"):
    """Create a mock get_security_data response for traffic routes."""
    normalized_routes = []
    for route in routes:
        normalized_routes.append({
            "id": route.get("_id", route.get("id", "")),
            "name": route.get("name", ""),
            "enabled": route.get("enabled", False),
            "route_type": route.get("type", "static"),
            "destination_network": route.get("static-route_network", ""),
            "next_hop": route.get("static-route_nexthop", ""),
            "distance": route.get("static-route_distance", 1),
            "interface": route.get("static-route_interface", ""),
            "api_version": api_version,
        })
    return {
        "data": normalized_routes,
        "api_version": api_version,
        "controller_type": controller_type,
    }


def create_forwards_response(forwards, api_version="v1", controller_type="traditional"):
    """Create a mock get_security_data response for port forwards."""
    normalized_forwards = []
    for fwd in forwards:
        proto = fwd.get("proto", "tcp")
        if proto == "tcp_udp":
            proto = "TCP/UDP"
        else:
            proto = proto.upper()
        normalized_forwards.append({
            "id": fwd.get("_id", fwd.get("id", "")),
            "name": fwd.get("name", ""),
            "enabled": fwd.get("enabled", False),
            "protocol": proto,
            "source_port": fwd.get("dst_port", ""),
            "destination_port": fwd.get("fwd_port", ""),
            "destination_ip": fwd.get("fwd", ""),
            "source_ip": fwd.get("src", "any"),
            "interface": fwd.get("pfwd_interface", ""),
            "logging": fwd.get("log", False),
            "api_version": api_version,
        })
    return {
        "data": normalized_forwards,
        "api_version": api_version,
        "controller_type": controller_type,
    }


# Mock route data
MOCK_ROUTES = [
    {
        "_id": "route1",
        "name": "VPN Route",
        "enabled": True,
        "type": "static",
        "static-route_network": "10.0.0.0/24",
        "static-route_nexthop": "192.168.1.254",
        "static-route_distance": 1,
        "static-route_interface": "eth0",
    },
    {
        "_id": "route2",
        "name": "Backup Route",
        "enabled": False,
        "type": "static",
        "static-route_network": "10.1.0.0/24",
        "static-route_nexthop": "192.168.1.253",
        "static-route_distance": 10,
        "static-route_interface": "eth1",
    },
]

# Mock port forward data
MOCK_FORWARDS = [
    {
        "_id": "forward1",
        "name": "Web Server",
        "enabled": True,
        "proto": "tcp",
        "src": "any",
        "dst_port": "80",
        "fwd": "192.168.10.100",
        "fwd_port": "8080",
        "log": False,
    },
    {
        "_id": "forward2",
        "name": "SSH Server",
        "enabled": True,
        "proto": "tcp_udp",
        "src": "192.168.1.0/24",
        "dst_port": "22",
        "fwd": "192.168.10.50",
        "fwd_port": "22",
        "log": True,
        "pfwd_interface": "wan",
    },
    {
        "_id": "forward3",
        "name": "Disabled Forward",
        "enabled": False,
        "proto": "udp",
        "src": "any",
        "dst_port": "53",
        "fwd": "192.168.10.1",
        "fwd_port": "53",
        "log": False,
    },
]


@pytest.fixture
def mock_client():
    """Create a mock UniFi client with get_security_data support."""
    client = MagicMock()
    client.get = AsyncMock()
    client.get_security_data = AsyncMock()
    return client


class TestListTrafficRoutesTool:
    """Tests for ListTrafficRoutesTool with v2 API support."""

    @pytest.mark.asyncio
    async def test_list_all_routes(self, mock_client):
        """Test listing all traffic routes."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["data"]) == 2
        mock_client.get_security_data.assert_called_once_with("traffic_routes")

    @pytest.mark.asyncio
    async def test_list_enabled_routes_only(self, mock_client):
        """Test filtering routes by enabled status."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"enabled_only": True})

        assert result["success"] is True
        assert result["total"] == 1
        assert result["data"][0]["name"] == "VPN Route"

    @pytest.mark.asyncio
    async def test_list_routes_pagination(self, mock_client):
        """Test pagination of route list."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"page": 1, "page_size": 1})

        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_routes_empty(self, mock_client):
        """Test listing routes when none exist."""
        mock_client.get_security_data.return_value = create_routes_response([])

        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["total"] == 0
        assert len(result["data"]) == 0


class TestGetRouteDetailsTool:
    """Tests for GetRouteDetailsTool with v2 API support."""

    @pytest.mark.asyncio
    async def test_get_route_details(self, mock_client):
        """Test getting route details by ID."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "route1"})

        assert result["success"] is True
        assert result["data"]["id"] == "route1"
        assert result["data"]["name"] == "VPN Route"

    @pytest.mark.asyncio
    async def test_get_route_details_not_found(self, mock_client):
        """Test getting route that doesn't exist."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "nonexistent"})

        assert "error" in result
        assert result["error"]["code"] == "ROUTE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_route_details_case_insensitive(self, mock_client):
        """Test that route search is case-insensitive."""
        mock_client.get_security_data.return_value = create_routes_response(MOCK_ROUTES)

        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "ROUTE1"})

        assert result["success"] is True
        assert result["data"]["id"] == "route1"


class TestListPortForwardsTool:
    """Tests for ListPortForwardsTool with v2 API support."""

    @pytest.mark.asyncio
    async def test_list_all_forwards(self, mock_client):
        """Test listing all port forwards."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["total"] == 3
        assert len(result["data"]) == 3
        mock_client.get_security_data.assert_called_once_with("port_forwards")

    @pytest.mark.asyncio
    async def test_list_enabled_forwards_only(self, mock_client):
        """Test filtering forwards by enabled status."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {"enabled_only": True})

        assert result["success"] is True
        assert result["total"] == 2
        # All returned items should be enabled
        for item in result["data"]:
            assert item["enabled"] is True

    @pytest.mark.asyncio
    async def test_list_forwards_protocol_formatting(self, mock_client):
        """Test that protocols are formatted correctly."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        # Find the TCP/UDP forward
        tcp_udp_forward = next(
            (f for f in result["data"] if f["name"] == "SSH Server"),
            None
        )
        assert tcp_udp_forward is not None
        assert tcp_udp_forward["protocol"] == "TCP/UDP"

    @pytest.mark.asyncio
    async def test_list_forwards_pagination(self, mock_client):
        """Test pagination of forward list."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {"page": 1, "page_size": 2})

        assert result["success"] is True
        assert result["total"] == 3
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_list_forwards_empty(self, mock_client):
        """Test listing forwards when none exist."""
        mock_client.get_security_data.return_value = create_forwards_response([])

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["total"] == 0
        assert len(result["data"]) == 0


class TestGetPortForwardDetailsTool:
    """Tests for GetPortForwardDetailsTool with v2 API support."""

    @pytest.mark.asyncio
    async def test_get_forward_details(self, mock_client):
        """Test getting port forward details by ID."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "forward1"})

        assert result["success"] is True
        assert result["data"]["id"] == "forward1"
        assert result["data"]["name"] == "Web Server"

    @pytest.mark.asyncio
    async def test_get_forward_details_with_source_restriction(self, mock_client):
        """Test getting forward with source IP restriction."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "forward2"})

        assert result["success"] is True
        assert result["data"]["source_ip"] == "192.168.1.0/24"

    @pytest.mark.asyncio
    async def test_get_forward_details_not_found(self, mock_client):
        """Test getting forward that doesn't exist."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "nonexistent"})

        assert "error" in result
        assert result["error"]["code"] == "FORWARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_forward_details_case_insensitive(self, mock_client):
        """Test that forward search is case-insensitive."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "FORWARD1"})

        assert result["success"] is True
        assert result["data"]["id"] == "forward1"

    @pytest.mark.asyncio
    async def test_get_forward_details_protocol_formatting(self, mock_client):
        """Test that protocol is formatted correctly in details."""
        mock_client.get_security_data.return_value = create_forwards_response(MOCK_FORWARDS)

        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "forward2"})

        assert result["success"] is True
        assert result["data"]["protocol"] == "TCP/UDP"


class TestV2APIMetadata:
    """Tests for v2 API metadata in routing tools."""

    @pytest.mark.asyncio
    async def test_routes_include_api_version(self, mock_client):
        """Test that route list includes API version metadata."""
        mock_client.get_security_data.return_value = create_routes_response(
            MOCK_ROUTES, api_version="v2", controller_type="unifi_os"
        )

        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["api_version"] == "v2"
        assert result["controller_type"] == "unifi_os"

    @pytest.mark.asyncio
    async def test_forwards_include_api_version(self, mock_client):
        """Test that forward list includes API version metadata."""
        mock_client.get_security_data.return_value = create_forwards_response(
            MOCK_FORWARDS, api_version="v2", controller_type="unifi_os"
        )

        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})

        assert result["success"] is True
        assert result["api_version"] == "v2"
        assert result["controller_type"] == "unifi_os"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
