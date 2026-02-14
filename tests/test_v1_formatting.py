"""Property-based tests for v1 pagination parameter pass-through and formatting invariants.

Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through
Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

Validates: Requirements 10.1, 10.3, 12.2, 12.3
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.config.loader import UniFiConfig
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.tools.firewall import ListFirewallZonesTool, ListFirewallPoliciesTool
from unifi_mcp.tools.resources import ListWANInterfacesTool


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

# Pagination parameters — constrained to valid input space
offsets = st.integers(min_value=0, max_value=10000)
limits = st.integers(min_value=1, max_value=200)

# Filter strings — non-empty, printable ASCII (realistic API filter expressions)
filters = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-=:"),
    min_size=1,
    max_size=50,
)

# Simple data items with UUID ids for formatting invariant tests
simple_items = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))),
})

# V1 response envelope
def v1_response(data_strategy, total_count_strategy=None):
    """Build a v1 response envelope wrapping generated data items."""
    if total_count_strategy is None:
        return st.builds(
            lambda data, offset: {
                "offset": offset,
                "limit": max(len(data), 1),
                "count": len(data),
                "totalCount": len(data) + offset,
                "data": data,
            },
            data=st.lists(data_strategy, max_size=20),
            offset=st.integers(min_value=0, max_value=500),
        )
    return st.builds(
        lambda data, offset, total: {
            "offset": offset,
            "limit": max(len(data), 1),
            "count": len(data),
            "totalCount": total,
            "data": data,
        },
        data=st.lists(data_strategy, max_size=20),
        offset=st.integers(min_value=0, max_value=500),
        total=total_count_strategy,
    )


# Firewall zone items (for full execute-path formatting tests)
firewall_zone_items = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "networkIds": st.lists(uuids, max_size=5),
    "metadata": st.fixed_dictionaries({
        "origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED"])
    }),
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(host: str = "192.168.1.1", port: int = 443) -> UniFiConfig:
    """Create a UniFiConfig for testing."""
    return UniFiConfig(
        host=host,
        port=port,
        username="",
        password="",
        api_key="test-key",
        site="default",
        verify_ssl=False,
        retry={},
    )


# ---------------------------------------------------------------------------
# Property 12: V1 Query Parameter Pass-Through
# Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through
# ---------------------------------------------------------------------------

class TestV1QueryParameterPassThrough:
    """For any valid combination of offset (non-negative int), limit (positive int),
    and filter (non-empty string), get_v1() SHALL include all provided parameters
    in the HTTP request query string without modification.

    **Validates: Requirements 10.1, 10.3**
    """

    @given(offset=offsets, limit=limits, filter_str=filters)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_params_passed_to_http_request(self, offset, limit, filter_str):
        """Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through

        When offset, limit, and filter are all provided, all three must appear
        in the HTTP request params without modification.
        """
        config = _make_config()
        client = UniFiClient(config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "test-site-uuid"

        # Build a mock response context manager
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "offset": offset, "limit": limit, "count": 0,
            "totalCount": 0, "data": [],
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        client.session.get = MagicMock(return_value=mock_response)

        params = {"offset": offset, "limit": limit, "filter": filter_str}

        import unifi_mcp.unifi_client as uc
        original_retry = uc.retry_async

        captured_params = {}

        async def fake_retry(func, *args, config=None):
            # args: (url, endpoint, params)
            captured_params["url"] = args[0]
            captured_params["endpoint"] = args[1]
            captured_params["params"] = args[2]
            return {
                "offset": offset, "limit": limit, "count": 0,
                "totalCount": 0, "data": [],
            }

        async def run():
            uc.retry_async = fake_retry
            try:
                await client.get_v1("firewall/zones", params=params, use_cache=False)
            finally:
                uc.retry_async = original_retry

        asyncio.run(run())

        # Verify all params were passed through without modification
        assert captured_params["params"] is params
        assert captured_params["params"]["offset"] == offset
        assert captured_params["params"]["limit"] == limit
        assert captured_params["params"]["filter"] == filter_str

    @given(offset=offsets)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_offset_only_passed_through(self, offset):
        """Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through

        When only offset is provided, it must appear in the request params.
        """
        config = _make_config()
        client = UniFiClient(config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "test-site-uuid"

        params = {"offset": offset}
        captured = {}

        import unifi_mcp.unifi_client as uc
        original_retry = uc.retry_async

        async def fake_retry(func, *args, config=None):
            captured["params"] = args[2]
            return {"offset": offset, "limit": 25, "count": 0, "totalCount": 0, "data": []}

        async def run():
            uc.retry_async = fake_retry
            try:
                await client.get_v1("devices", params=params, use_cache=False)
            finally:
                uc.retry_async = original_retry

        asyncio.run(run())

        assert captured["params"]["offset"] == offset

    @given(limit=limits)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_limit_only_passed_through(self, limit):
        """Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through

        When only limit is provided, it must appear in the request params.
        """
        config = _make_config()
        client = UniFiClient(config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "test-site-uuid"

        params = {"limit": limit}
        captured = {}

        import unifi_mcp.unifi_client as uc
        original_retry = uc.retry_async

        async def fake_retry(func, *args, config=None):
            captured["params"] = args[2]
            return {"offset": 0, "limit": limit, "count": 0, "totalCount": 0, "data": []}

        async def run():
            uc.retry_async = fake_retry
            try:
                await client.get_v1("clients", params=params, use_cache=False)
            finally:
                uc.retry_async = original_retry

        asyncio.run(run())

        assert captured["params"]["limit"] == limit

    @given(filter_str=filters)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_filter_only_passed_through(self, filter_str):
        """Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through

        When only filter is provided, it must appear in the request params.
        """
        config = _make_config()
        client = UniFiClient(config)
        client.session = MagicMock()
        client.authenticated = True
        client._site_id = "test-site-uuid"

        params = {"filter": filter_str}
        captured = {}

        import unifi_mcp.unifi_client as uc
        original_retry = uc.retry_async

        async def fake_retry(func, *args, config=None):
            captured["params"] = args[2]
            return {"offset": 0, "limit": 25, "count": 0, "totalCount": 0, "data": []}

        async def run():
            uc.retry_async = fake_retry
            try:
                await client.get_v1("networks", params=params, use_cache=False)
            finally:
                uc.retry_async = original_retry

        asyncio.run(run())

        assert captured["params"]["filter"] == filter_str

    @given(offset=offsets, limit=limits, filter_str=filters)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tool_execute_passes_params_to_get_v1(self, offset, limit, filter_str):
        """Feature: unifi-api-v1-migration, Property 12: V1 Query Parameter Pass-Through

        When a list tool is invoked with offset/limit/filter, those params
        must be forwarded to get_v1() as query parameters.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value={
            "offset": offset, "limit": limit, "count": 0,
            "totalCount": 0, "data": [],
        })

        tool = ListFirewallZonesTool()
        asyncio.run(tool.execute(
            mock_client,
            offset=offset,
            limit=limit,
            filter_expr=filter_str,
        ))

        # Verify get_v1 was called with the correct params
        mock_client.get_v1.assert_called_once()
        call_args = mock_client.get_v1.call_args
        passed_params = call_args.kwargs.get("params") or call_args[1] if len(call_args[1]) > 1 else call_args.kwargs.get("params")

        # The tool passes params as a positional or keyword arg
        # Check the actual call: get_v1("firewall/zones", params={...})
        actual_endpoint = call_args[0][0]
        assert actual_endpoint == "firewall/zones"

        # Extract params from the call
        if len(call_args[0]) > 1:
            actual_params = call_args[0][1]
        else:
            actual_params = call_args[1].get("params") if call_args[1] else None

        assert actual_params is not None
        assert actual_params["offset"] == offset
        assert actual_params["limit"] == limit
        assert actual_params["filter"] == filter_str


