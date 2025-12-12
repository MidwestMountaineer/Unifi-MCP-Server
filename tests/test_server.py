"""Tests for MCP server implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import Config, ServerConfig, UniFiConfig, ToolsConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        server=ServerConfig(
            name="test-unifi-mcp",
            log_level="DEBUG",
            diagnostics={},
            performance={},
            logging={},
        ),
        unifi=UniFiConfig(
            host="192.168.1.1",
            port=443,
            username="test",
            password="test",
            site="default",
            verify_ssl=False,
            retry={},
        ),
        tools=ToolsConfig(
            network_discovery={"enabled": True},
            security={"enabled": True},
            statistics={"enabled": True},
            migration={"enabled": True},
            write_operations={"enabled": False},
        ),
    )


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    with patch("unifi_mcp.server.UniFiClient") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


class TestUniFiMCPServer:
    """Tests for UniFiMCPServer class."""
    
    def test_server_initialization(self, mock_config, mock_unifi_client):
        """Test server initializes correctly."""
        server = UniFiMCPServer(mock_config)
        
        assert server.config == mock_config
        assert server.server is not None
        assert server.tool_registry is not None
        assert server.tool_registry.get_tool_count() == 0
    
    def test_register_tool(self, mock_config, mock_unifi_client):
        """Test tool registration."""
        server = UniFiMCPServer(mock_config)
        
        async def test_handler(client, **kwargs):
            return "test result"
        
        server.register_tool(
            name="unifi_test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=test_handler,
        )
        
        assert server.tool_registry.get_tool_count() == 1
        assert "unifi_test_tool" in server.tool_registry._tools
    
    def test_get_available_tools_empty(self, mock_config, mock_unifi_client):
        """Test getting available tools when none are registered."""
        server = UniFiMCPServer(mock_config)
        tools = server.tool_registry.get_tool_list()
        
        assert tools == []
    
    @pytest.mark.asyncio
    async def test_connect(self, mock_config, mock_unifi_client):
        """Test connecting to UniFi controller."""
        server = UniFiMCPServer(mock_config)
        
        await server.connect()
        
        mock_unifi_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_config, mock_unifi_client):
        """Test connection failure handling."""
        server = UniFiMCPServer(mock_config)
        mock_unifi_client.connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await server.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_config, mock_unifi_client):
        """Test disconnecting from UniFi controller."""
        server = UniFiMCPServer(mock_config)
        
        await server.disconnect()
        
        mock_unifi_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_error(self, mock_config, mock_unifi_client):
        """Test disconnect handles errors gracefully."""
        server = UniFiMCPServer(mock_config)
        mock_unifi_client.disconnect.side_effect = Exception("Disconnect error")
        
        # Should not raise exception
        await server.disconnect()
        
        mock_unifi_client.disconnect.assert_called_once()


class TestMCPProtocolHandlers:
    """Tests for MCP protocol handlers."""
    
    @pytest.mark.asyncio
    async def test_list_tools_handler(self, mock_config, mock_unifi_client):
        """Test tools/list handler returns empty list initially."""
        server = UniFiMCPServer(mock_config)
        
        # Get the list_tools handler
        # The handler is registered via decorator, so we test via tool_registry
        tools = server.tool_registry.get_tool_list()
        
        assert isinstance(tools, list)
        assert len(tools) == 0
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, mock_config, mock_unifi_client):
        """Test calling an unknown tool returns error."""
        server = UniFiMCPServer(mock_config)
        
        # Test that invoking an unknown tool raises ValueError
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.tool_registry.invoke("unknown_tool", mock_unifi_client, {})
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_config, mock_unifi_client):
        """Test successful tool invocation."""
        server = UniFiMCPServer(mock_config)
        
        # Register a test tool
        async def test_handler(client, test_param=None):
            return f"Result: {test_param}"
        
        server.register_tool(
            name="unifi_test",
            description="Test",
            input_schema={"type": "object"},
            handler=test_handler,
        )
        
        # Test that the handler is registered
        assert server.tool_registry.get_tool_count() == 1
        
        # Test calling the handler via registry
        result = await server.tool_registry.invoke(
            "unifi_test",
            mock_unifi_client,
            {"test_param": "value"}
        )
        assert result == "Result: value"
    
    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_arguments(self, mock_config, mock_unifi_client):
        """Test tool invocation with invalid arguments."""
        server = UniFiMCPServer(mock_config)
        
        # Register a test tool that requires specific arguments
        async def test_handler(client, required_param):
            return f"Result: {required_param}"
        
        server.register_tool(
            name="unifi_test",
            description="Test",
            input_schema={"type": "object"},
            handler=test_handler,
        )
        
        # Test that calling without required param raises TypeError
        with pytest.raises(TypeError):
            await server.tool_registry.invoke("unifi_test", mock_unifi_client, {})


class TestServerLifecycle:
    """Tests for server lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_server_initialization_sequence(self, mock_config, mock_unifi_client):
        """Test the server initialization sequence."""
        server = UniFiMCPServer(mock_config)
        
        # Verify initial state
        assert server.config == mock_config
        assert server.server is not None
        assert server.tool_registry.get_tool_count() == 0
        
        # Verify handlers are registered
        # The handlers are registered in _register_handlers() which is called in __init__
        # We can't easily test the decorated handlers, but we can verify the server object exists
        assert hasattr(server.server, 'list_tools')
        assert hasattr(server.server, 'call_tool')
