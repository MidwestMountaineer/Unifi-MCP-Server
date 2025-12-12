"""MCP server implementation for UniFi Network Controller.

This module implements the core MCP server using the official Python MCP SDK.
It handles:
- MCP protocol handshake and initialization
- Tool registration and discovery (tools/list)
- Tool invocation routing (tools/call)
- Error handling and response formatting
"""

import asyncio
import logging
from functools import partial
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config.loader import Config
from .tool_registry import ToolRegistry
from .unifi_client import UniFiClient
from .utils.logging import get_logger, redact_sensitive_data


logger = get_logger(__name__)


class UniFiMCPServer:
    """MCP server for UniFi Network Controller.
    
    This class implements the MCP protocol using the official Python SDK,
    providing AI agents with access to UniFi network management capabilities.
    
    Attributes:
        config: Server configuration
        unifi_client: UniFi API client
        server: MCP Server instance
        tool_registry: Registry of available tools
    """
    
    def __init__(self, config: Config):
        """Initialize the UniFi MCP server.
        
        Args:
            config: Server configuration object
        """
        self.config = config
        self.unifi_client = UniFiClient(
            config.unifi,
            server_config={
                "performance": config.server.performance,
                "diagnostics": config.server.diagnostics,
            }
        )
        self.server = Server(config.server.name)
        self.tool_registry = ToolRegistry(config)
        
        logger.info(
            "Initializing UniFi MCP Server",
            extra={
                "server_name": config.server.name,
                "unifi_host": config.unifi.host,
                "unifi_site": config.unifi.site,
            }
        )
        
        # Register MCP protocol handlers
        self._register_handlers()
        
        # Register all available tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all available tools with the registry.
        
        This method imports and registers all tool implementations from the tools package.
        """
        from .tools.network_discovery import (
            ListDevicesTool,
            GetDeviceDetailsTool,
            ListClientsTool,
            GetClientDetailsTool,
            ListNetworksTool,
            GetNetworkDetailsTool,
            ListWLANsTool,
            GetWLANDetailsTool,
        )
        from .tools.security import (
            ListFirewallRulesTool,
            GetFirewallRuleDetailsTool,
            ListTrafficRoutesTool,
            GetRouteDetailsTool,
            ListPortForwardsTool,
            GetPortForwardDetailsTool,
            GetIPSStatusTool,
        )
        from .tools.statistics import (
            GetNetworkStatsTool,
            GetSystemHealthTool,
            GetClientStatsTool,
            GetDeviceStatsTool,
            GetTopClientsTool,
            GetDPIStatsTool,
            GetAlertsTool,
        )
        from .tools.migration import (
            GetDHCPStatusTool,
            VerifyVLANConnectivityTool,
            ExportConfigurationTool,
        )
        
        # Network Discovery Tools
        tools_to_register = [
            ListDevicesTool(),
            GetDeviceDetailsTool(),
            ListClientsTool(),
            GetClientDetailsTool(),
            ListNetworksTool(),
            GetNetworkDetailsTool(),
            ListWLANsTool(),
            GetWLANDetailsTool(),
            # Security Tools
            ListFirewallRulesTool(),
            GetFirewallRuleDetailsTool(),
            ListTrafficRoutesTool(),
            GetRouteDetailsTool(),
            ListPortForwardsTool(),
            GetPortForwardDetailsTool(),
            GetIPSStatusTool(),
            # Statistics Tools
            GetNetworkStatsTool(),
            GetSystemHealthTool(),
            GetClientStatsTool(),
            GetDeviceStatsTool(),
            GetTopClientsTool(),
            GetDPIStatsTool(),
            GetAlertsTool(),
            # Migration Tools
            GetDHCPStatusTool(),
            VerifyVLANConnectivityTool(),
            ExportConfigurationTool(),
        ]
        
        # Register each tool with a handler that matches tool_registry.invoke signature
        # The tool_registry.invoke calls: handler(unifi_client, **arguments)
        for tool in tools_to_register:
            # Use a factory function to create a proper closure
            def create_handler(tool_instance):
                async def handler(client, **kwargs):
                    return await tool_instance.invoke(client, kwargs)
                return handler
            
            self.tool_registry.register_tool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
                handler=create_handler(tool),
                category=tool.category,
                requires_confirmation=tool.requires_confirmation,
            )
        
        logger.info(
            f"Registered {len(tools_to_register)} tools",
            extra={"tool_count": len(tools_to_register)}
        )
    
    def _register_handlers(self) -> None:
        """Register MCP protocol handlers.
        
        Sets up handlers for:
        - tools/list: Return available tools
        - tools/call: Execute tool invocations
        """
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Handle tools/list requests.
            
            Returns list of all available tools based on configuration.
            Tools are filtered based on enabled/disabled settings in config.
            
            Returns:
                List of Tool objects with name, description, and input schema
            """
            logger.debug("Handling tools/list request")
            
            try:
                # Get list of enabled tools from registry
                available_tools = self.tool_registry.get_tool_list()
                
                logger.info(
                    "Returning tool list",
                    extra={
                        "tool_count": len(available_tools),
                        "total_registered": self.tool_registry.get_tool_count(),
                        "enabled": self.tool_registry.get_enabled_tool_count()
                    }
                )
                
                return available_tools
            
            except Exception as e:
                logger.error(
                    "Failed to list tools",
                    extra={"error": str(e)},
                    exc_info=True
                )
                # Return empty list on error to prevent server crash
                return []
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tools/call requests.
            
            Routes tool invocations to appropriate handlers and returns results.
            
            Args:
                name: Tool name to invoke
                arguments: Tool arguments as dictionary
            
            Returns:
                List of TextContent with tool results or error messages
            """
            # Redact sensitive data from arguments for logging
            safe_args = redact_sensitive_data(arguments)
            
            logger.info(
                "Handling tool invocation",
                extra={
                    "tool_name": name,
                    "arguments": safe_args,
                }
            )
            
            try:
                # Invoke tool through registry
                result = await self.tool_registry.invoke(
                    name,
                    self.unifi_client,
                    arguments
                )
                
                logger.info(
                    "Tool invocation successful",
                    extra={"tool_name": name}
                )
                
                # Format result as TextContent
                return [TextContent(
                    type="text",
                    text=str(result)
                )]
            
            except ValueError as e:
                # Tool not found or disabled, or missing confirmation
                error_msg = str(e)
                logger.warning(error_msg)
                return [TextContent(
                    type="text",
                    text=f"Error: {error_msg}"
                )]
            
            except TypeError as e:
                # Invalid arguments
                error_msg = f"Invalid arguments for tool '{name}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: {error_msg}"
                )]
            
            except Exception as e:
                # Unexpected error
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(
                    "Tool invocation failed",
                    extra={
                        "tool_name": name,
                        "error": str(e),
                    },
                    exc_info=True
                )
                return [TextContent(
                    type="text",
                    text=f"Error: {error_msg}"
                )]
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Any,
        category: str = "general",
        requires_confirmation: bool = False
    ) -> None:
        """Register a tool with the server.
        
        This is a convenience method that delegates to the tool registry.
        
        Args:
            name: Tool name (should be prefixed with "unifi_")
            description: Tool description for AI agents
            input_schema: JSON schema for tool parameters
            handler: Async function to handle tool invocations
            category: Tool category (e.g., "network_discovery", "security")
            requires_confirmation: Whether tool requires explicit confirmation
        """
        self.tool_registry.register_tool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            category=category,
            requires_confirmation=requires_confirmation
        )
    
    async def connect(self) -> None:
        """Connect to UniFi controller.
        
        Establishes connection and authenticates with the UniFi controller.
        Must be called before starting the server.
        
        Raises:
            Exception: If connection or authentication fails
        """
        logger.info("Connecting to UniFi controller")
        
        try:
            await self.unifi_client.connect()
            logger.info("Successfully connected to UniFi controller")
        
        except Exception as e:
            logger.error(
                "Failed to connect to UniFi controller",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from UniFi controller.
        
        Closes the connection to the UniFi controller.
        Should be called when shutting down the server.
        """
        logger.info("Disconnecting from UniFi controller")
        
        try:
            await self.unifi_client.disconnect()
            logger.info("Successfully disconnected from UniFi controller")
        
        except Exception as e:
            logger.warning(
                "Error during disconnect",
                extra={"error": str(e)},
                exc_info=True
            )
    
    async def run(self) -> None:
        """Run the MCP server.
        
        Starts the MCP server with stdio transport.
        This method blocks until the server is shut down.
        
        The server communicates via stdin/stdout using JSON-RPC protocol.
        """
        logger.info("Starting MCP server with stdio transport")
        
        try:
            # Connect to UniFi controller before starting server
            await self.connect()
            
            # Run server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server running")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        
        except Exception as e:
            logger.error(
                "Server error",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
        
        finally:
            # Ensure we disconnect on shutdown
            await self.disconnect()
            logger.info("MCP server stopped")


async def main(config: Config) -> None:
    """Main entry point for the MCP server.
    
    Args:
        config: Server configuration
    """
    server = UniFiMCPServer(config)
    await server.run()
