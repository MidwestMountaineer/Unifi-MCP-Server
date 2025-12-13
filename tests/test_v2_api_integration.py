"""Integration tests for UniFi MCP Server v2 API support.

This module provides comprehensive integration tests for the v2 API support,
testing the full flow from tool call to normalized response for both
UniFi OS and traditional controllers.

Tests cover:
- Mock UniFi OS v2 API responses for all security endpoints
- Mock traditional controller v1 API responses
- Full flow from tool call to normalized response
- Correct endpoint selection based on controller type
- Backward compatibility with traditional controllers
- Response format consistency across API versions

Requirements validated:
- 2.1, 3.1, 4.1, 5.1: v2 endpoint usage for UniFi OS
- 7.1, 7.4: Backward compatibility with traditional controllers
"""

import pytest
from dataclasses import asdict
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from unifi_mcp.api.controller_detector import ControllerType, ControllerDetector
from unifi_mcp.api.endpoint_router import EndpointRouter
from unifi_mcp.api.response_normalizer import (
    ResponseNormalizer,
    NormalizedFirewallRule,
    NormalizedIPSStatus,
    NormalizedTrafficRoute,
    NormalizedPortForward,
)
from unifi_mcp.tools.security import (
    ListFirewallRulesTool,
    GetFirewallRuleDetailsTool,
    ListTrafficRoutesTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient


# =============================================================================
# Mock v2 API Responses (UniFi OS - Dream Machine, Cloud Gateway)
# =============================================================================

MOCK_V2_FIREWALL_RULES = [
    {
        "id": "v2-rule-001",
        "description": "Allow Core to Internet",
        "enabled": True,
        "action": "ALLOW",
        "ip_protocol": "all",
        "source": {
            "zone": "Core",
            "address": "192.168.10.0/24",
        },
        "destination": {
            "zone": "WAN",
            "address": "",
            "port": "",
        },
        "logging": False,
        "matching_target": "INTERNET",
    },
    {
        "id": "v2-rule-002",
        "description": "Block IoT to Core",
        "enabled": True,
        "action": "DENY",
        "ip_protocol": "all",
        "source": {
            "zone": "IoT",
            "address": "192.168.30.0/24",
        },
        "destination": {
            "zone": "Core",
            "address": "192.168.10.0/24",
            "port": "",
        },
        "logging": True,
        "matching_target": "INTER_VLAN",
    },
    {
        "id": "v2-rule-003",
        "description": "Allow HTTPS to Web Server",
        "enabled": True,
        "action": "ALLOW",
        "ip_protocol": "tcp",
        "source": {
            "zone": "WAN",
            "address": "",
        },
        "destination": {
            "zone": "Core",
            "address": "192.168.10.50",
            "port": "443",
        },
        "logging": False,
        "matching_target": "WAN_IN",
    },
    {
        "id": "v2-rule-004",
        "description": "Disabled Test Rule",
        "enabled": False,
        "action": "REJECT",
        "ip_protocol": "tcp_udp",
        "source": {
            "zone": "",
            "address": "",
        },
        "destination": {
            "zone": "",
            "address": "",
            "port": "22",
        },
        "logging": True,
        "matching_target": "LAN_LOCAL",
    },
]


MOCK_V2_THREAT_MANAGEMENT = {
    "enabled": True,
    "mode": "prevention",
    "stats": {
        "blocked_threats": 42,
        "detected_threats": 156,
        "scanned_packets": 1000000,
    },
    "alerts": [
        {
            "id": "alert-001",
            "timestamp": "2025-12-13T10:00:00Z",
            "category": "malware",
            "severity": "high",
            "description": "Malware communication blocked",
        },
        {
            "id": "alert-002",
            "timestamp": "2025-12-13T09:30:00Z",
            "category": "intrusion",
            "severity": "medium",
            "description": "Port scan detected",
        },
    ],
}


MOCK_V2_TRAFFIC_ROUTES = [
    {
        "id": "v2-route-001",
        "description": "VPN Route to Remote Office",
        "enabled": True,
        "matching_target": "policy",
        "destination": {
            "network": "10.0.0.0/8",
        },
        "target_device": {
            "ip": "192.168.1.254",
        },
        "interface": {
            "name": "wg0",
        },
        "distance": 10,
    },
    {
        "id": "v2-route-002",
        "description": "Static Route to Lab Network",
        "enabled": True,
        "matching_target": "static",
        "destination": {
            "network": "172.16.0.0/16",
        },
        "target_device": {
            "ip": "192.168.10.1",
        },
        "interface": {
            "name": "eth1",
        },
        "distance": 1,
    },
    {
        "id": "v2-route-003",
        "description": "Disabled Test Route",
        "enabled": False,
        "matching_target": "static",
        "destination": {
            "network": "192.168.100.0/24",
        },
        "target_device": {
            "ip": "192.168.10.254",
        },
        "interface": {
            "name": "eth0",
        },
        "distance": 5,
    },
]


MOCK_V2_PORT_FORWARDS = [
    {
        "id": "v2-pf-001",
        "name": "Web Server HTTPS",
        "enabled": True,
        "protocol": "TCP",
        "port": "443",
        "forward_port": "443",
        "forward_ip": "192.168.10.50",
        "source": {},
    },
    {
        "id": "v2-pf-002",
        "name": "Game Server",
        "enabled": True,
        "protocol": "UDP",
        "port": "27015",
        "forward_port": "27015",
        "forward_ip": "192.168.10.20",
        "source": {},
    },
    {
        "id": "v2-pf-003",
        "name": "SSH Access (Restricted)",
        "enabled": True,
        "protocol": "TCP",
        "port": "2222",
        "forward_port": "22",
        "forward_ip": "192.168.10.80",
        "source": {
            "ip": "203.0.113.0/24",
        },
    },
    {
        "id": "v2-pf-004",
        "name": "Disabled FTP",
        "enabled": False,
        "protocol": "TCP",
        "port": "21",
        "forward_port": "21",
        "forward_ip": "192.168.10.100",
        "source": {},
    },
]


# =============================================================================
# Mock v1 API Responses (Traditional Controller)
# =============================================================================

MOCK_V1_FIREWALL_RULES = [
    {
        "_id": "v1-rule-001",
        "rule_index": 2000,
        "name": "Allow Core to Internet",
        "enabled": True,
        "action": "accept",
        "protocol": "all",
        "src_firewallgroup_ids": ["group_core"],
        "dst_firewallgroup_ids": [],
        "src_address": "192.168.10.0/24",
        "dst_address": "",
        "dst_port": "",
        "logging": False,
        "ruleset": "WAN_OUT",
    },
    {
        "_id": "v1-rule-002",
        "rule_index": 2001,
        "name": "Block IoT to Core",
        "enabled": True,
        "action": "drop",
        "protocol": "all",
        "src_firewallgroup_ids": ["group_iot"],
        "dst_firewallgroup_ids": ["group_core"],
        "src_address": "192.168.30.0/24",
        "dst_address": "192.168.10.0/24",
        "dst_port": "",
        "logging": True,
        "ruleset": "LAN_IN",
    },
    {
        "_id": "v1-rule-003",
        "rule_index": 2002,
        "name": "Allow HTTPS to Web Server",
        "enabled": True,
        "action": "accept",
        "protocol": "tcp",
        "src_firewallgroup_ids": [],
        "dst_firewallgroup_ids": [],
        "src_address": "",
        "dst_address": "192.168.10.50",
        "dst_port": "443",
        "logging": False,
        "ruleset": "WAN_IN",
    },
    {
        "_id": "v1-rule-004",
        "rule_index": 2003,
        "name": "Disabled Test Rule",
        "enabled": False,
        "action": "reject",
        "protocol": "tcp_udp",
        "src_firewallgroup_ids": [],
        "dst_firewallgroup_ids": [],
        "src_address": "",
        "dst_address": "",
        "dst_port": "22",
        "logging": True,
        "ruleset": "LAN_LOCAL",
    },
]


MOCK_V1_IPS_SETTINGS = {
    "ips_mode": "ips",
    "suppression": {
        "enabled": True,
    },
}


MOCK_V1_ROUTING = [
    {
        "_id": "v1-route-001",
        "name": "VPN Route to Remote Office",
        "enabled": True,
        "type": "policy",
        "static-route_network": "10.0.0.0/8",
        "static-route_nexthop": "192.168.1.254",
        "static-route_interface": "wg0",
        "static-route_distance": 10,
    },
    {
        "_id": "v1-route-002",
        "name": "Static Route to Lab Network",
        "enabled": True,
        "type": "static",
        "static-route_network": "172.16.0.0/16",
        "static-route_nexthop": "192.168.10.1",
        "static-route_interface": "eth1",
        "static-route_distance": 1,
    },
    {
        "_id": "v1-route-003",
        "name": "Disabled Test Route",
        "enabled": False,
        "type": "static",
        "static-route_network": "192.168.100.0/24",
        "static-route_nexthop": "192.168.10.254",
        "static-route_interface": "eth0",
        "static-route_distance": 5,
    },
]


MOCK_V1_PORT_FORWARDS = [
    {
        "_id": "v1-pf-001",
        "name": "Web Server HTTPS",
        "enabled": True,
        "proto": "tcp",
        "src": "443",
        "fwd_port": "443",
        "fwd": "192.168.10.50",
        "src_ip": "",
    },
    {
        "_id": "v1-pf-002",
        "name": "Game Server",
        "enabled": True,
        "proto": "udp",
        "src": "27015",
        "fwd_port": "27015",
        "fwd": "192.168.10.20",
        "src_ip": "",
    },
    {
        "_id": "v1-pf-003",
        "name": "SSH Access (Restricted)",
        "enabled": True,
        "proto": "tcp",
        "src": "2222",
        "fwd_port": "22",
        "fwd": "192.168.10.80",
        "src_ip": "203.0.113.0/24",
    },
    {
        "_id": "v1-pf-004",
        "name": "Disabled FTP",
        "enabled": False,
        "proto": "tcp",
        "src": "21",
        "fwd_port": "21",
        "fwd": "192.168.10.100",
        "src_ip": "",
    },
]


# =============================================================================
# Helper Functions for Creating Mock Responses
# =============================================================================

def create_v2_security_data_response(
    data: Any,
    feature: str,
    controller_type: ControllerType = ControllerType.UNIFI_OS
) -> Dict[str, Any]:
    """Create a mock get_security_data response for v2 API (UniFi OS).
    
    Args:
        data: Raw v2 API response data
        feature: Feature name (firewall_rules, ips_status, etc.)
        controller_type: Controller type (default: UNIFI_OS)
    
    Returns:
        Mock response dictionary matching get_security_data format
    """
    normalizer = ResponseNormalizer()
    
    # Normalize the data based on feature type
    if feature == "firewall_rules":
        normalized = normalizer.normalize_firewall_rules(data, controller_type)
        normalized_data = [asdict(rule) for rule in normalized]
    elif feature == "ips_status":
        normalized = normalizer.normalize_ips_status(data, controller_type)
        normalized_data = asdict(normalized)
    elif feature == "traffic_routes":
        normalized = normalizer.normalize_traffic_routes(data, controller_type)
        normalized_data = [asdict(route) for route in normalized]
    elif feature == "port_forwards":
        normalized = normalizer.normalize_port_forwards(data, controller_type)
        normalized_data = [asdict(pf) for pf in normalized]
    else:
        normalized_data = data
    
    # Build endpoint based on feature
    # Note: As of UniFi Network API 10.0.160, all security features use v1 REST API
    endpoint_map = {
        "firewall_rules": "/api/s/default/rest/firewallrule",
        "ips_status": "/api/s/default/rest/setting/ips",
        "traffic_routes": "/api/s/default/rest/routing",
        "port_forwards": "/api/s/default/rest/portforward",
    }
    
    return {
        "data": normalized_data,
        "api_version": "v1",  # All security features use v1 REST API
        "controller_type": controller_type.value,
        "endpoint_used": endpoint_map.get(feature, f"/api/s/default/rest/{feature}"),
        "fallback_used": False,
    }


def create_v1_security_data_response(
    data: Any,
    feature: str,
    controller_type: ControllerType = ControllerType.TRADITIONAL
) -> Dict[str, Any]:
    """Create a mock get_security_data response for v1 API (Traditional).
    
    Args:
        data: Raw v1 API response data
        feature: Feature name (firewall_rules, ips_status, etc.)
        controller_type: Controller type (default: TRADITIONAL)
    
    Returns:
        Mock response dictionary matching get_security_data format
    """
    normalizer = ResponseNormalizer()
    
    # Normalize the data based on feature type
    if feature == "firewall_rules":
        normalized = normalizer.normalize_firewall_rules(data, controller_type)
        normalized_data = [asdict(rule) for rule in normalized]
    elif feature == "ips_status":
        normalized = normalizer.normalize_ips_status(data, controller_type)
        normalized_data = asdict(normalized)
    elif feature == "traffic_routes":
        normalized = normalizer.normalize_traffic_routes(data, controller_type)
        normalized_data = [asdict(route) for route in normalized]
    elif feature == "port_forwards":
        normalized = normalizer.normalize_port_forwards(data, controller_type)
        normalized_data = [asdict(pf) for pf in normalized]
    else:
        normalized_data = data
    
    # Build endpoint based on feature
    endpoint_map = {
        "firewall_rules": "/api/s/default/rest/firewallrule",
        "ips_status": "/api/s/default/rest/setting/ips",
        "traffic_routes": "/api/s/default/rest/routing",
        "port_forwards": "/api/s/default/rest/portforward",
    }
    
    return {
        "data": normalized_data,
        "api_version": "v1",
        "controller_type": controller_type.value,
        "endpoint_used": endpoint_map.get(feature, f"/api/s/default/rest/{feature}"),
        "fallback_used": False,
    }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_unifi_client_v2():
    """Create a mock UniFi client configured for UniFi OS (v2 API)."""
    client = MagicMock(spec=UniFiClient)
    client.get = AsyncMock()
    client.get_security_data = AsyncMock()
    
    # Configure as UniFi OS controller
    client.controller_type = ControllerType.UNIFI_OS
    
    return client


@pytest.fixture
def mock_unifi_client_v1():
    """Create a mock UniFi client configured for traditional controller (v1 API)."""
    client = MagicMock(spec=UniFiClient)
    client.get = AsyncMock()
    client.get_security_data = AsyncMock()
    
    # Configure as traditional controller
    client.controller_type = ControllerType.TRADITIONAL
    
    return client


# =============================================================================
# Integration Tests for UniFi OS (v2 API)
# =============================================================================

class TestUniFiOSFirewallRulesIntegration:
    """Integration tests for firewall rules on UniFi OS (v2 API).
    
    Validates: Requirements 2.1 - v2 endpoint usage for firewall rules
    """
    
    @pytest.mark.asyncio
    async def test_list_firewall_rules_v2_full_flow(self, mock_unifi_client_v2):
        """Test full flow from tool call to normalized response for UniFi OS firewall rules.
        
        Note: As of UniFi Network API 10.0.160, all security features use v1 REST API.
        
        Validates: Requirements 2.1, 2.3, 2.4
        """
        # Setup mock response with v2 data (normalized to v1 API format)
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_FIREWALL_RULES, "firewall_rules"
        )
        
        # Execute tool
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client_v2)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert result["count"] == 4
        assert result["api_version"] == "v1"  # All security features use v1 REST API
        assert result["controller_type"] == "unifi_os"
        
        # Verify correct endpoint was called
        mock_unifi_client_v2.get_security_data.assert_called_once_with("firewall_rules")
        
        # Verify normalized data format
        rules = result["data"]
        assert len(rules) == 4
        
        # Check first rule has expected normalized fields
        first_rule = rules[0]
        assert first_rule["id"] == "v2-rule-001"
        assert first_rule["name"] == "Allow Core to Internet"
        assert first_rule["enabled"] is True
        assert first_rule["action"] == "ALLOW"
        assert first_rule["protocol"] == "ALL"
        # Note: The normalized data's api_version indicates the data format (v2 for UniFi OS)
        # The response metadata's api_version indicates the endpoint used (v1 REST API)
        assert first_rule["api_version"] == "v2"  # Data format is v2 (UniFi OS)
    
    @pytest.mark.asyncio
    async def test_list_firewall_rules_v2_enabled_filter(self, mock_unifi_client_v2):
        """Test enabled_only filter works correctly with v2 API.
        
        Validates: Requirements 2.5
        """
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_FIREWALL_RULES, "firewall_rules"
        )
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client_v2, enabled_only=True)
        
        # Should only return enabled rules (3 out of 4)
        assert result["success"] is True
        assert result["count"] == 3
        assert all(rule["enabled"] is True for rule in result["data"])
    
    @pytest.mark.asyncio
    async def test_get_firewall_rule_details_v2(self, mock_unifi_client_v2):
        """Test getting specific rule details from UniFi OS.
        
        Note: As of UniFi Network API 10.0.160, all security features use v1 REST API.
        
        Validates: Requirements 2.3
        """
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_FIREWALL_RULES, "firewall_rules"
        )
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client_v2, rule_id="v2-rule-002")
        
        assert result["success"] is True
        assert result["type"] == "firewall_rule"
        
        rule = result["data"]
        assert rule["id"] == "v2-rule-002"
        assert rule["name"] == "Block IoT to Core"
        assert rule["action"] == "DENY"
        assert rule["logging"] is True
        # Note: The normalized data's api_version indicates the data format (v2 for UniFi OS)
        assert rule["api_version"] == "v2"  # Data format is v2 (UniFi OS)


