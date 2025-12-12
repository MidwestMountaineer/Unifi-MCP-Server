"""Demo script for client and device statistics tools.

This script demonstrates the new statistics tools:
- GetClientStatsTool: Get detailed stats for a specific client
- GetDeviceStatsTool: Get detailed stats for a specific device
- GetTopClientsTool: List top bandwidth consumers

Usage:
    python examples/client_device_stats_demo.py
"""

import asyncio
import os
from dotenv import load_dotenv

from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.config.loader import load_config
from unifi_mcp.tools.statistics import (
    GetClientStatsTool,
    GetDeviceStatsTool,
    GetTopClientsTool,
)


async def demo_client_stats(client: UniFiClient):
    """Demo GetClientStatsTool."""
    print("\n" + "=" * 80)
    print("DEMO: Get Client Statistics")
    print("=" * 80)
    
    tool = GetClientStatsTool()
    
    # First, get top clients to find a MAC address
    top_clients_tool = GetTopClientsTool()
    top_result = await top_clients_tool.execute(client, limit=1)
    
    if top_result["success"] and top_result["data"]["clients"]:
        mac_address = top_result["data"]["clients"][0]["mac_address"]
        print(f"\nFetching stats for client: {mac_address}")
        
        result = await tool.execute(client, mac_address=mac_address)
        
        if result["success"]:
            data = result["data"]
            
            print("\n--- Identity ---")
            print(f"Name: {data['identity']['name']}")
            print(f"MAC: {data['identity']['mac_address']}")
            print(f"IP: {data['identity']['ip_address']}")
            print(f"Hostname: {data['identity']['hostname']}")
            
            print("\n--- Connection ---")
            print(f"Type: {data['connection']['type']}")
            print(f"Network: {data['connection']['network']}")
            print(f"VLAN: {data['connection']['vlan']}")
            print(f"Uptime: {data['connection']['uptime_formatted']}")
            
            print("\n--- Bandwidth ---")
            print(f"TX: {data['bandwidth']['tx_bytes_formatted']} ({data['bandwidth']['tx_rate_formatted']})")
            print(f"RX: {data['bandwidth']['rx_bytes_formatted']} ({data['bandwidth']['rx_rate_formatted']})")
            
            print("\n--- Device Info ---")
            print(f"Manufacturer: {data['device_info']['manufacturer']}")
            print(f"OS: {data['device_info']['os_name']}")
            
            # Show wireless stats if available
            if "wireless" in data:
                print("\n--- Wireless ---")
                print(f"Signal: {data['wireless']['signal']} dBm")
                print(f"RSSI: {data['wireless']['rssi']}")
                print(f"Channel: {data['wireless']['channel']}")
                print(f"SSID: {data['wireless']['essid']}")
                print(f"Protocol: {data['wireless']['radio_proto']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        print("No clients found to demo")


async def demo_device_stats(client: UniFiClient):
    """Demo GetDeviceStatsTool."""
    print("\n" + "=" * 80)
    print("DEMO: Get Device Statistics")
    print("=" * 80)
    
    tool = GetDeviceStatsTool()
    
    # Get list of devices first
    from unifi_mcp.tools.network_discovery import ListDevicesTool
    list_tool = ListDevicesTool()
    list_result = await list_tool.execute(client)
    
    if list_result["success"] and list_result["data"]["devices"]:
        device_id = list_result["data"]["devices"][0]["id"]
        print(f"\nFetching stats for device: {device_id}")
        
        result = await tool.execute(client, device_id=device_id)
        
        if result["success"]:
            data = result["data"]
            
            print("\n--- Identity ---")
            print(f"Name: {data['identity']['name']}")
            print(f"Model: {data['identity']['model']}")
            print(f"Type: {data['identity']['type']}")
            print(f"Version: {data['identity']['version']}")
            print(f"MAC: {data['identity']['mac_address']}")
            
            print("\n--- Status ---")
            print(f"State: {data['status']['state']}")
            print(f"Adopted: {data['status']['adopted']}")
            print(f"Uptime: {data['status']['uptime_formatted']}")
            
            print("\n--- Network ---")
            print(f"IP: {data['network']['ip_address']}")
            print(f"Uplink Type: {data['network']['uplink']['type']}")
            print(f"Uplink Speed: {data['network']['uplink']['speed']} Mbps")
            
            print("\n--- Statistics ---")
            print(f"TX: {data['statistics']['tx_bytes_formatted']}")
            print(f"RX: {data['statistics']['rx_bytes_formatted']}")
            
            # Show system stats if available
            if "system" in data:
                print("\n--- System ---")
                print(f"CPU Usage: {data['system']['cpu_usage']}%")
                print(f"Memory Usage: {data['system']['memory_usage']}%")
                if "temperatures" in data["system"]:
                    print("Temperatures:")
                    for sensor, temp in data["system"]["temperatures"].items():
                        print(f"  {sensor}: {temp}°C")
            
            # Show port stats for switches
            if "ports" in data:
                print("\n--- Ports ---")
                print(f"Total: {data['ports']['total']}")
                print(f"Active: {data['ports']['active']}")
                print("\nPort Details (first 5):")
                for port in data['ports']['details'][:5]:
                    status = "UP" if port['up'] else "DOWN"
                    print(f"  Port {port['port_idx']} ({port['name']}): {status} - {port['speed']} Mbps")
            
            # Show wireless stats for APs
            if "wireless" in data:
                print("\n--- Wireless ---")
                print(f"Connected Clients: {data['wireless']['num_sta']}")
                print(f"User Clients: {data['wireless']['user-num_sta']}")
                print(f"Guest Clients: {data['wireless']['guest-num_sta']}")
                if "radios" in data["wireless"]:
                    print("\nRadios:")
                    for radio in data["wireless"]["radios"]:
                        print(f"  {radio['name']} ({radio['radio']}): Channel {radio['channel']}, {radio['num_sta']} clients")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        print("No devices found to demo")


async def demo_top_clients(client: UniFiClient):
    """Demo GetTopClientsTool."""
    print("\n" + "=" * 80)
    print("DEMO: Get Top Clients by Bandwidth")
    print("=" * 80)
    
    tool = GetTopClientsTool()
    
    print("\nFetching top 10 clients by bandwidth...")
    result = await tool.execute(client, limit=10)
    
    if result["success"]:
        data = result["data"]
        
        print("\n--- Summary ---")
        print(f"Total Clients: {data['summary']['total_clients']}")
        print(f"Top Clients: {data['summary']['top_clients_count']}")
        print(f"Total Bandwidth: {data['summary']['total_bandwidth_formatted']}")
        print(f"Top Bandwidth: {data['summary']['top_bandwidth_formatted']} ({data['summary']['top_percentage']}%)")
        
        print("\n--- Top Clients ---")
        print(f"{'Rank':<6} {'Name':<20} {'Type':<10} {'Total':<15} {'TX':<15} {'RX':<15}")
        print("-" * 90)
        
        for i, client_data in enumerate(data["clients"], 1):
            print(
                f"{i:<6} "
                f"{client_data['name'][:19]:<20} "
                f"{client_data['connection_type']:<10} "
                f"{client_data['total_bytes_formatted']:<15} "
                f"{client_data['tx_bytes_formatted']:<15} "
                f"{client_data['rx_bytes_formatted']:<15}"
            )
        
        # Show percentage breakdown
        print("\n--- Bandwidth Distribution ---")
        for i, client_data in enumerate(data["clients"][:5], 1):
            percentage = (client_data['total_bytes'] / data['summary']['total_bandwidth'] * 100) if data['summary']['total_bandwidth'] > 0 else 0
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            print(f"{client_data['name'][:20]:<20} {bar} {percentage:.1f}%")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


async def main():
    """Run all demos."""
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config = load_config()
    
    # Create UniFi client
    client = UniFiClient(config)
    
    try:
        # Connect to UniFi controller
        print("Connecting to UniFi controller...")
        await client.connect()
        print("Connected successfully!")
        
        # Run demos
        await demo_top_clients(client)
        await demo_client_stats(client)
        await demo_device_stats(client)
        
        print("\n" + "=" * 80)
        print("All demos completed successfully!")
        print("=" * 80)
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
