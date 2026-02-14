"""ACL rule tools for UniFi MCP server.

This module provides tools for inspecting switch-level ACL rules
on UniFi switches via the v1 integration API:
- List all ACL rules (IPv4 and MAC)
- Get detailed information about a specific ACL rule
- Get ACL rule evaluation ordering

These tools use the v1 integration API and are read-only.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient, UniFiClientError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListACLRulesTool(BaseTool):
    """List all ACL rules.

    This tool retrieves all switch-level ACL rules configured on UniFi
    switches, including both IPv4 and MAC-based rules. Provides summary
    information optimized for AI consumption.

    Example usage:
        - "List all ACL rules"
        - "Show me the switch access control rules"
        - "What ACL rules are configured?"
    """

    name = "unifi_list_acl_rules"
    description = "List all switch-level ACL rules including IPv4 and MAC rules"
    category = "acl"

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
        """Execute the list ACL rules tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of ACL rules
        """
        try:
            logger.info("Fetching ACL rules")

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
                "acl-rules", params=params if params else None
            )

            rules = response.get("data", [])
            total_count = response.get("totalCount", len(rules))

            logger.debug(f"Retrieved {len(rules)} ACL rules")

            formatted_rules = [
                self._format_rule_summary(rule) for rule in rules
            ]

            logger.info(f"Returning {len(formatted_rules)} ACL rules")

            return self.format_list(
                items=formatted_rules,
                total=total_count,
                page=1,
                page_size=len(formatted_rules),
            )

        except Exception as e:
            logger.error(f"Failed to list ACL rules: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve ACL rule list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_rule_summary(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format ACL rule data for summary view.

        Args:
            rule: Raw ACL rule data from v1 API

        Returns:
            Formatted rule summary
        """
        return {
            "id": rule.get("id", ""),
            "name": rule.get("name", ""),
            "type": rule.get("type", "UNKNOWN"),
            "enabled": rule.get("enabled", False),
            "action": rule.get("action", "UNKNOWN"),
            "index": rule.get("index", 0),
        }


class GetACLRuleTool(BaseTool):
    """Get detailed information about a specific ACL rule.

    This tool retrieves comprehensive information about a single ACL rule
    including enforcing device filter, source/destination filters, protocol
    filter, and metadata.

    Example usage:
        - "Show me details for ACL rule abc-123"
        - "What does this ACL rule do?"
        - "Get full information for a specific ACL rule"
    """

    name = "unifi_get_acl_rule"
    description = "Get detailed information about a specific ACL rule"
    category = "acl"

    input_schema = {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "ACL rule ID (UUID)",
            },
        },
        "required": ["rule_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        rule_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get ACL rule details tool.

        Args:
            unifi_client: UniFi API client
            rule_id: ACL rule ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted ACL rule details
        """
        try:
            logger.info(f"Fetching details for ACL rule: {rule_id}")

            response = await unifi_client.get_v1(f"acl-rules/{rule_id}")

            # v1 detail endpoints return the object directly (not wrapped in data array)
            rule = response.get("data", response) if isinstance(response, dict) else response

            # If the response has a data list (some endpoints wrap single items), extract first
            if isinstance(rule, list):
                if not rule:
                    raise ToolError(
                        code="ACL_RULE_NOT_FOUND",
                        message=f"ACL rule '{rule_id}' not found. Use unifi_list_acl_rules to see available rules.",
                        details=f"No ACL rule found with ID '{rule_id}'",
                        actionable_steps=[
                            "Verify the rule ID is correct",
                            "Use unifi_list_acl_rules to see available rules",
                        ],
                    )
                rule = rule[0]

            formatted_rule = self._format_rule_details(rule)

            logger.info(f"Retrieved details for ACL rule: {formatted_rule.get('name', rule_id)}")

            return self.format_detail(
                item=formatted_rule,
                item_type="acl_rule",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="ACL_RULE_NOT_FOUND",
                    message=f"ACL rule '{rule_id}' not found. Use unifi_list_acl_rules to see available rules.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the rule ID is correct",
                        "Use unifi_list_acl_rules to see available rules",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve ACL rule details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get ACL rule details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve ACL rule details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the rule ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_rule_details(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format ACL rule data for detailed view.

        Args:
            rule: Raw ACL rule data from v1 API

        Returns:
            Formatted rule details
        """
        return {
            "id": rule.get("id", ""),
            "name": rule.get("name", ""),
            "type": rule.get("type", "UNKNOWN"),
            "enabled": rule.get("enabled", False),
            "description": rule.get("description", ""),
            "action": rule.get("action", "UNKNOWN"),
            "index": rule.get("index", 0),
            "enforcingDeviceFilter": rule.get("enforcingDeviceFilter", {}),
            "sourceFilter": rule.get("sourceFilter"),
            "destinationFilter": rule.get("destinationFilter"),
            "protocolFilter": rule.get("protocolFilter", []),
            "metadata": rule.get("metadata", {}),
        }


class GetACLRuleOrderingTool(BaseTool):
    """Get ACL rule evaluation ordering.

    This tool retrieves the evaluation order of ACL rules. Rules are
    evaluated in order by their index, and this endpoint returns the
    ordered list of rule IDs.

    Example usage:
        - "What order are ACL rules evaluated?"
        - "Show me the ACL rule ordering"
        - "Get ACL rule evaluation order"
    """

    name = "unifi_get_acl_rule_ordering"
    description = "Get ACL rule evaluation ordering"
    category = "acl"

    input_schema = {
        "type": "object",
        "properties": {},
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get ACL rule ordering tool.

        Args:
            unifi_client: UniFi API client
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted ACL rule ordering
        """
        try:
            logger.info("Fetching ACL rule ordering")

            response = await unifi_client.get_v1("acl-rules/ordering")

            formatted_ordering = self._format_ordering(response)

            logger.info("Retrieved ACL rule ordering")

            return self.format_detail(
                item=formatted_ordering,
                item_type="acl_rule_ordering",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve ACL rule ordering",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get ACL rule ordering: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve ACL rule ordering",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Check server logs for details",
                ],
            )

    def _format_ordering(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format ACL rule ordering data.

        Args:
            response: Raw ordering response from v1 API

        Returns:
            Formatted ordering details
        """
        return {
            "orderedAclRuleIds": response.get("orderedAclRuleIds", []),
        }
