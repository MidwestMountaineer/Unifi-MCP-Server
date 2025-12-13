"""Tests for response normalization.

This module contains unit tests and property-based tests for the
ResponseNormalizer class and normalized data structures.
"""

import pytest
from hypothesis import given, settings, strategies as st, Phase, assume, HealthCheck
from dataclasses import asdict

from unifi_mcp.api.controller_detector import ControllerType
from unifi_mcp.api.response_normalizer import (
    ResponseNormalizer,
    NormalizedFirewallRule,
    NormalizedIPSStatus,
    NormalizedTrafficRoute,
    NormalizedPortForward,
)


# Configure hypothesis for minimum 100 iterations with health check suppression
settings.register_profile(
    "unifi_mcp",
    max_examples=100,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink],
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("unifi_mcp")


# ============================================================================
# Hypothesis Strategies for generating test data
# ============================================================================

# Strategy for generating v1 firewall rule data
firewall_rule_v1_strategy = st.fixed_dictionaries({
    "_id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "name": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "action": st.sampled_from(["accept", "drop", "reject"]),
    "protocol": st.sampled_from(["all", "tcp", "udp", "tcp_udp", "icmp"]),
    "src_address": st.one_of(st.just(""), st.text(min_size=7, max_size=18, alphabet="0123456789./")),
    "dst_address": st.one_of(st.just(""), st.text(min_size=7, max_size=18, alphabet="0123456789./")),
    "dst_port": st.one_of(st.just(""), st.text(min_size=1, max_size=11, alphabet="0123456789,-")),
    "logging": st.booleans(),
    "ruleset": st.sampled_from(["WAN_IN", "WAN_OUT", "LAN_IN", "LAN_OUT", "GUEST_IN", ""]),
})

# Strategy for generating v2 firewall rule data
firewall_rule_v2_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "description": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "action": st.sampled_from(["ALLOW", "DENY", "REJECT"]),
    "ip_protocol": st.sampled_from(["all", "tcp", "udp", "tcp_udp", "icmp", "any"]),
    "source": st.fixed_dictionaries({
        "zone": st.sampled_from(["WAN", "LAN", "GUEST", ""]),
        "address": st.one_of(st.just(""), st.text(min_size=7, max_size=18, alphabet="0123456789./")),
    }),
    "destination": st.fixed_dictionaries({
        "zone": st.sampled_from(["WAN", "LAN", "GUEST", ""]),
        "address": st.one_of(st.just(""), st.text(min_size=7, max_size=18, alphabet="0123456789./")),
        "port": st.one_of(st.just(""), st.text(min_size=1, max_size=11, alphabet="0123456789,-")),
    }),
    "logging": st.booleans(),
    "matching_target": st.sampled_from(["INTERNET", "LOCAL", "INTERNAL", ""]),
})


# Strategy for generating v1 IPS status data
ips_status_v1_strategy = st.fixed_dictionaries({
    "ips_mode": st.sampled_from(["off", "ids", "ips"]),
})

# Strategy for generating v2 IPS status data
ips_status_v2_strategy = st.fixed_dictionaries({
    "enabled": st.booleans(),
    "mode": st.sampled_from(["detection", "prevention"]),
    "stats": st.fixed_dictionaries({
        "blocked": st.integers(min_value=0, max_value=10000),
        "detected": st.integers(min_value=0, max_value=10000),
    }),
    "alerts": st.lists(
        st.fixed_dictionaries({
            "id": st.text(min_size=8, max_size=8, alphabet="0123456789abcdef"),
            "severity": st.sampled_from(["low", "medium", "high", "critical"]),
        }),
        min_size=0,
        max_size=5
    ),
})

# Strategy for generating v1 traffic route data
traffic_route_v1_strategy = st.fixed_dictionaries({
    "_id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "name": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "type": st.sampled_from(["static", "policy"]),
    "static-route_network": st.text(min_size=9, max_size=18, alphabet="0123456789./"),
    "static-route_nexthop": st.text(min_size=7, max_size=15, alphabet="0123456789."),
    "static-route_interface": st.sampled_from(["eth0", "eth1", "br0", ""]),
    "static-route_distance": st.integers(min_value=1, max_value=255),
})

