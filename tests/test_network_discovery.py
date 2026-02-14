"""Unit tests for network discovery tools.

Tests cover:
- ListDevicesTool: device listing with filtering and pagination
- GetDeviceDetailsTool: device detail retrieval
- Mock UniFi API responses
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from unifi_mcp.tools.network_discovery import (
    ListDevicesTool,
    GetDeviceDetailsTool,
    ListPendingDevicesTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient

# Mock device data (simulating UniFi API responses)

MOCK_DEVICES = [
    {
        "_id": "device1",
        "mac": "aa:bb:cc:dd:ee:01",
        "name": "Main Switch",
        "type": "usw",
        "model": "US24",
        "ip": "192.168.1.10",
        "state": 1,
        "uptime": 86400,
        "version": "6.5.55",
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
                "poe_enable": False,
                "poe_power": 0,
            }
        ],
    },
    {
        "_id": "device2",
        "mac": "aa:bb:cc:dd:ee:02",
        "name": "Living Room AP",
        "type": "uap",
        "model": "U6-LR",
        "ip": "192.168.1.20",
        "state": 1,
        "uptime": 172800,
        "version": "6.5.55",
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
        "_id": "device3",
        "mac": "aa:bb:cc:dd:ee:03",
        "name": "Dream Machine",
        "type": "udm",
        "model": "UDM-Pro",
        "ip": "192.168.1.1",
        "state": 1,
        "uptime": 259200,
        "version": "3.0.20",
        "adopted": True,
    },
    {
        "_id": "device4",
        "mac": "aa:bb:cc:dd:ee:04",
        "name": "Office AP",
        "type": "uap",
        "model": "U6-Pro",
        "ip": "192.168.1.21",
        "state": 0,  # Offline
        "uptime": 0,
        "version": "6.5.55",
        "adopted": True,
    },
]

@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get = AsyncMock()
    client.get_v1 = AsyncMock()
    return client

class TestListDevicesTool:
    """Test ListDevicesTool functionality."""
    
    @pytest.mark.asyncio
    async def test_list_all_devices(self, mock_unifi_client):
        """Test listing all devices without filtering."""
        # Setup mock response (v1 envelope)
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        # Create tool and execute
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert result["count"] == 4
        assert result["total"] == 4
        assert result["page"] == 1
        assert result["page_size"] == 50
        
        # Verify API call
        mock_unifi_client.get_v1.assert_called_once_with("devices", params=None)
    
    @pytest.mark.asyncio
    async def test_list_devices_filter_by_switch(self, mock_unifi_client):
        """Test filtering devices by type (switch)."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client, device_type="switch")
        
        # Should only return switches
        assert result["success"] is True
        assert result["count"] == 1
        assert result["data"][0]["type"] == "switch"
        assert result["data"][0]["name"] == "Main Switch"
    
    @pytest.mark.asyncio
    async def test_list_devices_filter_by_ap(self, mock_unifi_client):
        """Test filtering devices by type (access point)."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client, device_type="ap")
        
        # Should only return APs
        assert result["success"] is True
        assert result["count"] == 2
        assert all(d["type"] == "access_point" for d in result["data"])
    
    @pytest.mark.asyncio
    async def test_list_devices_filter_by_gateway(self, mock_unifi_client):
        """Test filtering devices by type (gateway)."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client, device_type="gateway")
        
        # Should only return gateways
        assert result["success"] is True
        assert result["count"] == 1
        assert result["data"][0]["type"] == "dream_machine"
        assert result["data"][0]["name"] == "Dream Machine"
    
    @pytest.mark.asyncio
    async def test_list_devices_pagination(self, mock_unifi_client):
        """Test pagination of device list."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        
        # Get first page (2 items per page)
        result_page1 = await tool.execute(
            mock_unifi_client,
            page=1,
            page_size=2
        )
        
        assert result_page1["success"] is True
        assert result_page1["count"] == 2
        assert result_page1["total"] == 4
        assert result_page1["page"] == 1
        assert result_page1["page_size"] == 2
        
        # Get second page
        result_page2 = await tool.execute(
            mock_unifi_client,
            page=2,
            page_size=2
        )
        
        assert result_page2["count"] == 2
        assert result_page2["page"] == 2
        
        # Verify different devices on each page
        page1_ids = [d["id"] for d in result_page1["data"]]
        page2_ids = [d["id"] for d in result_page2["data"]]
        assert page1_ids != page2_ids
    
    @pytest.mark.asyncio
    async def test_list_devices_last_page_partial(self, mock_unifi_client):
        """Test last page with partial results."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(
            mock_unifi_client,
            page=2,
            page_size=3
        )
        
        # Last page should have only 1 device (4 total, 3 per page)
        assert result["success"] is True
        assert result["count"] == 1
        assert result["total"] == 4
        assert result["page"] == 2
    
    @pytest.mark.asyncio
    async def test_list_devices_empty_result(self, mock_unifi_client):
        """Test listing devices when none exist."""
        mock_unifi_client.get_v1.return_value = {"data": [], "totalCount": 0}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)
        
        assert result["success"] is True
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["data"] == []
    
    @pytest.mark.asyncio
    async def test_list_devices_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get_v1.side_effect = Exception("API connection failed")
        
        tool = ListDevicesTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)
        
        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve device list" in error.message
    
    @pytest.mark.asyncio
    async def test_device_summary_format(self, mock_unifi_client):
        """Test that device summary contains expected fields."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check first device has expected summary fields
        device = result["data"][0]
        expected_fields = [
            "id", "mac", "name", "type", "model",
            "ip", "status", "uptime", "version", "adopted"
        ]
        
        for field in expected_fields:
            assert field in device, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_device_status_online(self, mock_unifi_client):
        """Test that online devices are marked correctly."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)
        
        # First three devices should be online
        assert result["data"][0]["status"] == "online"
        assert result["data"][1]["status"] == "online"
        assert result["data"][2]["status"] == "online"
    
    @pytest.mark.asyncio
    async def test_device_status_offline(self, mock_unifi_client):
        """Test that offline devices are marked correctly."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_DEVICES, "totalCount": len(MOCK_DEVICES)}
        
        tool = ListDevicesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Fourth device should be offline
        assert result["data"][3]["status"] == "offline"
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        tool = ListDevicesTool()
        
        assert tool.name == "unifi_list_devices"
        assert tool.category == "network_discovery"
        assert tool.requires_confirmation is False
        assert "filter" in tool.description.lower() or "list" in tool.description.lower()
        
        # Check input schema
        assert "properties" in tool.input_schema
        assert "device_type" in tool.input_schema["properties"]
        assert "page" in tool.input_schema["properties"]
        assert "page_size" in tool.input_schema["properties"]


class TestGetDeviceDetailsTool:
    """Test GetDeviceDetailsTool functionality."""

    def _mock_device_lookup(self, mock_unifi_client, device_id, devices=None):
        """Helper to set up get_v1 mock for device detail lookups.

        For direct ID lookup, returns the matching device.
        For MAC/not-found, simulates direct lookup failure + fallback to list.
        """
        if devices is None:
            devices = MOCK_DEVICES

        # Find device by _id
        target = None
        for d in devices:
            if d.get("_id", "").lower() == device_id.lower():
                target = d
                break

        if target:
            # Direct lookup succeeds - return the device directly
            mock_unifi_client.get_v1.return_value = target
        else:
            # Direct lookup fails, fallback fetches all devices
            mock_unifi_client.get_v1.side_effect = [
                Exception("404 Not Found"),
                {"data": devices, "totalCount": len(devices)},
            ]

    @pytest.mark.asyncio
    async def test_get_device_by_id(self, mock_unifi_client):
        """Test getting device details by ID."""
        self._mock_device_lookup(mock_unifi_client, "device1")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id="device1")

        assert result["success"] is True
        assert result["type"] == "device"
        assert "data" in result

        device = result["data"]
        assert device["id"] == "device1"
        assert device["name"] == "Main Switch"
        assert device["type"] == "switch"

    @pytest.mark.asyncio
    async def test_get_device_by_mac(self, mock_unifi_client):
        """Test getting device details by MAC address."""
        self._mock_device_lookup(mock_unifi_client, "aa:bb:cc:dd:ee:02")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="aa:bb:cc:dd:ee:02"
        )

        assert result["success"] is True
        device = result["data"]
        assert device["mac"] == "aa:bb:cc:dd:ee:02"
        assert device["name"] == "Living Room AP"

    @pytest.mark.asyncio
    async def test_get_device_by_mac_without_colons(self, mock_unifi_client):
        """Test getting device by MAC address without colons."""
        self._mock_device_lookup(mock_unifi_client, "aabbccddee02")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            device_id="aabbccddee02"
        )

        assert result["success"] is True
        device = result["data"]
        assert device["mac"] == "aa:bb:cc:dd:ee:02"

    @pytest.mark.asyncio
    async def test_get_device_not_found(self, mock_unifi_client):
        """Test getting device that doesn't exist."""
        self._mock_device_lookup(mock_unifi_client, "nonexistent")

        tool = GetDeviceDetailsTool()

        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, device_id="nonexistent")

        error = exc_info.value
        assert error.code == "DEVICE_NOT_FOUND"
        assert "nonexistent" in error.details

    @pytest.mark.asyncio
    async def test_device_detail_format(self, mock_unifi_client):
        """Test that device details contain expected fields."""
        self._mock_device_lookup(mock_unifi_client, "device1")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id="device1")

        device = result["data"]

        # Check basic fields
        expected_fields = [
            "id", "mac", "name", "type", "model", "model_name",
            "ip", "netmask", "gateway", "status", "adopted",
            "uptime", "uptime_readable", "version", "upgradable",
            "serial", "board_rev", "cpu_usage", "memory_usage", "uplink"
        ]

        for field in expected_fields:
            assert field in device, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_switch_includes_ports(self, mock_unifi_client):
        """Test that switch details include port information."""
        self._mock_device_lookup(mock_unifi_client, "device1")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id="device1")

        device = result["data"]
        assert "ports" in device
        assert "port_count" in device
        assert device["port_count"] == 1
        assert len(device["ports"]) == 1

        # Check port structure
        port = device["ports"][0]
        assert "port_idx" in port
        assert "name" in port
        assert "enabled" in port
        assert "up" in port
        assert "speed" in port

    @pytest.mark.asyncio
    async def test_ap_includes_radios(self, mock_unifi_client):
        """Test that AP details include radio information."""
        self._mock_device_lookup(mock_unifi_client, "device2")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id="device2")

        device = result["data"]
        assert "radios" in device
        assert "client_count" in device
        assert device["client_count"] == 5
        assert len(device["radios"]) == 1

        # Check radio structure
        radio = device["radios"][0]
        assert "name" in radio
        assert "channel" in radio
        assert "tx_power" in radio
        assert "num_sta" in radio

    @pytest.mark.asyncio
    async def test_uptime_formatting(self, mock_unifi_client):
        """Test uptime is formatted in human-readable format."""
        self._mock_device_lookup(mock_unifi_client, "device1")

        tool = GetDeviceDetailsTool()
        result = await tool.execute(mock_unifi_client, device_id="device1")

        device = result["data"]
        assert "uptime_readable" in device
        # 86400 seconds = 1 day
        assert "1d" in device["uptime_readable"]

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get_v1.side_effect = Exception("API connection failed")

        tool = GetDeviceDetailsTool()

        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, device_id="device1")

        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve device details" in error.message

    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        tool = GetDeviceDetailsTool()

        assert tool.name == "unifi_get_device_details"
        assert tool.category == "network_discovery"
        assert tool.requires_confirmation is False
        assert "detail" in tool.description.lower()

        # Check input schema
        assert "properties" in tool.input_schema
        assert "device_id" in tool.input_schema["properties"]
        assert "device_id" in tool.input_schema["required"]

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, mock_unifi_client):
        """Test that device search is case-insensitive."""
        self._mock_device_lookup(mock_unifi_client, "DEVICE1")

        tool = GetDeviceDetailsTool()

        # Try with uppercase ID
        result = await tool.execute(mock_unifi_client, device_id="DEVICE1")

        assert result["success"] is True
        assert result["data"]["id"] == "device1"

    @pytest.mark.asyncio
    async def test_mac_address_formats(self, mock_unifi_client):
        """Test various MAC address formats are accepted."""
        # Test with colons - MAC lookup uses fallback
        self._mock_device_lookup(mock_unifi_client, "aa:bb:cc:dd:ee:01")

        tool = GetDeviceDetailsTool()

        result1 = await tool.execute(
            mock_unifi_client,
            device_id="aa:bb:cc:dd:ee:01"
        )
        assert result1["success"] is True

        # Test without colons
        self._mock_device_lookup(mock_unifi_client, "aabbccddee01")
        result2 = await tool.execute(
            mock_unifi_client,
            device_id="aabbccddee01"
        )
        assert result2["success"] is True

        # Test uppercase
        self._mock_device_lookup(mock_unifi_client, "AA:BB:CC:DD:EE:01")
        result3 = await tool.execute(
            mock_unifi_client,
            device_id="AA:BB:CC:DD:EE:01"
        )
        assert result3["success"] is True



