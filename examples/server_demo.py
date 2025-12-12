"""Demo script showing UniFi MCP Server initialization and basic usage.

This script demonstrates:
1. Loading configuration
2. Creating the MCP server
3. Registering a simple tool
4. Server lifecycle management

Note: This is a demonstration only. The actual server runs via stdio transport
and communicates using JSON-RPC protocol with MCP clients.
"""

import asyncio
from unifi_mcp import load_config, UniFiMCPServer


async def example_tool_handler(client, device_type: str = "all"):
    """Example tool handler that would list devices.
    
    Args:
        client: UniFi client instance
        device_type: Type of devices to list
    
    Returns:
        Example result string
    """
    return f"Listing devices of type: {device_type}"


async def main():
    """Demonstrate server initialization and tool registration."""
    print("=" * 60)
    print("UniFi MCP Server - Initialization Demo")
    print("=" * 60)
    
    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Configuration loaded")
        print(f"   - Server name: {config.server.name}")
        print(f"   - UniFi host: {config.unifi.host}")
        print(f"   - UniFi site: {config.unifi.site}")
        
        # Create server
        print("\n2. Creating MCP server...")
        server = UniFiMCPServer(config)
        print(f"   ✓ Server created")
        
        # Register example tool
        print("\n3. Registering example tool...")
        server.register_tool(
            name="unifi_list_devices",
            description="List all UniFi devices",
            input_schema={
                "type": "object",
                "properties": {
                    "device_type": {
                        "type": "string",
                        "enum": ["all", "switch", "ap", "gateway"],
                        "description": "Filter by device type"
                    }
                }
            },
            handler=example_tool_handler
        )
        print(f"   ✓ Tool registered: unifi_list_devices")
        
        # Show registered tools
        print("\n4. Registered tools:")
        for tool_name in server.tools.keys():
            print(f"   - {tool_name}")
        
        # Test tool invocation (without actually connecting)
        print("\n5. Testing tool invocation (mock)...")
        result = await server.tools["unifi_list_devices"](None, device_type="switch")
        print(f"   ✓ Tool result: {result}")
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        print("\nTo run the actual server:")
        print("  python -m unifi_mcp")
        print("\nOr via uvx (for MCP clients):")
        print("  uvx unifi-mcp-server")
        print("\n")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
