"""Property-based tests for firewall zone and policy formatting.

Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

For any valid firewall zone dict (with id, name, networkIds, metadata) or
firewall policy dict (with id, name, enabled, action, source, destination),
the formatter SHALL produce output containing the zone/policy name, ID,
and all required summary fields.

Validates: Requirements 2.1, 2.2, 3.1, 3.2
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.tools.firewall import (
    ListFirewallZonesTool,
    GetFirewallZoneTool,
    ListFirewallPoliciesTool,
    GetFirewallPolicyTool,
)
from unifi_mcp.unifi_client import UniFiClient


# ---------------------------------------------------------------------------
# Hypothesis strategies (from design.md)
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

firewall_zones = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "networkIds": st.lists(uuids, max_size=10),
    "metadata": st.fixed_dictionaries({
        "origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED"])
    }),
})

firewall_policies = st.fixed_dictionaries({
    "id": uuids,
    "enabled": st.booleans(),
    "name": st.text(min_size=1, max_size=100),
    "description": st.text(max_size=200),
    "index": st.integers(min_value=0, max_value=1000),
    "action": st.fixed_dictionaries({
        "type": st.sampled_from(["ALLOW", "BLOCK", "REJECT"]),
        "allowReturnTraffic": st.booleans(),
    }),
    "source": st.fixed_dictionaries({
        "zoneId": uuids,
    }),
    "destination": st.fixed_dictionaries({
        "zoneId": uuids,
    }),
    "metadata": st.fixed_dictionaries({
        "origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED", "DERIVED"])
    }),
})

# V1 response envelope wrapping a list of items
def v1_response(data_strategy):
    return st.builds(
        lambda data, offset: {
            "offset": offset,
            "limit": max(len(data), 1),
            "count": len(data),
            "totalCount": len(data) + offset,
            "data": data,
        },
        data=st.lists(data_strategy, min_size=1, max_size=20),
        offset=st.integers(min_value=0, max_value=100),
    )


# ---------------------------------------------------------------------------
# Property 5a: Zone Summary Formatting
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestZoneSummaryFormattingProperty:
    """For any valid firewall zone dict, _format_zone_summary SHALL produce
    output containing the zone name, ID, networkIds, and origin.

    **Validates: Requirements 2.1**
    """

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_summary_contains_required_fields(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The zone summary must contain id, name, networkIds, and origin.
        """
        tool = ListFirewallZonesTool()
        result = tool._format_zone_summary(zone)

        assert "id" in result
        assert "name" in result
        assert "networkIds" in result
        assert "origin" in result

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_summary_preserves_id(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The zone ID in the output must match the input ID exactly (UUID preserved).
        """
        tool = ListFirewallZonesTool()
        result = tool._format_zone_summary(zone)

        assert result["id"] == zone["id"]

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_summary_preserves_name(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The zone name in the output must match the input name exactly.
        """
        tool = ListFirewallZonesTool()
        result = tool._format_zone_summary(zone)

        assert result["name"] == zone["name"]

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_summary_preserves_network_ids(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The networkIds list must match the input exactly.
        """
        tool = ListFirewallZonesTool()
        result = tool._format_zone_summary(zone)

        assert result["networkIds"] == zone["networkIds"]

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_summary_maps_origin_correctly(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        SYSTEM_DEFINED maps to 'system-defined', USER_DEFINED maps to 'user-defined'.
        """
        tool = ListFirewallZonesTool()
        result = tool._format_zone_summary(zone)

        origin_raw = zone["metadata"]["origin"]
        if origin_raw == "SYSTEM_DEFINED":
            assert result["origin"] == "system-defined"
        elif origin_raw == "USER_DEFINED":
            assert result["origin"] == "user-defined"


# ---------------------------------------------------------------------------
# Property 5b: Zone Detail Formatting
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestZoneDetailFormattingProperty:
    """For any valid firewall zone dict, _format_zone_details SHALL produce
    output containing the zone name, ID, networkIds, origin, and metadata.

    **Validates: Requirements 2.2**
    """

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_details_contains_all_fields(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Zone details must include id, name, networkIds, origin, and metadata.
        """
        tool = GetFirewallZoneTool()
        result = tool._format_zone_details(zone)

        assert "id" in result
        assert "name" in result
        assert "networkIds" in result
        assert "origin" in result
        assert "metadata" in result

    @given(zone=firewall_zones)
    @settings(max_examples=100)
    def test_zone_details_preserves_id_and_name(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting"""
        tool = GetFirewallZoneTool()
        result = tool._format_zone_details(zone)

        assert result["id"] == zone["id"]
        assert result["name"] == zone["name"]
        assert result["networkIds"] == zone["networkIds"]
        assert result["metadata"] == zone["metadata"]


# ---------------------------------------------------------------------------
# Property 5c: Policy Summary Formatting
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestPolicySummaryFormattingProperty:
    """For any valid firewall policy dict, _format_policy_summary SHALL produce
    output containing the policy name, ID, enabled state, action type,
    source zone ID, destination zone ID, and protocol scope.

    **Validates: Requirements 3.1**
    """

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_summary_contains_required_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Policy summary must contain id, name, enabled, actionType,
        sourceZoneId, destinationZoneId, and protocolScope.
        """
        tool = ListFirewallPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert "id" in result
        assert "name" in result
        assert "enabled" in result
        assert "actionType" in result
        assert "sourceZoneId" in result
        assert "destinationZoneId" in result
        assert "protocolScope" in result

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_summary_preserves_id_and_name(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Policy ID and name must be preserved exactly.
        """
        tool = ListFirewallPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["id"] == policy["id"]
        assert result["name"] == policy["name"]

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_summary_preserves_enabled_state(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The enabled boolean must match the input exactly.
        """
        tool = ListFirewallPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["enabled"] == policy["enabled"]

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_summary_extracts_action_type(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The actionType must match the action.type from the input.
        """
        tool = ListFirewallPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["actionType"] == policy["action"]["type"]

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_summary_extracts_zone_ids(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Source and destination zone IDs must match the input.
        """
        tool = ListFirewallPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["sourceZoneId"] == policy["source"]["zoneId"]
        assert result["destinationZoneId"] == policy["destination"]["zoneId"]


# ---------------------------------------------------------------------------
# Property 5d: Policy Detail Formatting
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestPolicyDetailFormattingProperty:
    """For any valid firewall policy dict, _format_policy_details SHALL produce
    output containing all required detail fields.

    **Validates: Requirements 3.2**
    """

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_details_contains_all_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Policy details must include id, name, description, enabled, index,
        action, source, destination, and metadata.
        """
        tool = GetFirewallPolicyTool()
        result = tool._format_policy_details(policy)

        assert "id" in result
        assert "name" in result
        assert "description" in result
        assert "enabled" in result
        assert "index" in result
        assert "action" in result
        assert "source" in result
        assert "destination" in result
        assert "metadata" in result

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_details_preserves_core_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Core fields (id, name, enabled, index) must be preserved exactly.
        """
        tool = GetFirewallPolicyTool()
        result = tool._format_policy_details(policy)

        assert result["id"] == policy["id"]
        assert result["name"] == policy["name"]
        assert result["enabled"] == policy["enabled"]
        assert result["index"] == policy["index"]

    @given(policy=firewall_policies)
    @settings(max_examples=100)
    def test_policy_details_preserves_action_and_zones(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        Action, source, and destination dicts must be preserved.
        """
        tool = GetFirewallPolicyTool()
        result = tool._format_policy_details(policy)

        assert result["action"] == policy["action"]
        assert result["source"] == policy["source"]
        assert result["destination"] == policy["destination"]
        assert result["metadata"] == policy["metadata"]


# ---------------------------------------------------------------------------
# Property 5e: Full Execute Path — Zone List
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestZoneListExecuteProperty:
    """For any valid v1 response containing zone data, the full execute path
    SHALL produce a successful result with all zones formatted correctly.

    **Validates: Requirements 2.1**
    """

    @given(response=v1_response(firewall_zones))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_zone_list_execute_returns_all_zones(self, response):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The execute path must return all zones from the response with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallZonesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, zone_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == zone_data["id"]
            assert formatted["name"] == zone_data["name"]
            assert formatted["networkIds"] == zone_data["networkIds"]
            assert formatted["origin"] in ("system-defined", "user-defined")


# ---------------------------------------------------------------------------
# Property 5f: Full Execute Path — Policy List
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestPolicyListExecuteProperty:
    """For any valid v1 response containing policy data, the full execute path
    SHALL produce a successful result with all policies formatted correctly.

    **Validates: Requirements 3.1**
    """

    @given(response=v1_response(firewall_policies))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_policy_list_execute_returns_all_policies(self, response):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The execute path must return all policies from the response with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListFirewallPoliciesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, policy_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == policy_data["id"]
            assert formatted["name"] == policy_data["name"]
            assert formatted["enabled"] == policy_data["enabled"]
            assert formatted["actionType"] == policy_data["action"]["type"]
            assert formatted["sourceZoneId"] == policy_data["source"]["zoneId"]
            assert formatted["destinationZoneId"] == policy_data["destination"]["zoneId"]


# ---------------------------------------------------------------------------
# Property 5g: Full Execute Path — Zone Detail
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestZoneDetailExecuteProperty:
    """For any valid zone dict, the GetFirewallZoneTool execute path SHALL
    produce a successful detail result with all zone fields.

    **Validates: Requirements 2.2**
    """

    @given(zone=firewall_zones)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_zone_detail_execute_returns_formatted_zone(self, zone):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The execute path must return zone details with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=zone)

        tool = GetFirewallZoneTool()
        result = asyncio.run(tool.execute(mock_client, zone_id=zone["id"]))

        assert result["success"] is True
        assert result["type"] == "firewall_zone"
        assert result["data"]["id"] == zone["id"]
        assert result["data"]["name"] == zone["name"]
        assert result["data"]["networkIds"] == zone["networkIds"]


# ---------------------------------------------------------------------------
# Property 5h: Full Execute Path — Policy Detail
# Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting
# ---------------------------------------------------------------------------

class TestPolicyDetailExecuteProperty:
    """For any valid policy dict, the GetFirewallPolicyTool execute path SHALL
    produce a successful detail result with all policy fields.

    **Validates: Requirements 3.2**
    """

    @given(policy=firewall_policies)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_policy_detail_execute_returns_formatted_policy(self, policy):
        """Feature: unifi-api-v1-migration, Property 5: Firewall Zone and Policy Formatting

        The execute path must return policy details with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=policy)

        tool = GetFirewallPolicyTool()
        result = asyncio.run(tool.execute(mock_client, policy_id=policy["id"]))

        assert result["success"] is True
        assert result["type"] == "firewall_policy"
        assert result["data"]["id"] == policy["id"]
        assert result["data"]["name"] == policy["name"]
        assert result["data"]["enabled"] == policy["enabled"]
        assert result["data"]["action"] == policy["action"]
        assert result["data"]["source"] == policy["source"]
        assert result["data"]["destination"] == policy["destination"]
