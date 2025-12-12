"""Phase 4 Interactive Demo with Mock Data

This demo shows actual tool output using mock UniFi data.
It demonstrates what the tools return when querying a real UniFi controller.
"""

import asyncio
import json
from unittest.mock import AsyncMock

from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.tools.network_discovery import (
    ListDevicesTool,
    GetDeviceDetailsTool,
    ListClientsTool,
    GetClientDetailsTool,
    ListNetworksTool,
    GetNetworkDetailsTool,
    ListWLANsTool,
    GetWLANDetailsTool,
)


# Mock data representing a typical homelab setup
MOCK_DEVICES = [
    {
        "_id": "device1",
        "mac": "aa:bb:cc:dd:ee:01",
        "name": "HalfRack-Switch",
        "type": "usw",
        "model": "US-24-250W",
        "ip": "192.168.10.11",
        "state": 1,
        "uptime": 2592000,  # 30 days
        "version": "6.5.55",
        "adopted": True,
        "system-stats": {"cpu": 12, "mem": 28},
        "port_table": [
            {"port_idx": 1, "name": "uNAS Pro", "enable": True, "up": True, "speed": 10000, "full_duplex": True, "poe_enable": False},
            {"port_idx": 2, "name": "RackPC", "enable": True, "up": True, "speed": 10000, "full_duplex": True, "poe_enable": False},
            {"port_idx": 3, "name": "Pi Cluster", "enable": True, "up": True, "speed": 1000, "full_duplex": True, "poe_enable": True, "poe_power": 15.2},
        ],
    },
    {
        "_id": "device2",
        "mac": "aa:bb:cc:dd:ee:02",
        "name": "Living-Room-AP",
        "type": "uap",
        "model": "U6-LR",
        "ip": "192.168.10.21",
        "state": 1,
        "uptime": 1728000,  # 20 days
        "version": "6.5.55",
        "adopted": True,
        "num_sta": 8,
        "radio_table": [
            {"name": "2.4GHz", "radio": "ng", "channel": 6, "tx_power": 20, "num_sta": 3},
            {"name": "5GHz", "radio": "na", "channel": 44, "tx_power": 23, "num_sta": 5},
        ],
    },
    {
        "_id": "device3",
        "mac": "aa:bb:cc:dd:ee:03",
        "name": "HalfRack-DM",
        "type": "udm",
        "model": "UDM-Pro",
        "ip": "192.168.1.1",
        "state": 1,
        "uptime": 3456000,  # 40 days
        "version": "3.0.20",
        "adopted": True,
    },
]

MOCK_CLIENTS = [
    {
        "mac": "11:22:33:44:55:01",
        "name": "Austin-Laptop",
        "ip": "192.168.10.100",
        "is_wired": False,
        "network": "Core",
        "uptime": 86400,
        "tx_bytes": 5368709120,  # 5 GB
        "rx_bytes": 21474836480,  # 20 GB
        "signal": -45,
        "rssi": -45,
        "essid": "HomeWiFi",
        "channel": 44,
    },
    {
        "mac": "11:22:33:44:55:02",
        "name": "RackPC",
        "ip": "192.168.10.20",
        "is_wired": True,
        "network": "Core",
        "uptime": 2592000,
        "tx_bytes": 107374182400,  # 100 GB
        "rx_bytes": 53687091200,  # 50 GB
        "sw_mac": "aa:bb:cc:dd:ee:01",
        "sw_name": "HalfRack-Switch",
    },
    {
        "mac": "11:22:33:44:55:03",
        "name": "Smart-TV",
        "ip": "192.168.20.50",
        "is_wired": False,
        "network": "IoT",
        "uptime": 172800,
        "tx_bytes": 1073741824,  # 1 GB
        "rx_bytes": 10737418240,  # 10 GB
        "signal": -62,
        "rssi": -62,
        "essid": "IoT-WiFi",
        "channel": 6,
    },
]

MOCK_NETWORKS = [
    {
        "_id": "network1",
        "name": "Core",
        "purpose": "corporate",
        "vlan": "10",
        "vlan_enabled": True,
        "ip_subnet": "192.168.10.0/24",
        "networkgroup": "LAN",
        "dhcpd_enabled": True,
        "dhcpd_start": "192.168.10.100",
        "dhcpd_stop": "192.168.10.200",
        "domain_name": "core.local",
        "enabled": True,
        "gateway_ip": "192.168.10.1",
        "dhcpd_leasetime": 86400,
        "dhcpd_dns": ["192.168.10.1", "8.8.8.8"],
        "is_nat": False,
        "is_guest": False,
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
        "dhcpd_leasetime": 86400,
        "dhcpd_dns": ["192.168.10.1"],
        "is_nat": False,
        "is_guest": False,
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
        "dhcpd_leasetime": 3600,
        "dhcpd_dns": ["8.8.8.8"],
        "is_nat": True,
        "is_guest": True,
    },
]

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
        "vlan": "10",
        "vlan_enabled": True,
        "is_guest": False,
        "hide_ssid": False,
        "band_steering_mode": "prefer_5g",
        "fast_roaming_enabled": True,
        "wpa3_support": False,
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
        "band_steering_mode": "off",
        "fast_roaming_enabled": False,
        "wpa3_support": False,
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
        "portal_enabled": True,
        "portal_customized": True,
        "band_steering_mode": "off",
        "fast_roaming_enabled": False,
        "wpa3_support": False,
    },
]


