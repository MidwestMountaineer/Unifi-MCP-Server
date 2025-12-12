"""Write operation tools for UniFi MCP server.

This module provides tools for making changes to the UniFi configuration:
- Toggle firewall rules (enable/disable)
- Create new firewall rules
- Update existing firewall rules

All write operations require explicit confirmation and are logged with full details.
These tools are disabled by default and must be explicitly enabled in configuration.

SECURITY WARNING: These tools can modify your network configuration. Use with caution.
"""

from typing import Any, Dict, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ToggleFirewallRuleTool(BaseTool):
    """Toggle a firewall rule (enable/disable).
    
    This tool enables or disables an existing firewall rule. This is useful
    for temporarily disabling rules without deleting them, or re-enabling
    previously disabled rules.
    
    REQUIRES CONFIRMATION: This is a write operation that modifies your
    firewall configuration. You must set confirm=true to execute.
    
    Example usage:
        - "Disable firewall rule abc123"
        - "Enable the IoT blocking rule"
        - "Toggle rule xyz789"
    """
    
    name = "unifi_toggle_firewall_rule"
    description = "Toggle a firewall rule (enable/disable)"
    category = "write_operations"
    requires_confirmation = True
    
    input_schema = {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "Firewall rule ID to toggle"
            },
            "enabled": {
                "type": "boolean",
                "description": "Set to true to enable, false to disable"
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be set to true to confirm this write operation"
            }
        },
        "required": ["rule_id", "enabled", "confirm"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        rule_id: str,
        enabled: bool,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the toggle firewall rule tool.
        
        Args:
            unifi_client: UniFi API client
            rule_id: Firewall rule ID to toggle
            enabled: True to enable, False to disable
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Success response with updated rule information
        """
        try:
            # Fetch current rule to verify it exists
            logger.info(f"Fetching firewall rule {rule_id} for toggle operation")
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/firewallrule")
            rules = response.get("data", [])
            
            # Find the specific rule
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
            
            # Check if rule is already in desired state
            current_state = rule.get("enabled", False)
            if current_state == enabled:
                action = "enabled" if enabled else "disabled"
                logger.info(f"Rule {rule_id} is already {action}")
                return self.format_success(
                    {
                        "rule_id": rule_id,
                        "rule_name": rule.get("name", "Unnamed Rule"),
                        "enabled": enabled,
                        "changed": False
                    },
                    message=f"Firewall rule is already {action}"
                )
            
            # Update the rule
            rule["enabled"] = enabled
            
            # Send update to UniFi controller
            action = "Enabling" if enabled else "Disabling"
            logger.info(f"{action} firewall rule {rule_id}: {rule.get('name', 'Unnamed Rule')}")
            
            update_response = await unifi_client.put(
                f"/api/s/{{site}}/rest/firewallrule/{rule_id}",
                data=rule
            )
            
            # Verify update was successful
            if update_response.get("meta", {}).get("rc") != "ok":
                raise ToolError(
                    code="UPDATE_FAILED",
                    message="Failed to update firewall rule",
                    details=f"UniFi controller returned error: {update_response}",
                    actionable_steps=[
                        "Check UniFi controller logs",
                        "Verify you have permission to modify firewall rules",
                        "Try again or contact administrator"
                    ]
                )
            
            action_past = "enabled" if enabled else "disabled"
            logger.info(f"Successfully {action_past} firewall rule {rule_id}")
            
            return self.format_success(
                {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name", "Unnamed Rule"),
                    "enabled": enabled,
                    "changed": True,
                    "previous_state": current_state
                },
                message=f"Firewall rule successfully {action_past}"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to toggle firewall rule: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to toggle firewall rule",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify you have permission to modify firewall rules",
                    "Check server logs for details",
                    "Consider rolling back if partial changes were made"
                ]
            )
    
    def _find_rule(
        self,
        rules: list,
        rule_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a firewall rule by ID.
        
        Args:
            rules: List of firewall rule dictionaries
            rule_id: Rule ID to search for
        
        Returns:
            Rule dictionary if found, None otherwise
        """
        rule_id_lower = rule_id.lower()
        
        for rule in rules:
            if rule.get("_id", "").lower() == rule_id_lower:
                return rule
        
        return None


class CreateFirewallRuleTool(BaseTool):
    """Create a new firewall rule.
    
    This tool creates a new firewall rule with the specified configuration.
    You can define the action (accept/drop/reject), protocol, source/destination
    addresses, ports, and other match criteria.
    
    REQUIRES CONFIRMATION: This is a write operation that modifies your
    firewall configuration. You must set confirm=true to execute.
    
    Example usage:
        - "Create a firewall rule to block IoT devices from accessing the internet"
        - "Add a rule to allow SSH from management network"
        - "Create a rule to drop all traffic from guest network to core network"
    """
    
    name = "unifi_create_firewall_rule"
    description = "Create a new firewall rule"
    category = "write_operations"
    requires_confirmation = True
    
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name for the firewall rule"
            },
            "action": {
                "type": "string",
                "enum": ["accept", "drop", "reject"],
                "description": "Action to take (accept, drop, or reject)"
            },
            "protocol": {
                "type": "string",
                "enum": ["all", "tcp", "udp", "tcp_udp", "icmp"],
                "description": "Protocol to match",
                "default": "all"
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the rule should be enabled",
                "default": True
            },
            "logging": {
                "type": "boolean",
                "description": "Whether to log matches",
                "default": False
            },
            "src_address": {
                "type": "string",
                "description": "Source IP address or CIDR (optional)"
            },
            "dst_address": {
                "type": "string",
                "description": "Destination IP address or CIDR (optional)"
            },
            "dst_port": {
                "type": "string",
                "description": "Destination port or port range (optional)"
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be set to true to confirm this write operation"
            }
        },
        "required": ["name", "action", "confirm"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        name: str,
        action: str,
        protocol: str = "all",
        enabled: bool = True,
        logging: bool = False,
        src_address: Optional[str] = None,
        dst_address: Optional[str] = None,
        dst_port: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the create firewall rule tool.
        
        Args:
            unifi_client: UniFi API client
            name: Name for the firewall rule
            action: Action to take (accept, drop, reject)
            protocol: Protocol to match
            enabled: Whether the rule should be enabled
            logging: Whether to log matches
            src_address: Source IP address or CIDR
            dst_address: Destination IP address or CIDR
            dst_port: Destination port or port range
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Success response with created rule information
        """
        try:
            # Build rule configuration
            logger.info(f"Creating firewall rule: {name}")
            
            rule_config = {
                "name": name,
                "action": action.lower(),
                "protocol": protocol.lower(),
                "enabled": enabled,
                "logging": logging,
                "ruleset": "WAN_IN",  # Default ruleset
            }
            
            # Add optional fields
            if src_address:
                rule_config["src_address"] = src_address
            
            if dst_address:
                rule_config["dst_address"] = dst_address
            
            if dst_port:
                rule_config["dst_port"] = dst_port
            
            # Send create request to UniFi controller
            logger.info(f"Sending create request for firewall rule: {name}")
            logger.debug(f"Rule configuration: {rule_config}")
            
            response = await unifi_client.post(
                f"/api/s/{{site}}/rest/firewallrule",
                data=rule_config
            )
            
            # Verify creation was successful
            if response.get("meta", {}).get("rc") != "ok":
                raise ToolError(
                    code="CREATE_FAILED",
                    message="Failed to create firewall rule",
                    details=f"UniFi controller returned error: {response}",
                    actionable_steps=[
                        "Check UniFi controller logs",
                        "Verify you have permission to create firewall rules",
                        "Verify the rule configuration is valid",
                        "Try again or contact administrator"
                    ]
                )
            
            # Extract created rule data
            created_rule = response.get("data", [{}])[0]
            rule_id = created_rule.get("_id", "")
            
            logger.info(f"Successfully created firewall rule {rule_id}: {name}")
            
            return self.format_success(
                {
                    "rule_id": rule_id,
                    "rule_name": name,
                    "action": action,
                    "protocol": protocol,
                    "enabled": enabled,
                    "logging": logging,
                    "src_address": src_address or "any",
                    "dst_address": dst_address or "any",
                    "dst_port": dst_port or "any"
                },
                message=f"Firewall rule '{name}' created successfully"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to create firewall rule: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to create firewall rule",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify you have permission to create firewall rules",
                    "Verify the rule configuration is valid",
                    "Check server logs for details"
                ]
            )


class UpdateFirewallRuleTool(BaseTool):
    """Update an existing firewall rule.
    
    This tool updates the configuration of an existing firewall rule.
    You can modify the action, protocol, addresses, ports, and other
    match criteria. Only specified fields will be updated.
    
    REQUIRES CONFIRMATION: This is a write operation that modifies your
    firewall configuration. You must set confirm=true to execute.
    
    Example usage:
        - "Update firewall rule abc123 to drop instead of reject"
        - "Change the destination port of rule xyz789 to 443"
        - "Update the IoT blocking rule to also log matches"
    """
    
    name = "unifi_update_firewall_rule"
    description = "Update an existing firewall rule"
    category = "write_operations"
    requires_confirmation = True
    
    input_schema = {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "Firewall rule ID to update"
            },
            "name": {
                "type": "string",
                "description": "New name for the rule (optional)"
            },
            "action": {
                "type": "string",
                "enum": ["accept", "drop", "reject"],
                "description": "New action (optional)"
            },
            "protocol": {
                "type": "string",
                "enum": ["all", "tcp", "udp", "tcp_udp", "icmp"],
                "description": "New protocol (optional)"
            },
            "enabled": {
                "type": "boolean",
                "description": "New enabled state (optional)"
            },
            "logging": {
                "type": "boolean",
                "description": "New logging state (optional)"
            },
            "src_address": {
                "type": "string",
                "description": "New source address (optional)"
            },
            "dst_address": {
                "type": "string",
                "description": "New destination address (optional)"
            },
            "dst_port": {
                "type": "string",
                "description": "New destination port (optional)"
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be set to true to confirm this write operation"
            }
        },
        "required": ["rule_id", "confirm"]
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        rule_id: str,
        name: Optional[str] = None,
        action: Optional[str] = None,
        protocol: Optional[str] = None,
        enabled: Optional[bool] = None,
        logging: Optional[bool] = None,
        src_address: Optional[str] = None,
        dst_address: Optional[str] = None,
        dst_port: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the update firewall rule tool.
        
        Args:
            unifi_client: UniFi API client
            rule_id: Firewall rule ID to update
            name: New name for the rule
            action: New action
            protocol: New protocol
            enabled: New enabled state
            logging: New logging state
            src_address: New source address
            dst_address: New destination address
            dst_port: New destination port
            **kwargs: Additional arguments (ignored)
        
        Returns:
            Success response with updated rule information
        """
        try:
            # Fetch current rule
            logger.info(f"Fetching firewall rule {rule_id} for update operation")
            
            response = await unifi_client.get(f"/api/s/{{site}}/rest/firewallrule")
            rules = response.get("data", [])
            
            # Find the specific rule
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
            
            # Track changes
            changes = {}
            
            # Update fields if provided
            if name is not None and name != rule.get("name"):
                changes["name"] = {"old": rule.get("name"), "new": name}
                rule["name"] = name
            
            if action is not None and action.lower() != rule.get("action"):
                changes["action"] = {"old": rule.get("action"), "new": action.lower()}
                rule["action"] = action.lower()
            
            if protocol is not None and protocol.lower() != rule.get("protocol"):
                changes["protocol"] = {"old": rule.get("protocol"), "new": protocol.lower()}
                rule["protocol"] = protocol.lower()
            
            if enabled is not None and enabled != rule.get("enabled"):
                changes["enabled"] = {"old": rule.get("enabled"), "new": enabled}
                rule["enabled"] = enabled
            
            if logging is not None and logging != rule.get("logging"):
                changes["logging"] = {"old": rule.get("logging"), "new": logging}
                rule["logging"] = logging
            
            if src_address is not None and src_address != rule.get("src_address"):
                changes["src_address"] = {"old": rule.get("src_address"), "new": src_address}
                rule["src_address"] = src_address
            
            if dst_address is not None and dst_address != rule.get("dst_address"):
                changes["dst_address"] = {"old": rule.get("dst_address"), "new": dst_address}
                rule["dst_address"] = dst_address
            
            if dst_port is not None and dst_port != rule.get("dst_port"):
                changes["dst_port"] = {"old": rule.get("dst_port"), "new": dst_port}
                rule["dst_port"] = dst_port
            
            # Check if any changes were made
            if not changes:
                logger.info(f"No changes needed for firewall rule {rule_id}")
                return self.format_success(
                    {
                        "rule_id": rule_id,
                        "rule_name": rule.get("name", "Unnamed Rule"),
                        "changed": False
                    },
                    message="No changes needed - rule already matches desired configuration"
                )
            
            # Send update to UniFi controller
            logger.info(f"Updating firewall rule {rule_id}: {rule.get('name', 'Unnamed Rule')}")
            logger.debug(f"Changes: {changes}")
            
            update_response = await unifi_client.put(
                f"/api/s/{{site}}/rest/firewallrule/{rule_id}",
                data=rule
            )
            
            # Verify update was successful
            if update_response.get("meta", {}).get("rc") != "ok":
                raise ToolError(
                    code="UPDATE_FAILED",
                    message="Failed to update firewall rule",
                    details=f"UniFi controller returned error: {update_response}",
                    actionable_steps=[
                        "Check UniFi controller logs",
                        "Verify you have permission to modify firewall rules",
                        "Verify the rule configuration is valid",
                        "Try again or contact administrator",
                        "Consider rolling back changes if needed"
                    ]
                )
            
            logger.info(f"Successfully updated firewall rule {rule_id}")
            
            return self.format_success(
                {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name", "Unnamed Rule"),
                    "changed": True,
                    "changes": changes
                },
                message=f"Firewall rule updated successfully ({len(changes)} field(s) changed)"
            )
        
        except ToolError:
            # Re-raise tool errors
            raise
        
        except Exception as e:
            logger.error(f"Failed to update firewall rule: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to update firewall rule",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify you have permission to modify firewall rules",
                    "Verify the rule configuration is valid",
                    "Check server logs for details",
                    "Consider rolling back if partial changes were made"
                ]
            )
    
    def _find_rule(
        self,
        rules: list,
        rule_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a firewall rule by ID.
        
        Args:
            rules: List of firewall rule dictionaries
            rule_id: Rule ID to search for
        
        Returns:
            Rule dictionary if found, None otherwise
        """
        rule_id_lower = rule_id.lower()
        
        for rule in rules:
            if rule.get("_id", "").lower() == rule_id_lower:
                return rule
        
        return None
