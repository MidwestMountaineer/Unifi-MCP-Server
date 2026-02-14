"""Unit tests for device tool v1 API migration.

Tests cover:
- ListDevicesTool: v1 API migration with get_v1("devices")
- GetDeviceDetailsTool: direct v1 lookup with get_v1("devices/{id}")
- ListPendingDevicesTool: new tool calling get_v1("devices/pending")
- v1 field name handling (id vs _id, state string vs integer)
- Backward compatibility with legacy field names
- 404 error handling for GetDeviceDetailsTool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.network_discovery import (
    ListDevicesTool,
    GetDeviceDetailsTool,
    ListPendingDevicesTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient


# Mock v1 device data (using v1 field names)

MOCK_V1_DEVICES = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "mac": "aa:bb:cc:dd:ee:01",
        "name": "Main Switch",
        "type": "usw",
        "model": "USW-Pro-24-PoE",
        "ip": "192.168.1.10",
        "state": "ONLINE",
        "uptime": 86400,
        "version": "7.0.50",
        "adopted": True,
        "system-stats": {"cpu": 15, "mem": 30},
        "port_table": [
            {
                "port_idx": 1,
                "name": "Port 1",
                "enable": True,
                "up": True,
                "speed": 1000,
                "full_duplex": True,
                "poe_enable": True,
                "poe_power": 5.2,
            }
        ],
    },
    {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "mac": "aa:bb:cc:dd:ee:02",
        "name": "Living Room AP",
        "type": "uap",
        "model": "U6-LR",
        "ip": "192.168.1.20",
        "state": "ONLINE",
        "uptime": 172800,
        "version": "7.0.50",
        "adopted": True,
        "num_sta": 5,
        "radio_table": [
            {
                "name": "2.4GHz",
                "radio": "ng",
                "channel": 6,
                "tx_power": 20,
                "num_sta": 3,
            }
        ],
    },
    {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "mac": "aa:bb:cc:dd:ee:03",
        "name": "Dream Machine",
        "type": "udm",
        "model": "UDM-SE",
        "ip": "192.168.1.1",
        "state": "ONLINE",
        "uptime": 259200,
        "version": "4.0.6",
        "adopted": True,
    },
    {
        "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "mac": "aa:bb:cc:dd:ee:04",
        "name": "Office AP",
        "type": "uap",
        "model": "U6-Pro",
        "ip": "192.168.1.21",
        "state": "OFFLINE",
        "uptime": 0,
        "version": "7.0.50",
        "adopted": True,
    },
]

MOCK_V1_PENDING_DEVICES = [
    {
        "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
        "mac": "ff:ee:dd:cc:bb:01",
        "name": "New Switch",
        "model": "USW-Lite-8-PoE",
        "type": "usw",
    },
    {
        "id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
        "mac": "ff:ee:dd:cc:bb:02",
        "model": "U6-Mesh",
        "type": "uap",
    },
]


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client with get_v1 support."""
    client = MagicMock(spec=UniFiClient)
    client.get_v1 = AsyncMock()
    return client


