"""Unit tests for tool registry.

Tests cover:
- Tool registration (single and multiple)
- Tool discovery (get all registered tools)
- Tool invocation routing by name
- Category-based organization
- Configuration-based filtering
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tool_registry import ToolRegistry, ToolDefinition
from unifi_mcp.config.loader import Config, ServerConfig, UniFiConfig, ToolsConfig


# Sample tool handlers for testing
async def sample_handler_1(unifi_client, **kwargs):
    """Sample tool handler 1."""
    return {"result": "handler_1", "args": kwargs}


async def sample_handler_2(unifi_client, **kwargs):
    """Sample tool handler 2."""
    return {"result": "handler_2", "args": kwargs}


async def sample_handler_with_confirmation(unifi_client, confirm=False, **kwargs):
    """Sample tool handler that requires confirmation."""
    if not confirm:
        raise ValueError("Confirmation required")
    return {"result": "confirmed", "args": kwargs}


@pytest.fixture
def registry():
    """Create a tool registry without configuration."""
    return ToolRegistry()


@pytest.fixture
def config_all_enabled():
    """Create a config with all tools enabled."""
    return Config(
        server=ServerConfig(),
        unifi=UniFiConfig(host="192.168.1.1"),
        tools=ToolsConfig(
            network_discovery={
                "enabled": True,
                "tools": ["list_devices", "get_device_details"]
            },
            security={
                "enabled": True,
                "tools": ["list_firewall_rules"]
            },
            statistics={
                "enabled": True,
                "tools": []  # Empty list means all tools enabled
            },
            write_operations={
                "enabled": False,
                "tools": ["toggle_firewall_rule"]
            }
        )
    )


@pytest.fixture
def config_partial_disabled():
    """Create a config with some categories disabled."""
    return Config(
        server=ServerConfig(),
        unifi=UniFiConfig(host="192.168.1.1"),
        tools=ToolsConfig(
            network_discovery={
                "enabled": True,
                "tools": ["list_devices"]  # Only list_devices enabled
            },
            security={
                "enabled": False,  # Entire category disabled
                "tools": ["list_firewall_rules"]
            },
            statistics={
                "enabled": True,
                "tools": []
            }
        )
    )


@pytest.fixture
def registry_with_config(config_all_enabled):
    """Create a tool registry with configuration."""
    return ToolRegistry(config_all_enabled)


class TestToolRegistration:
    """Tests for tool registration."""
    
    def test_register_single_tool(self, registry):
        """Test registering a single tool."""
        registry.register_tool(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="test"
        )
        
        assert registry.get_tool_count() == 1
        assert "unifi_test_tool" in registry._tools
        assert registry._tools["unifi_test_tool"].category == "test"
    
    def test_register_duplicate_tool_raises_error(self, registry):
        """Test that registering a duplicate tool raises an error."""
        registry.register_tool(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=sample_handler_1
        )
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_tool(
                name="unifi_test_tool",
                description="Duplicate tool",
                input_schema={"type": "object"},
                handler=sample_handler_2
            )
    
    def test_register_multiple_tools(self, registry):
        """Test registering multiple tools at once."""
        tools = [
            ToolDefinition(
                name="unifi_tool_1",
                description="Tool 1",
                input_schema={"type": "object"},
                handler=sample_handler_1,
                category="test"
            ),
            ToolDefinition(
                name="unifi_tool_2",
                description="Tool 2",
                input_schema={"type": "object"},
                handler=sample_handler_2,
                category="test"
            )
        ]
        
        registry.register_tools(tools)
        
        assert registry.get_tool_count() == 2
        assert "unifi_tool_1" in registry._tools
        assert "unifi_tool_2" in registry._tools
    
    def test_register_category(self, registry):
        """Test registering a category of tools."""
        tools = [
            ToolDefinition(
                name="unifi_tool_1",
                description="Tool 1",
                input_schema={"type": "object"},
                handler=sample_handler_1,
                category="old_category"  # This will be overridden
            ),
            ToolDefinition(
                name="unifi_tool_2",
                description="Tool 2",
                input_schema={"type": "object"},
                handler=sample_handler_2,
                category="old_category"
            )
        ]
        
        registry.register_category("network_discovery", tools)
        
        assert registry.get_tool_count() == 2
        # Verify category was overridden
        assert registry._tools["unifi_tool_1"].category == "network_discovery"
        assert registry._tools["unifi_tool_2"].category == "network_discovery"
        # Verify category index
        assert "network_discovery" in registry._categories
        assert len(registry._categories["network_discovery"]) == 2


class TestToolDiscovery:
    """Tests for tool discovery."""
    
    def test_get_tool_list_no_config(self, registry):
        """Test getting tool list without configuration (all enabled)."""
        registry.register_tool(
            name="unifi_tool_1",
            description="Tool 1",
            input_schema={"type": "object"},
            handler=sample_handler_1
        )
        registry.register_tool(
            name="unifi_tool_2",
            description="Tool 2",
            input_schema={"type": "object"},
            handler=sample_handler_2
        )
        
        tools = registry.get_tool_list()
        
        assert len(tools) == 2
        assert tools[0].name == "unifi_tool_1"
        assert tools[1].name == "unifi_tool_2"
    
    def test_get_tool_list_with_config(self, registry_with_config):
        """Test getting tool list with configuration filtering."""
        # Register tools in different categories
        registry_with_config.register_tool(
            name="unifi_list_devices",
            description="List devices",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="network_discovery"
        )
        registry_with_config.register_tool(
            name="unifi_get_device_details",
            description="Get device details",
            input_schema={"type": "object"},
            handler=sample_handler_2,
            category="network_discovery"
        )
        registry_with_config.register_tool(
            name="unifi_list_firewall_rules",
            description="List firewall rules",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="security"
        )
        
        tools = registry_with_config.get_tool_list()
        
        # All 3 tools should be enabled based on config
        assert len(tools) == 3
    
    def test_get_tool_list_with_disabled_category(self, config_partial_disabled):
        """Test that disabled categories are filtered out."""
        registry = ToolRegistry(config_partial_disabled)
        
        # Register tools
        registry.register_tool(
            name="unifi_list_devices",
            description="List devices",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_get_device_details",
            description="Get device details",
            input_schema={"type": "object"},
            handler=sample_handler_2,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_list_firewall_rules",
            description="List firewall rules",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="security"
        )
        
        tools = registry.get_tool_list()
        
        # Only list_devices should be enabled (get_device_details not in config list)
        # security category is disabled
        assert len(tools) == 1
        assert tools[0].name == "unifi_list_devices"
    
    def test_get_tools_by_category(self, registry):
        """Test getting tools by category."""
        registry.register_tool(
            name="unifi_tool_1",
            description="Tool 1",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_tool_2",
            description="Tool 2",
            input_schema={"type": "object"},
            handler=sample_handler_2,
            category="security"
        )
        
        network_tools = registry.get_tools_by_category("network_discovery")
        security_tools = registry.get_tools_by_category("security")
        
        assert len(network_tools) == 1
        assert network_tools[0].name == "unifi_tool_1"
        assert len(security_tools) == 1
        assert security_tools[0].name == "unifi_tool_2"
    
    def test_get_tools_by_nonexistent_category(self, registry):
        """Test getting tools from a category that doesn't exist."""
        tools = registry.get_tools_by_category("nonexistent")
        assert len(tools) == 0
    
    def test_get_categories(self, registry):
        """Test getting list of categories."""
        registry.register_tool(
            name="unifi_tool_1",
            description="Tool 1",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_tool_2",
            description="Tool 2",
            input_schema={"type": "object"},
            handler=sample_handler_2,
            category="security"
        )
        
        categories = registry.get_categories()
        
        assert len(categories) == 2
        assert "network_discovery" in categories
        assert "security" in categories
    
    def test_get_enabled_tool_count(self, config_partial_disabled):
        """Test getting count of enabled tools."""
        registry = ToolRegistry(config_partial_disabled)
        
        registry.register_tool(
            name="unifi_list_devices",
            description="List devices",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_get_device_details",
            description="Get device details",
            input_schema={"type": "object"},
            handler=sample_handler_2,
            category="network_discovery"
        )
        registry.register_tool(
            name="unifi_list_firewall_rules",
            description="List firewall rules",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="security"
        )
        
        assert registry.get_tool_count() == 3
        assert registry.get_enabled_tool_count() == 1  # Only list_devices