# Strategy for generating v2 traffic route data
traffic_route_v2_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "description": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "matching_target": st.sampled_from(["static", "policy_based", "internet", ""]),
    "destination": st.fixed_dictionaries({
        "network": st.text(min_size=9, max_size=18, alphabet="0123456789./"),
    }),
    "target_device": st.fixed_dictionaries({
        "ip": st.text(min_size=7, max_size=15, alphabet="0123456789."),
    }),
    "interface": st.fixed_dictionaries({
        "name": st.sampled_from(["eth0", "eth1", "br0", ""]),
    }),
    "distance": st.integers(min_value=1, max_value=255),
})

# Strategy for generating v1 port forward data
port_forward_v1_strategy = st.fixed_dictionaries({
    "_id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "name": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "proto": st.sampled_from(["tcp", "udp", "tcp_udp"]),
    "src": st.text(min_size=1, max_size=11, alphabet="0123456789,-"),
    "fwd_port": st.text(min_size=1, max_size=11, alphabet="0123456789,-"),
    "fwd": st.text(min_size=7, max_size=15, alphabet="0123456789."),
    "src_ip": st.one_of(st.just(""), st.text(min_size=7, max_size=15, alphabet="0123456789.")),
})

# Strategy for generating v2 port forward data
port_forward_v2_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=24, max_size=24, alphabet="0123456789abcdef"),
    "name": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "protocol": st.sampled_from(["TCP", "UDP", "TCP_UDP"]),
    "port": st.text(min_size=1, max_size=11, alphabet="0123456789,-"),
    "forward_port": st.text(min_size=1, max_size=11, alphabet="0123456789,-"),
    "forward_ip": st.text(min_size=7, max_size=15, alphabet="0123456789."),
    "source": st.fixed_dictionaries({
        "ip": st.one_of(st.just(""), st.text(min_size=7, max_size=15, alphabet="0123456789.")),
    }),
})



# ============================================================================
# Unit Tests for ResponseNormalizer
# ============================================================================

class TestResponseNormalizerInit:
    """Tests for ResponseNormalizer initialization."""
    
    def test_init_creates_logger(self):
        """Test that initialization creates a logger."""
        normalizer = ResponseNormalizer()
        assert normalizer._logger is not None


class TestNormalizedDataclasses:
    """Tests for normalized dataclass structures."""
    
    def test_normalized_firewall_rule_has_required_fields(self):
        """Test that NormalizedFirewallRule has all required fields."""
        rule = NormalizedFirewallRule(
            id="test123",
            name="Test Rule",
            enabled=True,
            action="ALLOW",
            protocol="TCP",
        )
        assert rule.id == "test123"
        assert rule.name == "Test Rule"
        assert rule.enabled is True
        assert rule.action == "ALLOW"
        assert rule.protocol == "TCP"
        assert rule.api_version == ""  # Default
    
    def test_normalized_ips_status_has_required_fields(self):
        """Test that NormalizedIPSStatus has all required fields."""
        status = NormalizedIPSStatus(
            enabled=True,
            enabled_display="yes",
            protection_mode="prevention",
        )
        assert status.enabled is True
        assert status.enabled_display == "yes"
        assert status.protection_mode == "prevention"
        assert status.threat_statistics == {}  # Default
    
    def test_normalized_traffic_route_has_required_fields(self):
        """Test that NormalizedTrafficRoute has all required fields."""
        route = NormalizedTrafficRoute(
            id="route123",
            name="Test Route",
            enabled=True,
            route_type="static",
        )
        assert route.id == "route123"
        assert route.name == "Test Route"
        assert route.enabled is True
        assert route.route_type == "static"
    
    def test_normalized_port_forward_has_required_fields(self):
        """Test that NormalizedPortForward has all required fields."""
        pf = NormalizedPortForward(
            id="pf123",
            name="Test Forward",
            enabled=True,
            protocol="TCP",
            source_port="80",
            destination_port="8080",
            destination_ip="192.168.1.100",
        )
        assert pf.id == "pf123"
        assert pf.name == "Test Forward"
        assert pf.enabled is True
        assert pf.protocol == "TCP"


