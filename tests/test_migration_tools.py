"""Unit tests for migration support tools.

Updated to support v2 API endpoint routing via get_security_data().
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

from unifi_mcp.tools.migration import (
    GetDHCPStatusTool,
    VerifyVLANConnectivityTool,
    ExportConfigurationTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.api import ControllerType


@pytest.fixture
def mock_unifi_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.get_security_data = AsyncMock()
    # Default controller type
    type(client).controller_type = PropertyMock(return_value=ControllerType.TRADITIONAL)
    return client


@pytest.fixture
def sample_networks():
    return [
        {
            "_id": "net1",
            "name": "Core Network",
            "vlan": "10",
            "ip_subnet": "192.168.10.0/24",
            "dhcpd_enabled": True,
            "dhcpd_start": "192.168.10.100",
            "dhcpd_stop": "192.168.10.200",
            "dhcpd_leasetime": 86400,
            "dhcpd_dns": ["192.168.10.1", "8.8.8.8"],
            "dhcpd_gateway": "192.168.10.1",
        },
        {
            "_id": "net2",
            "name": "IoT Network",
            "vlan": "30",
            "ip_subnet": "192.168.30.0/24",
            "dhcpd_enabled": True,
        },
        {
            "_id": "net3",
            "name": "Management",
            "vlan": "50",
            "ip_subnet": "192.168.50.0/24",
            "dhcpd_enabled": False,
        },
    ]


@pytest.fixture
def sample_clients():
    return [
        {"mac": "aa:bb:cc:dd:ee:01", "ip": "192.168.10.101", "use_fixedip": False},
        {"mac": "aa:bb:cc:dd:ee:02", "ip": "192.168.10.102", "use_fixedip": False},
        {"mac": "aa:bb:cc:dd:ee:03", "ip": "192.168.10.50", "use_fixedip": True},
        {"mac": "aa:bb:cc:dd:ee:04", "ip": "192.168.30.101", "use_fixedip": False},
    ]


@pytest.fixture
def sample_firewall_rules():
    return [
        {
            "_id": "rule1",
            "name": "Allow Core to IoT",
            "enabled": True,
            "action": "accept",
            "protocol": "all",
            "src_address": "192.168.10.0/24",
            "dst_address": "192.168.30.0/24",
        },
        {
            "_id": "rule2",
            "name": "Block IoT to Core",
            "enabled": True,
            "action": "drop",
            "protocol": "all",
            "src_address": "192.168.30.0/24",
            "dst_address": "192.168.10.0/24",
        },
    ]


async def test_get_dhcp_status_all_networks(mock_unifi_client, sample_networks, sample_clients):
    mock_unifi_client.get.side_effect = [{"data": sample_networks}, {"data": sample_clients}]
    tool = GetDHCPStatusTool()
    result = await tool.execute(mock_unifi_client)
    assert result["success"] is True
    assert result["data"]["total_networks"] == 3


async def test_verify_vlan_connectivity_allowed(mock_unifi_client, sample_networks, sample_firewall_rules):
    """Test VLAN connectivity check with v2 API support."""
    # Mock get for networks, get_security_data for firewall rules
    mock_unifi_client.get.return_value = {"data": sample_networks}
    mock_unifi_client.get_security_data.return_value = {
        "data": sample_firewall_rules,
        "api_version": "v1",
        "controller_type": "traditional",
    }

    tool = VerifyVLANConnectivityTool()
    result = await tool.execute(mock_unifi_client, source_vlan="10", destination_vlan="30")
    assert result["success"] is True
    # api_version is in result["data"] for connectivity result
    assert "api_version" in result["data"]


async def test_export_configuration_all_sections(mock_unifi_client, sample_networks, sample_firewall_rules):
    """Test export configuration with v2 API support."""
    # Mock get for networks and WLANs
    mock_unifi_client.get.side_effect = [
        {"data": sample_networks},  # networks
        {"data": []},  # wlans
    ]

    # Mock get_security_data for firewall rules, routes, port forwards
    mock_unifi_client.get_security_data.side_effect = [
        {"data": sample_firewall_rules, "api_version": "v1", "controller_type": "traditional"},
        {"data": [], "api_version": "v1", "controller_type": "traditional"},  # routes
        {"data": [], "api_version": "v1", "controller_type": "traditional"},  # port forwards
    ]

    tool = ExportConfigurationTool()
    result = await tool.execute(mock_unifi_client)
    assert result["success"] is True
    assert "configuration" in result["data"]
    # Verify metadata fields (Requirement 6.3)
    assert "controller_type" in result["data"]
    assert "api_version" in result["data"]


def test_get_dhcp_status_tool_metadata():
    tool = GetDHCPStatusTool()
    assert tool.name == "unifi_get_dhcp_status"
    assert tool.category == "migration"


def test_verify_vlan_connectivity_tool_metadata():
    tool = VerifyVLANConnectivityTool()
    assert tool.name == "unifi_verify_vlan_connectivity"
    assert tool.category == "migration"


def test_export_configuration_tool_metadata():
    tool = ExportConfigurationTool()
    assert tool.name == "unifi_export_configuration"
    assert tool.category == "migration"


# =============================================================================
# Property-Based Tests for Export Metadata Completeness
# =============================================================================

# Strategies for generating test data
controller_type_strategy = st.sampled_from([ControllerType.UNIFI_OS, ControllerType.TRADITIONAL])

export_options_strategy = st.fixed_dictionaries({
    "include_networks": st.booleans(),
    "include_firewall_rules": st.booleans(),
    "include_routing": st.booleans(),
    "include_port_forwards": st.booleans(),
    "include_wlans": st.booleans(),
})


def create_mock_client_with_controller_type(controller_type: ControllerType):
    """Create a mock UniFi client with a specific controller type."""
    client = MagicMock()
    client.get = AsyncMock(return_value={"data": []})
    client.get_security_data = AsyncMock(return_value={
        "data": [],
        "api_version": "v2" if controller_type == ControllerType.UNIFI_OS else "v1",
        "endpoint_used": "/test/endpoint",
        "fallback_used": False,
    })
    type(client).controller_type = PropertyMock(return_value=controller_type)
    return client


class TestExportMetadataCompleteness:
    """
    Property tests for export metadata completeness.

    **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
    **Validates: Requirements 6.3**
    """

    @given(controller_type=controller_type_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_export_contains_controller_type_metadata(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
        **Validates: Requirements 6.3**

        For any configuration export, the output SHALL include metadata field for controller_type.
        """
        client = create_mock_client_with_controller_type(controller_type)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            client,
            include_networks=True,
            include_firewall_rules=False,
            include_routing=False,
            include_port_forwards=False,
            include_wlans=False,
        )

        assert result["success"] is True
        assert "controller_type" in result["data"], "Export must include controller_type metadata"
        assert result["data"]["controller_type"] == controller_type.value

    @given(controller_type=controller_type_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_export_contains_api_version_metadata(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
        **Validates: Requirements 6.3**

        For any configuration export, the output SHALL include metadata field for api_version.
        """
        client = create_mock_client_with_controller_type(controller_type)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            client,
            include_networks=True,
            include_firewall_rules=False,
            include_routing=False,
            include_port_forwards=False,
            include_wlans=False,
        )

        assert result["success"] is True
        assert "api_version" in result["data"], "Export must include api_version metadata"

        # Verify api_version matches controller type
        expected_version = "v2" if controller_type == ControllerType.UNIFI_OS else "v1"
        assert result["data"]["api_version"] == expected_version

    @given(controller_type=controller_type_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_export_contains_timestamp_metadata(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
        **Validates: Requirements 6.3**

        For any configuration export, the output SHALL include export_timestamp metadata.
        """
        client = create_mock_client_with_controller_type(controller_type)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            client,
            include_networks=True,
            include_firewall_rules=False,
            include_routing=False,
            include_port_forwards=False,
            include_wlans=False,
        )

        assert result["success"] is True
        assert "export_timestamp" in result["data"], "Export must include export_timestamp metadata"
        # Verify timestamp is in ISO format (contains 'T' separator)
        assert "T" in result["data"]["export_timestamp"]

    @given(controller_type=controller_type_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_export_with_security_data_contains_api_versions_used(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
        **Validates: Requirements 6.3**

        For any configuration export that includes security data (firewall rules, routes, port forwards),
        the output SHALL include api_versions_used metadata showing which API version was used for each section.
        """
        client = create_mock_client_with_controller_type(controller_type)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            client,
            include_networks=True,
            include_firewall_rules=True,
            include_routing=True,
            include_port_forwards=True,
            include_wlans=True,
        )

        assert result["success"] is True
        assert "api_versions_used" in result["data"], "Export must include api_versions_used metadata"

        api_versions = result["data"]["api_versions_used"]

        # Verify all sections have API version tracking
        assert "networks" in api_versions
        assert "firewall_rules" in api_versions
        assert "routing_rules" in api_versions
        assert "port_forwards" in api_versions
        assert "wlans" in api_versions

    @given(controller_type=controller_type_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_export_metadata_consistency(self, controller_type):
        """
        **Feature: unifi-mcp-v2-api-support, Property 6: Export Metadata Completeness**
        **Validates: Requirements 6.3**

        For any configuration export, the controller_type and api_version metadata SHALL be consistent.
        """
        client = create_mock_client_with_controller_type(controller_type)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            client,
            include_networks=True,
            include_firewall_rules=True,
            include_routing=True,
            include_port_forwards=True,
            include_wlans=True,
        )

        assert result["success"] is True

        # Verify consistency between controller_type and api_version
        if result["data"]["controller_type"] == "unifi_os":
            assert result["data"]["api_version"] == "v2"
        elif result["data"]["controller_type"] == "traditional":
            assert result["data"]["api_version"] == "v1"


class TestVerifyVLANConnectivityWithRouting:
    """Tests for VerifyVLANConnectivityTool with endpoint routing."""

    @pytest.mark.asyncio
    async def test_vlan_connectivity_uses_endpoint_routing(self, mock_unifi_client, sample_networks):
        """Test that VLAN connectivity tool uses endpoint routing for firewall rules."""
        # Setup mock responses
        mock_unifi_client.get.return_value = {"data": sample_networks}
        mock_unifi_client.get_security_data.return_value = {
            "data": [
                {"_id": "rule1", "name": "Allow", "enabled": True, "action": "accept",
                 "src_address": "", "dst_address": ""}
            ],
            "api_version": "v2",
            "endpoint_used": "/proxy/network/v2/api/site/default/trafficroutes",
            "fallback_used": False,
        }

        tool = VerifyVLANConnectivityTool()
        result = await tool.execute(mock_unifi_client, source_vlan="10", destination_vlan="30")

        assert result["success"] is True
        # Verify get_security_data was called for firewall rules
        mock_unifi_client.get_security_data.assert_called_once_with("firewall_rules")
        # Verify api_version is included in result
        assert result["data"]["api_version"] == "v2"


class TestExportConfigurationWithRouting:
    """Tests for ExportConfigurationTool with endpoint routing."""

    @pytest.mark.asyncio
    async def test_export_uses_endpoint_routing_for_security_data(self, mock_unifi_client, sample_networks):
        """Test that export tool uses endpoint routing for security data."""
        # Setup mock responses
        mock_unifi_client.get.return_value = {"data": sample_networks}
        mock_unifi_client.get_security_data.return_value = {
            "data": [],
            "api_version": "v2",
            "endpoint_used": "/proxy/network/v2/api/site/default/trafficroutes",
            "fallback_used": False,
        }

        tool = ExportConfigurationTool()
        result = await tool.execute(
            mock_unifi_client,
            include_networks=True,
            include_firewall_rules=True,
            include_routing=True,
            include_port_forwards=True,
            include_wlans=True,
        )

        assert result["success"] is True

        # Verify get_security_data was called for each security feature
        calls = mock_unifi_client.get_security_data.call_args_list
        call_args = [call[0][0] for call in calls]
        assert "firewall_rules" in call_args
        assert "traffic_routes" in call_args
        assert "port_forwards" in call_args

    @pytest.mark.asyncio
    async def test_export_includes_controller_type_metadata(self, mock_unifi_client, sample_networks):
        """Test that export includes controller_type in metadata."""
        mock_unifi_client.get.return_value = {"data": sample_networks}
        mock_unifi_client.get_security_data.return_value = {
            "data": [],
            "api_version": "v1",
            "endpoint_used": "/api/s/default/rest/firewallrule",
            "fallback_used": False,
        }
        type(mock_unifi_client).controller_type = PropertyMock(return_value=ControllerType.TRADITIONAL)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            mock_unifi_client,
            include_networks=True,
            include_firewall_rules=True,
            include_routing=False,
            include_port_forwards=False,
            include_wlans=False,
        )

        assert result["success"] is True
        assert result["data"]["controller_type"] == "traditional"
        assert result["data"]["api_version"] == "v1"

    @pytest.mark.asyncio
    async def test_export_unifi_os_metadata(self, mock_unifi_client, sample_networks):
        """Test that export correctly identifies UniFi OS controller."""
        mock_unifi_client.get.return_value = {"data": sample_networks}
        mock_unifi_client.get_security_data.return_value = {
            "data": [],
            "api_version": "v2",
            "endpoint_used": "/proxy/network/v2/api/site/default/trafficroutes",
            "fallback_used": False,
        }
        type(mock_unifi_client).controller_type = PropertyMock(return_value=ControllerType.UNIFI_OS)

        tool = ExportConfigurationTool()
        result = await tool.execute(
            mock_unifi_client,
            include_networks=True,
            include_firewall_rules=True,
            include_routing=False,
            include_port_forwards=False,
            include_wlans=False,
        )

        assert result["success"] is True
        assert result["data"]["controller_type"] == "unifi_os"
        assert result["data"]["api_version"] == "v2"
