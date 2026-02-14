"""Security tools for UniFi MCP server.

This module provides tools for inspecting security configurations:
- Traffic routes and route details
- IPS (Intrusion Prevention System) status
- Port forwards and port forward details

Note: Firewall rule listing and details have been migrated to tools/firewall.py
which uses the v1 zone-based policy API. The legacy firewall rule tools that
called /api/s/{site}/rest/firewallrule have been removed as they return empty
results on UniFi Network 9.0+ Dream Machines.

These tools are read-only and provide security visibility without
making any changes to the firewall configuration.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListTrafficRoutesTool(BaseTool):
    """List all traffic routing rules.
    
    This tool retrieves all static routes and routing policies from the UniFi
    controller. Routes control how traffic is forwarded between networks and
    to external destinations.
    
    Example usage:
        - "List all traffic routes"
        - "Show me routing rules"
        - "What routes are configured?"
    """
    
    name = "unifi_list_traffic_routes"
    description = "List all traffic routing rules"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "enabled_only": {
                "type": "boolean",
                "description": "Show only enabled routes (true) or all routes (false)",
                "default": False
            },
            "page": {
                "type": "integer",
                "description": "Page number for pagination (1-indexed)",
                "minimum": 1,
                "default": 1
            },
            "page_size": {
                "type": "integer",
                "description": "Number of routes per page",
                "minimum": 1,
                "maximum": 500,
                "default": 50
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list traffic routes tool.
        
        Args:
            unifi_client: UniFi API client
            enabled_only: Show only enabled routes if True
            page: Page number for pagination
            page_size: Number of routes per page
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of traffic routes with pagination info
        """
        try:
            # Fetch routing rules from UniFi controller
            logger.info(
                f"Fetching traffic routes (enabled_only={enabled_only}, "
                f"page={page}, page_size={page_size})"
            )
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/routing")
            
            # Extract route data from response
            routes = response.get("data", [])
            
            logger.debug(f"Retrieved {len(routes)} traffic routes from controller")
            
            # Filter by enabled status if specified
            if enabled_only:
                routes = [route for route in routes if route.get("enabled", False)]
                logger.debug(f"Filtered to {len(routes)} enabled routes")
            
            # Format routes for AI consumption (summary view)
            formatted_routes = [
                self._format_route_summary(route)
                for route in routes
            ]
            
            # Apply pagination
            paginated_routes, total = self.paginate(formatted_routes, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_routes)} traffic routes "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            return self.format_list(
                items=paginated_routes,
                total=total,
                page=page,
                page_size=page_size
            )
        
        except Exception as e:
            logger.error(f"Failed to list traffic routes: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve traffic routes",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_route_summary(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Format traffic route data for summary view (AI-friendly).
        
        Args:
            route: Raw route data from UniFi API
        
        Returns:
            Formatted route summary
        """
        return {
            "id": route.get("_id", ""),
            "name": route.get("name", "Unnamed Route"),
            "enabled": route.get("enabled", False),
            "type": route.get("type", "static"),
            "destination_network": route.get("static-route_network", ""),
            "next_hop": route.get("static-route_nexthop", ""),
            "distance": route.get("static-route_distance", 1),
            "interface": route.get("static-route_interface", ""),
        }


class GetRouteDetailsTool(BaseTool):
    """Get detailed information about a specific traffic route.
    
    This tool retrieves comprehensive information about a single routing rule
    including destination network, next hop, interface, and metric information.
    Use this after listing routes to get full details about a specific route.
    
    Example usage:
        - "Show me details for route abc123"
        - "What's the configuration of the default route?"
        - "Get full information for the VPN route"
    """
    
    name = "unifi_get_route_details"
    description = "Get detailed information about a specific traffic route"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "route_id": {
                "type": "string",
                "description": "Route ID"
            }
        },
        "required": ["route_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        route_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get route details tool.
        
        Args:
            unifi_client: UniFi API client
            route_id: Route ID
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted route details
        """
        try:
            # Fetch all routes (UniFi doesn't have a single route endpoint)
            logger.info(f"Fetching details for traffic route: {route_id}")
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/routing")
            routes = response.get("data", [])
            
            # Find the specific route by ID
            route = self._find_route(routes, route_id)
            
            if not route:
                raise ToolError(
                    code="ROUTE_NOT_FOUND",
                    message=f"Traffic route not found: {route_id}",
                    details=f"No traffic route found with ID '{route_id}'",
                    actionable_steps=[
                        "Verify the route ID is correct",
                        "Use unifi_list_traffic_routes to see available routes",
                        "Check if the route still exists"
                    ]
                )
            
            # Format route details for AI consumption
            formatted_route = self._format_route_details(route)
            
            logger.info(f"Retrieved details for traffic route: {formatted_route['name']}")
            
            return self.format_detail(
                item=formatted_route,
                item_type="traffic_route"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to get route details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve route details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the route ID is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_route(
        self,
        routes: List[Dict[str, Any]],
        route_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a route by ID.
        
        Args:
            routes: List of route dictionaries
            route_id: Route ID to search for
        
        Returns:
            Route dictionary if found, None otherwise
        """
        route_id_lower = route_id.lower()
        
        for route in routes:
            # Check ID
            if route.get("_id", "").lower() == route_id_lower:
                return route
        
        return None
    
    def _format_route_details(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Format route data for detailed view (AI-friendly).
        
        Args:
            route: Raw route data from UniFi API
        
        Returns:
            Formatted route details
        """
        details = {
            # Basic information
            "id": route.get("_id", ""),
            "name": route.get("name", "Unnamed Route"),
            "enabled": route.get("enabled", False),
            "type": route.get("type", "static"),
            
            # Static route configuration
            "destination_network": route.get("static-route_network", ""),
            "next_hop": route.get("static-route_nexthop", ""),
            "distance": route.get("static-route_distance", 1),
            "interface": route.get("static-route_interface", ""),
            
            # Additional metadata
            "site_id": route.get("site_id", ""),
        }
        
        return details


class GetIPSStatusTool(BaseTool):
    """Get intrusion prevention system (IPS) status and alerts.
    
    This tool retrieves the current status of the UniFi IPS/IDS system,
    including enabled status, threat detection statistics, recent alerts,
    and signature information. Use this to monitor security threats and
    understand the IPS configuration.
    
    Example usage:
        - "What's the IPS status?"
        - "Show me IPS alerts"
        - "Is intrusion prevention enabled?"
        - "What threats has IPS detected?"
    """
    
    name = "unifi_get_ips_status"
    description = "Get intrusion prevention system status and alerts"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "include_alerts": {
                "type": "boolean",
                "description": "Include recent IPS alerts in the response",
                "default": True
            },
            "alert_limit": {
                "type": "integer",
                "description": "Maximum number of alerts to return",
                "minimum": 1,
                "maximum": 100,
                "default": 20
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        include_alerts: bool = True,
        alert_limit: int = 20,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get IPS status tool.
        
        Args:
            unifi_client: UniFi API client
            include_alerts: Include recent alerts if True
            alert_limit: Maximum number of alerts to return
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted IPS status and alerts
        """
        try:
            logger.info(
                f"Fetching IPS status (include_alerts={include_alerts}, "
                f"alert_limit={alert_limit})"
            )
            
            # Fetch IPS/IDS settings
            settings_response = await unifi_client.get(
                f"/api/s/{{site}}/rest/setting/ips"
            )
            settings = settings_response.get("data", [])
            
            # Get the IPS configuration (usually first item)
            ips_config = settings[0] if settings else {}
            
            # Fetch IPS statistics
            stats_response = await unifi_client.get(
                f"/api/s/{{site}}/stat/ips/event"
            )
            stats = stats_response.get("data", [])
            
            # Format IPS status
            ips_status = self._format_ips_status(ips_config, stats)
            
            # Fetch recent alerts if requested
            if include_alerts:
                # Fetch all alarms (no params to avoid boolean type issues)
                alerts_response = await unifi_client.get(
                    f"/api/s/{{site}}/rest/alarm"
                )
                all_alerts = alerts_response.get("data", [])
                
                # Filter out archived alerts manually
                all_alerts = [alert for alert in all_alerts if not alert.get("archived", False)]
                
                # Filter for IPS-related alerts
                ips_alerts = [
                    alert for alert in all_alerts
                    if self._is_ips_alert(alert)
                ]
                
                # Limit and format alerts
                limited_alerts = ips_alerts[:alert_limit]
                ips_status["recent_alerts"] = [
                    self._format_alert(alert)
                    for alert in limited_alerts
                ]
                ips_status["total_alerts"] = len(ips_alerts)
            
            logger.info(
                f"Retrieved IPS status: enabled={ips_status['enabled']}, "
                f"alerts={ips_status.get('total_alerts', 0)}"
            )
            
            return self.format_detail(
                item=ips_status,
                item_type="ips_status"
            )
        
        except Exception as e:
            logger.error(f"Failed to get IPS status: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve IPS status",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify IPS/IDS is configured on the controller",
                    "Check server logs for details"
                ]
            )
    
    def _format_ips_status(
        self,
        config: Dict[str, Any],
        stats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format IPS status for AI consumption.
        
        Args:
            config: IPS configuration from UniFi API
            stats: IPS statistics from UniFi API
        
        Returns:
            Formatted IPS status
        """
        # Calculate threat statistics
        threat_stats = self._calculate_threat_stats(stats)
        
        # Convert boolean values to strings for MCP compatibility
        enabled = config.get("enabled", False)
        suppression_enabled = config.get("suppression_enabled", False)
        
        status = {
            # Basic configuration
            "enabled": "yes" if enabled else "no",
            "enabled_bool": enabled,  # Keep boolean for programmatic use
            "key": str(config.get("key", "ips")),
            
            # Detection settings
            "suppression_enabled": "yes" if suppression_enabled else "no",
            "suppression_enabled_bool": suppression_enabled,  # Keep boolean for programmatic use
            "suppression_mode": str(config.get("suppression_mode", "")),
            
            # Threat statistics
            "threat_statistics": threat_stats,
            
            # Signature information
            "signature_version": str(config.get("signature_version", "unknown")),
            "last_signature_update": str(config.get("last_signature_update", "unknown")),
        }
        
        return status
    
    def _calculate_threat_stats(
        self,
        stats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate threat detection statistics.
        
        Args:
            stats: List of IPS event statistics
        
        Returns:
            Threat statistics summary
        """
        if not stats:
            return {
                "total_events": 0,
                "blocked_events": 0,
                "alerted_events": 0,
                "categories": {}
            }
        
        total_events = 0
        blocked_events = 0
        alerted_events = 0
        categories = {}
        
        for event in stats:
            # Count events by action
            action = event.get("action", "").lower()
            count = event.get("count", 0)
            
            total_events += count
            
            if action == "blocked":
                blocked_events += count
            elif action == "alerted":
                alerted_events += count
            
            # Count by category
            category = event.get("category", "unknown")
            categories[category] = categories.get(category, 0) + count
        
        return {
            "total_events": total_events,
            "blocked_events": blocked_events,
            "alerted_events": alerted_events,
            "categories": categories
        }
    
    def _is_ips_alert(self, alert: Dict[str, Any]) -> bool:
        """Check if an alert is IPS-related.
        
        Args:
            alert: Alert data from UniFi API
        
        Returns:
            True if alert is IPS-related, False otherwise
        """
        # Check alert key for IPS-related types
        key = alert.get("key", "").lower()
        
        ips_keywords = [
            "ips",
            "ids",
            "intrusion",
            "threat",
            "attack",
            "malware",
            "exploit"
        ]
        
        return any(keyword in key for keyword in ips_keywords)
    
    def _format_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Format an IPS alert for AI consumption.
        
        Args:
            alert: Raw alert data from UniFi API
        
        Returns:
            Formatted alert
        """
        return {
            "id": str(alert.get("_id", "")),
            "key": str(alert.get("key", "")),
            "message": str(alert.get("msg", "")),
            "timestamp": int(alert.get("time", 0)),
            "datetime": str(alert.get("datetime", "")),
            "severity": str(alert.get("subsystem", "unknown")),
            "source_ip": str(alert.get("src_ip", "")),
            "destination_ip": str(alert.get("dst_ip", "")),
            "signature_id": str(alert.get("signature_id", "")),
            "category": str(alert.get("catname", "unknown")),
        }


class ListPortForwardsTool(BaseTool):
    """List all port forwarding rules.
    
    This tool retrieves all port forwarding (NAT) rules from the UniFi
    controller. Port forwards allow external traffic to reach internal
    services by mapping external ports to internal IP addresses and ports.
    
    Example usage:
        - "List all port forwards"
        - "Show me NAT rules"
        - "What port forwarding is configured?"
    """
    
    name = "unifi_list_port_forwards"
    description = "List all port forwarding rules"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "enabled_only": {
                "type": "boolean",
                "description": "Show only enabled port forwards (true) or all (false)",
                "default": False
            },
            "page": {
                "type": "integer",
                "description": "Page number for pagination (1-indexed)",
                "minimum": 1,
                "default": 1
            },
            "page_size": {
                "type": "integer",
                "description": "Number of port forwards per page",
                "minimum": 1,
                "maximum": 500,
                "default": 50
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list port forwards tool.
        
        Args:
            unifi_client: UniFi API client
            enabled_only: Show only enabled port forwards if True
            page: Page number for pagination
            page_size: Number of port forwards per page
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of port forwards with pagination info
        """
        try:
            # Fetch port forwarding rules from UniFi controller
            logger.info(
                f"Fetching port forwards (enabled_only={enabled_only}, "
                f"page={page}, page_size={page_size})"
            )
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/portforward")
            
            # Extract port forward data from response
            forwards = response.get("data", [])
            
            logger.debug(f"Retrieved {len(forwards)} port forwards from controller")
            
            # Filter by enabled status if specified
            if enabled_only:
                forwards = [fwd for fwd in forwards if fwd.get("enabled", False)]
                logger.debug(f"Filtered to {len(forwards)} enabled port forwards")
            
            # Format port forwards for AI consumption (summary view)
            formatted_forwards = [
                self._format_forward_summary(forward)
                for forward in forwards
            ]
            
            # Apply pagination
            paginated_forwards, total = self.paginate(formatted_forwards, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_forwards)} port forwards "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            return self.format_list(
                items=paginated_forwards,
                total=total,
                page=page,
                page_size=page_size
            )
        
        except Exception as e:
            logger.error(f"Failed to list port forwards: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve port forwards",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_forward_summary(self, forward: Dict[str, Any]) -> Dict[str, Any]:
        """Format port forward data for summary view (AI-friendly).
        
        Args:
            forward: Raw port forward data from UniFi API
        
        Returns:
            Formatted port forward summary
        """
        return {
            "id": forward.get("_id", ""),
            "name": forward.get("name", "Unnamed Port Forward"),
            "enabled": forward.get("enabled", False),
            "protocol": self._format_protocol_pf(forward),
            "source": forward.get("src", "any"),
            "destination_ip": forward.get("fwd", ""),
            "destination_port": forward.get("fwd_port", ""),
            "external_port": forward.get("dst_port", ""),
            "log": forward.get("log", False),
        }
    
    def _format_protocol_pf(self, forward: Dict[str, Any]) -> str:
        """Format protocol information for port forwards.
        
        Args:
            forward: Port forward data
        
        Returns:
            Protocol string (e.g., "TCP", "UDP", "TCP/UDP")
        """
        protocol = forward.get("proto", "tcp_udp")
        
        if protocol == "tcp_udp":
            return "TCP/UDP"
        else:
            return protocol.upper()


class GetPortForwardDetailsTool(BaseTool):
    """Get detailed information about a specific port forward.
    
    This tool retrieves comprehensive information about a single port
    forwarding rule including protocol, source restrictions, destination
    IP and port mapping, and logging configuration.
    Use this after listing port forwards to get full details.
    
    Example usage:
        - "Show me details for port forward abc123"
        - "What's the configuration of the web server forward?"
        - "Get full information for the SSH port forward"
    """
    
    name = "unifi_get_port_forward_details"
    description = "Get detailed information about a specific port forward"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "forward_id": {
                "type": "string",
                "description": "Port forward ID"
            }
        },
        "required": ["forward_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        forward_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get port forward details tool.
        
        Args:
            unifi_client: UniFi API client
            forward_id: Port forward ID
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted port forward details
        """
        try:
            # Fetch all port forwards (UniFi doesn't have a single forward endpoint)
            logger.info(f"Fetching details for port forward: {forward_id}")
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/portforward")
            forwards = response.get("data", [])
            
            # Find the specific port forward by ID
            forward = self._find_forward(forwards, forward_id)
            
            if not forward:
                raise ToolError(
                    code="FORWARD_NOT_FOUND",
                    message=f"Port forward not found: {forward_id}",
                    details=f"No port forward found with ID '{forward_id}'",
                    actionable_steps=[
                        "Verify the port forward ID is correct",
                        "Use unifi_list_port_forwards to see available port forwards",
                        "Check if the port forward still exists"
                    ]
                )
            
            # Format port forward details for AI consumption
            formatted_forward = self._format_forward_details(forward)
            
            logger.info(f"Retrieved details for port forward: {formatted_forward['name']}")
            
            return self.format_detail(
                item=formatted_forward,
                item_type="port_forward"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to get port forward details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve port forward details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the port forward ID is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_forward(
        self,
        forwards: List[Dict[str, Any]],
        forward_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a port forward by ID.
        
        Args:
            forwards: List of port forward dictionaries
            forward_id: Port forward ID to search for
        
        Returns:
            Port forward dictionary if found, None otherwise
        """
        forward_id_lower = forward_id.lower()
        
        for forward in forwards:
            # Check ID
            if forward.get("_id", "").lower() == forward_id_lower:
                return forward
        
        return None
    
    def _format_forward_details(self, forward: Dict[str, Any]) -> Dict[str, Any]:
        """Format port forward data for detailed view (AI-friendly).
        
        Args:
            forward: Raw port forward data from UniFi API
        
        Returns:
            Formatted port forward details
        """
        details = {
            # Basic information
            "id": forward.get("_id", ""),
            "name": forward.get("name", "Unnamed Port Forward"),
            "enabled": forward.get("enabled", False),
            
            # Protocol and ports
            "protocol": self._format_protocol_detailed(forward),
            "external_port": forward.get("dst_port", ""),
            "destination_ip": forward.get("fwd", ""),
            "destination_port": forward.get("fwd_port", ""),
            
            # Source restrictions
            "source": forward.get("src", "any"),
            "source_network_id": forward.get("pfwd_interface", ""),
            
            # Logging
            "log": forward.get("log", False),
            
            # Additional metadata
            "site_id": forward.get("site_id", ""),
        }
        
        return details
    
    def _format_protocol_detailed(self, forward: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed protocol information.
        
        Args:
            forward: Port forward data
        
        Returns:
            Protocol configuration dictionary
        """
        protocol = forward.get("proto", "tcp_udp")
        
        result = {
            "type": protocol,
            "display": self._format_protocol_display(protocol),
        }
        
        return result
    
    def _format_protocol_display(self, protocol: str) -> str:
        """Format protocol for display.
        
        Args:
            protocol: Protocol string
        
        Returns:
            Display-friendly protocol string
        """
        if protocol == "tcp_udp":
            return "TCP/UDP"
        else:
            return protocol.upper()
