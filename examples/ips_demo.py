"""Demo script for IPS status tool.

This script demonstrates the GetIPSStatusTool functionality,
showing how to retrieve intrusion prevention system status,
threat statistics, and recent alerts.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.tools.security import GetIPSStatusTool
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.config.loader import load_config


async def demo_ips_status():
    """Demonstrate IPS status tool."""
    print("=" * 80)
    print("UniFi MCP Server - IPS Status Tool Demo")
    print("=" * 80)
    print()
    
    # Load configuration
    print("Loading configuration...")
    config = load_config()
    print(f"✓ Configuration loaded")
    print()
    
    # Create UniFi client
    print("Connecting to UniFi controller...")
    client = UniFiClient(config)
    await client.connect()
    print(f"✓ Connected to {config.unifi.host}")
    print()
    
    # Create IPS status tool
    ips_tool = GetIPSStatusTool()
    
    # Test 1: Get IPS status with alerts
    print("-" * 80)
    print("Test 1: Get IPS Status with Alerts")
    print("-" * 80)
    try:
        result = await ips_tool.execute(
            unifi_client=client,
            include_alerts=True,
            alert_limit=10
        )
        print(json.dumps(result, indent=2))
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
    
    # Test 2: Get IPS status without alerts
    print("-" * 80)
    print("Test 2: Get IPS Status without Alerts")
    print("-" * 80)
    try:
        result = await ips_tool.execute(
            unifi_client=client,
            include_alerts=False
        )
        print(json.dumps(result, indent=2))
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
    
    # Test 3: Get IPS status with limited alerts
    print("-" * 80)
    print("Test 3: Get IPS Status with Limited Alerts (5)")
    print("-" * 80)
    try:
        result = await ips_tool.execute(
            unifi_client=client,
            include_alerts=True,
            alert_limit=5
        )
        print(json.dumps(result, indent=2))
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
    
    # Close client
    await client.close()
    print("✓ Connection closed")
    print()
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_ips_status())
