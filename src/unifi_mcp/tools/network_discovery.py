"""Network discovery tools for UniFi MCP server.

This module provides tools for discovering and inspecting network devices and clients:
- List all UniFi devices (switches, APs, gateways) with filtering
- Get detailed information about specific devices
- List all connected clients with connection type filtering
- Get detailed information about specific clients
- Format device and client data for AI consumption (summary vs detail views)
- Support pagination for large device and client lists

These tools are read-only and provide network visibility without
making any changes to the infrastructure.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListDevicesTool(BaseTool):
    """List all UniFi devices with optional filtering.
    
    This tool retrieves all UniFi devices (switches, access points, gateways)
    from the controller and provides summary information optimized for AI
    consumption. Supports filtering by device type and pagination for large
    deployments.
    
    Example usage:
        - "List all devices on my network"
        - "Show me all access points"
        - "What switches do I have?"
    """
    
    name = "unifi_list_devices"
    description = "List all UniFi devices (switches, APs, gateways) with optional filtering"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "device_type": {
                "type": "string",
                "enum": ["all", "switch", "ap", "gateway", "usw", "uap", "ugw"],
                "description": "Filter by device type (all, switch, ap, gateway)",
                "default": "all"
            },
            "page": {
                "type": "integer",
                "description": "Page number for pagination (1-indexed)",
                "minimum": 1,
                "default": 1
            },
            "page_size": {
                "type": "integer",
                "description": "Number of devices per page",
                "minimum": 1,
                "maximum": 500,
                "default": 50
            },
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        device_type: str = "all",
        page: int = 1,
        page_size: int = 50,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list devices tool.
        
        Args:
            unifi_client: UniFi API client
            device_type: Filter by device type (all, switch, ap, gateway)
            page: Page number for pagination
            page_size: Number of devices per page
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of devices with pagination info
        """
        try:
            # Fetch devices from UniFi controller via v1 API
            logger.info(
                f"Fetching devices (type={device_type}, page={page}, page_size={page_size})"
            )
            
            # Handle 'filter' kwarg from MCP input schema
            if filter_expr is None and "filter" in kwargs:
                filter_expr = kwargs.pop("filter")

            params: Dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_expr is not None:
                params["filter"] = filter_expr

            response = await unifi_client.get_v1(
                "devices", params=params if params else None
            )
            
            # Extract device data from v1 response envelope
            devices = response.get("data", [])
            total_count = response.get("totalCount", len(devices))
            
            logger.debug(f"Retrieved {len(devices)} devices from controller (totalCount={total_count})")
            
            # Filter by device type if specified
            if device_type != "all":
                devices = self._filter_by_type(devices, device_type)
                logger.debug(f"Filtered to {len(devices)} devices of type '{device_type}'")
            
            # Format devices for AI consumption (summary view)
            formatted_devices = [
                self._format_device_summary(device)
                for device in devices
            ]
            
            # Apply pagination
            paginated_devices, total = self.paginate(formatted_devices, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_devices)} devices "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            return self.format_list(
                items=paginated_devices,
                total=total,
                page=page,
                page_size=page_size
            )
        
        except Exception as e:
            logger.error(f"Failed to list devices: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve device list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _filter_by_type(
        self,
        devices: List[Dict[str, Any]],
        device_type: str
    ) -> List[Dict[str, Any]]:
        """Filter devices by type.
        
        Args:
            devices: List of device dictionaries
            device_type: Type to filter by (switch, ap, gateway, usw, uap, ugw)
        
        Returns:
            Filtered list of devices
        """
        # Normalize device type
        type_map = {
            "switch": ["usw"],
            "ap": ["uap", "u7p"],
            "gateway": ["ugw", "udm", "uxg"],
            "usw": ["usw"],
            "uap": ["uap", "u7p"],
            "ugw": ["ugw", "udm", "uxg"],
        }
        
        allowed_types = type_map.get(device_type.lower(), [device_type.lower()])
        
        return [
            device for device in devices
            if any(device.get("type", "").lower().startswith(t) for t in allowed_types)
        ]
    
    def _format_device_summary(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Format device data for summary view (AI-friendly).
        
        Extracts only the most relevant fields for AI consumption,
        avoiding overwhelming the context window with unnecessary data.
        Handles both v1 and legacy field names gracefully.
        
        Args:
            device: Raw device data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted device summary
        """
        # Handle state field: v1 uses "ONLINE"/"OFFLINE" strings, legacy uses 1/0 integers
        state = device.get("state", 0)
        if isinstance(state, str):
            status = "online" if state.upper() == "ONLINE" else "offline"
        else:
            status = "online" if state == 1 else "offline"
        
        return {
            "id": device.get("id", device.get("_id", "")),
            "mac": device.get("mac", ""),
            "name": device.get("name", device.get("hostname", "Unknown")),
            "type": self._get_device_type_friendly(device.get("type", "")),
            "model": device.get("model", ""),
            "ip": device.get("ip", ""),
            "status": status,
            "uptime": device.get("uptime", 0),
            "version": device.get("version", ""),
            "adopted": device.get("adopted", False),
        }
    
    def _get_device_type_friendly(self, device_type: str) -> str:
        """Convert UniFi device type to friendly name.
        
        Args:
            device_type: UniFi device type code (e.g., "usw", "uap")
        
        Returns:
            Friendly device type name
        """
        type_map = {
            "usw": "switch",
            "uap": "access_point",
            "u7p": "access_point",
            "ugw": "gateway",
            "udm": "dream_machine",
            "uxg": "gateway",
        }
        
        for prefix, friendly_name in type_map.items():
            if device_type.lower().startswith(prefix):
                return friendly_name
        
        return device_type


class GetDeviceDetailsTool(BaseTool):
    """Get detailed information about a specific device.
    
    This tool retrieves comprehensive information about a single UniFi device
    including configuration, statistics, and status. Use this after listing
    devices to get full details about a specific device.
    
    Example usage:
        - "Show me details for device abc123"
        - "What's the status of my main switch?"
        - "Get full information for the living room AP"
    """
    
    name = "unifi_get_device_details"
    description = "Get detailed information about a specific UniFi device"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "Device ID or MAC address"
            }
        },
        "required": ["device_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        device_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get device details tool.
        
        Args:
            unifi_client: UniFi API client
            device_id: Device ID or MAC address
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted device details
        """
        try:
            logger.info(f"Fetching details for device: {device_id}")
            
            # Try direct v1 lookup by device ID first
            device = None
            try:
                response = await unifi_client.get_v1(f"devices/{device_id}")
                # v1 may return device directly or wrapped in data
                if "data" in response and isinstance(response["data"], list):
                    devices = response["data"]
                    device = devices[0] if devices else None
                elif "data" in response and isinstance(response["data"], dict):
                    device = response["data"]
                else:
                    # Response is the device itself
                    device = response
            except Exception as lookup_err:
                logger.debug(f"Direct v1 lookup failed for '{device_id}': {lookup_err}")
                # Fallback: fetch all devices and search by ID or MAC
                device = await self._find_device_fallback(unifi_client, device_id)
            
            if not device:
                raise ToolError(
                    code="DEVICE_NOT_FOUND",
                    message=f"Device not found: {device_id}",
                    details=f"No device found with ID or MAC address '{device_id}'",
                    actionable_steps=[
                        "Verify the device ID or MAC address is correct",
                        "Use unifi_list_devices to see available devices",
                        "Check if the device is adopted and online"
                    ]
                )
            
            # Format device details for AI consumption
            formatted_device = self._format_device_details(device)
            
            logger.info(f"Retrieved details for device: {formatted_device['name']}")
            
            return self.format_detail(
                item=formatted_device,
                item_type="device"
            )
        
        except ToolError:
            raise
        
        except Exception as e:
            logger.error(f"Failed to get device details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve device details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the device ID is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_device(
        self,
        devices: List[Dict[str, Any]],
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a device by ID or MAC address.
        
        Handles both v1 (id) and legacy (_id) field names.
        
        Args:
            devices: List of device dictionaries
            device_id: Device ID or MAC address to search for
        
        Returns:
            Device dictionary if found, None otherwise
        """
        device_id_lower = device_id.lower()
        
        for device in devices:
            # Check v1 ID field
            if device.get("id", "").lower() == device_id_lower:
                return device
            
            # Check legacy ID field
            if device.get("_id", "").lower() == device_id_lower:
                return device
            
            # Check MAC address (with or without colons)
            mac = device.get("mac", "").lower().replace(":", "")
            search_mac = device_id_lower.replace(":", "")
            
            if mac == search_mac:
                return device
        
        return None
    
    async def _find_device_fallback(
        self,
        unifi_client: UniFiClient,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fallback: fetch all devices via v1 API and search by ID or MAC.
        
        Used when direct v1 lookup by ID fails (e.g., when searching by MAC).
        
        Args:
            unifi_client: UniFi API client
            device_id: Device ID or MAC address to search for
        
        Returns:
            Device dictionary if found, None otherwise
        """
        response = await unifi_client.get_v1("devices")
        devices = response.get("data", [])
        return self._find_device(devices, device_id)
    
    def _format_device_details(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Format device data for detailed view (AI-friendly).
        
        Includes more comprehensive information than the summary view,
        but still filters out unnecessary fields to keep context window
        usage reasonable. Handles both v1 and legacy field names.
        
        Args:
            device: Raw device data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted device details
        """
        # Handle state field: v1 uses "ONLINE"/"OFFLINE" strings, legacy uses 1/0 integers
        state = device.get("state", 0)
        if isinstance(state, str):
            status = "online" if state.upper() == "ONLINE" else "offline"
        else:
            status = "online" if state == 1 else "offline"
        
        # Basic information
        details = {
            "id": device.get("id", device.get("_id", "")),
            "mac": device.get("mac", ""),
            "name": device.get("name", device.get("hostname", "Unknown")),
            "type": self._get_device_type_friendly(device.get("type", "")),
            "model": device.get("model", ""),
            "model_name": device.get("model_name", device.get("modelName", "")),
            
            # Network information
            "ip": device.get("ip", ""),
            "netmask": device.get("netmask", ""),
            "gateway": device.get("gateway", ""),
            
            # Status
            "status": status,
            "adopted": device.get("adopted", False),
            "uptime": device.get("uptime", 0),
            "uptime_readable": self._format_uptime(device.get("uptime", 0)),
            
            # Version information
            "version": device.get("version", device.get("firmwareVersion", "")),
            "upgradable": device.get("upgradable", False),
            "upgrade_to_version": device.get("upgrade_to_firmware", ""),
            
            # Hardware information
            "serial": device.get("serial", ""),
            "board_rev": device.get("board_rev", device.get("boardRevision", "")),
            
            # Statistics
            "cpu_usage": device.get("system-stats", {}).get("cpu", 0),
            "memory_usage": device.get("system-stats", {}).get("mem", 0),
            "uplink": self._format_uplink(device.get("uplink", {})),
        }
        
        # Add port information for switches
        if device.get("type", "").lower().startswith("usw"):
            details["ports"] = self._format_ports(device.get("port_table", []))
            details["port_count"] = len(device.get("port_table", []))
        
        # Add radio information for access points
        if device.get("type", "").lower().startswith("uap") or device.get("type", "").lower().startswith("u7p"):
            details["radios"] = self._format_radios(device.get("radio_table", []))
            details["client_count"] = device.get("num_sta", 0)
        
        return details
    
    def _get_device_type_friendly(self, device_type: str) -> str:
        """Convert UniFi device type to friendly name.
        
        Args:
            device_type: UniFi device type code
        
        Returns:
            Friendly device type name
        """
        type_map = {
            "usw": "switch",
            "uap": "access_point",
            "u7p": "access_point",
            "ugw": "gateway",
            "udm": "dream_machine",
            "uxg": "gateway",
        }
        
        for prefix, friendly_name in type_map.items():
            if device_type.lower().startswith(prefix):
                return friendly_name
        
        return device_type
    
    def _format_uptime(self, uptime_seconds: int) -> str:
        """Format uptime in human-readable format.
        
        Args:
            uptime_seconds: Uptime in seconds
        
        Returns:
            Human-readable uptime string
        """
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    def _format_uplink(self, uplink: Dict[str, Any]) -> Dict[str, Any]:
        """Format uplink information.
        
        Args:
            uplink: Raw uplink data
        
        Returns:
            Formatted uplink information
        """
        if not uplink:
            return {}
        
        return {
            "type": uplink.get("type", ""),
            "uplink_mac": uplink.get("uplink_mac", ""),
            "uplink_device_name": uplink.get("uplink_device_name", ""),
            "port_idx": uplink.get("port_idx", ""),
            "speed": uplink.get("speed", 0),
            "full_duplex": uplink.get("full_duplex", False),
        }
    
    def _format_ports(self, ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format switch port information.
        
        Args:
            ports: Raw port data
        
        Returns:
            Formatted port information (summary)
        """
        formatted_ports = []
        
        for port in ports:
            # Only include ports with interesting information
            if port.get("port_idx") is not None:
                formatted_ports.append({
                    "port_idx": port.get("port_idx", 0),
                    "name": port.get("name", f"Port {port.get('port_idx', 0)}"),
                    "enabled": port.get("enable", False),
                    "up": port.get("up", False),
                    "speed": port.get("speed", 0),
                    "full_duplex": port.get("full_duplex", False),
                    "poe_enable": port.get("poe_enable", False),
                    "poe_power": port.get("poe_power", 0),
                })
        
        return formatted_ports
    
    def _format_radios(self, radios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format access point radio information.
        
        Args:
            radios: Raw radio data
        
        Returns:
            Formatted radio information
        """
        formatted_radios = []
        
        for radio in radios:
            formatted_radios.append({
                "name": radio.get("name", ""),
                "radio": radio.get("radio", ""),
                "channel": radio.get("channel", 0),
                "tx_power": radio.get("tx_power", 0),
                "num_sta": radio.get("num_sta", 0),
            })
        
        return formatted_radios



class ListPendingDevicesTool(BaseTool):
    """List devices pending adoption.
    
    This tool retrieves devices that have been discovered but not yet
    adopted into the UniFi network. Useful for identifying new hardware
    that needs to be set up.
    
    Example usage:
        - "Are there any devices waiting to be adopted?"
        - "Show me pending devices"
    """
    
    name = "unifi_list_pending_devices"
    description = "List UniFi devices pending adoption"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list pending devices tool.
        
        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of pending devices
        """
        try:
            logger.info("Fetching pending devices")
            
            # Handle 'filter' kwarg from MCP input schema
            if filter_expr is None and "filter" in kwargs:
                filter_expr = kwargs.pop("filter")

            params: Dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_expr is not None:
                params["filter"] = filter_expr

            response = await unifi_client.get_v1(
                "devices/pending", params=params if params else None
            )
            
            # Extract device data from v1 response envelope
            devices = response.get("data", [])
            total_count = response.get("totalCount", len(devices))
            
            logger.debug(f"Retrieved {len(devices)} pending devices (totalCount={total_count})")
            
            # Format pending devices for AI consumption
            formatted_devices = [
                self._format_pending_device(device)
                for device in devices
            ]
            
            logger.info(f"Returning {len(formatted_devices)} pending devices")
            
            return self.format_list(
                items=formatted_devices,
                total=len(formatted_devices),
                page=1,
                page_size=len(formatted_devices) or 1
            )
        
        except Exception as e:
            logger.error(f"Failed to list pending devices: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve pending device list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_pending_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Format pending device data for summary view.
        
        Args:
            device: Raw pending device data from UniFi v1 API
        
        Returns:
            Formatted pending device summary
        """
        return {
            "id": device.get("id", device.get("_id", "")),
            "mac": device.get("mac", ""),
            "name": device.get("name", device.get("model", "Unknown")),
            "model": device.get("model", ""),
            "type": device.get("type", ""),
        }


class ListClientsTool(BaseTool):
    """List all connected clients with optional filtering.
    
    This tool retrieves all clients connected to the UniFi network
    (both wired and wireless) and provides summary information optimized
    for AI consumption. Supports filtering by connection type and pagination
    for large networks.
    
    Example usage:
        - "List all connected clients"
        - "Show me all wireless clients"
        - "What wired devices are connected?"
    """
    
    name = "unifi_list_clients"
    description = "List all connected clients across the network with optional filtering"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "connection_type": {
                "type": "string",
                "enum": ["all", "wired", "wireless"],
                "description": "Filter by connection type (all, wired, wireless)",
                "default": "all"
            },
            "page": {
                "type": "integer",
                "description": "Page number for pagination (1-indexed)",
                "minimum": 1,
                "default": 1
            },
            "page_size": {
                "type": "integer",
                "description": "Number of clients per page",
                "minimum": 1,
                "maximum": 500,
                "default": 50
            },
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        connection_type: str = "all",
        page: int = 1,
        page_size: int = 50,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list clients tool.
        
        Args:
            unifi_client: UniFi API client
            connection_type: Filter by connection type (all, wired, wireless)
            page: Page number for pagination
            page_size: Number of clients per page
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of clients with pagination info
        """
        try:
            # Fetch clients from UniFi controller via v1 API
            logger.info(
                f"Fetching clients (type={connection_type}, page={page}, page_size={page_size})"
            )
            
            # Handle 'filter' kwarg from MCP input schema
            if filter_expr is None and "filter" in kwargs:
                filter_expr = kwargs.pop("filter")

            params: Dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_expr is not None:
                params["filter"] = filter_expr

            response = await unifi_client.get_v1(
                "clients", params=params if params else None
            )
            
            # Extract client data from v1 response envelope
            clients = response.get("data", [])
            total_count = response.get("totalCount", len(clients))
            
            logger.debug(f"Retrieved {len(clients)} clients from controller (totalCount={total_count})")
            
            # Filter by connection type if specified
            if connection_type != "all":
                clients = self._filter_by_connection_type(clients, connection_type)
                logger.debug(f"Filtered to {len(clients)} clients of type '{connection_type}'")
            
            # Format clients for AI consumption (summary view)
            formatted_clients = [
                self._format_client_summary(client)
                for client in clients
            ]
            
            # Apply pagination
            paginated_clients, total = self.paginate(formatted_clients, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_clients)} clients "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            return self.format_list(
                items=paginated_clients,
                total=total,
                page=page,
                page_size=page_size
            )
        
        except Exception as e:
            logger.error(f"Failed to list clients: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve client list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _filter_by_connection_type(
        self,
        clients: List[Dict[str, Any]],
        connection_type: str
    ) -> List[Dict[str, Any]]:
        """Filter clients by connection type.
        
        Args:
            clients: List of client dictionaries
            connection_type: Type to filter by (wired, wireless)
        
        Returns:
            Filtered list of clients
        """
        if connection_type == "wired":
            return [
                client for client in clients
                if client.get("is_wired", False)
            ]
        elif connection_type == "wireless":
            return [
                client for client in clients
                if not client.get("is_wired", False)
            ]
        
        return clients
    
    def _format_client_summary(self, client: Dict[str, Any]) -> Dict[str, Any]:
        """Format client data for summary view (AI-friendly).
        
        Extracts only the most relevant fields for AI consumption,
        avoiding overwhelming the context window with unnecessary data.
        Handles both v1 and legacy field names gracefully.
        
        Args:
            client: Raw client data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted client summary
        """
        # v1 uses "type": "WIRED"/"WIRELESS", legacy uses "is_wired": bool
        client_type = client.get("type", "")
        if isinstance(client_type, str) and client_type.upper() in ("WIRED", "WIRELESS"):
            is_wired = client_type.upper() == "WIRED"
        else:
            is_wired = client.get("is_wired", False)
        
        summary = {
            "mac": client.get("mac", ""),
            "name": client.get("name", client.get("hostname", "Unknown")),
            "ip": client.get("ip", ""),
            "connection_type": "wired" if is_wired else "wireless",
            "network": client.get("network", ""),
            "uptime": client.get("uptime", 0),
            "uptime_readable": self._format_uptime(client.get("uptime", 0)),
            
            # Bandwidth information
            "tx_bytes": client.get("tx_bytes", 0),
            "rx_bytes": client.get("rx_bytes", 0),
            "tx_bytes_readable": self._format_bytes(client.get("tx_bytes", 0)),
            "rx_bytes_readable": self._format_bytes(client.get("rx_bytes", 0)),
        }
        
        # Add wireless-specific information
        if not is_wired:
            summary["signal_strength"] = client.get("signal", 0)
            summary["rssi"] = client.get("rssi", 0)
            summary["essid"] = client.get("essid", "")
            summary["channel"] = client.get("channel", 0)
        
        return summary
    
    def _format_uptime(self, uptime_seconds: int) -> str:
        """Format uptime in human-readable format.
        
        Args:
            uptime_seconds: Uptime in seconds
        
        Returns:
            Human-readable uptime string
        """
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes in human-readable format.
        
        Args:
            bytes_value: Number of bytes
        
        Returns:
            Human-readable bytes string (e.g., "1.5 GB")
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(value)} {units[unit_index]}"
        else:
            return f"{value:.2f} {units[unit_index]}"


class GetClientDetailsTool(BaseTool):
    """Get detailed information about a specific client.
    
    This tool retrieves comprehensive information about a single connected
    client including connection details, statistics, and device information.
    Use this after listing clients to get full details about a specific client.
    
    Example usage:
        - "Show me details for client with MAC aa:bb:cc:dd:ee:ff"
        - "What's the connection status of my laptop?"
        - "Get full information for the device at 192.168.10.50"
    """
    
    name = "unifi_get_client_details"
    description = "Get detailed information about a specific connected client"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "mac_address": {
                "type": "string",
                "description": "Client MAC address (with or without colons)"
            }
        },
        "required": ["mac_address"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        mac_address: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get client details tool.
        
        Args:
            unifi_client: UniFi API client
            mac_address: Client MAC address
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted client details
        """
        try:
            logger.info(f"Fetching details for client: {mac_address}")
            
            # v1 API doesn't support direct lookup by MAC, so fetch all and search
            response = await unifi_client.get_v1("clients")
            clients = response.get("data", [])
            
            # Find the specific client by MAC address
            client = self._find_client(clients, mac_address)
            
            if not client:
                raise ToolError(
                    code="CLIENT_NOT_FOUND",
                    message=f"Client not found: {mac_address}",
                    details=f"No client found with MAC address '{mac_address}'",
                    actionable_steps=[
                        "Verify the MAC address is correct",
                        "Use unifi_list_clients to see connected clients",
                        "Check if the client is currently connected"
                    ]
                )
            
            # Format client details for AI consumption
            formatted_client = self._format_client_details(client)
            
            logger.info(f"Retrieved details for client: {formatted_client['name']}")
            
            return self.format_detail(
                item=formatted_client,
                item_type="client"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to get client details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve client details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the MAC address is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_client(
        self,
        clients: List[Dict[str, Any]],
        mac_address: str
    ) -> Optional[Dict[str, Any]]:
        """Find a client by MAC address.
        
        Args:
            clients: List of client dictionaries
            mac_address: MAC address to search for (with or without colons)
        
        Returns:
            Client dictionary if found, None otherwise
        """
        # Normalize MAC address (remove colons and convert to lowercase)
        search_mac = mac_address.lower().replace(":", "")
        
        for client in clients:
            client_mac = client.get("mac", "").lower().replace(":", "")
            
            if client_mac == search_mac:
                return client
        
        return None
    
    def _format_client_details(self, client: Dict[str, Any]) -> Dict[str, Any]:
        """Format client data for detailed view (AI-friendly).
        
        Includes more comprehensive information than the summary view,
        but still filters out unnecessary fields to keep context window
        usage reasonable. Handles both v1 and legacy field names.
        
        Args:
            client: Raw client data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted client details
        """
        # v1 uses "type": "WIRED"/"WIRELESS", legacy uses "is_wired": bool
        client_type = client.get("type", "")
        if isinstance(client_type, str) and client_type.upper() in ("WIRED", "WIRELESS"):
            is_wired = client_type.upper() == "WIRED"
        else:
            is_wired = client.get("is_wired", False)
        
        # Basic information
        details = {
            "mac": client.get("mac", ""),
            "name": client.get("name", client.get("hostname", "Unknown")),
            "ip": client.get("ip", ""),
            "connection_type": "wired" if is_wired else "wireless",
            
            # Network information
            "network": client.get("network", ""),
            "network_id": client.get("network_id", client.get("networkId", "")),
            "vlan": client.get("vlan", 0),
            
            # Device information
            "oui": client.get("oui", ""),
            "manufacturer": client.get("oui", "Unknown"),
            "os_name": client.get("os_name", client.get("osName", "")),
            "os_class": client.get("os_class", client.get("osClass", "")),
            "device_name": client.get("dev_id_override", client.get("device_name", "")),
            
            # Connection status
            "first_seen": client.get("first_seen", client.get("firstSeen", 0)),
            "last_seen": client.get("last_seen", client.get("lastSeen", 0)),
            "uptime": client.get("uptime", 0),
            "uptime_readable": self._format_uptime(client.get("uptime", 0)),
            
            # Bandwidth statistics
            "tx_bytes": client.get("tx_bytes", 0),
            "rx_bytes": client.get("rx_bytes", 0),
            "tx_bytes_readable": self._format_bytes(client.get("tx_bytes", 0)),
            "rx_bytes_readable": self._format_bytes(client.get("rx_bytes", 0)),
            "tx_packets": client.get("tx_packets", 0),
            "rx_packets": client.get("rx_packets", 0),
            
            # Rate information
            "tx_rate": client.get("tx_rate", 0),
            "rx_rate": client.get("rx_rate", 0),
        }
        
        # Add wireless-specific information
        if not is_wired:
            details.update({
                "essid": client.get("essid", ""),
                "bssid": client.get("bssid", ""),
                "channel": client.get("channel", 0),
                "radio": client.get("radio", ""),
                "radio_proto": client.get("radio_proto", client.get("radioProto", "")),
                
                # Signal information
                "signal": client.get("signal", 0),
                "rssi": client.get("rssi", 0),
                "noise": client.get("noise", 0),
                
                # Connection quality
                "satisfaction": client.get("satisfaction", 0),
                "tx_retries": client.get("tx_retries", 0),
                "rx_retries": client.get("rx_retries", 0),
            })
        else:
            # Add wired-specific information
            details.update({
                "switch_mac": client.get("sw_mac", client.get("switchMac", "")),
                "switch_port": client.get("sw_port", client.get("switchPort", 0)),
                "wired_rate_mbps": client.get("wired-rx_rate-max", 0),
            })
        
        # Add connected device information
        if client.get("ap_mac"):
            details["connected_device_mac"] = client.get("ap_mac", "")
            details["connected_device_name"] = client.get("ap_name", client.get("apName", ""))
        elif client.get("sw_mac") or client.get("switchMac"):
            details["connected_device_mac"] = client.get("sw_mac", client.get("switchMac", ""))
            details["connected_device_name"] = client.get("sw_name", client.get("switchName", ""))
        
        return details
    
    def _format_uptime(self, uptime_seconds: int) -> str:
        """Format uptime in human-readable format.
        
        Args:
            uptime_seconds: Uptime in seconds
        
        Returns:
            Human-readable uptime string
        """
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes in human-readable format.
        
        Args:
            bytes_value: Number of bytes
        
        Returns:
            Human-readable bytes string (e.g., "1.5 GB")
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(value)} {units[unit_index]}"
        else:
            return f"{value:.2f} {units[unit_index]}"


class ListNetworksTool(BaseTool):
    """List all configured networks and VLANs.
    
    This tool retrieves all networks configured in the UniFi controller,
    including VLANs, subnets, and network settings. Provides summary
    information optimized for AI consumption.
    
    Example usage:
        - "List all networks on my controller"
        - "Show me all VLANs"
        - "What networks are configured?"
    """
    
    name = "unifi_list_networks"
    description = "List all configured networks and VLANs"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list networks tool.
        
        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of networks
        """
        try:
            # Fetch networks from UniFi controller via v1 API
            logger.info("Fetching networks")
            
            # Handle 'filter' kwarg from MCP input schema
            if filter_expr is None and "filter" in kwargs:
                filter_expr = kwargs.pop("filter")

            params: Dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_expr is not None:
                params["filter"] = filter_expr

            response = await unifi_client.get_v1(
                "networks", params=params if params else None
            )
            
            # Extract network data from v1 response envelope
            networks = response.get("data", [])
            total_count = response.get("totalCount", len(networks))
            
            logger.debug(f"Retrieved {len(networks)} networks from controller (totalCount={total_count})")
            
            # Format networks for AI consumption (summary view)
            formatted_networks = [
                self._format_network_summary(network)
                for network in networks
            ]
            
            logger.info(f"Returning {len(formatted_networks)} networks")
            
            return self.format_list(
                items=formatted_networks,
                total=total_count,
                page=1,
                page_size=len(formatted_networks)
            )
        
        except Exception as e:
            logger.error(f"Failed to list networks: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve network list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_network_summary(self, network: Dict[str, Any]) -> Dict[str, Any]:
        """Format network data for summary view (AI-friendly).
        
        Handles both v1 and legacy field names.
        
        Args:
            network: Raw network data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted network summary
        """
        return {
            "id": network.get("id", network.get("_id", "")),
            "name": network.get("name", ""),
            "purpose": network.get("purpose", ""),
            "vlan": network.get("vlan", network.get("vlanId", "")),
            "vlan_enabled": network.get("vlan_enabled", network.get("vlanId") is not None),
            "ip_subnet": network.get("ip_subnet", network.get("ipSubnet", "")),
            "network_group": network.get("networkgroup", network.get("networkGroup", "")),
            "dhcp_enabled": network.get("dhcpd_enabled", network.get("dhcpEnabled", False)),
            "dhcp_start": network.get("dhcpd_start", network.get("dhcpStart", "")),
            "dhcp_stop": network.get("dhcpd_stop", network.get("dhcpStop", "")),
            "domain_name": network.get("domain_name", network.get("domainName", "")),
            "enabled": network.get("enabled", True),
        }



class GetNetworkDetailsTool(BaseTool):
    """Get detailed information about a specific network.
    
    This tool retrieves comprehensive information about a single network
    including VLAN configuration, DHCP settings, and firewall rules.
    Use this after listing networks to get full details about a specific network.
    
    Example usage:
        - "Show me details for network abc123"
        - "What's the configuration of my IoT VLAN?"
        - "Get full information for the guest network"
    """
    
    name = "unifi_get_network_details"
    description = "Get detailed information about a specific network"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "network_id": {
                "type": "string",
                "description": "Network ID"
            }
        },
        "required": ["network_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        network_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get network details tool.
        
        Args:
            unifi_client: UniFi API client
            network_id: Network ID
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted network details
        """
        try:
            logger.info(f"Fetching details for network: {network_id}")
            
            # Try direct v1 lookup by network ID first
            network = None
            try:
                response = await unifi_client.get_v1(f"networks/{network_id}")
                # v1 may return network directly or wrapped in data
                if "data" in response and isinstance(response["data"], list):
                    networks = response["data"]
                    network = networks[0] if networks else None
                elif "data" in response and isinstance(response["data"], dict):
                    network = response["data"]
                else:
                    network = response
            except Exception as lookup_err:
                logger.debug(f"Direct v1 lookup failed for '{network_id}': {lookup_err}")
                # Fallback: fetch all networks and search by ID or name
                network = await self._find_network_fallback(unifi_client, network_id)
            
            if not network:
                raise ToolError(
                    code="NETWORK_NOT_FOUND",
                    message=f"Network not found: {network_id}",
                    details=f"No network found with ID '{network_id}'",
                    actionable_steps=[
                        "Verify the network ID is correct",
                        "Use unifi_list_networks to see available networks",
                        "Check if the network is enabled"
                    ]
                )
            
            # Format network details for AI consumption
            formatted_network = self._format_network_details(network)
            
            logger.info(f"Retrieved details for network: {formatted_network['name']}")
            
            return self.format_detail(
                item=formatted_network,
                item_type="network"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to get network details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve network details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the network ID is correct",
                    "Check server logs for details"
                ]
            )

    
    def _find_network(
        self,
        networks: List[Dict[str, Any]],
        network_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a network by ID or name.
        
        Handles both v1 (id) and legacy (_id) field names.
        
        Args:
            networks: List of network dictionaries
            network_id: Network ID or name to search for
        
        Returns:
            Network dictionary if found, None otherwise
        """
        network_id_lower = network_id.lower()
        
        for network in networks:
            # Check v1 ID field
            if network.get("id", "").lower() == network_id_lower:
                return network
            
            # Check legacy ID field
            if network.get("_id", "").lower() == network_id_lower:
                return network
            
            # Also check by name for convenience
            if network.get("name", "").lower() == network_id_lower:
                return network
        
        return None
    
    async def _find_network_fallback(
        self,
        unifi_client: UniFiClient,
        network_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fallback: fetch all networks via v1 API and search by ID or name.
        
        Used when direct v1 lookup by ID fails (e.g., when searching by name).
        
        Args:
            unifi_client: UniFi API client
            network_id: Network ID or name to search for
        
        Returns:
            Network dictionary if found, None otherwise
        """
        response = await unifi_client.get_v1("networks")
        networks = response.get("data", [])
        return self._find_network(networks, network_id)
    
    def _format_network_details(self, network: Dict[str, Any]) -> Dict[str, Any]:
        """Format network data for detailed view (AI-friendly).
        
        Handles both v1 and legacy field names. Includes new v1 fields
        (vlanId, dhcpGuarding, management, default) when present.
        
        Args:
            network: Raw network data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted network details
        """
        details = {
            "id": network.get("id", network.get("_id", "")),
            "name": network.get("name", ""),
            "purpose": network.get("purpose", ""),
            
            # VLAN configuration (v1 uses vlanId, legacy uses vlan)
            "vlan": network.get("vlan", network.get("vlanId", "")),
            "vlan_enabled": network.get("vlan_enabled", network.get("vlanId") is not None),
            
            # IP configuration
            "ip_subnet": network.get("ip_subnet", network.get("ipSubnet", "")),
            "gateway_ip": network.get("gateway_ip", network.get("gatewayIp", "")),
            "gateway_type": network.get("gateway_type", network.get("gatewayType", "")),
            "network_group": network.get("networkgroup", network.get("networkGroup", "")),
            
            # DHCP configuration (v1 uses camelCase)
            "dhcp_enabled": network.get("dhcpd_enabled", network.get("dhcpEnabled", False)),
            "dhcp_start": network.get("dhcpd_start", network.get("dhcpStart", "")),
            "dhcp_stop": network.get("dhcpd_stop", network.get("dhcpStop", "")),
            "dhcp_lease_time": network.get("dhcpd_leasetime", network.get("dhcpLeaseTime", 0)),
            "dhcp_dns": network.get("dhcpd_dns", network.get("dhcpDns", [])),
            "dhcp_gateway": network.get("dhcpd_gateway", network.get("dhcpGateway", "")),
            
            # DNS configuration
            "domain_name": network.get("domain_name", network.get("domainName", "")),
            "dns_servers": network.get("dhcpd_dns", network.get("dhcpDns", [])),
            
            # Network settings
            "enabled": network.get("enabled", True),
            "is_nat": network.get("is_nat", network.get("isNat", False)),
            "is_guest": network.get("is_guest", network.get("isGuest", False)),
            "igmp_snooping": network.get("igmp_snooping", network.get("igmpSnooping", False)),
            "dhcp_relay_enabled": network.get("dhcp_relay_enabled", network.get("dhcpRelayEnabled", False)),
            
            # IPv6 settings (if configured)
            "ipv6_interface_type": network.get("ipv6_interface_type", network.get("ipv6InterfaceType", "")),
            "ipv6_pd_start": network.get("ipv6_pd_start", network.get("ipv6PdStart", "")),
            "ipv6_pd_stop": network.get("ipv6_pd_stop", network.get("ipv6PdStop", "")),
        }
        
        # New v1-specific fields — include when present
        if "vlanId" in network:
            details["vlanId"] = network["vlanId"]
        if "dhcpGuarding" in network:
            details["dhcpGuarding"] = network["dhcpGuarding"]
        if "management" in network:
            details["management"] = network["management"]
        if "default" in network:
            details["default"] = network["default"]
        
        # Add DHCP options if present
        if network.get("dhcpd_options") or network.get("dhcpOptions"):
            details["dhcp_options"] = network.get("dhcpd_options", network.get("dhcpOptions", []))
        
        return details



class ListWLANsTool(BaseTool):
    """List all configured WiFi broadcasts (wireless networks).
    
    This tool retrieves all WiFi broadcasts configured in the UniFi controller
    via the v1 integration API, including SSIDs, security settings, and VLAN
    assignments. Provides summary information optimized for AI consumption.
    
    Example usage:
        - "List all wireless networks"
        - "Show me all SSIDs"
        - "What WLANs are configured?"
    """
    
    name = "unifi_list_wlans"
    description = "List all configured WiFi broadcasts (wireless networks)"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list WLANs tool.
        
        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of WiFi broadcasts
        """
        try:
            # Fetch WiFi broadcasts from UniFi controller via v1 API
            logger.info("Fetching WiFi broadcasts")
            
            # Handle 'filter' kwarg from MCP input schema
            if filter_expr is None and "filter" in kwargs:
                filter_expr = kwargs.pop("filter")

            params: Dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_expr is not None:
                params["filter"] = filter_expr

            response = await unifi_client.get_v1(
                "wifi/broadcasts", params=params if params else None
            )
            
            # Extract broadcast data from v1 response envelope
            wlans = response.get("data", [])
            total_count = response.get("totalCount", len(wlans))
            
            logger.debug(f"Retrieved {len(wlans)} WiFi broadcasts from controller (totalCount={total_count})")
            
            # Format broadcasts for AI consumption (summary view)
            formatted_wlans = [
                self._format_wlan_summary(wlan)
                for wlan in wlans
            ]
            
            logger.info(f"Returning {len(formatted_wlans)} WiFi broadcasts")
            
            return self.format_list(
                items=formatted_wlans,
                total=total_count,
                page=1,
                page_size=len(formatted_wlans)
            )
        
        except Exception as e:
            logger.error(f"Failed to list WiFi broadcasts: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve WiFi broadcast list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )

    
    def _format_wlan_summary(self, wlan: Dict[str, Any]) -> Dict[str, Any]:
        """Format WiFi broadcast data for summary view (AI-friendly).
        
        Handles both v1 and legacy field names.
        
        Args:
            wlan: Raw WiFi broadcast data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted WiFi broadcast summary
        """
        return {
            "id": wlan.get("id", wlan.get("_id", "")),
            "name": wlan.get("name", ""),
            "ssid": wlan.get("ssid", wlan.get("x_passphrase", wlan.get("name", ""))),
            "enabled": wlan.get("enabled", True),
            "security": wlan.get("security", ""),
            "wpa_mode": wlan.get("wpaMode", wlan.get("wpa_mode", "")),
            "wpa_enc": wlan.get("wpaEnc", wlan.get("wpa_enc", "")),
            "network_id": wlan.get("networkId", wlan.get("networkconf_id", "")),
            "vlan": wlan.get("vlan", ""),
            "vlan_enabled": wlan.get("vlanEnabled", wlan.get("vlan_enabled", False)),
            "is_guest": wlan.get("isGuest", wlan.get("is_guest", False)),
            "hide_ssid": wlan.get("hideSsid", wlan.get("hide_ssid", False)),
        }



class GetWLANDetailsTool(BaseTool):
    """Get detailed information about a specific WiFi broadcast.
    
    This tool retrieves comprehensive information about a single WiFi broadcast
    via the v1 integration API, including security settings, radio configuration,
    and advanced options. Uses direct v1 lookup by ID with fallback to list+search.
    
    Example usage:
        - "Show me details for WLAN abc123"
        - "What's the configuration of my guest WiFi?"
        - "Get full information for the IoT wireless network"
    """
    
    name = "unifi_get_wlan_details"
    description = "Get detailed information about a specific WiFi broadcast"
    category = "network_discovery"
    
    input_schema = {
        "type": "object",
        "properties": {
            "wlan_id": {
                "type": "string",
                "description": "WiFi broadcast ID or name"
            }
        },
        "required": ["wlan_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        wlan_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get WiFi broadcast details tool.
        
        Args:
            unifi_client: UniFi API client
            wlan_id: WiFi broadcast ID or name
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted WiFi broadcast details
        """
        try:
            logger.info(f"Fetching details for WiFi broadcast: {wlan_id}")
            
            # Try direct v1 lookup by broadcast ID first
            wlan = None
            try:
                response = await unifi_client.get_v1(f"wifi/broadcasts/{wlan_id}")
                # v1 may return broadcast directly or wrapped in data
                if "data" in response and isinstance(response["data"], list):
                    wlans = response["data"]
                    wlan = wlans[0] if wlans else None
                elif "data" in response and isinstance(response["data"], dict):
                    wlan = response["data"]
                else:
                    wlan = response
            except Exception as lookup_err:
                logger.debug(f"Direct v1 lookup failed for '{wlan_id}': {lookup_err}")
                # Fallback: fetch all broadcasts and search by ID or name
                wlan = await self._find_wlan_fallback(unifi_client, wlan_id)
            
            if not wlan:
                raise ToolError(
                    code="WLAN_NOT_FOUND",
                    message=f"WiFi broadcast not found: {wlan_id}",
                    details=f"No WiFi broadcast found with ID '{wlan_id}'",
                    actionable_steps=[
                        "Verify the broadcast ID is correct",
                        "Use unifi_list_wlans to see available WiFi broadcasts",
                        "Check if the broadcast is enabled"
                    ]
                )
            
            # Format broadcast details for AI consumption
            formatted_wlan = self._format_wlan_details(wlan)
            
            logger.info(f"Retrieved details for WiFi broadcast: {formatted_wlan['name']}")
            
            return self.format_detail(
                item=formatted_wlan,
                item_type="wlan"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to get WiFi broadcast details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve WiFi broadcast details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the broadcast ID is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_wlan(
        self,
        wlans: List[Dict[str, Any]],
        wlan_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a WiFi broadcast by ID or name.
        
        Handles both v1 (id) and legacy (_id) field names.
        
        Args:
            wlans: List of WiFi broadcast dictionaries
            wlan_id: Broadcast ID or name to search for
        
        Returns:
            Broadcast dictionary if found, None otherwise
        """
        wlan_id_lower = wlan_id.lower()
        
        for wlan in wlans:
            # Check v1 ID field
            if wlan.get("id", "").lower() == wlan_id_lower:
                return wlan
            
            # Check legacy ID field
            if wlan.get("_id", "").lower() == wlan_id_lower:
                return wlan
            
            # Also check by name for convenience
            if wlan.get("name", "").lower() == wlan_id_lower:
                return wlan
        
        return None

    async def _find_wlan_fallback(
        self,
        unifi_client: UniFiClient,
        wlan_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fallback: fetch all WiFi broadcasts via v1 API and search by ID or name.
        
        Used when direct v1 lookup by ID fails (e.g., when searching by name).
        
        Args:
            unifi_client: UniFi API client
            wlan_id: Broadcast ID or name to search for
        
        Returns:
            Broadcast dictionary if found, None otherwise
        """
        response = await unifi_client.get_v1("wifi/broadcasts")
        wlans = response.get("data", [])
        return self._find_wlan(wlans, wlan_id)

    
    def _format_wlan_details(self, wlan: Dict[str, Any]) -> Dict[str, Any]:
        """Format WiFi broadcast data for detailed view (AI-friendly).
        
        Handles both v1 and legacy field names.
        
        Args:
            wlan: Raw WiFi broadcast data from UniFi API (v1 or legacy)
        
        Returns:
            Formatted WiFi broadcast details
        """
        details = {
            "id": wlan.get("id", wlan.get("_id", "")),
            "name": wlan.get("name", ""),
            "ssid": wlan.get("ssid", wlan.get("x_passphrase", wlan.get("name", ""))),
            "enabled": wlan.get("enabled", True),
            
            # Security settings
            "security": wlan.get("security", ""),
            "wpa_mode": wlan.get("wpaMode", wlan.get("wpa_mode", "")),
            "wpa_enc": wlan.get("wpaEnc", wlan.get("wpa_enc", "")),
            "wep_idx": wlan.get("wepIdx", wlan.get("wep_idx", 0)),
            
            # Network assignment
            "network_id": wlan.get("networkId", wlan.get("networkconf_id", "")),
            "vlan": wlan.get("vlan", ""),
            "vlan_enabled": wlan.get("vlanEnabled", wlan.get("vlan_enabled", False)),
            
            # Guest network settings
            "is_guest": wlan.get("isGuest", wlan.get("is_guest", False)),
            "guest_portal_enabled": wlan.get("portalEnabled", wlan.get("portal_enabled", False)),
            "guest_portal_customized": wlan.get("portalCustomized", wlan.get("portal_customized", False)),
            
            # SSID settings
            "hide_ssid": wlan.get("hideSsid", wlan.get("hide_ssid", False)),
            "mac_filter_enabled": wlan.get("macFilterEnabled", wlan.get("mac_filter_enabled", False)),
            "mac_filter_policy": wlan.get("macFilterPolicy", wlan.get("mac_filter_policy", "")),
            
            # Radio settings
            "minrate_ng_enabled": wlan.get("minrateNgEnabled", wlan.get("minrate_ng_enabled", False)),
            "minrate_ng_data_rate_kbps": wlan.get("minrateNgDataRateKbps", wlan.get("minrate_ng_data_rate_kbps", 0)),
            "minrate_na_enabled": wlan.get("minrateNaEnabled", wlan.get("minrate_na_enabled", False)),
            "minrate_na_data_rate_kbps": wlan.get("minrateNaDataRateKbps", wlan.get("minrate_na_data_rate_kbps", 0)),
            
            # Advanced settings
            "dtim_mode": wlan.get("dtimMode", wlan.get("dtim_mode", "")),
            "dtim_ng": wlan.get("dtimNg", wlan.get("dtim_ng", 0)),
            "dtim_na": wlan.get("dtimNa", wlan.get("dtim_na", 0)),
            "schedule_enabled": wlan.get("scheduleEnabled", wlan.get("schedule_enabled", False)),
            "schedule": wlan.get("schedule", []),
            
            # Band steering
            "band_steering_mode": wlan.get("bandSteeringMode", wlan.get("band_steering_mode", "")),
            
            # Fast roaming
            "fast_roaming_enabled": wlan.get("fastRoamingEnabled", wlan.get("fast_roaming_enabled", False)),
            
            # RADIUS settings (if applicable)
            "radius_enabled": wlan.get("radiusEnabled", wlan.get("radius_enabled", False)),
            "radius_nas_id": wlan.get("radiusNasId", wlan.get("radius_nas_id", "")),
            
            # Group rekey interval
            "group_rekey": wlan.get("groupRekey", wlan.get("group_rekey", 0)),
            
            # WPA3 settings
            "wpa3_support": wlan.get("wpa3Support", wlan.get("wpa3_support", False)),
            "wpa3_transition": wlan.get("wpa3Transition", wlan.get("wpa3_transition", False)),
        }
        
        # Add MAC filter list if enabled
        mac_filter_enabled = wlan.get("macFilterEnabled", wlan.get("mac_filter_enabled"))
        if mac_filter_enabled:
            details["mac_filter_list"] = wlan.get("macFilterList", wlan.get("mac_filter_list", []))
        
        return details
