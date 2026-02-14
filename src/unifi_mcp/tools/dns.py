"""DNS policy tools for UniFi MCP server.

This module provides tools for inspecting DNS filtering policies
on the Dream Machine via the v1 integration API:
- List all DNS policies
- Get detailed information about a specific DNS policy

These tools use the v1 integration API and are read-only.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient, UniFiClientError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListDNSPoliciesTool(BaseTool):
    """List all DNS policies.

    This tool retrieves all DNS filtering policies configured on the
    Dream Machine. Provides summary information optimized for AI
    consumption.

    Example usage:
        - "List all DNS policies"
        - "Show me the DNS filtering rules"
        - "What DNS policies are configured?"
    """

    name = "unifi_list_dns_policies"
    description = "List all DNS filtering policies configured on the Dream Machine"
    category = "dns"

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
        """Execute the list DNS policies tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of DNS policies
        """
        try:
            logger.info("Fetching DNS policies")

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
                "dns/policies", params=params if params else None
            )

            policies = response.get("data", [])
            total_count = response.get("totalCount", len(policies))

            logger.debug(f"Retrieved {len(policies)} DNS policies")

            formatted_policies = [
                self._format_policy_summary(policy) for policy in policies
            ]

            logger.info(f"Returning {len(formatted_policies)} DNS policies")

            return self.format_list(
                items=formatted_policies,
                total=total_count,
                page=1,
                page_size=len(formatted_policies),
            )

        except Exception as e:
            logger.error(f"Failed to list DNS policies: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve DNS policy list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_policy_summary(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Format DNS policy data for summary view.

        Args:
            policy: Raw DNS policy data from v1 API

        Returns:
            Formatted policy summary
        """
        return {
            "id": policy.get("id", ""),
            "name": policy.get("name", ""),
            "enabled": policy.get("enabled", False),
        }


class GetDNSPolicyTool(BaseTool):
    """Get detailed information about a specific DNS policy.

    This tool retrieves comprehensive information about a single DNS
    policy including all configuration details and metadata.

    Example usage:
        - "Show me details for DNS policy abc-123"
        - "What does this DNS policy do?"
        - "Get full information for a specific DNS policy"
    """

    name = "unifi_get_dns_policy"
    description = "Get detailed information about a specific DNS policy"
    category = "dns"

    input_schema = {
        "type": "object",
        "properties": {
            "policy_id": {
                "type": "string",
                "description": "DNS policy ID (UUID)",
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
        """Execute the get DNS policy details tool.

        Args:
            unifi_client: UniFi API client
            policy_id: DNS policy ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted DNS policy details
        """
        try:
            logger.info(f"Fetching details for DNS policy: {policy_id}")

            response = await unifi_client.get_v1(f"dns/policies/{policy_id}")

            # v1 detail endpoints return the object directly (not wrapped in data array)
            policy = response.get("data", response) if isinstance(response, dict) else response

            # If the response has a data list (some endpoints wrap single items), extract first
            if isinstance(policy, list):
                if not policy:
                    raise ToolError(
                        code="DNS_POLICY_NOT_FOUND",
                        message=f"DNS policy '{policy_id}' not found. Use unifi_list_dns_policies to see available policies.",
                        details=f"No DNS policy found with ID '{policy_id}'",
                        actionable_steps=[
                            "Verify the policy ID is correct",
                            "Use unifi_list_dns_policies to see available policies",
                        ],
                    )
                policy = policy[0]

            formatted_policy = self._format_policy_details(policy)

            logger.info(f"Retrieved details for DNS policy: {formatted_policy.get('name', policy_id)}")

            return self.format_detail(
                item=formatted_policy,
                item_type="dns_policy",
            )

        except ToolError:
            raise

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="DNS_POLICY_NOT_FOUND",
                    message=f"DNS policy '{policy_id}' not found. Use unifi_list_dns_policies to see available policies.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the policy ID is correct",
                        "Use unifi_list_dns_policies to see available policies",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve DNS policy details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get DNS policy details: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve DNS policy details",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the policy ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_policy_details(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Format DNS policy data for detailed view.

        Args:
            policy: Raw DNS policy data from v1 API

        Returns:
            Formatted policy details
        """
        return {
            "id": policy.get("id", ""),
            "name": policy.get("name", ""),
            "enabled": policy.get("enabled", False),
            "description": policy.get("description", ""),
            "metadata": policy.get("metadata", {}),
        }