# ---------------------------------------------------------------------------
# Property 13: V1 Formatting Invariants
# Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants
# ---------------------------------------------------------------------------

class TestV1FormattingInvariants:
    """For any v1 list response with a totalCount field, the formatted tool output
    SHALL contain the totalCount value. For any UUID-format ID in the v1 response
    data, the formatted output SHALL contain that exact UUID string without
    transformation.

    **Validates: Requirements 12.2, 12.3**
    """

    @given(response=v1_response(firewall_zone_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_total_count_present_in_formatted_output(self, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        The formatted output must contain the totalCount from the v1 response.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallZonesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        # format_list stores totalCount as "total"
        assert "total" in result
        assert result["total"] == response["totalCount"]

    @given(
        total_count=st.integers(min_value=0, max_value=10000),
        response=v1_response(firewall_zone_items),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_total_count_value_preserved_exactly(self, total_count, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        The totalCount value must be preserved exactly — not transformed or rounded.
        """
        # Override totalCount with our generated value
        response["totalCount"] = total_count

        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallZonesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["total"] == total_count

    @given(response=v1_response(firewall_zone_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_uuid_ids_preserved_in_formatted_output(self, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        Every UUID-format ID in the v1 response data must appear in the
        formatted output without transformation.
        """
        assume(len(response["data"]) > 0)

        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallZonesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, item in enumerate(response["data"]):
            formatted = result["data"][i]
            # UUID id must be preserved exactly
            assert formatted["id"] == item["id"], (
                f"UUID mismatch at index {i}: expected {item['id']}, got {formatted['id']}"
            )

    @given(response=v1_response(firewall_zone_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_id_uuids_preserved(self, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        UUID networkIds within zone data must be preserved without transformation.
        """
        assume(len(response["data"]) > 0)

        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallZonesTool()
        result = asyncio.run(tool.execute(mock_client))

        for i, item in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["networkIds"] == item["networkIds"], (
                f"networkIds mismatch at index {i}"
            )

    @given(response=v1_response(firewall_zone_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_total_count_in_wan_list_output(self, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        totalCount must be present in WAN interface list tool output as well,
        confirming the invariant holds across different tool types.
        """
        # Enrich items with fields required by WAN formatter
        for item in response["data"]:
            item.setdefault("wanType", "WAN")
            item.setdefault("interface", "eth0")
            item.setdefault("enabled", True)

        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListWANInterfacesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert "total" in result
        assert result["total"] == response["totalCount"]

    @given(response=v1_response(firewall_zone_items))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_uuid_ids_preserved_across_tool_types(self, response):
        """Feature: unifi-api-v1-migration, Property 13: V1 Formatting Invariants

        UUID IDs must be preserved in WAN interface list output — confirming
        the invariant holds across different tool types.
        """
        assume(len(response["data"]) > 0)

        # Enrich items with WAN-required fields
        for item in response["data"]:
            item.setdefault("wanType", "WAN")
            item.setdefault("interface", "eth0")
            item.setdefault("enabled", True)

        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListWANInterfacesTool()
        result = asyncio.run(tool.execute(mock_client))

        for i, item in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == item["id"], (
                f"WAN UUID mismatch at index {i}: expected {item['id']}, got {formatted['id']}"
            )
