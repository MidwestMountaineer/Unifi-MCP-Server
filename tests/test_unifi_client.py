"""Tests for UniFi API client."""

import asyncio
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from unifi_mcp.config.loader import UniFiConfig
from unifi_mcp.unifi_client import (
    UniFiClient,
    UniFiClientError,
    AuthenticationError,
    ConnectionError,
)


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
def server_config():
    """Create test server configuration."""
    return {
        "performance": {
            "cache_ttl": 30,
            "cache_ttl_by_endpoint": {
                "devices": 30,
                "clients": 30,
                "networks": 60,
                "wlans": 60,
                "firewall": 60,
                "routes": 60,
                "port_forwards": 60,
                "stats": 10,
                "alerts": 10,
                "health": 10,
            }
        }
    }


@pytest.fixture
def unifi_config_with_ssl():
    """Create test UniFi configuration with SSL verification."""
    return UniFiConfig(
        host="192.168.1.1",
        port=443,
        username="admin",
        password="secret123",
        site="default",
        verify_ssl=True,
        retry={}
    )


@pytest.fixture
def unifi_config_with_api_key():
    """Create test UniFi configuration with API key."""
    return UniFiConfig(
        host="192.168.1.1",
        port=443,
        username="",
        password="",
        api_key="test-api-key-12345",
        site="default",
        verify_ssl=False,
        retry={}
    )


class TestUniFiClientInitialization:
    """Tests for UniFi client initialization."""
    
    def test_init_creates_base_url(self, unifi_config):
        """Test that initialization creates correct base URL."""
        client = UniFiClient(unifi_config)
        
        assert client.base_url == "https://192.168.1.1:443"
        assert client.config == unifi_config
        assert client.session is None
        assert client.authenticated is False
        assert client.use_api_key is False
    
    def test_init_with_api_key(self, unifi_config_with_api_key):
        """Test initialization with API key."""
        client = UniFiClient(unifi_config_with_api_key)
        
        assert client.base_url == "https://192.168.1.1:443/proxy/network"
        assert client.use_api_key is True
    
    def test_init_with_custom_port(self):
        """Test initialization with custom port."""
        config = UniFiConfig(
            host="unifi.local",
            port=8443,
            username="admin",
            password="secret",
            site="default",
            verify_ssl=False,
            retry={}
        )
        client = UniFiClient(config)
        
        assert client.base_url == "https://unifi.local:8443"
    
    def test_ssl_context_without_verification(self, unifi_config):
        """Test SSL context creation without verification."""
        client = UniFiClient(unifi_config)
        
        assert client.ssl_context is not None
        assert client.ssl_context.check_hostname is False
        assert client.ssl_context.verify_mode == ssl.CERT_NONE
    
    def test_ssl_context_with_verification(self, unifi_config_with_ssl):
        """Test SSL context creation with verification."""
        client = UniFiClient(unifi_config_with_ssl)
        
        assert client.ssl_context is not None
        # Default context has verification enabled
        assert client.ssl_context.verify_mode != ssl.CERT_NONE


