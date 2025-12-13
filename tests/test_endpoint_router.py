"""Tests for endpoint routing.

This module contains unit tests and property-based tests for the
EndpointRouter class.
"""

import pytest
from hypothesis import given, settings, strategies as st, Phase
from unittest.mock import AsyncMock, MagicMock, patch

from unifi_mcp.api.controller_detector import ControllerType
from unifi_mcp.api.endpoint_router import EndpointRouter
from unifi_mcp.config.loader import UniFiConfig


# Configure hypothesis for minimum 100 iterations
settings.register_profile(
    "unifi_mcp",
    max_examples=100,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink]
)
settings.load_profile("unifi_mcp")


class TestEndpointRouterInit:
    """Tests for EndpointRouter initialization."""
    
    def test_init_creates_logger(self):
        """Test that initialization creates a logger."""
        router = EndpointRouter()
        assert router._logger is not None
    
    def test_endpoint_map_exists(self):
        """Test that ENDPOINT_MAP is defined."""
        router = EndpointRouter()
        assert hasattr(router, 'ENDPOINT_MAP')
        assert len(router.ENDPOINT_MAP) > 0
    
    def test_fallback_map_exists(self):
        """Test that FALLBACK_MAP is defined.
        
        Note: As of UniFi Network API 10.0.160, FALLBACK_MAP is empty since
        all security features use v1 REST API directly.
        """
        router = EndpointRouter()
        assert hasattr(router, 'FALLBACK_MAP')
        # FALLBACK_MAP is empty - will be populated when v2 security API is released
        assert isinstance(router.FALLBACK_MAP, dict)
    
    def test_supported_features_property(self):
        """Test that supported_features returns list of features."""
        router = EndpointRouter()
        features = router.supported_features
        assert isinstance(features, list)
        assert "firewall_rules" in features
        assert "ips_status" in features
        assert "traffic_routes" in features
        assert "port_forwards" in features