class TestUniFiOSIPSIntegration:
    """Integration tests for IPS/threat management on UniFi OS (v2 API).
    
    Validates: Requirements 3.1 - v2 endpoint usage for IPS status
    """
    
    @pytest.mark.asyncio
    async def test_ips_status_v2_enabled(self, mock_unifi_client_v2):
        """Test IPS status retrieval from UniFi OS when enabled.
        
        Note: As of UniFi Network API 10.0.160, all security features use v1 REST API.
        
        Validates: Requirements 3.1, 3.3, 3.5
        """
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_THREAT_MANAGEMENT, "ips_status"
        )
        
        # Mock the alerts endpoint (IPS tool fetches alerts separately)
        mock_unifi_client_v2.get.return_value = {"data": []}
        
        # Import IPS tool from security module
        from unifi_mcp.tools.security import GetIPSStatusTool
        
        tool = GetIPSStatusTool()
        result = await tool.execute(mock_unifi_client_v2)
        
        assert result["success"] is True
        
        # Verify IPS is correctly reported as enabled
        # Note: The tool formats enabled as "yes"/"no" string for AI consumption
        ips_data = result["data"]
        assert ips_data["enabled"] == "yes"
        assert ips_data["protection_mode"] == "prevention"
        # Note: The normalized data's api_version indicates the data format (v2 for UniFi OS)
        assert ips_data["api_version"] == "v2"  # Data format is v2 (UniFi OS)
        
        # Verify statistics are included
        assert "threat_statistics" in ips_data
        assert ips_data["threat_statistics"]["blocked_threats"] == 42


