"""Property-based tests for supporting resource formatting.

Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting

For any valid site dict (with id and name), WAN interface dict, VPN tunnel dict,
VPN server dict, or network references list, the formatter SHALL produce output
containing the resource's identifying fields (ID, name where applicable).

**Validates: Requirements 9.1, 9.3, 9.4, 9.5, 9.6**
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.tools.resources import (
    ListSitesTool,
    GetAppInfoTool,
    ListWANInterfacesTool,
    ListVPNTunnelsTool,
    ListVPNServersTool,
    GetNetworkReferencesTool,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

# Site dicts
sites = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
})

# App info response dicts
app_infos = st.fixed_dictionaries({
    "version": st.from_regex(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", fullmatch=True),
    "name": st.text(min_size=1, max_size=50),
})

# WAN interface dicts
wan_interfaces = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
})

# VPN tunnel dicts
vpn_tunnels = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
})

# VPN server dicts
vpn_servers = st.fixed_dictionaries({
    "id": uuids,
    "name": st.text(min_size=1, max_size=50),
})

# Reference types
reference_types = st.sampled_from([
    "FIREWALL_ZONE", "FIREWALL_POLICY", "VPN_TUNNEL", "VPN_SERVER",
    "WLAN", "DEVICE", "CLIENT",
])

# Network reference dicts
network_references = st.fixed_dictionaries({
    "id": uuids,
    "type": reference_types,
    "name": st.text(min_size=1, max_size=50),
})


# ---------------------------------------------------------------------------
# Property 11a: Site Summary Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestSiteSummaryFormattingProperty:
    """For any valid site dict, _format_site_summary SHALL produce output
    containing the site's id and name.

    **Validates: Requirements 9.1**
    """

    def setup_method(self):
        self.tool = ListSitesTool()

    @given(site=sites)
    @settings(max_examples=100)
    def test_site_summary_contains_id_and_name(self, site):
        """Site summary output must contain id and name fields.

        **Validates: Requirements 9.1**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_site_summary(site)

        assert "id" in result
        assert "name" in result

    @given(site=sites)
    @settings(max_examples=100)
    def test_site_summary_preserves_values(self, site):
        """Site summary must preserve the original id and name values.

        **Validates: Requirements 9.1**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_site_summary(site)

        assert result["id"] == site["id"]
        assert result["name"] == site["name"]


# ---------------------------------------------------------------------------
# Property 11b: App Info Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestAppInfoFormattingProperty:
    """For any valid app info response, _format_app_info SHALL produce output
    containing version and name.

    **Validates: Requirements 9.1**
    """

    def setup_method(self):
        self.tool = GetAppInfoTool()

    @given(info=app_infos)
    @settings(max_examples=100)
    def test_app_info_contains_version_and_name(self, info):
        """App info output must contain version and name fields.

        **Validates: Requirements 9.1**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_app_info(info)

        assert "version" in result
        assert "name" in result

    @given(info=app_infos)
    @settings(max_examples=100)
    def test_app_info_preserves_values(self, info):
        """App info must preserve the original version and name values.

        **Validates: Requirements 9.1**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_app_info(info)

        assert result["version"] == info["version"]
        assert result["name"] == info["name"]


# ---------------------------------------------------------------------------
# Property 11c: WAN Interface Summary Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestWANSummaryFormattingProperty:
    """For any valid WAN interface dict, _format_wan_summary SHALL produce
    output containing the WAN's id and name.

    **Validates: Requirements 9.3**
    """

    def setup_method(self):
        self.tool = ListWANInterfacesTool()

    @given(wan=wan_interfaces)
    @settings(max_examples=100)
    def test_wan_summary_contains_id_and_name(self, wan):
        """WAN summary output must contain id and name fields.

        **Validates: Requirements 9.3**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_wan_summary(wan)

        assert "id" in result
        assert "name" in result

    @given(wan=wan_interfaces)
    @settings(max_examples=100)
    def test_wan_summary_preserves_values(self, wan):
        """WAN summary must preserve the original id and name values.

        **Validates: Requirements 9.3**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_wan_summary(wan)

        assert result["id"] == wan["id"]
        assert result["name"] == wan["name"]


# ---------------------------------------------------------------------------
# Property 11d: VPN Tunnel Summary Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestVPNTunnelSummaryFormattingProperty:
    """For any valid VPN tunnel dict, _format_tunnel_summary SHALL produce
    output containing the tunnel's id and name.

    **Validates: Requirements 9.4**
    """

    def setup_method(self):
        self.tool = ListVPNTunnelsTool()

    @given(tunnel=vpn_tunnels)
    @settings(max_examples=100)
    def test_tunnel_summary_contains_id_and_name(self, tunnel):
        """VPN tunnel summary output must contain id and name fields.

        **Validates: Requirements 9.4**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_tunnel_summary(tunnel)

        assert "id" in result
        assert "name" in result

    @given(tunnel=vpn_tunnels)
    @settings(max_examples=100)
    def test_tunnel_summary_preserves_values(self, tunnel):
        """VPN tunnel summary must preserve the original id and name values.

        **Validates: Requirements 9.4**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_tunnel_summary(tunnel)

        assert result["id"] == tunnel["id"]
        assert result["name"] == tunnel["name"]


# ---------------------------------------------------------------------------
# Property 11e: VPN Server Summary Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestVPNServerSummaryFormattingProperty:
    """For any valid VPN server dict, _format_server_summary SHALL produce
    output containing the server's id and name.

    **Validates: Requirements 9.5**
    """

    def setup_method(self):
        self.tool = ListVPNServersTool()

    @given(server=vpn_servers)
    @settings(max_examples=100)
    def test_server_summary_contains_id_and_name(self, server):
        """VPN server summary output must contain id and name fields.

        **Validates: Requirements 9.5**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_server_summary(server)

        assert "id" in result
        assert "name" in result

    @given(server=vpn_servers)
    @settings(max_examples=100)
    def test_server_summary_preserves_values(self, server):
        """VPN server summary must preserve the original id and name values.

        **Validates: Requirements 9.5**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_server_summary(server)

        assert result["id"] == server["id"]
        assert result["name"] == server["name"]


# ---------------------------------------------------------------------------
# Property 11f: Network Reference Formatting
# Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
# ---------------------------------------------------------------------------

class TestNetworkReferenceFormattingProperty:
    """For any valid network reference dict, _format_reference SHALL produce
    output containing the reference's id, type, and name.

    **Validates: Requirements 9.6**
    """

    def setup_method(self):
        self.tool = GetNetworkReferencesTool()

    @given(ref=network_references)
    @settings(max_examples=100)
    def test_reference_contains_id_type_and_name(self, ref):
        """Network reference output must contain id, type, and name fields.

        **Validates: Requirements 9.6**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_reference(ref)

        assert "id" in result
        assert "type" in result
        assert "name" in result

    @given(ref=network_references)
    @settings(max_examples=100)
    def test_reference_preserves_values(self, ref):
        """Network reference must preserve the original id, type, and name values.

        **Validates: Requirements 9.6**
        """
        # Feature: unifi-api-v1-migration, Property 11: Supporting Resource Formatting
        result = self.tool._format_reference(ref)

        assert result["id"] == ref["id"]
        assert result["type"] == ref["type"]
        assert result["name"] == ref["name"]
