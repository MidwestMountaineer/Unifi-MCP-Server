"""Security tools for UniFi MCP server.

This module provides tools for inspecting security configurations:
- List all firewall rules with filtering by enabled/disabled status
- Get detailed information about specific firewall rules
- Format firewall rule data for AI consumption (action, zones, addresses, ports)

These tools are read-only and provide security visibility without
making any changes to the firewall configuration.
"""

from typing import Any, Dict, List, Optional

from ..api.endpoint_router import EndpointError
from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


def _handle_endpoint_error(error: EndpointError, feature_name: str) -> ToolError:
    """Convert EndpointError to ToolError with appropriate messaging.
    
    This helper function provides consistent error handling for security tools
    when endpoint requests fail, including fallback failures.
    
    Args:
        error: The EndpointError from the endpoint router
        feature_name: Human-readable name of the feature (e.g., "firewall rules")
    
    Returns:
        ToolError with appropriate code, message, and actionable steps
    """
    if error.fallback_endpoint and error.fallback_error:
        # Both endpoints failed
        return ToolError(
            code="BOTH_ENDPOINTS_FAILED",
            message=f"Failed to retrieve {feature_name} - both v2 and v1 API endpoints failed",
            details=(
                f"v2 endpoint ({error.primary_endpoint}): {error.primary_error}. "
                f"v1 fallback ({error.fallback_endpoint}): {error.fallback_error}"
            ),
            actionable_steps=error.get_actionable_steps()
        )
    else:
        # Single endpoint failed (traditional controller or no fallback available)
        return ToolError(
            code="API_ERROR",
            message=f"Failed to retrieve {feature_name}",
            details=f"Endpoint {error.primary_endpoint}: {error.primary_error}",
            actionable_steps=error.get_actionable_steps()
        )


