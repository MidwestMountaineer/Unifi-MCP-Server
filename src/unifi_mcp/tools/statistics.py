"""Statistics and monitoring tools for UniFi MCP server.

This module provides tools for accessing network statistics and monitoring:
- Get overall network statistics and health metrics
- Get system health information
- Get client-specific statistics
- Get device-specific statistics
- Get top bandwidth consumers
- Format statistics data for AI consumption

These tools are read-only and provide visibility into network performance
and system status without making any changes.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


class GetNetworkStatsTool(BaseTool):
    """Get overall network statistics and health metrics.
    
    This tool retrieves comprehensive network-wide statistics including:
    - Total connected clients (wired and wireless)
    - Bandwidth usage (upload/download)
    - Device status summary
    - Network uptime
    - Traffic statistics
    
    Use this to get a high-level overview of network health and activity.
    
    Example usage:
        - "What's the overall network status?"
        - "Show me network statistics"
        - "How many clients are connected?"
        - "What's the current bandwidth usage?"
    """
    
    name = "unifi_get_network_stats"
    description = "Get overall network statistics and health"
    category = "statistics"
    
    input_schema = {
        "type": "object",
        "properties": {}
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get network stats tool.
        
        Args:
            unifi_client: UniFi API client
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted network statistics
        """
        try:
            logger.info("Fetching network statistics")
            
            # Fetch multiple data sources for comprehensive stats
            # 1. Site statistics (overall metrics)
            site_stats = await self._get_site_stats(unifi_client)
            
            # 2. Device statistics (device health)
            device_stats = await self._get_device_stats(unifi_client)
            
            # 3. Client statistics (connected clients)
            client_stats = await self._get_client_stats(unifi_client)
            
            # Combine and format statistics
            network_stats = {
                "summary": {
                    "total_clients": client_stats.get("total", 0),
                    "wired_clients": client_stats.get("wired", 0),
                    "wireless_clients": client_stats.get("wireless", 0),
                    "total_devices": device_stats.get("total", 0),
                    "online_devices": device_stats.get("online", 0),
                    "offline_devices": device_stats.get("offline", 0),
                },
                "bandwidth": {
                    "total_tx_bytes": site_stats.get("tx_bytes", 0),
                    "total_rx_bytes": site_stats.get("rx_bytes", 0),
                    "total_tx_bytes_formatted": self._format_bytes(site_stats.get("tx_bytes", 0)),
                    "total_rx_bytes_formatted": self._format_bytes(site_stats.get("rx_bytes", 0)),
                },
                "health": {
                    "wan_status": site_stats.get("wan_status", "unknown"),
                    "lan_status": site_stats.get("lan_status", "unknown"),
                    "vpn_status": site_stats.get("vpn_status", "unknown"),
                    "www_status": site_stats.get("www_status", "unknown"),
                },
                "uptime": {
                    "gateway_uptime": site_stats.get("gateway_uptime", 0),
                    "gateway_uptime_formatted": self._format_uptime(site_stats.get("gateway_uptime", 0)),
                }
            }
            
            logger.info(
                f"Retrieved network stats: {network_stats['summary']['total_clients']} clients, "
                f"{network_stats['summary']['online_devices']}/{network_stats['summary']['total_devices']} devices online"
            )
            
            return self.format_success(
                data=network_stats,
                message="Network statistics retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to get network statistics: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve network statistics",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    async def _get_site_stats(self, unifi_client: UniFiClient) -> Dict[str, Any]:
        """Get site-level statistics.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            Site statistics dictionary
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/health")
            health_data = response.get("data", [])
            
            # Aggregate health data from different subsystems
            stats = {
                "tx_bytes": 0,
                "rx_bytes": 0,
                "gateway_uptime": 0,
                "wan_status": "unknown",
                "lan_status": "unknown",
                "vpn_status": "unknown",
                "www_status": "unknown",
            }
            
            for subsystem in health_data:
                subsystem_name = subsystem.get("subsystem", "")
                
                # Aggregate bandwidth
                stats["tx_bytes"] += subsystem.get("tx_bytes-r", 0)
                stats["rx_bytes"] += subsystem.get("rx_bytes-r", 0)
                
                # Get gateway uptime
                if subsystem_name == "wan":
                    stats["gateway_uptime"] = subsystem.get("uptime", 0)
                    stats["wan_status"] = subsystem.get("status", "unknown")
                
                # Get subsystem statuses
                if subsystem_name == "lan":
                    stats["lan_status"] = subsystem.get("status", "unknown")
                elif subsystem_name == "vpn":
                    stats["vpn_status"] = subsystem.get("status", "unknown")
                elif subsystem_name == "www":
                    stats["www_status"] = subsystem.get("status", "unknown")
            
            return stats
        
        except Exception as e:
            logger.warning(f"Failed to get site stats: {e}")
            return {}
    
    async def _get_device_stats(self, unifi_client: UniFiClient) -> Dict[str, Any]:
        """Get device statistics.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            Device statistics dictionary
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/device")
            devices = response.get("data", [])
            
            stats = {
                "total": len(devices),
                "online": 0,
                "offline": 0,
            }
            
            for device in devices:
                state = device.get("state", 0)
                if state == 1:
                    stats["online"] += 1
                else:
                    stats["offline"] += 1
            
            return stats
        
        except Exception as e:
            logger.warning(f"Failed to get device stats: {e}")
            return {"total": 0, "online": 0, "offline": 0}
    
    async def _get_client_stats(self, unifi_client: UniFiClient) -> Dict[str, Any]:
        """Get client statistics.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            Client statistics dictionary
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/sta")
            clients = response.get("data", [])
            
            stats = {
                "total": len(clients),
                "wired": 0,
                "wireless": 0,
            }
            
            for client in clients:
                is_wired = client.get("is_wired", False)
                if is_wired:
                    stats["wired"] += 1
                else:
                    stats["wireless"] += 1
            
            return stats
        
        except Exception as e:
            logger.warning(f"Failed to get client stats: {e}")
            return {"total": 0, "wired": 0, "wireless": 0}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format.
        
        Args:
            bytes_value: Number of bytes
        
        Returns:
            Formatted string (e.g., "1.5 GB", "256 MB")
        """
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        elif bytes_value < 1024 ** 4:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes_value / (1024 ** 4):.2f} TB"
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to human-readable format.
        
        Args:
            seconds: Uptime in seconds
        
        Returns:
            Formatted string (e.g., "2 days, 3 hours", "45 minutes")
        """
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days} days, {hours} hours"


class GetSystemHealthTool(BaseTool):
    """Get overall system health metrics.
    
    This tool retrieves system health information for the UniFi controller
    and connected devices including:
    - Controller status and version
    - Device health (CPU, memory, temperature)
    - Subsystem status (WAN, LAN, VPN, WWW)
    - Alerts and warnings
    
    Use this to monitor the health of the UniFi infrastructure itself.
    
    Example usage:
        - "What's the system health?"
        - "Show me controller status"
        - "Are there any system alerts?"
        - "Check device health"
    """
    
    name = "unifi_get_system_health"
    description = "Get overall system health metrics"
    category = "statistics"
    
    input_schema = {
        "type": "object",
        "properties": {}
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get system health tool.
        
        Args:
            unifi_client: UniFi API client
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted system health information
        """
        try:
            logger.info("Fetching system health")
            
            # Fetch health data from multiple sources
            # 1. Subsystem health (WAN, LAN, VPN, etc.)
            subsystem_health = await self._get_subsystem_health(unifi_client)
            
            # 2. Device health (CPU, memory, temperature)
            device_health = await self._get_device_health(unifi_client)
            
            # 3. Controller info
            controller_info = await self._get_controller_info(unifi_client)
            
            # 4. Recent alerts
            alerts = await self._get_recent_alerts(unifi_client)
            
            # Combine and format health data
            system_health = {
                "controller": {
                    "version": controller_info.get("version", "unknown"),
                    "hostname": controller_info.get("hostname", "unknown"),
                    "uptime": controller_info.get("uptime", 0),
                    "uptime_formatted": self._format_uptime(controller_info.get("uptime", 0)),
                },
                "subsystems": subsystem_health,
                "devices": device_health,
                "alerts": {
                    "total": len(alerts),
                    "recent": alerts[:5],  # Only include 5 most recent
                }
            }
            
            # Calculate overall health status
            system_health["overall_status"] = self._calculate_overall_status(
                subsystem_health,
                device_health,
                alerts
            )
            
            logger.info(
                f"Retrieved system health: {system_health['overall_status']}, "
                f"{len(device_health)} devices, {len(alerts)} alerts"
            )
            
            return self.format_success(
                data=system_health,
                message="System health retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to get system health: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve system health",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    async def _get_subsystem_health(self, unifi_client: UniFiClient) -> List[Dict[str, Any]]:
        """Get subsystem health information.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            List of subsystem health dictionaries
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/health")
            health_data = response.get("data", [])
            
            subsystems = []
            for subsystem in health_data:
                subsystems.append({
                    "name": subsystem.get("subsystem", "unknown"),
                    "status": subsystem.get("status", "unknown"),
                    "uptime": subsystem.get("uptime", 0),
                    "latency": subsystem.get("latency", 0),
                    "drops": subsystem.get("drops", 0),
                    "tx_bytes": subsystem.get("tx_bytes-r", 0),
                    "rx_bytes": subsystem.get("rx_bytes-r", 0),
                })
            
            return subsystems
        
        except Exception as e:
            logger.warning(f"Failed to get subsystem health: {e}")
            return []
    
    async def _get_device_health(self, unifi_client: UniFiClient) -> List[Dict[str, Any]]:
        """Get device health information.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            List of device health dictionaries
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/device")
            devices = response.get("data", [])
            
            device_health = []
            for device in devices:
                health = {
                    "name": device.get("name", "Unknown"),
                    "type": device.get("type", "unknown"),
                    "model": device.get("model", "unknown"),
                    "state": "online" if device.get("state", 0) == 1 else "offline",
                    "uptime": device.get("uptime", 0),
                }
                
                # Add system stats if available
                system_stats = device.get("system-stats", {})
                if system_stats:
                    health["cpu_usage"] = system_stats.get("cpu", 0)
                    health["memory_usage"] = system_stats.get("mem", 0)
                    health["temperature"] = system_stats.get("temps", {}).get("Board (CPU)", 0)
                
                device_health.append(health)
            
            return device_health
        
        except Exception as e:
            logger.warning(f"Failed to get device health: {e}")
            return []
    
    async def _get_controller_info(self, unifi_client: UniFiClient) -> Dict[str, Any]:
        """Get controller information.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            Controller information dictionary
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/sysinfo")
            sysinfo = response.get("data", [])
            
            if sysinfo:
                info = sysinfo[0]
                return {
                    "version": info.get("version", "unknown"),
                    "hostname": info.get("hostname", "unknown"),
                    "uptime": info.get("uptime", 0),
                }
            
            return {}
        
        except Exception as e:
            logger.warning(f"Failed to get controller info: {e}")
            return {}
    
    async def _get_recent_alerts(self, unifi_client: UniFiClient) -> List[Dict[str, Any]]:
        """Get recent system alerts.
        
        Args:
            unifi_client: UniFi API client
        
        Returns:
            List of alert dictionaries
        """
        try:
            response = await unifi_client.get("/api/s/{site}/stat/alarm")
            alarms = response.get("data", [])
            
            # Format alerts for AI consumption
            alerts = []
            for alarm in alarms[:10]:  # Limit to 10 most recent
                alerts.append({
                    "key": alarm.get("key", "unknown"),
                    "message": alarm.get("msg", ""),
                    "timestamp": alarm.get("datetime", ""),
                    "archived": alarm.get("archived", False),
                })
            
            return alerts
        
        except Exception as e:
            logger.warning(f"Failed to get recent alerts: {e}")
            return []
    
    def _calculate_overall_status(
        self,
        subsystems: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]]
    ) -> str:
        """Calculate overall system health status.
        
        Args:
            subsystems: List of subsystem health data
            devices: List of device health data
            alerts: List of recent alerts
        
        Returns:
            Overall status string ("healthy", "warning", "critical")
        """
        # Check for critical issues
        critical_subsystems = [
            s for s in subsystems
            if s.get("status") not in ["ok", "unknown"]
        ]
        
        offline_devices = [
            d for d in devices
            if d.get("state") == "offline"
        ]
        
        unarchived_alerts = [
            a for a in alerts
            if not a.get("archived", False)
        ]
        
        # Determine status
        if critical_subsystems or len(offline_devices) > len(devices) * 0.5:
            return "critical"
        elif offline_devices or unarchived_alerts:
            return "warning"
        else:
            return "healthy"
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to human-readable format.
        
        Args:
            seconds: Uptime in seconds
        
        Returns:
            Formatted string (e.g., "2 days, 3 hours", "45 minutes")
        """
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days} days, {hours} hours"



