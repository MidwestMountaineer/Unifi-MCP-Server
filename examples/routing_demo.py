"""Demo script for routing and port forward tools.

This script demonstrates the usage of the routing and port forward tools
added in Task 15. It shows how to:
- List traffic routes
- Get route details
- List port forwards
- Get port forward details

Run this script to test the new tools interactively.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.tools.security import (
    ListTrafficRoutesTool,
    GetRouteDetailsTool,
    ListPortForwardsTool,
    GetPortForwardDetailsTool,
)
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.config.loader import load_config


async def demo_routing_tools():
    """Demonstrate routing and port forward tools."""
    
    print("=" * 80)
    print("UniFi MCP Server - Routing and Port Forward Tools Demo")
    print("=" * 80)
    print()
    
    # Load configuration
    print("Loading configuration...")
    try:
        config = load_config()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return
    
    print()
    
    # Create UniFi client
    print("Connecting to UniFi controller...")
    client = UniFiClient(config.unifi)
    
    try:
        await client.connect()
        print(f"✓ Connected to {config.unifi.host}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    print()
    print("=" * 80)
    
    # Demo 1: List Traffic Routes
    print("\n1. LIST TRAFFIC ROUTES")
    print("-" * 80)
    
    list_routes_tool = ListTrafficRoutesTool()
    
    try:
        result = await list_routes_tool.invoke(client, {})
        
        if result.get("success"):
            routes = result["data"]
            total = result.get("total", len(routes))
            
            print(f"Found {total} traffic route(s)")
            print()
            
            if routes:
                for i, route in enumerate(routes, 1):
                    print(f"Route {i}:")
                    print(f"  ID: {route['id']}")
                    print(f"  Name: {route['name']}")
                    print(f"  Enabled: {route['enabled']}")
                    print(f"  Type: {route['type']}")
                    print(f"  Destination: {route['destination_network']}")
                    print(f"  Next Hop: {route['next_hop']}")
                    print(f"  Distance: {route['distance']}")
                    print(f"  Interface: {route['interface']}")
                    print()
            else:
                print("No traffic routes configured")
        else:
            print(f"Error: {result.get('error', {}).get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error listing routes: {e}")
    
    # Demo 2: Get Route Details (if routes exist)
    print("\n2. GET ROUTE DETAILS")
    print("-" * 80)
    
    get_route_tool = GetRouteDetailsTool()
    
    try:
        # First get the list to find a route ID
        result = await list_routes_tool.invoke(client, {})
        
        if result.get("success") and result["data"]:
            route_id = result["data"][0]["id"]
            print(f"Getting details for route: {route_id}")
            print()
            
            details_result = await get_route_tool.invoke(client, {"route_id": route_id})
            
            if details_result.get("success"):
                route = details_result["data"]
                print("Route Details:")
                print(json.dumps(route, indent=2))
            else:
                print(f"Error: {details_result.get('error', {}).get('message', 'Unknown error')}")
        else:
            print("No routes available to get details for")
    
    except Exception as e:
        print(f"Error getting route details: {e}")
    
    # Demo 3: List Port Forwards
    print("\n3. LIST PORT FORWARDS")
    print("-" * 80)
    
    list_forwards_tool = ListPortForwardsTool()
    
    try:
        result = await list_forwards_tool.invoke(client, {})
        
        if result.get("success"):
            forwards = result["data"]
            total = result.get("total", len(forwards))
            
            print(f"Found {total} port forward(s)")
            print()
            
            if forwards:
                for i, forward in enumerate(forwards, 1):
                    print(f"Port Forward {i}:")
                    print(f"  ID: {forward['id']}")
                    print(f"  Name: {forward['name']}")
                    print(f"  Enabled: {forward['enabled']}")
                    print(f"  Protocol: {forward['protocol']}")
                    print(f"  External Port: {forward['external_port']}")
                    print(f"  Destination: {forward['destination_ip']}:{forward['destination_port']}")
                    print(f"  Source: {forward['source']}")
                    print(f"  Logging: {forward['log']}")
                    print()
            else:
                print("No port forwards configured")
        else:
            print(f"Error: {result.get('error', {}).get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error listing port forwards: {e}")
    
    # Demo 4: Get Port Forward Details (if forwards exist)
    print("\n4. GET PORT FORWARD DETAILS")
    print("-" * 80)
    
    get_forward_tool = GetPortForwardDetailsTool()
    
    try:
        # First get the list to find a forward ID
        result = await list_forwards_tool.invoke(client, {})
        
        if result.get("success") and result["data"]:
            forward_id = result["data"][0]["id"]
            print(f"Getting details for port forward: {forward_id}")
            print()
            
            details_result = await get_forward_tool.invoke(client, {"forward_id": forward_id})
            
            if details_result.get("success"):
                forward = details_result["data"]
                print("Port Forward Details:")
                print(json.dumps(forward, indent=2))
            else:
                print(f"Error: {details_result.get('error', {}).get('message', 'Unknown error')}")
        else:
            print("No port forwards available to get details for")
    
    except Exception as e:
        print(f"Error getting port forward details: {e}")
    
    # Demo 5: Filter enabled only
    print("\n5. LIST ENABLED PORT FORWARDS ONLY")
    print("-" * 80)
    
    try:
        result = await list_forwards_tool.invoke(client, {"enabled_only": True})
        
        if result.get("success"):
            forwards = result["data"]
            total = result.get("total", len(forwards))
            
            print(f"Found {total} enabled port forward(s)")
            print()
            
            if forwards:
                for i, forward in enumerate(forwards, 1):
                    print(f"{i}. {forward['name']} - {forward['protocol']} "
                          f"{forward['external_port']} → "
                          f"{forward['destination_ip']}:{forward['destination_port']}")
            else:
                print("No enabled port forwards")
        else:
            print(f"Error: {result.get('error', {}).get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error listing enabled port forwards: {e}")
    
    print()
    print("=" * 80)
    print("Demo completed!")
    print("=" * 80)
    
    # Close client
    await client.close()


if __name__ == "__main__":
    asyncio.run(demo_routing_tools())