class TestListDevicesToolV1:
    """Test ListDevicesTool with v1 API migration."""

    @pytest.mark.asyncio
    async def test_list_devices_calls_get_v1(self, mock_unifi_client):
        """Verify ListDevicesTool calls get_v1('devices') instead of legacy endpoint."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_V1_DEVICES,
            "totalCount": len(MOCK_V1_DEVICES),
            "offset": 0,
            "limit": 25,
            "count": len(MOCK_V1_DEVICES),
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)

        mock_unifi_client.get_v1.assert_called_once_with("devices", params=None)
        assert result["total"] == len(MOCK_V1_DEVICES)

    @pytest.mark.asyncio
    async def test_list_devices_v1_id_field(self, mock_unifi_client):
        """Verify v1 'id' field is used instead of legacy '_id'."""
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_V1_DEVICES[0]],
            "totalCount": 1,
            "offset": 0,
            "limit": 25,
            "count": 1,
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)

        device = result["data"][0]
        assert device["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    @pytest.mark.asyncio
    async def test_list_devices_v1_state_string(self, mock_unifi_client):
        """Verify v1 string state ('ONLINE'/'OFFLINE') is handled correctly."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_V1_DEVICES,
            "totalCount": len(MOCK_V1_DEVICES),
            "offset": 0,
            "limit": 25,
            "count": len(MOCK_V1_DEVICES),
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)

        # First 3 devices are ONLINE
        assert result["data"][0]["status"] == "online"
        assert result["data"][1]["status"] == "online"
        assert result["data"][2]["status"] == "online"
        # Last device is OFFLINE
        assert result["data"][3]["status"] == "offline"

    @pytest.mark.asyncio
    async def test_list_devices_legacy_state_integer(self, mock_unifi_client):
        """Verify legacy integer state (1/0) still works for backward compat."""
        legacy_device = {
            "_id": "legacy-id-123",
            "mac": "11:22:33:44:55:66",
            "name": "Legacy Device",
            "type": "usw",
            "model": "US-8",
            "ip": "192.168.1.50",
            "state": 1,
            "uptime": 3600,
            "version": "6.5.55",
            "adopted": True,
        }
        mock_unifi_client.get_v1.return_value = {
            "data": [legacy_device],
            "totalCount": 1,
            "offset": 0,
            "limit": 25,
            "count": 1,
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)

        device = result["data"][0]
        assert device["id"] == "legacy-id-123"
        assert device["status"] == "online"

    @pytest.mark.asyncio
    async def test_list_devices_filter_by_type(self, mock_unifi_client):
        """Verify device type filtering still works with v1 data."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_V1_DEVICES,
            "totalCount": len(MOCK_V1_DEVICES),
            "offset": 0,
            "limit": 25,
            "count": len(MOCK_V1_DEVICES),
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client, device_type="ap")

        # Should only return the 2 APs
        assert result["total"] == 2
        for device in result["data"]:
            assert device["type"] == "access_point"

    @pytest.mark.asyncio
    async def test_list_devices_empty_response(self, mock_unifi_client):
        """Verify empty v1 response is handled."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
            "offset": 0,
            "limit": 25,
            "count": 0,
        }

        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_list_devices_api_error(self, mock_unifi_client):
        """Verify API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListDevicesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"


class TestGetDeviceDetailsToolV1:
    """Test GetDeviceDetailsTool with v1 API migration."""

    @pytest.mark.asyncio
    async def test_direct_v1_lookup(self, mock_unifi_client):
        """Verify direct v1 lookup by device ID."""
        device_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_unifi_client.get_v1.return_value = MOCK_V1_DEVICES[0]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id=device_id)

        mock_unifi_client.get_v1.assert_called_once_with(f"devices/{device_id}")
        assert result["data"]["id"] == device_id
        assert result["data"]["name"] == "Main Switch"

    @pytest.mark.asyncio
    async def test_direct_v1_lookup_wrapped_response(self, mock_unifi_client):
        """Verify handling of v1 response wrapped in data array."""
        device_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_V1_DEVICES[0]],
        }

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id=device_id)

        assert result["data"]["id"] == device_id

    @pytest.mark.asyncio
    async def test_fallback_to_list_on_lookup_failure(self, mock_unifi_client):
        """Verify fallback to list+search when direct lookup fails (e.g., MAC search)."""
        mac = "aa:bb:cc:dd:ee:01"

        # First call (direct lookup) fails, second call (list all) succeeds
        mock_unifi_client.get_v1.side_effect = [
            Exception("404 Not Found"),
            {
                "data": MOCK_V1_DEVICES,
                "totalCount": len(MOCK_V1_DEVICES),
            },
        ]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id=mac)

        assert result["data"]["mac"] == mac
        assert result["data"]["name"] == "Main Switch"
        # Should have called get_v1 twice: once for direct, once for fallback
        assert mock_unifi_client.get_v1.call_count == 2

    @pytest.mark.asyncio
    async def test_device_not_found(self, mock_unifi_client):
        """Verify 404 handling when device doesn't exist."""
        # Direct lookup fails
        mock_unifi_client.get_v1.side_effect = [
            Exception("404 Not Found"),
            {"data": MOCK_V1_DEVICES, "totalCount": len(MOCK_V1_DEVICES)},
        ]

        tool = GetDeviceDetailsTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, device_id="nonexistent-id")

        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_v1_state_string_in_details(self, mock_unifi_client):
        """Verify v1 string state is handled in detail formatting."""
        mock_unifi_client.get_v1.return_value = MOCK_V1_DEVICES[0]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        )

        assert result["data"]["status"] == "online"

    @pytest.mark.asyncio
    async def test_v1_id_field_in_details(self, mock_unifi_client):
        """Verify v1 'id' field is used in detail formatting."""
        mock_unifi_client.get_v1.return_value = MOCK_V1_DEVICES[0]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        )

        assert result["data"]["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    @pytest.mark.asyncio
    async def test_switch_includes_ports(self, mock_unifi_client):
        """Verify switch device includes port information."""
        mock_unifi_client.get_v1.return_value = MOCK_V1_DEVICES[0]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        )

        assert "ports" in result["data"]
        assert result["data"]["port_count"] == 1

    @pytest.mark.asyncio
    async def test_ap_includes_radios(self, mock_unifi_client):
        """Verify AP device includes radio information."""
        mock_unifi_client.get_v1.return_value = MOCK_V1_DEVICES[1]

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
        )

        assert "radios" in result["data"]
        assert result["data"]["client_count"] == 5

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Verify general API errors are wrapped in ToolError."""
        # Both direct and fallback fail with non-ToolError
        mock_unifi_client.get_v1.side_effect = Exception("Connection timeout")

        tool = GetDeviceDetailsTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, device_id="some-id")

        assert exc_info.value.code == "API_ERROR"


class TestListPendingDevicesTool:
    """Test ListPendingDevicesTool (new v1 tool)."""

    @pytest.mark.asyncio
    async def test_list_pending_devices(self, mock_unifi_client):
        """Verify pending devices are fetched via get_v1('devices/pending')."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_V1_PENDING_DEVICES,
            "totalCount": len(MOCK_V1_PENDING_DEVICES),
            "offset": 0,
            "limit": 25,
            "count": len(MOCK_V1_PENDING_DEVICES),
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        mock_unifi_client.get_v1.assert_called_once_with("devices/pending", params=None)
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_pending_device_format(self, mock_unifi_client):
        """Verify pending device formatting includes id, mac, name, model, type."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_V1_PENDING_DEVICES,
            "totalCount": len(MOCK_V1_PENDING_DEVICES),
            "offset": 0,
            "limit": 25,
            "count": len(MOCK_V1_PENDING_DEVICES),
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        device = result["data"][0]
        assert device["id"] == "e5f6a7b8-c9d0-1234-efab-345678901234"
        assert device["mac"] == "ff:ee:dd:cc:bb:01"
        assert device["name"] == "New Switch"
        assert device["model"] == "USW-Lite-8-PoE"
        assert device["type"] == "usw"

    @pytest.mark.asyncio
    async def test_pending_device_name_fallback(self, mock_unifi_client):
        """Verify name falls back to model when name is missing."""
        mock_unifi_client.get_v1.return_value = {
            "data": [MOCK_V1_PENDING_DEVICES[1]],
            "totalCount": 1,
            "offset": 0,
            "limit": 25,
            "count": 1,
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        # Second pending device has no name, should fall back to model
        device = result["data"][0]
        assert device["name"] == "U6-Mesh"

    @pytest.mark.asyncio
    async def test_pending_devices_empty(self, mock_unifi_client):
        """Verify empty pending devices response."""
        mock_unifi_client.get_v1.return_value = {
            "data": [],
            "totalCount": 0,
            "offset": 0,
            "limit": 25,
            "count": 0,
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["total"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_pending_devices_api_error(self, mock_unifi_client):
        """Verify API errors are wrapped in ToolError."""
        mock_unifi_client.get_v1.side_effect = Exception("Connection refused")

        tool = ListPendingDevicesTool()
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        assert exc_info.value.code == "API_ERROR"

    def test_tool_metadata(self):
        """Verify tool metadata is correct."""
        tool = ListPendingDevicesTool()
        assert tool.name == "unifi_list_pending_devices"
        assert tool.category == "network_discovery"
