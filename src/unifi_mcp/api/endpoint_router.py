"""Endpoint routing for UniFi MCP Server.

This module provides functionality to route API requests to the correct endpoints
based on the detected controller type (UniFi OS vs Traditional).

UniFi OS devices use v2 API endpoints with /proxy/network prefix, while
traditional controllers use v1 API endpoints without the prefix.

Key Features:
- Endpoint mapping for all security features
- Automatic endpoint selection based on controller type
- Fallback mechanism for v2 endpoint failures
- Logging of endpoint routing decisions
- Structured error handling for endpoint failures
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .controller_detector import ControllerType


@dataclass
class EndpointError(Exception):
    """Structured error for endpoint failures.
    
    This exception is raised when API endpoint requests fail, providing
    detailed context about the failure including primary and fallback
    endpoint information.
    
    Attributes:
        feature: The security feature being requested
        primary_endpoint: The primary endpoint that was tried
        primary_error: Error message from primary endpoint failure
        fallback_endpoint: The fallback endpoint that was tried (if any)
        fallback_error: Error message from fallback endpoint failure (if any)
        message: Human-readable error message
    """
    feature: str
    primary_endpoint: str
    primary_error: str
    fallback_endpoint: Optional[str] = None
    fallback_error: Optional[str] = None
    message: str = ""
    
    def __str__(self) -> str:
        """String representation of the error."""
        return self.message or f"Endpoint error for feature '{self.feature}'"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for tool responses.
        
        Returns:
            Dictionary with error details
        """
        result = {
            "code": "ENDPOINT_ERROR",
            "message": self.message,
            "feature": self.feature,
            "primary_endpoint": self.primary_endpoint,
            "primary_error": self.primary_error,
        }
        
        if self.fallback_endpoint:
            result["fallback_endpoint"] = self.fallback_endpoint
            result["fallback_error"] = self.fallback_error
            result["both_endpoints_failed"] = True
        else:
            result["both_endpoints_failed"] = False
        
        return result
    
    def get_actionable_steps(self) -> List[str]:
        """Get actionable steps to resolve the error.
        
        Returns:
            List of steps the user can take
        """
        steps = [
            "Check UniFi controller is accessible",
            "Verify network connectivity to the controller",
        ]
        
        if self.fallback_endpoint:
            steps.extend([
                "Both v2 and v1 API endpoints failed - controller may be unreachable",
                "Check if the feature is supported on your controller version",
                "Review server logs for detailed error information",
            ])
        else:
            steps.extend([
                "Check if the feature is configured on the controller",
                "Verify your user account has permission to access this feature",
            ])
        
        return steps

if TYPE_CHECKING:
    from unifi_mcp.unifi_client import UniFiClient


