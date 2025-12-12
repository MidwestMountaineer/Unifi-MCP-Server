"""UniFi MCP tools package.

This package contains all MCP tools organized by category:
- base: Base tool class and utilities
- network_discovery: Device and client discovery tools
- security: Firewall and security tools
- statistics: Network statistics and monitoring tools
- migration: Migration support tools (future)
- write_operations: Write operation tools (future)
"""

from .base import BaseTool, ToolError
from .network_discovery import ListDevicesTool, GetDeviceDetailsTool
from .statistics import GetNetworkStatsTool, GetSystemHealthTool


__all__ = [
    "BaseTool",
    "ToolError",
    "ListDevicesTool",
    "GetDeviceDetailsTool",
    "GetNetworkStatsTool",
    "GetSystemHealthTool",
]
