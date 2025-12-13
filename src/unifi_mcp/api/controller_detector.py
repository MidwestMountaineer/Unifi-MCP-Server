"""Controller type detection for UniFi MCP Server.

This module provides functionality to detect whether a UniFi controller is
running UniFi OS (Dream Machine, Cloud Gateway, Cloud Key Gen2+) or is a
traditional controller (standalone software, Cloud Key Gen1).

The detection is important because UniFi OS uses v2 API endpoints with
/proxy/network prefix, while traditional controllers use v1 API endpoints.

Key Features:
- Automatic detection via API endpoint probing
- Environment variable override support
- Session-lifetime caching of detection results
- Configurable detection timeout
"""

import asyncio
import logging
import os
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from unifi_mcp.unifi_client import UniFiClient


class ControllerType(Enum):
    """Enumeration of UniFi controller types.
    
    This enum represents the different types of UniFi controllers that the
    MCP server can connect to. Each type uses different API endpoint patterns.
    
    Attributes:
        UNIFI_OS: UniFi OS-based devices (Dream Machine, Dream Machine Pro,
            Cloud Gateway, Cloud Key Gen2+). These use v2 API endpoints with
            /proxy/network prefix (e.g., /proxy/network/v2/api/site/{site}/...).
        TRADITIONAL: Legacy UniFi Controller software (standalone installation
            or Cloud Key Gen1). These use v1 API endpoints without the proxy
            prefix (e.g., /api/s/{site}/rest/...).
        UNKNOWN: Controller type could not be determined. This typically occurs
            when detection fails due to network issues or timeout. The system
            will default to traditional controller behavior in this case.
    """
    
    UNIFI_OS = "unifi_os"
    """UniFi OS devices: Dream Machine, Cloud Gateway, Cloud Key Gen2+.
    
    Uses v2 API endpoints with /proxy/network prefix.
    Examples:
    - /proxy/network/v2/api/site/{site}/trafficroutes
    - /proxy/network/v2/api/site/{site}/threat-management
    - /proxy/network/v2/api/site/{site}/portforward
    """
    
    TRADITIONAL = "traditional"
    """Traditional UniFi Controller: standalone software or Cloud Key Gen1.
    
    Uses v1 API endpoints without proxy prefix.
    Examples:
    - /api/s/{site}/rest/firewallrule
    - /api/s/{site}/rest/setting/ips
    - /api/s/{site}/rest/routing
    """
    
    UNKNOWN = "unknown"
    """Controller type could not be determined.
    
    This occurs when detection fails. The system defaults to traditional
    controller behavior when the type is unknown.
    """


