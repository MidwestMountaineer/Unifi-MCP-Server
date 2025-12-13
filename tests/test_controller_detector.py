"""Tests for controller type detection.

This module contains unit tests and property-based tests for the
ControllerDetector class and ControllerType enum.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st, Phase

from unifi_mcp.api.controller_detector import ControllerType, ControllerDetector
from unifi_mcp.config.loader import UniFiConfig


# Configure hypothesis for minimum 100 iterations
settings.register_profile(
    "unifi_mcp",
    max_examples=100,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink]
)
settings.load_profile("unifi_mcp")


@pytest.fixture
def unifi_config():
    """Create test UniFi configuration."""
    return UniFiConfig(
        host="192.168.1.1",
        port=443,
        username="admin",
        password="secret123",
        site="default",
        verify_ssl=False,
        retry={}
    )


@pytest.fixture
def mock_client(unifi_config):
    """Create a mock UniFi client."""
    client = MagicMock()
    client.config = unifi_config
    client.session = MagicMock()
    client.ssl_context = MagicMock()
    return client


class TestControllerTypeEnum:
    """Tests for ControllerType enum."""
    
    def test_unifi_os_value(self):
        """Test UNIFI_OS enum value."""
        assert ControllerType.UNIFI_OS.value == "unifi_os"
    
    def test_traditional_value(self):
        """Test TRADITIONAL enum value."""
        assert ControllerType.TRADITIONAL.value == "traditional"
    
    def test_unknown_value(self):
        """Test UNKNOWN enum value."""
        assert ControllerType.UNKNOWN.value == "unknown"
    
    def test_all_types_are_unique(self):
        """Test that all controller types have unique values."""
        values = [ct.value for ct in ControllerType]
        assert len(values) == len(set(values))


class TestControllerDetectorInit:
    """Tests for ControllerDetector initialization."""
    
    def test_init_sets_client(self, mock_client):
        """Test that initialization sets the client."""
        detector = ControllerDetector(mock_client)
        assert detector._client == mock_client
    
    def test_init_sets_default_timeout(self, mock_client):
        """Test that initialization sets default timeout."""
        detector = ControllerDetector(mock_client)
        assert detector.detection_timeout == ControllerDetector.DEFAULT_TIMEOUT
    
    def test_init_cache_is_none(self, mock_client):
        """Test that cache is initially None."""
        detector = ControllerDetector(mock_client)
        assert detector.get_cached_type() is None
    
    def test_timeout_setter_valid(self, mock_client):
        """Test setting a valid timeout."""
        detector = ControllerDetector(mock_client)
        detector.detection_timeout = 10.0
        assert detector.detection_timeout == 10.0
    
    def test_timeout_setter_invalid(self, mock_client):
        """Test setting an invalid timeout raises error."""
        detector = ControllerDetector(mock_client)
        with pytest.raises(ValueError):
            detector.detection_timeout = 0
        with pytest.raises(ValueError):
            detector.detection_timeout = -1


class TestControllerDetectorCaching:
    """Tests for caching behavior."""
    
    def test_get_cached_type_returns_none_initially(self, mock_client):
        """Test that get_cached_type returns None before detection."""
        detector = ControllerDetector(mock_client)
        assert detector.get_cached_type() is None
    
    def test_clear_cache(self, mock_client):
        """Test that clear_cache clears the cached type."""
        detector = ControllerDetector(mock_client)
        detector._cached_type = ControllerType.UNIFI_OS
        detector.clear_cache()
        assert detector.get_cached_type() is None
    
    def test_set_type(self, mock_client):
        """Test that set_type sets the cached type."""
        detector = ControllerDetector(mock_client)
        detector.set_type(ControllerType.TRADITIONAL)
        assert detector.get_cached_type() == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_detect_returns_cached_type(self, mock_client):
        """Test that detect returns cached type without re-detecting."""
        detector = ControllerDetector(mock_client)
        detector._cached_type = ControllerType.UNIFI_OS
        
        result = await detector.detect()
        
        assert result == ControllerType.UNIFI_OS
        # Session should not be accessed since we used cache
        mock_client.session.get.assert_not_called()


class TestControllerDetectorEnvOverride:
    """Tests for environment variable override."""
    
    @pytest.mark.asyncio
    async def test_env_override_unifi_os(self, mock_client):
        """Test environment variable override for UniFi OS."""
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {"UNIFI_CONTROLLER_TYPE": "unifi_os"}):
            result = await detector.detect()
        
        assert result == ControllerType.UNIFI_OS
    
    @pytest.mark.asyncio
    async def test_env_override_traditional(self, mock_client):
        """Test environment variable override for traditional."""
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {"UNIFI_CONTROLLER_TYPE": "traditional"}):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_env_override_unifios_variant(self, mock_client):
        """Test environment variable override with 'unifios' variant."""
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {"UNIFI_CONTROLLER_TYPE": "unifios"}):
            result = await detector.detect()
        
        assert result == ControllerType.UNIFI_OS
    
    @pytest.mark.asyncio
    async def test_env_override_legacy_variant(self, mock_client):
        """Test environment variable override with 'legacy' variant."""
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {"UNIFI_CONTROLLER_TYPE": "legacy"}):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_env_override_case_insensitive(self, mock_client):
        """Test that environment variable override is case insensitive."""
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {"UNIFI_CONTROLLER_TYPE": "UNIFI_OS"}):
            result = await detector.detect()
        
        assert result == ControllerType.UNIFI_OS
    
    def test_parse_env_override_invalid(self, mock_client):
        """Test that invalid env override returns None."""
        detector = ControllerDetector(mock_client)
        
        result = detector._parse_env_override("invalid_value")
        
        assert result is None


class TestControllerDetectorAPIDetection:
    """Tests for API-based detection."""
    
    @pytest.mark.asyncio
    async def test_detect_unifi_os_success(self, mock_client):
        """Test detection of UniFi OS via API probe."""
        detector = ControllerDetector(mock_client)
        
        # Mock successful response (200)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.session.get = MagicMock(return_value=mock_response)
        
        # Clear any env override
        with patch.dict(os.environ, {}, clear=True):
            result = await detector.detect()
        
        assert result == ControllerType.UNIFI_OS
    
    @pytest.mark.asyncio
    async def test_detect_traditional_404(self, mock_client):
        """Test detection of traditional controller via 404 response."""
        detector = ControllerDetector(mock_client)
        
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.session.get = MagicMock(return_value=mock_response)
        
        with patch.dict(os.environ, {}, clear=True):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_detect_timeout_defaults_to_traditional(self, mock_client):
        """Test that timeout defaults to traditional controller."""
        detector = ControllerDetector(mock_client)
        detector.detection_timeout = 0.1  # Very short timeout
        
        # Mock a slow response that will timeout
        async def slow_get(*args, **kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return MagicMock()
        
        mock_client.session.get = slow_get
        
        with patch.dict(os.environ, {}, clear=True):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_detect_no_session_defaults_to_traditional(self, mock_client):
        """Test that missing session defaults to traditional."""
        mock_client.session = None
        detector = ControllerDetector(mock_client)
        
        with patch.dict(os.environ, {}, clear=True):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL
    
    @pytest.mark.asyncio
    async def test_detect_exception_defaults_to_traditional(self, mock_client):
        """Test that exceptions default to traditional controller."""
        detector = ControllerDetector(mock_client)
        
        # Mock an exception
        mock_client.session.get = MagicMock(side_effect=Exception("Connection failed"))
        
        with patch.dict(os.environ, {}, clear=True):
            result = await detector.detect()
        
        assert result == ControllerType.TRADITIONAL


def _create_mock_client():
    """Helper function to create a mock UniFi client for property tests."""
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
    client.session = MagicMock()
    client.ssl_context = MagicMock()
    return client


class TestControllerDetectorPropertyTests:
    """Property-based tests for ControllerDetector.
    
    These tests verify universal properties that should hold across all inputs.
    """
    
    @given(controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL, ControllerType.UNKNOWN]))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_detection_caching_consistency(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 1: Controller Detection Consistency**
        **Validates: Requirements 1.1, 1.5**
        
        For any UniFi controller connection, the controller type detection SHALL
        return the same result when called multiple times within the same session
        (caching works correctly).
        """
        mock_client = _create_mock_client()
        detector = ControllerDetector(mock_client)
        
        # Set the cached type directly (simulating a completed detection)
        detector.set_type(controller_type)
        
        # Call detect multiple times
        result1 = await detector.detect()
        result2 = await detector.detect()
        result3 = await detector.detect()
        
        # All results should be identical
        assert result1 == result2 == result3 == controller_type
        
        # Verify the cached type is still the same
        assert detector.get_cached_type() == controller_type
    
    @given(
        controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]),
        num_calls=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_cached_detection_never_changes(self, controller_type, num_calls):
        """
        **Feature: unifi-mcp-v2-api-support, Property 1: Controller Detection Consistency**
        **Validates: Requirements 1.1, 1.5**
        
        For any number of detect() calls after caching, the result should never change.
        """
        mock_client = _create_mock_client()
        detector = ControllerDetector(mock_client)
        detector.set_type(controller_type)
        
        results = []
        for _ in range(num_calls):
            result = await detector.detect()
            results.append(result)
        
        # All results should be the same
        assert all(r == controller_type for r in results)
    
    @given(controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]))
    @settings(max_examples=100)
    def test_set_type_then_get_cached_type_consistency(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 1: Controller Detection Consistency**
        **Validates: Requirements 1.1, 1.5**
        
        For any controller type, setting it and then getting the cached type
        should return the same value.
        """
        mock_client = _create_mock_client()
        detector = ControllerDetector(mock_client)
        
        detector.set_type(controller_type)
        cached = detector.get_cached_type()
        
        assert cached == controller_type
    
    @given(controller_type=st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL]))
    @settings(max_examples=100)
    def test_clear_cache_resets_state(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 1: Controller Detection Consistency**
        **Validates: Requirements 1.1, 1.5**
        
        For any cached controller type, clearing the cache should reset to None.
        """
        mock_client = _create_mock_client()
        detector = ControllerDetector(mock_client)
        
        detector.set_type(controller_type)
        assert detector.get_cached_type() == controller_type
        
        detector.clear_cache()
        assert detector.get_cached_type() is None
