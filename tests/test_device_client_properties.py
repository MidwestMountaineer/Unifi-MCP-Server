"""Property-based tests for migrated device and client formatting.

Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

For any valid v1 device dict or client dict, the migrated formatter SHALL
produce output containing all fields that the legacy formatter produced
(name/hostname, MAC, IP, model/type), ensuring no regression in output content.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from unifi_mcp.tools.network_discovery import (
    ListDevicesTool,
    GetDeviceDetailsTool,
    ListPendingDevicesTool,
    ListClientsTool,
    GetClientDetailsTool,
)
from unifi_mcp.unifi_client import UniFiClient


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

uuids = st.uuids().map(str)

# MAC addresses in aa:bb:cc:dd:ee:ff format
mac_addresses = st.tuples(
    *[st.integers(min_value=0, max_value=255) for _ in range(6)]
).map(lambda t: ":".join(f"{b:02x}" for b in t))

# IPv4 addresses
ipv4_addresses = st.tuples(
    st.integers(1, 254),
    st.integers(0, 255),
    st.integers(0, 255),
    st.integers(1, 254),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}")

# Device type codes
device_types = st.sampled_from(["usw", "uap", "u7p", "ugw", "udm", "uxg"])

# Device state: v1 uses strings
device_states = st.sampled_from(["ONLINE", "OFFLINE"])

# Firmware version strings (simple strategy, avoids slow regex)
firmware_versions = st.tuples(
    st.integers(1, 9), st.integers(0, 99), st.integers(0, 99)
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}")

# V1 device dicts
v1_devices = st.fixed_dictionaries({
    "id": uuids,
    "mac": mac_addresses,
    "name": st.text(min_size=1, max_size=50),
    "type": device_types,
    "model": st.text(min_size=1, max_size=20),
    "ip": ipv4_addresses,
    "state": device_states,
    "uptime": st.integers(min_value=0, max_value=10_000_000),
    "version": firmware_versions,
    "adopted": st.booleans(),
})

# V1 device dicts with detail-level fields
v1_devices_detailed = st.fixed_dictionaries({
    "id": uuids,
    "mac": mac_addresses,
    "name": st.text(min_size=1, max_size=50),
    "type": device_types,
    "model": st.text(min_size=1, max_size=20),
    "model_name": st.text(min_size=1, max_size=30),
    "ip": ipv4_addresses,
    "netmask": st.just("255.255.255.0"),
    "gateway": ipv4_addresses,
    "state": device_states,
    "uptime": st.integers(min_value=0, max_value=10_000_000),
    "version": firmware_versions,
    "adopted": st.booleans(),
    "upgradable": st.booleans(),
    "serial": st.text(min_size=0, max_size=20),
    "system-stats": st.fixed_dictionaries({
        "cpu": st.integers(min_value=0, max_value=100),
        "mem": st.integers(min_value=0, max_value=100),
    }),
    "uplink": st.just({}),
})

# V1 pending device dicts
v1_pending_devices = st.fixed_dictionaries({
    "id": uuids,
    "mac": mac_addresses,
    "name": st.text(min_size=1, max_size=50),
    "model": st.text(min_size=1, max_size=20),
    "type": device_types,
})

# Client dicts — use is_wired (bool) for connection type detection
# (the formatter uses is_wired to determine wired vs wireless)
v1_clients = st.fixed_dictionaries({
    "mac": mac_addresses,
    "name": st.text(min_size=1, max_size=50),
    "ip": ipv4_addresses,
    "is_wired": st.booleans(),
    "network": st.text(min_size=1, max_size=30),
    "uptime": st.integers(min_value=0, max_value=10_000_000),
    "tx_bytes": st.integers(min_value=0, max_value=10**12),
    "rx_bytes": st.integers(min_value=0, max_value=10**12),
})

# Client dicts with detail-level fields
v1_clients_detailed = st.fixed_dictionaries({
    "mac": mac_addresses,
    "name": st.text(min_size=1, max_size=50),
    "ip": ipv4_addresses,
    "is_wired": st.booleans(),
    "network": st.text(min_size=1, max_size=30),
    "network_id": uuids,
    "vlan": st.integers(min_value=0, max_value=4094),
    "oui": st.text(min_size=0, max_size=30),
    "uptime": st.integers(min_value=0, max_value=10_000_000),
    "tx_bytes": st.integers(min_value=0, max_value=10**12),
    "rx_bytes": st.integers(min_value=0, max_value=10**12),
    "tx_packets": st.integers(min_value=0, max_value=10**9),
    "rx_packets": st.integers(min_value=0, max_value=10**9),
    "tx_rate": st.integers(min_value=0, max_value=10**9),
    "rx_rate": st.integers(min_value=0, max_value=10**9),
    "first_seen": st.integers(min_value=0, max_value=2_000_000_000),
    "last_seen": st.integers(min_value=0, max_value=2_000_000_000),
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
# Property 9a: Device Summary Formatting
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestDeviceSummaryFormattingProperty:
    """For any valid v1 device dict, _format_device_summary SHALL produce
    output containing name, MAC, IP, model, type, and status.

    **Validates: Requirements 7.1**
    """

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_contains_required_fields(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Device summary must contain id, mac, name, type, model, ip, status.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        assert "id" in result
        assert "mac" in result
        assert "name" in result
        assert "type" in result
        assert "model" in result
        assert "ip" in result
        assert "status" in result

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_preserves_mac_and_ip(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        MAC and IP must be preserved exactly from input.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        assert result["mac"] == device["mac"]
        assert result["ip"] == device["ip"]

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_preserves_id_and_name(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        ID and name must be preserved from v1 input.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        assert result["id"] == device["id"]
        assert result["name"] == device["name"]

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_preserves_model(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Model must be preserved from input.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        assert result["model"] == device["model"]

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_maps_type_to_friendly_name(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Device type code must be mapped to a friendly name.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        expected_types = {
            "usw": "switch",
            "uap": "access_point",
            "u7p": "access_point",
            "ugw": "gateway",
            "udm": "dream_machine",
            "uxg": "gateway",
        }
        assert result["type"] == expected_types[device["type"]]

    @given(device=v1_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_summary_maps_v1_state_to_status(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        V1 state strings (ONLINE/OFFLINE) must map to online/offline status.
        """
        tool = ListDevicesTool()
        result = tool._format_device_summary(device)

        expected = "online" if device["state"] == "ONLINE" else "offline"
        assert result["status"] == expected