class TestUniFiOSTrafficRoutesIntegration:
    """Integration tests for traffic routes on UniFi OS (v2 API).
    
    Validates: Requirements 4.1 - v2 endpoint usage for traffic routes
    """
    
    @pytest.mark.asyncio
    async def test_list_traffic_routes_v2_full_flow(self, mock_unifi_client_v2):
        """Test full flow from tool call to normalized response for UniFi OS traffic routes.
        
        Note: As of UniFi Network API 10.0.160, all security features use v1 REST API.
        
        Validates: Requirements 4.1, 4.3
        """
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_TRAFFIC_ROUTES, "traffic_routes"
        )
        
        tool = ListTrafficRoutesTool()
        result = await tool.execute(mock_unifi_client_v2)
        
        assert result["success"] is True
        assert result["count"] == 3
        assert result["api_version"] == "v1"  # All security features use v1 REST API
        
        # Verify normalized data format
        routes = result["data"]
        first_route = routes[0]
        assert first_route["id"] == "v2-route-001"
        assert first_route["name"] == "VPN Route to Remote Office"
        assert first_route["enabled"] is True
        assert first_route["type"] == "policy"  # Tool uses "type" not "route_type"
        # Note: The normalized data's api_version indicates the data format (v2 for UniFi OS)
        assert first_route["api_version"] == "v2"  # Data format is v2 (UniFi OS)
    
    @pytest.mark.asyncio
    async def test_list_traffic_routes_v2_enabled_filter(self, mock_unifi_client_v2):
        """Test enabled_only filter works correctly with v2 traffic routes.
        
        Validates: Requirements 4.4
        """
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_TRAFFIC_ROUTES, "traffic_routes"
        )
        
        tool = ListTrafficRoutesTool()
        result = await tool.execute(mock_unifi_client_v2, enabled_only=True)
        
        # Should only return enabled routes (2 out of 3)
        assert result["success"] is True
        assert result["count"] == 2
        assert all(route["enabled"] is True for route in result["data"])


