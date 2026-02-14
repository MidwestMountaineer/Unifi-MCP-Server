"""Firewall zone and policy tools for UniFi MCP server.

This module provides tools for inspecting the zone-based firewall model
introduced in UniFi Network 9.0+:
- List all firewall zones (Internal, External, Gateway, VPN, custom)
- Get detailed information about a specific firewall zone
- List firewall policies (replaces broken legacy firewall rules)
- Get detailed information about a specific firewall policy
- Get firewall policy ordering for a zone pair
- List and inspect traffic matching lists

These tools use the v1 integration API and are read-only.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient, UniFiClientError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListFirewallZonesTool(BaseTool):
    """List all firewall zones.

    This tool retrieves all firewall zones configured on the Dream Machine,
    including system-defined zones (Internal, External, Gateway, VPN) and
    any user-defined zones. Provides summary information optimized for
    AI consumption.

    Example usage:
        - "List all firewall zones"
        - "Show me the zone-based firewall topology"
        - "What firewall zones are configured?"
    """

    name = "unifi_list_firewall_zones"
    description = "List all firewall zones including system-defined and user-defined zones"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1,
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API",
            },
        },
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the list firewall zones tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of firewall zones
        """
        try:
            logger.info("Fetching firewall zones")

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
                "firewall/zones", params=params if params else None
            )

            zones = response.get("data", [])
            total_count = response.get("totalCount", len(zones))

            logger.debug(f"Retrieved {len(zones)} firewall zones")

            formatted_zones = [
                self._format_zone_summary(zone) for zone in zones
            ]

            logger.info(f"Returning {len(formatted_zones)} firewall zones")

            return self.format_list(
                items=formatted_zones,
                total=total_count,
                page=1,
                page_size=len(formatted_zones),
            )

        except Exception as e:
            logger.error(f"Failed to list firewall zones: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall zone list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_zone_summary(self, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Format zone data for summary view.

        Args:
            zone: Raw zone data from v1 API

        Returns:
            Formatted zone summary
        """
        metadata = zone.get("metadata", {})
        origin_raw = metadata.get("origin", "UNKNOWN")
        origin = (
            "system-defined"
            if origin_raw == "SYSTEM_DEFINED"
            else "user-defined"
            if origin_raw == "USER_DEFINED"
            else origin_raw.lower().replace("_", "-")
        )

        return {
            "id": zone.get("id", ""),
            "name": zone.get("name", ""),
            "networkIds": zone.get("networkIds", []),
            "origin": origin,
        }


class GetFirewallZoneTool(BaseTool):
    """Get detailed information about a specific firewall zone.

    This tool retrieves comprehensive information about a single firewall
    zone including its name, associated network IDs, and metadata.
    Use this after listing zones to get full details about a specific zone.

    Example usage:
        - "Show me details for the Internal zone"
        - "What networks are in firewall zone abc-123?"
        - "Get full information for the External zone"
    """

    name = "unifi_get_firewall_zone"
    description = "Get detailed information about a specific firewall zone"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "zone_id": {
                "type": "string",
                "description": "Firewall zone ID (UUID)",
            },
        },
        "required": ["zone_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        zone_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get firewall zone details tool.

        Args:
            unifi_client: UniFi API client
            zone_id: Firewall zone ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted firewall zone details
        """
        try:
            logger.info(f"Fetching details for firewall zone: {zone_id}")

            response = await unifi_client.get_v1(f"firewall/zones/{zone_id}")

            # v1 detail endpoints return the object directly (not wrapped in data array)
            zone = response.get("data", response) if isinstance(response, dict) else response

            # If the response has a data list (some endpoints wrap single items), extract first
            if isinstance(zone, list):
                if not zone:
                    raise ToolError(
                        code="ZONE_NOT_FOUND",
                        message=f"Firewall zone '{zone_id}' not found. Use unifi_list_firewall_zones to see available zones.",
                        details=f"No zone found with ID '{zone_id}'",
                        actionable_steps=[
                            "Verify the zone ID is correct",
                            "Use unifi_list_firewall_zones to see available zones",
                        ],
                    )
                zone = zone[0]

            formatted_zone = self._format_zone_details(zone)

            logger.info(f"Retrieved details for firewall zone: {formatted_zone.get('name', zone_id)}")

            return self.format_detail(
                item=formatted_zone,
                item_type="firewall_zone",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="ZONE_NOT_FOUND",
                    message=f"Firewall zone '{zone_id}' not found. Use unifi_list_firewall_zones to see available zones.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the zone ID is correct",
                        "Use unifi_list_firewall_zones to see available zones",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall zone details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get firewall zone details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall zone details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the zone ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_zone_details(self, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Format zone data for detailed view.

        Args:
            zone: Raw zone data from v1 API

        Returns:
            Formatted zone details
        """
        metadata = zone.get("metadata", {})
        origin_raw = metadata.get("origin", "UNKNOWN")
        origin = (
            "system-defined"
            if origin_raw == "SYSTEM_DEFINED"
            else "user-defined"
            if origin_raw == "USER_DEFINED"
            else origin_raw.lower().replace("_", "-")
        )

        return {
            "id": zone.get("id", ""),
            "name": zone.get("name", ""),
            "networkIds": zone.get("networkIds", []),
            "origin": origin,
            "metadata": metadata,
        }


class ListFirewallPoliciesTool(BaseTool):
    """List all firewall policies.

    This tool retrieves all firewall policies configured on the Dream Machine,
    replacing the broken legacy firewall rules endpoint. Policies define
    traffic rules between source and destination zones.

    Example usage:
        - "List all firewall rules"
        - "Show me the firewall policies"
        - "What firewall rules are configured?"
    """

    name = "unifi_list_firewall_rules"
    description = "List all firewall policies (zone-based rules) configured on the Dream Machine"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1,
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API",
            },
        },
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the list firewall policies tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of firewall policies
        """
        try:
            logger.info("Fetching firewall policies")

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
                "firewall/policies", params=params if params else None
            )

            policies = response.get("data", [])
            total_count = response.get("totalCount", len(policies))

            logger.debug(f"Retrieved {len(policies)} firewall policies")

            formatted_policies = [
                self._format_policy_summary(policy) for policy in policies
            ]

            logger.info(f"Returning {len(formatted_policies)} firewall policies")

            return self.format_list(
                items=formatted_policies,
                total=total_count,
                page=1,
                page_size=len(formatted_policies),
            )

        except Exception as e:
            logger.error(f"Failed to list firewall policies: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall policy list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_policy_summary(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Format policy data for summary view.

        Args:
            policy: Raw policy data from v1 API

        Returns:
            Formatted policy summary
        """
        action = policy.get("action", {})
        source = policy.get("source", {})
        destination = policy.get("destination", {})
        ip_protocol_scope = policy.get("ipProtocolScope", {})

        return {
            "id": policy.get("id", ""),
            "name": policy.get("name", ""),
            "enabled": policy.get("enabled", False),
            "actionType": action.get("type", "UNKNOWN"),
            "sourceZoneId": source.get("zoneId", ""),
            "destinationZoneId": destination.get("zoneId", ""),
            "protocolScope": ip_protocol_scope,
        }


class GetFirewallPolicyTool(BaseTool):
    """Get detailed information about a specific firewall policy.

    This tool retrieves comprehensive information about a single firewall
    policy including action configuration, traffic filters, connection state,
    schedule, logging, and metadata.

    Example usage:
        - "Show me details for firewall rule abc-123"
        - "What does this firewall policy do?"
        - "Get full information for a specific firewall rule"
    """

    name = "unifi_get_firewall_rule_details"
    description = "Get detailed information about a specific firewall policy"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "policy_id": {
                "type": "string",
                "description": "Firewall policy ID (UUID)",
            },
        },
        "required": ["policy_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        policy_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get firewall policy details tool.

        Args:
            unifi_client: UniFi API client
            policy_id: Firewall policy ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted firewall policy details
        """
        try:
            logger.info(f"Fetching details for firewall policy: {policy_id}")

            response = await unifi_client.get_v1(f"firewall/policies/{policy_id}")

            # v1 detail endpoints return the object directly (not wrapped in data array)
            policy = response.get("data", response) if isinstance(response, dict) else response

            # If the response has a data list (some endpoints wrap single items), extract first
            if isinstance(policy, list):
                if not policy:
                    raise ToolError(
                        code="POLICY_NOT_FOUND",
                        message=f"Firewall policy '{policy_id}' not found. Use unifi_list_firewall_rules to see available policies.",
                        details=f"No policy found with ID '{policy_id}'",
                        actionable_steps=[
                            "Verify the policy ID is correct",
                            "Use unifi_list_firewall_rules to see available policies",
                        ],
                    )
                policy = policy[0]

            formatted_policy = self._format_policy_details(policy)

            logger.info(f"Retrieved details for firewall policy: {formatted_policy.get('name', policy_id)}")

            return self.format_detail(
                item=formatted_policy,
                item_type="firewall_policy",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="POLICY_NOT_FOUND",
                    message=f"Firewall policy '{policy_id}' not found. Use unifi_list_firewall_rules to see available policies.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the policy ID is correct",
                        "Use unifi_list_firewall_rules to see available policies",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall policy details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get firewall policy details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall policy details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the policy ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_policy_details(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Format policy data for detailed view.

        Args:
            policy: Raw policy data from v1 API

        Returns:
            Formatted policy details
        """
        action = policy.get("action", {})
        source = policy.get("source", {})
        destination = policy.get("destination", {})
        metadata = policy.get("metadata", {})

        return {
            "id": policy.get("id", ""),
            "name": policy.get("name", ""),
            "description": policy.get("description", ""),
            "enabled": policy.get("enabled", False),
            "index": policy.get("index", 0),
            "action": action,
            "source": source,
            "destination": destination,
            "ipProtocolScope": policy.get("ipProtocolScope", {}),
            "connectionStateFilter": policy.get("connectionStateFilter", []),
            "ipsecFilter": policy.get("ipsecFilter"),
            "loggingEnabled": policy.get("loggingEnabled", False),
            "schedule": policy.get("schedule", {}),
            "metadata": metadata,
        }


class GetFirewallPolicyOrderingTool(BaseTool):
    """Get firewall policy ordering for a zone pair.

    This tool retrieves the evaluation order of firewall policies for a
    given source and destination zone pair. Policies are split into
    before-system-defined and after-system-defined groups.

    Example usage:
        - "What order are firewall rules evaluated for Internal to External?"
        - "Show me the policy ordering between two zones"
        - "Get firewall policy evaluation order"
    """

    name = "unifi_get_firewall_policy_ordering"
    description = "Get firewall policy evaluation ordering for a source/destination zone pair"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "source_zone_id": {
                "type": "string",
                "description": "Source firewall zone ID (UUID)",
            },
            "destination_zone_id": {
                "type": "string",
                "description": "Destination firewall zone ID (UUID)",
            },
        },
        "required": ["source_zone_id", "destination_zone_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        source_zone_id: str,
        destination_zone_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get firewall policy ordering tool.

        Args:
            unifi_client: UniFi API client
            source_zone_id: Source firewall zone ID (UUID)
            destination_zone_id: Destination firewall zone ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted policy ordering for the zone pair
        """
        try:
            logger.info(
                f"Fetching policy ordering for zones: {source_zone_id} -> {destination_zone_id}"
            )

            response = await unifi_client.get_v1(
                "firewall/policies/ordering",
                params={
                    "sourceFirewallZoneId": source_zone_id,
                    "destinationFirewallZoneId": destination_zone_id,
                },
            )

            formatted_ordering = self._format_ordering(
                response, source_zone_id, destination_zone_id
            )

            logger.info("Retrieved firewall policy ordering")

            return self.format_detail(
                item=formatted_ordering,
                item_type="firewall_policy_ordering",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="ORDERING_NOT_FOUND",
                    message=(
                        f"Firewall policy ordering not found for zone pair "
                        f"'{source_zone_id}' -> '{destination_zone_id}'. "
                        f"Use unifi_list_firewall_zones to verify zone IDs."
                    ),
                    details=str(e),
                    actionable_steps=[
                        "Verify both zone IDs are correct",
                        "Use unifi_list_firewall_zones to see available zones",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall policy ordering",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get firewall policy ordering: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve firewall policy ordering",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the zone IDs are correct",
                    "Check server logs for details",
                ],
            )

    def _format_ordering(
        self,
        response: Dict[str, Any],
        source_zone_id: str,
        destination_zone_id: str,
    ) -> Dict[str, Any]:
        """Format policy ordering data.

        Args:
            response: Raw ordering response from v1 API
            source_zone_id: Source zone ID for context
            destination_zone_id: Destination zone ID for context

        Returns:
            Formatted ordering details
        """
        ordered_ids = response.get("orderedFirewallPolicyIds", {})

        return {
            "sourceZoneId": source_zone_id,
            "destinationZoneId": destination_zone_id,
            "beforeSystemDefined": ordered_ids.get("beforeSystemDefined", []),
            "afterSystemDefined": ordered_ids.get("afterSystemDefined", []),
        }


class ListTrafficMatchingListsTool(BaseTool):
    """List all traffic matching lists.

    This tool retrieves all traffic matching lists configured on the
    Dream Machine. Traffic matching lists are reusable definitions of
    traffic patterns (ports, IPs, regions) referenced by firewall policies.

    Example usage:
        - "List all traffic matching lists"
        - "Show me the traffic definitions used by firewall policies"
        - "What traffic matching lists are configured?"
    """

    name = "unifi_list_traffic_matching_lists"
    description = "List all traffic matching lists (reusable traffic pattern definitions)"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Number of items to skip (v1 pagination)",
                "minimum": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (v1 pagination)",
                "minimum": 1,
            },
            "filter": {
                "type": "string",
                "description": "Filter expression for v1 API",
            },
        },
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_expr: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the list traffic matching lists tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of traffic matching lists
        """
        try:
            logger.info("Fetching traffic matching lists")

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
                "traffic-matching-lists", params=params if params else None
            )

            lists = response.get("data", [])
            total_count = response.get("totalCount", len(lists))

            logger.debug(f"Retrieved {len(lists)} traffic matching lists")

            formatted_lists = [
                self._format_list_summary(item) for item in lists
            ]

            logger.info(f"Returning {len(formatted_lists)} traffic matching lists")

            return self.format_list(
                items=formatted_lists,
                total=total_count,
                page=1,
                page_size=len(formatted_lists),
            )

        except Exception as e:
            logger.error(f"Failed to list traffic matching lists: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve traffic matching list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_list_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format traffic matching list data for summary view.

        Args:
            item: Raw traffic matching list data from v1 API

        Returns:
            Formatted list summary
        """
        return {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "type": item.get("type", ""),
        }


class GetTrafficMatchingListTool(BaseTool):
    """Get detailed information about a specific traffic matching list.

    This tool retrieves comprehensive information about a single traffic
    matching list including all traffic pattern definitions and metadata.

    Example usage:
        - "Show me details for traffic matching list abc-123"
        - "What traffic patterns are in this list?"
        - "Get full information for a specific traffic matching list"
    """

    name = "unifi_get_traffic_matching_list"
    description = "Get detailed information about a specific traffic matching list"
    category = "firewall"

    input_schema = {
        "type": "object",
        "properties": {
            "list_id": {
                "type": "string",
                "description": "Traffic matching list ID (UUID)",
            },
        },
        "required": ["list_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        list_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get traffic matching list details tool.

        Args:
            unifi_client: UniFi API client
            list_id: Traffic matching list ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted traffic matching list details
        """
        try:
            logger.info(f"Fetching details for traffic matching list: {list_id}")

            response = await unifi_client.get_v1(f"traffic-matching-lists/{list_id}")

            # v1 detail endpoints return the object directly (not wrapped in data array)
            item = response.get("data", response) if isinstance(response, dict) else response

            # If the response has a data list (some endpoints wrap single items), extract first
            if isinstance(item, list):
                if not item:
                    raise ToolError(
                        code="TRAFFIC_LIST_NOT_FOUND",
                        message=f"Traffic matching list '{list_id}' not found. Use unifi_list_traffic_matching_lists to see available lists.",
                        details=f"No traffic matching list found with ID '{list_id}'",
                        actionable_steps=[
                            "Verify the list ID is correct",
                            "Use unifi_list_traffic_matching_lists to see available lists",
                        ],
                    )
                item = item[0]

            formatted_item = self._format_list_details(item)

            logger.info(f"Retrieved details for traffic matching list: {formatted_item.get('name', list_id)}")

            return self.format_detail(
                item=formatted_item,
                item_type="traffic_matching_list",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="TRAFFIC_LIST_NOT_FOUND",
                    message=f"Traffic matching list '{list_id}' not found. Use unifi_list_traffic_matching_lists to see available lists.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the list ID is correct",
                        "Use unifi_list_traffic_matching_lists to see available lists",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve traffic matching list details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get traffic matching list details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve traffic matching list details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the list ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_list_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format traffic matching list data for detailed view.

        Args:
            item: Raw traffic matching list data from v1 API

        Returns:
            Formatted list details
        """
        return {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "description": item.get("description", ""),
            "metadata": item.get("metadata", {}),
        }
