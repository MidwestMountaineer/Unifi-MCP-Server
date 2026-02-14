"""Supporting resource tools for UniFi MCP server.

This module provides tools for inspecting supporting network resources
via the v1 integration API:
- List local sites (site-independent endpoint)
- Get application info (site-independent endpoint)
- List WAN interfaces
- List site-to-site VPN tunnels
- List VPN server configurations
- Get network references (resources referencing a specific network)

These tools use the v1 integration API and are read-only.
"""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool, ToolError
from ..unifi_client import UniFiClient, UniFiClientError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ListSitesTool(BaseTool):
    """List all local sites.

    This tool retrieves all sites configured on the Dream Machine.
    Uses the site-independent /v1/sites endpoint (no siteId required).

    Example usage:
        - "List all UniFi sites"
        - "Show me the configured sites"
        - "What sites are available?"
    """

    name = "unifi_list_sites"
    description = "List all local sites including each site's UUID and name"
    category = "resources"

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
        """Execute the list sites tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of sites
        """
        try:
            logger.info("Fetching sites")

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
                "/v1/sites", params=params if params else None
            )

            sites = response.get("data", [])
            total_count = response.get("totalCount", len(sites))

            logger.debug(f"Retrieved {len(sites)} sites")

            formatted_sites = [
                self._format_site_summary(site) for site in sites
            ]

            logger.info(f"Returning {len(formatted_sites)} sites")

            return self.format_list(
                items=formatted_sites,
                total=total_count,
                page=1,
                page_size=len(formatted_sites),
            )

        except Exception as e:
            logger.error(f"Failed to list sites: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve site list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_site_summary(self, site: Dict[str, Any]) -> Dict[str, Any]:
        """Format site data for summary view.

        Args:
            site: Raw site data from v1 API

        Returns:
            Formatted site summary
        """
        return {
            "id": site.get("id", ""),
            "name": site.get("name", ""),
        }



class GetAppInfoTool(BaseTool):
    """Get application version information.

    This tool retrieves the UniFi Network application version info.
    Uses the site-independent /v1/info endpoint (no siteId required).

    Example usage:
        - "What version of UniFi Network is running?"
        - "Get the application info"
        - "Show me the UniFi app version"
    """

    name = "unifi_get_app_info"
    description = "Get UniFi Network application version information"
    category = "resources"

    input_schema = {
        "type": "object",
        "properties": {},
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get app info tool.

        Args:
            unifi_client: UniFi API client
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted application info
        """
        try:
            logger.info("Fetching application info")

            response = await unifi_client.get_v1("/v1/info")

            formatted_info = self._format_app_info(response)

            logger.info("Retrieved application info")

            return self.format_detail(
                item=formatted_info,
                item_type="app_info",
            )

        except Exception as e:
            logger.error(f"Failed to get app info: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve application info",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_app_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format application info data.

        Args:
            response: Raw info response from v1 API

        Returns:
            Formatted app info
        """
        return {
            "version": response.get("version", ""),
            "name": response.get("name", ""),
        }


class ListWANInterfacesTool(BaseTool):
    """List all WAN interfaces.

    This tool retrieves all WAN interfaces configured on the Dream Machine.

    Example usage:
        - "List all WAN interfaces"
        - "Show me the WAN connections"
        - "What WAN interfaces are configured?"
    """

    name = "unifi_list_wan_interfaces"
    description = "List all WAN interfaces configured on the Dream Machine"
    category = "resources"

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
        """Execute the list WAN interfaces tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of WAN interfaces
        """
        try:
            logger.info("Fetching WAN interfaces")

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
                "wans", params=params if params else None
            )

            wans = response.get("data", [])
            total_count = response.get("totalCount", len(wans))

            logger.debug(f"Retrieved {len(wans)} WAN interfaces")

            formatted_wans = [
                self._format_wan_summary(wan) for wan in wans
            ]

            logger.info(f"Returning {len(formatted_wans)} WAN interfaces")

            return self.format_list(
                items=formatted_wans,
                total=total_count,
                page=1,
                page_size=len(formatted_wans),
            )

        except Exception as e:
            logger.error(f"Failed to list WAN interfaces: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve WAN interface list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_wan_summary(self, wan: Dict[str, Any]) -> Dict[str, Any]:
        """Format WAN interface data for summary view.

        Args:
            wan: Raw WAN interface data from v1 API

        Returns:
            Formatted WAN summary
        """
        return {
            "id": wan.get("id", ""),
            "name": wan.get("name", ""),
        }


class ListVPNTunnelsTool(BaseTool):
    """List all site-to-site VPN tunnels.

    This tool retrieves all site-to-site VPN tunnels configured on
    the Dream Machine.

    Example usage:
        - "List all VPN tunnels"
        - "Show me the site-to-site VPN connections"
        - "What VPN tunnels are configured?"
    """

    name = "unifi_list_vpn_tunnels"
    description = "List all site-to-site VPN tunnels"
    category = "resources"

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
        """Execute the list VPN tunnels tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of VPN tunnels
        """
        try:
            logger.info("Fetching VPN tunnels")

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
                "vpn/site-to-site-tunnels", params=params if params else None
            )

            tunnels = response.get("data", [])
            total_count = response.get("totalCount", len(tunnels))

            logger.debug(f"Retrieved {len(tunnels)} VPN tunnels")

            formatted_tunnels = [
                self._format_tunnel_summary(tunnel) for tunnel in tunnels
            ]

            logger.info(f"Returning {len(formatted_tunnels)} VPN tunnels")

            return self.format_list(
                items=formatted_tunnels,
                total=total_count,
                page=1,
                page_size=len(formatted_tunnels),
            )

        except Exception as e:
            logger.error(f"Failed to list VPN tunnels: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve VPN tunnel list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_tunnel_summary(self, tunnel: Dict[str, Any]) -> Dict[str, Any]:
        """Format VPN tunnel data for summary view.

        Args:
            tunnel: Raw VPN tunnel data from v1 API

        Returns:
            Formatted tunnel summary
        """
        return {
            "id": tunnel.get("id", ""),
            "name": tunnel.get("name", ""),
        }


class ListVPNServersTool(BaseTool):
    """List all VPN server configurations.

    This tool retrieves all VPN server configurations on the Dream Machine.

    Example usage:
        - "List all VPN servers"
        - "Show me the VPN server configurations"
        - "What VPN servers are configured?"
    """

    name = "unifi_list_vpn_servers"
    description = "List all VPN server configurations"
    category = "resources"

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
        """Execute the list VPN servers tool.

        Args:
            unifi_client: UniFi API client
            offset: Number of items to skip (v1 pagination)
            limit: Maximum number of items to return (v1 pagination)
            filter_expr: Filter expression for v1 API
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of VPN servers
        """
        try:
            logger.info("Fetching VPN servers")

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
                "vpn/servers", params=params if params else None
            )

            servers = response.get("data", [])
            total_count = response.get("totalCount", len(servers))

            logger.debug(f"Retrieved {len(servers)} VPN servers")

            formatted_servers = [
                self._format_server_summary(server) for server in servers
            ]

            logger.info(f"Returning {len(formatted_servers)} VPN servers")

            return self.format_list(
                items=formatted_servers,
                total=total_count,
                page=1,
                page_size=len(formatted_servers),
            )

        except Exception as e:
            logger.error(f"Failed to list VPN servers: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve VPN server list",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

    def _format_server_summary(self, server: Dict[str, Any]) -> Dict[str, Any]:
        """Format VPN server data for summary view.

        Args:
            server: Raw VPN server data from v1 API

        Returns:
            Formatted server summary
        """
        return {
            "id": server.get("id", ""),
            "name": server.get("name", ""),
        }


class GetNetworkReferencesTool(BaseTool):
    """Get resources that reference a specific network.

    This tool retrieves a list of resources (firewall zones, policies, etc.)
    that reference a given network by its ID.

    Example usage:
        - "What references this network?"
        - "Show me resources using network abc-123"
        - "Get network references for a specific network"
    """

    name = "unifi_get_network_references"
    description = "Get a list of resources that reference a specific network"
    category = "resources"

    input_schema = {
        "type": "object",
        "properties": {
            "network_id": {
                "type": "string",
                "description": "Network ID (UUID)",
            },
        },
        "required": ["network_id"],
    }

    async def execute(
        self,
        unifi_client: UniFiClient,
        network_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the get network references tool.

        Args:
            unifi_client: UniFi API client
            network_id: Network ID (UUID)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted list of network references
        """
        try:
            logger.info(f"Fetching references for network: {network_id}")

            response = await unifi_client.get_v1(f"networks/{network_id}/references")

            references = response.get("data", [])
            total_count = response.get("totalCount", len(references))

            logger.debug(f"Retrieved {len(references)} references for network {network_id}")

            formatted_refs = [
                self._format_reference(ref) for ref in references
            ]

            logger.info(f"Returning {len(formatted_refs)} network references")

            return self.format_list(
                items=formatted_refs,
                total=total_count,
                page=1,
                page_size=len(formatted_refs),
            )

        except UniFiClientError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ToolError(
                    code="NETWORK_NOT_FOUND",
                    message=f"Network '{network_id}' not found. Use unifi_list_networks to see available networks.",
                    details=str(e),
                    actionable_steps=[
                        "Verify the network ID is correct",
                        "Use unifi_list_networks to see available networks",
                    ],
                )
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve network references",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify API key has read access",
                    "Check server logs for details",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get network references: {e}", exc_info=True)
            raise ToolError(
                code="API_ERROR",
                message="Failed to retrieve network references",
                details=str(e),
                actionable_steps=[
                    "Check UniFi controller is accessible",
                    "Verify the network ID is correct",
                    "Check server logs for details",
                ],
            )

    def _format_reference(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Format network reference data.

        Args:
            ref: Raw reference data from v1 API

        Returns:
            Formatted reference
        """
        return {
            "id": ref.get("id", ""),
            "type": ref.get("type", ""),
            "name": ref.get("name", ""),
        }