class TestUniFiOSPortForwardsIntegration:
    """Integration tests for port forwards on UniFi OS (v2 API).
    
    Validates: Requirements 5.1 - v2 endpoint usage for port forwards
    """
    
    @pytest.mark.asyncio
    async def test_list_port_forwards_v2_full_flow(self, mock_unifi_client_v2):
        """Test full flow from tool call to normalized response for UniFi OS port forwards.
        
        Note: As of UniFi Network API 10.0.160, all security features use v1 REST API.
        
        Validates: Requirements 5.1, 5.3
        """
        # Import port forward tool
        from unifi_mcp.tools.security import ListPortForwardsTool
        
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_PORT_FORWARDS, "port_forwards"
        )
        
        tool = ListPortForwardsTool()
        result = await tool.execute(mock_unifi_client_v2)
        
        assert result["success"] is True
        assert result["count"] == 4
        assert result["api_version"] == "v1"  # All security features use v1 REST API
        
        # Verify normalized data format
        forwards = result["data"]
        first_pf = forwards[0]
        assert first_pf["id"] == "v2-pf-001"
        assert first_pf["name"] == "Web Server HTTPS"
        assert first_pf["enabled"] is True
        assert first_pf["protocol"] == "TCP"
        assert first_pf["external_port"] == "443"  # Tool uses "external_port" not "source_port"
        assert first_pf["destination_ip"] == "192.168.10.50"
        # Note: The normalized data's api_version indicates the data format (v2 for UniFi OS)
        assert first_pf["api_version"] == "v2"  # Data format is v2 (UniFi OS)
    
    @pytest.mark.asyncio
    async def test_list_port_forwards_v2_enabled_filter(self, mock_unifi_client_v2):
        """Test enabled_only filter works correctly with v2 port forwards.
        
        Validates: Requirements 5.4
        """
        from unifi_mcp.tools.security import ListPortForwardsTool
        
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_PORT_FORWARDS, "port_forwards"
        )
        
        tool = ListPortForwardsTool()
        result = await tool.execute(mock_unifi_client_v2, enabled_only=True)
        
        # Should only return enabled port forwards (3 out of 4)
        assert result["success"] is True
        assert result["count"] == 3
        assert all(pf["enabled"] is True for pf in result["data"])


