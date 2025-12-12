"""Unit tests for security tools (firewall rules).

Tests cover:
- ListFirewallRulesTool: rule listing with filtering and pagination
- GetFirewallRuleDetailsTool: rule detail retrieval
- Mock UniFi API responses
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.security import (
    ListFirewallRulesTool,
    GetFirewallRuleDetailsTool,
)
from unifi_mcp.tools.base import ToolError
from unifi_mcp.unifi_client import UniFiClient


# Mock firewall rule data (simulating UniFi API responses)

MOCK_FIREWALL_RULES = [
    {
        "_id": "rule1",
        "rule_index": 2000,
        "name": "Allow Core to Internet",
        "enabled": True,
        "action": "accept",
        "protocol": "all",
        "src_firewallgroup_ids": ["group_core"],
        "dst_firewallgroup_ids": [],
        "src_address": "192.168.10.0/24",
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
        "src_firewallgroup_ids": ["group_iot"],
        "dst_firewallgroup_ids": ["group_core"],
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
        "src_firewallgroup_ids": [],
        "dst_firewallgroup_ids": [],
        "src_address": "",
        "dst_address": "192.168.10.50",
        "dst_port": "443",
        "logging": False,
        "state_new": True,
        "state_established": True,
        "state_invalid": False,
        "state_related": True,
        "tcp_flags": ["syn"],
    },
    {
        "_id": "rule4",
        "rule_index": 2003,
        "name": "Disabled Test Rule",
        "enabled": False,
        "action": "reject",
        "protocol": "tcp_udp",
        "src_firewallgroup_ids": [],
        "dst_firewallgroup_ids": [],
        "src_address": "",
        "dst_address": "",
        "dst_port": "22",
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
        "enabled": True,
        "action": "accept",
        "protocol": "udp",
        "src_firewallgroup_ids": [],
        "dst_firewallgroup_ids": [],
        "src_address": "",
        "dst_address": "",
        "dst_port": "53",
        "logging": False,
        "state_new": True,
        "state_established": True,
        "state_invalid": False,
        "state_related": True,
    },
]


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    client.get = AsyncMock()
    return client


class TestListFirewallRulesTool:
    """Test ListFirewallRulesTool functionality."""
    
    @pytest.mark.asyncio
    async def test_list_all_rules(self, mock_unifi_client):
        """Test listing all firewall rules without filtering."""
        # Setup mock response
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        # Create tool and execute
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Verify result structure
        assert result["success"] is True
        assert "data" in result
        assert result["count"] == 5
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 50
        
        # Verify API call
        mock_unifi_client.get.assert_called_once()
        call_args = mock_unifi_client.get.call_args[0][0]
        assert "/rest/firewallrule" in call_args
    
    @pytest.mark.asyncio
    async def test_list_rules_enabled_only(self, mock_unifi_client):
        """Test filtering rules by enabled status."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client, enabled_only=True)
        
        # Should only return enabled rules (4 out of 5)
        assert result["success"] is True
        assert result["count"] == 4
        assert all(rule["enabled"] is True for rule in result["data"])
    
    @pytest.mark.asyncio
    async def test_list_rules_pagination(self, mock_unifi_client):
        """Test pagination of firewall rule list."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        
        # Get first page (2 items per page)
        result_page1 = await tool.execute(
            mock_unifi_client,
            page=1,
            page_size=2
        )
        
        assert result_page1["success"] is True
        assert result_page1["count"] == 2
        assert result_page1["total"] == 5
        assert result_page1["page"] == 1
        assert result_page1["page_size"] == 2
        
        # Get second page
        result_page2 = await tool.execute(
            mock_unifi_client,
            page=2,
            page_size=2
        )
        
        assert result_page2["count"] == 2
        assert result_page2["page"] == 2
        
        # Verify different rules on each page
        page1_ids = [r["id"] for r in result_page1["data"]]
        page2_ids = [r["id"] for r in result_page2["data"]]
        assert page1_ids != page2_ids
    
    @pytest.mark.asyncio
    async def test_list_rules_last_page_partial(self, mock_unifi_client):
        """Test last page with partial results."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(
            mock_unifi_client,
            page=2,
            page_size=3
        )
        
        # Last page should have only 2 rules (5 total, 3 per page)
        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 5
        assert result["page"] == 2
    
    @pytest.mark.asyncio
    async def test_list_rules_empty_result(self, mock_unifi_client):
        """Test listing rules when none exist."""
        mock_unifi_client.get.return_value = {"data": []}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        assert result["success"] is True
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["data"] == []
    
    @pytest.mark.asyncio
    async def test_list_rules_api_error(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        tool = ListFirewallRulesTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client)
        
        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve firewall rules" in error.message
    
    @pytest.mark.asyncio
    async def test_rule_summary_format(self, mock_unifi_client):
        """Test that rule summary contains expected fields."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check first rule has expected summary fields
        rule = result["data"][0]
        expected_fields = [
            "id", "rule_index", "name", "enabled", "action",
            "protocol", "source_zone", "destination_zone",
            "source_address", "destination_address", "destination_port", "logging"
        ]
        
        for field in expected_fields:
            assert field in rule, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_rule_action_formatting(self, mock_unifi_client):
        """Test that rule actions are formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check actions are uppercase
        assert result["data"][0]["action"] == "ACCEPT"
        assert result["data"][1]["action"] == "DROP"
        assert result["data"][3]["action"] == "REJECT"
    
    @pytest.mark.asyncio
    async def test_protocol_formatting(self, mock_unifi_client):
        """Test that protocols are formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check protocol formatting
        assert result["data"][0]["protocol"] == "ALL"
        assert result["data"][2]["protocol"] == "TCP"
        assert result["data"][3]["protocol"] == "TCP/UDP"
        assert result["data"][4]["protocol"] == "UDP"
    
    @pytest.mark.asyncio
    async def test_address_formatting(self, mock_unifi_client):
        """Test that addresses are formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check address formatting
        assert result["data"][0]["source_address"] == "192.168.10.0/24"
        assert result["data"][1]["destination_address"] == "192.168.10.0/24"
        assert result["data"][2]["destination_address"] == "192.168.10.50"
    
    @pytest.mark.asyncio
    async def test_port_formatting(self, mock_unifi_client):
        """Test that ports are formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = ListFirewallRulesTool()
        result = await tool.execute(mock_unifi_client)
        
        # Check port formatting
        assert result["data"][2]["destination_port"] == "443"
        assert result["data"][3]["destination_port"] == "22"
        assert result["data"][4]["destination_port"] == "53"
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        tool = ListFirewallRulesTool()
        
        assert tool.name == "unifi_list_firewall_rules"
        assert tool.category == "security"
        assert tool.requires_confirmation is False
        assert "firewall" in tool.description.lower()
        
        # Check input schema
        assert "properties" in tool.input_schema
        assert "enabled_only" in tool.input_schema["properties"]
        assert "page" in tool.input_schema["properties"]
        assert "page_size" in tool.input_schema["properties"]


class TestGetFirewallRuleDetailsTool:
    """Test GetFirewallRuleDetailsTool functionality."""
    
    @pytest.mark.asyncio
    async def test_get_rule_by_id(self, mock_unifi_client):
        """Test getting firewall rule details by ID."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule1")
        
        assert result["success"] is True
        assert result["type"] == "firewall_rule"
        assert "data" in result
        
        rule = result["data"]
        assert rule["id"] == "rule1"
        assert rule["name"] == "Allow Core to Internet"
        assert rule["action"] == "ACCEPT"
    
    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, mock_unifi_client):
        """Test getting rule that doesn't exist."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id="nonexistent")
        
        error = exc_info.value
        assert error.code == "RULE_NOT_FOUND"
        assert "nonexistent" in error.details
    
    @pytest.mark.asyncio
    async def test_rule_detail_format(self, mock_unifi_client):
        """Test that rule details contain expected fields."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule1")
        
        rule = result["data"]
        
        # Check basic fields
        expected_fields = [
            "id", "rule_index", "name", "enabled", "action", "logging",
            "protocol", "protocol_match_excepted",
            "source", "destination",
            "state_new", "state_established", "state_invalid", "state_related",
            "icmp_typename", "ipsec"
        ]
        
        for field in expected_fields:
            assert field in rule, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_rule_source_config(self, mock_unifi_client):
        """Test that source configuration is formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule1")
        
        rule = result["data"]
        assert "source" in rule
        
        source = rule["source"]
        assert "address" in source
        assert "network_id" in source
        assert "firewall_groups" in source
        assert "mac_address" in source
        assert "port" in source
        assert "address_display" in source
    
    @pytest.mark.asyncio
    async def test_rule_destination_config(self, mock_unifi_client):
        """Test that destination configuration is formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule1")
        
        rule = result["data"]
        assert "destination" in rule
        
        destination = rule["destination"]
        assert "address" in destination
        assert "network_id" in destination
        assert "firewall_groups" in destination
        assert "port" in destination
        assert "address_display" in destination
    
    @pytest.mark.asyncio
    async def test_rule_protocol_details(self, mock_unifi_client):
        """Test that protocol details are formatted correctly."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule3")
        
        rule = result["data"]
        assert "protocol" in rule
        
        protocol = rule["protocol"]
        assert "type" in protocol
        assert "display" in protocol
        assert protocol["type"] == "tcp"
        assert protocol["display"] == "TCP"
    
    @pytest.mark.asyncio
    async def test_rule_tcp_flags(self, mock_unifi_client):
        """Test that TCP flags are included for TCP rules."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule3")
        
        rule = result["data"]
        protocol = rule["protocol"]
        
        # TCP rule should have tcp_flags
        assert "tcp_flags" in protocol
        assert protocol["tcp_flags"] == ["syn"]
    
    @pytest.mark.asyncio
    async def test_rule_state_fields(self, mock_unifi_client):
        """Test that state fields are included."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        result = await tool.execute(mock_unifi_client, rule_id="rule1")
        
        rule = result["data"]
        
        # Check state fields
        assert rule["state_new"] is True
        assert rule["state_established"] is True
        assert rule["state_invalid"] is False
        assert rule["state_related"] is True
    
    @pytest.mark.asyncio
    async def test_rule_logging_field(self, mock_unifi_client):
        """Test that logging field is included."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        
        # Test rule with logging enabled
        result1 = await tool.execute(mock_unifi_client, rule_id="rule2")
        assert result1["data"]["logging"] is True
        
        # Test rule with logging disabled
        result2 = await tool.execute(mock_unifi_client, rule_id="rule1")
        assert result2["data"]["logging"] is False
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_unifi_client):
        """Test handling of API errors."""
        mock_unifi_client.get.side_effect = Exception("API connection failed")
        
        tool = GetFirewallRuleDetailsTool()
        
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(mock_unifi_client, rule_id="rule1")
        
        error = exc_info.value
        assert error.code == "API_ERROR"
        assert "Failed to retrieve firewall rule details" in error.message
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        tool = GetFirewallRuleDetailsTool()
        
        assert tool.name == "unifi_get_firewall_rule_details"
        assert tool.category == "security"
        assert tool.requires_confirmation is False
        assert "detail" in tool.description.lower()
        
        # Check input schema
        assert "properties" in tool.input_schema
        assert "rule_id" in tool.input_schema["properties"]
        assert "rule_id" in tool.input_schema["required"]
    
    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, mock_unifi_client):
        """Test that rule search is case-insensitive."""
        mock_unifi_client.get.return_value = {"data": MOCK_FIREWALL_RULES}
        
        tool = GetFirewallRuleDetailsTool()
        
        # Try with uppercase ID
        result = await tool.execute(mock_unifi_client, rule_id="RULE1")
        
        assert result["success"] is True
        assert result["data"]["id"] == "rule1"


