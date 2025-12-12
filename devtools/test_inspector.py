"""Quick test script to validate MCP Inspector integration."""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config


async def test_validation():
    """Test protocol compliance validation."""
    print("\n=== Testing Protocol Compliance ===\n")
    
    try:
        # Load config
        config = load_config()
        print("✓ Configuration loaded successfully")
        
        # Initialize server
        server = UniFiMCPServer(config)
        print("✓ Server initialization successful")
        
        # Test tool listing via registry
        tools = server.tool_registry.get_tool_list()
        print(f"✓ Tool listing successful ({len(tools)} tools)")
        
        # Validate tool schemas
        errors = []
        for tool in tools:
            # Convert Tool object to dict for validation
            tool_dict = {
                'name': tool.name,
                'description': tool.description,
                'inputSchema': tool.inputSchema
            }
            
            if not tool_dict.get('name'):
                errors.append(f"Tool missing name: {tool_dict}")
            if not tool_dict.get('description'):
                errors.append(f"Tool missing description: {tool_dict.get('name', 'unknown')}")
            if not tool_dict.get('inputSchema'):
                errors.append(f"Tool missing inputSchema: {tool_dict.get('name', 'unknown')}")
        
        if errors:
            print("\n✗ Schema validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print(f"✓ All tool schemas valid")
        print(f"\n✓ Protocol compliance validation PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_tools():
    """List all available tools."""
    print("\n=== Listing Available Tools ===\n")
    
    try:
        config = load_config()
        server = UniFiMCPServer(config)
        tools = server.tool_registry.get_tool_list()
        
        # Simple list without categories (since we don't have get_tool_info)
        print("AVAILABLE TOOLS:")
        for tool in sorted(tools, key=lambda t: t.name):
            print(f"  - {tool.name}")
            print(f"    {tool.description}")
        print()
        
        print(f"Total: {len(tools)} tools")
        return True
        
    except Exception as e:
        print(f"✗ Failed to list tools: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  UniFi MCP Server - Inspector Integration Test")
    print("="*60)
    
    # Test validation
    validation_passed = await test_validation()
    
    # Test tool listing
    listing_passed = await test_list_tools()
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    print(f"Protocol Compliance: {'✓ PASSED' if validation_passed else '✗ FAILED'}")
    print(f"Tool Listing:        {'✓ PASSED' if listing_passed else '✗ FAILED'}")
    print("="*60 + "\n")
    
    return validation_passed and listing_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
