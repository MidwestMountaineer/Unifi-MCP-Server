"""Demo script for statistics tools.

This script demonstrates the usage of statistics tools:
- GetNetworkStatsTool: Get overall network statistics
- GetSystemHealthTool: Get system health metrics

Run this script to test the statistics tools against your UniFi controller.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.tools.statistics import GetNetworkStatsTool, GetSystemHealthTool
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.config.loader import load_config


async def demo_network_stats():
    """Demonstrate GetNetworkStatsTool."""
    print("\n" + "=" * 80)
    print("DEMO: Get Network Statistics")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    # Create UniFi client (pass unifi config, not full config)
    client = UniFiClient(config.unifi, config.server.performance)
    
    try:
        # Connect to UniFi controller
        print("\n1. Connecting to UniFi controller...")
        await client.connect()
        print("   ✓ Connected successfully")
        
        # Create tool instance
        tool = GetNetworkStatsTool()
        print(f"\n2. Tool: {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Category: {tool.category}")
        
        # Execute tool
        print("\n3. Executing tool...")
        result = await tool.invoke(client, {})
        
        # Display results
        print("\n4. Results:")
        print(json.dumps(result, indent=2))
        
        # Extract key metrics
        if result.get("success"):
            data = result.get("data", {})
            summary = data.get("summary", {})
            bandwidth = data.get("bandwidth", {})
            health = data.get("health", {})
            
            print("\n5. Key Metrics:")
            print(f"   • Total Clients: {summary.get('total_clients', 0)}")
            print(f"     - Wired: {summary.get('wired_clients', 0)}")
            print(f"     - Wireless: {summary.get('wireless_clients', 0)}")
            print(f"   • Devices: {summary.get('online_devices', 0)}/{summary.get('total_devices', 0)} online")
            print(f"   • Bandwidth:")
            print(f"     - TX: {bandwidth.get('total_tx_bytes_formatted', 'N/A')}")
            print(f"     - RX: {bandwidth.get('total_rx_bytes_formatted', 'N/A')}")
            print(f"   • Health:")
            print(f"     - WAN: {health.get('wan_status', 'unknown')}")
            print(f"     - LAN: {health.get('lan_status', 'unknown')}")
            print(f"     - WWW: {health.get('www_status', 'unknown')}")
    
    finally:
        # Close client
        await client.close()
        print("\n✓ Demo completed")


async def demo_system_health():
    """Demonstrate GetSystemHealthTool."""
    print("\n" + "=" * 80)
    print("DEMO: Get System Health")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    # Create UniFi client (pass unifi config, not full config)
    client = UniFiClient(config.unifi, config.server.performance)
    
    try:
        # Connect to UniFi controller
        print("\n1. Connecting to UniFi controller...")
        await client.connect()
        print("   ✓ Connected successfully")
        
        # Create tool instance
        tool = GetSystemHealthTool()
        print(f"\n2. Tool: {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Category: {tool.category}")
        
        # Execute tool
        print("\n3. Executing tool...")
        result = await tool.invoke(client, {})
        
        # Display results
        print("\n4. Results:")
        print(json.dumps(result, indent=2))
        
        # Extract key metrics
        if result.get("success"):
            data = result.get("data", {})
            controller = data.get("controller", {})
            subsystems = data.get("subsystems", [])
            devices = data.get("devices", [])
            alerts = data.get("alerts", {})
            overall_status = data.get("overall_status", "unknown")
            
            print("\n5. Key Metrics:")
            print(f"   • Overall Status: {overall_status.upper()}")
            print(f"   • Controller:")
            print(f"     - Version: {controller.get('version', 'unknown')}")
            print(f"     - Hostname: {controller.get('hostname', 'unknown')}")
            print(f"     - Uptime: {controller.get('uptime_formatted', 'unknown')}")
            print(f"   • Subsystems: {len(subsystems)}")
            for subsystem in subsystems:
                print(f"     - {subsystem.get('name', 'unknown')}: {subsystem.get('status', 'unknown')}")
            print(f"   • Devices: {len(devices)}")
            for device in devices[:5]:  # Show first 5
                print(f"     - {device.get('name', 'unknown')}: {device.get('state', 'unknown')}")
            if len(devices) > 5:
                print(f"     ... and {len(devices) - 5} more")
            print(f"   • Alerts: {alerts.get('total', 0)} total")
    
    finally:
        # Close client
        await client.close()
        print("\n✓ Demo completed")


async def demo_all():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("STATISTICS TOOLS DEMO")
    print("=" * 80)
    print("\nThis demo will test the statistics tools:")
    print("1. GetNetworkStatsTool - Overall network statistics")
    print("2. GetSystemHealthTool - System health metrics")
    
    # Run demos
    await demo_network_stats()
    await demo_system_health()
    
    print("\n" + "=" * 80)
    print("ALL DEMOS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for required environment variables
    # Either API key OR username/password is required
    has_api_key = bool(os.getenv("UNIFI_API_KEY"))
    has_credentials = bool(os.getenv("UNIFI_USERNAME")) and bool(os.getenv("UNIFI_PASSWORD"))
    
    if not os.getenv("UNIFI_HOST"):
        print("Error: UNIFI_HOST environment variable is required")
        sys.exit(1)
    
    if not has_api_key and not has_credentials:
        print("Error: Either UNIFI_API_KEY or (UNIFI_USERNAME and UNIFI_PASSWORD) is required")
        print("\nPlease set these variables in your .env file")
        sys.exit(1)
    
    # Run demos
    asyncio.run(demo_all())