# Mock pending device data
MOCK_PENDING_DEVICES = [
    {
        "id": "pending-uuid-001",
        "mac": "ff:ee:dd:cc:bb:01",
        "name": "New Switch",
        "model": "USW-24-PoE",
        "type": "usw",
    },
    {
        "id": "pending-uuid-002",
        "mac": "ff:ee:dd:cc:bb:02",
        "model": "U6-Pro",
        "type": "uap",
    },
]


class TestListPendingDevicesTool:
    """Test ListPendingDevicesTool functionality."""

    @pytest.mark.asyncio
    async def test_list_pending_devices(self, mock_unifi_client):
        """Test listing pending devices."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_PENDING_DEVICES,
            "totalCount": len(MOCK_PENDING_DEVICES),
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 2
        mock_unifi_client.get_v1.assert_called_once_with("devices/pending", params=None)

    @pytest.mark.asyncio
    async def test_list_pending_devices_empty(self, mock_unifi_client):
        """Test listing pending devices when none exist."""
        mock_unifi_client.get_v1.return_value = {"data": [], "totalCount": 0}

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_pending_device_format(self, mock_unifi_client):
        """Test that pending device summary contains expected fields."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_PENDING_DEVICES,
            "totalCount": len(MOCK_PENDING_DEVICES),
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        device = result["data"][0]
        assert device["id"] == "pending-uuid-001"
        assert device["mac"] == "ff:ee:dd:cc:bb:01"
        assert device["name"] == "New Switch"
        assert device["model"] == "USW-24-PoE"
        assert device["type"] == "usw"

    @pytest.mark.asyncio
    async def test_pending_device_missing_name_uses_model(self, mock_unifi_client):
        """Test that pending device without name falls back to model."""
        mock_unifi_client.get_v1.return_value = {
            "data": MOCK_PENDING_DEVICES,
            "totalCount": len(MOCK_PENDING_DEVICES),
        }

        tool = ListPendingDevicesTool()
        result = await tool.execute(mock_unifi_client)

        # Second device has no name, should fall back to model
        device = result["data"][1]
        assert device["name"] == "U6-Pro"

    @pytest.mark.asyncio
    async def test_list_pending_devices_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get_v1.side_effect = Exception("API connection failed")

        tool = ListPendingDevicesTool()

        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)

        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "pending" in error.message.lower()

    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        tool = ListPendingDevicesTool()

        assert tool.name == "unifi_list_pending_devices"
        assert tool.category == "network_discovery"
        assert tool.requires_confirmation is False