class ListFirewallRulesTool(BaseTool):
    """List all firewall rules with optional filtering.
    
    This tool retrieves all firewall policies and rules from the UniFi
    controller and provides summary information optimized for AI consumption.
    Supports filtering by enabled/disabled status and pagination for large
    rule sets.
    
    Example usage:
        - "List all firewall rules"
        - "Show me enabled firewall rules"
        - "What firewall rules are disabled?"
    """
    
    name = "unifi_list_firewall_rules"
    description = "List all firewall policies and rules with optional filtering"
    category = "security"
    
    # Fields to include in concise response format
    CONCISE_FIELDS = ["id", "name", "enabled", "action", "protocol"]
    
    input_schema = {
        "type": "object",
        "properties": {
            "enabled_only": {
                "type": "boolean",
                "description": "Show only enabled rules (true) or all rules (false)",
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
                "description": "Number of rules per page",
                "minimum": 1,
                "maximum": 500,
                "default": 50
            },
            "response_format": {
                "type": "string",
                "enum": ["detailed", "concise"],
                "description": "Response format: 'detailed' for all fields, 'concise' for essential fields only",
                "default": "detailed"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        response_format: str = "detailed",
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list firewall rules tool.
        
        Args:
            unifi_client: UniFi API client
            enabled_only: Show only enabled rules if True
            page: Page number for pagination
            page_size: Number of rules per page
            response_format: "detailed" or "concise" response format
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of firewall rules with pagination info
        """
        try:
            # Fetch firewall rules using endpoint routing for v2 API support
            logger.info(
                f"Fetching firewall rules (enabled_only={enabled_only}, "
                f"page={page}, page_size={page_size}, format={response_format})"
            )
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("firewall_rules")
            
            # Extract normalized rule data
            rules = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
            logger.debug(
                f"Retrieved {len(rules)} firewall rules from controller "
                f"(api_version={api_version})"
            )
            
            # Filter by enabled status if specified
            if enabled_only:
                rules = [rule for rule in rules if rule.get("enabled", False)]
                logger.debug(f"Filtered to {len(rules)} enabled rules")
            
            # Format rules for AI consumption (summary view)
            # Data is already normalized, just extract summary fields
            formatted_rules = [
                self._format_normalized_rule_summary(rule)
                for rule in rules
            ]
            
            # Apply pagination
            paginated_rules, total = self.paginate(formatted_rules, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_rules)} firewall rules "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            # Use format_list_with_truncation for response format support
            response = self.format_list_with_truncation(
                items=paginated_rules,
                total=total,
                page=page,
                page_size=page_size,
                response_format=response_format,
                concise_fields=self.CONCISE_FIELDS
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to list firewall rules: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "firewall rules")
        
        except Exception as e:
            logger.error(f"Failed to list firewall rules: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall rules",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_normalized_rule_summary(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized firewall rule data for summary view (AI-friendly).
        
        Works with normalized rule data from ResponseNormalizer.
        
        Args:
            rule: Normalized firewall rule data
        
        Returns:
            Formatted firewall rule summary
        """
        return {
            "id": rule.get("id", ""),
            "name": rule.get("name", "Unnamed Rule"),
            "enabled": rule.get("enabled", False),
            "action": rule.get("action", ""),
            "protocol": rule.get("protocol", "ALL"),
            "source_zone": rule.get("source_zone", "any"),
            "destination_zone": rule.get("destination_zone", "any"),
            "source_address": rule.get("source_address", "any"),
            "destination_address": rule.get("destination_address", "any"),
            "destination_port": rule.get("destination_port", "any"),
            "logging": rule.get("logging", False),
            "api_version": rule.get("api_version", ""),
        }
    
    def _format_rule_summary(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format firewall rule data for summary view (AI-friendly).
        
        Extracts only the most relevant fields for AI consumption,
        avoiding overwhelming the context window with unnecessary data.
        
        Args:
            rule: Raw firewall rule data from UniFi API
        
        Returns:
            Formatted firewall rule summary
        """
        return {
            "id": rule.get("_id", ""),
            "rule_index": rule.get("rule_index", 0),
            "name": rule.get("name", "Unnamed Rule"),
            "enabled": rule.get("enabled", False),
            "action": rule.get("action", "").upper(),
            "protocol": self._format_protocol(rule),
            "source_zone": rule.get("src_firewallgroup_ids", ["any"])[0] if rule.get("src_firewallgroup_ids") else "any",
            "destination_zone": rule.get("dst_firewallgroup_ids", ["any"])[0] if rule.get("dst_firewallgroup_ids") else "any",
            "source_address": self._format_address(rule, "src"),
            "destination_address": self._format_address(rule, "dst"),
            "destination_port": self._format_port(rule),
            "logging": rule.get("logging", False),
        }
    
    def _format_protocol(self, rule: Dict[str, Any]) -> str:
        """Format protocol information.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Protocol string (e.g., "TCP", "UDP", "ALL")
        """
        protocol = rule.get("protocol", "all")
        
        if protocol == "all":
            return "ALL"
        elif protocol == "tcp_udp":
            return "TCP/UDP"
        else:
            return protocol.upper()
    
    def _format_address(self, rule: Dict[str, Any], direction: str) -> str:
        """Format source or destination address.
        
        Args:
            rule: Firewall rule data
            direction: "src" or "dst"
        
        Returns:
            Address string (e.g., "192.168.1.0/24", "any")
        """
        # Check for address field
        address_field = f"{direction}_address"
        if address_field in rule and rule[address_field]:
            return rule[address_field]
        
        # Check for network ID
        network_field = f"{direction}_networkconf_id"
        if network_field in rule and rule[network_field]:
            return f"network:{rule[network_field]}"
        
        # Check for firewall group
        group_field = f"{direction}_firewallgroup_ids"
        if group_field in rule and rule[group_field]:
            groups = rule[group_field]
            if groups:
                return f"group:{groups[0]}"
        
        return "any"
    
    def _format_port(self, rule: Dict[str, Any]) -> str:
        """Format destination port information.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Port string (e.g., "443", "80,443", "any")
        """
        # Check for destination port
        if "dst_port" in rule and rule["dst_port"]:
            return rule["dst_port"]
        
        # Check for port group
        if "dst_firewallgroup_ids" in rule and rule["dst_firewallgroup_ids"]:
            groups = rule["dst_firewallgroup_ids"]
            if groups:
                return f"group:{groups[0]}"
        
        return "any"


class GetFirewallRuleDetailsTool(BaseTool):
    """Get detailed information about a specific firewall rule.
    
    This tool retrieves comprehensive information about a single firewall
    rule including all configuration details, match criteria, and actions.
    Use this after listing rules to get full details about a specific rule.
    
    Example usage:
        - "Show me details for firewall rule abc123"
        - "What's the configuration of rule 5?"
        - "Get full information for the IoT blocking rule"
    """
    
    name = "unifi_get_firewall_rule_details"
    description = "Get detailed information about a specific firewall rule"
    category = "security"
    
    input_schema = {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "Firewall rule ID"
            }
        },
        "required": ["rule_id"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        rule_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get firewall rule details tool.
        
        Args:
            unifi_client: UniFi API client
            rule_id: Firewall rule ID
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted firewall rule details
        """
        try:
            # Fetch all firewall rules using endpoint routing for v2 API support
            logger.info(f"Fetching details for firewall rule: {rule_id}")
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("firewall_rules")
            rules = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
            # Find the specific rule by ID
            rule = self._find_rule(rules, rule_id)
            
            if not rule:
                raise ToolError(
                    code="RULE_NOT_FOUND",
                    message=f"Firewall rule not found: {rule_id}",
                    details=f"No firewall rule found with ID '{rule_id}'",
                    actionable_steps=[
                        "Verify the rule ID is correct",
                        "Use unifi_list_firewall_rules to see available rules",
                        "Check if the rule still exists"
                    ]
                )
            
            # Format rule details for AI consumption (data is already normalized)
            formatted_rule = self._format_normalized_rule_details(rule)
            
            logger.info(
                f"Retrieved details for firewall rule: {formatted_rule['name']} "
                f"(api_version={api_version})"
            )
            
            response = self.format_detail(
                item=formatted_rule,
                item_type="firewall_rule"
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to get firewall rule details: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "firewall rule details")
        
        except Exception as e:
            logger.error(f"Failed to get firewall rule details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall rule details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the rule ID is correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_rule(
        self,
        rules: List[Dict[str, Any]],
        rule_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a firewall rule by ID.
        
        Args:
            rules: List of firewall rule dictionaries (normalized or raw)
            rule_id: Rule ID to search for
        
        Returns:
            Rule dictionary if found, None otherwise
        """
        rule_id_lower = rule_id.lower()
        
        for rule in rules:
            # Check normalized 'id' field first, then legacy '_id' field
            rule_id_value = rule.get("id", rule.get("_id", ""))
            if str(rule_id_value).lower() == rule_id_lower:
                return rule
        
        return None
    
    def _format_normalized_rule_details(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized firewall rule data for detailed view (AI-friendly).
        
        Works with normalized rule data from ResponseNormalizer.
        
        Args:
            rule: Normalized firewall rule data
        
        Returns:
            Formatted firewall rule details
        """
        return {
            # Basic information
            "id": rule.get("id", ""),
            "name": rule.get("name", "Unnamed Rule"),
            "enabled": rule.get("enabled", False),
            
            # Action
            "action": rule.get("action", ""),
            "logging": rule.get("logging", False),
            
            # Protocol
            "protocol": rule.get("protocol", "ALL"),
            
            # Source configuration
            "source_zone": rule.get("source_zone", ""),
            "source_address": rule.get("source_address", "any"),
            
            # Destination configuration
            "destination_zone": rule.get("destination_zone", ""),
            "destination_address": rule.get("destination_address", "any"),
            "destination_port": rule.get("destination_port", "any"),
            
            # Metadata
            "api_version": rule.get("api_version", ""),
            "raw_type": rule.get("raw_type", ""),
        }
    
    def _format_rule_details(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format firewall rule data for detailed view (AI-friendly).
        
        Includes comprehensive information about the rule configuration,
        but filters out unnecessary internal fields to keep context window
        usage reasonable.
        
        Args:
            rule: Raw firewall rule data from UniFi API
        
        Returns:
            Formatted firewall rule details
        """
        details = {
            # Basic information
            "id": rule.get("_id", ""),
            "rule_index": rule.get("rule_index", 0),
            "name": rule.get("name", "Unnamed Rule"),
            "enabled": rule.get("enabled", False),
            
            # Action
            "action": rule.get("action", "").upper(),
            "logging": rule.get("logging", False),
            
            # Protocol
            "protocol": self._format_protocol_detailed(rule),
            "protocol_match_excepted": rule.get("protocol_match_excepted", False),
            
            # Source configuration
            "source": self._format_source_config(rule),
            
            # Destination configuration
            "destination": self._format_destination_config(rule),
            
            # State configuration
            "state_new": rule.get("state_new", False),
            "state_established": rule.get("state_established", False),
            "state_invalid": rule.get("state_invalid", False),
            "state_related": rule.get("state_related", False),
            
            # ICMP type (if applicable)
            "icmp_typename": rule.get("icmp_typename", ""),
            
            # IPsec (if applicable)
            "ipsec": rule.get("ipsec", ""),
        }
        
        return details
    
    def _format_protocol_detailed(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed protocol information.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Protocol configuration dictionary
        """
        protocol = rule.get("protocol", "all")
        
        result = {
            "type": protocol,
            "display": self._format_protocol_display(protocol),
        }
        
        # Add protocol-specific details
        if protocol in ["tcp", "udp", "tcp_udp"]:
            result["tcp_flags"] = rule.get("tcp_flags", [])
        
        return result
    
    def _format_protocol_display(self, protocol: str) -> str:
        """Format protocol for display.
        
        Args:
            protocol: Protocol string
        
        Returns:
            Display-friendly protocol string
        """
        if protocol == "all":
            return "ALL"
        elif protocol == "tcp_udp":
            return "TCP/UDP"
        else:
            return protocol.upper()
    
    def _format_source_config(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format source configuration.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Source configuration dictionary
        """
        config = {
            "address": rule.get("src_address", "any"),
            "network_id": rule.get("src_networkconf_id", ""),
            "firewall_groups": rule.get("src_firewallgroup_ids", []),
            "mac_address": rule.get("src_mac_address", ""),
            "port": rule.get("src_port", ""),
        }
        
        # Add display-friendly address
        config["address_display"] = self._format_address_display(
            config["address"],
            config["network_id"],
            config["firewall_groups"]
        )
        
        return config
    
    def _format_destination_config(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format destination configuration.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Destination configuration dictionary
        """
        config = {
            "address": rule.get("dst_address", "any"),
            "network_id": rule.get("dst_networkconf_id", ""),
            "firewall_groups": rule.get("dst_firewallgroup_ids", []),
            "port": rule.get("dst_port", ""),
        }
        
        # Add display-friendly address
        config["address_display"] = self._format_address_display(
            config["address"],
            config["network_id"],
            config["firewall_groups"]
        )
        
        return config
    
    def _format_address_display(
        self,
        address: str,
        network_id: str,
        firewall_groups: List[str]
    ) -> str:
        """Format address for display.
        
        Args:
            address: IP address or CIDR
            network_id: Network configuration ID
            firewall_groups: List of firewall group IDs
        
        Returns:
            Display-friendly address string
        """
        if address and address != "any":
            return address
        
        if network_id:
            return f"network:{network_id}"
        
        if firewall_groups:
            return f"group:{firewall_groups[0]}"
        
        return "any"
    
    def _format_protocol(self, rule: Dict[str, Any]) -> str:
        """Format protocol information.
        
        Args:
            rule: Firewall rule data
        
        Returns:
            Protocol string (e.g., "TCP", "UDP", "ALL")
        """
        protocol = rule.get("protocol", "all")
        
        if protocol == "all":
            return "ALL"
        elif protocol == "tcp_udp":
            return "TCP/UDP"
        else:
            return protocol.upper()



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
    
    # Fields to include in concise response format
    CONCISE_FIELDS = ["id", "name", "enabled", "type", "destination_network"]
    
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
            },
            "response_format": {
                "type": "string",
                "enum": ["detailed", "concise"],
                "description": "Response format: 'detailed' for all fields, 'concise' for essential fields only",
                "default": "detailed"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        response_format: str = "detailed",
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list traffic routes tool.
        
        Args:
            unifi_client: UniFi API client
            enabled_only: Show only enabled routes if True
            page: Page number for pagination
            page_size: Number of routes per page
            response_format: "detailed" or "concise" response format
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of traffic routes with pagination info
        """
        try:
            # Fetch routing rules using endpoint routing for v2 API support
            logger.info(
                f"Fetching traffic routes (enabled_only={enabled_only}, "
                f"page={page}, page_size={page_size}, format={response_format})"
            )
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("traffic_routes")
            
            # Extract normalized route data
            routes = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
            logger.debug(
                f"Retrieved {len(routes)} traffic routes from controller "
                f"(api_version={api_version})"
            )
            
            # Filter by enabled status if specified
            if enabled_only:
                routes = [route for route in routes if route.get("enabled", False)]
                logger.debug(f"Filtered to {len(routes)} enabled routes")
            
            # Format routes for AI consumption (summary view)
            # Data is already normalized, just extract summary fields
            formatted_routes = [
                self._format_normalized_route_summary(route)
                for route in routes
            ]
            
            # Apply pagination
            paginated_routes, total = self.paginate(formatted_routes, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_routes)} traffic routes "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            # Use format_list_with_truncation for response format support
            response = self.format_list_with_truncation(
                items=paginated_routes,
                total=total,
                page=page,
                page_size=page_size,
                response_format=response_format,
                concise_fields=self.CONCISE_FIELDS
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to list traffic routes: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "traffic routes")
        
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
    
    def _format_normalized_route_summary(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized traffic route data for summary view (AI-friendly).
        
        Works with normalized route data from ResponseNormalizer.
        
        Args:
            route: Normalized route data
        
        Returns:
            Formatted route summary
        """
        return {
            "id": route.get("id", ""),
            "name": route.get("name", "Unnamed Route"),
            "enabled": route.get("enabled", False),
            "type": route.get("route_type", "static"),
            "destination_network": route.get("destination_network", ""),
            "next_hop": route.get("next_hop", ""),
            "distance": route.get("distance", 0),
            "interface": route.get("interface", ""),
            "api_version": route.get("api_version", ""),
        }
    
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
            # Fetch all routes using endpoint routing for v2 API support
            logger.info(f"Fetching details for traffic route: {route_id}")
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("traffic_routes")
            routes = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
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
            
            # Format route details for AI consumption (data is already normalized)
            formatted_route = self._format_normalized_route_details(route)
            
            logger.info(
                f"Retrieved details for traffic route: {formatted_route['name']} "
                f"(api_version={api_version})"
            )
            
            response = self.format_detail(
                item=formatted_route,
                item_type="traffic_route"
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to get route details: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "route details")
        
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
            routes: List of route dictionaries (normalized or raw)
            route_id: Route ID to search for
        
        Returns:
            Route dictionary if found, None otherwise
        """
        route_id_lower = route_id.lower()
        
        for route in routes:
            # Check normalized 'id' field first, then legacy '_id' field
            route_id_value = route.get("id", route.get("_id", ""))
            if str(route_id_value).lower() == route_id_lower:
                return route
        
        return None
    
    def _format_normalized_route_details(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized route data for detailed view (AI-friendly).
        
        Works with normalized route data from ResponseNormalizer.
        
        Args:
            route: Normalized route data
        
        Returns:
            Formatted route details
        """
        return {
            # Basic information
            "id": route.get("id", ""),
            "name": route.get("name", "Unnamed Route"),
            "enabled": route.get("enabled", False),
            "type": route.get("route_type", "static"),
            
            # Route configuration
            "destination_network": route.get("destination_network", ""),
            "next_hop": route.get("next_hop", ""),
            "distance": route.get("distance", 0),
            "interface": route.get("interface", ""),
            
            # Metadata
            "api_version": route.get("api_version", ""),
        }
    
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
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("ips_status")
            ips_data = result.get("data", {})
            api_version = result.get("api_version", "v1")
            
            # Format IPS status from normalized data
            ips_status = self._format_normalized_ips_status(ips_data)
            
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
                f"alerts={ips_status.get('total_alerts', 0)} "
                f"(api_version={api_version})"
            )
            
            response = self.format_detail(
                item=ips_status,
                item_type="ips_status"
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to get IPS status: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "IPS status")
        
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
    
    def _format_normalized_ips_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized IPS status for AI consumption.
        
        Works with normalized IPS data from ResponseNormalizer.
        
        Args:
            data: Normalized IPS status data
        
        Returns:
            Formatted IPS status
        """
        # Get enabled state - ensure it correctly reflects the state on UniFi OS
        enabled = data.get("enabled", False)
        enabled_display = data.get("enabled_display", "yes" if enabled else "no")
        
        status = {
            # Basic configuration - ensure enabled field correctly reflects state
            "enabled": enabled_display,
            "enabled_bool": enabled,  # Keep boolean for programmatic use
            
            # Protection mode
            "protection_mode": data.get("protection_mode", "unknown"),
            
            # Threat statistics
            "threat_statistics": data.get("threat_statistics", {}),
            
            # API metadata
            "api_version": data.get("api_version", ""),
            "controller_type": data.get("controller_type", ""),
        }
        
        return status
    
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
    
    # Fields to include in concise response format
    CONCISE_FIELDS = ["id", "name", "enabled", "protocol", "destination_ip", "destination_port"]
    
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
            },
            "response_format": {
                "type": "string",
                "enum": ["detailed", "concise"],
                "description": "Response format: 'detailed' for all fields, 'concise' for essential fields only",
                "default": "detailed"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        response_format: str = "detailed",
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the list port forwards tool.
        
        Args:
            unifi_client: UniFi API client
            enabled_only: Show only enabled port forwards if True
            page: Page number for pagination
            page_size: Number of port forwards per page
            response_format: "detailed" or "concise" response format
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted list of port forwards with pagination info
        """
        try:
            # Fetch port forwarding rules using endpoint routing for v2 API support
            logger.info(
                f"Fetching port forwards (enabled_only={enabled_only}, "
                f"page={page}, page_size={page_size}, format={response_format})"
            )
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("port_forwards")
            
            # Extract normalized port forward data
            forwards = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
            logger.debug(
                f"Retrieved {len(forwards)} port forwards from controller "
                f"(api_version={api_version})"
            )
            
            # Filter by enabled status if specified
            if enabled_only:
                forwards = [fwd for fwd in forwards if fwd.get("enabled", False)]
                logger.debug(f"Filtered to {len(forwards)} enabled port forwards")
            
            # Format port forwards for AI consumption (summary view)
            # Data is already normalized, just extract summary fields
            formatted_forwards = [
                self._format_normalized_forward_summary(forward)
                for forward in forwards
            ]
            
            # Apply pagination
            paginated_forwards, total = self.paginate(formatted_forwards, page, page_size)
            
            logger.info(
                f"Returning {len(paginated_forwards)} port forwards "
                f"(page {page}/{(total + page_size - 1) // page_size}, total={total})"
            )
            
            # Use format_list_with_truncation for response format support
            response = self.format_list_with_truncation(
                items=paginated_forwards,
                total=total,
                page=page,
                page_size=page_size,
                response_format=response_format,
                concise_fields=self.CONCISE_FIELDS
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to list port forwards: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "port forwards")
        
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
    
    def _format_normalized_forward_summary(self, forward: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized port forward data for summary view (AI-friendly).
        
        Works with normalized port forward data from ResponseNormalizer.
        
        Args:
            forward: Normalized port forward data
        
        Returns:
            Formatted port forward summary
        """
        return {
            "id": forward.get("id", ""),
            "name": forward.get("name", "Unnamed Port Forward"),
            "enabled": forward.get("enabled", False),
            "protocol": forward.get("protocol", "TCP"),
            "source_ip": forward.get("source_ip", "any"),
            "destination_ip": forward.get("destination_ip", ""),
            "destination_port": forward.get("destination_port", ""),
            "external_port": forward.get("source_port", ""),
            "api_version": forward.get("api_version", ""),
        }
    
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
            # Fetch all port forwards using endpoint routing for v2 API support
            logger.info(f"Fetching details for port forward: {forward_id}")
            
            # Use get_security_data for automatic endpoint routing and normalization
            result = await unifi_client.get_security_data("port_forwards")
            forwards = result.get("data", [])
            api_version = result.get("api_version", "v1")
            
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
            
            # Format port forward details for AI consumption (data is already normalized)
            formatted_forward = self._format_normalized_forward_details(forward)
            
            logger.info(
                f"Retrieved details for port forward: {formatted_forward['name']} "
                f"(api_version={api_version})"
            )
            
            response = self.format_detail(
                item=formatted_forward,
                item_type="port_forward"
            )
            
            # Add api_version to response metadata
            response["api_version"] = api_version
            response["controller_type"] = result.get("controller_type", "unknown")
            
            return response
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except EndpointError as e:
            # Handle v2 endpoint failures gracefully with clear error messages
            logger.error(f"Failed to get port forward details: {e}", exc_info=True)
            raise _handle_endpoint_error(e, "port forward details")
        
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
            forwards: List of port forward dictionaries (normalized or raw)
            forward_id: Port forward ID to search for
        
        Returns:
            Port forward dictionary if found, None otherwise
        """
        forward_id_lower = forward_id.lower()
        
        for forward in forwards:
            # Check normalized 'id' field first, then legacy '_id' field
            forward_id_value = forward.get("id", forward.get("_id", ""))
            if str(forward_id_value).lower() == forward_id_lower:
                return forward
        
        return None
    
    def _format_normalized_forward_details(self, forward: Dict[str, Any]) -> Dict[str, Any]:
        """Format normalized port forward data for detailed view (AI-friendly).
        
        Works with normalized port forward data from ResponseNormalizer.
        
        Args:
            forward: Normalized port forward data
        
        Returns:
            Formatted port forward details
        """
        return {
            # Basic information
            "id": forward.get("id", ""),
            "name": forward.get("name", "Unnamed Port Forward"),
            "enabled": forward.get("enabled", False),
            
            # Protocol and ports
            "protocol": forward.get("protocol", "TCP"),
            "external_port": forward.get("source_port", ""),
            "destination_ip": forward.get("destination_ip", ""),
            "destination_port": forward.get("destination_port", ""),
            
            # Source restrictions
            "source_ip": forward.get("source_ip", "any"),
            
            # Metadata
            "api_version": forward.get("api_version", ""),
        }
    
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