class TestFirewallRuleNormalization:
    """Tests for firewall rule normalization."""
    
    def test_normalize_v1_firewall_rule(self):
        """Test normalizing a v1 firewall rule."""
        normalizer = ResponseNormalizer()
        v1_data = [{
            "_id": "abc123def456789012345678",
            "name": "Allow HTTP",
            "enabled": True,
            "action": "accept",
            "protocol": "tcp",
            "dst_port": "80",
            "logging": True,
        }]
        
        result = normalizer.normalize_firewall_rules(v1_data, ControllerType.TRADITIONAL)
        
        assert len(result) == 1
        assert result[0].id == "abc123def456789012345678"
        assert result[0].name == "Allow HTTP"
        assert result[0].enabled is True
        assert result[0].action == "ALLOW"
        assert result[0].protocol == "TCP"
        assert result[0].destination_port == "80"
        assert result[0].api_version == "v1"
    
    def test_normalize_v2_firewall_rule(self):
        """Test normalizing a v2 firewall rule."""
        normalizer = ResponseNormalizer()
        v2_data = [{
            "id": "abc123def456789012345678",
            "description": "Allow HTTP",
            "enabled": True,
            "action": "ALLOW",
            "ip_protocol": "tcp",
            "destination": {"port": "80"},
            "logging": True,
        }]
        
        result = normalizer.normalize_firewall_rules(v2_data, ControllerType.UNIFI_OS)
        
        assert len(result) == 1
        assert result[0].id == "abc123def456789012345678"
        assert result[0].name == "Allow HTTP"
        assert result[0].enabled is True
        assert result[0].action == "ALLOW"
        assert result[0].protocol == "TCP"
        assert result[0].destination_port == "80"
        assert result[0].api_version == "v2"
    
    def test_normalize_empty_firewall_rules(self):
        """Test normalizing empty firewall rules list."""
        normalizer = ResponseNormalizer()
        result = normalizer.normalize_firewall_rules([], ControllerType.TRADITIONAL)
        assert result == []


class TestIPSStatusNormalization:
    """Tests for IPS status normalization."""
    
    def test_normalize_v1_ips_enabled(self):
        """Test normalizing v1 IPS status when enabled."""
        normalizer = ResponseNormalizer()
        v1_data = {"ips_mode": "ips"}
        
        result = normalizer.normalize_ips_status(v1_data, ControllerType.TRADITIONAL)
        
        assert result.enabled is True
        assert result.enabled_display == "yes"
        assert result.protection_mode == "prevention"
        assert result.api_version == "v1"
    
    def test_normalize_v1_ips_disabled(self):
        """Test normalizing v1 IPS status when disabled."""
        normalizer = ResponseNormalizer()
        v1_data = {"ips_mode": "off"}
        
        result = normalizer.normalize_ips_status(v1_data, ControllerType.TRADITIONAL)
        
        assert result.enabled is False
        assert result.enabled_display == "no"
        assert result.protection_mode == "disabled"
    
    def test_normalize_v2_ips_enabled(self):
        """Test normalizing v2 IPS status when enabled."""
        normalizer = ResponseNormalizer()
        v2_data = {
            "enabled": True,
            "mode": "prevention",
            "stats": {"blocked": 100, "detected": 50},
        }
        
        result = normalizer.normalize_ips_status(v2_data, ControllerType.UNIFI_OS)
        
        assert result.enabled is True
        assert result.enabled_display == "yes"
        assert result.protection_mode == "prevention"
        assert result.threat_statistics == {"blocked": 100, "detected": 50}
        assert result.api_version == "v2"
    
    def test_normalize_v2_ips_disabled(self):
        """Test normalizing v2 IPS status when disabled."""
        normalizer = ResponseNormalizer()
        v2_data = {"enabled": False, "mode": "detection"}
        
        result = normalizer.normalize_ips_status(v2_data, ControllerType.UNIFI_OS)
        
        assert result.enabled is False
        assert result.enabled_display == "no"


