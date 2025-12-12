"""Unit tests for migration support tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.migration import (
    GetDHCPStatusTool,
    VerifyVLANConnectivityTool,
    ExportConfigurationTool,
)
from unifi_mcp.tools.base import ToolError


@pytest.fixture
def mock_unifi_client():
    client = MagicMock()
    client.get = AsyncMock()
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
        {"_id": "rule1", "name": "Allow Core to IoT", "enabled": True, "action": "accept", "protocol": "all", "src_address": "192.168.10.0/24", "dst_address": "192.168.30.0/24"},
        {"_id": "rule2", "name": "Block IoT to Core", "enabled": True, "action": "drop", "protocol": "all", "src_address": "192.168.30.0/24", "dst_address": "192.168.10.0/24"},
    ]


async def test_get_dhcp_status_all_networks(mock_unifi_client, sample_networks, sample_clients):
    mock_unifi_client.get.side_effect = [{"data": sample_networks}, {"data": sample_clients}]
    tool = GetDHCPStatusTool()
    result = await tool.execute(mock_unifi_client)
    assert result["success"] is True
    assert result["data"]["total_networks"] == 3


async def test_verify_vlan_connectivity_allowed(mock_unifi_client, sample_networks, sample_firewall_rules):
    mock_unifi_client.get.side_effect = [{"data": sample_networks}, {"data": sample_firewall_rules}]
    tool = VerifyVLANConnectivityTool()
    result = await tool.execute(mock_unifi_client, source_vlan="10", destination_vlan="30")
    assert result["success"] is True


async def test_export_configuration_all_sections(mock_unifi_client, sample_networks, sample_firewall_rules):
    mock_unifi_client.get.side_effect = [
        {"data": sample_networks},
        {"data": sample_firewall_rules},
        {"data": []},
        {"data": []},
        {"data": []},
    ]
    tool = ExportConfigurationTool()
    result = await tool.execute(mock_unifi_client)
    assert result["success"] is True
    assert "configuration" in result["data"]


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