class TestUniFiClientConnection:
    """Tests for UniFi client connection and authentication."""
    
    @pytest.mark.asyncio
    async def test_connect_creates_session(self, unifi_config):
        """Test that connect creates HTTP session."""
        client = UniFiClient(unifi_config)
        
        # Mock the authentication method
        with patch.object(client, '_authenticate', new_callable=AsyncMock):
            await client.connect()
            
            assert client.session is not None
            assert isinstance(client.session, aiohttp.ClientSession)
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_connect_calls_authenticate(self, unifi_config):
        """Test that connect calls authentication."""
        client = UniFiClient(unifi_config)
        
        with patch.object(client, '_authenticate', new_callable=AsyncMock) as mock_auth:
            await client.connect()
            
            mock_auth.assert_called_once()
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, unifi_config):
        """Test successful authentication."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        
        await client._authenticate()
        
        assert client.authenticated is True
        mock_session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, unifi_config):
        """Test authentication with invalid credentials."""
        client = UniFiClient(unifi_config)
        
        # Create mock response with 400 status
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Invalid credentials")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        
        with pytest.raises(AuthenticationError) as exc_info:
            await client._authenticate()
        
        assert "Invalid username or password" in str(exc_info.value)
        assert client.authenticated is False
    
    @pytest.mark.asyncio
    async def test_authenticate_unauthorized(self, unifi_config):
        """Test authentication with 401 response."""
        client = UniFiClient(unifi_config)
        
        # Create mock response with 401 status
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        
        with pytest.raises(AuthenticationError) as exc_info:
            await client._authenticate()
        
        assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_without_session(self, unifi_config):
        """Test authentication without initialized session."""
        client = UniFiClient(unifi_config)
        
        with pytest.raises(UniFiClientError) as exc_info:
            await client._authenticate()
        
        assert "Session not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_close_cleans_up_session(self, unifi_config):
        """Test that close cleans up session."""
        client = UniFiClient(unifi_config)
        
        # Create mock session
        mock_session = AsyncMock()
        client.session = mock_session
        client.authenticated = True
        
        await client.close()
        
        mock_session.close.assert_called_once()
        assert client.session is None
        assert client.authenticated is False
    
    @pytest.mark.asyncio
    async def test_connect_with_api_key(self, unifi_config_with_api_key):
        """Test connection with API key authentication."""
        client = UniFiClient(unifi_config_with_api_key)
        
        # Mock session creation
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            await client.connect()
            
            # Should not call _authenticate for API key
            assert client.authenticated is True
            assert client.session is not None
            
            # Verify headers were set
            call_kwargs = mock_session_class.call_args[1]
            assert 'headers' in call_kwargs
            assert call_kwargs['headers']['X-API-KEY'] == 'test-api-key-12345'
            
            await client.close()


class TestUniFiClientContextManager:
    """Tests for async context manager support."""
    
    @pytest.mark.asyncio
    async def test_context_manager_connects_and_closes(self, unifi_config):
        """Test that context manager connects and closes properly."""
        with patch.object(UniFiClient, '_authenticate', new_callable=AsyncMock):
            async with UniFiClient(unifi_config) as client:
                assert client.session is not None
            
            # After exiting context, session should be closed
            assert client.session is None
            assert client.authenticated is False


class TestUniFiClientRequests:
    """Tests for making API requests."""
    
    def test_build_url_replaces_site_placeholder(self, unifi_config):
        """Test that _build_url replaces {site} placeholder."""
        client = UniFiClient(unifi_config)
        
        url = client._build_url("/api/s/{site}/stat/device")
        
        assert url == "https://192.168.1.1:443/api/s/default/stat/device"
    
    def test_build_url_without_placeholder(self, unifi_config):
        """Test _build_url with endpoint without placeholder."""
        client = UniFiClient(unifi_config)
        
        url = client._build_url("/api/login")
        
        assert url == "https://192.168.1.1:443/api/login"
    
    @pytest.mark.asyncio
    async def test_get_request_success(self, unifi_config):
        """Test successful GET request."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "123"}]})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        result = await client.get("/api/s/{site}/stat/device")
        
        assert result == {"data": [{"id": "123"}]}
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_request_with_params(self, unifi_config):
        """Test GET request with query parameters."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        params = {"type": "switch"}
        await client.get("/api/s/{site}/stat/device", params=params)
        
        # Verify params were passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"] == params
    
    @pytest.mark.asyncio
    async def test_get_request_not_connected(self, unifi_config):
        """Test GET request without connection."""
        client = UniFiClient(unifi_config)
        
        with pytest.raises(UniFiClientError) as exc_info:
            await client.get("/api/s/{site}/stat/device")
        
        assert "Not connected" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_post_request_success(self, unifi_config):
        """Test successful POST request."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"meta": {"rc": "ok"}})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        data = {"enabled": True}
        result = await client.post("/api/s/{site}/rest/firewallrule/123", json=data)
        
        assert result == {"meta": {"rc": "ok"}}
        mock_session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_request_not_connected(self, unifi_config):
        """Test POST request without connection."""
        client = UniFiClient(unifi_config)
        
        with pytest.raises(UniFiClientError) as exc_info:
            await client.post("/api/s/{site}/rest/firewallrule/123", json={})
        
        assert "Not connected" in str(exc_info.value)