class EndpointRouter:
    """Routes API requests to correct endpoints based on controller type.
    
    This class maintains a mapping of feature names to their corresponding
    API endpoints for both UniFi OS (v2) and traditional (v1) controllers.
    It provides methods to get the appropriate endpoint and to make requests
    with automatic fallback to legacy endpoints.
    
    Example:
        >>> router = EndpointRouter()
        >>> endpoint = router.get_endpoint("firewall_rules", ControllerType.UNIFI_OS)
        >>> print(endpoint)
        '/proxy/network/v2/api/site/{site}/trafficroutes'
    
    Attributes:
        ENDPOINT_MAP: Mapping of features to endpoints by controller type
    """
    
    # Endpoint mapping for each security feature
    # Format: feature_name -> {controller_type -> endpoint}
    # 
    # IMPORTANT: As of UniFi Network API 10.0.160, the official v2 API does NOT yet
    # expose security settings (firewall rules, IPS, traffic routes, port forwards).
    # The official documentation states "Settings (Coming Soon)" for these features.
    # 
    # Available v2 API endpoints:
    # - Sites, Devices, Clients, Networks, Wifi Broadcasts
    # 
    # NOT available in v2 API (use legacy v1 REST API):
    # - Firewall rules, IPS/Threat management, Traffic routes, Port forwards
    # 
    # Therefore, ALL security features use the legacy v1 REST API endpoints for both
    # controller types until Ubiquiti releases the v2 security settings API.
    # 
    # The /proxy/network prefix is added automatically by the UniFi client for UniFi OS.
    ENDPOINT_MAP: Dict[str, Dict[ControllerType, str]] = {
        "firewall_rules": {
            # v2 API does not yet support firewall rules - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/firewallrule",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/firewallrule",
        },
        "firewall_policies": {
            # v2 API does not yet support firewall policies - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/firewallrule",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/firewallrule",
        },
        "ips_status": {
            # v2 API does not yet support IPS/threat management - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/setting/ips",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/setting/ips",
        },
        "ips_settings": {
            # v2 API does not yet support IPS settings - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/setting/ips",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/setting/ips",
        },
        "traffic_routes": {
            # v2 API does not yet support traffic routes - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/routing",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/routing",
        },
        "port_forwards": {
            # v2 API does not yet support port forwards - use legacy REST API
            ControllerType.UNIFI_OS: "/api/s/{site}/rest/portforward",
            ControllerType.TRADITIONAL: "/api/s/{site}/rest/portforward",
        },
    }

    # Fallback mapping: v2 endpoint -> v1 fallback endpoint
    # Currently empty since all security features use v1 REST API directly.
    # This will be populated when Ubiquiti releases v2 security settings API.
    FALLBACK_MAP: Dict[str, str] = {
        # No fallbacks needed - all security features use v1 REST API
    }
    
    def __init__(self):
        """Initialize the endpoint router."""
        self._logger = logging.getLogger(__name__)
    
    def get_endpoint(self, feature: str, controller_type: ControllerType) -> str:
        """Get the appropriate endpoint for a feature and controller type.
        
        Args:
            feature: Feature name (e.g., "firewall_rules", "ips_status")
            controller_type: The detected controller type
        
        Returns:
            API endpoint string with {site} placeholder
        
        Raises:
            ValueError: If feature is not recognized
            ValueError: If controller type has no endpoint mapping
        """
        if feature not in self.ENDPOINT_MAP:
            raise ValueError(f"Unknown feature: {feature}. Valid features: {list(self.ENDPOINT_MAP.keys())}")
        
        feature_endpoints = self.ENDPOINT_MAP[feature]
        
        # Handle UNKNOWN controller type by defaulting to traditional
        effective_type = controller_type
        if controller_type == ControllerType.UNKNOWN:
            self._logger.warning(
                f"Controller type is UNKNOWN, defaulting to TRADITIONAL for feature '{feature}'"
            )
            effective_type = ControllerType.TRADITIONAL
        
        if effective_type not in feature_endpoints:
            raise ValueError(
                f"No endpoint mapping for controller type '{effective_type.value}' "
                f"and feature '{feature}'"
            )
        
        endpoint = feature_endpoints[effective_type]
        
        self._logger.debug(
            f"Selected endpoint for feature '{feature}'",
            extra={
                "feature": feature,
                "controller_type": effective_type.value,
                "endpoint": endpoint,
            }
        )
        
        return endpoint
    
    def get_fallback_endpoint(self, v2_endpoint: str) -> Optional[str]:
        """Get the fallback v1 endpoint for a v2 endpoint.
        
        Args:
            v2_endpoint: The v2 endpoint that failed
        
        Returns:
            Fallback v1 endpoint, or None if no fallback exists
        """
        return self.FALLBACK_MAP.get(v2_endpoint)
    
    def get_all_endpoints_for_feature(self, feature: str) -> Dict[ControllerType, str]:
        """Get all endpoint mappings for a feature.
        
        Args:
            feature: Feature name
        
        Returns:
            Dictionary mapping controller types to endpoints
        
        Raises:
            ValueError: If feature is not recognized
        """
        if feature not in self.ENDPOINT_MAP:
            raise ValueError(f"Unknown feature: {feature}")
        
        return self.ENDPOINT_MAP[feature].copy()
    
    @property
    def supported_features(self) -> list:
        """Get list of supported feature names."""
        return list(self.ENDPOINT_MAP.keys())
    
    async def request_with_fallback(
        self,
        client: "UniFiClient",
        feature: str,
        controller_type: ControllerType,
        site: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make request with automatic fallback to legacy endpoint.
        
        This method tries the primary endpoint for the controller type first.
        If it fails on UniFi OS, it falls back to the legacy v1 endpoint.
        
        Args:
            client: UniFi client instance for making requests
            feature: Feature name (e.g., "firewall_rules")
            controller_type: The detected controller type
            site: Optional site name (uses client's default if not provided)
        
        Returns:
            Dictionary containing:
            - data: Response data from the API
            - endpoint_used: The endpoint that succeeded
            - api_version: "v2" or "v1"
            - fallback_used: Whether fallback was used
        
        Raises:
            EndpointError: If both primary and fallback endpoints fail
        """
        site = site or client.config.site
        
        # Get primary endpoint
        primary_endpoint = self.get_endpoint(feature, controller_type)
        primary_endpoint = primary_endpoint.replace("{site}", site)
        
        # Determine API version from endpoint
        api_version = "v2" if "/v2/" in primary_endpoint or "/proxy/network" in primary_endpoint else "v1"
        
        # Log endpoint being used at debug level (Requirement 8.1)
        self._logger.debug(
            f"Making API request for feature '{feature}' using {api_version} endpoint",
            extra={
                "feature": feature,
                "endpoint": primary_endpoint,
                "controller_type": controller_type.value,
                "api_version": api_version,
            }
        )
        
        try:
            # Try primary endpoint
            response = await client.get(primary_endpoint)
            
            self._logger.debug(
                f"Primary endpoint request successful",
                extra={
                    "feature": feature,
                    "endpoint": primary_endpoint,
                    "api_version": api_version,
                }
            )
            
            # Log warning if response is empty (Requirement 8.3)
            if self._is_empty_response(response):
                self._logger.warning(
                    f"Empty results returned for feature '{feature}' - "
                    f"possible API version mismatch or no data configured",
                    extra={
                        "feature": feature,
                        "endpoint": primary_endpoint,
                        "api_version": api_version,
                        "controller_type": controller_type.value,
                    }
                )
            
            return {
                "data": response,
                "endpoint_used": primary_endpoint,
                "api_version": api_version,
                "fallback_used": False,
            }
        
        except Exception as primary_error:
            # Only attempt fallback for UniFi OS
            if controller_type != ControllerType.UNIFI_OS:
                self._logger.error(
                    f"Request failed for traditional controller, no fallback available",
                    extra={
                        "feature": feature,
                        "endpoint": primary_endpoint,
                        "error": str(primary_error),
                        "error_type": type(primary_error).__name__,
                    }
                )
                raise EndpointError(
                    feature=feature,
                    primary_endpoint=primary_endpoint,
                    primary_error=str(primary_error),
                    fallback_endpoint=None,
                    fallback_error=None,
                    message=f"API request failed for feature '{feature}': {primary_error}"
                ) from primary_error
            
            # Get fallback endpoint
            fallback_template = self.get_fallback_endpoint(
                self.get_endpoint(feature, controller_type)
            )
            
            if not fallback_template:
                self._logger.error(
                    f"No fallback endpoint available for feature '{feature}'",
                    extra={
                        "feature": feature,
                        "primary_endpoint": primary_endpoint,
                        "error": str(primary_error),
                    }
                )
                raise EndpointError(
                    feature=feature,
                    primary_endpoint=primary_endpoint,
                    primary_error=str(primary_error),
                    fallback_endpoint=None,
                    fallback_error=None,
                    message=f"v2 endpoint failed and no fallback available for feature '{feature}'"
                ) from primary_error
            
            fallback_endpoint = fallback_template.replace("{site}", site)
            
            # Log fallback attempt at info level (Requirement 8.2)
            self._logger.info(
                f"v2 endpoint failed for feature '{feature}', attempting v1 fallback",
                extra={
                    "feature": feature,
                    "primary_endpoint": primary_endpoint,
                    "fallback_endpoint": fallback_endpoint,
                    "primary_error": str(primary_error),
                    "primary_error_type": type(primary_error).__name__,
                }
            )
            
            try:
                # Try fallback endpoint
                response = await client.get(fallback_endpoint)
                
                self._logger.info(
                    f"Fallback to v1 endpoint successful for feature '{feature}'",
                    extra={
                        "feature": feature,
                        "fallback_endpoint": fallback_endpoint,
                    }
                )
                
                # Log warning if fallback response is empty (Requirement 8.3)
                if self._is_empty_response(response):
                    self._logger.warning(
                        f"Empty results returned from fallback endpoint for feature '{feature}' - "
                        f"possible API version mismatch or no data configured",
                        extra={
                            "feature": feature,
                            "endpoint": fallback_endpoint,
                            "api_version": "v1",
                            "controller_type": controller_type.value,
                        }
                    )
                
                return {
                    "data": response,
                    "endpoint_used": fallback_endpoint,
                    "api_version": "v1",
                    "fallback_used": True,
                }
            
            except Exception as fallback_error:
                self._logger.error(
                    f"Both v2 and v1 endpoints failed for feature '{feature}'",
                    extra={
                        "feature": feature,
                        "primary_endpoint": primary_endpoint,
                        "primary_error": str(primary_error),
                        "primary_error_type": type(primary_error).__name__,
                        "fallback_endpoint": fallback_endpoint,
                        "fallback_error": str(fallback_error),
                        "fallback_error_type": type(fallback_error).__name__,
                    }
                )
                # Raise structured error with context about both failures
                raise EndpointError(
                    feature=feature,
                    primary_endpoint=primary_endpoint,
                    primary_error=str(primary_error),
                    fallback_endpoint=fallback_endpoint,
                    fallback_error=str(fallback_error),
                    message=(
                        f"Both endpoints failed for feature '{feature}'. "
                        f"v2 endpoint ({primary_endpoint}): {primary_error}. "
                        f"v1 fallback ({fallback_endpoint}): {fallback_error}"
                    )
                ) from fallback_error
    
    def _is_empty_response(self, response: Any) -> bool:
        """Check if a response is empty.
        
        Args:
            response: API response to check
        
        Returns:
            True if response is empty, False otherwise
        """
        if response is None:
            return True
        
        if isinstance(response, dict):
            # Check for empty data field
            data = response.get("data", response)
            if isinstance(data, list):
                return len(data) == 0
            if isinstance(data, dict):
                return len(data) == 0
            return data is None
        
        if isinstance(response, list):
            return len(response) == 0
        
        return False