class GetClientStatsTool(BaseTool):
    """Get statistics for a specific client.
    
    This tool retrieves detailed statistics for a specific client including:
    - Connection information (wired/wireless, signal strength)
    - Bandwidth usage (upload/download, total and rate)
    - Session information (uptime, first seen, last seen)
    - Network details (IP, hostname, VLAN)
    - Device information (OS, manufacturer)
    
    Use this to analyze individual client performance and behavior.
    
    Example usage:
        - "Show me stats for client aa:bb:cc:dd:ee:ff"
        - "What's the bandwidth usage for my laptop?"
        - "How long has this device been connected?"
        - "What's the signal strength for this wireless client?"
    """
    
    name = "unifi_get_client_stats"
    description = "Get statistics for a specific client"
    category = "statistics"
    
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
        """Execute the get client stats tool.
        
        Args:
            unifi_client: UniFi API client
            mac_address: Client MAC address
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted client statistics
        """
        try:
            # Normalize MAC address (remove colons, lowercase)
            normalized_mac = mac_address.replace(":", "").replace("-", "").lower()
            
            logger.info(f"Fetching statistics for client {mac_address}")
            
            # Get all clients and find the specific one
            response = await unifi_client.get("/api/s/{site}/stat/sta")
            clients = response.get("data", [])
            
            # Find the client by MAC address
            client = None
            for c in clients:
                client_mac = c.get("mac", "").replace(":", "").lower()
                if client_mac == normalized_mac:
                    client = c
                    break
            
            if not client:
                raise ToolError(
                    code="NOT_FOUND",
                    message=f"Client not found: {mac_address}",
                    details=f"No client with MAC address {mac_address} is currently connected",
                    actionable_steps=[
                        "Verify the MAC address is correct",
                        "Check if the client is currently connected",
                        "Use unifi_list_clients to see all connected clients"
                    ]
                )
            
            # Format client statistics
            is_wired = client.get("is_wired", False)
            
            client_stats = {
                "identity": {
                    "mac_address": client.get("mac", ""),
                    "name": client.get("name") or client.get("hostname", "Unknown"),
                    "hostname": client.get("hostname", ""),
                    "ip_address": client.get("ip", ""),
                },
                "connection": {
                    "type": "wired" if is_wired else "wireless",
                    "network": client.get("network", ""),
                    "vlan": client.get("vlan", 0),
                    "uptime": client.get("uptime", 0),
                    "uptime_formatted": self._format_uptime(client.get("uptime", 0)),
                },
                "bandwidth": {
                    "tx_bytes": client.get("tx_bytes", 0),
                    "rx_bytes": client.get("rx_bytes", 0),
                    "tx_bytes_formatted": self._format_bytes(client.get("tx_bytes", 0)),
                    "rx_bytes_formatted": self._format_bytes(client.get("rx_bytes", 0)),
                    "tx_rate": client.get("tx_rate", 0),
                    "rx_rate": client.get("rx_rate", 0),
                    "tx_rate_formatted": f"{client.get('tx_rate', 0) / 1000:.2f} Mbps",
                    "rx_rate_formatted": f"{client.get('rx_rate', 0) / 1000:.2f} Mbps",
                },
                "device_info": {
                    "manufacturer": client.get("oui", "Unknown"),
                    "os_name": client.get("os_name", "Unknown"),
                    "os_class": client.get("os_class", "Unknown"),
                    "device_name": client.get("dev_id_override") or client.get("name", "Unknown"),
                }
            }
            
            # Add wireless-specific stats if applicable
            if not is_wired:
                client_stats["wireless"] = {
                    "signal": client.get("signal", 0),
                    "noise": client.get("noise", 0),
                    "rssi": client.get("rssi", 0),
                    "channel": client.get("channel", 0),
                    "essid": client.get("essid", ""),
                    "radio": client.get("radio", ""),
                    "radio_proto": client.get("radio_proto", ""),
                }
            
            # Add session information
            client_stats["session"] = {
                "first_seen": client.get("first_seen", 0),
                "last_seen": client.get("last_seen", 0),
                "latest_assoc_time": client.get("latest_assoc_time", 0),
            }
            
            logger.info(
                f"Retrieved stats for client {mac_address}: "
                f"{client_stats['bandwidth']['tx_bytes_formatted']} TX, "
                f"{client_stats['bandwidth']['rx_bytes_formatted']} RX"
            )
            
            return self.format_success(
                data=client_stats,
                message=f"Client statistics retrieved successfully for {mac_address}"
            )
        
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to get client statistics: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve client statistics",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the MAC address format",
                    "Check server logs for details"
                ]
            )
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        elif bytes_value < 1024 ** 4:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes_value / (1024 ** 4):.2f} TB"
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to human-readable format."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days} days, {hours} hours"