def create_mock_client():
    """Create a mock UniFi client with test data."""
    client = AsyncMock(spec=UniFiClient)
    
    async def mock_get(endpoint):
        if "stat/device" in endpoint:
            return {"data": MOCK_DEVICES}
        elif "stat/sta" in endpoint:
            return {"data": MOCK_CLIENTS}
        elif "rest/networkconf" in endpoint:
            return {"data": MOCK_NETWORKS}
        elif "rest/wlanconf" in endpoint:
            return {"data": MOCK_WLANS}
        return {"data": []}
    
    client.get = mock_get
    return client


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_json(data: dict, indent: int = 2) -> None:
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent))


async def demo_devices():
    """Demo device tools with mock data."""
    print_section("1. DEVICE DISCOVERY")
    
    client = create_mock_client()
    
    # List devices
    print("🔍 Command: List all devices\n")
    tool = ListDevicesTool()
    result = await tool.execute(client)
    
    print("📋 Result:")
    print_json(result)
    
    # Get device details
    print("\n\n🔍 Command: Get details for 'HalfRack-Switch'\n")
    tool = GetDeviceDetailsTool()
    result = await tool.execute(client, device_id="device1")
    
    print("📋 Result:")
    print_json(result)


async def demo_clients():
    """Demo client tools with mock data."""
    print_section("2. CLIENT DISCOVERY")
    
    client = create_mock_client()
    
    # List clients
    print("🔍 Command: List all connected clients\n")
    tool = ListClientsTool()
    result = await tool.execute(client)
    
    print("📋 Result:")
    print_json(result)
    
    # Get client details
    print("\n\n🔍 Command: Get details for 'Austin-Laptop'\n")
    tool = GetClientDetailsTool()
    result = await tool.execute(client, mac_address="11:22:33:44:55:01")
    
    print("📋 Result:")
    print_json(result)


async def demo_networks():
    """Demo network tools with mock data."""
    print_section("3. NETWORK CONFIGURATION")
    
    client = create_mock_client()
    
    # List networks
    print("🔍 Command: List all networks and VLANs\n")
    tool = ListNetworksTool()
    result = await tool.execute(client)
    
    print("📋 Result:")
    print_json(result)
    
    # Get network details
    print("\n\n🔍 Command: Get details for 'IoT' network\n")
    tool = GetNetworkDetailsTool()
    result = await tool.execute(client, network_id="network2")
    
    print("📋 Result:")
    print_json(result)


async def demo_wlans():
    """Demo WLAN tools with mock data."""
    print_section("4. WIRELESS NETWORKS")
    
    client = create_mock_client()
    
    # List WLANs
    print("🔍 Command: List all wireless networks\n")
    tool = ListWLANsTool()
    result = await tool.execute(client)
    
    print("📋 Result:")
    print_json(result)
    
    # Get WLAN details
    print("\n\n🔍 Command: Get details for 'Guest-WiFi'\n")
    tool = GetWLANDetailsTool()
    result = await tool.execute(client, wlan_id="wlan3")
    
    print("📋 Result:")
    print_json(result)


async def main():
    """Run the interactive demo."""
    print("\n" + "=" * 80)
    print("  UniFi MCP Server - Phase 4 Interactive Demo")
    print("  Showing Actual Tool Output with Mock Data")
    print("=" * 80)
    
    print("\n📝 This demo shows what the tools return when querying a UniFi controller.")
    print("   The data represents a typical homelab setup with:")
    print("   - 3 devices (switch, AP, gateway)")
    print("   - 3 clients (laptop, PC, smart TV)")
    print("   - 3 networks (Core, IoT, Guest)")
    print("   - 3 wireless networks (HomeWiFi, IoT-WiFi, Guest-WiFi)")
    
    await demo_devices()
    await demo_clients()
    await demo_networks()
    await demo_wlans()
    
    print_section("DEMO COMPLETE")
    print("✅ All 8 tools demonstrated successfully!")
    print("\n📚 Key Takeaways:")
    print("   • Tools return structured JSON data")
    print("   • Summary views for lists (optimized for AI)")
    print("   • Detail views for individual items (comprehensive)")
    print("   • Consistent error handling across all tools")
    print("   • Pagination support for large datasets")
    print("   • Flexible lookup (by ID, MAC, or name)")
    print("\n🚀 Ready to use with your UniFi controller!")
    print("   See docs/MCP-SERVER.md for setup instructions.\n")


if __name__ == "__main__":
    asyncio.run(main())