# ---------------------------------------------------------------------------
# Property 9b: Device Detail Formatting
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestDeviceDetailFormattingProperty:
    """For any valid v1 device dict, _format_device_details SHALL produce
    output containing name, MAC, IP, model, type, status, and extended fields.

    **Validates: Requirements 7.2**
    """

    @given(device=v1_devices_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_details_contains_required_fields(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Device details must contain all core fields: id, mac, name, type,
        model, ip, status, adopted, uptime, version.
        """
        tool = GetDeviceDetailsTool()
        result = tool._format_device_details(device)

        assert "id" in result
        assert "mac" in result
        assert "name" in result
        assert "type" in result
        assert "model" in result
        assert "ip" in result
        assert "status" in result
        assert "adopted" in result
        assert "uptime" in result
        assert "version" in result

    @given(device=v1_devices_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_details_preserves_core_fields(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Core identifying fields must be preserved exactly.
        """
        tool = GetDeviceDetailsTool()
        result = tool._format_device_details(device)

        assert result["id"] == device["id"]
        assert result["mac"] == device["mac"]
        assert result["name"] == device["name"]
        assert result["ip"] == device["ip"]
        assert result["model"] == device["model"]
        assert result["adopted"] == device["adopted"]
        assert result["uptime"] == device["uptime"]

    @given(device=v1_devices_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_details_includes_system_stats(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        System stats (cpu, memory) must be extracted from the device data.
        """
        tool = GetDeviceDetailsTool()
        result = tool._format_device_details(device)

        assert "cpu_usage" in result
        assert "memory_usage" in result
        assert result["cpu_usage"] == device["system-stats"]["cpu"]
        assert result["memory_usage"] == device["system-stats"]["mem"]

    @given(device=v1_devices_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_details_includes_uptime_readable(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        A human-readable uptime string must be present.
        """
        tool = GetDeviceDetailsTool()
        result = tool._format_device_details(device)

        assert "uptime_readable" in result
        assert isinstance(result["uptime_readable"], str)
        assert len(result["uptime_readable"]) > 0


# ---------------------------------------------------------------------------
# Property 9c: Pending Device Formatting
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestPendingDeviceFormattingProperty:
    """For any valid v1 pending device dict, _format_pending_device SHALL
    produce output containing id, mac, name, model, and type.

    **Validates: Requirements 7.5**
    """

    @given(device=v1_pending_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_pending_device_contains_required_fields(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Pending device summary must contain id, mac, name, model, type.
        """
        tool = ListPendingDevicesTool()
        result = tool._format_pending_device(device)

        assert "id" in result
        assert "mac" in result
        assert "name" in result
        assert "model" in result
        assert "type" in result

    @given(device=v1_pending_devices)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_pending_device_preserves_fields(self, device):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        All fields must be preserved from the input.
        """
        tool = ListPendingDevicesTool()
        result = tool._format_pending_device(device)

        assert result["id"] == device["id"]
        assert result["mac"] == device["mac"]
        assert result["name"] == device["name"]
        assert result["model"] == device["model"]
        assert result["type"] == device["type"]


# ---------------------------------------------------------------------------
# Property 9d: Client Summary Formatting
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestClientSummaryFormattingProperty:
    """For any valid client dict, _format_client_summary SHALL produce
    output containing name, MAC, IP, and connection type.

    **Validates: Requirements 7.3**
    """

    @given(client=v1_clients)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_summary_contains_required_fields(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Client summary must contain mac, name, ip, connection_type, network.
        """
        tool = ListClientsTool()
        result = tool._format_client_summary(client)

        assert "mac" in result
        assert "name" in result
        assert "ip" in result
        assert "connection_type" in result
        assert "network" in result

    @given(client=v1_clients)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_summary_preserves_mac_and_ip(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        MAC and IP must be preserved exactly.
        """
        tool = ListClientsTool()
        result = tool._format_client_summary(client)

        assert result["mac"] == client["mac"]
        assert result["ip"] == client["ip"]

    @given(client=v1_clients)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_summary_preserves_name(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Client name must be preserved from input.
        """
        tool = ListClientsTool()
        result = tool._format_client_summary(client)

        assert result["name"] == client["name"]

    @given(client=v1_clients)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_summary_maps_is_wired_to_connection_type(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        is_wired boolean must map to wired/wireless connection_type.
        """
        tool = ListClientsTool()
        result = tool._format_client_summary(client)

        expected = "wired" if client["is_wired"] else "wireless"
        assert result["connection_type"] == expected

    @given(client=v1_clients)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_summary_includes_bandwidth_info(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Bandwidth fields (tx_bytes, rx_bytes) and readable versions must be present.
        """
        tool = ListClientsTool()
        result = tool._format_client_summary(client)

        assert result["tx_bytes"] == client["tx_bytes"]
        assert result["rx_bytes"] == client["rx_bytes"]
        assert "tx_bytes_readable" in result
        assert "rx_bytes_readable" in result


# ---------------------------------------------------------------------------
# Property 9e: Client Detail Formatting
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestClientDetailFormattingProperty:
    """For any valid client dict, _format_client_details SHALL produce
    output containing name, MAC, IP, connection type, and extended fields.

    **Validates: Requirements 7.4**
    """

    @given(client=v1_clients_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_details_contains_required_fields(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Client details must contain mac, name, ip, connection_type, network,
        uptime, tx_bytes, rx_bytes.
        """
        tool = GetClientDetailsTool()
        result = tool._format_client_details(client)

        assert "mac" in result
        assert "name" in result
        assert "ip" in result
        assert "connection_type" in result
        assert "network" in result
        assert "uptime" in result
        assert "tx_bytes" in result
        assert "rx_bytes" in result

    @given(client=v1_clients_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_details_preserves_core_fields(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        Core identifying fields must be preserved exactly.
        """
        tool = GetClientDetailsTool()
        result = tool._format_client_details(client)

        assert result["mac"] == client["mac"]
        assert result["name"] == client["name"]
        assert result["ip"] == client["ip"]
        assert result["network"] == client["network"]
        assert result["uptime"] == client["uptime"]
        assert result["tx_bytes"] == client["tx_bytes"]
        assert result["rx_bytes"] == client["rx_bytes"]

    @given(client=v1_clients_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_details_maps_is_wired(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        is_wired must map correctly to connection_type.
        """
        tool = GetClientDetailsTool()
        result = tool._format_client_details(client)

        expected = "wired" if client["is_wired"] else "wireless"
        assert result["connection_type"] == expected

    @given(client=v1_clients_detailed)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_details_includes_uptime_readable(self, client):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        A human-readable uptime string must be present.
        """
        tool = GetClientDetailsTool()
        result = tool._format_client_details(client)

        assert "uptime_readable" in result
        assert isinstance(result["uptime_readable"], str)
        assert len(result["uptime_readable"]) > 0


# ---------------------------------------------------------------------------
# Property 9f: Full Execute Path — Device List
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestDeviceListExecuteProperty:
    """For any valid v1 response containing device data, the full execute path
    SHALL produce a successful result with all devices formatted correctly.

    **Validates: Requirements 7.1**
    """

    @given(response=v1_response(v1_devices))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_device_list_execute_returns_all_devices(self, response):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        The execute path must return all devices with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListDevicesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, device_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["mac"] == device_data["mac"]
            assert formatted["ip"] == device_data["ip"]
            assert formatted["name"] == device_data["name"]
            assert formatted["model"] == device_data["model"]
            assert "type" in formatted
            assert "status" in formatted


# ---------------------------------------------------------------------------
# Property 9g: Full Execute Path — Client List
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestClientListExecuteProperty:
    """For any valid response containing client data, the full execute path
    SHALL produce a successful result with all clients formatted correctly.

    **Validates: Requirements 7.3**
    """

    @given(response=v1_response(v1_clients))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_client_list_execute_returns_all_clients(self, response):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        The execute path must return all clients with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        # ListClientsTool.execute() calls get_v1("clients") in the migrated version
        # and get("/api/s/{site}/stat/sta") in the legacy version.
        # Mock both to handle whichever version is installed.
        mock_client.get_v1 = AsyncMock(return_value=response)
        mock_client.get = AsyncMock(return_value=response)

        tool = ListClientsTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True

        for i, client_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["mac"] == client_data["mac"]
            assert formatted["ip"] == client_data["ip"]
            assert formatted["name"] == client_data["name"]
            assert "connection_type" in formatted


# ---------------------------------------------------------------------------
# Property 9h: Full Execute Path — Pending Devices
# Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting
# ---------------------------------------------------------------------------

class TestPendingDeviceListExecuteProperty:
    """For any valid v1 response containing pending device data, the full
    execute path SHALL produce a successful result with all devices formatted.

    **Validates: Requirements 7.5**
    """

    @given(response=v1_response(v1_pending_devices))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_pending_device_list_execute_returns_all(self, response):
        """Feature: unifi-api-v1-migration, Property 9: Migrated Device and Client Formatting

        The execute path must return all pending devices with correct formatting.
        """
        mock_client = MagicMock(spec=UniFiClient)
        mock_client.get_v1 = AsyncMock(return_value=response)

        tool = ListPendingDevicesTool()
        result = asyncio.run(tool.execute(mock_client))

        assert result["success"] is True
        assert result["count"] == len(response["data"])

        for i, device_data in enumerate(response["data"]):
            formatted = result["data"][i]
            assert formatted["id"] == device_data["id"]
            assert formatted["mac"] == device_data["mac"]
            assert formatted["model"] == device_data["model"]
            assert formatted["type"] == device_data["type"]