class TestDeviceTypeMapping:
    """Test device type mapping and friendly names."""
    
    def test_switch_type_mapping(self):
        """Test switch type is mapped correctly."""
        tool = ListDevicesTool()
        
        # Test USW prefix
        friendly = tool._get_device_type_friendly("usw")
        assert friendly == "switch"
        
        friendly = tool._get_device_type_friendly("usw-24")
        assert friendly == "switch"
    
    def test_ap_type_mapping(self):
        """Test AP type is mapped correctly."""
        tool = ListDevicesTool()
        
        # Test UAP prefix
        friendly = tool._get_device_type_friendly("uap")
        assert friendly == "access_point"
        
        # Test U7P prefix (WiFi 7)
        friendly = tool._get_device_type_friendly("u7p")
        assert friendly == "access_point"
    
    def test_gateway_type_mapping(self):
        """Test gateway type is mapped correctly."""
        tool = ListDevicesTool()
        
        # Test UGW prefix
        friendly = tool._get_device_type_friendly("ugw")
        assert friendly == "gateway"
        
        # Test UDM prefix
        friendly = tool._get_device_type_friendly("udm")
        assert friendly == "dream_machine"
        
        # Test UXG prefix
        friendly = tool._get_device_type_friendly("uxg")
        assert friendly == "gateway"
    
    def test_unknown_type_passthrough(self):
        """Test unknown types are passed through."""
        tool = ListDevicesTool()
        
        friendly = tool._get_device_type_friendly("unknown-device")
        assert friendly == "unknown-device"

class TestUptimeFormatting:
    """Test uptime formatting helper."""
    
    def test_format_uptime_days(self):
        """Test uptime formatting with days."""
        tool = GetDeviceDetailsTool()
        
        # 2 days, 3 hours, 45 minutes
        uptime = (2 * 86400) + (3 * 3600) + (45 * 60)
        formatted = tool._format_uptime(uptime)
        
        assert "2d" in formatted
        assert "3h" in formatted
        assert "45m" in formatted
    
    def test_format_uptime_hours(self):
        """Test uptime formatting with hours only."""
        tool = GetDeviceDetailsTool()
        
        # 5 hours, 30 minutes
        uptime = (5 * 3600) + (30 * 60)
        formatted = tool._format_uptime(uptime)
        
        assert "5h" in formatted
        assert "30m" in formatted
        assert "d" not in formatted
    
    def test_format_uptime_minutes(self):
        """Test uptime formatting with minutes only."""
        tool = GetDeviceDetailsTool()
        
        # 45 minutes
        uptime = 45 * 60
        formatted = tool._format_uptime(uptime)
        
        assert "45m" in formatted
        assert "h" not in formatted
        assert "d" not in formatted
    
    def test_format_uptime_zero(self):
        """Test uptime formatting with zero."""
        tool = GetDeviceDetailsTool()
        
        formatted = tool._format_uptime(0)
        
        assert "0m" in formatted

class TestInputValidation:
    """Test input validation for network discovery tools."""
    
    def test_list_devices_valid_input(self):
        """Test ListDevicesTool accepts valid input."""
        tool = ListDevicesTool()
        
        # Should not raise
        tool.validate_input({
            "device_type": "switch",
            "page": 1,
            "page_size": 50
        })
    
    def test_list_devices_invalid_device_type(self):
        """Test ListDevicesTool rejects invalid device type."""
        tool = ListDevicesTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"device_type": "invalid_type"})
    
    def test_list_devices_invalid_page(self):
        """Test ListDevicesTool rejects invalid page number."""
        tool = ListDevicesTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page": 0})  # Must be >= 1
    
    def test_list_devices_invalid_page_size(self):
        """Test ListDevicesTool rejects invalid page size."""
        tool = ListDevicesTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page_size": 1000})  # Max is 500
    
    def test_get_device_details_valid_input(self):
        """Test GetDeviceDetailsTool accepts valid input."""
        tool = GetDeviceDetailsTool()
        
        # Should not raise
        tool.validate_input({"device_id": "device123"})
    
    def test_get_device_details_missing_device_id(self):
        """Test GetDeviceDetailsTool requires device_id."""
        tool = GetDeviceDetailsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({})  # Missing required device_id