class TestToolInvocation:
    """Tests for tool invocation."""
    
    @pytest.mark.asyncio
    async def test_invoke_tool_success(self, registry):
        """Test successful tool invocation."""
        registry.register_tool(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=sample_handler_1
        )
        
        mock_client = MagicMock()
        result = await registry.invoke(
            "unifi_test_tool",
            mock_client,
            {"param1": "value1"}
        )
        
        assert result["result"] == "handler_1"
        assert result["args"]["param1"] == "value1"
    
    @pytest.mark.asyncio
    async def test_invoke_nonexistent_tool(self, registry):
        """Test invoking a tool that doesn't exist."""
        mock_client = MagicMock()
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await registry.invoke("unifi_nonexistent", mock_client, {})
    
    @pytest.mark.asyncio
    async def test_invoke_disabled_tool(self, config_partial_disabled):
        """Test invoking a tool that is disabled."""
        registry = ToolRegistry(config_partial_disabled)
        
        registry.register_tool(
            name="unifi_list_firewall_rules",
            description="List firewall rules",
            input_schema={"type": "object"},
            handler=sample_handler_1,
            category="security"
        )
        
        mock_client = MagicMock()
        
        with pytest.raises(ValueError, match="disabled in configuration"):
            await registry.invoke("unifi_list_firewall_rules", mock_client, {})
    
    @pytest.mark.asyncio
    async def test_invoke_tool_with_confirmation_required(self, registry):
        """Test invoking a tool that requires confirmation."""
        registry.register_tool(
            name="unifi_write_tool",
            description="Write tool",
            input_schema={"type": "object"},
            handler=sample_handler_with_confirmation,
            requires_confirmation=True
        )
        
        mock_client = MagicMock()
        
        # Without confirmation
        with pytest.raises(ValueError, match="requires explicit confirmation"):
            await registry.invoke("unifi_write_tool", mock_client, {})
        
        # With confirmation
        result = await registry.invoke(
            "unifi_write_tool",
            mock_client,
            {"confirm": True}
        )
        assert result["result"] == "confirmed"
    
    @pytest.mark.asyncio
    async def test_invoke_tool_with_invalid_arguments(self, registry):
        """Test invoking a tool with invalid arguments."""
        async def handler_with_required_param(unifi_client, required_param):
            return {"param": required_param}
        
        registry.register_tool(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=handler_with_required_param
        )
        
        mock_client = MagicMock()
        
        # Missing required parameter
        with pytest.raises(TypeError, match="Invalid arguments"):
            await registry.invoke("unifi_test_tool", mock_client, {})
    
    @pytest.mark.asyncio
    async def test_invoke_tool_handler_exception(self, registry):
        """Test handling exceptions from tool handlers."""
        async def failing_handler(unifi_client):
            raise RuntimeError("Handler failed")
        
        registry.register_tool(
            name="unifi_failing_tool",
            description="Failing tool",
            input_schema={"type": "object"},
            handler=failing_handler
        )
        
        mock_client = MagicMock()
        
        with pytest.raises(RuntimeError, match="Handler failed"):
            await registry.invoke("unifi_failing_tool", mock_client, {})


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""
    
    def test_tool_definition_to_mcp_tool(self):
        """Test converting ToolDefinition to MCP Tool."""
        tool_def = ToolDefinition(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
            handler=sample_handler_1,
            category="test"
        )
        
        mcp_tool = tool_def.to_mcp_tool()
        
        assert mcp_tool.name == "unifi_test_tool"
        assert mcp_tool.description == "Test tool"
        assert mcp_tool.inputSchema == {"type": "object", "properties": {}}


class TestRegistryUtilities:
    """Tests for registry utility methods."""
    
    def test_clear_registry(self, registry):
        """Test clearing the registry."""
        registry.register_tool(
            name="unifi_tool_1",
            description="Tool 1",
            input_schema={"type": "object"},
            handler=sample_handler_1
        )
        registry.register_tool(
            name="unifi_tool_2",
            description="Tool 2",
            input_schema={"type": "object"},
            handler=sample_handler_2
        )
        
        assert registry.get_tool_count() == 2
        
        registry.clear()
        
        assert registry.get_tool_count() == 0
        assert len(registry._categories) == 0
