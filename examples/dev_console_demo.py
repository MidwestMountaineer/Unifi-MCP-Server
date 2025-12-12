"""Demo script showing how to use the dev console programmatically.

This script demonstrates:
1. Loading configuration
2. Creating a server instance
3. Using the dev console API
4. Invoking tools programmatically
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config.loader import load_config, ConfigurationError
from unifi_mcp.server import UniFiMCPServer


async def demo_programmatic_usage():
    """Demonstrate programmatic usage of the dev console."""
    
    print("=" * 70)
    print("Dev Console - Programmatic Usage Demo")
    print("=" * 70)
    
    # Load configuration
    print("\n1. Loading configuration...")
    try:
        config = load_config()
        print(f"   ✓ Connected to: {config.unifi.host}")
    except ConfigurationError as e:
        print(f"   ✗ Configuration error: {e}")
        return
    
    # Create server
    print("\n2. Creating server instance...")
    server = UniFiMCPServer(config)
    print(f"   ✓ Server created with {server.tool_registry.get_tool_count()} tools")
    
    # Connect to UniFi
    print("\n3. Connecting to UniFi controller...")
    try:
        await server.connect()
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return
    
    # List available tools
    print("\n4. Listing available tools...")
    tools = server.tool_registry.get_tool_list()
    print(f"   ✓ Found {len(tools)} enabled tools")
    
    # Show categories
    categories = server.tool_registry.get_categories()
    print(f"\n   Categories:")
    for category in sorted(categories):
        cat_tools = server.tool_registry.get_tools_by_category(category)
        print(f"     • {category}: {len(cat_tools)} tools")
    
    # Invoke a simple tool
    print("\n5. Invoking unifi_list_devices...")
    try:
        result = await server.tool_registry.invoke(
            "unifi_list_devices",
            server.unifi_client,
            {"device_type": "all"}
        )
        
        if isinstance(result, dict):
            device_count = len(result.get("devices", []))
            print(f"   ✓ Found {device_count} devices")
            
            # Show first device as example
            if result.get("devices"):
                first_device = result["devices"][0]
                print(f"\n   Example device:")
                print(f"     Name: {first_device.get('name', 'N/A')}")
                print(f"     Type: {first_device.get('type', 'N/A')}")
                print(f"     Model: {first_device.get('model', 'N/A')}")
                print(f"     Status: {first_device.get('status', 'N/A')}")
        else:
            print(f"   Result: {result}")
    
    except Exception as e:
        print(f"   ✗ Tool invocation failed: {e}")
    
    # Invoke another tool
    print("\n6. Invoking unifi_get_network_stats...")
    try:
        result = await server.tool_registry.invoke(
            "unifi_get_network_stats",
            server.unifi_client,
            {}
        )
        
        if isinstance(result, dict):
            print(f"   ✓ Network statistics retrieved")
            print(f"\n   Summary:")
            if "summary" in result:
                summary = result["summary"]
                print(f"     Total devices: {summary.get('total_devices', 'N/A')}")
                print(f"     Total clients: {summary.get('total_clients', 'N/A')}")
                print(f"     Uptime: {summary.get('uptime_display', 'N/A')}")
        else:
            print(f"   Result: {result}")
    
    except Exception as e:
        print(f"   ✗ Tool invocation failed: {e}")
    
    # Disconnect
    print("\n7. Disconnecting...")
    await server.disconnect()
    print("   ✓ Disconnected")
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)
    print("\nTo use the interactive console, run:")
    print("  python -m devtools.dev_console")
    print("=" * 70)


async def demo_interactive_simulation():
    """Simulate interactive console usage."""
    
    print("\n" + "=" * 70)
    print("Simulating Interactive Console Commands")
    print("=" * 70)
    
    # Load configuration
    try:
        config = load_config()
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        return
    
    # Create server and connect
    server = UniFiMCPServer(config)
    await server.connect()
    
    # Simulate commands
    commands = [
        ("list", "List all tools"),
        ("categories", "Show categories"),
        ("invoke unifi_list_devices", "List all devices"),
        ('invoke unifi_list_clients {"connection_type": "wireless"}', "List wireless clients"),
    ]
    
    for command, description in commands:
        print(f"\n> {command}")
        print(f"  ({description})")
        
        # Parse command
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "list":
            tools = server.tool_registry.get_tool_list()
            print(f"  → {len(tools)} tools available")
        
        elif cmd == "categories":
            categories = server.tool_registry.get_categories()
            print(f"  → {len(categories)} categories:")
            for cat in sorted(categories):
                print(f"      • {cat}")
        
        elif cmd == "invoke":
            # Parse tool name and args
            invoke_parts = args.split(maxsplit=1)
            tool_name = invoke_parts[0]
            json_args = invoke_parts[1] if len(invoke_parts) > 1 else "{}"
            
            try:
                arguments = json.loads(json_args)
                result = await server.tool_registry.invoke(
                    tool_name,
                    server.unifi_client,
                    arguments
                )
                
                if isinstance(result, dict):
                    # Show summary
                    if "devices" in result:
                        print(f"  → Found {len(result['devices'])} devices")
                    elif "clients" in result:
                        print(f"  → Found {len(result['clients'])} clients")
                    else:
                        print(f"  → Result: {list(result.keys())}")
                else:
                    print(f"  → Result: {type(result).__name__}")
            
            except Exception as e:
                print(f"  → Error: {e}")
    
    # Disconnect
    await server.disconnect()
    
    print("\n" + "=" * 70)


async def main():
    """Run all demos."""
    
    # Run programmatic demo
    await demo_programmatic_usage()
    
    # Run interactive simulation
    await demo_interactive_simulation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
