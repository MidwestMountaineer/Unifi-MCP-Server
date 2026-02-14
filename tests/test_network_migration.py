"""Property-based tests for migrated network and WiFi formatting.

Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

For any valid v1 network dict containing new fields (vlanId, dhcpGuarding,
management, default), the migrated formatter SHALL include those fields in
the output when present. For any valid v1 WiFi broadcast dict, the formatter
SHALL produce output containing the broadcast name and ID.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.tools.network_discovery import (
    ListNetworksTool,
    GetNetworkDetailsTool,
    ListWLANsTool,
    GetWLANDetailsTool,
)
from unifi_mcp.unifi_client import UniFiClient


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

# IPv4 subnet strings like "192.168.1.0/24"
ip_subnets = st.tuples(
    st.integers(1, 254),
    st.integers(0, 255),
    st.integers(0, 255),
    st.sampled_from([0]),
    st.sampled_from([8, 16, 24, 28]),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}/{t[4]}")

# IPv4 addresses
ipv4_addresses = st.tuples(
    st.integers(1, 254),
    st.integers(0, 255),
    st.integers(0, 255),
    st.integers(1, 254),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}")

# Network purposes
network_purposes = st.sampled_from(["corporate", "guest", "vlan-only", "remote-user-vpn", ""])

# V1 network dicts (summary-level, with v1 camelCase fields)
v1_networks = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "purpose": network_purposes,
    "vlanId": st.one_of(st.none(), st.integers(min_value=1, max_value=4094)),
    "ipSubnet": ip_subnets,
    "networkGroup": st.sampled_from(["LAN", "WAN", "WAN2", ""]),
    "dhcpEnabled": st.booleans(),
    "dhcpStart": ipv4_addresses,
    "dhcpStop": ipv4_addresses,
    "domainName": st.text(min_size=0, max_size=30),
    "enabled": st.booleans(),
})

# V1 network dicts with detail-level fields including new v1 fields
v1_networks_detailed = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "purpose": network_purposes,
    "vlanId": st.one_of(st.none(), st.integers(min_value=1, max_value=4094)),
    "ipSubnet": ip_subnets,
    "gatewayIp": ipv4_addresses,
    "gatewayType": st.sampled_from(["default", "none", ""]),
    "networkGroup": st.sampled_from(["LAN", "WAN", "WAN2", ""]),
    "dhcpEnabled": st.booleans(),
    "dhcpStart": ipv4_addresses,
    "dhcpStop": ipv4_addresses,
    "dhcpLeaseTime": st.integers(min_value=0, max_value=86400),
    "dhcpDns": st.lists(ipv4_addresses, max_size=3),
    "dhcpGateway": ipv4_addresses,
    "domainName": st.text(min_size=0, max_size=30),
    "enabled": st.booleans(),
    "isNat": st.booleans(),
    "isGuest": st.booleans(),
    "igmpSnooping": st.booleans(),
    "dhcpRelayEnabled": st.booleans(),
    # New v1-specific fields
    "dhcpGuarding": st.booleans(),
    "management": st.booleans(),
    "default": st.booleans(),
})

# WiFi security modes
wifi_security_modes = st.sampled_from(["wpapsk", "wpaeap", "open", "wep", ""])
wifi_wpa_modes = st.sampled_from(["wpa2", "wpa3", "wpa2/wpa3", ""])

# V1 WiFi broadcast dicts (summary-level, camelCase fields)
v1_wifi_broadcasts = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "ssid": st.text(min_size=1, max_size=32),
    "enabled": st.booleans(),
    "security": wifi_security_modes,
    "wpaMode": wifi_wpa_modes,
    "wpaEnc": st.sampled_from(["ccmp", "gcmp256", "auto", ""]),
    "networkId": uuids,
    "vlan": st.one_of(st.just(""), st.integers(min_value=1, max_value=4094).map(str)),
    "vlanEnabled": st.booleans(),
    "isGuest": st.booleans(),
    "hideSsid": st.booleans(),
})

# V1 WiFi broadcast dicts with detail-level fields
v1_wifi_broadcasts_detailed = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
    "ssid": st.text(min_size=1, max_size=32),
    "enabled": st.booleans(),
    "security": wifi_security_modes,
    "wpaMode": wifi_wpa_modes,
    "wpaEnc": st.sampled_from(["ccmp", "gcmp256", "auto", ""]),
    "wepIdx": st.integers(min_value=0, max_value=3),
    "networkId": uuids,
    "vlan": st.one_of(st.just(""), st.integers(min_value=1, max_value=4094).map(str)),
    "vlanEnabled": st.booleans(),
    "isGuest": st.booleans(),
    "portalEnabled": st.booleans(),
    "portalCustomized": st.booleans(),
    "hideSsid": st.booleans(),
    "macFilterEnabled": st.booleans(),
    "macFilterPolicy": st.sampled_from(["allow", "deny", ""]),
    "bandSteeringMode": st.sampled_from(["off", "prefer_5g", ""]),
    "fastRoamingEnabled": st.booleans(),
    "radiusEnabled": st.booleans(),
    "radiusNasId": st.text(min_size=0, max_size=20),
    "groupRekey": st.integers(min_value=0, max_value=86400),
    "wpa3Support": st.booleans(),
    "wpa3Transition": st.booleans(),
    "scheduleEnabled": st.booleans(),
    "schedule": st.just([]),
    "dtimMode": st.sampled_from(["default", "custom", ""]),
    "dtimNg": st.integers(min_value=0, max_value=10),
    "dtimNa": st.integers(min_value=0, max_value=10),
    "minrateNgEnabled": st.booleans(),
    "minrateNgDataRateKbps": st.integers(min_value=0, max_value=54000),
    "minrateNaEnabled": st.booleans(),
    "minrateNaDataRateKbps": st.integers(min_value=0, max_value=54000),
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
        data=st.lists(data_strategy, min_size=1, max_size=10),
        offset=st.integers(min_value=0, max_value=100),
    )


# ---------------------------------------------------------------------------
# Property 10a: Network Summary Formatting
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestNetworkSummaryFormattingProperty:
    """For any valid v1 network dict, _format_network_summary SHALL produce
    output containing id, name, purpose, vlan, ip_subnet, and enabled.

    **Validates: Requirements 8.1**
    """

    @given(network=v1_networks)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_summary_contains_required_fields(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Network summary must contain id, name, purpose, vlan, ip_subnet, enabled.

        **Validates: Requirements 8.1**
        """
        tool = ListNetworksTool()
        result = tool._format_network_summary(network)

        assert "id" in result
        assert "name" in result
        assert "purpose" in result
        assert "vlan" in result
        assert "ip_subnet" in result
        assert "enabled" in result

    @given(network=v1_networks)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_summary_preserves_id_and_name(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        ID and name must be preserved from v1 input.

        **Validates: Requirements 8.1**
        """
        tool = ListNetworksTool()
        result = tool._format_network_summary(network)

        assert result["id"] == network["id"]
        assert result["name"] == network["name"]

    @given(network=v1_networks)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_summary_maps_v1_vlan_id(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        v1 vlanId field must be mapped to the vlan output field.

        **Validates: Requirements 8.1**
        """
        tool = ListNetworksTool()
        result = tool._format_network_summary(network)

        # The formatter uses network.get("vlan", network.get("vlanId", ""))
        # Since v1 data has vlanId but not vlan, it should pick up vlanId
        if "vlan" not in network:
            assert result["vlan"] == network.get("vlanId", "")

    @given(network=v1_networks)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_summary_preserves_purpose(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Purpose must be preserved from input.

        **Validates: Requirements 8.1**
        """
        tool = ListNetworksTool()
        result = tool._format_network_summary(network)

        assert result["purpose"] == network["purpose"]


# ---------------------------------------------------------------------------
# Property 10b: Network Detail Formatting with v1 Fields
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestNetworkDetailFormattingProperty:
    """For any valid v1 network dict with new fields (vlanId, dhcpGuarding,
    management, default), _format_network_details SHALL include those fields
    in the output when present.

    **Validates: Requirements 8.2**
    """

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_contains_core_fields(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Network details must contain id, name, purpose, vlan, ip_subnet, enabled.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert "id" in result
        assert "name" in result
        assert "purpose" in result
        assert "vlan" in result
        assert "ip_subnet" in result
        assert "enabled" in result

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_preserves_id_and_name(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        ID and name must be preserved exactly from v1 input.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert result["id"] == network["id"]
        assert result["name"] == network["name"]

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_includes_vlanId_when_present(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        When vlanId is present in v1 data, it must appear in the output.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        # vlanId is always present in our strategy (may be None or int)
        assert "vlanId" in result
        assert result["vlanId"] == network["vlanId"]

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_includes_dhcpGuarding_when_present(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        When dhcpGuarding is present in v1 data, it must appear in the output.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert "dhcpGuarding" in result
        assert result["dhcpGuarding"] == network["dhcpGuarding"]

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_includes_management_when_present(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        When management is present in v1 data, it must appear in the output.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert "management" in result
        assert result["management"] == network["management"]

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_includes_default_when_present(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        When default is present in v1 data, it must appear in the output.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert "default" in result
        assert result["default"] == network["default"]

    @given(network=v1_networks_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_details_includes_dhcp_config(self, network):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        DHCP configuration fields must be present in the output.

        **Validates: Requirements 8.2**
        """
        tool = GetNetworkDetailsTool()
        result = tool._format_network_details(network)

        assert "dhcp_enabled" in result
        assert "dhcp_start" in result
        assert "dhcp_stop" in result


# ---------------------------------------------------------------------------
# Property 10c: WiFi Broadcast Summary Formatting
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestWiFiSummaryFormattingProperty:
    """For any valid v1 WiFi broadcast dict, _format_wlan_summary SHALL
    produce output containing the broadcast name and ID.

    **Validates: Requirements 8.3**
    """

    @given(wlan=v1_wifi_broadcasts)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_summary_contains_required_fields(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        WiFi broadcast summary must contain id, name, ssid, enabled, security.

        **Validates: Requirements 8.3**
        """
        tool = ListWLANsTool()
        result = tool._format_wlan_summary(wlan)

        assert "id" in result
        assert "name" in result
        assert "ssid" in result
        assert "enabled" in result
        assert "security" in result

    @given(wlan=v1_wifi_broadcasts)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_summary_preserves_id_and_name(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        ID and name must be preserved from v1 input.

        **Validates: Requirements 8.3**
        """
        tool = ListWLANsTool()
        result = tool._format_wlan_summary(wlan)

        assert result["id"] == wlan["id"]
        assert result["name"] == wlan["name"]

    @given(wlan=v1_wifi_broadcasts)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_summary_maps_v1_camelcase_fields(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        v1 camelCase fields (wpaMode, networkId, vlanEnabled, isGuest, hideSsid)
        must be mapped to the output.

        **Validates: Requirements 8.3**
        """
        tool = ListWLANsTool()
        result = tool._format_wlan_summary(wlan)

        assert result["wpa_mode"] == wlan["wpaMode"]
        assert result["network_id"] == wlan["networkId"]
        assert result["vlan_enabled"] == wlan["vlanEnabled"]
        assert result["is_guest"] == wlan["isGuest"]
        assert result["hide_ssid"] == wlan["hideSsid"]

    @given(wlan=v1_wifi_broadcasts)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_summary_preserves_ssid(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        SSID must be preserved from v1 input.

        **Validates: Requirements 8.3**
        """
        tool = ListWLANsTool()
        result = tool._format_wlan_summary(wlan)

        assert result["ssid"] == wlan["ssid"]


# ---------------------------------------------------------------------------
# Property 10d: WiFi Broadcast Detail Formatting
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestWiFiDetailFormattingProperty:
    """For any valid v1 WiFi broadcast dict, _format_wlan_details SHALL
    produce output containing the broadcast name, ID, and all detail fields.

    **Validates: Requirements 8.4**
    """

    @given(wlan=v1_wifi_broadcasts_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_details_contains_core_fields(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        WiFi broadcast details must contain id, name, ssid, enabled, security.

        **Validates: Requirements 8.4**
        """
        tool = GetWLANDetailsTool()
        result = tool._format_wlan_details(wlan)

        assert "id" in result
        assert "name" in result
        assert "ssid" in result
        assert "enabled" in result
        assert "security" in result

    @given(wlan=v1_wifi_broadcasts_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_details_preserves_id_and_name(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        ID and name must be preserved from v1 input.

        **Validates: Requirements 8.4**
        """
        tool = GetWLANDetailsTool()
        result = tool._format_wlan_details(wlan)

        assert result["id"] == wlan["id"]
        assert result["name"] == wlan["name"]

    @given(wlan=v1_wifi_broadcasts_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_details_includes_security_settings(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Security settings (wpa_mode, wpa_enc, wpa3_support) must be present.

        **Validates: Requirements 8.4**
        """
        tool = GetWLANDetailsTool()
        result = tool._format_wlan_details(wlan)

        assert result["wpa_mode"] == wlan["wpaMode"]
        assert result["wpa_enc"] == wlan["wpaEnc"]
        assert result["wpa3_support"] == wlan["wpa3Support"]
        assert result["wpa3_transition"] == wlan["wpa3Transition"]

    @given(wlan=v1_wifi_broadcasts_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_details_includes_network_assignment(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Network assignment fields (network_id, vlan, vlan_enabled) must be present.

        **Validates: Requirements 8.4**
        """
        tool = GetWLANDetailsTool()
        result = tool._format_wlan_details(wlan)

        assert result["network_id"] == wlan["networkId"]
        assert result["vlan"] == wlan["vlan"]
        assert result["vlan_enabled"] == wlan["vlanEnabled"]

    @given(wlan=v1_wifi_broadcasts_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_details_includes_guest_settings(self, wlan):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        Guest network settings must be present.

        **Validates: Requirements 8.4**
        """
        tool = GetWLANDetailsTool()
        result = tool._format_wlan_details(wlan)

        assert result["is_guest"] == wlan["isGuest"]
        assert result["hide_ssid"] == wlan["hideSsid"]


# ---------------------------------------------------------------------------
# Property 10e: Full Execute Path — Network List
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestNetworkListExecuteProperty:
    """For any valid v1 response containing network data, the full execute path
    SHALL produce a successful result with all networks formatted correctly.

    **Validates: Requirements 8.1**
    """

    @given(response=v1_response(v1_networks))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_network_list_execute_returns_all_networks(self, response):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        The execute path must return all networks with correct formatting.

        **Validates: Requirements 8.1**
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListNetworksTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, network_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == network_data["id"]
            assert formatted["name"] == network_data["name"]
            assert "purpose" in formatted
            assert "vlan" in formatted
            assert "enabled" in formatted


# ---------------------------------------------------------------------------
# Property 10f: Full Execute Path — WiFi Broadcast List
# Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting
# ---------------------------------------------------------------------------

class TestWiFiListExecuteProperty:
    """For any valid v1 response containing WiFi broadcast data, the full
    execute path SHALL produce a successful result with all broadcasts formatted.

    **Validates: Requirements 8.3**
    """

    @given(response=v1_response(v1_wifi_broadcasts))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_wifi_list_execute_returns_all_broadcasts(self, response):
        """Feature: unifi-api-v1-migration, Property 10: Migrated Network and WiFi Formatting

        The execute path must return all WiFi broadcasts with correct formatting.

        **Validates: Requirements 8.3**
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListWLANsTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, wlan_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == wlan_data["id"]
            assert formatted["name"] == wlan_data["name"]
            assert "ssid" in formatted
            assert "enabled" in formatted
