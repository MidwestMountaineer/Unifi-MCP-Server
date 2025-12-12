"""Demo script for DPI and alerts tools.

This script demonstrates the usage of:
- GetDPIStatsTool: Deep packet inspection statistics
- GetAlertsTool: Recent system alerts and events

Run this script to see example output from these tools.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.tools.statistics import GetDPIStatsTool, GetAlertsTool
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.config.loader import load_config


async def demo_dpi_stats():
    """Demonstrate DPI statistics tool."""
    print("\n" + "=" * 80)
    print("DPI STATISTICS TOOL DEMO")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    # Create UniFi client
    client = UniFiClient(
        config.unifi,
        server_config={
            "performance": config.server.performance,
            "diagnostics": config.server.diagnostics,
        }
    )
    
    try:
        # Connect to UniFi controller
        print("\n1. Connecting to UniFi controller...")
        await client.connect()
        print("   ✓ Connected successfully")
        
        # Create tool instance
        dpi_tool = GetDPIStatsTool()
        
        # Execute tool
        print("\n2. Fetching DPI statistics...")
        result = await dpi_tool.execute(client)
        
        if result["success"]:
            data = result["data"]
            
            print("\n3. DPI Statistics Summary:")
            print(f"   Total Traffic: {data['total_traffic']['total_bytes_formatted']}")
            print(f"   TX: {data['total_traffic']['tx_bytes_formatted']}")
            print(f"   RX: {data['total_traffic']['rx_bytes_formatted']}")
            print(f"   Applications Tracked: {len(data['categories'])}")
            
            print("\n4. Top 10 Applications by Traffic:")
            for i, app in enumerate(data['top_applications'][:10], 1):
                print(f"   {i}. {app['application']} ({app['category']})")
                print(f"      Total: {app['total_bytes_formatted']}")
                print(f"      TX: {app['tx_bytes_formatted']}, RX: {app['rx_bytes_formatted']}")
            
            # Show full JSON for reference
            print("\n5. Full JSON Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    finally:
        # Close client
        await client.close()


async def demo_alerts():
    """Demonstrate alerts tool."""
    print("\n" + "=" * 80)
    print("ALERTS TOOL DEMO")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    # Create UniFi client
    client = UniFiClient(
        config.unifi,
        server_config={
            "performance": config.server.performance,
            "diagnostics": config.server.diagnostics,
        }
    )
    
    try:
        # Connect to UniFi controller
        print("\n1. Connecting to UniFi controller...")
        await client.connect()
        print("   ✓ Connected successfully")
        
        # Create tool instance
        alerts_tool = GetAlertsTool()
        
        # Execute tool with default limit (50)
        print("\n2. Fetching recent alerts (default limit: 50)...")
        result = await alerts_tool.execute(client)
        
        if result["success"]:
            data = result["data"]
            summary = data["summary"]
            
            print("\n3. Alerts Summary:")
            print(f"   Total Available: {summary['total_available']}")
            print(f"   Returned: {summary['returned']}")
            print(f"   Unarchived: {summary['unarchived']}")
            print(f"   Archived: {summary['archived']}")
            
            print("\n4. Alert Types:")
            for alert_type, count in summary['alert_types'].items():
                print(f"   {alert_type}: {count}")
            
            print("\n5. Recent Alerts (first 5):")
            for i, alert in enumerate(data['alerts'][:5], 1):
                print(f"\n   Alert {i}:")
                print(f"   Type: {alert['key']}")
                print(f"   Message: {alert['message']}")
                print(f"   Time: {alert['timestamp']}")
                print(f"   Subsystem: {alert['subsystem']}")
                print(f"   Archived: {alert['archived']}")
                
                if 'device_name' in alert:
                    print(f"   Device: {alert['device_name']} ({alert['device_mac']})")
                if 'client_name' in alert:
                    print(f"   Client: {alert['client_name']} ({alert['client_mac']})")
            
            # Test with custom limit
            print("\n6. Fetching alerts with custom limit (10)...")
            result_limited = await alerts_tool.execute(client, limit=10)
            
            if result_limited["success"]:
                print(f"   ✓ Retrieved {len(result_limited['data']['alerts'])} alerts")
            
            # Show full JSON for reference
            print("\n7. Full JSON Response (first request):")
            print(json.dumps(result, indent=2))
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    finally:
        # Close client
        await client.close()


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("UNIFI MCP SERVER - DPI AND ALERTS TOOLS DEMO")
    print("=" * 80)
    print("\nThis demo shows the usage of DPI statistics and alerts tools.")
    print("These tools provide visibility into network traffic patterns and system events.")
    
    # Run DPI demo
    await demo_dpi_stats()
    
    # Run alerts demo
    await demo_alerts()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("1. DPI Statistics:")
    print("   - Application and category traffic breakdown")
    print("   - Top bandwidth consumers")
    print("   - Total traffic statistics")
    print("\n2. System Alerts:")
    print("   - Recent system events and alerts")
    print("   - Alert filtering and limiting")
    print("   - Alert type categorization")
    print("   - Device and client information")
    print("\nThese tools are useful for:")
    print("- Understanding network usage patterns")
    print("- Identifying bandwidth hogs")
    print("- Monitoring system health")
    print("- Tracking security events")
    print("- Troubleshooting network issues")


if __name__ == "__main__":
    asyncio.run(main())