class GetDeviceStatsTool(BaseTool):
    """Get statistics for a specific device.
    
    This tool retrieves detailed statistics for a specific UniFi device including:
    - Device information (name, model, type, version)
    - System metrics (CPU, memory, temperature)
    - Network statistics (uplink speed, port statistics)
    - Status information (state, uptime, last seen)
    - Performance metrics (load, throughput)
    
    Use this to monitor individual device health and performance.
    
    Example usage:
        - "Show me stats for device abc123"
        - "What's the CPU usage on my switch?"
        - "Check the temperature of my access point"
        - "How much traffic is going through this device?"
    """
    
    name = "unifi_get_device_stats"
    description = "Get statistics for a specific device"
    category = "statistics"
    
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
        """Execute the get device stats tool.
        
        Args:
            unifi_client: UniFi API client
            device_id: Device ID or MAC address
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted device statistics
        """
        try:
            logger.info(f"Fetching statistics for device {device_id}")
            
            # Get all devices and find the specific one
            response = await unifi_client.get("/api/s/{site}/stat/device")
            devices = response.get("data", [])
            
            # Find the device by ID or MAC address
            device = None
            normalized_id = device_id.replace(":", "").replace("-", "").lower()
            
            for d in devices:
                device_mac = d.get("mac", "").replace(":", "").lower()
                device_uid = d.get("_id", "").lower()
                
                if device_uid == normalized_id or device_mac == normalized_id:
                    device = d
                    break
            
            if not device:
                raise ToolError(
                    code="NOT_FOUND",
                    message=f"Device not found: {device_id}",
                    details=f"No device with ID or MAC address {device_id} found",
                    actionable_steps=[
                        "Verify the device ID or MAC address is correct",
                        "Use unifi_list_devices to see all devices"
                    ]
                )
            
            # Format device statistics
            device_stats = {
                "identity": {
                    "id": device.get("_id", ""),
                    "mac_address": device.get("mac", ""),
                    "name": device.get("name", "Unknown"),
                    "model": device.get("model", ""),
                    "type": device.get("type", ""),
                    "version": device.get("version", ""),
                },
                "status": {
                    "state": "online" if device.get("state", 0) == 1 else "offline",
                    "adopted": device.get("adopted", False),
                    "uptime": device.get("uptime", 0),
                    "uptime_formatted": self._format_uptime(device.get("uptime", 0)),
                    "last_seen": device.get("last_seen", 0),
                },
                "network": {
                    "ip_address": device.get("ip", ""),
                    "uplink": {
                        "type": device.get("uplink", {}).get("type", ""),
                        "speed": device.get("uplink", {}).get("speed", 0),
                        "full_duplex": device.get("uplink", {}).get("full_duplex", False),
                    }
                },
                "statistics": {
                    "tx_bytes": device.get("tx_bytes", 0),
                    "rx_bytes": device.get("rx_bytes", 0),
                    "tx_bytes_formatted": self._format_bytes(device.get("tx_bytes", 0)),
                    "rx_bytes_formatted": self._format_bytes(device.get("rx_bytes", 0)),
                }
            }
            
            # Add system stats if available
            system_stats = device.get("system-stats", {})
            if system_stats:
                device_stats["system"] = {
                    "cpu_usage": system_stats.get("cpu", 0),
                    "memory_usage": system_stats.get("mem", 0),
                    "uptime": system_stats.get("uptime", 0),
                }
                
                # Add temperature if available
                temps = system_stats.get("temps", {})
                if temps:
                    device_stats["system"]["temperatures"] = temps
            
            # Add port statistics for switches
            if device.get("type") in ["usw", "ugw"]:
                port_table = device.get("port_table", [])
                if port_table:
                    device_stats["ports"] = {
                        "total": len(port_table),
                        "active": sum(1 for p in port_table if p.get("up", False)),
                        "details": [
                            {
                                "port_idx": p.get("port_idx", 0),
                                "name": p.get("name", f"Port {p.get('port_idx', 0)}"),
                                "up": p.get("up", False),
                                "speed": p.get("speed", 0),
                                "full_duplex": p.get("full_duplex", False),
                                "tx_bytes": p.get("tx_bytes", 0),
                                "rx_bytes": p.get("rx_bytes", 0),
                            }
                            for p in port_table[:10]  # Limit to first 10 ports
                        ]
                    }
            
            # Add wireless stats for APs
            if device.get("type") == "uap":
                device_stats["wireless"] = {
                    "num_sta": device.get("num_sta", 0),
                    "user-num_sta": device.get("user-num_sta", 0),
                    "guest-num_sta": device.get("guest-num_sta", 0),
                }
                
                # Add radio stats if available
                radio_table = device.get("radio_table", [])
                if radio_table:
                    device_stats["wireless"]["radios"] = [
                        {
                            "name": r.get("name", ""),
                            "radio": r.get("radio", ""),
                            "channel": r.get("channel", 0),
                            "tx_power": r.get("tx_power", 0),
                            "num_sta": r.get("num_sta", 0),
                        }
                        for r in radio_table
                    ]
            
            logger.info(
                f"Retrieved stats for device {device_id}: "
                f"{device_stats['status']['state']}, "
                f"{device_stats['statistics']['tx_bytes_formatted']} TX, "
                f"{device_stats['statistics']['rx_bytes_formatted']} RX"
            )
            
            return self.format_success(
                data=device_stats,
                message=f"Device statistics retrieved successfully for {device_id}"
            )
        
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to get device statistics: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve device statistics",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the device ID or MAC address",
                    "Check server logs for details"
                ]
            )
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        elif bytes_value < 1024 ** 4:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes_value / (1024 ** 4):.2f} TB"
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to human-readable format."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days} days, {hours} hours"


