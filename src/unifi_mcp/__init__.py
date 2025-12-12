"""UniFi MCP Server - Model Context Protocol server for UniFi Network Controller.

This package provides an MCP server that exposes UniFi Network Controller
capabilities to AI agents through a well-designed tool interface.
"""

from .config.loader import Config, ConfigurationError, load_config
from .server import UniFiMCPServer
from .unifi_client import UniFiClient

__version__ = "0.1.0"

__all__ = [
    "Config",
    "ConfigurationError",
    "load_config",
    "UniFiMCPServer",
    "UniFiClient",
]