class TestUniFiClientLogging:
    """Tests for logging behavior."""
    
    @pytest.mark.asyncio
    async def test_authentication_logs_redacted_credentials(self, unifi_config):
        """Test that authentication logs redact credentials."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        
        # Capture log output
        with patch.object(client.logger, 'info') as mock_log:
            await client._authenticate()
            
            # Verify logging was called
            assert mock_log.called
            
            # Check that password is not in any log call
            for call in mock_log.call_args_list:
                call_str = str(call)
                assert "secret123" not in call_str or "[REDACTED]" in call_str



class TestUniFiClientCaching:
    """Tests for caching functionality."""
    
    def test_cache_initialization(self, unifi_config, server_config):
        """Test that cache is initialized with correct settings."""
        client = UniFiClient(unifi_config, server_config)
        
        assert client.cache is not None
        assert client.cache_enabled is True
        assert client.default_cache_ttl == 30
        assert "devices" in client.cache_ttl_by_endpoint
        assert client.cache_ttl_by_endpoint["devices"] == 30
        assert client.cache_ttl_by_endpoint["stats"] == 10
        assert client.cache_ttl_by_endpoint["networks"] == 60
    
    def test_cache_initialization_without_config(self, unifi_config):
        """Test cache initialization with default settings."""
        client = UniFiClient(unifi_config)
        
        assert client.cache is not None
        assert client.cache_enabled is True
        assert client.default_cache_ttl == 30
    
    def test_get_cache_key_without_params(self, unifi_config):
        """Test cache key generation without parameters."""
        client = UniFiClient(unifi_config)
        
        key1 = client._get_cache_key("/api/s/default/stat/device")
        key2 = client._get_cache_key("/api/s/default/stat/device")
        
        # Same endpoint should generate same key
        assert key1 == key2
        
        # Different endpoint should generate different key
        key3 = client._get_cache_key("/api/s/default/stat/sta")
        assert key1 != key3
    
    def test_get_cache_key_with_params(self, unifi_config):
        """Test cache key generation with parameters."""
        client = UniFiClient(unifi_config)
        
        key1 = client._get_cache_key("/api/s/default/stat/device", {"type": "switch"})
        key2 = client._get_cache_key("/api/s/default/stat/device", {"type": "switch"})
        
        # Same endpoint and params should generate same key
        assert key1 == key2
        
        # Different params should generate different key
        key3 = client._get_cache_key("/api/s/default/stat/device", {"type": "ap"})
        assert key1 != key3
        
        # No params should generate different key
        key4 = client._get_cache_key("/api/s/default/stat/device")
        assert key1 != key4
    
    def test_get_cache_key_params_order_independent(self, unifi_config):
        """Test that cache key is independent of parameter order."""
        client = UniFiClient(unifi_config)
        
        key1 = client._get_cache_key("/api/test", {"a": "1", "b": "2"})
        key2 = client._get_cache_key("/api/test", {"b": "2", "a": "1"})
        
        # Same params in different order should generate same key
        assert key1 == key2
    
    def test_get_endpoint_type_devices(self, unifi_config):
        """Test endpoint type detection for devices."""
        client = UniFiClient(unifi_config)
        
        assert client._get_endpoint_type("/api/s/default/stat/device") == "devices"
        assert client._get_endpoint_type("/API/S/DEFAULT/STAT/DEVICE") == "devices"
    
    def test_get_endpoint_type_clients(self, unifi_config):
        """Test endpoint type detection for clients."""
        client = UniFiClient(unifi_config)
        
        assert client._get_endpoint_type("/api/s/default/stat/sta") == "clients"
        assert client._get_endpoint_type("/api/s/default/stat/client") == "clients"
    
    def test_get_endpoint_type_networks(self, unifi_config):
        """Test endpoint type detection for networks."""
        client = UniFiClient(unifi_config)
        
        assert client._get_endpoint_type("/api/s/default/rest/networkconf") == "networks"
        assert client._get_endpoint_type("/api/s/default/list/networkconf") == "networks"
    
    def test_get_endpoint_type_stats(self, unifi_config):
        """Test endpoint type detection for stats."""
        client = UniFiClient(unifi_config)
        
        assert client._get_endpoint_type("/api/s/default/stat/something") == "stats"
    
    def test_get_endpoint_type_unknown(self, unifi_config):
        """Test endpoint type detection for unknown endpoints."""
        client = UniFiClient(unifi_config)
        
        assert client._get_endpoint_type("/api/unknown/endpoint") is None
    
    def test_get_cache_ttl_by_endpoint_type(self, unifi_config, server_config):
        """Test cache TTL lookup by endpoint type."""
        client = UniFiClient(unifi_config, server_config)
        
        # Test specific endpoint types
        assert client._get_cache_ttl("/api/s/default/stat/device") == 30
        assert client._get_cache_ttl("/api/s/default/stat/sta") == 30
        assert client._get_cache_ttl("/api/s/default/rest/networkconf") == 60
        assert client._get_cache_ttl("/api/s/default/stat/health") == 10
        
        # Test unknown endpoint (should use default)
        assert client._get_cache_ttl("/api/unknown") == 30
    
    @pytest.mark.asyncio
    async def test_get_request_caches_response(self, unifi_config):
        """Test that GET request caches the response."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "123"}]})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First request should hit the API
        result1 = await client.get(endpoint)
        assert result1 == {"data": [{"id": "123"}]}
        assert mock_session.get.call_count == 1
        
        # Second request should use cache
        result2 = await client.get(endpoint)
        assert result2 == {"data": [{"id": "123"}]}
        assert mock_session.get.call_count == 1  # Still 1, not called again
    
    @pytest.mark.asyncio
    async def test_get_request_cache_with_different_params(self, unifi_config):
        """Test that different parameters create different cache entries."""
        client = UniFiClient(unifi_config)
        
        # Create mock responses
        mock_response1 = MagicMock()
        mock_response1.status = 200
        mock_response1.json = AsyncMock(return_value={"data": [{"type": "switch"}]})
        mock_response1.raise_for_status = MagicMock()
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)
        
        mock_response2 = MagicMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": [{"type": "ap"}]})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session that returns different responses
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[mock_response1, mock_response2])
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # Request with first params
        result1 = await client.get(endpoint, {"type": "switch"})
        assert result1 == {"data": [{"type": "switch"}]}
        
        # Request with different params should hit API again
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        result2 = await client.get(endpoint, {"type": "ap"})
        assert result2 == {"data": [{"type": "ap"}]}
        
        assert mock_session.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_request_bypass_cache(self, unifi_config):
        """Test that cache can be bypassed with use_cache=False."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "123"}]})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First request with cache disabled
        result1 = await client.get(endpoint, use_cache=False)
        assert result1 == {"data": [{"id": "123"}]}
        assert mock_session.get.call_count == 1
        
        # Second request with cache disabled should hit API again
        result2 = await client.get(endpoint, use_cache=False)
        assert result2 == {"data": [{"id": "123"}]}
        assert mock_session.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_post_request_invalidates_cache(self, unifi_config):
        """Test that POST request invalidates cache."""
        client = UniFiClient(unifi_config)
        
        # Create mock GET response
        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={"data": [{"id": "123"}]})
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock POST response
        mock_post_response = MagicMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"meta": {"rc": "ok"}})
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.post = MagicMock(return_value=mock_post_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First GET request - should cache
        result1 = await client.get(endpoint)
        assert mock_session.get.call_count == 1
        
        # Second GET request - should use cache
        result2 = await client.get(endpoint)
        assert mock_session.get.call_count == 1  # Still 1
        
        # POST request - should invalidate cache
        await client.post("/api/s/default/rest/device/123", json={"enabled": True})
        
        # Third GET request - should hit API again (cache was invalidated)
        result3 = await client.get(endpoint)
        assert mock_session.get.call_count == 2  # Now 2
    
    def test_invalidate_cache_all(self, unifi_config):
        """Test invalidating all cache entries."""
        client = UniFiClient(unifi_config)
        
        # Add some entries to cache
        client.cache["key1"] = "value1"
        client.cache["key2"] = "value2"
        
        assert len(client.cache) == 2
        
        # Invalidate all
        client.invalidate_cache()
        
        assert len(client.cache) == 0
    
    def test_invalidate_cache_with_pattern(self, unifi_config):
        """Test invalidating cache with pattern (currently clears all)."""
        client = UniFiClient(unifi_config)
        
        # Add some entries to cache
        client.cache["key1"] = "value1"
        client.cache["key2"] = "value2"
        
        assert len(client.cache) == 2
        
        # Invalidate with pattern (currently clears all)
        client.invalidate_cache("/api/s/default/stat/device")
        
        assert len(client.cache) == 0
    
    @pytest.mark.asyncio
    async def test_cache_hit_behavior(self, unifi_config):
        """Test cache hit behavior - second request uses cached data."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "device1"}]})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First request - cache miss, should hit API
        result1 = await client.get(endpoint)
        assert result1 == {"data": [{"id": "device1"}]}
        assert mock_session.get.call_count == 1
        
        # Verify cache was populated
        cache_key = client._get_cache_key(endpoint)
        assert cache_key in client.cache
        assert client.cache[cache_key] == {"data": [{"id": "device1"}]}
        
        # Second request - cache hit, should NOT hit API
        result2 = await client.get(endpoint)
        assert result2 == {"data": [{"id": "device1"}]}
        assert mock_session.get.call_count == 1  # Still 1, not incremented
    
    @pytest.mark.asyncio
    async def test_cache_miss_behavior(self, unifi_config):
        """Test cache miss behavior - different endpoints create separate cache entries."""
        client = UniFiClient(unifi_config)
        
        # Create mock responses
        mock_response1 = MagicMock()
        mock_response1.status = 200
        mock_response1.json = AsyncMock(return_value={"data": "devices"})
        mock_response1.raise_for_status = MagicMock()
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)
        
        mock_response2 = MagicMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": "clients"})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        mock_response2.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[mock_response1, mock_response2])
        
        client.session = mock_session
        client.authenticated = True
        
        # Request first endpoint
        result1 = await client.get("/api/s/default/stat/device")
        assert result1 == {"data": "devices"}
        assert mock_session.get.call_count == 1
        
        # Request different endpoint - cache miss, should hit API
        result2 = await client.get("/api/s/default/stat/sta")
        assert result2 == {"data": "clients"}
        assert mock_session.get.call_count == 2
        
        # Verify both are cached
        assert len(client.cache) == 2
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, unifi_config):
        """Test that cache entries expire after TTL."""
        import time
        
        # Create client with very short TTL for testing
        server_config = {
            "performance": {
                "cache_ttl": 1,  # 1 second TTL
                "cache_ttl_by_endpoint": {
                    "devices": 1,
                }
            }
        }
        client = UniFiClient(unifi_config, server_config)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "device1"}]})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First request - cache miss
        result1 = await client.get(endpoint)
        assert result1 == {"data": [{"id": "device1"}]}
        assert mock_session.get.call_count == 1
        
        # Immediate second request - cache hit
        result2 = await client.get(endpoint)
        assert result2 == {"data": [{"id": "device1"}]}
        assert mock_session.get.call_count == 1
        
        # Wait for TTL to expire
        time.sleep(1.5)
        
        # Third request after TTL - cache miss, should hit API again
        result3 = await client.get(endpoint)
        assert result3 == {"data": [{"id": "device1"}]}
        assert mock_session.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_write(self, unifi_config):
        """Test that write operations invalidate the cache."""
        client = UniFiClient(unifi_config)
        
        # Create mock GET response
        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={"data": "original"})
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock POST response
        mock_post_response = MagicMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"meta": {"rc": "ok"}})
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.post = MagicMock(return_value=mock_post_response)
        
        client.session = mock_session
        client.authenticated = True
        
        # Populate cache with GET request
        await client.get("/api/s/default/stat/device")
        assert len(client.cache) > 0
        initial_cache_size = len(client.cache)
        
        # Perform write operation
        await client.post("/api/s/default/rest/device/123", json={"enabled": True})
        
        # Cache should be cleared
        assert len(client.cache) == 0
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_disabled(self, unifi_config):
        """Test that cache invalidation can be disabled for POST requests."""
        client = UniFiClient(unifi_config)
        
        # Create mock GET response
        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={"data": "original"})
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock POST response
        mock_post_response = MagicMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"meta": {"rc": "ok"}})
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.post = MagicMock(return_value=mock_post_response)
        
        client.session = mock_session
        client.authenticated = True
        
        # Populate cache with GET request
        await client.get("/api/s/default/stat/device")
        assert len(client.cache) > 0
        
        # Perform write operation with invalidate_cache=False
        await client.post(
            "/api/s/default/rest/device/123",
            json={"enabled": True},
            invalidate_cache=False
        )
        
        # Cache should NOT be cleared
        assert len(client.cache) > 0
    
    @pytest.mark.asyncio
    async def test_cache_with_params_creates_separate_entries(self, unifi_config):
        """Test that requests with different parameters create separate cache entries."""
        client = UniFiClient(unifi_config)
        
        # Create mock responses
        mock_response1 = MagicMock()
        mock_response1.status = 200
        mock_response1.json = AsyncMock(return_value={"data": "switches"})
        mock_response1.raise_for_status = MagicMock()
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)
        
        mock_response2 = MagicMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": "aps"})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        mock_response2.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[mock_response1, mock_response2])
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # Request with first params
        result1 = await client.get(endpoint, {"type": "switch"})
        assert result1 == {"data": "switches"}
        
        # Request with different params - should create new cache entry
        result2 = await client.get(endpoint, {"type": "ap"})
        assert result2 == {"data": "aps"}
        
        # Both should be cached
        assert len(client.cache) == 2
        assert mock_session.get.call_count == 2
        
        # Request with first params again - should use cache
        result3 = await client.get(endpoint, {"type": "switch"})
        assert result3 == {"data": "switches"}
        assert mock_session.get.call_count == 2  # Still 2
    
    @pytest.mark.asyncio
    async def test_cache_disabled_with_use_cache_false(self, unifi_config):
        """Test that cache can be bypassed on a per-request basis."""
        client = UniFiClient(unifi_config)
        
        # Create mock response
        call_count = {"value": 0}
        
        async def mock_json():
            call_count["value"] += 1
            return {"data": f"response_{call_count['value']}"}
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = mock_json
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        endpoint = "/api/s/default/stat/device"
        
        # First request with cache disabled
        result1 = await client.get(endpoint, use_cache=False)
        assert result1 == {"data": "response_1"}
        assert mock_session.get.call_count == 1
        
        # Second request with cache disabled - should hit API again
        result2 = await client.get(endpoint, use_cache=False)
        assert result2 == {"data": "response_2"}
        assert mock_session.get.call_count == 2
        
        # Cache should be empty
        assert len(client.cache) == 0
    
    def test_cache_key_consistency(self, unifi_config):
        """Test that cache keys are generated consistently."""
        client = UniFiClient(unifi_config)
        
        endpoint = "/api/s/default/stat/device"
        params = {"type": "switch", "limit": 10}
        
        # Generate key multiple times
        key1 = client._get_cache_key(endpoint, params)
        key2 = client._get_cache_key(endpoint, params)
        key3 = client._get_cache_key(endpoint, params)
        
        # All should be identical
        assert key1 == key2 == key3
        
        # Key should be a hash (MD5 hex string)
        assert len(key1) == 32
        assert all(c in "0123456789abcdef" for c in key1)