class TestTrafficRouteNormalization:
    """Tests for traffic route normalization."""
    
    def test_normalize_v1_traffic_route(self):
        """Test normalizing a v1 traffic route."""
        normalizer = ResponseNormalizer()
        v1_data = [{
            "_id": "route123456789012345678",
            "name": "Static Route",
            "enabled": True,
            "type": "static",
            "static-route_network": "10.0.0.0/24",
            "static-route_nexthop": "192.168.1.1",
            "static-route_distance": 10,
        }]
        
        result = normalizer.normalize_traffic_routes(v1_data, ControllerType.TRADITIONAL)
        
        assert len(result) == 1
        assert result[0].id == "route123456789012345678"
        assert result[0].name == "Static Route"
        assert result[0].enabled is True
        assert result[0].route_type == "static"
        assert result[0].destination_network == "10.0.0.0/24"
        assert result[0].next_hop == "192.168.1.1"
        assert result[0].api_version == "v1"
    
    def test_normalize_v2_traffic_route(self):
        """Test normalizing a v2 traffic route."""
        normalizer = ResponseNormalizer()
        v2_data = [{
            "id": "route123456789012345678",
            "description": "Static Route",
            "enabled": True,
            "matching_target": "static",
            "destination": {"network": "10.0.0.0/24"},
            "target_device": {"ip": "192.168.1.1"},
            "distance": 10,
        }]
        
        result = normalizer.normalize_traffic_routes(v2_data, ControllerType.UNIFI_OS)
        
        assert len(result) == 1
        assert result[0].id == "route123456789012345678"
        assert result[0].name == "Static Route"
        assert result[0].enabled is True
        assert result[0].route_type == "static"
        assert result[0].destination_network == "10.0.0.0/24"
        assert result[0].next_hop == "192.168.1.1"
        assert result[0].api_version == "v2"


class TestPortForwardNormalization:
    """Tests for port forward normalization."""
    
    def test_normalize_v1_port_forward(self):
        """Test normalizing a v1 port forward."""
        normalizer = ResponseNormalizer()
        v1_data = [{
            "_id": "pf123456789012345678901",
            "name": "Web Server",
            "enabled": True,
            "proto": "tcp",
            "src": "80",
            "fwd_port": "8080",
            "fwd": "192.168.1.100",
        }]
        
        result = normalizer.normalize_port_forwards(v1_data, ControllerType.TRADITIONAL)
        
        assert len(result) == 1
        assert result[0].id == "pf123456789012345678901"
        assert result[0].name == "Web Server"
        assert result[0].enabled is True
        assert result[0].protocol == "TCP"
        assert result[0].source_port == "80"
        assert result[0].destination_port == "8080"
        assert result[0].destination_ip == "192.168.1.100"
        assert result[0].api_version == "v1"
    
    def test_normalize_v2_port_forward(self):
        """Test normalizing a v2 port forward."""
        normalizer = ResponseNormalizer()
        v2_data = [{
            "id": "pf123456789012345678901",
            "name": "Web Server",
            "enabled": True,
            "protocol": "TCP",
            "port": "80",
            "forward_port": "8080",
            "forward_ip": "192.168.1.100",
        }]
        
        result = normalizer.normalize_port_forwards(v2_data, ControllerType.UNIFI_OS)
        
        assert len(result) == 1
        assert result[0].id == "pf123456789012345678901"
        assert result[0].name == "Web Server"
        assert result[0].enabled is True
        assert result[0].protocol == "TCP"
        assert result[0].source_port == "80"
        assert result[0].destination_port == "8080"
        assert result[0].destination_ip == "192.168.1.100"
        assert result[0].api_version == "v2"


class TestToDictMethods:
    """Tests for to_dict conversion methods."""
    
    def test_to_dict_firewall_rule(self):
        """Test converting firewall rule to dict."""
        normalizer = ResponseNormalizer()
        rule = NormalizedFirewallRule(
            id="test123",
            name="Test Rule",
            enabled=True,
            action="ALLOW",
            protocol="TCP",
        )
        
        result = normalizer.to_dict(rule)
        
        assert isinstance(result, dict)
        assert result["id"] == "test123"
        assert result["name"] == "Test Rule"
        assert result["enabled"] is True
    
    def test_to_dict_list(self):
        """Test converting list of rules to dicts."""
        normalizer = ResponseNormalizer()
        rules = [
            NormalizedFirewallRule(id="1", name="Rule 1", enabled=True, action="ALLOW", protocol="TCP"),
            NormalizedFirewallRule(id="2", name="Rule 2", enabled=False, action="DENY", protocol="UDP"),
        ]
        
        result = normalizer.to_dict_list(rules)
        
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"



