"""Migration support tools for UniFi MCP server.

This module provides tools to support network infrastructure migration:
- Get DHCP server status and lease information
- Verify connectivity across VLANs
- Export network configuration for backup

These tools help with planning and validating network migrations,
particularly for the homelab network infrastructure migration project.

Updated to support v2 API endpoints on UniFi OS devices while maintaining
backward compatibility with traditional controllers.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..api import ControllerType
from ..utils.logging import get_logger


logger = get_logger(__name__)


class GetDHCPStatusTool(BaseTool):
    """Get DHCP server status and lease information.
    
    This tool retrieves DHCP server configuration and active leases
    from the UniFi controller. Useful for understanding IP address
    assignments and planning network migrations.
    
    Example usage:
        - "What's the DHCP status?"
        - "Show me DHCP leases"
        - "What IP addresses are assigned?"
        - "Is DHCP enabled on the Core VLAN?"
    """
    
    name = "unifi_get_dhcp_status"
    description = "Get DHCP server status and lease information"
    category = "migration"
    
    input_schema = {
        "type": "object",
        "properties": {
            "network_id": {
                "type": "string",
                "description": "Optional network ID to filter DHCP info for specific network"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        network_id: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the get DHCP status tool.
        
        Args:
            unifi_client: UniFi API client
            network_id: Optional network ID to filter results
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Formatted DHCP status and lease information
        """
        try:
            logger.info(f"Fetching DHCP status (network_id={network_id})")
            
            # Fetch network configuration to get DHCP settings
            networks_response = await unifi_client.get(f"/api/s/{{site}}/rest/networkconf")
            networks = networks_response.get("data", [])
            
            # Filter by network ID if specified
            if network_id:
                networks = [n for n in networks if n.get("_id") == network_id]
                if not networks:
                    raise ToolError(
                        code="NETWORK_NOT_FOUND",
                        message=f"Network not found: {network_id}",
                        details=f"No network found with ID '{network_id}'",
                        actionable_steps=[
                            "Verify the network ID is correct",
                            "Use unifi_list_networks to see available networks"
                        ]
                    )
            
            # Fetch DHCP leases
            leases_response = await unifi_client.get(f"/api/s/{{site}}/stat/sta")
            clients = leases_response.get("data", [])
            
            # Format DHCP status for each network
            dhcp_status = []
            for network in networks:
                network_status = self._format_network_dhcp_status(network, clients)
                dhcp_status.append(network_status)
            
            logger.info(f"Retrieved DHCP status for {len(dhcp_status)} network(s)")
            
            return self.format_success(
                data={
                    "networks": dhcp_status,
                    "total_networks": len(dhcp_status),
                    "total_active_leases": sum(n["active_leases"] for n in dhcp_status)
                },
                message="DHCP status retrieved successfully"
            )
        
        except ToolError:
            raise
        
        except Exception as e:
            logger.error(f"Failed to get DHCP status: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve DHCP status",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _format_network_dhcp_status(
        self,
        network: Dict[str, Any],
        clients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format DHCP status for a single network.
        
        Args:
            network: Network configuration data
            clients: List of all clients (for lease counting)
        
        Returns:
            Formatted DHCP status for the network
        """
        network_id = network.get("_id", "")
        network_name = network.get("name", "Unnamed Network")
        
        # Check if DHCP is enabled
        dhcp_enabled = network.get("dhcpd_enabled", False)
        
        # Get DHCP configuration
        dhcp_config = {
            "enabled": dhcp_enabled,
            "start": network.get("dhcpd_start", ""),
            "stop": network.get("dhcpd_stop", ""),
            "lease_time": network.get("dhcpd_leasetime", 86400),
            "dns_servers": network.get("dhcpd_dns", []),
            "gateway": network.get("dhcpd_gateway", ""),
        }
        
        # Count active leases for this network
        network_subnet = network.get("ip_subnet", "")
        active_leases = self._count_network_leases(clients, network_subnet)
        
        return {
            "network_id": network_id,
            "network_name": network_name,
            "vlan_id": network.get("vlan", ""),
            "subnet": network_subnet,
            "dhcp_config": dhcp_config,
            "active_leases": active_leases,
        }
    
    def _count_network_leases(
        self,
        clients: List[Dict[str, Any]],
        subnet: str
    ) -> int:
        """Count active DHCP leases for a network subnet.
        
        Args:
            clients: List of all clients
            subnet: Network subnet (e.g., "192.168.10.0/24")
        
        Returns:
            Number of active leases
        """
        if not subnet:
            return 0
        
        # Simple subnet matching (could be improved with ipaddress module)
        subnet_prefix = subnet.split("/")[0].rsplit(".", 1)[0]
        
        count = 0
        for client in clients:
            ip = client.get("ip", "")
            if ip and ip.startswith(subnet_prefix):
                # Check if it's a DHCP lease (not static)
                if client.get("use_fixedip", False) is False:
                    count += 1
        
        return count


class VerifyVLANConnectivityTool(BaseTool):
    """Verify connectivity across VLANs.
    
    This tool checks if connectivity is possible between two VLANs
    based on firewall rules and routing configuration. Useful for
    validating network segmentation and troubleshooting connectivity
    issues during migration.
    
    Note: This performs a configuration-based check, not an actual
    ping or connectivity test.
    
    Example usage:
        - "Can the Core VLAN reach the IoT VLAN?"
        - "Verify connectivity from VLAN 10 to VLAN 30"
        - "Check if Guest network can access Core network"
    """
    
    name = "unifi_verify_vlan_connectivity"
    description = "Verify connectivity across VLANs based on firewall rules"
    category = "migration"
    
    input_schema = {
        "type": "object",
        "properties": {
            "source_vlan": {
                "type": "string",
                "description": "Source VLAN ID or network name"
            },
            "destination_vlan": {
                "type": "string",
                "description": "Destination VLAN ID or network name"
            }
        },
        "required": ["source_vlan", "destination_vlan"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        source_vlan: str,
        destination_vlan: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the verify VLAN connectivity tool.
        
        Args:
            unifi_client: UniFi API client
            source_vlan: Source VLAN ID or network name
            destination_vlan: Destination VLAN ID or network name
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Connectivity verification result with firewall rules
        """
        try:
            logger.info(
                f"Verifying VLAN connectivity: {source_vlan} -> {destination_vlan}"
            )
            
            # Fetch networks to resolve VLAN names/IDs
            networks_response = await unifi_client.get(f"/api/s/{{site}}/rest/networkconf")
            networks = networks_response.get("data", [])
            
            # Resolve source and destination networks
            source_network = self._find_network(networks, source_vlan)
            dest_network = self._find_network(networks, destination_vlan)
            
            if not source_network:
                raise ToolError(
                    code="NETWORK_NOT_FOUND",
                    message=f"Source network not found: {source_vlan}",
                    details=f"No network found matching '{source_vlan}'",
                    actionable_steps=[
                        "Verify the VLAN ID or network name is correct",
                        "Use unifi_list_networks to see available networks"
                    ]
                )
            
            if not dest_network:
                raise ToolError(
                    code="NETWORK_NOT_FOUND",
                    message=f"Destination network not found: {destination_vlan}",
                    details=f"No network found matching '{destination_vlan}'",
                    actionable_steps=[
                        "Verify the VLAN ID or network name is correct",
                        "Use unifi_list_networks to see available networks"
                    ]
                )
            
            # Fetch firewall rules using endpoint routing for v2 API support
            try:
                result = await unifi_client.get_security_data("firewall_rules")
                firewall_rules = result.get("data", [])
                api_version = result.get("api_version", "v1")
                logger.debug(f"Retrieved firewall rules via endpoint routing (API {api_version})")
            except Exception as e:
                logger.warning(f"Failed to get firewall rules via routing, falling back: {e}")
                # Fallback to direct endpoint
                rules_response = await unifi_client.get(f"/api/s/{{site}}/rest/firewallrule")
                firewall_rules = rules_response.get("data", [])
                api_version = "v1"
            
            # Analyze connectivity
            connectivity_result = self._analyze_connectivity(
                source_network,
                dest_network,
                firewall_rules
            )
            
            # Add API version to result
            connectivity_result["api_version"] = api_version
            
            logger.info(
                f"VLAN connectivity check complete: "
                f"{connectivity_result['connectivity_status']}"
            )
            
            return self.format_success(
                data=connectivity_result,
                message="VLAN connectivity verification complete"
            )
        
        except ToolError:
            raise
        
        except Exception as e:
            logger.error(f"Failed to verify VLAN connectivity: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to verify VLAN connectivity",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify VLAN IDs or network names are correct",
                    "Check server logs for details"
                ]
            )
    
    def _find_network(
        self,
        networks: List[Dict[str, Any]],
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """Find a network by VLAN ID or name.
        
        Args:
            networks: List of network configurations
            identifier: VLAN ID or network name
        
        Returns:
            Network configuration if found, None otherwise
        """
        identifier_lower = identifier.lower()
        
        for network in networks:
            # Check VLAN ID
            vlan = str(network.get("vlan", ""))
            if vlan == identifier:
                return network
            
            # Check network name
            name = network.get("name", "").lower()
            if name == identifier_lower:
                return network
            
            # Check network ID
            network_id = network.get("_id", "").lower()
            if network_id == identifier_lower:
                return network
        
        return None
    
    def _analyze_connectivity(
        self,
        source_network: Dict[str, Any],
        dest_network: Dict[str, Any],
        firewall_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze connectivity between two networks based on firewall rules.
        
        Args:
            source_network: Source network configuration
            dest_network: Destination network configuration
            firewall_rules: List of firewall rules
        
        Returns:
            Connectivity analysis result
        """
        source_subnet = source_network.get("ip_subnet", "")
        dest_subnet = dest_network.get("ip_subnet", "")
        
        # Find relevant firewall rules
        relevant_rules = self._find_relevant_rules(
            firewall_rules,
            source_subnet,
            dest_subnet
        )
        
        # Determine connectivity status
        connectivity_status = self._determine_connectivity_status(relevant_rules)
        
        return {
            "source_network": {
                "id": source_network.get("_id", ""),
                "name": source_network.get("name", ""),
                "vlan": source_network.get("vlan", ""),
                "subnet": source_subnet,
            },
            "destination_network": {
                "id": dest_network.get("_id", ""),
                "name": dest_network.get("name", ""),
                "vlan": dest_network.get("vlan", ""),
                "subnet": dest_subnet,
            },
            "connectivity_status": connectivity_status,
            "relevant_firewall_rules": relevant_rules,
            "rule_count": len(relevant_rules),
        }
    
    def _find_relevant_rules(
        self,
        firewall_rules: List[Dict[str, Any]],
        source_subnet: str,
        dest_subnet: str
    ) -> List[Dict[str, Any]]:
        """Find firewall rules relevant to the connectivity check.
        
        Args:
            firewall_rules: List of all firewall rules
            source_subnet: Source network subnet
            dest_subnet: Destination network subnet
        
        Returns:
            List of relevant firewall rules
        """
        relevant_rules = []
        
        for rule in firewall_rules:
            # Only consider enabled rules
            if not rule.get("enabled", False):
                continue
            
            # Check if rule applies to these networks
            # This is a simplified check - real implementation would need
            # more sophisticated subnet matching
            src_address = rule.get("src_address", "")
            dst_address = rule.get("dst_address", "")
            
            # Check for "any" rules or matching subnets
            if (src_address in ["", "any"] or source_subnet.startswith(src_address.split("/")[0])) and \
               (dst_address in ["", "any"] or dest_subnet.startswith(dst_address.split("/")[0])):
                relevant_rules.append({
                    "id": rule.get("_id", ""),
                    "name": rule.get("name", "Unnamed Rule"),
                    "action": rule.get("action", "").upper(),
                    "protocol": rule.get("protocol", "all").upper(),
                    "source": src_address or "any",
                    "destination": dst_address or "any",
                })
        
        return relevant_rules
    
    def _determine_connectivity_status(
        self,
        relevant_rules: List[Dict[str, Any]]
    ) -> str:
        """Determine connectivity status based on firewall rules.
        
        Args:
            relevant_rules: List of relevant firewall rules
        
        Returns:
            Connectivity status string
        """
        if not relevant_rules:
            return "UNKNOWN - No explicit firewall rules found"
        
        # Check for explicit ACCEPT rules
        has_accept = any(rule["action"] == "ACCEPT" for rule in relevant_rules)
        
        # Check for explicit DROP/REJECT rules
        has_block = any(rule["action"] in ["DROP", "REJECT"] for rule in relevant_rules)
        
        if has_accept and not has_block:
            return "ALLOWED - Explicit allow rules found"
        elif has_block and not has_accept:
            return "BLOCKED - Explicit block rules found"
        elif has_accept and has_block:
            return "MIXED - Both allow and block rules found (order matters)"
        else:
            return "UNKNOWN - No definitive rules found"


class ExportConfigurationTool(BaseTool):
    """Export network configuration for backup.
    
    This tool exports the current network configuration including
    networks, firewall rules, routing, and other settings. Useful
    for creating backups before making changes or for documentation.
    
    By default, credentials are excluded from the export for security.
    
    Example usage:
        - "Export my network configuration"
        - "Create a backup of current settings"
        - "Export config for documentation"
    """
    
    name = "unifi_export_configuration"
    description = "Export network configuration for backup (without credentials by default)"
    category = "migration"
    
    input_schema = {
        "type": "object",
        "properties": {
            "include_credentials": {
                "type": "boolean",
                "description": "Include credentials in export (NOT recommended)",
                "default": False
            },
            "include_networks": {
                "type": "boolean",
                "description": "Include network configurations",
                "default": True
            },
            "include_firewall_rules": {
                "type": "boolean",
                "description": "Include firewall rules",
                "default": True
            },
            "include_routing": {
                "type": "boolean",
                "description": "Include routing rules",
                "default": True
            },
            "include_port_forwards": {
                "type": "boolean",
                "description": "Include port forwarding rules",
                "default": True
            },
            "include_wlans": {
                "type": "boolean",
                "description": "Include wireless network configurations",
                "default": True
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        include_credentials: bool = False,
        include_networks: bool = True,
        include_firewall_rules: bool = True,
        include_routing: bool = True,
        include_port_forwards: bool = True,
        include_wlans: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the export configuration tool.
        
        Args:
            unifi_client: UniFi API client
            include_credentials: Include credentials if True (NOT recommended)
            include_networks: Include network configurations
            include_firewall_rules: Include firewall rules
            include_routing: Include routing rules
            include_port_forwards: Include port forwarding rules
            include_wlans: Include WLAN configurations
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Exported configuration data with controller_type and api_version metadata
        """
        try:
            logger.info("Exporting network configuration")
            
            if include_credentials:
                logger.warning(
                    "Configuration export includes credentials - "
                    "handle with care!"
                )
            
            # Get controller type for metadata
            controller_type = unifi_client.controller_type
            controller_type_str = controller_type.value if controller_type else "unknown"
            
            # Track API versions used for each section
            api_versions_used = {}
            
            export_data = {
                "export_timestamp": self._get_timestamp(),
                "controller_type": controller_type_str,
                "api_version": "v2" if controller_type == ControllerType.UNIFI_OS else "v1",
                "export_options": {
                    "include_credentials": include_credentials,
                    "include_networks": include_networks,
                    "include_firewall_rules": include_firewall_rules,
                    "include_routing": include_routing,
                    "include_port_forwards": include_port_forwards,
                    "include_wlans": include_wlans,
                },
                "configuration": {}
            }
            
            # Export networks (uses standard endpoint, not security data)
            if include_networks:
                networks_response = await unifi_client.get(
                    f"/api/s/{{site}}/rest/networkconf"
                )
                networks = networks_response.get("data", [])
                export_data["configuration"]["networks"] = [
                    self._sanitize_config(net, include_credentials)
                    for net in networks
                ]
                api_versions_used["networks"] = "v1"  # Networks use standard endpoint
                logger.debug(f"Exported {len(networks)} networks")
            
            # Export firewall rules using endpoint routing
            if include_firewall_rules:
                try:
                    result = await unifi_client.get_security_data("firewall_rules")
                    rules = result.get("data", [])
                    api_version = result.get("api_version", "v1")
                    export_data["configuration"]["firewall_rules"] = [
                        self._sanitize_config(rule, include_credentials)
                        for rule in rules
                    ]
                    api_versions_used["firewall_rules"] = api_version
                    logger.debug(f"Exported {len(rules)} firewall rules (API {api_version})")
                except Exception as e:
                    logger.warning(f"Failed to export firewall rules via routing, falling back: {e}")
                    # Fallback to direct endpoint
                    rules_response = await unifi_client.get(
                        f"/api/s/{{site}}/rest/firewallrule"
                    )
                    rules = rules_response.get("data", [])
                    export_data["configuration"]["firewall_rules"] = [
                        self._sanitize_config(rule, include_credentials)
                        for rule in rules
                    ]
                    api_versions_used["firewall_rules"] = "v1"
                    logger.debug(f"Exported {len(rules)} firewall rules (fallback)")
            
            # Export routing rules using endpoint routing
            if include_routing:
                try:
                    result = await unifi_client.get_security_data("traffic_routes")
                    routes = result.get("data", [])
                    api_version = result.get("api_version", "v1")
                    export_data["configuration"]["routing_rules"] = [
                        self._sanitize_config(route, include_credentials)
                        for route in routes
                    ]
                    api_versions_used["routing_rules"] = api_version
                    logger.debug(f"Exported {len(routes)} routing rules (API {api_version})")
                except Exception as e:
                    logger.warning(f"Failed to export routing rules via routing, falling back: {e}")
                    # Fallback to direct endpoint
                    routing_response = await unifi_client.get(
                        f"/api/s/{{site}}/rest/routing"
                    )
                    routes = routing_response.get("data", [])
                    export_data["configuration"]["routing_rules"] = [
                        self._sanitize_config(route, include_credentials)
                        for route in routes
                    ]
                    api_versions_used["routing_rules"] = "v1"
                    logger.debug(f"Exported {len(routes)} routing rules (fallback)")
            
            # Export port forwards using endpoint routing
            if include_port_forwards:
                try:
                    result = await unifi_client.get_security_data("port_forwards")
                    forwards = result.get("data", [])
                    api_version = result.get("api_version", "v1")
                    export_data["configuration"]["port_forwards"] = [
                        self._sanitize_config(forward, include_credentials)
                        for forward in forwards
                    ]
                    api_versions_used["port_forwards"] = api_version
                    logger.debug(f"Exported {len(forwards)} port forwards (API {api_version})")
                except Exception as e:
                    logger.warning(f"Failed to export port forwards via routing, falling back: {e}")
                    # Fallback to direct endpoint
                    forwards_response = await unifi_client.get(
                        f"/api/s/{{site}}/rest/portforward"
                    )
                    forwards = forwards_response.get("data", [])
                    export_data["configuration"]["port_forwards"] = [
                        self._sanitize_config(forward, include_credentials)
                        for forward in forwards
                    ]
                    api_versions_used["port_forwards"] = "v1"
                    logger.debug(f"Exported {len(forwards)} port forwards (fallback)")
            
            # Export WLANs (uses standard endpoint, not security data)
            if include_wlans:
                wlans_response = await unifi_client.get(
                    f"/api/s/{{site}}/rest/wlanconf"
                )
                wlans = wlans_response.get("data", [])
                export_data["configuration"]["wlans"] = [
                    self._sanitize_config(wlan, include_credentials)
                    for wlan in wlans
                ]
                api_versions_used["wlans"] = "v1"  # WLANs use standard endpoint
                logger.debug(f"Exported {len(wlans)} WLANs")
            
            # Add API versions used to metadata
            export_data["api_versions_used"] = api_versions_used
            
            logger.info(
                f"Configuration export complete (controller_type={controller_type_str})"
            )
            
            return self.format_success(
                data=export_data,
                message="Configuration exported successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to export configuration",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify network connectivity",
                    "Check server logs for details"
                ]
            )
    
    def _sanitize_config(
        self,
        config: Dict[str, Any],
        include_credentials: bool
    ) -> Dict[str, Any]:
        """Sanitize configuration data by removing sensitive fields.
        
        Args:
            config: Configuration dictionary
            include_credentials: Keep credentials if True
        
        Returns:
            Sanitized configuration dictionary
        """
        if include_credentials:
            return config
        
        # Create a copy to avoid modifying original
        sanitized = config.copy()
        
        # List of sensitive fields to remove
        sensitive_fields = [
            "x_passphrase",
            "x_password",
            "password",
            "passphrase",
            "wpa_enc",
            "wpa_mode",
            "wep_idx",
            "radius_secret",
            "radius_das_secret",
        ]
        
        # Remove sensitive fields
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
        
        return sanitized
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format.
        
        Returns:
            ISO format timestamp string
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