# =============================================================================
# Backward Compatibility Tests (Traditional Controller - v1 API)
# =============================================================================

class TestTraditionalControllerFirewallRulesIntegration:
    """Integration tests for firewall rules on traditional controller (v1 API).
    
    Validates: Requirements 7.1 - Backward compatibility with traditional controllers
    """
    
    @pytest.mark.asyncio
    async def test_list_firewall_rules_v1_full_flow(self, mock_unifi_client_v1):
        """Test full flow from tool call to normalized response for v1 firewall rules.
        
        Validates: Requirements 7.1, 7.4
        """
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_FIREWALL_RULES, "firewall_rules"
        )
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client_v1)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert result["count"] == 4
        assert result["api_version"] == "v1"
        assert result["controller_type"] == "traditional"
        
        # Verify correct endpoint was called
        mock_unifi_client_v1.get_security_data.assert_called_once_with("firewall_rules")
        
        # Verify normalized data format matches v2 format
        rules = result["data"]
        assert len(rules) == 4
        
        # Check first rule has expected normalized fields (same as v2)
        first_rule = rules[0]
        assert first_rule["id"] == "v1-rule-001"
        assert first_rule["name"] == "Allow Core to Internet"
        assert first_rule["enabled"] is True
        assert first_rule["action"] == "ALLOW"  # Normalized from "accept"
        assert first_rule["protocol"] == "ALL"  # Normalized from "all"
        assert first_rule["api_version"] == "v1"
    
    @pytest.mark.asyncio
    async def test_list_firewall_rules_v1_enabled_filter(self, mock_unifi_client_v1):
        """Test enabled_only filter works correctly with v1 API.
        
        Validates: Requirements 2.5, 7.1
        """
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_FIREWALL_RULES, "firewall_rules"
        )
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client_v1, enabled_only=True)
        
        # Should only return enabled rules (3 out of 4)
        assert result["success"] is True
        assert result["count"] == 3
        assert all(rule["enabled"] is True for rule in result["data"])
    
    @pytest.mark.asyncio
    async def test_get_firewall_rule_details_v1(self, mock_unifi_client_v1):
        """Test getting specific rule details from v1 API.
        
        Validates: Requirements 7.1, 7.4
        """
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_FIREWALL_RULES, "firewall_rules"
        )
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client_v1, rule_id="v1-rule-002")
        
        assert result["success"] is True
        assert result["type"] == "firewall_rule"
        
        rule = result["data"]
        assert rule["id"] == "v1-rule-002"
        assert rule["name"] == "Block IoT to Core"
        assert rule["action"] == "DENY"  # Normalized from "drop"
        assert rule["logging"] is True
        assert rule["api_version"] == "v1"