# ============================================================================
# Property-Based Tests for ResponseNormalizer
# ============================================================================

class TestResponseNormalizerPropertyTests:
    """Property-based tests for ResponseNormalizer.
    
    These tests verify universal properties that should hold across all inputs.
    """
    
    @given(rules=st.lists(firewall_rule_v1_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v1_firewall_normalization_preserves_count(self, rules):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 2.3, 2.4, 7.4**
        
        For any list of v1 firewall rules, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.TRADITIONAL)
        assert len(normalized) == len(rules)
    
    @given(rules=st.lists(firewall_rule_v2_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v2_firewall_normalization_preserves_count(self, rules):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 2.3, 2.4, 7.4**
        
        For any list of v2 firewall rules, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.UNIFI_OS)
        assert len(normalized) == len(rules)
    
    @given(rule=firewall_rule_v1_strategy)
    @settings(max_examples=100)
    def test_v1_firewall_normalization_has_required_fields(self, rule):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 2.3, 2.4, 7.4**
        
        For any v1 firewall rule, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules([rule], ControllerType.TRADITIONAL)
        
        assert len(normalized) == 1
        result = normalized[0]
        
        # Check required fields exist and have correct types
        assert isinstance(result.id, str)
        assert isinstance(result.name, str)
        assert isinstance(result.enabled, bool)
        assert isinstance(result.action, str)
        assert isinstance(result.protocol, str)
        assert result.api_version == "v1"
    
    @given(rule=firewall_rule_v2_strategy)
    @settings(max_examples=100)
    def test_v2_firewall_normalization_has_required_fields(self, rule):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 2.3, 2.4, 7.4**
        
        For any v2 firewall rule, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules([rule], ControllerType.UNIFI_OS)
        
        assert len(normalized) == 1
        result = normalized[0]
        
        # Check required fields exist and have correct types
        assert isinstance(result.id, str)
        assert isinstance(result.name, str)
        assert isinstance(result.enabled, bool)
        assert isinstance(result.action, str)
        assert isinstance(result.protocol, str)
        assert result.api_version == "v2"
    
    @given(
        v1_rule=firewall_rule_v1_strategy,
        v2_rule=firewall_rule_v2_strategy
    )
    @settings(max_examples=100)
    def test_firewall_normalization_consistent_structure(self, v1_rule, v2_rule):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 2.3, 2.4, 7.4**
        
        For any v1 and v2 firewall rules, the normalized outputs have the same structure.
        """
        normalizer = ResponseNormalizer()
        
        v1_normalized = normalizer.normalize_firewall_rules([v1_rule], ControllerType.TRADITIONAL)[0]
        v2_normalized = normalizer.normalize_firewall_rules([v2_rule], ControllerType.UNIFI_OS)[0]
        
        # Both should have the same set of attributes
        v1_dict = asdict(v1_normalized)
        v2_dict = asdict(v2_normalized)
        
        assert set(v1_dict.keys()) == set(v2_dict.keys())
    
    @given(routes=st.lists(traffic_route_v1_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v1_traffic_route_normalization_preserves_count(self, routes):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 4.3, 7.4**
        
        For any list of v1 traffic routes, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_traffic_routes(routes, ControllerType.TRADITIONAL)
        assert len(normalized) == len(routes)
    
    @given(routes=st.lists(traffic_route_v2_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v2_traffic_route_normalization_preserves_count(self, routes):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 4.3, 7.4**
        
        For any list of v2 traffic routes, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_traffic_routes(routes, ControllerType.UNIFI_OS)
        assert len(normalized) == len(routes)
    
    @given(route=traffic_route_v1_strategy)
    @settings(max_examples=100)
    def test_v1_traffic_route_normalization_has_required_fields(self, route):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 4.3, 7.4**
        
        For any v1 traffic route, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_traffic_routes([route], ControllerType.TRADITIONAL)
        
        assert len(normalized) == 1
        result = normalized[0]
        
        assert isinstance(result.id, str)
        assert isinstance(result.name, str)
        assert isinstance(result.enabled, bool)
        assert isinstance(result.route_type, str)
        assert result.api_version == "v1"
    
    @given(pfs=st.lists(port_forward_v1_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v1_port_forward_normalization_preserves_count(self, pfs):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 5.3, 7.4**
        
        For any list of v1 port forwards, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_port_forwards(pfs, ControllerType.TRADITIONAL)
        assert len(normalized) == len(pfs)
    
    @given(pfs=st.lists(port_forward_v2_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_v2_port_forward_normalization_preserves_count(self, pfs):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 5.3, 7.4**
        
        For any list of v2 port forwards, normalization preserves the count.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_port_forwards(pfs, ControllerType.UNIFI_OS)
        assert len(normalized) == len(pfs)
    
    @given(pf=port_forward_v1_strategy)
    @settings(max_examples=100)
    def test_v1_port_forward_normalization_has_required_fields(self, pf):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 5.3, 7.4**
        
        For any v1 port forward, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_port_forwards([pf], ControllerType.TRADITIONAL)
        
        assert len(normalized) == 1
        result = normalized[0]
        
        assert isinstance(result.id, str)
        assert isinstance(result.name, str)
        assert isinstance(result.enabled, bool)
        assert isinstance(result.protocol, str)
        assert isinstance(result.source_port, str)
        assert isinstance(result.destination_port, str)
        assert isinstance(result.destination_ip, str)
        assert result.api_version == "v1"
    
    @given(ips_data=ips_status_v1_strategy)
    @settings(max_examples=100)
    def test_v1_ips_normalization_has_required_fields(self, ips_data):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 3.3, 7.4**
        
        For any v1 IPS status, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        result = normalizer.normalize_ips_status(ips_data, ControllerType.TRADITIONAL)
        
        assert isinstance(result.enabled, bool)
        assert isinstance(result.enabled_display, str)
        assert result.enabled_display in ("yes", "no")
        assert isinstance(result.protection_mode, str)
        assert result.api_version == "v1"
    
    @given(ips_data=ips_status_v2_strategy)
    @settings(max_examples=100)
    def test_v2_ips_normalization_has_required_fields(self, ips_data):
        """
        **Feature: unifi-mcp-v2-api-support, Property 3: Response Normalization Consistency**
        **Validates: Requirements 3.3, 7.4**
        
        For any v2 IPS status, the normalized output contains all required fields.
        """
        normalizer = ResponseNormalizer()
        result = normalizer.normalize_ips_status(ips_data, ControllerType.UNIFI_OS)
        
        assert isinstance(result.enabled, bool)
        assert isinstance(result.enabled_display, str)
        assert result.enabled_display in ("yes", "no")
        assert isinstance(result.protection_mode, str)
        assert result.api_version == "v2"



# ============================================================================
# Property-Based Tests for IPS Enabled State (Property 5)
# ============================================================================

class TestIPSEnabledStatePropertyTests:
    """Property-based tests for IPS enabled state accuracy.
    
    These tests verify that the IPS enabled state is correctly reflected
    in the normalized response.
    """
    
    @given(ips_data=ips_status_v2_strategy)
    @settings(max_examples=100)
    def test_v2_ips_enabled_state_accuracy(self, ips_data):
        """
        **Feature: unifi-mcp-v2-api-support, Property 5: IPS Enabled State Accuracy**
        **Validates: Requirements 3.5**
        
        For any IPS configuration where the IPS is enabled, the normalized
        response SHALL correctly reflect enabled=true and enabled_display="yes".
        """
        normalizer = ResponseNormalizer()
        result = normalizer.normalize_ips_status(ips_data, ControllerType.UNIFI_OS)
        
        # The enabled field in the result should match the input
        assert result.enabled == ips_data["enabled"]
        
        # enabled_display should correctly reflect the enabled state
        if result.enabled:
            assert result.enabled_display == "yes"
        else:
            assert result.enabled_display == "no"
    
    @given(ips_data=ips_status_v1_strategy)
    @settings(max_examples=100)
    def test_v1_ips_enabled_state_accuracy(self, ips_data):
        """
        **Feature: unifi-mcp-v2-api-support, Property 5: IPS Enabled State Accuracy**
        **Validates: Requirements 3.5**
        
        For any v1 IPS configuration, the enabled state should be correctly
        derived from ips_mode field.
        """
        normalizer = ResponseNormalizer()
        result = normalizer.normalize_ips_status(ips_data, ControllerType.TRADITIONAL)
        
        # Determine expected enabled state from ips_mode
        ips_mode = ips_data.get("ips_mode", "off").lower()
        expected_enabled = ips_mode in ("ids", "ips")
        
        assert result.enabled == expected_enabled
        
        # enabled_display should correctly reflect the enabled state
        if result.enabled:
            assert result.enabled_display == "yes"
        else:
            assert result.enabled_display == "no"
    
    @given(enabled=st.booleans())
    @settings(max_examples=100)
    def test_v2_ips_enabled_display_consistency(self, enabled):
        """
        **Feature: unifi-mcp-v2-api-support, Property 5: IPS Enabled State Accuracy**
        **Validates: Requirements 3.5**
        
        For any boolean enabled state, enabled_display should be "yes" when
        enabled is True and "no" when enabled is False.
        """
        normalizer = ResponseNormalizer()
        ips_data = {
            "enabled": enabled,
            "mode": "prevention",
        }
        
        result = normalizer.normalize_ips_status(ips_data, ControllerType.UNIFI_OS)
        
        assert result.enabled == enabled
        expected_display = "yes" if enabled else "no"
        assert result.enabled_display == expected_display
    
    @given(mode=st.sampled_from(["off", "ids", "ips"]))
    @settings(max_examples=100)
    def test_v1_ips_mode_to_enabled_mapping(self, mode):
        """
        **Feature: unifi-mcp-v2-api-support, Property 5: IPS Enabled State Accuracy**
        **Validates: Requirements 3.5**
        
        For any v1 ips_mode value, the enabled state should be correctly mapped:
        - "off" -> enabled=False
        - "ids" -> enabled=True
        - "ips" -> enabled=True
        """
        normalizer = ResponseNormalizer()
        ips_data = {"ips_mode": mode}
        
        result = normalizer.normalize_ips_status(ips_data, ControllerType.TRADITIONAL)
        
        expected_enabled = mode in ("ids", "ips")
        assert result.enabled == expected_enabled
        
        expected_display = "yes" if expected_enabled else "no"
        assert result.enabled_display == expected_display
    
    @given(
        enabled=st.booleans(),
        mode=st.sampled_from(["detection", "prevention"])
    )
    @settings(max_examples=100)
    def test_v2_ips_protection_mode_preserved(self, enabled, mode):
        """
        **Feature: unifi-mcp-v2-api-support, Property 5: IPS Enabled State Accuracy**
        **Validates: Requirements 3.5**
        
        For any v2 IPS configuration, the protection mode should be preserved
        in the normalized output.
        """
        normalizer = ResponseNormalizer()
        ips_data = {
            "enabled": enabled,
            "mode": mode,
        }
        
        result = normalizer.normalize_ips_status(ips_data, ControllerType.UNIFI_OS)
        
        assert result.protection_mode == mode


# ============================================================================
# Property-Based Tests for Enabled Filter Correctness (Property 4)
# ============================================================================

class TestEnabledFilterPropertyTests:
    """Property-based tests for enabled filter correctness.
    
    These tests verify that when filtering by enabled_only=true, the result
    contains only items where enabled=true.
    
    **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
    **Validates: Requirements 2.5, 4.4, 5.4**
    """
    
    @given(rules=st.lists(firewall_rule_v1_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_firewall_rules_enabled_filter_v1(self, rules):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 2.5**
        
        For any list of v1 firewall rules with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.TRADITIONAL)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [rule for rule in normalized if rule.enabled]
        
        # Verify all filtered items are enabled
        for rule in filtered:
            assert rule.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for r in rules if r.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(rules=st.lists(firewall_rule_v2_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_firewall_rules_enabled_filter_v2(self, rules):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 2.5**
        
        For any list of v2 firewall rules with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.UNIFI_OS)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [rule for rule in normalized if rule.enabled]
        
        # Verify all filtered items are enabled
        for rule in filtered:
            assert rule.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for r in rules if r.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(routes=st.lists(traffic_route_v1_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_traffic_routes_enabled_filter_v1(self, routes):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 4.4**
        
        For any list of v1 traffic routes with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_traffic_routes(routes, ControllerType.TRADITIONAL)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [route for route in normalized if route.enabled]
        
        # Verify all filtered items are enabled
        for route in filtered:
            assert route.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for r in routes if r.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(routes=st.lists(traffic_route_v2_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_traffic_routes_enabled_filter_v2(self, routes):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 4.4**
        
        For any list of v2 traffic routes with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_traffic_routes(routes, ControllerType.UNIFI_OS)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [route for route in normalized if route.enabled]
        
        # Verify all filtered items are enabled
        for route in filtered:
            assert route.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for r in routes if r.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(pfs=st.lists(port_forward_v1_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_port_forwards_enabled_filter_v1(self, pfs):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 5.4**
        
        For any list of v1 port forwards with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_port_forwards(pfs, ControllerType.TRADITIONAL)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [pf for pf in normalized if pf.enabled]
        
        # Verify all filtered items are enabled
        for pf in filtered:
            assert pf.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for p in pfs if p.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(pfs=st.lists(port_forward_v2_strategy, min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_port_forwards_enabled_filter_v2(self, pfs):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 5.4**
        
        For any list of v2 port forwards with mixed enabled states, when filtering
        by enabled_only=true, the result SHALL contain only items where enabled=true.
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_port_forwards(pfs, ControllerType.UNIFI_OS)
        
        # Apply enabled filter (simulating what the tool does)
        filtered = [pf for pf in normalized if pf.enabled]
        
        # Verify all filtered items are enabled
        for pf in filtered:
            assert pf.enabled is True
        
        # Verify count matches expected
        expected_count = sum(1 for p in pfs if p.get("enabled", False))
        assert len(filtered) == expected_count
    
    @given(
        enabled_count=st.integers(min_value=0, max_value=10),
        disabled_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_enabled_filter_preserves_only_enabled_items(self, enabled_count, disabled_count):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 2.5, 4.4, 5.4**
        
        For any mix of enabled and disabled items, filtering by enabled_only=true
        SHALL return exactly the enabled items.
        """
        # Create a mix of enabled and disabled rules
        rules = []
        for i in range(enabled_count):
            rules.append({
                "_id": f"enabled{i:024d}",
                "name": f"Enabled Rule {i}",
                "enabled": True,
                "action": "accept",
                "protocol": "tcp",
                "src_address": "",
                "dst_address": "",
                "dst_port": "",
                "logging": False,
                "ruleset": "",
            })
        for i in range(disabled_count):
            rules.append({
                "_id": f"disabled{i:024d}",
                "name": f"Disabled Rule {i}",
                "enabled": False,
                "action": "drop",
                "protocol": "udp",
                "src_address": "",
                "dst_address": "",
                "dst_port": "",
                "logging": False,
                "ruleset": "",
            })
        
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.TRADITIONAL)
        
        # Apply enabled filter
        filtered = [rule for rule in normalized if rule.enabled]
        
        # Verify exactly enabled_count items remain
        assert len(filtered) == enabled_count
        
        # Verify all are enabled
        for rule in filtered:
            assert rule.enabled is True
    
    @given(rules=st.lists(firewall_rule_v1_strategy, min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_enabled_filter_idempotent(self, rules):
        """
        **Feature: unifi-mcp-v2-api-support, Property 4: Enabled Filter Correctness**
        **Validates: Requirements 2.5, 4.4, 5.4**
        
        Applying the enabled filter twice should produce the same result as
        applying it once (idempotence).
        """
        normalizer = ResponseNormalizer()
        normalized = normalizer.normalize_firewall_rules(rules, ControllerType.TRADITIONAL)
        
        # Apply filter once
        filtered_once = [rule for rule in normalized if rule.enabled]
        
        # Apply filter again
        filtered_twice = [rule for rule in filtered_once if rule.enabled]
        
        # Results should be identical
        assert len(filtered_once) == len(filtered_twice)
        for r1, r2 in zip(filtered_once, filtered_twice):
            assert r1.id == r2.id
            assert r1.enabled == r2.enabled
