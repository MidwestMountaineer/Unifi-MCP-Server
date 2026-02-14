"""Tests for UniFi v1 API client extensions.

Tests for resolve_site_id(), _build_v1_url(), get_v1(), and _get_v1_with_auth()
added to UniFiClient for the v1 integration API migration.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import aiohttp

from unifi_mcp.config.loader import UniFiConfig
from unifi_mcp.unifi_client import (
    UniFiClient,
    UniFiClientError,
    AuthenticationError,
    ConnectionError,
    TimeoutError,
    RateLimitError,
    SessionExpiredError,
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
        retry={},
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
        retry={},
    )


class TestSiteIdField:
    """Tests for _site_id instance variable initialization."""

    def test_site_id_initialized_to_none(self, unifi_config):
        client = UniFiClient(unifi_config)
        assert client._site_id is None

    def test_site_id_initialized_to_none_with_api_key(self, unifi_config_with_api_key):
        client = UniFiClient(unifi_config_with_api_key)
        assert client._site_id is None


class TestBuildV1Url:
    """Tests for _build_v1_url() method."""

    def test_site_scoped_endpoint(self, unifi_config):
        client = UniFiClient(unifi_config)
        client._site_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        url = client._build_v1_url("firewall/zones")
        assert url == (
            "https://192.168.1.1:443/proxy/network/integration"
            "/v1/sites/a1b2c3d4-e5f6-7890-abcd-ef1234567890/firewall/zones"
        )

    def test_site_scoped_endpoint_with_leading_slash(self, unifi_config):
        client = UniFiClient(unifi_config)
        client._site_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        url = client._build_v1_url("/firewall/policies")
        assert url == (
            "https://192.168.1.1:443/proxy/network/integration"
            "/v1/sites/a1b2c3d4-e5f6-7890-abcd-ef1234567890/firewall/policies"
        )

    def test_site_independent_endpoint(self, unifi_config):
        client = UniFiClient(unifi_config)
        # _site_id not needed for site-independent endpoints

        url = client._build_v1_url("/v1/sites")
        assert url == "https://192.168.1.1:443/proxy/network/integration/v1/sites"

    def test_site_independent_info_endpoint(self, unifi_config):
        client = UniFiClient(unifi_config)

        url = client._build_v1_url("/v1/info")
        assert url == "https://192.168.1.1:443/proxy/network/integration/v1/info"

    def test_nested_site_scoped_endpoint(self, unifi_config):
        client = UniFiClient(unifi_config)
        client._site_id = "site-uuid-123"

        url = client._build_v1_url("firewall/policies/ordering")
        assert url == (
            "https://192.168.1.1:443/proxy/network/integration"
            "/v1/sites/site-uuid-123/firewall/policies/ordering"
        )

    def test_custom_port(self):
        config = UniFiConfig(
            host="10.0.0.1",
            port=8443,
            username="admin",
            password="pass",
            site="default",
            verify_ssl=False,
            retry={},
        )
        client = UniFiClient(config)
        client._site_id = "uuid-abc"

        url = client._build_v1_url("devices")
        assert url == (
            "https://10.0.0.1:8443/proxy/network/integration"
            "/v1/sites/uuid-abc/devices"
        )


class TestResolveSiteId:
    """Tests for resolve_site_id() method."""

    async def test_returns_cached_site_id(self, unifi_config):
        """If _site_id is already set, return it without making a request."""
        client = UniFiClient(unifi_config)
        client._site_id = "cached-uuid-123"

        result = await client.resolve_site_id()
        assert result == "cached-uuid-123"

    async def test_raises_when_not_connected(self, unifi_config):
        """Should raise UniFiClientError when session is None."""
        client = UniFiClient(unifi_config)
        assert client.session is None

        with pytest.raises(UniFiClientError, match="Not connected"):
            await client.resolve_site_id()

    async def test_resolves_from_list_response(self, unifi_config):
        """Resolves site ID from a list response (array of sites)."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {"id": "site-uuid-abc", "name": "Default"},
            {"id": "site-uuid-def", "name": "Other"},
        ])
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        result = await client.resolve_site_id()
        assert result == "site-uuid-abc"
        assert client._site_id == "site-uuid-abc"

    async def test_resolves_from_data_envelope(self, unifi_config):
        """Resolves site ID from a v1 envelope response with 'data' field."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [{"id": "envelope-uuid", "name": "MySite"}],
        })
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        result = await client.resolve_site_id()
        assert result == "envelope-uuid"

    async def test_raises_on_empty_sites(self, unifi_config):
        """Should raise UniFiClientError when no sites are returned."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(UniFiClientError, match="No sites found"):
            await client.resolve_site_id()

    async def test_raises_auth_error_on_401(self, unifi_config):
        """Should raise AuthenticationError on 401 response."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await client.resolve_site_id()

    async def test_raises_auth_error_on_403(self, unifi_config):
        """Should raise AuthenticationError on 403 response."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await client.resolve_site_id()

    async def test_caches_after_first_resolution(self, unifi_config):
        """Second call should return cached value without making a request."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {"id": "cached-uuid", "name": "Default"},
        ])
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        # First call resolves
        result1 = await client.resolve_site_id()
        assert result1 == "cached-uuid"

        # Second call returns cached — no additional HTTP call
        result2 = await client.resolve_site_id()
        assert result2 == "cached-uuid"
        assert mock_session.get.call_count == 1


class TestGetV1:
    """Tests for get_v1() method."""

    async def test_raises_when_not_connected(self, unifi_config):
        client = UniFiClient(unifi_config)
        with pytest.raises(UniFiClientError, match="Not connected"):
            await client.get_v1("firewall/zones")

    async def test_resolves_site_id_for_scoped_endpoint(self, unifi_config):
        """get_v1 should call resolve_site_id for site-scoped endpoints."""
        client = UniFiClient(unifi_config)
        client.session = MagicMock()  # non-None session
        client.authenticated = True

        with patch.object(client, "resolve_site_id", new_callable=AsyncMock, return_value="uuid-123") as mock_resolve, \
             patch.object(client, "_get_v1_with_auth", new_callable=AsyncMock, return_value={"data": []}) as mock_get, \
             patch("unifi_mcp.unifi_client.retry_async", new_callable=AsyncMock, return_value={"data": []}):
            await client.get_v1("firewall/zones", use_cache=False)
            mock_resolve.assert_awaited_once()

    async def test_skips_site_id_for_independent_endpoint(self, unifi_config):
        """get_v1 should NOT call resolve_site_id for /v1/ endpoints."""
        client = UniFiClient(unifi_config)
        client.session = MagicMock()
        client.authenticated = True

        with patch.object(client, "resolve_site_id", new_callable=AsyncMock) as mock_resolve, \
             patch("unifi_mcp.unifi_client.retry_async", new_callable=AsyncMock, return_value={"data": []}):
            await client.get_v1("/v1/sites", use_cache=False)
            mock_resolve.assert_not_awaited()

    async def test_caches_v1_response(self, unifi_config):
        """get_v1 should cache responses and return cached on second call."""
        client = UniFiClient(unifi_config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "uuid-123"

        response_data = {"data": [{"id": "zone-1"}], "totalCount": 1}

        with patch("unifi_mcp.unifi_client.retry_async", new_callable=AsyncMock, return_value=response_data) as mock_retry:
            # First call — cache miss
            result1 = await client.get_v1("firewall/zones")
            assert result1 == response_data
            assert mock_retry.await_count == 1

            # Second call — cache hit
            result2 = await client.get_v1("firewall/zones")
            assert result2 == response_data
            assert mock_retry.await_count == 1  # no additional call

    async def test_bypasses_cache_when_disabled(self, unifi_config):
        """get_v1 with use_cache=False should always make a request."""
        client = UniFiClient(unifi_config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "uuid-123"

        response_data = {"data": []}

        with patch("unifi_mcp.unifi_client.retry_async", new_callable=AsyncMock, return_value=response_data) as mock_retry:
            await client.get_v1("firewall/zones", use_cache=False)
            await client.get_v1("firewall/zones", use_cache=False)
            assert mock_retry.await_count == 2


class TestGetV1WithAuth:
    """Tests for _get_v1_with_auth() internal method."""

    async def test_successful_request(self, unifi_config):
        """Successful v1 GET returns parsed JSON."""
        client = UniFiClient(unifi_config)
        client.authenticated = True

        response_data = {"data": [{"id": "z1"}], "totalCount": 1, "offset": 0, "limit": 25, "count": 1}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        result = await client._get_v1_with_auth(
            "https://192.168.1.1:443/proxy/network/integration/v1/sites/uuid/firewall/zones",
            "firewall/zones",
        )
        assert result == response_data

    async def test_401_raises_session_expired(self, unifi_config):
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(SessionExpiredError):
            await client._get_v1_with_auth("https://host/url", "endpoint")
        assert client.authenticated is False

    async def test_403_raises_auth_error(self, unifi_config):
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(AuthenticationError, match="Insufficient permissions"):
            await client._get_v1_with_auth("https://host/url", "endpoint")

    async def test_404_raises_client_error(self, unifi_config):
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(UniFiClientError, match="Resource not found"):
            await client._get_v1_with_auth("https://host/url", "firewall/zones/bad-id")

    async def test_429_raises_rate_limit(self, unifi_config):
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await client._get_v1_with_auth("https://host/url", "endpoint")

    async def test_500_raises_connection_error(self, unifi_config):
        client = UniFiClient(unifi_config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(ConnectionError, match="Server error 500"):
            await client._get_v1_with_auth("https://host/url", "endpoint")


class TestLegacyUnchanged:
    """Verify that legacy get() and _build_url() remain unchanged."""

    def test_build_url_still_works(self, unifi_config):
        """Legacy _build_url should still produce the same URLs."""
        client = UniFiClient(unifi_config)
        url = client._build_url("/api/s/{site}/stat/device")
        assert url == "https://192.168.1.1:443/api/s/default/stat/device"

    def test_build_url_with_api_key(self, unifi_config_with_api_key):
        """API key base URL includes /proxy/network."""
        client = UniFiClient(unifi_config_with_api_key)
        url = client._build_url("/api/s/{site}/stat/device")
        assert url == "https://192.168.1.1:443/proxy/network/api/s/default/stat/device"
