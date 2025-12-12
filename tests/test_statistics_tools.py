"""Unit tests for statistics tools.

This module tests the statistics tools:
- GetNetworkStatsTool: Overall network statistics
- GetSystemHealthTool: System health metrics
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.statistics import GetNetworkStatsTool, GetSystemHealthTool
from unifi_mcp.tools.base import ToolError


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = AsyncMock()
    return client


@pytest.fixture
def network_stats_tool():
    """Create a GetNetworkStatsTool instance."""
    return GetNetworkStatsTool()


@pytest.fixture
def system_health_tool():
    """Create a GetSystemHealthTool instance."""
    return GetSystemHealthTool()


# Mock data for testing
MOCK_HEALTH_DATA = {
    "data": [
        {
            "subsystem": "wan",
            "status": "ok",
            "uptime": 86400,
            "tx_bytes-r": 1000000,
            "rx_bytes-r": 2000000,
        },
        {
            "subsystem": "lan",
            "status": "ok",
            "uptime": 86400,
            "tx_bytes-r": 500000,
            "rx_bytes-r": 1500000,
        },
    ]
}

MOCK_DEVICE_DATA = {
    "data": [
        {
            "_id": "device1",
            "name": "Switch 1",
            "type": "usw",
            "model": "US-24-250W",
            "state": 1,
            "uptime": 86400,
            "system-stats": {
                "cpu": 15,
                "mem": 30,
                "temps": {"Board (CPU)": 45},
            },
        },
        {
            "_id": "device2",
            "name": "AP 1",
            "type": "uap",
            "model": "U6-Pro",
            "state": 1,
            "uptime": 43200,
            "system-stats": {
                "cpu": 10,
                "mem": 25,
                "temps": {"Board (CPU)": 40},
            },
        },
        {
            "_id": "device3",
            "name": "Offline Device",
            "type": "usw",
            "model": "US-8-60W",
            "state": 0,
            "uptime": 0,
        },
    ]
}

MOCK_CLIENT_DATA = {
    "data": [
        {
            "mac": "aa:bb:cc:dd:ee:01",
            "name": "Desktop",
            "is_wired": True,
        },
        {
            "mac": "aa:bb:cc:dd:ee:02",
            "name": "Laptop",
            "is_wired": False,
        },
        {
            "mac": "aa:bb:cc:dd:ee:03",
            "name": "Phone",
            "is_wired": False,
        },
    ]
}

MOCK_SYSINFO_DATA = {
    "data": [
        {
            "version": "7.5.176",
            "hostname": "unifi-controller",
            "uptime": 172800,
        }
    ]
}

MOCK_ALARM_DATA = {
    "data": [
        {
            "key": "EVT_GW_WANTransition",
            "msg": "WAN connection restored",
            "datetime": "2025-10-09T10:00:00Z",
            "archived": False,
        },
        {
            "key": "EVT_AP_Disconnected",
            "msg": "AP disconnected",
            "datetime": "2025-10-09T09:00:00Z",
            "archived": True,
        },
    ]
}


class TestGetNetworkStatsTool:
    """Tests for GetNetworkStatsTool."""
    
    def test_tool_metadata(self, network_stats_tool):
        """Test tool has correct metadata."""
        assert network_stats_tool.name == "unifi_get_network_stats"
        assert network_stats_tool.description == "Get overall network statistics and health"
        assert network_stats_tool.category == "statistics"
        assert network_stats_tool.input_schema["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_get_network_stats_success(self, network_stats_tool, mock_unifi_client):
        """Test successful network stats retrieval."""
        # Mock API responses
        mock_unifi_client.get.side_effect = [
            MOCK_HEALTH_DATA,  # Site stats
            MOCK_DEVICE_DATA,  # Device stats
            MOCK_CLIENT_DATA,  # Client stats
        ]
        
        # Execute tool
        result = await network_stats_tool.execute(mock_unifi_client)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert "message" in result
        
        # Verify data structure
        data = result["data"]
        assert "summary" in data
        assert "bandwidth" in data
        assert "health" in data
        assert "uptime" in data
        
        # Verify summary data
        summary = data["summary"]
        assert summary["total_clients"] == 3
        assert summary["wired_clients"] == 1
        assert summary["wireless_clients"] == 2
        assert summary["total_devices"] == 3
        assert summary["online_devices"] == 2
        assert summary["offline_devices"] == 1
        
        # Verify bandwidth data
        bandwidth = data["bandwidth"]
        assert bandwidth["total_tx_bytes"] == 1500000
        assert bandwidth["total_rx_bytes"] == 3500000
        assert "total_tx_bytes_formatted" in bandwidth
        assert "total_rx_bytes_formatted" in bandwidth
        
        # Verify health data
        health = data["health"]
        assert health["wan_status"] == "ok"
        assert health["lan_status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_get_network_stats_api_error(self, network_stats_tool, mock_unifi_client):
        """Test network stats retrieval with API error.
        
        The tool gracefully handles API errors by returning empty data
        rather than failing completely. This allows partial data to be
        returned even if some API calls fail.
        """
        # Mock API error
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        # Execute tool - should return empty data, not raise error
        result = await network_stats_tool.execute(mock_unifi_client)
        
        # Verify result structure (should succeed with empty data)
        assert result["success"] is True
        assert "data" in result
        
        # Verify data is empty/default values
        data = result["data"]
        assert data["summary"]["total_clients"] == 0
        assert data["summary"]["total_devices"] == 0
        assert data["bandwidth"]["total_tx_bytes"] == 0
        assert data["health"]["wan_status"] == "unknown"
    
    def test_format_bytes(self, network_stats_tool):
        """Test byte formatting."""
        assert network_stats_tool._format_bytes(500) == "500 B"
        assert network_stats_tool._format_bytes(1024) == "1.00 KB"
        assert network_stats_tool._format_bytes(1024 ** 2) == "1.00 MB"
        assert network_stats_tool._format_bytes(1024 ** 3) == "1.00 GB"
        assert network_stats_tool._format_bytes(1024 ** 4) == "1.00 TB"
    
    def test_format_uptime(self, network_stats_tool):
        """Test uptime formatting."""
        assert network_stats_tool._format_uptime(30) == "30 seconds"
        assert network_stats_tool._format_uptime(120) == "2 minutes"
        assert network_stats_tool._format_uptime(3600) == "1 hours, 0 minutes"
        assert network_stats_tool._format_uptime(86400) == "1 days, 0 hours"
        assert network_stats_tool._format_uptime(90000) == "1 days, 1 hours"


class TestGetSystemHealthTool:
    """Tests for GetSystemHealthTool."""
    
    def test_tool_metadata(self, system_health_tool):
        """Test tool has correct metadata."""
        assert system_health_tool.name == "unifi_get_system_health"
        assert system_health_tool.description == "Get overall system health metrics"
        assert system_health_tool.category == "statistics"
        assert system_health_tool.input_schema["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_get_system_health_success(self, system_health_tool, mock_unifi_client):
        """Test successful system health retrieval."""
        # Mock API responses
        mock_unifi_client.get.side_effect = [
            MOCK_HEALTH_DATA,    # Subsystem health
            MOCK_DEVICE_DATA,    # Device health
            MOCK_SYSINFO_DATA,   # Controller info
            MOCK_ALARM_DATA,     # Recent alerts
        ]
        
        # Execute tool
        result = await system_health_tool.execute(mock_unifi_client)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert "message" in result
        
        # Verify data structure
        data = result["data"]
        assert "controller" in data
        assert "subsystems" in data
        assert "devices" in data
        assert "alerts" in data
        assert "overall_status" in data
        
        # Verify controller data
        controller = data["controller"]
        assert controller["version"] == "7.5.176"
        assert controller["hostname"] == "unifi-controller"
        assert controller["uptime"] == 172800
        assert "uptime_formatted" in controller
        
        # Verify subsystems data
        subsystems = data["subsystems"]
        assert len(subsystems) == 2
        assert subsystems[0]["name"] == "wan"
        assert subsystems[0]["status"] == "ok"
        assert subsystems[1]["name"] == "lan"
        assert subsystems[1]["status"] == "ok"
        
        # Verify devices data
        devices = data["devices"]
        assert len(devices) == 3
        assert devices[0]["name"] == "Switch 1"
        assert devices[0]["state"] == "online"
        assert devices[0]["cpu_usage"] == 15
        assert devices[0]["memory_usage"] == 30
        assert devices[0]["temperature"] == 45
        assert devices[2]["state"] == "offline"
        
        # Verify alerts data
        alerts = data["alerts"]
        assert alerts["total"] == 2
        assert len(alerts["recent"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_system_health_api_error(self, system_health_tool, mock_unifi_client):
        """Test system health retrieval with API error.
        
        The tool gracefully handles API errors by returning empty data
        rather than failing completely. This allows partial data to be
        returned even if some API calls fail.
        """
        # Mock API error
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        # Execute tool - should return empty data, not raise error
        result = await system_health_tool.execute(mock_unifi_client)
        
        # Verify result structure (should succeed with empty data)
        assert result["success"] is True
        assert "data" in result
        
        # Verify data is empty/default values
        data = result["data"]
        assert data["controller"]["version"] == "unknown"
        assert len(data["subsystems"]) == 0
        assert len(data["devices"]) == 0
        assert data["overall_status"] == "healthy"  # No data = healthy
    
    def test_calculate_overall_status_healthy(self, system_health_tool):
        """Test overall status calculation - healthy."""
        subsystems = [
            {"status": "ok"},
            {"status": "ok"},
        ]
        devices = [
            {"state": "online"},
            {"state": "online"},
        ]
        alerts = []
        
        status = system_health_tool._calculate_overall_status(subsystems, devices, alerts)
        assert status == "healthy"
    
    def test_calculate_overall_status_warning(self, system_health_tool):
        """Test overall status calculation - warning."""
        subsystems = [
            {"status": "ok"},
            {"status": "ok"},
        ]
        devices = [
            {"state": "online"},
            {"state": "offline"},
        ]
        alerts = []
        
        status = system_health_tool._calculate_overall_status(subsystems, devices, alerts)
        assert status == "warning"
    
    def test_calculate_overall_status_critical(self, system_health_tool):
        """Test overall status calculation - critical."""
        subsystems = [
            {"status": "error"},
            {"status": "ok"},
        ]
        devices = [
            {"state": "online"},
            {"state": "online"},
        ]
        alerts = []
        
        status = system_health_tool._calculate_overall_status(subsystems, devices, alerts)
        assert status == "critical"
    
    def test_format_uptime(self, system_health_tool):
        """Test uptime formatting."""
        assert system_health_tool._format_uptime(30) == "30 seconds"
        assert system_health_tool._format_uptime(120) == "2 minutes"
        assert system_health_tool._format_uptime(3600) == "1 hours, 0 minutes"
        assert system_health_tool._format_uptime(86400) == "1 days, 0 hours"
        assert system_health_tool._format_uptime(172800) == "2 days, 0 hours"


class TestStatisticsToolsIntegration:
    """Integration tests for statistics tools."""
    
    @pytest.mark.asyncio
    async def test_network_stats_with_empty_data(self, network_stats_tool, mock_unifi_client):
        """Test network stats with empty data."""
        # Mock empty responses
        mock_unifi_client.get.side_effect = [
            {"data": []},  # Site stats
            {"data": []},  # Device stats
            {"data": []},  # Client stats
        ]
        
        # Execute tool
        result = await network_stats_tool.execute(mock_unifi_client)
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        assert data["summary"]["total_clients"] == 0
        assert data["summary"]["total_devices"] == 0
    
    @pytest.mark.asyncio
    async def test_system_health_with_empty_data(self, system_health_tool, mock_unifi_client):
        """Test system health with empty data."""
        # Mock empty responses
        mock_unifi_client.get.side_effect = [
            {"data": []},  # Subsystem health
            {"data": []},  # Device health
            {"data": []},  # Controller info
            {"data": []},  # Recent alerts
        ]
        
        # Execute tool
        result = await system_health_tool.execute(mock_unifi_client)
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        assert data["overall_status"] == "healthy"
        assert len(data["subsystems"]) == 0
        assert len(data["devices"]) == 0



# Mock data for client and device statistics tests
MOCK_CLIENT_STATS_DATA = {
    "data": [
        {
            "mac": "aa:bb:cc:dd:ee:01",
            "name": "Desktop PC",
            "hostname": "desktop-pc",
            "ip": "192.168.10.100",
            "is_wired": True,
            "network": "Core",
            "vlan": 10,
            "uptime": 86400,
            "tx_bytes": 1073741824,  # 1 GB
            "rx_bytes": 2147483648,  # 2 GB
            "tx_rate": 1000000,  # 1 Gbps
            "rx_rate": 1000000,
            "oui": "Dell Inc.",
            "os_name": "Windows",
            "os_class": "Windows",
            "first_seen": 1696800000,
            "last_seen": 1696886400,
            "latest_assoc_time": 1696800000,
        },
        {
            "mac": "aa:bb:cc:dd:ee:02",
            "name": "Laptop",
            "hostname": "laptop",
            "ip": "192.168.10.101",
            "is_wired": False,
            "network": "Core",
            "vlan": 10,
            "uptime": 43200,
            "tx_bytes": 536870912,  # 512 MB
            "rx_bytes": 1073741824,  # 1 GB
            "tx_rate": 500000,
            "rx_rate": 500000,
            "signal": -45,
            "noise": -95,
            "rssi": 50,
            "channel": 36,
            "essid": "HomeNetwork",
            "radio": "ng",
            "radio_proto": "ax",
            "oui": "Apple Inc.",
            "os_name": "macOS",
            "os_class": "macOS",
            "first_seen": 1696800000,
            "last_seen": 1696886400,
            "latest_assoc_time": 1696843200,
        },
        {
            "mac": "aa:bb:cc:dd:ee:03",
            "name": "Phone",
            "hostname": "phone",
            "ip": "192.168.10.102",
            "is_wired": False,
            "network": "Core",
            "vlan": 10,
            "uptime": 21600,
            "tx_bytes": 268435456,  # 256 MB
            "rx_bytes": 536870912,  # 512 MB
            "tx_rate": 250000,
            "rx_rate": 250000,
            "signal": -55,
            "noise": -95,
            "rssi": 40,
            "channel": 36,
            "essid": "HomeNetwork",
            "radio": "ng",
            "radio_proto": "ac",
            "oui": "Samsung",
            "os_name": "Android",
            "os_class": "Android",
            "first_seen": 1696800000,
            "last_seen": 1696886400,
            "latest_assoc_time": 1696864800,
        },
    ]
}

MOCK_DEVICE_STATS_DATA = {
    "data": [
        {
            "_id": "device123",
            "mac": "11:22:33:44:55:66",
            "name": "Core Switch",
            "model": "US-24-250W",
            "type": "usw",
            "version": "6.5.59",
            "state": 1,
            "adopted": True,
            "uptime": 172800,
            "last_seen": 1696886400,
            "ip": "192.168.10.2",
            "tx_bytes": 10737418240,  # 10 GB
            "rx_bytes": 21474836480,  # 20 GB
            "uplink": {
                "type": "wire",
                "speed": 10000,
                "full_duplex": True,
            },
            "system-stats": {
                "cpu": 15,
                "mem": 30,
                "uptime": 172800,
                "temps": {
                    "Board (CPU)": 45,
                    "PHY": 50,
                }
            },
            "port_table": [
                {
                    "port_idx": 1,
                    "name": "Port 1",
                    "up": True,
                    "speed": 1000,
                    "full_duplex": True,
                    "tx_bytes": 1073741824,
                    "rx_bytes": 2147483648,
                },
                {
                    "port_idx": 2,
                    "name": "Port 2",
                    "up": False,
                    "speed": 0,
                    "full_duplex": False,
                    "tx_bytes": 0,
                    "rx_bytes": 0,
                },
            ]
        },
        {
            "_id": "device456",
            "mac": "77:88:99:aa:bb:cc",
            "name": "Living Room AP",
            "model": "U6-Pro",
            "type": "uap",
            "version": "6.5.54",
            "state": 1,
            "adopted": True,
            "uptime": 86400,
            "last_seen": 1696886400,
            "ip": "192.168.10.3",
            "tx_bytes": 5368709120,  # 5 GB
            "rx_bytes": 10737418240,  # 10 GB
            "uplink": {
                "type": "wire",
                "speed": 1000,
                "full_duplex": True,
            },
            "system-stats": {
                "cpu": 10,
                "mem": 25,
                "uptime": 86400,
                "temps": {
                    "Board (CPU)": 40,
                }
            },
            "num_sta": 5,
            "user-num_sta": 4,
            "guest-num_sta": 1,
            "radio_table": [
                {
                    "name": "wifi0",
                    "radio": "ng",
                    "channel": 6,
                    "tx_power": 20,
                    "num_sta": 3,
                },
                {
                    "name": "wifi1",
                    "radio": "na",
                    "channel": 36,
                    "tx_power": 22,
                    "num_sta": 2,
                },
            ]
        },
    ]
}


class TestGetClientStatsTool:
    """Tests for GetClientStatsTool."""
    
    @pytest.fixture
    def client_stats_tool(self):
        """Create a GetClientStatsTool instance."""
        from unifi_mcp.tools.statistics import GetClientStatsTool
        return GetClientStatsTool()
    
    def test_tool_metadata(self, client_stats_tool):
        """Test tool has correct metadata."""
        assert client_stats_tool.name == "unifi_get_client_stats"
        assert client_stats_tool.description == "Get statistics for a specific client"
        assert client_stats_tool.category == "statistics"
        assert client_stats_tool.input_schema["type"] == "object"
        assert "mac_address" in client_stats_tool.input_schema["properties"]
        assert "mac_address" in client_stats_tool.input_schema["required"]
    
    @pytest.mark.asyncio
    async def test_get_client_stats_wired_success(self, client_stats_tool, mock_unifi_client):
        """Test successful client stats retrieval for wired client."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool
        result = await client_stats_tool.execute(
            mock_unifi_client,
            mac_address="aa:bb:cc:dd:ee:01"
        )
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert "message" in result
        
        # Verify data structure
        data = result["data"]
        assert "identity" in data
        assert "connection" in data
        assert "bandwidth" in data
        assert "device_info" in data
        assert "session" in data
        assert "wireless" not in data  # Wired client shouldn't have wireless stats
        
        # Verify identity data
        identity = data["identity"]
        assert identity["mac_address"] == "aa:bb:cc:dd:ee:01"
        assert identity["name"] == "Desktop PC"
        assert identity["ip_address"] == "192.168.10.100"
        
        # Verify connection data
        connection = data["connection"]
        assert connection["type"] == "wired"
        assert connection["network"] == "Core"
        assert connection["vlan"] == 10
        
        # Verify bandwidth data
        bandwidth = data["bandwidth"]
        assert bandwidth["tx_bytes"] == 1073741824
        assert bandwidth["rx_bytes"] == 2147483648
        assert "1.00 GB" in bandwidth["tx_bytes_formatted"]
        assert "2.00 GB" in bandwidth["rx_bytes_formatted"]
    
    @pytest.mark.asyncio
    async def test_get_client_stats_wireless_success(self, client_stats_tool, mock_unifi_client):
        """Test successful client stats retrieval for wireless client."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool
        result = await client_stats_tool.execute(
            mock_unifi_client,
            mac_address="aa:bb:cc:dd:ee:02"
        )
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        
        # Verify wireless stats are included
        assert "wireless" in data
        wireless = data["wireless"]
        assert wireless["signal"] == -45
        assert wireless["noise"] == -95
        assert wireless["rssi"] == 50
        assert wireless["channel"] == 36
        assert wireless["essid"] == "HomeNetwork"
    
    @pytest.mark.asyncio
    async def test_get_client_stats_mac_normalization(self, client_stats_tool, mock_unifi_client):
        """Test MAC address normalization (with/without colons)."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Test with colons
        result1 = await client_stats_tool.execute(
            mock_unifi_client,
            mac_address="aa:bb:cc:dd:ee:01"
        )
        assert result1["success"] is True
        
        # Test without colons
        result2 = await client_stats_tool.execute(
            mock_unifi_client,
            mac_address="aabbccddee01"
        )
        assert result2["success"] is True
        
        # Test with uppercase
        result3 = await client_stats_tool.execute(
            mock_unifi_client,
            mac_address="AA:BB:CC:DD:EE:01"
        )
        assert result3["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_client_stats_not_found(self, client_stats_tool, mock_unifi_client):
        """Test client stats retrieval when client not found."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool with non-existent MAC
        with pytest.raises(Exception) as exc_info:
            await client_stats_tool.execute(
                mock_unifi_client,
                mac_address="ff:ff:ff:ff:ff:ff"
            )
        
        # Verify error
        assert "NOT_FOUND" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestGetDeviceStatsTool:
    """Tests for GetDeviceStatsTool."""
    
    @pytest.fixture
    def device_stats_tool(self):
        """Create a GetDeviceStatsTool instance."""
        from unifi_mcp.tools.statistics import GetDeviceStatsTool
        return GetDeviceStatsTool()
    
    def test_tool_metadata(self, device_stats_tool):
        """Test tool has correct metadata."""
        assert device_stats_tool.name == "unifi_get_device_stats"
        assert device_stats_tool.description == "Get statistics for a specific device"
        assert device_stats_tool.category == "statistics"
        assert device_stats_tool.input_schema["type"] == "object"
        assert "device_id" in device_stats_tool.input_schema["properties"]
        assert "device_id" in device_stats_tool.input_schema["required"]
    
    @pytest.mark.asyncio
    async def test_get_device_stats_switch_success(self, device_stats_tool, mock_unifi_client):
        """Test successful device stats retrieval for switch."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_DEVICE_STATS_DATA
        
        # Execute tool
        result = await device_stats_tool.execute(
            mock_unifi_client,
            device_id="device123"
        )
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        
        # Verify data structure
        data = result["data"]
        assert "identity" in data
        assert "status" in data
        assert "network" in data
        assert "statistics" in data
        assert "system" in data
        assert "ports" in data  # Switch should have port stats
        
        # Verify identity data
        identity = data["identity"]
        assert identity["id"] == "device123"
        assert identity["name"] == "Core Switch"
        assert identity["model"] == "US-24-250W"
        assert identity["type"] == "usw"
        
        # Verify status data
        status = data["status"]
        assert status["state"] == "online"
        assert status["adopted"] is True
        
        # Verify system stats
        system = data["system"]
        assert system["cpu_usage"] == 15
        assert system["memory_usage"] == 30
        assert "temperatures" in system
        
        # Verify port stats
        ports = data["ports"]
        assert ports["total"] == 2
        assert ports["active"] == 1
        assert len(ports["details"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_device_stats_ap_success(self, device_stats_tool, mock_unifi_client):
        """Test successful device stats retrieval for access point."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_DEVICE_STATS_DATA
        
        # Execute tool
        result = await device_stats_tool.execute(
            mock_unifi_client,
            device_id="device456"
        )
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        
        # Verify wireless stats are included for AP
        assert "wireless" in data
        wireless = data["wireless"]
        assert wireless["num_sta"] == 5
        assert wireless["user-num_sta"] == 4
        assert wireless["guest-num_sta"] == 1
        assert "radios" in wireless
        assert len(wireless["radios"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_device_stats_by_mac(self, device_stats_tool, mock_unifi_client):
        """Test device stats retrieval by MAC address."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_DEVICE_STATS_DATA
        
        # Execute tool with MAC address
        result = await device_stats_tool.execute(
            mock_unifi_client,
            device_id="11:22:33:44:55:66"
        )
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        assert data["identity"]["mac_address"] == "11:22:33:44:55:66"
    
    @pytest.mark.asyncio
    async def test_get_device_stats_not_found(self, device_stats_tool, mock_unifi_client):
        """Test device stats retrieval when device not found."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_DEVICE_STATS_DATA
        
        # Execute tool with non-existent ID
        with pytest.raises(Exception) as exc_info:
            await device_stats_tool.execute(
                mock_unifi_client,
                device_id="nonexistent"
            )
        
        # Verify error
        assert "NOT_FOUND" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestGetTopClientsTool:
    """Tests for GetTopClientsTool."""
    
    @pytest.fixture
    def top_clients_tool(self):
        """Create a GetTopClientsTool instance."""
        from unifi_mcp.tools.statistics import GetTopClientsTool
        return GetTopClientsTool()
    
    def test_tool_metadata(self, top_clients_tool):
        """Test tool has correct metadata."""
        assert top_clients_tool.name == "unifi_get_top_clients"
        assert top_clients_tool.description == "List clients by bandwidth usage"
        assert top_clients_tool.category == "statistics"
        assert top_clients_tool.input_schema["type"] == "object"
        assert "limit" in top_clients_tool.input_schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_top_clients_success(self, top_clients_tool, mock_unifi_client):
        """Test successful top clients retrieval."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool
        result = await top_clients_tool.execute(mock_unifi_client, limit=10)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        
        # Verify data structure
        data = result["data"]
        assert "clients" in data
        assert "summary" in data
        
        # Verify clients are sorted by bandwidth (descending)
        clients = data["clients"]
        assert len(clients) == 3  # All 3 clients
        
        # Desktop PC should be first (1GB + 2GB = 3GB)
        assert clients[0]["name"] == "Desktop PC"
        assert clients[0]["total_bytes"] == 3221225472
        
        # Laptop should be second (512MB + 1GB = 1.5GB)
        assert clients[1]["name"] == "Laptop"
        assert clients[1]["total_bytes"] == 1610612736
        
        # Phone should be third (256MB + 512MB = 768MB)
        assert clients[2]["name"] == "Phone"
        assert clients[2]["total_bytes"] == 805306368
        
        # Verify summary
        summary = data["summary"]
        assert summary["total_clients"] == 3
        assert summary["top_clients_count"] == 3
        assert summary["total_bandwidth"] > 0
        assert "total_bandwidth_formatted" in summary
    
    @pytest.mark.asyncio
    async def test_get_top_clients_with_limit(self, top_clients_tool, mock_unifi_client):
        """Test top clients retrieval with limit."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool with limit of 2
        result = await top_clients_tool.execute(mock_unifi_client, limit=2)
        
        # Verify only 2 clients returned
        assert result["success"] is True
        data = result["data"]
        assert len(data["clients"]) == 2
        assert data["summary"]["top_clients_count"] == 2
        
        # Verify top 2 are correct
        assert data["clients"][0]["name"] == "Desktop PC"
        assert data["clients"][1]["name"] == "Laptop"
    
    @pytest.mark.asyncio
    async def test_get_top_clients_empty(self, top_clients_tool, mock_unifi_client):
        """Test top clients retrieval with no clients."""
        # Mock empty response
        mock_unifi_client.get.return_value = {"data": []}
        
        # Execute tool
        result = await top_clients_tool.execute(mock_unifi_client)
        
        # Verify result
        assert result["success"] is True
        data = result["data"]
        assert len(data["clients"]) == 0
        assert data["total_clients"] == 0
    
    @pytest.mark.asyncio
    async def test_get_top_clients_sorting(self, top_clients_tool, mock_unifi_client):
        """Test that clients are correctly sorted by total bandwidth."""
        # Mock API response
        mock_unifi_client.get.return_value = MOCK_CLIENT_STATS_DATA
        
        # Execute tool
        result = await top_clients_tool.execute(mock_unifi_client)
        
        # Verify sorting
        clients = result["data"]["clients"]
        for i in range(len(clients) - 1):
            assert clients[i]["total_bytes"] >= clients[i + 1]["total_bytes"]


# Mock data for DPI and alerts testing
MOCK_DPI_DATA = {
    "data": [
        {
            "cat": "Streaming",
            "app": "Netflix",
            "tx_bytes": 5000000000,
            "rx_bytes": 50000000000,
        },
        {
            "cat": "Social",
            "app": "Facebook",
            "tx_bytes": 1000000000,
            "rx_bytes": 2000000000,
        },
        {
            "cat": "Gaming",
            "app": "Steam",
            "tx_bytes": 500000000,
            "rx_bytes": 10000000000,
        },
    ]
}

MOCK_ALERTS_DATA = {
    "data": [
        {
            "key": "EVT_GW_WANTransition",
            "msg": "WAN connection restored",
            "datetime": "2025-10-09T10:00:00Z",
            "time": 1728468000,
            "archived": False,
            "handled": False,
            "subsystem": "wan",
        },
        {
            "key": "EVT_AP_Disconnected",
            "msg": "AP disconnected",
            "datetime": "2025-10-09T09:00:00Z",
            "time": 1728464400,
            "archived": True,
            "handled": True,
            "subsystem": "wlan",
            "ap": "aa:bb:cc:dd:ee:ff",
            "ap_name": "Living Room AP",
        },
        {
            "key": "EVT_AP_Connected",
            "msg": "AP connected",
            "datetime": "2025-10-09T09:30:00Z",
            "time": 1728466200,
            "archived": False,
            "handled": False,
            "subsystem": "wlan",
            "ap": "aa:bb:cc:dd:ee:ff",
            "ap_name": "Living Room AP",
        },
    ]
}


@pytest.fixture
def dpi_stats_tool():
    """Create a GetDPIStatsTool instance."""
    from unifi_mcp.tools.statistics import GetDPIStatsTool
    return GetDPIStatsTool()


@pytest.fixture
def alerts_tool():
    """Create a GetAlertsTool instance."""
    from unifi_mcp.tools.statistics import GetAlertsTool
    return GetAlertsTool()


class TestGetDPIStatsTool:
    """Tests for GetDPIStatsTool."""
    
    def test_tool_metadata(self, dpi_stats_tool):
        """Test tool has correct metadata."""
        assert dpi_stats_tool.name == "unifi_get_dpi_stats"
        assert dpi_stats_tool.description == "Get deep packet inspection statistics"
        assert dpi_stats_tool.category == "statistics"
        assert dpi_stats_tool.input_schema["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_get_dpi_stats_success(self, dpi_stats_tool, mock_unifi_client):
        """Test successful DPI stats retrieval."""
        # Mock the API response
        mock_unifi_client.get.return_value = MOCK_DPI_DATA
        
        # Execute the tool
        result = await dpi_stats_tool.execute(mock_unifi_client)
        
        # Verify API was called correctly
        mock_unifi_client.get.assert_called_once_with("/api/s/{site}/stat/dpi")
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert "categories" in result["data"]
        assert "top_applications" in result["data"]
        assert "total_traffic" in result["data"]
        
        # Verify data content
        data = result["data"]
        assert len(data["categories"]) == 3
        assert len(data["top_applications"]) == 3  # All 3 since we have less than 10
        
        # Verify sorting (should be by total bytes descending)
        assert data["categories"][0]["application"] == "Netflix"  # Highest traffic
        assert data["categories"][0]["total_bytes"] == 55000000000
        
        # Verify total traffic calculation
        assert data["total_traffic"]["tx_bytes"] == 6500000000
        assert data["total_traffic"]["rx_bytes"] == 62000000000
        assert data["total_traffic"]["total_bytes"] == 68500000000
        
        # Verify formatted values exist
        assert "tx_bytes_formatted" in data["total_traffic"]
        assert "rx_bytes_formatted" in data["total_traffic"]
        assert "total_bytes_formatted" in data["total_traffic"]
    
    @pytest.mark.asyncio
    async def test_get_dpi_stats_no_data(self, dpi_stats_tool, mock_unifi_client):
        """Test DPI stats retrieval with no data."""
        # Mock empty response
        mock_unifi_client.get.return_value = {"data": []}
        
        # Execute the tool
        result = await dpi_stats_tool.execute(mock_unifi_client)
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["categories"] == []
        assert result["data"]["top_applications"] == []
        assert result["data"]["total_traffic"]["total_bytes"] == 0
    
    @pytest.mark.asyncio
    async def test_get_dpi_stats_api_error(self, dpi_stats_tool, mock_unifi_client):
        """Test DPI stats retrieval with API error."""
        # Mock API error
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        # Execute the tool and expect error
        with pytest.raises(ToolError) as exc_info:
            await dpi_stats_tool.execute(mock_unifi_client)
        
        # Verify error details
        assert exc_info.value.code == "API_ERROR"
        assert "Failed to retrieve DPI statistics" in exc_info.value.message
    
    def test_format_bytes(self, dpi_stats_tool):
        """Test byte formatting."""
        assert dpi_stats_tool._format_bytes(500) == "500 B"
        assert dpi_stats_tool._format_bytes(1024) == "1.00 KB"
        assert dpi_stats_tool._format_bytes(1048576) == "1.00 MB"
        assert dpi_stats_tool._format_bytes(1073741824) == "1.00 GB"
        assert dpi_stats_tool._format_bytes(1099511627776) == "1.00 TB"


class TestGetAlertsTool:
    """Tests for GetAlertsTool."""
    
    def test_tool_metadata(self, alerts_tool):
        """Test tool has correct metadata."""
        assert alerts_tool.name == "unifi_get_alerts"
        assert alerts_tool.description == "Get recent system alerts and events"
        assert alerts_tool.category == "statistics"
        assert alerts_tool.input_schema["type"] == "object"
        assert "limit" in alerts_tool.input_schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_alerts_success(self, alerts_tool, mock_unifi_client):
        """Test successful alerts retrieval."""
        # Mock the API response
        mock_unifi_client.get.return_value = MOCK_ALERTS_DATA
        
        # Execute the tool
        result = await alerts_tool.execute(mock_unifi_client)
        
        # Verify API was called correctly
        mock_unifi_client.get.assert_called_once_with("/api/s/{site}/stat/alarm")
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert "alerts" in result["data"]
        assert "summary" in result["data"]
        
        # Verify data content
        data = result["data"]
        assert len(data["alerts"]) == 3
        assert data["summary"]["total_available"] == 3
        assert data["summary"]["returned"] == 3
        assert data["summary"]["archived"] == 1
        assert data["summary"]["unarchived"] == 2
        
        # Verify alert structure
        alert = data["alerts"][0]
        assert "key" in alert
        assert "message" in alert
        assert "timestamp" in alert
        assert "time" in alert
        assert "archived" in alert
        assert "handled" in alert
        assert "subsystem" in alert
        
        # Verify device information is included when present
        alert_with_device = data["alerts"][1]
        assert "device_mac" in alert_with_device
        assert "device_name" in alert_with_device
        assert alert_with_device["device_mac"] == "aa:bb:cc:dd:ee:ff"
        assert alert_with_device["device_name"] == "Living Room AP"
    
    @pytest.mark.asyncio
    async def test_get_alerts_with_limit(self, alerts_tool, mock_unifi_client):
        """Test alerts retrieval with limit parameter."""
        # Mock the API response
        mock_unifi_client.get.return_value = MOCK_ALERTS_DATA
        
        # Execute the tool with limit
        result = await alerts_tool.execute(mock_unifi_client, limit=2)
        
        # Verify only 2 alerts returned
        assert len(result["data"]["alerts"]) == 2
        assert result["data"]["summary"]["returned"] == 2
        assert result["data"]["summary"]["total_available"] == 3
    
    @pytest.mark.asyncio
    async def test_get_alerts_limit_validation(self, alerts_tool, mock_unifi_client):
        """Test limit parameter validation."""
        # Mock the API response
        mock_unifi_client.get.return_value = MOCK_ALERTS_DATA
        
        # Test with limit < 1 (should be clamped to 1)
        result = await alerts_tool.execute(mock_unifi_client, limit=0)
        assert len(result["data"]["alerts"]) >= 1
        
        # Test with limit > 500 (should be clamped to 500)
        result = await alerts_tool.execute(mock_unifi_client, limit=1000)
        # Should return all available (3) since it's less than 500
        assert len(result["data"]["alerts"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_alerts_no_data(self, alerts_tool, mock_unifi_client):
        """Test alerts retrieval with no data."""
        # Mock empty response
        mock_unifi_client.get.return_value = {"data": []}
        
        # Execute the tool
        result = await alerts_tool.execute(mock_unifi_client)
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["alerts"] == []
        assert result["data"]["summary"]["total_available"] == 0
        assert result["data"]["summary"]["returned"] == 0
    
    @pytest.mark.asyncio
    async def test_get_alerts_api_error(self, alerts_tool, mock_unifi_client):
        """Test alerts retrieval with API error."""
        # Mock API error
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        # Execute the tool and expect error
        with pytest.raises(ToolError) as exc_info:
            await alerts_tool.execute(mock_unifi_client)
        
        # Verify error details
        assert exc_info.value.code == "API_ERROR"
        assert "Failed to retrieve alerts" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_get_alerts_summary_statistics(self, alerts_tool, mock_unifi_client):
        """Test alert summary statistics calculation."""
        # Mock the API response
        mock_unifi_client.get.return_value = MOCK_ALERTS_DATA
        
        # Execute the tool
        result = await alerts_tool.execute(mock_unifi_client)
        
        # Verify summary statistics
        summary = result["data"]["summary"]
        assert "alert_types" in summary
        assert summary["alert_types"]["EVT_GW_WANTransition"] == 1
        assert summary["alert_types"]["EVT_AP_Disconnected"] == 1
        assert summary["alert_types"]["EVT_AP_Connected"] == 1
