"""UniFi MCP API abstraction layer.

This module provides an abstraction layer for handling different UniFi controller
API versions (v1 legacy and v2 UniFi OS). It enables automatic detection of
controller type and transparent routing of API requests to the correct endpoints.

Key Components:
- ControllerType: Enum representing the type of UniFi controller
- ControllerDetector: Detects and caches controller type (UniFi OS vs Traditional)
- EndpointRouter: Routes API requests to correct endpoints based on controller type
- ResponseNormalizer: Normalizes responses from different API versions

Example:
    >>> from unifi_mcp.api import ControllerType, ControllerDetector
    >>> detector = ControllerDetector(client)
    >>> controller_type = await detector.detect()
    >>> if controller_type == ControllerType.UNIFI_OS:
    ...     # Use v2 endpoints
    ...     pass
"""

from .controller_detector import ControllerType, ControllerDetector
from .endpoint_router import EndpointRouter, EndpointError
from .response_normalizer import (
    ResponseNormalizer,
    NormalizedFirewallRule,
    NormalizedIPSStatus,
    NormalizedTrafficRoute,
    NormalizedPortForward,
)

__all__ = [
    "ControllerType",
    "ControllerDetector",
    "EndpointRouter",
    "EndpointError",
    "ResponseNormalizer",
    "NormalizedFirewallRule",
    "NormalizedIPSStatus",
    "NormalizedTrafficRoute",
    "NormalizedPortForward",
]