class TestTraditionalControllerIPSIntegration:
    """Integration tests for IPS on traditional controller (v1 API).
    
    Validates: Requirements 7.1 - Backward compatibility with traditional controllers
    """
    
    @pytest.mark.asyncio
    async def test_ips_status_v1_enabled(self, mock_unifi_client_v1):
        """Test IPS status retrieval from v1 API when enabled.
        
        Validates: Requirements 7.1, 7.4
        """
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_IPS_SETTINGS, "ips_status"
        )
        
        # Mock the alerts endpoint (IPS tool fetches alerts separately)
        mock_unifi_client_v1.get.return_value = {"data": []}
        
        from unifi_mcp.tools.security import GetIPSStatusTool
        
        tool = GetIPSStatusTool()
        result = await tool.execute(mock_unifi_client_v1)
        
        assert result["success"] is True
        
        # Verify IPS is correctly reported as enabled
        # Note: The tool formats enabled as "yes"/"no" string for AI consumption
        ips_data = result["data"]
        assert ips_data["enabled"] == "yes"
        assert ips_data["protection_mode"] == "prevention"  # Normalized from "ips"
        assert ips_data["api_version"] == "v1"


class TestTraditionalControllerTrafficRoutesIntegration:
    """Integration tests for traffic routes on traditional controller (v1 API).
    
    Validates: Requirements 7.1 - Backward compatibility with traditional controllers
    """
    
    @pytest.mark.asyncio
    async def test_list_traffic_routes_v1_full_flow(self, mock_unifi_client_v1):
        """Test full flow from tool call to normalized response for v1 traffic routes.
        
        Validates: Requirements 7.1, 7.4
        """
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_ROUTING, "traffic_routes"
        )
        
        tool = ListTrafficRoutesTool()
        result = await tool.execute(mock_unifi_client_v1)
        
        assert result["success"] is True
        assert result["count"] == 3
        assert result["api_version"] == "v1"
        
        # Verify normalized data format matches v2 format
        routes = result["data"]
        first_route = routes[0]
        assert first_route["id"] == "v1-route-001"
        assert first_route["name"] == "VPN Route to Remote Office"
        assert first_route["enabled"] is True
        assert first_route["type"] == "policy"  # Tool uses "type" not "route_type"
        assert first_route["api_version"] == "v1"


class TestTraditionalControllerPortForwardsIntegration:
    """Integration tests for port forwards on traditional controller (v1 API).
    
    Validates: Requirements 7.1 - Backward compatibility with traditional controllers
    """
    
    @pytest.mark.asyncio
    async def test_list_port_forwards_v1_full_flow(self, mock_unifi_client_v1):
        """Test full flow from tool call to normalized response for v1 port forwards.
        
        Validates: Requirements 7.1, 7.4
        """
        from unifi_mcp.tools.security import ListPortForwardsTool
        
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_PORT_FORWARDS, "port_forwards"
        )
        
        tool = ListPortForwardsTool()
        result = await tool.execute(mock_unifi_client_v1)
        
        assert result["success"] is True
        assert result["count"] == 4
        assert result["api_version"] == "v1"
        
        # Verify normalized data format matches v2 format
        forwards = result["data"]
        first_pf = forwards[0]
        assert first_pf["id"] == "v1-pf-001"
        assert first_pf["name"] == "Web Server HTTPS"
        assert first_pf["enabled"] is True
        assert first_pf["protocol"] == "TCP"  # Normalized from "tcp"
        assert first_pf["external_port"] == "443"  # Tool uses "external_port" not "source_port"
        assert first_pf["destination_ip"] == "192.168.10.50"
        assert first_pf["api_version"] == "v1"


# =============================================================================
# Response Format Consistency Tests
# =============================================================================

