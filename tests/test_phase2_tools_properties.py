"""Property-based tests for ACL, DNS, and traffic matching list formatting.

Feature: unifi-api-v1-migration, Properties 6, 7, 8

Property 6: ACL Rule Formatting — For any valid ACL rule dict, verify output
contains name, type, enabled, action, index.

Property 7: DNS Policy Formatting — For any valid DNS policy dict, verify
output contains ID and name.

Property 8: Traffic Matching List Formatting — For any valid traffic matching
list dict, verify output contains ID and name.

Validates: Requirements 4.1, 4.2, 5.1, 5.2, 6.1, 6.2
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.tools.acl import ListACLRulesTool, GetACLRuleTool
from unifi_mcp.tools.dns import ListDNSPoliciesTool, GetDNSPolicyTool
from unifi_mcp.tools.firewall import ListTrafficMatchingListsTool, GetTrafficMatchingListTool
from unifi_mcp.unifi_client import UniFiClient


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

acl_rules = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "type": st.sampled_from(["IPV4", "MAC"]),
    "enabled": st.booleans(),
    "action": st.sampled_from(["ALLOW", "BLOCK"]),
    "index": st.integers(min_value=0, max_value=1000),
    "description": st.text(max_size=200),
    "enforcingDeviceFilter": st.just({}),
    "sourceFilter": st.one_of(st.none(), st.just({})),
    "destinationFilter": st.one_of(st.none(), st.just({})),
    "protocolFilter": st.lists(st.text(min_size=1, max_size=10), max_size=5),
    "metadata": st.fixed_dictionaries({"origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED"])}),
})

dns_policies = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "enabled": st.booleans(),
    "description": st.text(max_size=200),
    "metadata": st.fixed_dictionaries({"origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED"])}),
})

traffic_matching_lists = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "type": st.text(min_size=1, max_size=20),
    "description": st.text(max_size=200),
    "metadata": st.fixed_dictionaries({"origin": st.sampled_from(["SYSTEM_DEFINED", "USER_DEFINED"])}),
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


# ===========================================================================
# Property 6: ACL Rule Formatting
# Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 6a: ACL Rule Summary Formatting
# ---------------------------------------------------------------------------

class TestACLRuleSummaryFormattingProperty:
    """For any valid ACL rule dict, _format_rule_summary SHALL produce
    output containing the rule name, type, enabled state, action, and index.

    **Validates: Requirements 4.1**
    """

    @given(rule=acl_rules)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_acl_summary_contains_required_fields(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The ACL rule summary must contain id, name, type, enabled, action, and index.
        """
        tool = ListACLRulesTool()
        result = tool._format_rule_summary(rule)

        assert "id" in result
        assert "name" in result
        assert "type" in result
        assert "enabled" in result
        assert "action" in result
        assert "index" in result

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_summary_preserves_id_and_name(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The rule ID and name in the output must match the input exactly.
        """
        tool = ListACLRulesTool()
        result = tool._format_rule_summary(rule)

        assert result["id"] == rule["id"]
        assert result["name"] == rule["name"]

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_summary_preserves_type_and_action(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The type and action must match the input exactly.
        """
        tool = ListACLRulesTool()
        result = tool._format_rule_summary(rule)

        assert result["type"] == rule["type"]
        assert result["action"] == rule["action"]

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_summary_preserves_enabled_and_index(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The enabled state and index must match the input exactly.
        """
        tool = ListACLRulesTool()
        result = tool._format_rule_summary(rule)

        assert result["enabled"] == rule["enabled"]
        assert result["index"] == rule["index"]


# ---------------------------------------------------------------------------
# Property 6b: ACL Rule Detail Formatting
# ---------------------------------------------------------------------------

class TestACLRuleDetailFormattingProperty:
    """For any valid ACL rule dict, _format_rule_details SHALL produce
    output containing all required detail fields.

    **Validates: Requirements 4.2**
    """

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_details_contains_all_fields(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        ACL rule details must include id, name, type, enabled, description,
        action, index, enforcingDeviceFilter, sourceFilter, destinationFilter,
        protocolFilter, and metadata.
        """
        tool = GetACLRuleTool()
        result = tool._format_rule_details(rule)

        assert "id" in result
        assert "name" in result
        assert "type" in result
        assert "enabled" in result
        assert "description" in result
        assert "action" in result
        assert "index" in result
        assert "enforcingDeviceFilter" in result
        assert "sourceFilter" in result
        assert "destinationFilter" in result
        assert "protocolFilter" in result
        assert "metadata" in result

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_details_preserves_core_fields(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        Core fields must be preserved exactly from input.
        """
        tool = GetACLRuleTool()
        result = tool._format_rule_details(rule)

        assert result["id"] == rule["id"]
        assert result["name"] == rule["name"]
        assert result["type"] == rule["type"]
        assert result["enabled"] == rule["enabled"]
        assert result["action"] == rule["action"]
        assert result["index"] == rule["index"]
        assert result["metadata"] == rule["metadata"]

    @given(rule=acl_rules)
    @settings(max_examples=100)
    def test_acl_details_preserves_filters(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        Filter fields must be preserved exactly from input.
        """
        tool = GetACLRuleTool()
        result = tool._format_rule_details(rule)

        assert result["enforcingDeviceFilter"] == rule["enforcingDeviceFilter"]
        assert result["sourceFilter"] == rule["sourceFilter"]
        assert result["destinationFilter"] == rule["destinationFilter"]
        assert result["protocolFilter"] == rule["protocolFilter"]


# ---------------------------------------------------------------------------
# Property 6c: Full Execute Path — ACL Rule List
# ---------------------------------------------------------------------------

class TestACLRuleListExecuteProperty:
    """For any valid v1 response containing ACL rule data, the full execute path
    SHALL produce a successful result with all rules formatted correctly.

    **Validates: Requirements 4.1**
    """

    @given(response=v1_response(acl_rules))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_acl_list_execute_returns_all_rules(self, response):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The execute path must return all ACL rules from the response with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListACLRulesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, rule_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == rule_data["id"]
            assert formatted["name"] == rule_data["name"]
            assert formatted["type"] == rule_data["type"]
            assert formatted["enabled"] == rule_data["enabled"]
            assert formatted["action"] == rule_data["action"]
            assert formatted["index"] == rule_data["index"]


# ---------------------------------------------------------------------------
# Property 6d: Full Execute Path — ACL Rule Detail
# ---------------------------------------------------------------------------

class TestACLRuleDetailExecuteProperty:
    """For any valid ACL rule dict, the GetACLRuleTool execute path SHALL
    produce a successful detail result with all rule fields.

    **Validates: Requirements 4.2**
    """

    @given(rule=acl_rules)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_acl_detail_execute_returns_formatted_rule(self, rule):
        """Feature: unifi-api-v1-migration, Property 6: ACL Rule Formatting

        The execute path must return ACL rule details with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=rule)

        tool = GetACLRuleTool()
        result = asyncio.run(tool.execute(mock_client, rule_id=rule["id"]))

        assert result["success"] is True
        assert result["type"] == "acl_rule"
        assert result["data"]["id"] == rule["id"]
        assert result["data"]["name"] == rule["name"]
        assert result["data"]["type"] == rule["type"]
        assert result["data"]["enabled"] == rule["enabled"]
        assert result["data"]["action"] == rule["action"]
        assert result["data"]["index"] == rule["index"]


# ===========================================================================
# Property 7: DNS Policy Formatting
# Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 7a: DNS Policy Summary Formatting
# ---------------------------------------------------------------------------

class TestDNSPolicySummaryFormattingProperty:
    """For any valid DNS policy dict, _format_policy_summary SHALL produce
    output containing the policy ID, name, and enabled state.

    **Validates: Requirements 5.1**
    """

    @given(policy=dns_policies)
    @settings(max_examples=100)
    def test_dns_summary_contains_required_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        The DNS policy summary must contain id, name, and enabled.
        """
        tool = ListDNSPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert "id" in result
        assert "name" in result
        assert "enabled" in result

    @given(policy=dns_policies)
    @settings(max_examples=100)
    def test_dns_summary_preserves_id_and_name(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        The policy ID and name in the output must match the input exactly.
        """
        tool = ListDNSPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["id"] == policy["id"]
        assert result["name"] == policy["name"]

    @given(policy=dns_policies)
    @settings(max_examples=100)
    def test_dns_summary_preserves_enabled(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        The enabled boolean must match the input exactly.
        """
        tool = ListDNSPoliciesTool()
        result = tool._format_policy_summary(policy)

        assert result["enabled"] == policy["enabled"]


# ---------------------------------------------------------------------------
# Property 7b: DNS Policy Detail Formatting
# ---------------------------------------------------------------------------

class TestDNSPolicyDetailFormattingProperty:
    """For any valid DNS policy dict, _format_policy_details SHALL produce
    output containing all required detail fields.

    **Validates: Requirements 5.2**
    """

    @given(policy=dns_policies)
    @settings(max_examples=100)
    def test_dns_details_contains_all_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        DNS policy details must include id, name, enabled, description, and metadata.
        """
        tool = GetDNSPolicyTool()
        result = tool._format_policy_details(policy)

        assert "id" in result
        assert "name" in result
        assert "enabled" in result
        assert "description" in result
        assert "metadata" in result

    @given(policy=dns_policies)
    @settings(max_examples=100)
    def test_dns_details_preserves_all_fields(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        All fields must be preserved exactly from input.
        """
        tool = GetDNSPolicyTool()
        result = tool._format_policy_details(policy)

        assert result["id"] == policy["id"]
        assert result["name"] == policy["name"]
        assert result["enabled"] == policy["enabled"]
        assert result["description"] == policy["description"]
        assert result["metadata"] == policy["metadata"]


# ---------------------------------------------------------------------------
# Property 7c: Full Execute Path — DNS Policy List
# ---------------------------------------------------------------------------

class TestDNSPolicyListExecuteProperty:
    """For any valid v1 response containing DNS policy data, the full execute path
    SHALL produce a successful result with all policies formatted correctly.

    **Validates: Requirements 5.1**
    """

    @given(response=v1_response(dns_policies))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_dns_list_execute_returns_all_policies(self, response):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        The execute path must return all DNS policies from the response with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListDNSPoliciesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, policy_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == policy_data["id"]
            assert formatted["name"] == policy_data["name"]
            assert formatted["enabled"] == policy_data["enabled"]


# ---------------------------------------------------------------------------
# Property 7d: Full Execute Path — DNS Policy Detail
# ---------------------------------------------------------------------------

class TestDNSPolicyDetailExecuteProperty:
    """For any valid DNS policy dict, the GetDNSPolicyTool execute path SHALL
    produce a successful detail result with all policy fields.

    **Validates: Requirements 5.2**
    """

    @given(policy=dns_policies)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_dns_detail_execute_returns_formatted_policy(self, policy):
        """Feature: unifi-api-v1-migration, Property 7: DNS Policy Formatting

        The execute path must return DNS policy details with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=policy)

        tool = GetDNSPolicyTool()
        result = asyncio.run(tool.execute(mock_client, policy_id=policy["id"]))

        assert result["success"] is True
        assert result["type"] == "dns_policy"
        assert result["data"]["id"] == policy["id"]
        assert result["data"]["name"] == policy["name"]
        assert result["data"]["enabled"] == policy["enabled"]
        assert result["data"]["metadata"] == policy["metadata"]


# ===========================================================================
# Property 8: Traffic Matching List Formatting
# Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 8a: Traffic Matching List Summary Formatting
# ---------------------------------------------------------------------------

class TestTrafficMatchingListSummaryFormattingProperty:
    """For any valid traffic matching list dict, _format_list_summary SHALL
    produce output containing the list ID, name, and type.

    **Validates: Requirements 6.1**
    """

    @given(item=traffic_matching_lists)
    @settings(max_examples=100)
    def test_tml_summary_contains_required_fields(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        The traffic matching list summary must contain id, name, and type.
        """
        tool = ListTrafficMatchingListsTool()
        result = tool._format_list_summary(item)

        assert "id" in result
        assert "name" in result
        assert "type" in result

    @given(item=traffic_matching_lists)
    @settings(max_examples=100)
    def test_tml_summary_preserves_id_and_name(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        The list ID and name in the output must match the input exactly.
        """
        tool = ListTrafficMatchingListsTool()
        result = tool._format_list_summary(item)

        assert result["id"] == item["id"]
        assert result["name"] == item["name"]

    @given(item=traffic_matching_lists)
    @settings(max_examples=100)
    def test_tml_summary_preserves_type(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        The type must match the input exactly.
        """
        tool = ListTrafficMatchingListsTool()
        result = tool._format_list_summary(item)

        assert result["type"] == item["type"]


# ---------------------------------------------------------------------------
# Property 8b: Traffic Matching List Detail Formatting
# ---------------------------------------------------------------------------

class TestTrafficMatchingListDetailFormattingProperty:
    """For any valid traffic matching list dict, _format_list_details SHALL
    produce output containing all required detail fields.

    **Validates: Requirements 6.2**
    """

    @given(item=traffic_matching_lists)
    @settings(max_examples=100)
    def test_tml_details_contains_all_fields(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        Traffic matching list details must include id, name, type, description, and metadata.
        """
        tool = GetTrafficMatchingListTool()
        result = tool._format_list_details(item)

        assert "id" in result
        assert "name" in result
        assert "type" in result
        assert "description" in result
        assert "metadata" in result

    @given(item=traffic_matching_lists)
    @settings(max_examples=100)
    def test_tml_details_preserves_all_fields(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        All fields must be preserved exactly from input.
        """
        tool = GetTrafficMatchingListTool()
        result = tool._format_list_details(item)

        assert result["id"] == item["id"]
        assert result["name"] == item["name"]
        assert result["type"] == item["type"]
        assert result["description"] == item["description"]
        assert result["metadata"] == item["metadata"]


# ---------------------------------------------------------------------------
# Property 8c: Full Execute Path — Traffic Matching List
# ---------------------------------------------------------------------------

class TestTrafficMatchingListExecuteProperty:
    """For any valid v1 response containing traffic matching list data, the full
    execute path SHALL produce a successful result with all lists formatted correctly.

    **Validates: Requirements 6.1**
    """

    @given(response=v1_response(traffic_matching_lists))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tml_list_execute_returns_all_lists(self, response):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        The execute path must return all traffic matching lists from the response with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListTrafficMatchingListsTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, item_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == item_data["id"]
            assert formatted["name"] == item_data["name"]
            assert formatted["type"] == item_data["type"]


# ---------------------------------------------------------------------------
# Property 8d: Full Execute Path — Traffic Matching List Detail
# ---------------------------------------------------------------------------

class TestTrafficMatchingListDetailExecuteProperty:
    """For any valid traffic matching list dict, the GetTrafficMatchingListTool
    execute path SHALL produce a successful detail result with all fields.

    **Validates: Requirements 6.2**
    """

    @given(item=traffic_matching_lists)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tml_detail_execute_returns_formatted_list(self, item):
        """Feature: unifi-api-v1-migration, Property 8: Traffic Matching List Formatting

        The execute path must return traffic matching list details with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=item)

        tool = GetTrafficMatchingListTool()
        result = asyncio.run(tool.execute(mock_client, list_id=item["id"]))

        assert result["success"] is True
        assert result["type"] == "traffic_matching_list"
        assert result["data"]["id"] == item["id"]
        assert result["data"]["name"] == item["name"]
        assert result["data"]["type"] == item["type"]
        assert result["data"]["description"] == item["description"]
        assert result["data"]["metadata"] == item["metadata"]
