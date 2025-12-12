"""Unit tests for routing and port forward tools.

Tests the routing and port forward tools implemented in Task 15:
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
        "site_id": "default",
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
        "site_id": "default",
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
        "site_id": "default",
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
        "site_id": "default",
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
        "site_id": "default",
    },
]


@pytest.fixture
def mock_client():
    """Create a mock UniFi client."""
    client = MagicMock()
    client.get = AsyncMock()
    return client


class TestListTrafficRoutesTool:
    """Tests for ListTrafficRoutesTool."""
    
    @pytest.mark.asyncio
    async def test_list_all_routes(self, mock_client):
        """Test listing all traffic routes."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify result
        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2
        assert len(result["data"]) == 2
        
        # Verify first route
        route = result["data"][0]
        assert route["id"] == "route1"
        assert route["name"] == "VPN Route"
        assert route["enabled"] is True
        assert route["destination_network"] == "10.0.0.0/24"
        assert route["next_hop"] == "192.168.1.254"
        
        # Verify API call
        mock_client.get.assert_called_once_with("/api/s/{site}/rest/routing")
    
    @pytest.mark.asyncio
    async def test_list_enabled_routes_only(self, mock_client):
        """Test listing only enabled routes."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke with enabled_only filter
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"enabled_only": True})
        
        # Verify result - should only have 1 enabled route
        assert result["success"] is True
        assert result["count"] == 1
        assert result["total"] == 1
        assert result["data"][0]["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_list_routes_pagination(self, mock_client):
        """Test route listing with pagination."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke with pagination
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"page": 1, "page_size": 1})
        
        # Verify result - should only have 1 route per page
        assert result["success"] is True
        assert result["count"] == 1
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 1
    
    @pytest.mark.asyncio
    async def test_list_routes_empty(self, mock_client):
        """Test listing routes when none exist."""
        # Setup mock response with no routes
        mock_client.get.return_value = {"data": []}
        
        # Create tool and invoke
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify result
        assert result["success"] is True
        assert result["count"] == 0
        assert result["total"] == 0
        assert len(result["data"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_routes_api_error(self, mock_client):
        """Test handling of API errors."""
        # Setup mock to raise exception
        mock_client.get.side_effect = Exception("Connection failed")
        
        # Create tool and invoke
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "API_ERROR"
        assert "Failed to retrieve traffic routes" in result["error"]["message"]


class TestGetRouteDetailsTool:
    """Tests for GetRouteDetailsTool."""
    
    @pytest.mark.asyncio
    async def test_get_route_details(self, mock_client):
        """Test getting details for a specific route."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke
        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "route1"})
        
        # Verify result
        assert result["success"] is True
        assert result["type"] == "traffic_route"
        
        route = result["data"]
        assert route["id"] == "route1"
        assert route["name"] == "VPN Route"
        assert route["enabled"] is True
        assert route["destination_network"] == "10.0.0.0/24"
        assert route["next_hop"] == "192.168.1.254"
        assert route["distance"] == 1
        assert route["interface"] == "eth0"
    
    @pytest.mark.asyncio
    async def test_get_route_details_not_found(self, mock_client):
        """Test getting details for non-existent route."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke with invalid ID
        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "nonexistent"})
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "ROUTE_NOT_FOUND"
        assert "nonexistent" in result["error"]["details"]
    
    @pytest.mark.asyncio
    async def test_get_route_details_case_insensitive(self, mock_client):
        """Test that route ID lookup is case-insensitive."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_ROUTES}
        
        # Create tool and invoke with uppercase ID
        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {"route_id": "ROUTE1"})
        
        # Verify result - should find the route
        assert result["success"] is True
        assert result["data"]["id"] == "route1"


class TestListPortForwardsTool:
    """Tests for ListPortForwardsTool."""
    
    @pytest.mark.asyncio
    async def test_list_all_forwards(self, mock_client):
        """Test listing all port forwards."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke
        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify result
        assert result["success"] is True
        assert result["count"] == 3
        assert result["total"] == 3
        assert len(result["data"]) == 3
        
        # Verify first forward
        forward = result["data"][0]
        assert forward["id"] == "forward1"
        assert forward["name"] == "Web Server"
        assert forward["enabled"] is True
        assert forward["protocol"] == "TCP"
        assert forward["external_port"] == "80"
        assert forward["destination_ip"] == "192.168.10.100"
        assert forward["destination_port"] == "8080"
        
        # Verify API call
        mock_client.get.assert_called_once_with("/api/s/{site}/rest/portforward")
    
    @pytest.mark.asyncio
    async def test_list_enabled_forwards_only(self, mock_client):
        """Test listing only enabled port forwards."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke with enabled_only filter
        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {"enabled_only": True})
        
        # Verify result - should only have 2 enabled forwards
        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2
        assert all(fwd["enabled"] for fwd in result["data"])
    
    @pytest.mark.asyncio
    async def test_list_forwards_protocol_formatting(self, mock_client):
        """Test protocol formatting in port forwards."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke
        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify protocol formatting
        forwards = result["data"]
        assert forwards[0]["protocol"] == "TCP"  # tcp -> TCP
        assert forwards[1]["protocol"] == "TCP/UDP"  # tcp_udp -> TCP/UDP
        assert forwards[2]["protocol"] == "UDP"  # udp -> UDP
    
    @pytest.mark.asyncio
    async def test_list_forwards_pagination(self, mock_client):
        """Test port forward listing with pagination."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke with pagination
        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {"page": 1, "page_size": 2})
        
        # Verify result - should only have 2 forwards per page
        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 2
    
    @pytest.mark.asyncio
    async def test_list_forwards_empty(self, mock_client):
        """Test listing port forwards when none exist."""
        # Setup mock response with no forwards
        mock_client.get.return_value = {"data": []}
        
        # Create tool and invoke
        tool = ListPortForwardsTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify result
        assert result["success"] is True
        assert result["count"] == 0
        assert result["total"] == 0
        assert len(result["data"]) == 0


class TestGetPortForwardDetailsTool:
    """Tests for GetPortForwardDetailsTool."""
    
    @pytest.mark.asyncio
    async def test_get_forward_details(self, mock_client):
        """Test getting details for a specific port forward."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke
        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "forward1"})
        
        # Verify result
        assert result["success"] is True
        assert result["type"] == "port_forward"
        
        forward = result["data"]
        assert forward["id"] == "forward1"
        assert forward["name"] == "Web Server"
        assert forward["enabled"] is True
        assert forward["external_port"] == "80"
        assert forward["destination_ip"] == "192.168.10.100"
        assert forward["destination_port"] == "8080"
        assert forward["protocol"]["type"] == "tcp"
        assert forward["protocol"]["display"] == "TCP"
    
    @pytest.mark.asyncio
    async def test_get_forward_details_with_source_restriction(self, mock_client):
        """Test getting details for forward with source restriction."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke
        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "forward2"})
        
        # Verify result includes source restriction
        assert result["success"] is True
        forward = result["data"]
        assert forward["source"] == "192.168.1.0/24"
        assert forward["source_network_id"] == "wan"
        assert forward["log"] is True
    
    @pytest.mark.asyncio
    async def test_get_forward_details_not_found(self, mock_client):
        """Test getting details for non-existent port forward."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke with invalid ID
        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "nonexistent"})
        
        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "FORWARD_NOT_FOUND"
        assert "nonexistent" in result["error"]["details"]
    
    @pytest.mark.asyncio
    async def test_get_forward_details_case_insensitive(self, mock_client):
        """Test that forward ID lookup is case-insensitive."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke with uppercase ID
        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {"forward_id": "FORWARD1"})
        
        # Verify result - should find the forward
        assert result["success"] is True
        assert result["data"]["id"] == "forward1"
    
    @pytest.mark.asyncio
    async def test_get_forward_details_protocol_formatting(self, mock_client):
        """Test protocol formatting in detailed view."""
        # Setup mock response
        mock_client.get.return_value = {"data": MOCK_FORWARDS}
        
        # Create tool and invoke
        tool = GetPortForwardDetailsTool()
        
        # Test TCP
        result = await tool.invoke(mock_client, {"forward_id": "forward1"})
        assert result["data"]["protocol"]["display"] == "TCP"
        
        # Test TCP/UDP
        result = await tool.invoke(mock_client, {"forward_id": "forward2"})
        assert result["data"]["protocol"]["display"] == "TCP/UDP"
        
        # Test UDP
        result = await tool.invoke(mock_client, {"forward_id": "forward3"})
        assert result["data"]["protocol"]["display"] == "UDP"


class TestInputValidation:
    """Tests for input validation."""
    
    @pytest.mark.asyncio
    async def test_list_routes_invalid_page(self, mock_client):
        """Test validation of page parameter."""
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"page": 0})
        
        # Verify validation error
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_list_routes_invalid_page_size(self, mock_client):
        """Test validation of page_size parameter."""
        tool = ListTrafficRoutesTool()
        result = await tool.invoke(mock_client, {"page_size": 1000})
        
        # Verify validation error
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_route_missing_id(self, mock_client):
        """Test validation of required route_id parameter."""
        tool = GetRouteDetailsTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify validation error
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_forward_missing_id(self, mock_client):
        """Test validation of required forward_id parameter."""
        tool = GetPortForwardDetailsTool()
        result = await tool.invoke(mock_client, {})
        
        # Verify validation error
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
