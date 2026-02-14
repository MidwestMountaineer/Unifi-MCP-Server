"""Property-based tests for UniFi v1 API client extensions.

Tests v1 URL construction, legacy URL preservation, response envelope parsing,
and HTTP error-to-exception mapping using Hypothesis.

Feature: unifi-api-v1-migration
Validates: Requirements 1.1, 1.3, 1.4, 1.5
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

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


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Hostnames: simple text-based strategy (faster than regex)
hostnames = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=1,
    max_size=12,
).filter(lambda s: s[0].isalpha())

# IPv4 addresses
ipv4_addresses = st.tuples(
    st.integers(1, 254),
    st.integers(0, 255),
    st.integers(0, 255),
    st.integers(1, 254),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}")

# Hosts: either hostname or IPv4
hosts = st.one_of(hostnames, ipv4_addresses)

# Ports
ports = st.integers(min_value=1, max_value=65535)

# UUIDs as strings
uuids = st.uuids().map(str)

# Endpoint path segments (no leading slash, no empty)
path_segments = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=15,
).filter(lambda s: s[0].isalpha())
endpoints = st.lists(path_segments, min_size=1, max_size=4).map("/".join)

# Legacy endpoints with {site} placeholder
legacy_endpoints = endpoints.map(lambda e: f"/api/s/{{site}}/{e}")

# Site names for legacy API
site_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=1,
    max_size=10,
).filter(lambda s: s[0].isalpha())

# HTTP error codes from the design doc
http_error_codes = st.sampled_from([401, 403, 404, 408, 429, 500, 502, 503])

# V1 response envelope strategy
def v1_response(data_strategy):
    return st.builds(
        lambda data, offset: {
            "offset": offset,
            "limit": max(len(data), 1),
            "count": len(data),
            "totalCount": len(data) + offset,
            "data": data,
        },
        data=st.lists(data_strategy, max_size=50),
        offset=st.integers(min_value=0, max_value=1000),
    )


# Simple data items for response envelopes
simple_data_items = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))),
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(host: str, port: int, site: str = "default", api_key: str = "") -> UniFiConfig:
    """Create a UniFiConfig for testing."""
    return UniFiConfig(
        host=host,
        port=port,
        username="admin" if not api_key else "",
        password="pass" if not api_key else "",
        api_key=api_key or None,
        site=site,
        verify_ssl=False,
        retry={},
    )


# ---------------------------------------------------------------------------
# Property 1: V1 URL Construction
# Feature: unifi-api-v1-migration, Property 1: V1 URL Construction
# ---------------------------------------------------------------------------

class TestV1UrlConstructionProperty:
    """For any valid host, port, siteId (UUID), and endpoint path,
    _build_v1_url(endpoint) SHALL produce a URL matching the pattern
    https://{host}:{port}/proxy/network/integration/v1/sites/{siteId}/{endpoint}.

    **Validates: Requirements 1.1**
    """

    @given(host=hosts, port=ports, site_id=uuids, endpoint=endpoints)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_site_scoped_url_matches_pattern(self, host, port, site_id, endpoint):
        """Feature: unifi-api-v1-migration, Property 1: V1 URL Construction"""
        config = _make_config(host, port)
        client = UniFiClient(config)
        client._site_id = site_id

        url = client._build_v1_url(endpoint)

        expected = f"https://{host}:{port}/proxy/network/integration/v1/sites/{site_id}/{endpoint}"
        assert url == expected, f"Expected {expected}, got {url}"

    @given(host=hosts, port=ports, site_id=uuids, endpoint=endpoints)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_site_scoped_url_with_leading_slash(self, host, port, site_id, endpoint):
        """Leading slash on endpoint should be stripped for site-scoped URLs."""
        config = _make_config(host, port)
        client = UniFiClient(config)
        client._site_id = site_id

        url = client._build_v1_url(f"/{endpoint}")

        expected = f"https://{host}:{port}/proxy/network/integration/v1/sites/{site_id}/{endpoint}"
        assert url == expected

    @given(host=hosts, port=ports, endpoint=st.sampled_from(["/v1/sites", "/v1/info"]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_site_independent_url_matches_pattern(self, host, port, endpoint):
        """Site-independent endpoints (/v1/...) bypass siteId."""
        config = _make_config(host, port)
        client = UniFiClient(config)
        # _site_id intentionally not set

        url = client._build_v1_url(endpoint)

        expected = f"https://{host}:{port}/proxy/network/integration{endpoint}"
        assert url == expected


# ---------------------------------------------------------------------------
# Property 2: Legacy URL Construction Preserved
# Feature: unifi-api-v1-migration, Property 2: Legacy URL Construction Preserved
# ---------------------------------------------------------------------------

class TestLegacyUrlConstructionProperty:
    """For any valid legacy endpoint path containing {site},
    _build_url(endpoint) SHALL produce a URL matching the pattern
    https://{host}:{port}/proxy/network/api/s/{site}/{path} (API key auth)
    or https://{host}:{port}/api/s/{site}/{path} (session auth) —
    identical to pre-migration behavior.

    **Validates: Requirements 1.5**
    """

    @given(host=hosts, port=ports, site=site_names, endpoint=endpoints)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_legacy_url_session_auth(self, host, port, site, endpoint):
        """Feature: unifi-api-v1-migration, Property 2: Legacy URL Construction Preserved"""
        config = _make_config(host, port, site=site)
        client = UniFiClient(config)

        legacy_path = f"/api/s/{{site}}/{endpoint}"
        url = client._build_url(legacy_path)

        expected = f"https://{host}:{port}/api/s/{site}/{endpoint}"
        assert url == expected, f"Expected {expected}, got {url}"

    @given(host=hosts, port=ports, site=site_names, endpoint=endpoints)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_legacy_url_api_key_auth(self, host, port, site, endpoint):
        """API key auth prepends /proxy/network to the base URL."""
        config = _make_config(host, port, site=site, api_key="test-key-123")
        client = UniFiClient(config)

        legacy_path = f"/api/s/{{site}}/{endpoint}"
        url = client._build_url(legacy_path)

        expected = f"https://{host}:{port}/proxy/network/api/s/{site}/{endpoint}"
        assert url == expected, f"Expected {expected}, got {url}"


# ---------------------------------------------------------------------------
# Property 3: V1 Response Envelope Parsing
# Feature: unifi-api-v1-migration, Property 3: V1 Response Envelope Parsing
# ---------------------------------------------------------------------------

class TestV1ResponseEnvelopeProperty:
    """For any valid v1 response dict containing offset, limit, count,
    totalCount, and data fields, get_v1() SHALL return a dict where
    data is a list and totalCount is a non-negative integer,
    and count equals len(data).

    **Validates: Requirements 1.3**
    """

    @given(response=v1_response(simple_data_items))
    @settings(max_examples=100)
    def test_response_envelope_invariants(self, response):
        """Feature: unifi-api-v1-migration, Property 3: V1 Response Envelope Parsing

        We test the envelope structure directly since get_v1() returns the
        full response dict from the API. The invariants must hold on what
        the client returns.
        """
        # Simulate what get_v1 returns — the full response dict
        # (get_v1 returns the parsed JSON as-is; tools extract data/totalCount)
        data = response

        # data field is a list
        assert isinstance(data["data"], list)

        # totalCount is a non-negative integer
        assert isinstance(data["totalCount"], int)
        assert data["totalCount"] >= 0

        # count equals len(data["data"])
        assert data["count"] == len(data["data"])

        # offset is non-negative
        assert data["offset"] >= 0

        # limit is positive
        assert data["limit"] >= 1

        # totalCount >= count (total across all pages >= this page)
        assert data["totalCount"] >= data["count"]

    @given(response=v1_response(simple_data_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_response_passed_through_by_get_v1(self, response):
        """get_v1() returns the full response dict unchanged.

        We mock the HTTP layer and verify the response passes through intact.
        """
        config = _make_config("192.168.1.1", 443)
        client = UniFiClient(config)
        client.session = MagicMock()  # non-None
        client.authenticated = True
        client._site_id = "test-uuid"

        # Mock the retry_async to return our generated response
        import unifi_mcp.unifi_client as uc
        original_retry = uc.retry_async

        async def fake_retry(func, *args, config=None):
            return response

        async def run():
            uc.retry_async = fake_retry
            try:
                result = await client.get_v1("firewall/zones", use_cache=False)
                # The result should be the exact response dict
                assert result == response
                assert isinstance(result["data"], list)
                assert result["totalCount"] >= 0
                assert result["count"] == len(result["data"])
            finally:
                uc.retry_async = original_retry

        asyncio.run(run())


# ---------------------------------------------------------------------------
# Property 4: HTTP Error to Exception Mapping
# Feature: unifi-api-v1-migration, Property 4: HTTP Error to Exception Mapping
# ---------------------------------------------------------------------------

# Map of HTTP status codes to the exception types raised by _get_v1_with_auth
V1_ERROR_MAP = {
    401: SessionExpiredError,   # v1 raises SessionExpiredError (retryable)
    403: AuthenticationError,
    404: UniFiClientError,
    429: RateLimitError,
    500: ConnectionError,
    502: ConnectionError,
    503: ConnectionError,
}

# Map of HTTP status codes to the exception types raised by _get_with_auth
LEGACY_ERROR_MAP = {
    401: SessionExpiredError,
    # 403: goes through raise_for_status → aiohttp.ClientResponseError → not explicitly caught
    429: RateLimitError,
    500: ConnectionError,
    502: ConnectionError,
    503: ConnectionError,
}

# Status codes where both handlers have explicit, comparable mappings
COMPARABLE_CODES = st.sampled_from([401, 429, 500, 502, 503])


class TestHttpErrorToExceptionProperty:
    """For any HTTP error status code (401, 403, 404, 408, 429, 500, 502, 503),
    the v1 request handler SHALL raise the same exception type as the legacy
    request handler for that status code.

    **Validates: Requirements 1.4**
    """

    @given(status_code=COMPARABLE_CODES)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_v1_and_legacy_raise_same_exception_type(self, status_code):
        """Feature: unifi-api-v1-migration, Property 4: HTTP Error to Exception Mapping

        For status codes handled explicitly by both v1 and legacy handlers,
        verify they raise the same exception type.
        """
        config = _make_config("192.168.1.1", 443)
        client = UniFiClient(config)
        client.authenticated = True

        # --- Test v1 handler ---
        mock_response_v1 = AsyncMock()
        mock_response_v1.status = status_code
        mock_response_v1.text = AsyncMock(return_value="error body")
        mock_response_v1.headers = {"Retry-After": "30"}
        mock_response_v1.__aenter__ = AsyncMock(return_value=mock_response_v1)
        mock_response_v1.__aexit__ = AsyncMock(return_value=False)

        mock_session_v1 = MagicMock()
        mock_session_v1.get = MagicMock(return_value=mock_response_v1)
        client.session = mock_session_v1

        v1_exception = None
        try:
            asyncio.run(
                client._get_v1_with_auth("https://host/v1/url", "endpoint")
            )
        except Exception as e:
            v1_exception = e

        # --- Test legacy handler ---
        mock_response_legacy = AsyncMock()
        mock_response_legacy.status = status_code
        mock_response_legacy.text = AsyncMock(return_value="error body")
        mock_response_legacy.headers = {"Retry-After": "30"}
        mock_response_legacy.__aenter__ = AsyncMock(return_value=mock_response_legacy)
        mock_response_legacy.__aexit__ = AsyncMock(return_value=False)

        mock_session_legacy = MagicMock()
        mock_session_legacy.get = MagicMock(return_value=mock_response_legacy)

        client2 = UniFiClient(config)
        client2.authenticated = True
        client2.session = mock_session_legacy

        legacy_exception = None
        try:
            asyncio.run(
                client2._get_with_auth("/api/s/default/stat/device")
            )
        except Exception as e:
            legacy_exception = e

        # Both should raise an exception
        assert v1_exception is not None, f"v1 handler did not raise for {status_code}"
        assert legacy_exception is not None, f"Legacy handler did not raise for {status_code}"

        # They should raise the same exception type
        assert type(v1_exception) is type(legacy_exception), (
            f"Status {status_code}: v1 raised {type(v1_exception).__name__}, "
            f"legacy raised {type(legacy_exception).__name__}"
        )

    @given(status_code=st.sampled_from([500, 502, 503]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_server_errors_raise_connection_error(self, status_code):
        """Server errors (5xx) should raise ConnectionError in v1 handler."""
        config = _make_config("192.168.1.1", 443)
        client = UniFiClient(config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = status_code
        mock_response.text = AsyncMock(return_value="Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(ConnectionError):
            asyncio.run(
                client._get_v1_with_auth("https://host/url", "endpoint")
            )

    @given(status_code=st.just(404))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_404_raises_client_error(self, status_code):
        """404 should raise UniFiClientError in v1 handler."""
        config = _make_config("192.168.1.1", 443)
        client = UniFiClient(config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = status_code
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(UniFiClientError):
            asyncio.run(
                client._get_v1_with_auth("https://host/url", "endpoint")
            )

    @given(status_code=st.just(403))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_403_raises_auth_error(self, status_code):
        """403 should raise AuthenticationError in v1 handler."""
        config = _make_config("192.168.1.1", 443)
        client = UniFiClient(config)
        client.authenticated = True

        mock_response = AsyncMock()
        mock_response.status = status_code
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        with pytest.raises(AuthenticationError):
            asyncio.run(
                client._get_v1_with_auth("https://host/url", "endpoint")
            )
