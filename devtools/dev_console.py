"""Developer testing console for UniFi MCP Server.

This interactive console allows developers to:
- List all available tools
- Invoke tools with custom arguments
- View formatted results
- Test tool behavior without MCP client
- Load credentials from .env file

Usage:
    python -m devtools.dev_console

Commands:
    list                    - List all available tools
    list <category>         - List tools in a specific category
    invoke <tool> [args]    - Invoke a tool with JSON arguments
    help                    - Show help message
    exit                    - Exit the console
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config.loader import load_config, ConfigurationError
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.utils.logging import get_logger


logger = get_logger(__name__)


class DevConsole:
    """Interactive developer console for testing MCP tools.
    
    Provides a command-line interface for:
    - Listing available tools
    - Invoking tools with custom arguments
    - Viewing formatted results
    - Testing without MCP client
    """
    
    def __init__(self, server: UniFiMCPServer):
        """Initialize the dev console.
        
        Args:
            server: UniFi MCP server instance
        """
        self.server = server
        self.running = False
    
    async def start(self) -> None:
        """Start the interactive console."""
        self.running = True
        
        # Connect to UniFi controller
        try:
            await self.server.connect()
            print("✓ Connected to UniFi controller")
        except Exception as e:
            print(f"✗ Failed to connect to UniFi controller: {e}")
            print("  Check your credentials and network connection")
            return
        
        # Print welcome message
        self._print_welcome()
        
        # Main command loop
        while self.running:
            try:
                # Get user input
                command = input("\n> ").strip()
                
                if not command:
                    continue
                
                # Parse and execute command
                await self._execute_command(command)
            
            except KeyboardInterrupt:
                print("\n\nUse 'exit' to quit")
            
            except EOFError:
                break
            
            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Command execution error: {e}", exc_info=True)
        
        # Disconnect from UniFi controller
        await self.server.disconnect()
        print("\n✓ Disconnected from UniFi controller")
    
    def _print_welcome(self) -> None:
        """Print welcome message and help."""
        print("\n" + "=" * 70)
        print("  UniFi MCP Server - Developer Console")
        print("=" * 70)
        print("\nCommands:")
        print("  list                    - List all available tools")
        print("  list <category>         - List tools in a specific category")
        print("  categories              - List all tool categories")
        print("  invoke <tool> [args]    - Invoke a tool with JSON arguments")
        print("  help                    - Show this help message")
        print("  exit                    - Exit the console")
        print("\nExamples:")
        print('  invoke unifi_list_devices {"device_type": "switch"}')
        print('  invoke unifi_get_device_details {"device_id": "abc123"}')
        print('  invoke unifi_list_clients')
        print("=" * 70)
    
    async def _execute_command(self, command: str) -> None:
        """Execute a console command.
        
        Args:
            command: Command string to execute
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "exit" or cmd == "quit":
            self.running = False
            print("Goodbye!")
        
        elif cmd == "help":
            self._print_welcome()
        
        elif cmd == "list":
            await self._list_tools(args)
        
        elif cmd == "categories":
            self._list_categories()
        
        elif cmd == "invoke":
            await self._invoke_tool(args)
        
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")
    
    async def _list_tools(self, category: str = "") -> None:
        """List available tools.
        
        Args:
            category: Optional category filter
        """
        if category:
            # List tools in specific category
            tools = self.server.tool_registry.get_tools_by_category(category)
            if not tools:
                print(f"No tools found in category: {category}")
                return
            
            print(f"\nTools in category '{category}':")
        else:
            # List all tools
            tools = self.server.tool_registry.get_tool_list()
            print(f"\nAvailable tools ({len(tools)} total):")
        
        # Group tools by category for display
        tools_by_category: Dict[str, list] = {}
        for tool in tools:
            # Get tool definition to access category
            tool_def = self.server.tool_registry._tools.get(tool.name)
            if tool_def:
                cat = tool_def.category
                if cat not in tools_by_category:
                    tools_by_category[cat] = []
                tools_by_category[cat].append(tool)
        
        # Print tools grouped by category
        for cat, cat_tools in sorted(tools_by_category.items()):
            print(f"\n  [{cat}]")
            for tool in sorted(cat_tools, key=lambda t: t.name):
                # Check if tool requires confirmation
                tool_def = self.server.tool_registry._tools.get(tool.name)
                confirm_marker = " [REQUIRES CONFIRMATION]" if tool_def and tool_def.requires_confirmation else ""
                print(f"    • {tool.name}{confirm_marker}")
                print(f"      {tool.description}")
    
    def _list_categories(self) -> None:
        """List all tool categories."""
        categories = self.server.tool_registry.get_categories()
        print(f"\nTool categories ({len(categories)} total):")
        for category in sorted(categories):
            # Count tools in category
            tools = self.server.tool_registry.get_tools_by_category(category)
            print(f"  • {category} ({len(tools)} tools)")
    
    async def _invoke_tool(self, args: str) -> None:
        """Invoke a tool with arguments.
        
        Args:
            args: Tool name and optional JSON arguments
        """
        if not args:
            print("Usage: invoke <tool_name> [json_arguments]")
            print('Example: invoke unifi_list_devices {"device_type": "switch"}')
            return
        
        # Parse tool name and arguments
        parts = args.split(maxsplit=1)
        tool_name = parts[0]
        json_args = parts[1] if len(parts) > 1 else "{}"
        
        # Parse JSON arguments
        try:
            arguments = json.loads(json_args)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON arguments: {e}")
            print("Arguments must be valid JSON")
            return
        
        # Check if tool exists
        if tool_name not in self.server.tool_registry._tools:
            print(f"Unknown tool: {tool_name}")
            print("Use 'list' to see available tools")
            return
        
        # Show invocation details
        print(f"\nInvoking: {tool_name}")
        if arguments:
            print(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        # Invoke tool
        try:
            result = await self.server.tool_registry.invoke(
                tool_name,
                self.server.unifi_client,
                arguments
            )
            
            # Format and display result
            print("\n" + "-" * 70)
            print("Result:")
            print("-" * 70)
            self._print_result(result)
            print("-" * 70)
        
        except ValueError as e:
            print(f"\n✗ Error: {e}")
        
        except Exception as e:
            print(f"\n✗ Tool execution failed: {e}")
            logger.error(f"Tool invocation error: {e}", exc_info=True)
    
    def _print_result(self, result: Any) -> None:
        """Print formatted result.
        
        Args:
            result: Tool result to print
        """
        if isinstance(result, dict):
            # Pretty print JSON
            print(json.dumps(result, indent=2))
        elif isinstance(result, list):
            # Print list items
            if not result:
                print("(empty list)")
            else:
                for i, item in enumerate(result, 1):
                    if isinstance(item, dict):
                        print(f"\n[{i}]")
                        print(json.dumps(item, indent=2))
                    else:
                        print(f"  {i}. {item}")
        else:
            # Print as string
            print(str(result))


async def main() -> None:
    """Main entry point for dev console."""
    print("Loading configuration...")
    
    try:
        # Load configuration from .env and config.yaml
        config = load_config()
        print("✓ Configuration loaded")
    
    except ConfigurationError as e:
        print(f"✗ Configuration error: {e}")
        print("\nMake sure you have:")
        print("  1. Created a .env file with your UniFi credentials")
        print("  2. Set UNIFI_HOST, and either UNIFI_API_KEY or UNIFI_USERNAME/UNIFI_PASSWORD")
        print("\nSee .env.example for reference")
        return
    
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return
    
    # Create server instance
    print("Initializing server...")
    server = UniFiMCPServer(config)
    print("✓ Server initialized")
    
    # Start console
    console = DevConsole(server)
    await console.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