class TestEndpointRouterGetEndpoint:
    """Tests for get_endpoint method.
    
    Note: As of UniFi Network API 10.0.160, the official v2 API does NOT yet
    expose security settings. All security features use the legacy v1 REST API
    for both UniFi OS and traditional controllers.
    
    The /proxy/network prefix is added automatically by the UniFi client for UniFi OS.
    """
    
    def test_get_endpoint_firewall_rules_unifi_os(self):
        """Test getting firewall rules endpoint for UniFi OS."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("firewall_rules", ControllerType.UNIFI_OS)
        # v2 API does not yet support firewall rules - use legacy REST API
        assert "/api/s/{site}/rest/firewallrule" == endpoint
    
    def test_get_endpoint_firewall_rules_traditional(self):
        """Test getting firewall rules endpoint for traditional controller."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("firewall_rules", ControllerType.TRADITIONAL)
        assert "/api/s/{site}/rest/firewallrule" == endpoint
    
    def test_get_endpoint_ips_status_unifi_os(self):
        """Test getting IPS status endpoint for UniFi OS."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("ips_status", ControllerType.UNIFI_OS)
        # v2 API does not yet support IPS - use legacy REST API
        assert "/api/s/{site}/rest/setting/ips" == endpoint
    
    def test_get_endpoint_ips_status_traditional(self):
        """Test getting IPS status endpoint for traditional controller."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("ips_status", ControllerType.TRADITIONAL)
        assert "/api/s/{site}/rest/setting/ips" == endpoint
    
    def test_get_endpoint_traffic_routes_unifi_os(self):
        """Test getting traffic routes endpoint for UniFi OS."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("traffic_routes", ControllerType.UNIFI_OS)
        # v2 API does not yet support traffic routes - use legacy REST API
        assert "/api/s/{site}/rest/routing" == endpoint
    
    def test_get_endpoint_traffic_routes_traditional(self):
        """Test getting traffic routes endpoint for traditional controller."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("traffic_routes", ControllerType.TRADITIONAL)
        assert "/api/s/{site}/rest/routing" == endpoint
    
    def test_get_endpoint_port_forwards_unifi_os(self):
        """Test getting port forwards endpoint for UniFi OS."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("port_forwards", ControllerType.UNIFI_OS)
        # v2 API does not yet support port forwards - use legacy REST API
        assert "/api/s/{site}/rest/portforward" == endpoint
    
    def test_get_endpoint_port_forwards_traditional(self):
        """Test getting port forwards endpoint for traditional controller."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("port_forwards", ControllerType.TRADITIONAL)
        assert "/api/s/{site}/rest/portforward" == endpoint
    
    def test_get_endpoint_unknown_defaults_to_traditional(self):
        """Test that UNKNOWN controller type defaults to traditional."""
        router = EndpointRouter()
        endpoint = router.get_endpoint("firewall_rules", ControllerType.UNKNOWN)
        # Should return traditional endpoint (same as UniFi OS for security features)
        assert "/api/s/{site}/rest/firewallrule" == endpoint
    
    def test_get_endpoint_invalid_feature_raises(self):
        """Test that invalid feature raises ValueError."""
        router = EndpointRouter()
        with pytest.raises(ValueError) as exc_info:
            router.get_endpoint("invalid_feature", ControllerType.UNIFI_OS)
        assert "Unknown feature" in str(exc_info.value)
    
    def test_all_security_features_use_same_endpoint_both_controllers(self):
        """Test that all security features use the same v1 REST API for both controller types.
        
        This is because the official v2 API does not yet expose security settings.
        """
        router = EndpointRouter()
        features = ["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]
        
        for feature in features:
            unifi_os_endpoint = router.get_endpoint(feature, ControllerType.UNIFI_OS)
            traditional_endpoint = router.get_endpoint(feature, ControllerType.TRADITIONAL)
            assert unifi_os_endpoint == traditional_endpoint, \
                f"Expected same endpoint for {feature} on both controller types"


class TestEndpointRouterFallback:
    """Tests for fallback mechanism.
    
    Note: As of UniFi Network API 10.0.160, the official v2 API does NOT yet
    expose security settings. All security features use the legacy v1 REST API
    directly, so no fallback mechanism is needed.
    
    The FALLBACK_MAP is empty and will be populated when Ubiquiti releases
    the v2 security settings API.
    """
    
    def test_fallback_map_is_empty(self):
        """Test that FALLBACK_MAP is empty since all features use v1 REST API."""
        router = EndpointRouter()
        assert len(router.FALLBACK_MAP) == 0, \
            "FALLBACK_MAP should be empty - all security features use v1 REST API"
    
    def test_get_fallback_endpoint_returns_none_for_all_endpoints(self):
        """Test that get_fallback_endpoint returns None for all security endpoints."""
        router = EndpointRouter()
        
        # All security feature endpoints should have no fallback
        endpoints = [
            "/api/s/{site}/rest/firewallrule",
            "/api/s/{site}/rest/setting/ips",
            "/api/s/{site}/rest/routing",
            "/api/s/{site}/rest/portforward",
        ]
        
        for endpoint in endpoints:
            fallback = router.get_fallback_endpoint(endpoint)
            assert fallback is None, f"Expected no fallback for {endpoint}"
    
    def test_get_fallback_endpoint_none_for_unknown(self):
        """Test that unknown endpoint returns None."""
        router = EndpointRouter()
        fallback = router.get_fallback_endpoint("/unknown/endpoint")
        assert fallback is None


class TestEndpointRouterGetAllEndpoints:
    """Tests for get_all_endpoints_for_feature method."""
    
    def test_get_all_endpoints_firewall_rules(self):
        """Test getting all endpoints for firewall rules."""
        router = EndpointRouter()
        endpoints = router.get_all_endpoints_for_feature("firewall_rules")
        assert ControllerType.UNIFI_OS in endpoints
        assert ControllerType.TRADITIONAL in endpoints
    
    def test_get_all_endpoints_invalid_feature_raises(self):
        """Test that invalid feature raises ValueError."""
        router = EndpointRouter()
        with pytest.raises(ValueError):
            router.get_all_endpoints_for_feature("invalid_feature")
    
    def test_get_all_endpoints_returns_copy(self):
        """Test that get_all_endpoints returns a copy."""
        router = EndpointRouter()
        endpoints1 = router.get_all_endpoints_for_feature("firewall_rules")
        endpoints2 = router.get_all_endpoints_for_feature("firewall_rules")
        # Modifying one should not affect the other
        endpoints1[ControllerType.UNIFI_OS] = "modified"
        assert endpoints2[ControllerType.UNIFI_OS] != "modified"


def _create_mock_client():
    """Helper function to create a mock UniFi client for tests."""
    config = UniFiConfig(
        host="192.168.1.1",
        port=443,
        username="admin",
        password="secret123",
        site="default",
        verify_ssl=False,
        retry={}
    )
    client = MagicMock()
    client.config = config
    client.get = AsyncMock()
    return client


class TestEndpointRouterRequestWithFallback:
    """Tests for request_with_fallback method.
    
    Note: Since all security features use v1 REST API for both controller types,
    the fallback mechanism is not triggered. These tests verify the basic
    request functionality works correctly.
    """
    
    @pytest.mark.asyncio
    async def test_request_with_fallback_success_unifi_os(self):
        """Test successful request on UniFi OS."""
        router = EndpointRouter()
        client = _create_mock_client()
        client.get.return_value = {"data": [{"id": "1", "name": "rule1"}]}
        
        result = await router.request_with_fallback(
            client, "firewall_rules", ControllerType.UNIFI_OS
        )
        
        assert result["fallback_used"] is False
        # All security features use v1 REST API
        assert result["api_version"] == "v1"
        assert "firewallrule" in result["endpoint_used"]
    
    @pytest.mark.asyncio
    async def test_request_with_fallback_success_traditional(self):
        """Test successful request on traditional controller."""
        router = EndpointRouter()
        client = _create_mock_client()
        client.get.return_value = {"data": [{"_id": "1", "name": "rule1"}]}
        
        result = await router.request_with_fallback(
            client, "firewall_rules", ControllerType.TRADITIONAL
        )
        
        assert result["fallback_used"] is False
        assert result["api_version"] == "v1"
        assert "firewallrule" in result["endpoint_used"]
    
    @pytest.mark.asyncio
    async def test_request_raises_on_failure_unifi_os(self):
        """Test that exception is raised when request fails on UniFi OS."""
        from unifi_mcp.api.endpoint_router import EndpointError
        
        router = EndpointRouter()
        client = _create_mock_client()
        
        # Request fails - no fallback available since all features use v1 REST API
        client.get.side_effect = Exception("endpoint failed")
        
        with pytest.raises(EndpointError) as exc_info:
            await router.request_with_fallback(
                client, "firewall_rules", ControllerType.UNIFI_OS
            )
        
        # Should raise error without fallback attempt
        assert "endpoint failed" in str(exc_info.value)
        assert exc_info.value.fallback_endpoint is None
    
    @pytest.mark.asyncio
    async def test_request_raises_on_failure_traditional(self):
        """Test that exception is raised when request fails on traditional controller."""
        from unifi_mcp.api.endpoint_router import EndpointError
        
        router = EndpointRouter()
        client = _create_mock_client()
        
        # Request fails
        client.get.side_effect = Exception("endpoint failed")
        
        with pytest.raises(EndpointError) as exc_info:
            await router.request_with_fallback(
                client, "firewall_rules", ControllerType.TRADITIONAL
            )
        
        # Should raise error without fallback attempt
        assert "endpoint failed" in str(exc_info.value)
        assert exc_info.value.fallback_endpoint is None
    
    @pytest.mark.asyncio
    async def test_request_with_fallback_custom_site(self):
        """Test request with custom site parameter."""
        router = EndpointRouter()
        client = _create_mock_client()
        client.get.return_value = {"data": []}
        
        result = await router.request_with_fallback(
            client, "firewall_rules", ControllerType.UNIFI_OS, site="custom_site"
        )
        
        assert "custom_site" in result["endpoint_used"]
    
    @pytest.mark.asyncio
    async def test_same_endpoint_used_for_both_controller_types(self):
        """Test that the same endpoint is used for both controller types."""
        router = EndpointRouter()
        client = _create_mock_client()
        client.get.return_value = {"data": []}
        
        result_unifi_os = await router.request_with_fallback(
            client, "firewall_rules", ControllerType.UNIFI_OS
        )
        
        result_traditional = await router.request_with_fallback(
            client, "firewall_rules", ControllerType.TRADITIONAL
        )
        
        # Both should use the same v1 REST API endpoint
        assert result_unifi_os["endpoint_used"] == result_traditional["endpoint_used"]
        assert result_unifi_os["api_version"] == result_traditional["api_version"]


class TestEndpointRouterPropertyTests:
    """Property-based tests for EndpointRouter.
    
    These tests verify universal properties that should hold across all inputs.
    
    Note: As of UniFi Network API 10.0.160, all security features use the same
    v1 REST API endpoints for both UniFi OS and traditional controllers.
    """
    
    @given(
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]),
        feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"])
    )
    @settings(max_examples=100)
    def test_endpoint_selection_deterministic(self, controller_type, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For any controller type and feature, endpoint selection is deterministic.
        The same inputs should always produce the same output.
        """
        router = EndpointRouter()
        endpoint1 = router.get_endpoint(feature, controller_type)
        endpoint2 = router.get_endpoint(feature, controller_type)
        assert endpoint1 == endpoint2
    
    @given(
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]),
        feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"])
    )
    @settings(max_examples=100)
    def test_endpoint_contains_site_placeholder(self, controller_type, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For any controller type and feature, the endpoint should contain
        the {site} placeholder for site substitution.
        """
        router = EndpointRouter()
        endpoint = router.get_endpoint(feature, controller_type)
        assert "{site}" in endpoint
    
    @given(
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]),
        feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"])
    )
    @settings(max_examples=100)
    def test_endpoint_uses_v1_rest_api(self, controller_type, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For any controller type and feature, the endpoint should use the v1 REST API
        pattern since the official v2 API does not yet expose security settings.
        """
        router = EndpointRouter()
        endpoint = router.get_endpoint(feature, controller_type)
        
        # All security features use v1 REST API
        assert "/rest/" in endpoint or "/setting/" in endpoint
        assert endpoint.startswith("/api/s/")
    
    @given(feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]))
    @settings(max_examples=100)
    def test_unifi_os_and_traditional_endpoints_same(self, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For all security features, UniFi OS and traditional endpoints should be the same
        since the official v2 API does not yet expose security settings.
        """
        router = EndpointRouter()
        unifi_os_endpoint = router.get_endpoint(feature, ControllerType.UNIFI_OS)
        traditional_endpoint = router.get_endpoint(feature, ControllerType.TRADITIONAL)
        assert unifi_os_endpoint == traditional_endpoint
    
    @given(feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]))
    @settings(max_examples=100)
    def test_unknown_controller_type_defaults_to_traditional(self, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For any feature, UNKNOWN controller type should return the same
        endpoint as TRADITIONAL controller type.
        """
        router = EndpointRouter()
        unknown_endpoint = router.get_endpoint(feature, ControllerType.UNKNOWN)
        traditional_endpoint = router.get_endpoint(feature, ControllerType.TRADITIONAL)
        assert unknown_endpoint == traditional_endpoint
    
    @given(
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]),
        feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"])
    )
    @settings(max_examples=100)
    def test_get_all_endpoints_contains_get_endpoint_result(self, controller_type, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 2: Endpoint Routing by Controller Type**
        **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2**
        
        For any controller type and feature, the result of get_endpoint should
        be present in the result of get_all_endpoints_for_feature.
        """
        router = EndpointRouter()
        single_endpoint = router.get_endpoint(feature, controller_type)
        all_endpoints = router.get_all_endpoints_for_feature(feature)
        assert single_endpoint in all_endpoints.values()


class TestFallbackBehaviorPropertyTests:
    """Property-based tests for fallback behavior.
    
    Note: As of UniFi Network API 10.0.160, all security features use the v1 REST API
    directly for both controller types. The fallback mechanism is not triggered since
    there are no v2 endpoints to fall back from.
    
    These tests verify that the system handles failures correctly without fallback.
    """
    
    @given(feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_no_fallback_for_unifi_os(self, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 7: Fallback Behavior on v2 Failure**
        **Validates: Requirements 7.2**
        
        For any UniFi OS connection, no fallback is attempted since all security
        features use the v1 REST API directly.
        """
        from unifi_mcp.api.endpoint_router import EndpointError
        
        router = EndpointRouter()
        client = _create_mock_client()
        
        # Configure endpoint to fail
        client.get.side_effect = Exception("endpoint failed")
        
        # Make request with UniFi OS controller type
        with pytest.raises(EndpointError) as exc_info:
            await router.request_with_fallback(
                client, feature, ControllerType.UNIFI_OS
            )
        
        # Verify only one endpoint was called (no fallback)
        assert client.get.call_count == 1
        
        # Verify error indicates no fallback was attempted
        assert exc_info.value.fallback_endpoint is None
    
    @given(feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_no_fallback_for_traditional_controller(self, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 7: Fallback Behavior on v2 Failure**
        **Validates: Requirements 7.2**
        
        For any traditional controller connection, the system SHALL NOT
        attempt fallback when the primary endpoint fails.
        """
        from unifi_mcp.api.endpoint_router import EndpointError
        
        router = EndpointRouter()
        client = _create_mock_client()
        
        # Configure endpoint to fail
        client.get.side_effect = Exception("endpoint failed")
        
        # Make request with traditional controller type
        with pytest.raises(EndpointError) as exc_info:
            await router.request_with_fallback(
                client, feature, ControllerType.TRADITIONAL
            )
        
        # Verify only one endpoint was called (no fallback)
        assert client.get.call_count == 1
        
        # Verify error indicates no fallback was attempted
        assert exc_info.value.fallback_endpoint is None
    
    @given(feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]))
    @settings(max_examples=100)
    def test_no_fallback_endpoints_exist(self, feature):
        """
        **Feature: unifi-mcp-v2-api-support, Property 7: Fallback Behavior on v2 Failure**
        **Validates: Requirements 7.2**
        
        For all security features, no fallback endpoints exist since all features
        use the v1 REST API directly.
        """
        router = EndpointRouter()
        
        # Get the endpoint for UniFi OS
        endpoint = router.get_endpoint(feature, ControllerType.UNIFI_OS)
        
        # Verify no fallback exists
        fallback = router.get_fallback_endpoint(endpoint)
        assert fallback is None, f"Unexpected fallback endpoint for {feature}: {fallback}"
    
    @given(
        feature=st.sampled_from(["firewall_rules", "ips_status", "traffic_routes", "port_forwards"]),
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL])
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_structured_error_on_failure(self, feature, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 7: Fallback Behavior on v2 Failure**
        **Validates: Requirements 7.2**
        
        For any controller type and feature, when the endpoint fails,
        the system SHALL raise a structured error with details.
        """
        from unifi_mcp.api.endpoint_router import EndpointError
        
        router = EndpointRouter()
        client = _create_mock_client()
        
        # Configure endpoint to fail
        client.get.side_effect = Exception("endpoint failed")
        
        # Make request
        with pytest.raises(EndpointError) as exc_info:
            await router.request_with_fallback(
                client, feature, controller_type
            )
        
        # Verify error contains expected information
        error = exc_info.value
        assert error.feature == feature
        assert error.primary_endpoint is not None
        assert error.primary_error is not None
        assert error.fallback_endpoint is None  # No fallback attempted
        
        # Verify error can be converted to dict for tool responses
        error_dict = error.to_dict()
        assert error_dict["both_endpoints_failed"] is False
        assert "primary_error" in error_dict