class TestUniFiClientPerformanceOptimizations:
    """Tests for performance optimizations."""
    
    def test_performance_config_initialization(self, unifi_config):
        """Test that performance configuration is properly initialized."""
        server_config = {
            "performance": {
                "connection_timeout": 15,
                "request_timeout": 45,
                "max_concurrent_requests": 20,
                "connection_limit": 200,
                "connection_limit_per_host": 20,
            }
        }
        
        client = UniFiClient(unifi_config, server_config)
        
        assert client.connection_timeout == 15
        assert client.request_timeout == 45
        assert client.max_concurrent_requests == 20
        assert client.connection_limit == 200
        assert client.connection_limit_per_host == 20
    
    def test_performance_config_defaults(self, unifi_config):
        """Test that performance configuration uses defaults when not provided."""
        client = UniFiClient(unifi_config, None)
        
        assert client.connection_timeout == 10
        assert client.request_timeout == 30
        assert client.max_concurrent_requests == 10
        assert client.connection_limit == 100
        assert client.connection_limit_per_host == 10
    
    def test_semaphore_initialization(self, unifi_config):
        """Test that request semaphore is initialized."""
        client = UniFiClient(unifi_config, None)
        
        assert hasattr(client, '_request_semaphore')
        assert client._request_semaphore._value == 10
    
    @pytest.mark.asyncio
    async def test_connection_pooling_configuration(self, unifi_config):
        """Test that connection pooling is configured correctly."""
        server_config = {
            "performance": {
                "connection_limit": 150,
                "connection_limit_per_host": 15,
            }
        }
        
        client = UniFiClient(unifi_config, server_config)
        
        # Mock the session creation and authentication
        with patch('aiohttp.TCPConnector') as mock_connector:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=mock_response)
            
            with patch('aiohttp.ClientSession', return_value=mock_session):
                await client.connect()
                
                # Verify TCPConnector was called with correct parameters
                mock_connector.assert_called_once()
                call_kwargs = mock_connector.call_args[1]
                
                assert call_kwargs['limit'] == 150
                assert call_kwargs['limit_per_host'] == 15
                assert call_kwargs['force_close'] is False  # Keep-alive enabled
                assert call_kwargs['enable_cleanup_closed'] is True
    
    @pytest.mark.asyncio
    async def test_request_timing_logging(self, unifi_config, caplog):
        """Test that request timing is logged."""
        import logging
        
        client = UniFiClient(unifi_config, None)
        
        # Mock session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        # Make request with DEBUG logging enabled
        with caplog.at_level(logging.DEBUG):
            result = await client.get("/api/s/default/stat/device", use_cache=False)
        
        # Check that timing was logged by looking at log records
        timing_logged = False
        for record in caplog.records:
            if hasattr(record, 'duration_ms'):
                timing_logged = True
                assert record.duration_ms >= 0
                break
        
        assert timing_logged, "Request timing was not logged"
    
    @pytest.mark.asyncio
    async def test_slow_request_warning(self, unifi_config, caplog):
        """Test that slow requests trigger a warning."""
        import time
        
        client = UniFiClient(unifi_config, None)
        
        # Mock session and response with delay
        mock_response = AsyncMock()
        mock_response.status = 200
        
        async def slow_json():
            await asyncio.sleep(2.1)  # Simulate slow response
            return {"data": "test"}
        
        mock_response.json = slow_json
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        # Make request
        with caplog.at_level("WARNING"):
            result = await client.get("/api/s/default/stat/device", use_cache=False)
        
        # Check that slow request warning was logged
        assert "Slow GET request detected" in caplog.text
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, unifi_config):
        """Test that concurrent requests are limited by semaphore."""
        import asyncio
        
        client = UniFiClient(unifi_config, None)
        client.max_concurrent_requests = 2
        client._request_semaphore = asyncio.Semaphore(2)
        
        # Track concurrent requests inside the semaphore
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def slow_json():
            """Simulate slow response to allow concurrent tracking."""
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate work
            async with lock:
                concurrent_count -= 1
            return {"data": "test"}
        
        # Mock session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = slow_json
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        client.session = mock_session
        client.authenticated = True
        
        # Launch 5 concurrent requests
        tasks = [client.get("/api/s/default/stat/device", use_cache=False) for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify that no more than 2 requests were concurrent
        assert max_concurrent <= 2