class ControllerDetector:
    """Detects UniFi controller type (UniFi OS vs Traditional).
    
    This class is responsible for determining whether the connected UniFi
    controller is running UniFi OS or is a traditional controller. The
    detection result is cached for the session lifetime to avoid repeated
    detection attempts.
    
    Detection Methods:
    1. Environment variable override (UNIFI_CONTROLLER_TYPE)
    2. API endpoint probing (/proxy/network/api/s/{site}/stat/health)
    
    The detection uses a 5-second timeout to avoid blocking on unresponsive
    controllers.
    
    Example:
        >>> detector = ControllerDetector(client)
        >>> controller_type = await detector.detect()
        >>> if controller_type == ControllerType.UNIFI_OS:
        ...     print("Connected to UniFi OS device")
        ... else:
        ...     print("Connected to traditional controller")
    
    Attributes:
        ENV_OVERRIDE_KEY: Environment variable name for manual override
        DEFAULT_TIMEOUT: Default detection timeout in seconds
    """
    
    ENV_OVERRIDE_KEY = "UNIFI_CONTROLLER_TYPE"
    """Environment variable name for controller type override."""
    
    DEFAULT_TIMEOUT = 5.0
    """Default timeout for detection in seconds."""
    
    # Detection endpoint - this endpoint exists on UniFi OS with /proxy/network prefix
    DETECTION_ENDPOINT = "/proxy/network/api/s/{site}/stat/health"
    """Endpoint used to detect UniFi OS controllers."""
    
    def __init__(self, client: "UniFiClient"):
        """Initialize the controller detector.
        
        Args:
            client: UniFi client instance for making API requests.
                The client should already be connected and authenticated.
        """
        self._client = client
        self._cached_type: Optional[ControllerType] = None
        self._detection_timeout = self.DEFAULT_TIMEOUT
        self._logger = logging.getLogger(__name__)
    
    @property
    def detection_timeout(self) -> float:
        """Get the detection timeout in seconds."""
        return self._detection_timeout
    
    @detection_timeout.setter
    def detection_timeout(self, value: float) -> None:
        """Set the detection timeout in seconds.
        
        Args:
            value: Timeout value in seconds. Must be positive.
        
        Raises:
            ValueError: If timeout is not positive.
        """
        if value <= 0:
            raise ValueError("Detection timeout must be positive")
        self._detection_timeout = value
    
    async def detect(self) -> ControllerType:
        """Detect controller type, using cache if available.
        
        This method first checks for a cached result, then checks for an
        environment variable override, and finally performs API-based
        detection if needed.
        
        The detection result is cached for the session lifetime.
        
        Returns:
            ControllerType indicating the detected controller type.
        
        Note:
            If detection fails, returns UNKNOWN and logs a warning.
            The system should default to traditional controller behavior
            when the type is unknown.
        """
        # Return cached result if available
        if self._cached_type is not None:
            self._logger.debug(
                "Using cached controller type",
                extra={"controller_type": self._cached_type.value}
            )
            return self._cached_type
        
        # Check for environment variable override
        env_override = os.environ.get(self.ENV_OVERRIDE_KEY, "").lower().strip()
        if env_override:
            detected_type = self._parse_env_override(env_override)
            if detected_type is not None:
                self._cached_type = detected_type
                self._logger.info(
                    "Controller type set via environment variable",
                    extra={
                        "controller_type": detected_type.value,
                        "env_var": self.ENV_OVERRIDE_KEY,
                        "env_value": env_override,
                    }
                )
                return detected_type
        
        # Perform API-based detection
        detected_type = await self._detect_via_api()
        self._cached_type = detected_type
        
        return detected_type
    
    def _parse_env_override(self, value: str) -> Optional[ControllerType]:
        """Parse environment variable override value.
        
        Args:
            value: Environment variable value (lowercase, stripped).
        
        Returns:
            ControllerType if valid value, None otherwise.
        """
        if value in ("unifi_os", "unifios", "unifi-os"):
            return ControllerType.UNIFI_OS
        elif value in ("traditional", "legacy", "classic"):
            return ControllerType.TRADITIONAL
        else:
            self._logger.warning(
                f"Invalid {self.ENV_OVERRIDE_KEY} value, ignoring",
                extra={
                    "env_value": value,
                    "valid_values": ["unifi_os", "traditional"],
                }
            )
            return None
    
    async def _detect_via_api(self) -> ControllerType:
        """Detect controller type by probing API endpoints.
        
        This method attempts to access a UniFi OS-specific endpoint.
        If successful, the controller is UniFi OS. If it fails with
        404 or times out, it's assumed to be a traditional controller.
        
        Returns:
            ControllerType based on API probe results.
        """
        self._logger.info("Detecting controller type via API probe")
        
        try:
            # Build the detection URL
            # For UniFi OS, we need to probe the /proxy/network endpoint
            # The client's base_url may or may not include /proxy/network
            # depending on whether API key auth is used
            
            site = self._client.config.site
            detection_endpoint = self.DETECTION_ENDPOINT.replace("{site}", site)
            
            # Build full URL for detection
            # We need to probe the UniFi OS path directly
            base_host = f"https://{self._client.config.host}:{self._client.config.port}"
            detection_url = f"{base_host}{detection_endpoint}"
            
            self._logger.debug(
                "Probing detection endpoint",
                extra={"url": detection_url, "timeout": self._detection_timeout}
            )
            
            # Make the detection request with timeout
            async with asyncio.timeout(self._detection_timeout):
                # Use the client's session directly for the probe
                if self._client.session is None:
                    self._logger.warning(
                        "Client session not available for detection, defaulting to traditional"
                    )
                    return ControllerType.TRADITIONAL
                
                async with self._client.session.get(
                    detection_url,
                    ssl=self._client.ssl_context
                ) as response:
                    if response.status == 200:
                        # Successfully accessed UniFi OS endpoint
                        self._logger.info(
                            "Controller type detected: UniFi OS",
                            extra={
                                "detection_method": "api_probe",
                                "endpoint": detection_endpoint,
                                "status": response.status,
                            }
                        )
                        return ControllerType.UNIFI_OS
                    elif response.status == 404:
                        # Endpoint not found - traditional controller
                        self._logger.info(
                            "Controller type detected: Traditional",
                            extra={
                                "detection_method": "api_probe",
                                "endpoint": detection_endpoint,
                                "status": response.status,
                            }
                        )
                        return ControllerType.TRADITIONAL
                    else:
                        # Unexpected status - log and default to traditional
                        self._logger.warning(
                            f"Unexpected status during detection: {response.status}",
                            extra={
                                "endpoint": detection_endpoint,
                                "status": response.status,
                            }
                        )
                        return ControllerType.TRADITIONAL
        
        except asyncio.TimeoutError:
            self._logger.warning(
                f"Controller detection timed out after {self._detection_timeout}s, "
                "defaulting to traditional",
                extra={"timeout": self._detection_timeout}
            )
            return ControllerType.TRADITIONAL
        
        except Exception as e:
            self._logger.warning(
                f"Controller detection failed: {e}, defaulting to traditional",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return ControllerType.TRADITIONAL
    
    def get_cached_type(self) -> Optional[ControllerType]:
        """Return cached controller type without performing detection.
        
        Returns:
            Cached ControllerType if available, None otherwise.
        """
        return self._cached_type
    
    def clear_cache(self) -> None:
        """Clear the cached controller type.
        
        This forces re-detection on the next call to detect().
        """
        self._cached_type = None
        self._logger.debug("Controller type cache cleared")
    
    def set_type(self, controller_type: ControllerType) -> None:
        """Manually set the controller type.
        
        This can be used to override detection results or set the type
        when detection is not possible.
        
        Args:
            controller_type: The controller type to set.
        """
        self._cached_type = controller_type
        self._logger.info(
            "Controller type manually set",
            extra={"controller_type": controller_type.value}
        )