class TestFirewallRuleFormatting:
    """Test firewall rule formatting helpers."""
    
    def test_format_protocol_all(self):
        """Test formatting 'all' protocol."""
        tool = ListFirewallRulesTool()
        
        rule = {"protocol": "all"}
        formatted = tool._format_protocol(rule)
        
        assert formatted == "ALL"
    
    def test_format_protocol_tcp_udp(self):
        """Test formatting 'tcp_udp' protocol."""
        tool = ListFirewallRulesTool()
        
        rule = {"protocol": "tcp_udp"}
        formatted = tool._format_protocol(rule)
        
        assert formatted == "TCP/UDP"
    
    def test_format_protocol_specific(self):
        """Test formatting specific protocols."""
        tool = ListFirewallRulesTool()
        
        # TCP
        rule_tcp = {"protocol": "tcp"}
        assert tool._format_protocol(rule_tcp) == "TCP"
        
        # UDP
        rule_udp = {"protocol": "udp"}
        assert tool._format_protocol(rule_udp) == "UDP"
        
        # ICMP
        rule_icmp = {"protocol": "icmp"}
        assert tool._format_protocol(rule_icmp) == "ICMP"
    
    def test_format_address_with_ip(self):
        """Test formatting address with IP."""
        tool = ListFirewallRulesTool()
        
        rule = {"src_address": "192.168.1.0/24"}
        formatted = tool._format_address(rule, "src")
        
        assert formatted == "192.168.1.0/24"
    
    def test_format_address_with_network_id(self):
        """Test formatting address with network ID."""
        tool = ListFirewallRulesTool()
        
        rule = {"src_networkconf_id": "net123"}
        formatted = tool._format_address(rule, "src")
        
        assert formatted == "network:net123"
    
    def test_format_address_with_firewall_group(self):
        """Test formatting address with firewall group."""
        tool = ListFirewallRulesTool()
        
        rule = {"src_firewallgroup_ids": ["group123"]}
        formatted = tool._format_address(rule, "src")
        
        assert formatted == "group:group123"
    
    def test_format_address_any(self):
        """Test formatting address when none specified."""
        tool = ListFirewallRulesTool()
        
        rule = {}
        formatted = tool._format_address(rule, "src")
        
        assert formatted == "any"
    
    def test_format_port_with_port(self):
        """Test formatting port with specific port."""
        tool = ListFirewallRulesTool()
        
        rule = {"dst_port": "443"}
        formatted = tool._format_port(rule)
        
        assert formatted == "443"
    
    def test_format_port_with_group(self):
        """Test formatting port with firewall group."""
        tool = ListFirewallRulesTool()
        
        rule = {"dst_firewallgroup_ids": ["portgroup123"]}
        formatted = tool._format_port(rule)
        
        assert formatted == "group:portgroup123"
    
    def test_format_port_any(self):
        """Test formatting port when none specified."""
        tool = ListFirewallRulesTool()
        
        rule = {}
        formatted = tool._format_port(rule)
        
        assert formatted == "any"


class TestInputValidation:
    """Test input validation for firewall tools."""
    
    def test_list_rules_valid_input(self):
        """Test ListFirewallRulesTool accepts valid input."""
        tool = ListFirewallRulesTool()
        
        # Should not raise
        tool.validate_input({
            "enabled_only": True,
            "page": 1,
            "page_size": 50
        })
    
    def test_list_rules_invalid_page(self):
        """Test ListFirewallRulesTool rejects invalid page number."""
        tool = ListFirewallRulesTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page": 0})  # Must be >= 1
    
    def test_list_rules_invalid_page_size(self):
        """Test ListFirewallRulesTool rejects invalid page size."""
        tool = ListFirewallRulesTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({"page_size": 1000})  # Max is 500
    
    def test_get_rule_details_valid_input(self):
        """Test GetFirewallRuleDetailsTool accepts valid input."""
        tool = GetFirewallRuleDetailsTool()
        
        # Should not raise
        tool.validate_input({"rule_id": "rule123"})
    
    def test_get_rule_details_missing_rule_id(self):
        """Test GetFirewallRuleDetailsTool requires rule_id."""
        tool = GetFirewallRuleDetailsTool()
        
        with pytest.raises(ToolError):
            tool.validate_input({})  # Missing required rule_id