# Mock client data (simulating UniFi API responses)

MOCK_CLIENTS = [
    {
        "mac": "11:22:33:44:55:01",
        "name": "Desktop PC",
        "hostname": "desktop-pc",
        "ip": "192.168.10.10",
        "is_wired": True,
        "network": "Core",
        "network_id": "net123",
        "vlan": 10,
        "uptime": 86400,
        "tx_bytes": 1073741824,  # 1 GB
        "rx_bytes": 2147483648,  # 2 GB
        "tx_packets": 1000000,
        "rx_packets": 2000000,
        "tx_rate": 1000,
        "rx_rate": 1000,
        "sw_mac": "aa:bb:cc:dd:ee:01",
        "sw_port": 5,
        "sw_name": "Main Switch",
        "wired-rx_rate-max": 1000,
        "oui": "Dell Inc.",
        "os_name": "Windows",
        "os_class": "Desktop",
        "first_seen": 1000000,
        "last_seen": 1086400,
    },
    {
        "mac": "11:22:33:44:55:02",
        "name": "iPhone",
        "hostname": "iphone",
        "ip": "192.168.10.20",
        "is_wired": False,
        "network": "Core",
        "network_id": "net123",
        "vlan": 10,
        "uptime": 43200,
        "tx_bytes": 536870912,  # 512 MB
        "rx_bytes": 1073741824,  # 1 GB
        "tx_packets": 500000,
        "rx_packets": 1000000,
        "tx_rate": 500,
        "rx_rate": 500,
        "essid": "HomeWiFi",
        "bssid": "aa:bb:cc:dd:ee:02",
        "channel": 36,
        "radio": "na",
        "radio_proto": "ax",
        "signal": -45,
        "rssi": -45,
        "noise": -95,
        "satisfaction": 95,
        "tx_retries": 100,
        "rx_retries": 50,
        "ap_mac": "aa:bb:cc:dd:ee:02",
        "ap_name": "Living Room AP",
        "oui": "Apple Inc.",
        "os_name": "iOS",
        "os_class": "Mobile",
        "first_seen": 1000000,
        "last_seen": 1043200,
    },
    {
        "mac": "11:22:33:44:55:03",
        "name": "Laptop",
        "hostname": "laptop",
        "ip": "192.168.10.30",
        "is_wired": False,
        "network": "Core",
        "network_id": "net123",
        "vlan": 10,
        "uptime": 21600,
        "tx_bytes": 268435456,  # 256 MB
        "rx_bytes": 536870912,  # 512 MB
        "tx_packets": 250000,
        "rx_packets": 500000,
        "tx_rate": 866,
        "rx_rate": 866,
        "essid": "HomeWiFi",
        "bssid": "aa:bb:cc:dd:ee:02",
        "channel": 36,
        "radio": "na",
        "radio_proto": "ac",
        "signal": -60,
        "rssi": -60,
        "noise": -95,
        "satisfaction": 85,
        "tx_retries": 200,
        "rx_retries": 100,
        "ap_mac": "aa:bb:cc:dd:ee:02",
        "ap_name": "Living Room AP",
        "oui": "Dell Inc.",
        "os_name": "Linux",
        "os_class": "Laptop",
        "first_seen": 1000000,
        "last_seen": 1021600,
    },
    {
        "mac": "11:22:33:44:55:04",
        "name": "Server",
        "hostname": "server",
        "ip": "192.168.10.40",
        "is_wired": True,
        "network": "Core",
        "network_id": "net123",
        "vlan": 10,
        "uptime": 259200,
        "tx_bytes": 10737418240,  # 10 GB
        "rx_bytes": 21474836480,  # 20 GB
        "tx_packets": 10000000,
        "rx_packets": 20000000,
        "tx_rate": 10000,
        "rx_rate": 10000,
        "sw_mac": "aa:bb:cc:dd:ee:01",
        "sw_port": 10,
        "sw_name": "Main Switch",
        "wired-rx_rate-max": 10000,
        "oui": "Supermicro",
        "os_name": "Linux",
        "os_class": "Server",
        "first_seen": 1000000,
        "last_seen": 1259200,
    },
]

