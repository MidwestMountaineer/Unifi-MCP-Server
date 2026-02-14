"""Tool registry for managing MCP tools.

This module provides a registry system for managing MCP tools, including:
- Tool registration (individual tools or tool groups)
- Tool discovery (get all registered tools)
- Tool invocation routing by name
- Support for tool categories/groups
- Configuration-based tool filtering

The registry acts as a central hub for all tools, making it easy to:
1. Register new tools as they are implemented
2. Filter tools based on configuration (enabled/disabled)
3. Route tool invocations to the correct handler
4. Organize tools by category for better management
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from mcp.types import Tool

from .config.loader import Config, ToolsConfig
from .utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """Definition of an MCP tool.
    
    Attributes:
        name: Tool name (should be prefixed with "unifi_")
        description: Tool description for AI agents (concise, <200 chars)
        input_schema: JSON schema for tool parameters
        handler: Async function to handle tool invocations
        category: Tool category (e.g., "network_discovery", "security")
        requires_confirmation: Whether tool requires explicit confirmation
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable
    category: str = "general"
    requires_confirmation: bool = False
    
    def to_mcp_tool(self) -> Tool:
        """Convert to MCP Tool type.
        
        Returns:
            MCP Tool object
        """
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )


class ToolRegistry:
    """Registry for managing MCP tools.
    
    The registry provides:
    - Tool registration by name
    - Tool discovery (filtered by configuration)
    - Tool invocation routing
    - Category-based organization
    - Configuration-based filtering
    
    Example:
        >>> registry = ToolRegistry(config)
        >>> 
        >>> # Register a tool
        >>> registry.register_tool(
        ...     name="unifi_list_devices",
        ...     description="List all UniFi devices",
        ...     input_schema={"type": "object", "properties": {}},
        ...     handler=list_devices_handler,
        ...     category="network_discovery"
        ... )
        >>> 
        >>> # Get available tools
        >>> tools = registry.get_tool_list()
        >>> 
        >>> # Invoke a tool
        >>> result = await registry.invoke("unifi_list_devices", unifi_client, {})
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the tool registry.
        
        Args:
            config: Optional configuration for filtering tools
        """
        self.config = config
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        
        logger.info("Tool registry initialized")
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
        category: str = "general",
        requires_confirmation: bool = False
    ) -> None:
        """Register a single tool.
        
        Args:
            name: Tool name (should be prefixed with "unifi_")
            description: Tool description for AI agents
            input_schema: JSON schema for tool parameters
            handler: Async function to handle tool invocations
            category: Tool category (e.g., "network_discovery", "security")
            requires_confirmation: Whether tool requires explicit confirmation
        
        Raises:
            ValueError: If tool name is already registered
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
        
        # Create tool definition
        tool_def = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            category=category,
            requires_confirmation=requires_confirmation
        )
        
        # Register tool
        self._tools[name] = tool_def
        
        # Add to category index
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
        
        logger.debug(
            f"Registered tool: {name}",
            extra={
                "tool_name": name,
                "category": category,
                "requires_confirmation": requires_confirmation
            }
        )
    
    def register_tools(self, tools: List[ToolDefinition]) -> None:
        """Register multiple tools at once.
        
        Args:
            tools: List of ToolDefinition objects to register
        """
        for tool_def in tools:
            self.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                input_schema=tool_def.input_schema,
                handler=tool_def.handler,
                category=tool_def.category,
                requires_confirmation=tool_def.requires_confirmation
            )
        
        logger.info(
            f"Registered {len(tools)} tools",
            extra={"count": len(tools)}
        )
    
    def register_category(
        self,
        category: str,
        tools: List[ToolDefinition]
    ) -> None:
        """Register a group of tools under a category.
        
        This is a convenience method for registering related tools together.
        
        Args:
            category: Category name (e.g., "network_discovery")
            tools: List of ToolDefinition objects in this category
        """
        for tool_def in tools:
            # Override category to ensure consistency
            self.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                input_schema=tool_def.input_schema,
                handler=tool_def.handler,
                category=category,
                requires_confirmation=tool_def.requires_confirmation
            )
        
        logger.info(
            f"Registered category '{category}' with {len(tools)} tools",
            extra={"category": category, "count": len(tools)}
        )
    
    def get_tool_list(self) -> List[Tool]:
        """Get list of all registered tools for MCP.
        
        Filters tools based on configuration (enabled/disabled).
        Returns tools in MCP Tool format.
        
        Returns:
            List of MCP Tool objects
        """
        available_tools = []
        
        for tool_name, tool_def in self._tools.items():
            # Check if tool is enabled based on configuration
            if self._is_tool_enabled(tool_def):
                available_tools.append(tool_def.to_mcp_tool())
        
        logger.debug(
            f"Returning {len(available_tools)} available tools",
            extra={
                "total_registered": len(self._tools),
                "available": len(available_tools)
            }
        )
        
        return available_tools
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category.
        
        Args:
            category: Category name
        
        Returns:
            List of MCP Tool objects in the category
        """
        if category not in self._categories:
            logger.warning(f"Category '{category}' not found")
            return []
        
        tools = []
        for tool_name in self._categories[category]:
            tool_def = self._tools[tool_name]
            if self._is_tool_enabled(tool_def):
                tools.append(tool_def.to_mcp_tool())
        
        logger.debug(
            f"Returning {len(tools)} tools in category '{category}'",
            extra={"category": category, "count": len(tools)}
        )
        
        return tools
    
    def get_categories(self) -> List[str]:
        """Get list of all registered categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    async def invoke(
        self,
        tool_name: str,
        unifi_client: Any,
        arguments: Dict[str, Any]
    ) -> Any:
        """Invoke a tool by name.
        
        Routes the tool invocation to the appropriate handler.
        Provides additional safety checks for write operations.
        
        Args:
            tool_name: Name of the tool to invoke
            unifi_client: UniFi API client instance
            arguments: Tool arguments as dictionary
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool is not found or not enabled
            TypeError: If arguments are invalid
        """
        # Check if tool exists
        if tool_name not in self._tools:
            available_tools = ", ".join(self._tools.keys())
            raise ValueError(
                f"Unknown tool: {tool_name}. "
                f"Available tools: {available_tools}"
            )
        
        tool_def = self._tools[tool_name]
        
        # Check if tool is enabled (includes write_operations.enabled check)
        if not self._is_tool_enabled(tool_def):
            # Provide specific error message for write operations
            if tool_def.requires_confirmation:
                raise ValueError(
                    f"Write operation tool '{tool_name}' is disabled. "
                    f"Set 'write_operations.enabled: true' in configuration to enable write operations."
                )
            else:
                raise ValueError(
                    f"Tool '{tool_name}' is disabled in configuration"
                )
        
        # Check confirmation requirement for write operations
        if tool_def.requires_confirmation:
            confirm = arguments.get("confirm", False)
            if not confirm:
                raise ValueError(
                    f"Tool '{tool_name}' requires explicit confirmation. "
                    f"Set 'confirm': true in the arguments to proceed."
                )
        
        logger.info(
            f"Invoking tool: {tool_name}",
            extra={
                "tool_name": tool_name,
                "category": tool_def.category,
                "is_write_operation": tool_def.requires_confirmation
            }
        )
        
        try:
            # Invoke the tool handler
            result = await tool_def.handler(unifi_client, **arguments)
            
            logger.info(
                f"Tool invocation successful: {tool_name}",
                extra={"tool_name": tool_name}
            )
            
            return result
        
        except TypeError as e:
            # Invalid arguments
            logger.error(
                f"Invalid arguments for tool '{tool_name}': {e}",
                exc_info=True
            )
            raise TypeError(
                f"Invalid arguments for tool '{tool_name}': {e}"
            )
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Tool invocation failed: {tool_name}",
                extra={
                    "tool_name": tool_name,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    def _is_tool_enabled(self, tool_def: ToolDefinition) -> bool:
        """Check if a tool is enabled based on configuration.
        
        For write operations, this also checks if write_operations.enabled is True.
        This provides an additional safety layer for tools that modify configuration.
        
        Args:
            tool_def: Tool definition to check
        
        Returns:
            True if tool is enabled, False otherwise
        """
        # If no config, all tools are enabled
        if not self.config:
            return True
        
        # Special handling for write operations
        # Write operations are filtered out if write_operations.enabled is False
        if tool_def.requires_confirmation:
            write_ops_config = self._get_category_config("write_operations")
            if write_ops_config is not None:
                # If write_operations.enabled is explicitly False, filter out all write tools
                if not write_ops_config.get("enabled", False):
                    logger.debug(
                        f"Write operation tool '{tool_def.name}' filtered out (write_operations.enabled=False)",
                        extra={"tool_name": tool_def.name, "category": tool_def.category}
                    )
                    return False
        
        # Get category configuration
        category_config = self._get_category_config(tool_def.category)
        
        # If category is not in config, assume enabled
        if category_config is None:
            return True
        
        # Check if category is enabled
        if not category_config.get("enabled", True):
            return False
        
        # Check if specific tool is in the enabled tools list
        enabled_tools = category_config.get("tools", [])
        
        # If no tools list specified, all tools in category are enabled
        if not enabled_tools:
            return True
        
        # Extract tool name without "unifi_" prefix for comparison
        tool_name_short = tool_def.name.replace("unifi_", "")
        
        # Check if tool is in the enabled list
        return tool_name_short in enabled_tools
    
    def _get_category_config(self, category: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific category.
        
        Args:
            category: Category name
        
        Returns:
            Category configuration dictionary or None if not found
        """
        if not self.config or not self.config.tools:
            return None
        
        # Map category names to config attributes
        category_map = {
            "network_discovery": self.config.tools.network_discovery,
            "security": self.config.tools.security,
            "statistics": self.config.tools.statistics,
            "migration": self.config.tools.migration,
            "write_operations": self.config.tools.write_operations,
            "firewall": self.config.tools.firewall,
            "acl": self.config.tools.acl,
            "dns": self.config.tools.dns,
            "resources": self.config.tools.resources,
        }
        
        return category_map.get(category)
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools.
        
        Returns:
            Number of registered tools
        """
        return len(self._tools)
    
    def get_enabled_tool_count(self) -> int:
        """Get number of enabled tools.
        
        Returns:
            Number of enabled tools
        """
        return len([
            tool for tool in self._tools.values()
            if self._is_tool_enabled(tool)
        ])
    
    def clear(self) -> None:
        """Clear all registered tools.
        
        This is primarily useful for testing.
        """
        self._tools.clear()
        self._categories.clear()
        logger.info("Tool registry cleared")