class TestResponseFormatConsistency:
    """Tests to verify response format is consistent between v1 and v2 APIs.
    
    Validates: Requirements 7.4 - Consistent tool output regardless of API version
    """
    
    @pytest.mark.asyncio
    async def test_firewall_rules_format_consistency(
        self, mock_unifi_client_v1, mock_unifi_client_v2
    ):
        """Verify firewall rules have same normalized fields for v1 and v2.
        
        Validates: Requirements 7.4
        """
        # Get v2 response
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_FIREWALL_RULES, "firewall_rules"
        )
        tool = ListFirewallRulesTool()
        v2_result = await tool.execute(mock_unifi_client_v2)
        
        # Get v1 response
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_FIREWALL_RULES, "firewall_rules"
        )
        v1_result = await tool.execute(mock_unifi_client_v1)
        
        # Both should have same top-level structure
        assert set(v2_result.keys()) == set(v1_result.keys())
        
        # Both should have same fields in rule data (except api_version value)
        v2_rule_fields = set(v2_result["data"][0].keys())
        v1_rule_fields = set(v1_result["data"][0].keys())
        assert v2_rule_fields == v1_rule_fields
        
        # Verify common required fields exist
        required_fields = {
            "id", "name", "enabled", "action", "protocol",
            "source_zone", "destination_zone", "source_address",
            "destination_address", "destination_port", "logging", "api_version"
        }
        assert required_fields.issubset(v2_rule_fields)
        assert required_fields.issubset(v1_rule_fields)
    
    @pytest.mark.asyncio
    async def test_traffic_routes_format_consistency(
        self, mock_unifi_client_v1, mock_unifi_client_v2
    ):
        """Verify traffic routes have same normalized fields for v1 and v2.
        
        Validates: Requirements 7.4
        """
        # Get v2 response
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_TRAFFIC_ROUTES, "traffic_routes"
        )
        tool = ListTrafficRoutesTool()
        v2_result = await tool.execute(mock_unifi_client_v2)
        
        # Get v1 response
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_ROUTING, "traffic_routes"
        )
        v1_result = await tool.execute(mock_unifi_client_v1)
        
        # Both should have same fields in route data
        v2_route_fields = set(v2_result["data"][0].keys())
        v1_route_fields = set(v1_result["data"][0].keys())
        assert v2_route_fields == v1_route_fields
        
        # Verify common required fields exist (tool uses "type" not "route_type")
        required_fields = {
            "id", "name", "enabled", "type",
            "destination_network", "next_hop", "interface", "distance", "api_version"
        }
        assert required_fields.issubset(v2_route_fields)
        assert required_fields.issubset(v1_route_fields)
    
    @pytest.mark.asyncio
    async def test_port_forwards_format_consistency(
        self, mock_unifi_client_v1, mock_unifi_client_v2
    ):
        """Verify port forwards have same normalized fields for v1 and v2.
        
        Validates: Requirements 7.4
        """
        from unifi_mcp.tools.security import ListPortForwardsTool
        
        # Get v2 response
        mock_unifi_client_v2.get_security_data.return_value = create_v2_security_data_response(
            MOCK_V2_PORT_FORWARDS, "port_forwards"
        )
        tool = ListPortForwardsTool()
        v2_result = await tool.execute(mock_unifi_client_v2)
        
        # Get v1 response
        mock_unifi_client_v1.get_security_data.return_value = create_v1_security_data_response(
            MOCK_V1_PORT_FORWARDS, "port_forwards"
        )
        v1_result = await tool.execute(mock_unifi_client_v1)
        
        # Both should have same fields in port forward data
        v2_pf_fields = set(v2_result["data"][0].keys())
        v1_pf_fields = set(v1_result["data"][0].keys())
        assert v2_pf_fields == v1_pf_fields
        
        # Verify common required fields exist (tool uses "external_port" not "source_port")
        required_fields = {
            "id", "name", "enabled", "protocol",
            "external_port", "destination_port", "destination_ip", "source_ip", "api_version"
        }
        assert required_fields.issubset(v2_pf_fields)
        assert required_fields.issubset(v1_pf_fields)


# =============================================================================
# Endpoint Routing Verification Tests
# =============================================================================