class TestListClientsTool:
    """Test ListClientsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_list_all_clients(self, mock_unifi_client):
        """Test listing all clients without filtering."""
        # Setup mock response (v1 envelope format)
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        # Import the tool
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        # Create tool and execute
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert result["count"] == 4
        assert result["total"] == 4
        assert result["page"] == 1
        assert result["page_size"] == 50
        
        # Verify API call
        mock_unifi_client.get_v1.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_clients_filter_by_wired(self, mock_unifi_client):
        """Test filtering clients by wired connection."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client, connection_type="wired")
        
        # Should only return wired clients
        assert result["success"] is True
        assert result["count"] == 2
        assert all(c["connection_type"] == "wired" for c in result["data"])
    
    @pytest.mark.asyncio
    async def test_list_clients_filter_by_wireless(self, mock_unifi_client):
        """Test filtering clients by wireless connection."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client, connection_type="wireless")
        
        # Should only return wireless clients
        assert result["success"] is True
        assert result["count"] == 2
        assert all(c["connection_type"] == "wireless" for c in result["data"])
    
    @pytest.mark.asyncio
    async def test_list_clients_pagination(self, mock_unifi_client):
        """Test pagination of client list."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # Get first page (2 items per page)
        result_page1 = await tool.execute(
            mock_unifi_client,
            page=1,
            page_size=2
        )
        
        assert result_page1["success"] is True
        assert result_page1["count"] == 2
        assert result_page1["total"] == 4
        assert result_page1["page"] == 1
        assert result_page1["page_size"] == 2
        
        # Get second page
        result_page2 = await tool.execute(
            mock_unifi_client,
            page=2,
            page_size=2
        )
        
        assert result_page2["count"] == 2
        assert result_page2["page"] == 2
        
        # Verify different clients on each page
        page1_macs = [c["mac"] for c in result_page1["data"]]
        page2_macs = [c["mac"] for c in result_page2["data"]]
        assert page1_macs != page2_macs
    
    @pytest.mark.asyncio
    async def test_list_clients_empty_result(self, mock_unifi_client):
        """Test listing clients when none exist."""
        mock_unifi_client.get_v1.return_value = {"data": [], "totalCount": 0, "offset": 0, "limit": 25, "count": 0}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client)
        
        assert result["success"] is True
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["data"] == []
    
    @pytest.mark.asyncio
    async def test_list_clients_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get_v1.side_effect = Exception("API connection failed")
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)
        
        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve client list" in error.message
    
    @pytest.mark.asyncio
    async def test_client_summary_format(self, mock_unifi_client):
        """Test that client summary contains expected fields."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check first client has expected summary fields
        client = result["data"][0]
        expected_fields = [
            "mac", "name", "ip", "connection_type", "network",
            "uptime", "uptime_readable", "tx_bytes", "rx_bytes",
            "tx_bytes_readable", "rx_bytes_readable"
        ]
        
        for field in expected_fields:
            assert field in client, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_wireless_client_has_signal_info(self, mock_unifi_client):
        """Test that wireless clients include signal information."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client, connection_type="wireless")
        
        # Check wireless client has signal fields
        client = result["data"][0]
        assert "signal_strength" in client
        assert "rssi" in client
        assert "essid" in client
        assert "channel" in client
    
    @pytest.mark.asyncio
    async def test_wired_client_no_signal_info(self, mock_unifi_client):
        """Test that wired clients don't include signal information."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        result = await tool.execute(mock_unifi_client, connection_type="wired")
        
        # Check wired client doesn't have signal fields
        client = result["data"][0]
        assert "signal_strength" not in client
        assert "rssi" not in client
        assert "essid" not in client
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        assert tool.name == "unifi_list_clients"
        assert tool.category == "network_discovery"
        assert tool.requires_confirmation is False
        assert "client" in tool.description.lower()
        
        # Check input schema
        assert "properties" in tool.input_schema
        assert "connection_type" in tool.input_schema["properties"]
        assert "page" in tool.input_schema["properties"]
        assert "page_size" in tool.input_schema["properties"]

class TestGetClientDetailsTool:
    """Test GetClientDetailsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_get_client_by_mac(self, mock_unifi_client):
        """Test getting client details by MAC address."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01"
        )
        
        assert result["success"] is True
        assert result["type"] == "client"
        assert "data" in result
        
        client = result["data"]
        assert client["mac"] == "11:22:33:44:55:01"
        assert client["name"] == "Desktop PC"
        assert client["connection_type"] == "wired"
    
    @pytest.mark.asyncio
    async def test_get_client_by_mac_without_colons(self, mock_unifi_client):
        """Test getting client by MAC address without colons."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="112233445502"
        )
        
        assert result["success"] is True
        client = result["data"]
        assert client["mac"] == "11:22:33:44:55:02"
    
    @pytest.mark.asyncio
    async def test_get_client_not_found(self, mock_unifi_client):
        """Test getting client that doesn't exist."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, mac_address="99:99:99:99:99:99")
        
        error = exc_info.value
        assert error.code == "CLIENT_NOT_FOUND"
        assert "99:99:99:99:99:99" in error.details
    
    @pytest.mark.asyncio
    async def test_client_detail_format(self, mock_unifi_client):
        """Test that client details contain expected fields."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01"
        )
        
        client = result["data"]
        
        # Check basic fields
        expected_fields = [
            "mac", "name", "ip", "connection_type", "network", "network_id",
            "vlan", "oui", "manufacturer", "os_name", "os_class",
            "first_seen", "last_seen", "uptime", "uptime_readable",
            "tx_bytes", "rx_bytes", "tx_bytes_readable", "rx_bytes_readable",
            "tx_packets", "rx_packets", "tx_rate", "rx_rate"
        ]
        
        for field in expected_fields:
            assert field in client, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_wireless_client_includes_wireless_fields(self, mock_unifi_client):
        """Test that wireless client details include wireless-specific fields."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:02"
        )
        
        client = result["data"]
        
        # Check wireless-specific fields
        wireless_fields = [
            "essid", "bssid", "channel", "radio", "radio_proto",
            "signal", "rssi", "noise", "satisfaction", "tx_retries", "rx_retries"
        ]
        
        for field in wireless_fields:
            assert field in client, f"Missing wireless field: {field}"
    
    @pytest.mark.asyncio
    async def test_wired_client_includes_wired_fields(self, mock_unifi_client):
        """Test that wired client details include wired-specific fields."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01"
        )
        
        client = result["data"]
        
        # Check wired-specific fields
        wired_fields = ["switch_mac", "switch_port", "wired_rate_mbps"]
        
        for field in wired_fields:
            assert field in client, f"Missing wired field: {field}"
    
    @pytest.mark.asyncio
    async def test_client_includes_connected_device_info(self, mock_unifi_client):
        """Test that client details include connected device information."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        # Test wireless client (connected to AP)
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:02"
        )
        
        client = result["data"]
        assert "connected_device_mac" in client
        assert "connected_device_name" in client
        assert client["connected_device_mac"] == "aa:bb:cc:dd:ee:02"
        assert client["connected_device_name"] == "Living Room AP"
    
    @pytest.mark.asyncio
    async def test_uptime_formatting(self, mock_unifi_client):
        """Test uptime is formatted in human-readable format."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01"
        )
        
        client = result["data"]
        assert "uptime_readable" in client
        # 86400 seconds = 1 day
        assert "1d" in client["uptime_readable"]
    
    @pytest.mark.asyncio
    async def test_bytes_formatting(self, mock_unifi_client):
        """Test bytes are formatted in human-readable format."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01"
        )
        
        client = result["data"]
        assert "tx_bytes_readable" in client
        assert "rx_bytes_readable" in client
        # 1 GB transmitted
        assert "GB" in client["tx_bytes_readable"]
        # 2 GB received
        assert "GB" in client["rx_bytes_readable"]
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get_v1.side_effect = Exception("API connection failed")
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                mock_unifi_client,
                mac_address="11:22:33:44:55:01"
            )
        
        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve client details" in error.message
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        assert tool.name == "unifi_get_client_details"
        assert tool.category == "network_discovery"
        assert tool.requires_confirmation is False
        assert "client" in tool.description.lower() and "detail" in tool.description.lower()
        
        # Check input schema
        assert "properties" in tool.input_schema
        assert "mac_address" in tool.input_schema["properties"]
        assert "mac_address" in tool.input_schema["required"]
    
    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, mock_unifi_client):
        """Test that client search is case-insensitive."""
        mock_unifi_client.get_v1.return_value = {"data": MOCK_CLIENTS, "totalCount": len(MOCK_CLIENTS), "offset": 0, "limit": 25, "count": len(MOCK_CLIENTS)}
        
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        # Try with uppercase MAC
        result = await tool.execute(
            mock_unifi_client,
            mac_address="11:22:33:44:55:01".upper()
        )
        
        assert result["success"] is True
        assert result["data"]["mac"] == "11:22:33:44:55:01"

class TestBytesFormatting:
    """Test bytes formatting helper."""
    
    def test_format_bytes_b(self):
        """Test bytes formatting for bytes."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        formatted = tool._format_bytes(512)
        assert "512 B" in formatted
    
    def test_format_bytes_kb(self):
        """Test bytes formatting for kilobytes."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # 5 KB
        formatted = tool._format_bytes(5 * 1024)
        assert "5.00 KB" in formatted
    
    def test_format_bytes_mb(self):
        """Test bytes formatting for megabytes."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # 256 MB
        formatted = tool._format_bytes(256 * 1024 * 1024)
        assert "256.00 MB" in formatted
    
    def test_format_bytes_gb(self):
        """Test bytes formatting for gigabytes."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # 1.5 GB
        formatted = tool._format_bytes(int(1.5 * 1024 * 1024 * 1024))
        assert "1.50 GB" in formatted
    
    def test_format_bytes_tb(self):
        """Test bytes formatting for terabytes."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # 2 TB
        formatted = tool._format_bytes(2 * 1024 * 1024 * 1024 * 1024)
        assert "2.00 TB" in formatted
    
    def test_format_bytes_zero(self):
        """Test bytes formatting with zero."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        formatted = tool._format_bytes(0)
        assert "0 B" in formatted

class TestClientInputValidation:
    """Test input validation for client tools."""
    
    def test_list_clients_valid_input(self):
        """Test ListClientsTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        # Should not raise
        tool.validate_input({
            "connection_type": "wired",
            "page": 1,
            "page_size": 50
        })
    
    def test_list_clients_invalid_connection_type(self):
        """Test ListClientsTool rejects invalid connection type."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"connection_type": "invalid_type"})
    
    def test_list_clients_invalid_page(self):
        """Test ListClientsTool rejects invalid page number."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page": 0})  # Must be >= 1
    
    def test_list_clients_invalid_page_size(self):
        """Test ListClientsTool rejects invalid page size."""
        from unifi_mcp.tools.network_discovery import ListClientsTool
        
        tool = ListClientsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page_size": 1000})  # Max is 500
    
    def test_get_client_details_valid_input(self):
        """Test GetClientDetailsTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        # Should not raise
        tool.validate_input({"mac_address": "11:22:33:44:55:66"})
    
    def test_get_client_details_missing_mac_address(self):
        """Test GetClientDetailsTool requires mac_address."""
        from unifi_mcp.tools.network_discovery import GetClientDetailsTool
        
        tool = GetClientDetailsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({})  # Missing required mac_address

# Mock network data (simulating UniFi API responses)

MOCK_NETWORKS = [
    {
        "_id": "network1",
        "name": "Default",
        "purpose": "corporate",
        "vlan": "",
        "vlan_enabled": False,
        "ip_subnet": "192.168.1.0/24",
        "networkgroup": "LAN",
        "dhcpd_enabled": True,
        "dhcpd_start": "192.168.1.100",
        "dhcpd_stop": "192.168.1.200",
        "domain_name": "local",
        "enabled": True,
        "gateway_ip": "192.168.1.1",
        "gateway_type": "default",
        "dhcpd_leasetime": 86400,
        "dhcpd_dns": ["8.8.8.8", "1.1.1.1"],
        "dhcpd_gateway": "192.168.1.1",
        "is_nat": False,
        "is_guest": False,
        "igmp_snooping": False,
        "dhcp_relay_enabled": False,
    },
    {
        "_id": "network2",
        "name": "IoT",
        "purpose": "vlan-only",
        "vlan": "20",
        "vlan_enabled": True,
        "ip_subnet": "192.168.20.0/24",
        "networkgroup": "LAN",
        "dhcpd_enabled": True,
        "dhcpd_start": "192.168.20.100",
        "dhcpd_stop": "192.168.20.200",
        "domain_name": "iot.local",
        "enabled": True,
        "gateway_ip": "192.168.20.1",
        "gateway_type": "default",
        "dhcpd_leasetime": 86400,
        "dhcpd_dns": ["192.168.1.1"],
        "dhcpd_gateway": "192.168.20.1",
        "is_nat": False,
        "is_guest": False,
        "igmp_snooping": True,
        "dhcp_relay_enabled": False,
    },
    {
        "_id": "network3",
        "name": "Guest",
        "purpose": "guest",
        "vlan": "30",
        "vlan_enabled": True,
        "ip_subnet": "192.168.30.0/24",
        "networkgroup": "LAN",
        "dhcpd_enabled": True,
        "dhcpd_start": "192.168.30.100",
        "dhcpd_stop": "192.168.30.200",
        "domain_name": "guest.local",
        "enabled": True,
        "gateway_ip": "192.168.30.1",
        "gateway_type": "default",
        "dhcpd_leasetime": 3600,
        "dhcpd_dns": ["8.8.8.8"],
        "dhcpd_gateway": "192.168.30.1",
        "is_nat": True,
        "is_guest": True,
        "igmp_snooping": False,
        "dhcp_relay_enabled": False,
    },
]

# Mock WLAN data (simulating UniFi API responses)

MOCK_WLANS = [
    {
        "_id": "wlan1",
        "name": "HomeWiFi",
        "x_passphrase": "HomeWiFi",
        "enabled": True,
        "security": "wpapsk",
        "wpa_mode": "wpa2",
        "wpa_enc": "ccmp",
        "networkconf_id": "network1",
        "vlan": "",
        "vlan_enabled": False,
        "is_guest": False,
        "hide_ssid": False,
        "mac_filter_enabled": False,
        "mac_filter_policy": "",
        "minrate_ng_enabled": False,
        "minrate_ng_data_rate_kbps": 0,
        "minrate_na_enabled": False,
        "minrate_na_data_rate_kbps": 0,
        "dtim_mode": "default",
        "dtim_ng": 1,
        "dtim_na": 1,
        "schedule_enabled": False,
        "schedule": [],
        "band_steering_mode": "prefer_5g",
        "fast_roaming_enabled": True,
        "radius_enabled": False,
        "radius_nas_id": "",
        "group_rekey": 3600,
        "wpa3_support": False,
        "wpa3_transition": False,
        "portal_enabled": False,
        "portal_customized": False,
    },
    {
        "_id": "wlan2",
        "name": "IoT-WiFi",
        "x_passphrase": "IoT-WiFi",
        "enabled": True,
        "security": "wpapsk",
        "wpa_mode": "wpa2",
        "wpa_enc": "ccmp",
        "networkconf_id": "network2",
        "vlan": "20",
        "vlan_enabled": True,
        "is_guest": False,
        "hide_ssid": False,
        "mac_filter_enabled": False,
        "mac_filter_policy": "",
        "minrate_ng_enabled": True,
        "minrate_ng_data_rate_kbps": 6000,
        "minrate_na_enabled": False,
        "minrate_na_data_rate_kbps": 0,
        "dtim_mode": "default",
        "dtim_ng": 3,
        "dtim_na": 3,
        "schedule_enabled": False,
        "schedule": [],
        "band_steering_mode": "off",
        "fast_roaming_enabled": False,
        "radius_enabled": False,
        "radius_nas_id": "",
        "group_rekey": 3600,
        "wpa3_support": False,
        "wpa3_transition": False,
        "portal_enabled": False,
        "portal_customized": False,
    },
    {
        "_id": "wlan3",
        "name": "Guest-WiFi",
        "x_passphrase": "Guest-WiFi",
        "enabled": True,
        "security": "open",
        "wpa_mode": "",
        "wpa_enc": "",
        "networkconf_id": "network3",
        "vlan": "30",
        "vlan_enabled": True,
        "is_guest": True,
        "hide_ssid": False,
        "mac_filter_enabled": False,
        "mac_filter_policy": "",
        "minrate_ng_enabled": False,
        "minrate_ng_data_rate_kbps": 0,
        "minrate_na_enabled": False,
        "minrate_na_data_rate_kbps": 0,
        "dtim_mode": "default",
        "dtim_ng": 1,
        "dtim_na": 1,
        "schedule_enabled": False,
        "schedule": [],
        "band_steering_mode": "off",
        "fast_roaming_enabled": False,
        "radius_enabled": False,
        "radius_nas_id": "",
        "group_rekey": 0,
        "wpa3_support": False,
        "wpa3_transition": False,
        "portal_enabled": True,
        "portal_customized": True,
    },
]

class TestListNetworksTool:
    """Test ListNetworksTool functionality."""
    
    @pytest.mark.asyncio
    async def test_list_networks_success(self, mock_unifi_client):
        """Test successful network listing."""
        from unifi_mcp.tools.network_discovery import ListNetworksTool
        
        # Mock API response (v1 envelope format)
        mock_unifi_client.get_v1.return_value = {"data": MOCK_NETWORKS, "totalCount": len(MOCK_NETWORKS), "offset": 0, "limit": 25, "count": len(MOCK_NETWORKS)}
        
        tool = ListNetworksTool()
        result = await tool.execute(mock_unifi_client)
        
        # Verify API call
        mock_unifi_client.get_v1.assert_called_once()
        
        # Verify result structure
        assert "data" in result
        assert "total" in result
        assert result["total"] == 3
        assert len(result["data"]) == 3
        
        # Verify first network
        network = result["data"][0]
        assert network["id"] == "network1"
        assert network["name"] == "Default"
        assert network["vlan_enabled"] is False
        assert network["dhcp_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_list_networks_empty(self, mock_unifi_client):
        """Test listing networks when none exist."""
        from unifi_mcp.tools.network_discovery import ListNetworksTool
        
        # Mock empty response (v1 envelope format)
        mock_unifi_client.get_v1.return_value = {"data": [], "totalCount": 0, "offset": 0, "limit": 25, "count": 0}
        
        tool = ListNetworksTool()
        result = await tool.execute(mock_unifi_client)
        
        assert result["total"] == 0
        assert len(result["data"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_networks_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        from unifi_mcp.tools.network_discovery import ListNetworksTool
        
        # Mock API error
        mock_unifi_client.get_v1.side_effect = Exception("Connection failed")
        
        tool = ListNetworksTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)
        
        assert exc_info.value.code == "API_ERROR"
        assert "Failed to retrieve network list" in exc_info.value.message

class TestGetNetworkDetailsTool:
    """Test GetNetworkDetailsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_get_network_details_by_id(self, mock_unifi_client):
        """Test getting network details by ID."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        # Mock direct v1 lookup response (returns single network in data list)
        target_network = MOCK_NETWORKS[1]  # IoT network (network2)
        mock_unifi_client.get_v1.return_value = {"data": [target_network], "totalCount": 1, "offset": 0, "limit": 25, "count": 1}
        
        tool = GetNetworkDetailsTool()
        result = await tool.execute(mock_unifi_client, network_id="network2")
        
        # Verify result
        assert "data" in result
        network = result["data"]
        assert network["id"] == "network2"
        assert network["name"] == "IoT"
        assert network["vlan"] == "20"
        assert network["vlan_enabled"] is True
        assert network["dhcp_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_get_network_details_by_name(self, mock_unifi_client):
        """Test getting network details by name."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        # Direct v1 lookup by name will fail, fallback fetches all networks
        mock_unifi_client.get_v1.side_effect = [
            Exception("Not found"),  # Direct lookup fails
            {"data": MOCK_NETWORKS, "totalCount": len(MOCK_NETWORKS), "offset": 0, "limit": 25, "count": len(MOCK_NETWORKS)}  # Fallback succeeds
        ]
        
        tool = GetNetworkDetailsTool()
        result = await tool.execute(mock_unifi_client, network_id="guest")
        
        # Verify result (case-insensitive match)
        network = result["data"]
        assert network["name"] == "Guest"
        assert network["is_guest"] is True
    
    @pytest.mark.asyncio
    async def test_get_network_details_not_found(self, mock_unifi_client):
        """Test getting details for non-existent network."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        # Direct v1 lookup fails, fallback returns all networks but none match
        mock_unifi_client.get_v1.side_effect = [
            Exception("Not found"),  # Direct lookup fails
            {"data": MOCK_NETWORKS, "totalCount": len(MOCK_NETWORKS), "offset": 0, "limit": 25, "count": len(MOCK_NETWORKS)}  # Fallback succeeds but no match
        ]
        
        tool = GetNetworkDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, network_id="nonexistent")
        
        assert exc_info.value.code == "NETWORK_NOT_FOUND"
        assert "Network not found" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_get_network_details_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        # Mock API error (both direct lookup and fallback fail)
        mock_unifi_client.get_v1.side_effect = Exception("Connection failed")
        
        tool = GetNetworkDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, network_id="network1")
        
        assert exc_info.value.code == "API_ERROR"

class TestListWLANsTool:
    """Test ListWLANsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_list_wlans_success(self, mock_unifi_client):
        """Test successful WLAN listing."""
        from unifi_mcp.tools.network_discovery import ListWLANsTool
        
        # Mock API response (v1 envelope format)
        mock_unifi_client.get_v1.return_value = {"data": MOCK_WLANS, "totalCount": len(MOCK_WLANS), "offset": 0, "limit": 25, "count": len(MOCK_WLANS)}
        
        tool = ListWLANsTool()
        result = await tool.execute(mock_unifi_client)
        
        # Verify API call
        mock_unifi_client.get_v1.assert_called_once()
        
        # Verify result structure
        assert "data" in result
        assert "total" in result
        assert result["total"] == 3
        assert len(result["data"]) == 3
        
        # Verify first WLAN
        wlan = result["data"][0]
        assert wlan["id"] == "wlan1"
        assert wlan["name"] == "HomeWiFi"
        assert wlan["security"] == "wpapsk"
        assert wlan["is_guest"] is False
    
    @pytest.mark.asyncio
    async def test_list_wlans_empty(self, mock_unifi_client):
        """Test listing WLANs when none exist."""
        from unifi_mcp.tools.network_discovery import ListWLANsTool
        
        # Mock empty response (v1 envelope format)
        mock_unifi_client.get_v1.return_value = {"data": [], "totalCount": 0, "offset": 0, "limit": 25, "count": 0}
        
        tool = ListWLANsTool()
        result = await tool.execute(mock_unifi_client)
        
        assert result["total"] == 0
        assert len(result["data"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_wlans_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        from unifi_mcp.tools.network_discovery import ListWLANsTool
        
        # Mock API error
        mock_unifi_client.get_v1.side_effect = Exception("Connection failed")
        
        tool = ListWLANsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)
        
        assert exc_info.value.code == "API_ERROR"
        assert "Failed to retrieve WiFi broadcast list" in exc_info.value.message

class TestGetWLANDetailsTool:
    """Test GetWLANDetailsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_get_wlan_details_by_id(self, mock_unifi_client):
        """Test getting WLAN details by ID."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        # Mock direct v1 lookup response (returns single WLAN in data list)
        target_wlan = MOCK_WLANS[1]  # IoT-WiFi (wlan2)
        mock_unifi_client.get_v1.return_value = {"data": [target_wlan], "totalCount": 1, "offset": 0, "limit": 25, "count": 1}
        
        tool = GetWLANDetailsTool()
        result = await tool.execute(mock_unifi_client, wlan_id="wlan2")
        
        # Verify result
        assert "data" in result
        wlan = result["data"]
        assert wlan["id"] == "wlan2"
        assert wlan["name"] == "IoT-WiFi"
        assert wlan["vlan"] == "20"
        assert wlan["vlan_enabled"] is True
        assert wlan["security"] == "wpapsk"
    
    @pytest.mark.asyncio
    async def test_get_wlan_details_by_name(self, mock_unifi_client):
        """Test getting WLAN details by name."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        # Direct v1 lookup by name will fail, fallback fetches all WLANs
        mock_unifi_client.get_v1.side_effect = [
            Exception("Not found"),  # Direct lookup fails
            {"data": MOCK_WLANS, "totalCount": len(MOCK_WLANS), "offset": 0, "limit": 25, "count": len(MOCK_WLANS)}  # Fallback succeeds
        ]
        
        tool = GetWLANDetailsTool()
        result = await tool.execute(mock_unifi_client, wlan_id="guest-wifi")
        
        # Verify result (case-insensitive match)
        wlan = result["data"]
        assert wlan["name"] == "Guest-WiFi"
        assert wlan["is_guest"] is True
        assert wlan["security"] == "open"
    
    @pytest.mark.asyncio
    async def test_get_wlan_details_not_found(self, mock_unifi_client):
        """Test getting details for non-existent WLAN."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        # Direct v1 lookup fails, fallback returns all WLANs but none match
        mock_unifi_client.get_v1.side_effect = [
            Exception("Not found"),  # Direct lookup fails
            {"data": MOCK_WLANS, "totalCount": len(MOCK_WLANS), "offset": 0, "limit": 25, "count": len(MOCK_WLANS)}  # Fallback succeeds but no match
        ]
        
        tool = GetWLANDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, wlan_id="nonexistent")
        
        assert exc_info.value.code == "WLAN_NOT_FOUND"
        assert "WiFi broadcast not found" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_get_wlan_details_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        # Mock API error (both direct lookup and fallback fail)
        mock_unifi_client.get_v1.side_effect = Exception("Connection failed")
        
        tool = GetWLANDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, wlan_id="wlan1")
        
        assert exc_info.value.code == "API_ERROR"