class GetDPIStatsTool(BaseTool):
    """Get deep packet inspection statistics.
    
    This tool retrieves DPI (Deep Packet Inspection) statistics showing:
    - Application categories and their bandwidth usage
    - Top applications by traffic volume
    - Protocol distribution
    - Traffic patterns and trends
    
    DPI provides visibility into what applications and services are consuming
    bandwidth on your network.
    
    Use this to understand network usage patterns and identify bandwidth hogs.
    
    Example usage:
        - "What applications are using the most bandwidth?"
        - "Show me DPI statistics"
        - "What's the traffic breakdown by category?"
        - "Which protocols are most active?"
    """
    
    name = "unifi_get_dpi_stats"
    description = "Get deep packet inspection statistics"
    category = "statistics"
    
    input_schema = {
        "type": "object",
        "properties": {}
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get DPI stats tool.
        
        Args:
            unifi_client: UniFi API client
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted DPI statistics
        """
        try:
            logger.info("Fetching DPI statistics")
            
            # Fetch DPI data from UniFi controller
            response = await unifi_client.get("/api/s/{site}/stat/dpi")
            dpi_data = response.get("data", [])
            
            if not dpi_data:
                logger.warning("No DPI data available")
                return self.format_success(
                    data={
                        "categories": [],
                        "top_applications": [],
                        "total_traffic": {
                            "tx_bytes": 0,
                            "rx_bytes": 0,
                            "total_bytes": 0,
                        },
                        "summary": "No DPI data available"
                    },
                    message="No DPI statistics available"
                )
            
            # Process DPI data
            categories = []
            total_tx = 0
            total_rx = 0
            
            for entry in dpi_data:
                cat_name = entry.get("cat", "Unknown")
                app_name = entry.get("app", "Unknown")
                tx_bytes = entry.get("tx_bytes", 0)
                rx_bytes = entry.get("rx_bytes", 0)
                total_bytes = tx_bytes + rx_bytes
                
                total_tx += tx_bytes
                total_rx += rx_bytes
                
                categories.append({
                    "category": cat_name,
                    "application": app_name,
                    "tx_bytes": tx_bytes,
                    "rx_bytes": rx_bytes,
                    "total_bytes": total_bytes,
                    "tx_bytes_formatted": self._format_bytes(tx_bytes),
                    "rx_bytes_formatted": self._format_bytes(rx_bytes),
                    "total_bytes_formatted": self._format_bytes(total_bytes),
                })
            
            # Sort by total bytes descending
            categories.sort(key=lambda x: x["total_bytes"], reverse=True)
            
            # Get top 10 applications
            top_applications = categories[:10]
            
            # Calculate total traffic
            total_traffic = total_tx + total_rx
            
            dpi_stats = {
                "categories": categories,
                "top_applications": top_applications,
                "total_traffic": {
                    "tx_bytes": total_tx,
                    "rx_bytes": total_rx,
                    "total_bytes": total_traffic,
                    "tx_bytes_formatted": self._format_bytes(total_tx),
                    "rx_bytes_formatted": self._format_bytes(total_rx),
                    "total_bytes_formatted": self._format_bytes(total_traffic),
                },
                "summary": f"{len(categories)} applications tracked, {self._format_bytes(total_traffic)} total traffic"
            }
            
            logger.info(
                f"Retrieved DPI stats: {len(categories)} applications, "
                f"{dpi_stats['total_traffic']['total_bytes_formatted']} total traffic"
            )
            
            return self.format_success(
                data=dpi_stats,
                message="DPI statistics retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to get DPI statistics: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve DPI statistics",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify DPI is enabled on the controller",
                    "Check server logs for details"
                ]
            )
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        elif bytes_value < 1024 ** 4:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes_value / (1024 ** 4):.2f} TB"


class GetAlertsTool(BaseTool):
    """Get recent system alerts and events.
    
    This tool retrieves recent alerts and alarms from the UniFi controller including:
    - System alerts (device offline, authentication failures, etc.)
    - Security events (IPS alerts, unauthorized access attempts)
    - Network events (client connections, disconnections)
    - Configuration changes
    
    Alerts can be filtered by limit to control how many are returned.
    
    Use this to monitor system events and identify issues.
    
    Example usage:
        - "Show me recent alerts"
        - "What are the latest system events?"
        - "Are there any security alerts?"
        - "Show me the last 20 alerts"
    """
    
    name = "unifi_get_alerts"
    description = "Get recent system alerts and events"
    category = "statistics"
    
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of alerts to return (default: 50, max: 500)",
                "default": 50,
                "minimum": 1,
                "maximum": 500
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        limit: int = 50,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get alerts tool.
        
        Args:
            unifi_client: UniFi API client
            limit: Number of alerts to return
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted alerts list
        """
        try:
            # Validate limit
            if limit < 1:
                limit = 1
            elif limit > 500:
                limit = 500
            
            logger.info(f"Fetching up to {limit} alerts")
            
            # Fetch alerts from UniFi controller
            response = await unifi_client.get("/api/s/{site}/stat/alarm")
            all_alerts = response.get("data", [])
            
            # Limit the number of alerts
            alerts = all_alerts[:limit]
            
            # Format alerts for AI consumption
            formatted_alerts = []
            for alert in alerts:
                formatted_alert = {
                    "key": alert.get("key", "unknown"),
                    "message": alert.get("msg", ""),
                    "timestamp": alert.get("datetime", ""),
                    "time": alert.get("time", 0),
                    "archived": alert.get("archived", False),
                    "handled": alert.get("handled", False),
                    "subsystem": alert.get("subsystem", ""),
                }
                
                # Add device information if available
                if "ap" in alert:
                    formatted_alert["device_mac"] = alert.get("ap", "")
                if "ap_name" in alert:
                    formatted_alert["device_name"] = alert.get("ap_name", "")
                
                # Add client information if available
                if "client_mac" in alert:
                    formatted_alert["client_mac"] = alert.get("client_mac", "")
                if "client_name" in alert:
                    formatted_alert["client_name"] = alert.get("client_name", "")
                
                formatted_alerts.append(formatted_alert)
            
            # Calculate summary statistics
            total_alerts = len(all_alerts)
            archived_count = sum(1 for a in alerts if a.get("archived", False))
            unarchived_count = len(alerts) - archived_count
            
            # Group alerts by key for summary
            alert_types = {}
            for alert in alerts:
                key = alert.get("key", "unknown")
                alert_types[key] = alert_types.get(key, 0) + 1
            
            alerts_data = {
                "alerts": formatted_alerts,
                "summary": {
                    "total_available": total_alerts,
                    "returned": len(alerts),
                    "archived": archived_count,
                    "unarchived": unarchived_count,
                    "alert_types": alert_types,
                },
                "message": f"Retrieved {len(alerts)} of {total_alerts} total alerts"
            }
            
            logger.info(
                f"Retrieved {len(alerts)} alerts: "
                f"{unarchived_count} unarchived, {archived_count} archived"
            )
            
            return self.format_success(
                data=alerts_data,
                message=f"Retrieved {len(alerts)} alerts successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve alerts",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )


class GetTopClientsTool(BaseTool):
    """List clients by bandwidth usage.
    
    This tool retrieves the top bandwidth consumers on the network, sorted
    by total data transferred (upload + download). Useful for:
    - Identifying bandwidth hogs
    - Monitoring network usage patterns
    - Troubleshooting performance issues
    - Capacity planning
    
    Results include client identity, connection type, and bandwidth metrics.
    
    Example usage:
        - "Who are the top bandwidth users?"
        - "Show me the top 5 clients by bandwidth"
        - "Which devices are using the most data?"
        - "List bandwidth hogs on my network"
    """
    
    name = "unifi_get_top_clients"
    description = "List clients by bandwidth usage"
    category = "statistics"
    
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of top clients to return",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get top clients tool.
        
        Args:
            unifi_client: UniFi API client
            limit: Number of top clients to return (default: 10)
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of top clients by bandwidth
        """
        try:
            logger.info(f"Fetching top {limit} clients by bandwidth")
            
            # Get all clients
            response = await unifi_client.get("/api/s/{site}/stat/sta")
            clients = response.get("data", [])
            
            if not clients:
                return self.format_success(
                    data={"clients": [], "total_clients": 0},
                    message="No clients currently connected"
                )
            
            # Calculate total bandwidth for each client and sort
            client_bandwidth = []
            for client in clients:
                tx_bytes = client.get("tx_bytes", 0)
                rx_bytes = client.get("rx_bytes", 0)
                total_bytes = tx_bytes + rx_bytes
                
                client_bandwidth.append({
                    "mac_address": client.get("mac", ""),
                    "name": client.get("name") or client.get("hostname", "Unknown"),
                    "hostname": client.get("hostname", ""),
                    "ip_address": client.get("ip", ""),
                    "connection_type": "wired" if client.get("is_wired", False) else "wireless",
                    "network": client.get("network", ""),
                    "tx_bytes": tx_bytes,
                    "rx_bytes": rx_bytes,
                    "total_bytes": total_bytes,
                    "tx_bytes_formatted": self._format_bytes(tx_bytes),
                    "rx_bytes_formatted": self._format_bytes(rx_bytes),
                    "total_bytes_formatted": self._format_bytes(total_bytes),
                    "uptime": client.get("uptime", 0),
                    "uptime_formatted": self._format_uptime(client.get("uptime", 0)),
                })
            
            # Sort by total bandwidth (descending)
            client_bandwidth.sort(key=lambda x: x["total_bytes"], reverse=True)
            
            # Limit results
            top_clients = client_bandwidth[:limit]
            
            # Calculate summary statistics
            total_bandwidth = sum(c["total_bytes"] for c in client_bandwidth)
            top_bandwidth = sum(c["total_bytes"] for c in top_clients)
            top_percentage = (top_bandwidth / total_bandwidth * 100) if total_bandwidth > 0 else 0
            
            result = {
                "clients": top_clients,
                "summary": {
                    "total_clients": len(clients),
                    "top_clients_count": len(top_clients),
                    "total_bandwidth": total_bandwidth,
                    "total_bandwidth_formatted": self._format_bytes(total_bandwidth),
                    "top_bandwidth": top_bandwidth,
                    "top_bandwidth_formatted": self._format_bytes(top_bandwidth),
                    "top_percentage": round(top_percentage, 2),
                }
            }
            
            logger.info(
                f"Retrieved top {len(top_clients)} clients: "
                f"{result['summary']['top_bandwidth_formatted']} "
                f"({result['summary']['top_percentage']}% of total)"
            )
            
            return self.format_success(
                data=result,
                message=f"Top {len(top_clients)} clients by bandwidth retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to get top clients: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve top clients",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        elif bytes_value < 1024 ** 4:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes_value / (1024 ** 4):.2f} TB"
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to human-readable format."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days} days, {hours} hours"