class TestEndpointRoutingVerification:
    """Tests to verify correct endpoints are called based on controller type.
    
    Note: As of UniFi Network API 10.0.160, all security features use v1 REST API
    for both UniFi OS and traditional controllers.
    
    Validates: Requirements 2.1, 3.1, 4.1, 5.1
    """
    
    def test_endpoint_router_selects_v1_for_unifi_os(self):
        """Verify EndpointRouter selects v1 REST API endpoints for UniFi OS.
        
        Note: The official v2 API does not yet expose security settings.
        
        Validates: Requirements 2.1, 3.1, 4.1, 5.1
        """
        router = EndpointRouter()
        
        # Test all security features
        features = ["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]
        
        for feature in features:
            endpoint = router.get_endpoint(feature, ControllerType.UNIFI_OS)
            assert "/rest/" in endpoint or "/setting/" in endpoint, \
                f"Expected v1 REST API endpoint for {feature} on UniFi OS, got {endpoint}"
            assert endpoint.startswith("/api/s/"), \
                f"Expected v1 REST API pattern for {feature}, got {endpoint}"
    
    def test_endpoint_router_selects_v1_for_traditional(self):
        """Verify EndpointRouter selects v1 endpoints for traditional controller.
        
        Validates: Requirements 2.2, 3.2, 4.2, 5.2
        """
        router = EndpointRouter()
        
        # Test all security features
        features = ["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]
        
        for feature in features:
            endpoint = router.get_endpoint(feature, ControllerType.TRADITIONAL)
            assert "/rest/" in endpoint or "/setting/" in endpoint, \
                f"Expected v1 endpoint for {feature} on traditional, got {endpoint}"
            assert endpoint.startswith("/api/s/"), \
                f"Expected v1 REST API pattern for {feature}, got {endpoint}"
    
    def test_endpoint_router_same_endpoints_both_controllers(self):
        """Verify EndpointRouter uses same endpoints for both controller types.
        
        Note: The official v2 API does not yet expose security settings,
        so both controller types use the same v1 REST API endpoints.
        
        Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2
        """
        router = EndpointRouter()
        
        # Test all security features
        features = ["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]
        
        for feature in features:
            unifi_os_endpoint = router.get_endpoint(feature, ControllerType.UNIFI_OS)
            traditional_endpoint = router.get_endpoint(feature, ControllerType.TRADITIONAL)
            assert unifi_os_endpoint == traditional_endpoint, \
                f"Expected same endpoint for {feature} on both controller types"
    
    def test_endpoint_router_handles_unknown_controller(self):
        """Verify EndpointRouter defaults to v1 for unknown controller type.
        
        Validates: Requirements 1.4
        """
        router = EndpointRouter()
        
        # Unknown should default to traditional (v1)
        endpoint = router.get_endpoint("firewall_rules", ControllerType.UNKNOWN)
        assert "/rest/" in endpoint, \
            "Expected v1 endpoint for unknown controller type"


# =============================================================================
# Normalization Verification Tests
# =============================================================================

class TestNormalizationVerification:
    """Tests to verify response normalization works correctly.
    
    Validates: Requirements 2.3, 3.3, 4.3, 5.3, 7.4
    """
    
    def test_normalize_v2_firewall_rules(self):
        """Verify v2 firewall rules are normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_firewall_rules(
            MOCK_V2_FIREWALL_RULES, ControllerType.UNIFI_OS
        )
        
        assert len(normalized) == 4
        
        # Check first rule
        rule = normalized[0]
        assert isinstance(rule, NormalizedFirewallRule)
        assert rule.id == "v2-rule-001"
        assert rule.name == "Allow Core to Internet"
        assert rule.enabled is True
        assert rule.action == "ALLOW"
        assert rule.protocol == "ALL"
        assert rule.api_version == "v2"
    
    def test_normalize_v1_firewall_rules(self):
        """Verify v1 firewall rules are normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_firewall_rules(
            MOCK_V1_FIREWALL_RULES, ControllerType.TRADITIONAL
        )
        
        assert len(normalized) == 4
        
        # Check first rule - action should be normalized
        rule = normalized[0]
        assert isinstance(rule, NormalizedFirewallRule)
        assert rule.id == "v1-rule-001"
        assert rule.action == "ALLOW"  # Normalized from "accept"
        assert rule.protocol == "ALL"  # Normalized from "all"
        assert rule.api_version == "v1"
    
    def test_normalize_v2_ips_status(self):
        """Verify v2 IPS status is normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_ips_status(
            MOCK_V2_THREAT_MANAGEMENT, ControllerType.UNIFI_OS
        )
        
        assert isinstance(normalized, NormalizedIPSStatus)
        assert normalized.enabled is True
        assert normalized.enabled_display == "yes"
        assert normalized.protection_mode == "prevention"
        assert normalized.api_version == "v2"
        assert normalized.threat_statistics["blocked_threats"] == 42
    
    def test_normalize_v1_ips_status(self):
        """Verify v1 IPS status is normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_ips_status(
            MOCK_V1_IPS_SETTINGS, ControllerType.TRADITIONAL
        )
        
        assert isinstance(normalized, NormalizedIPSStatus)
        assert normalized.enabled is True
        assert normalized.enabled_display == "yes"
        assert normalized.protection_mode == "prevention"  # Normalized from "ips"
        assert normalized.api_version == "v1"
    
    def test_normalize_v2_traffic_routes(self):
        """Verify v2 traffic routes are normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_traffic_routes(
            MOCK_V2_TRAFFIC_ROUTES, ControllerType.UNIFI_OS
        )
        
        assert len(normalized) == 3
        
        route = normalized[0]
        assert isinstance(route, NormalizedTrafficRoute)
        assert route.id == "v2-route-001"
        assert route.route_type == "policy"
        assert route.api_version == "v2"
    
    def test_normalize_v2_port_forwards(self):
        """Verify v2 port forwards are normalized correctly."""
        normalizer = ResponseNormalizer()
        
        normalized = normalizer.normalize_port_forwards(
            MOCK_V2_PORT_FORWARDS, ControllerType.UNIFI_OS
        )
        
        assert len(normalized) == 4
        
        pf = normalized[0]
        assert isinstance(pf, NormalizedPortForward)
        assert pf.id == "v2-pf-001"
        assert pf.protocol == "TCP"
        assert pf.api_version == "v2"
