"""Demo script for security tools.

This script demonstrates the firewall rule tools:
- ListFirewallRulesTool: List all firewall rules with filtering
- GetFirewallRuleDetailsTool: Get detailed information about a specific rule

Run this script to see the tools in action with mock data.
"""

import asyncio
import json
from unittest.mock import AsyncMock

from unifi_mcp.tools.security import (
    ListFirewallRulesTool,
    GetFirewallRuleDetailsTool,
)


# Mock firewall rule data (simulating UniFi API responses)
MOCK_FIREWALL_RULES = [
    {
        "_id": "rule1",
        "rule_index": 2000,
        "name": "Allow LAN to WAN",
        "enabled": True,
        "action": "accept",
        "protocol": "all",
        "src_firewallgroup_ids": ["LAN"],
        "dst_firewallgroup_ids": ["WAN"],
        "src_address": "",
        "dst_address": "",
        "dst_port": "",
        "logging": False,
        "state_new": True,
        "state_established": True,
        "state_invalid": False,
        "state_related": True,
    },
    {
        "_id": "rule2",
        "rule_index": 2001,
        "name": "Block IoT to Core",
        "enabled": True,
        "action": "drop",
        "protocol": "all",
        "src_networkconf_id": "iot_network",
        "dst_networkconf_id": "core_network",
        "src_address": "192.168.30.0/24",
        "dst_address": "192.168.10.0/24",
        "dst_port": "",
        "logging": True,
        "state_new": True,
        "state_established": False,
        "state_invalid": False,
        "state_related": False,
    },
    {
        "_id": "rule3",
        "rule_index": 2002,
        "name": "Allow HTTPS to Web Server",
        "enabled": True,
        "action": "accept",
        "protocol": "tcp",
        "src_address": "any",
        "dst_address": "192.168.10.50",
        "dst_port": "443",
        "logging": False,
        "state_new": True,
        "state_established": True,
        "state_invalid": False,
        "state_related": True,
    },
    {
        "_id": "rule4",
        "rule_index": 2003,
        "name": "Block Guest to LAN",
        "enabled": True,
        "action": "reject",
        "protocol": "all",
        "src_networkconf_id": "guest_network",
        "dst_firewallgroup_ids": ["LAN"],
        "src_address": "192.168.50.0/24",
        "dst_address": "",
        "dst_port": "",
        "logging": True,
        "state_new": True,
        "state_established": False,
        "state_invalid": False,
        "state_related": False,
    },
    {
        "_id": "rule5",
        "rule_index": 2004,
        "name": "Allow DNS",
        "enabled": False,  # Disabled rule
        "action": "accept",
        "protocol": "udp",
        "src_address": "any",
        "dst_address": "192.168.10.1",
        "dst_port": "53",
        "logging": False,
        "state_new": True,
        "state_established": True,
        "state_invalid": False,
        "state_related": True,
    },
]


async def demo_list_firewall_rules():
    """Demo: List all firewall rules."""
    print("\n" + "=" * 80)
    print("DEMO: List Firewall Rules")
    print("=" * 80)
    
    # Create mock UniFi client
    mock_client = AsyncMock()
    mock_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
    
    # Create tool instance
    tool = ListFirewallRulesTool()
    
    # Test 1: List all rules
    print("\n--- Test 1: List all firewall rules ---")
    result = await tool.invoke(mock_client, {})
    print(json.dumps(result, indent=2))
    
    # Test 2: List only enabled rules
    print("\n--- Test 2: List only enabled rules ---")
    result = await tool.invoke(mock_client, {"enabled_only": True})
    print(json.dumps(result, indent=2))
    
    # Test 3: Pagination
    print("\n--- Test 3: List rules with pagination (page_size=2) ---")
    result = await tool.invoke(mock_client, {"page": 1, "page_size": 2})
    print(json.dumps(result, indent=2))


async def demo_get_firewall_rule_details():
    """Demo: Get firewall rule details."""
    print("\n" + "=" * 80)
    print("DEMO: Get Firewall Rule Details")
    print("=" * 80)
    
    # Create mock UniFi client
    mock_client = AsyncMock()
    mock_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
    
    # Create tool instance
    tool = GetFirewallRuleDetailsTool()
    
    # Test 1: Get details for a specific rule
    print("\n--- Test 1: Get details for 'Block IoT to Core' rule ---")
    result = await tool.invoke(mock_client, {"rule_id": "rule2"})
    print(json.dumps(result, indent=2))
    
    # Test 2: Get details for another rule
    print("\n--- Test 2: Get details for 'Allow HTTPS to Web Server' rule ---")
    result = await tool.invoke(mock_client, {"rule_id": "rule3"})
    print(json.dumps(result, indent=2))
    
    # Test 3: Try to get details for non-existent rule
    print("\n--- Test 3: Try to get details for non-existent rule ---")
    result = await tool.invoke(mock_client, {"rule_id": "nonexistent"})
    print(json.dumps(result, indent=2))


async def demo_tool_validation():
    """Demo: Tool input validation."""
    print("\n" + "=" * 80)
    print("DEMO: Tool Input Validation")
    print("=" * 80)
    
    # Create mock UniFi client
    mock_client = AsyncMock()
    mock_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
    
    # Test 1: Missing required parameter
    print("\n--- Test 1: Missing required parameter (rule_id) ---")
    tool = GetFirewallRuleDetailsTool()
    result = await tool.invoke(mock_client, {})
    print(json.dumps(result, indent=2))
    
    # Test 2: Invalid parameter type
    print("\n--- Test 2: Invalid parameter type (enabled_only should be boolean) ---")
    tool = ListFirewallRulesTool()
    result = await tool.invoke(mock_client, {"enabled_only": "yes"})
    print(json.dumps(result, indent=2))


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("SECURITY TOOLS DEMO")
    print("=" * 80)
    print("\nThis demo showcases the firewall rule tools:")
    print("- ListFirewallRulesTool: List all firewall rules with filtering")
    print("- GetFirewallRuleDetailsTool: Get detailed information about a specific rule")
    print("\nAll demos use mock data to simulate UniFi API responses.")
    
    await demo_list_firewall_rules()
    await demo_get_firewall_rule_details()
    await demo_tool_validation()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey takeaways:")
    print("- Firewall rules can be listed with optional filtering by enabled status")
    print("- Pagination is supported for large rule sets")
    print("- Detailed rule information includes action, zones, addresses, and ports")
    print("- Input validation provides clear error messages")
    print("- All data is formatted for AI consumption")


if __name__ == "__main__":
    asyncio.run(main())
