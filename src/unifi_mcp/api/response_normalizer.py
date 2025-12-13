"""Response normalization for UniFi MCP Server.

This module provides functionality to normalize API responses from different
UniFi controller types (UniFi OS v2 API vs Traditional v1 API) into a
consistent format.

The normalization ensures that tools receive consistent data structures
regardless of which API version the data came from, enabling seamless
operation across different controller types.

Key Features:
- Normalized data structures for firewall rules, IPS, routes, port forwards
- Automatic field mapping from v1 and v2 API responses
- Consistent output format for all security tools
- Metadata tracking of source API version
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .controller_detector import ControllerType


@dataclass
class NormalizedFirewallRule:
    """Normalized firewall rule from either API version.
    
    This dataclass represents a firewall rule in a consistent format,
    regardless of whether it came from v1 or v2 API.
    
    Attributes:
        id: Unique identifier for the rule
        name: Human-readable name/description of the rule
        enabled: Whether the rule is currently active
        action: Rule action (ALLOW, DENY, REJECT)
        protocol: Network protocol (TCP, UDP, ALL, etc.)
        source_zone: Source network zone
        destination_zone: Destination network zone
        source_address: Source IP/network address
        destination_address: Destination IP/network address
        destination_port: Destination port(s)
        logging: Whether logging is enabled for this rule
        api_version: Source API version (v1 or v2)
        raw_type: Original type from API response
    """
    id: str
    name: str
    enabled: bool
    action: str
    protocol: str
    source_zone: str = ""
    destination_zone: str = ""
    source_address: str = ""
    destination_address: str = ""
    destination_port: str = ""
    logging: bool = False
    api_version: str = ""
    raw_type: str = ""


@dataclass
class NormalizedIPSStatus:
    """Normalized IPS status from either API version.
    
    This dataclass represents IPS/threat management status in a consistent
    format, regardless of whether it came from v1 or v2 API.
    
    Attributes:
        enabled: Whether IPS is enabled
        enabled_display: Human-readable enabled state ("yes" or "no")
        protection_mode: IPS mode (detection, prevention)
        threat_statistics: Dictionary of threat counts by category
        recent_alerts: List of recent IPS alerts
        api_version: Source API version (v1 or v2)
        controller_type: Type of controller (unifi_os or traditional)
    """
    enabled: bool
    enabled_display: str
    protection_mode: str
    threat_statistics: Dict[str, int] = field(default_factory=dict)
    recent_alerts: List[Dict[str, Any]] = field(default_factory=list)
    api_version: str = ""
    controller_type: str = ""


@dataclass
class NormalizedTrafficRoute:
    """Normalized traffic route from either API version.
    
    This dataclass represents a traffic route in a consistent format,
    regardless of whether it came from v1 or v2 API.
    
    Attributes:
        id: Unique identifier for the route
        name: Human-readable name/description of the route
        enabled: Whether the route is currently active
        route_type: Type of route (static, policy)
        destination_network: Destination network CIDR
        next_hop: Next hop IP address or interface
        interface: Network interface for the route
        distance: Administrative distance/metric
        api_version: Source API version (v1 or v2)
    """
    id: str
    name: str
    enabled: bool
    route_type: str
    destination_network: str = ""
    next_hop: str = ""
    interface: str = ""
    distance: int = 0
    api_version: str = ""


@dataclass
class NormalizedPortForward:
    """Normalized port forward from either API version.
    
    This dataclass represents a port forward rule in a consistent format,
    regardless of whether it came from v1 or v2 API.
    
    Attributes:
        id: Unique identifier for the port forward
        name: Human-readable name/description
        enabled: Whether the port forward is currently active
        protocol: Network protocol (TCP, UDP, TCP/UDP)
        source_port: External/source port(s)
        destination_port: Internal/destination port(s)
        destination_ip: Internal destination IP address
        source_ip: Optional source IP restriction
        api_version: Source API version (v1 or v2)
    """
    id: str
    name: str
    enabled: bool
    protocol: str
    source_port: str
    destination_port: str
    destination_ip: str
    source_ip: str = ""
    api_version: str = ""



class ResponseNormalizer:
    """Normalizes API responses to consistent format.
    
    This class provides methods to normalize responses from different UniFi
    API versions (v1 traditional and v2 UniFi OS) into consistent data
    structures that can be used by the MCP tools.
    
    Example:
        >>> normalizer = ResponseNormalizer()
        >>> rules = normalizer.normalize_firewall_rules(v2_data, ControllerType.UNIFI_OS)
        >>> for rule in rules:
        ...     print(f"{rule.name}: {rule.action}")
    """
    
    def __init__(self):
        """Initialize the response normalizer."""
        self._logger = logging.getLogger(__name__)
    
    def normalize_firewall_rules(
        self,
        data: List[Dict[str, Any]],
        source: ControllerType
    ) -> List[NormalizedFirewallRule]:
        """Normalize firewall rules from v1 or v2 API.
        
        Args:
            data: List of firewall rule dictionaries from API
            source: Controller type indicating API version
        
        Returns:
            List of NormalizedFirewallRule objects
        """
        if source == ControllerType.UNIFI_OS:
            return self._normalize_firewall_rules_v2(data)
        else:
            return self._normalize_firewall_rules_v1(data)
    
    def _normalize_firewall_rules_v1(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedFirewallRule]:
        """Normalize firewall rules from v1 API.
        
        v1 API fields:
        - _id: Rule ID
        - name: Rule name
        - enabled: Boolean enabled state
        - action: accept, drop, reject
        - protocol: all, tcp, udp, tcp_udp, etc.
        - src_address: Source address
        - dst_address: Destination address
        - dst_port: Destination port
        - logging: Boolean logging state
        - ruleset: Ruleset name (e.g., WAN_IN, LAN_OUT)
        """
        normalized = []
        for rule in data:
            try:
                # Map v1 action to normalized action
                action_map = {
                    "accept": "ALLOW",
                    "drop": "DENY",
                    "reject": "REJECT",
                }
                raw_action = str(rule.get("action", "")).lower()
                action = action_map.get(raw_action, raw_action.upper())
                
                # Map v1 protocol to normalized protocol
                protocol_map = {
                    "all": "ALL",
                    "tcp": "TCP",
                    "udp": "UDP",
                    "tcp_udp": "TCP/UDP",
                    "icmp": "ICMP",
                }
                raw_protocol = str(rule.get("protocol", "all")).lower()
                protocol = protocol_map.get(raw_protocol, raw_protocol.upper())
                
                # Extract zone info from ruleset if available
                ruleset = str(rule.get("ruleset", ""))
                source_zone = ""
                dest_zone = ""
                if "_" in ruleset:
                    parts = ruleset.split("_")
                    if len(parts) >= 2:
                        source_zone = parts[0]
                        dest_zone = parts[1] if parts[1] not in ("IN", "OUT", "LOCAL") else ""
                
                normalized_rule = NormalizedFirewallRule(
                    id=str(rule.get("_id", "")),
                    name=str(rule.get("name", "")),
                    enabled=bool(rule.get("enabled", True)),
                    action=action,
                    protocol=protocol,
                    source_zone=source_zone,
                    destination_zone=dest_zone,
                    source_address=str(rule.get("src_address", "")),
                    destination_address=str(rule.get("dst_address", "")),
                    destination_port=str(rule.get("dst_port", "")),
                    logging=bool(rule.get("logging", False)),
                    api_version="v1",
                    raw_type=str(rule.get("rule_index", "")),
                )
                normalized.append(normalized_rule)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v1 firewall rule: {e}",
                    extra={"rule": rule, "error": str(e)}
                )
        
        return normalized

    
    def _normalize_firewall_rules_v2(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedFirewallRule]:
        """Normalize firewall rules from v2 API (traffic routes).
        
        v2 API fields (trafficroutes):
        - id or _id: Rule ID
        - description: Rule description/name
        - enabled: Boolean enabled state
        - action: ALLOW, DENY, REJECT
        - ip_protocol: all, tcp, udp, etc.
        - source: Source configuration object
        - destination: Destination configuration object
        - logging: Boolean logging state
        - matching_target: Target type
        """
        normalized = []
        for rule in data:
            try:
                # Get ID from either 'id' or '_id' field
                rule_id = str(rule.get("id", rule.get("_id", "")))
                
                # Get name from description or name field
                name = str(rule.get("description", rule.get("name", "")))
                
                # Action is already uppercase in v2
                action = str(rule.get("action", "ALLOW")).upper()
                
                # Protocol mapping
                raw_protocol = str(rule.get("ip_protocol", rule.get("protocol", "all"))).lower()
                protocol_map = {
                    "all": "ALL",
                    "tcp": "TCP",
                    "udp": "UDP",
                    "tcp_udp": "TCP/UDP",
                    "icmp": "ICMP",
                    "any": "ALL",
                }
                protocol = protocol_map.get(raw_protocol, raw_protocol.upper())
                
                # Extract source info
                source_obj = rule.get("source", {})
                if isinstance(source_obj, dict):
                    source_zone = str(source_obj.get("zone", source_obj.get("network", "")))
                    source_address = str(source_obj.get("address", source_obj.get("ip", "")))
                else:
                    source_zone = ""
                    source_address = str(source_obj) if source_obj else ""
                
                # Extract destination info
                dest_obj = rule.get("destination", {})
                if isinstance(dest_obj, dict):
                    dest_zone = str(dest_obj.get("zone", dest_obj.get("network", "")))
                    dest_address = str(dest_obj.get("address", dest_obj.get("ip", "")))
                    dest_port = str(dest_obj.get("port", dest_obj.get("port_ranges", "")))
                else:
                    dest_zone = ""
                    dest_address = str(dest_obj) if dest_obj else ""
                    dest_port = ""
                
                normalized_rule = NormalizedFirewallRule(
                    id=rule_id,
                    name=name,
                    enabled=bool(rule.get("enabled", True)),
                    action=action,
                    protocol=protocol,
                    source_zone=source_zone,
                    destination_zone=dest_zone,
                    source_address=source_address,
                    destination_address=dest_address,
                    destination_port=dest_port,
                    logging=bool(rule.get("logging", False)),
                    api_version="v2",
                    raw_type=str(rule.get("matching_target", rule.get("type", ""))),
                )
                normalized.append(normalized_rule)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v2 firewall rule: {e}",
                    extra={"rule": rule, "error": str(e)}
                )
        
        return normalized

    
    def normalize_ips_status(
        self,
        data: Dict[str, Any],
        source: ControllerType
    ) -> NormalizedIPSStatus:
        """Normalize IPS status from v1 or v2 API.
        
        Args:
            data: IPS status dictionary from API
            source: Controller type indicating API version
        
        Returns:
            NormalizedIPSStatus object
        """
        if source == ControllerType.UNIFI_OS:
            return self._normalize_ips_status_v2(data)
        else:
            return self._normalize_ips_status_v1(data)
    
    def _normalize_ips_status_v1(
        self,
        data: Dict[str, Any]
    ) -> NormalizedIPSStatus:
        """Normalize IPS status from v1 API.
        
        v1 API fields (setting/ips):
        - ips_mode: off, ids, ips
        - enabled: Boolean (may not be present)
        - suppression: Suppression settings
        """
        try:
            # Determine enabled state from ips_mode
            ips_mode = str(data.get("ips_mode", "off")).lower()
            enabled = ips_mode in ("ids", "ips")
            
            # Map mode to protection mode
            mode_map = {
                "off": "disabled",
                "ids": "detection",
                "ips": "prevention",
            }
            protection_mode = mode_map.get(ips_mode, ips_mode)
            
            return NormalizedIPSStatus(
                enabled=enabled,
                enabled_display="yes" if enabled else "no",
                protection_mode=protection_mode,
                threat_statistics={},
                recent_alerts=[],
                api_version="v1",
                controller_type="traditional",
            )
        except Exception as e:
            self._logger.warning(
                f"Failed to normalize v1 IPS status: {e}",
                extra={"data": data, "error": str(e)}
            )
            return NormalizedIPSStatus(
                enabled=False,
                enabled_display="no",
                protection_mode="unknown",
                api_version="v1",
                controller_type="traditional",
            )
    
    def _normalize_ips_status_v2(
        self,
        data: Dict[str, Any]
    ) -> NormalizedIPSStatus:
        """Normalize IPS status from v2 API (threat-management).
        
        v2 API fields (threat-management):
        - enabled: Boolean enabled state
        - mode: detection, prevention
        - stats: Statistics object
        - alerts: Recent alerts list
        """
        try:
            # v2 API has explicit enabled field
            enabled = bool(data.get("enabled", False))
            
            # Get protection mode
            mode = str(data.get("mode", "detection")).lower()
            protection_mode = mode if mode in ("detection", "prevention") else "detection"
            
            # Extract statistics if available
            stats = data.get("stats", data.get("statistics", {}))
            threat_statistics = {}
            if isinstance(stats, dict):
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        threat_statistics[key] = int(value)
            
            # Extract alerts if available
            alerts = data.get("alerts", data.get("recent_alerts", []))
            recent_alerts = alerts if isinstance(alerts, list) else []
            
            return NormalizedIPSStatus(
                enabled=enabled,
                enabled_display="yes" if enabled else "no",
                protection_mode=protection_mode,
                threat_statistics=threat_statistics,
                recent_alerts=recent_alerts,
                api_version="v2",
                controller_type="unifi_os",
            )
        except Exception as e:
            self._logger.warning(
                f"Failed to normalize v2 IPS status: {e}",
                extra={"data": data, "error": str(e)}
            )
            return NormalizedIPSStatus(
                enabled=False,
                enabled_display="no",
                protection_mode="unknown",
                api_version="v2",
                controller_type="unifi_os",
            )

    
    def normalize_traffic_routes(
        self,
        data: List[Dict[str, Any]],
        source: ControllerType
    ) -> List[NormalizedTrafficRoute]:
        """Normalize traffic routes from v1 or v2 API.
        
        Args:
            data: List of traffic route dictionaries from API
            source: Controller type indicating API version
        
        Returns:
            List of NormalizedTrafficRoute objects
        """
        if source == ControllerType.UNIFI_OS:
            return self._normalize_traffic_routes_v2(data)
        else:
            return self._normalize_traffic_routes_v1(data)
    
    def _normalize_traffic_routes_v1(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedTrafficRoute]:
        """Normalize traffic routes from v1 API.
        
        v1 API fields (routing):
        - _id: Route ID
        - name: Route name
        - enabled: Boolean enabled state
        - type: static, policy
        - static-route_network: Destination network
        - static-route_nexthop: Next hop address
        - static-route_interface: Interface name
        - static-route_distance: Administrative distance
        """
        normalized = []
        for route in data:
            try:
                # Get route type
                route_type = str(route.get("type", "static")).lower()
                
                # Extract destination network
                dest_network = str(route.get(
                    "static-route_network",
                    route.get("network", route.get("destination", ""))
                ))
                
                # Extract next hop
                next_hop = str(route.get(
                    "static-route_nexthop",
                    route.get("nexthop", route.get("gateway", ""))
                ))
                
                # Extract interface
                interface = str(route.get(
                    "static-route_interface",
                    route.get("interface", "")
                ))
                
                # Extract distance
                distance_raw = route.get(
                    "static-route_distance",
                    route.get("distance", route.get("metric", 0))
                )
                distance = int(distance_raw) if distance_raw else 0
                
                normalized_route = NormalizedTrafficRoute(
                    id=str(route.get("_id", "")),
                    name=str(route.get("name", "")),
                    enabled=bool(route.get("enabled", True)),
                    route_type=route_type,
                    destination_network=dest_network,
                    next_hop=next_hop,
                    interface=interface,
                    distance=distance,
                    api_version="v1",
                )
                normalized.append(normalized_route)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v1 traffic route: {e}",
                    extra={"route": route, "error": str(e)}
                )
        
        return normalized
    
    def _normalize_traffic_routes_v2(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedTrafficRoute]:
        """Normalize traffic routes from v2 API.
        
        v2 API fields (trafficroutes):
        - id or _id: Route ID
        - description or name: Route name
        - enabled: Boolean enabled state
        - matching_target: Route type indicator
        - destination: Destination configuration
        - target_device: Next hop/target
        - interface: Interface configuration
        """
        normalized = []
        for route in data:
            try:
                # Get ID
                route_id = str(route.get("id", route.get("_id", "")))
                
                # Get name
                name = str(route.get("description", route.get("name", "")))
                
                # Determine route type from matching_target or type
                matching_target = str(route.get("matching_target", route.get("type", ""))).lower()
                if "policy" in matching_target:
                    route_type = "policy"
                else:
                    route_type = "static"
                
                # Extract destination network
                dest_obj = route.get("destination", {})
                if isinstance(dest_obj, dict):
                    dest_network = str(dest_obj.get("network", dest_obj.get("address", "")))
                else:
                    dest_network = str(dest_obj) if dest_obj else ""
                
                # Extract next hop
                target = route.get("target_device", route.get("target", {}))
                if isinstance(target, dict):
                    next_hop = str(target.get("ip", target.get("address", "")))
                else:
                    next_hop = str(target) if target else ""
                
                # Extract interface
                iface = route.get("interface", {})
                if isinstance(iface, dict):
                    interface = str(iface.get("name", iface.get("id", "")))
                else:
                    interface = str(iface) if iface else ""
                
                # Extract distance/metric
                distance_raw = route.get("distance", route.get("metric", 0))
                distance = int(distance_raw) if distance_raw else 0
                
                normalized_route = NormalizedTrafficRoute(
                    id=route_id,
                    name=name,
                    enabled=bool(route.get("enabled", True)),
                    route_type=route_type,
                    destination_network=dest_network,
                    next_hop=next_hop,
                    interface=interface,
                    distance=distance,
                    api_version="v2",
                )
                normalized.append(normalized_route)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v2 traffic route: {e}",
                    extra={"route": route, "error": str(e)}
                )
        
        return normalized

    
    def normalize_port_forwards(
        self,
        data: List[Dict[str, Any]],
        source: ControllerType
    ) -> List[NormalizedPortForward]:
        """Normalize port forwards from v1 or v2 API.
        
        Args:
            data: List of port forward dictionaries from API
            source: Controller type indicating API version
        
        Returns:
            List of NormalizedPortForward objects
        """
        if source == ControllerType.UNIFI_OS:
            return self._normalize_port_forwards_v2(data)
        else:
            return self._normalize_port_forwards_v1(data)
    
    def _normalize_port_forwards_v1(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedPortForward]:
        """Normalize port forwards from v1 API.
        
        v1 API fields (portforward):
        - _id: Port forward ID
        - name: Port forward name
        - enabled: Boolean enabled state
        - proto: tcp, udp, tcp_udp
        - src: Source port
        - dst_port: Destination port
        - fwd: Forward destination IP
        - fwd_port: Forward destination port
        - src_ip: Source IP restriction (optional)
        """
        normalized = []
        for pf in data:
            try:
                # Map protocol
                raw_proto = str(pf.get("proto", pf.get("protocol", "tcp"))).lower()
                protocol_map = {
                    "tcp": "TCP",
                    "udp": "UDP",
                    "tcp_udp": "TCP/UDP",
                    "both": "TCP/UDP",
                }
                protocol = protocol_map.get(raw_proto, raw_proto.upper())
                
                # Get source port (external port)
                src_port = str(pf.get("src", pf.get("dst_port", pf.get("external_port", ""))))
                
                # Get destination port (internal port)
                dst_port = str(pf.get("fwd_port", pf.get("internal_port", src_port)))
                
                # Get destination IP
                dst_ip = str(pf.get("fwd", pf.get("fwd_ip", pf.get("destination_ip", ""))))
                
                # Get source IP restriction
                src_ip = str(pf.get("src_ip", pf.get("source_ip", "")))
                
                normalized_pf = NormalizedPortForward(
                    id=str(pf.get("_id", "")),
                    name=str(pf.get("name", "")),
                    enabled=bool(pf.get("enabled", True)),
                    protocol=protocol,
                    source_port=src_port,
                    destination_port=dst_port,
                    destination_ip=dst_ip,
                    source_ip=src_ip,
                    api_version="v1",
                )
                normalized.append(normalized_pf)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v1 port forward: {e}",
                    extra={"port_forward": pf, "error": str(e)}
                )
        
        return normalized
    
    def _normalize_port_forwards_v2(
        self,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedPortForward]:
        """Normalize port forwards from v2 API.
        
        v2 API fields (portforward):
        - id or _id: Port forward ID
        - name or description: Port forward name
        - enabled: Boolean enabled state
        - protocol: TCP, UDP, TCP_UDP
        - port: External port
        - forward_port: Internal port
        - forward_ip: Internal IP
        - source: Source restriction (optional)
        """
        normalized = []
        for pf in data:
            try:
                # Get ID
                pf_id = str(pf.get("id", pf.get("_id", "")))
                
                # Get name
                name = str(pf.get("name", pf.get("description", "")))
                
                # Map protocol
                raw_proto = str(pf.get("protocol", pf.get("proto", "TCP"))).upper()
                protocol_map = {
                    "TCP": "TCP",
                    "UDP": "UDP",
                    "TCP_UDP": "TCP/UDP",
                    "BOTH": "TCP/UDP",
                }
                protocol = protocol_map.get(raw_proto, raw_proto)
                
                # Get source port (external port)
                src_port = str(pf.get("port", pf.get("external_port", pf.get("dst_port", ""))))
                
                # Get destination port (internal port)
                dst_port = str(pf.get("forward_port", pf.get("fwd_port", pf.get("internal_port", src_port))))
                
                # Get destination IP
                dst_ip = str(pf.get("forward_ip", pf.get("fwd", pf.get("destination_ip", ""))))
                
                # Get source IP restriction
                source_obj = pf.get("source", {})
                if isinstance(source_obj, dict):
                    src_ip = str(source_obj.get("ip", source_obj.get("address", "")))
                else:
                    src_ip = str(source_obj) if source_obj else ""
                
                normalized_pf = NormalizedPortForward(
                    id=pf_id,
                    name=name,
                    enabled=bool(pf.get("enabled", True)),
                    protocol=protocol,
                    source_port=src_port,
                    destination_port=dst_port,
                    destination_ip=dst_ip,
                    source_ip=src_ip,
                    api_version="v2",
                )
                normalized.append(normalized_pf)
            except Exception as e:
                self._logger.warning(
                    f"Failed to normalize v2 port forward: {e}",
                    extra={"port_forward": pf, "error": str(e)}
                )
        
        return normalized

    
    def to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert a normalized object to a dictionary.
        
        Args:
            obj: A normalized dataclass object
        
        Returns:
            Dictionary representation of the object
        """
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return dict(obj) if hasattr(obj, '__iter__') else {"value": obj}
    
    def to_dict_list(
        self,
        objects: List[Any]
    ) -> List[Dict[str, Any]]:
        """Convert a list of normalized objects to dictionaries.
        
        Args:
            objects: List of normalized dataclass objects
        
        Returns:
            List of dictionary representations
        """
        return [self.to_dict(obj) for obj in objects]