class TestNetworkInputValidation:
    """Test input validation for network tools."""
    
    def test_list_networks_valid_input(self):
        """Test ListNetworksTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import ListNetworksTool
        
        tool = ListNetworksTool()
        
        # Should not raise (empty input is valid)
        tool.validate_input({})
    
    def test_get_network_details_valid_input(self):
        """Test GetNetworkDetailsTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        tool = GetNetworkDetailsTool()
        
        # Should not raise
        tool.validate_input({"network_id": "network1"})
    
    def test_get_network_details_missing_network_id(self):
        """Test GetNetworkDetailsTool requires network_id."""
        from unifi_mcp.tools.network_discovery import GetNetworkDetailsTool
        
        tool = GetNetworkDetailsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({})  # Missing required network_id

class TestWLANInputValidation:
    """Test input validation for WLAN tools."""
    
    def test_list_wlans_valid_input(self):
        """Test ListWLANsTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import ListWLANsTool
        
        tool = ListWLANsTool()
        
        # Should not raise (empty input is valid)
        tool.validate_input({})
    
    def test_get_wlan_details_valid_input(self):
        """Test GetWLANDetailsTool accepts valid input."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        tool = GetWLANDetailsTool()
        
        # Should not raise
        tool.validate_input({"wlan_id": "wlan1"})
    
    def test_get_wlan_details_missing_wlan_id(self):
        """Test GetWLANDetailsTool requires wlan_id."""
        from unifi_mcp.tools.network_discovery import GetWLANDetailsTool
        
        tool = GetWLANDetailsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({})  # Missing required wlan_id
