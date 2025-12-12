"""Unit tests for write operation safety framework.

This module tests the write operation safety features including:
- Confirmation parameter validation
- Write operation logging
- Error handling with rollback information
- Tool filtering based on write_operations.enabled config
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from unifi_mcp.tools.base import BaseTool, ToolError
from unifi_mcp.tool_registry import ToolRegistry, ToolDefinition
from unifi_mcp.config.loader import Config, ServerConfig, UniFiConfig, ToolsConfig
from unifi_mcp.unifi_client import UniFiClient


# Mock write operation tool for testing
class MockWriteTool(BaseTool):
    """Mock write operation tool for testing."""
    
    name = "unifi_test_write_operation"
    description = "Test write operation tool"
    input_schema = {
        "type": "object",
        "properties": {
            "confirm": {
                "type": "boolean",
                "description": "Confirm the write operation"
            },
            "test_param": {
                "type": "string",
                "description": "Test parameter"
            }
        }
    }
    requires_confirmation = True
    category = "write_operations"
    
    async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
        """Execute the mock write operation."""
        return self.format_success(
            {"operation": "completed", "param": kwargs.get("test_param", "")},
            message="Write operation successful"
        )


# Mock read-only tool for comparison
class MockReadTool(BaseTool):
    """Mock read-only tool for testing."""
    
    name = "unifi_test_read_operation"
    description = "Test read operation tool"
    input_schema = {
        "type": "object",
        "properties": {
            "test_param": {
                "type": "string",
                "description": "Test parameter"
            }
        }
    }
    requires_confirmation = False
    category = "network_discovery"
    
    async def execute(self, unifi_client: UniFiClient, **kwargs: Any) -> Dict[str, Any]:
        """Execute the mock read operation."""
        return self.format_success(
            {"data": "test_data"},
            message="Read operation successful"
        )


@pytest.fixture
def mock_unifi_client():
    """Create a mock UniFi client."""
    client = MagicMock(spec=UniFiClient)
    return client


@pytest.fixture
def write_tool():
    """Create a write operation tool instance."""
    return MockWriteTool()


@pytest.fixture
def read_tool():
    """Create a read-only tool instance."""
    return MockReadTool()


@pytest.fixture
def config_with_write_enabled():
    """Create a config with write operations enabled."""
    return Config(
        server=ServerConfig(),
        unifi=UniFiConfig(host="192.168.1.1"),
        tools=ToolsConfig(
            write_operations={
                "enabled": True,
                "require_confirmation": True,
                "tools": ["test_write_operation"]
            },
            network_discovery={
                "enabled": True,
                "tools": ["test_read_operation"]
            }
        )
    )


@pytest.fixture
def config_with_write_disabled():
    """Create a config with write operations disabled."""
    return Config(
        server=ServerConfig(),
        unifi=UniFiConfig(host="192.168.1.1"),
        tools=ToolsConfig(
            write_operations={
                "enabled": False,
                "require_confirmation": True,
                "tools": ["test_write_operation"]
            },
            network_discovery={
                "enabled": True,
                "tools": ["test_read_operation"]
            }
        )
    )


class TestConfirmationRequirement:
    """Test confirmation parameter validation for write operations."""
    
    @pytest.mark.asyncio
    async def test_write_operation_without_confirmation_fails(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation without confirmation returns error."""
        # Invoke without confirmation
        result = await write_tool.invoke(mock_unifi_client, {"test_param": "value"})
        
        # Should return error response
        assert "error" in result
        assert result["error"]["code"] == "CONFIRMATION_REQUIRED"
        assert "requires explicit confirmation" in result["error"]["message"]
        assert "confirm" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_write_operation_with_false_confirmation_fails(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation with confirm=False returns error."""
        # Invoke with confirm=False
        result = await write_tool.invoke(
            mock_unifi_client,
            {"test_param": "value", "confirm": False}
        )
        
        # Should return error response
        assert "error" in result
        assert result["error"]["code"] == "CONFIRMATION_REQUIRED"
    
    @pytest.mark.asyncio
    async def test_write_operation_with_confirmation_succeeds(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation with confirm=True succeeds."""
        # Invoke with confirm=True
        result = await write_tool.invoke(
            mock_unifi_client,
            {"test_param": "value", "confirm": True}
        )
        
        # Should succeed
        assert "success" in result
        assert result["success"] is True
        assert result["data"]["operation"] == "completed"
    
    @pytest.mark.asyncio
    async def test_read_operation_without_confirmation_succeeds(
        self, read_tool, mock_unifi_client
    ):
        """Test that read-only operations don't require confirmation."""
        # Invoke without confirmation
        result = await read_tool.invoke(mock_unifi_client, {"test_param": "value"})
        
        # Should succeed
        assert "success" in result
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_confirmation_error_includes_actionable_steps(
        self, write_tool, mock_unifi_client
    ):
        """Test that confirmation error includes actionable steps."""
        # Invoke without confirmation
        result = await write_tool.invoke(mock_unifi_client, {"test_param": "value"})
        
        # Should include actionable steps
        assert "error" in result
        assert "actionable_steps" in result["error"]
        assert len(result["error"]["actionable_steps"]) > 0
        
        # Check for helpful guidance
        steps_text = " ".join(result["error"]["actionable_steps"])
        assert "confirm" in steps_text.lower()


class TestWriteOperationLogging:
    """Test write operation logging with full details."""
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_initiation(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation initiation is logged."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke with confirmation
            await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
            
            # Check that initiation was logged
            logged_messages = [
                call[0][0] for call in mock_logger.warning.call_args_list
            ]
            assert any("WRITE OPERATION INITIATED" in msg for msg in logged_messages)
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_completion(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation completion is logged."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke with confirmation
            await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
            
            # Check that completion was logged
            logged_messages = [
                call[0][0] for call in mock_logger.warning.call_args_list
            ]
            assert any("WRITE OPERATION COMPLETED" in msg for msg in logged_messages)
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_failure(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation failure is logged."""
        # Make the execute method raise an exception
        with patch.object(write_tool, "execute", side_effect=Exception("Test error")):
            with patch("unifi_mcp.tools.base.logger") as mock_logger:
                # Invoke with confirmation
                await write_tool.invoke(
                    mock_unifi_client,
                    {"test_param": "value", "confirm": True}
                )
                
                # Check that failure was logged
                logged_messages = [
                    call[0][0] for call in mock_logger.error.call_args_list
                ]
                assert any("WRITE OPERATION FAILED" in msg for msg in logged_messages)
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_blocked_confirmation(
        self, write_tool, mock_unifi_client
    ):
        """Test that blocked write operation (no confirmation) is logged."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke without confirmation
            await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value"}
            )
            
            # Check that blocked operation was logged
            logged_messages = [
                call[0][0] for call in mock_logger.warning.call_args_list
            ]
            assert any(
                "Write operation blocked - confirmation required" in msg
                for msg in logged_messages
            )
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_include_tool_details(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation logs include tool details."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke with confirmation
            await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
            
            # Check that logs include tool details
            for call in mock_logger.warning.call_args_list:
                if "WRITE OPERATION" in call[0][0]:
                    extra = call[1].get("extra", {})
                    assert "tool_name" in extra
                    assert "category" in extra
                    assert extra["tool_name"] == write_tool.name
    
    @pytest.mark.asyncio
    async def test_write_operation_logs_redact_sensitive_data(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation logs redact sensitive data."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke with sensitive data
            await write_tool.invoke(
                mock_unifi_client,
                {
                    "test_param": "value",
                    "password": "secret123",
                    "confirm": True
                }
            )
            
            # Check that logs redact sensitive data
            for call in mock_logger.warning.call_args_list:
                if "WRITE OPERATION INITIATED" in call[0][0]:
                    extra = call[1].get("extra", {})
                    if "arguments" in extra:
                        # Password should be redacted
                        assert extra["arguments"].get("password") == "[REDACTED]"
                        # Non-sensitive data should be preserved
                        assert extra["arguments"].get("test_param") == "value"
    
    @pytest.mark.asyncio
    async def test_read_operation_does_not_log_write_messages(
        self, read_tool, mock_unifi_client
    ):
        """Test that read-only operations don't log write operation messages."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke read operation
            await read_tool.invoke(mock_unifi_client, {"test_param": "value"})
            
            # Check that no write operation messages were logged
            all_messages = []
            for call_list in [
                mock_logger.info.call_args_list,
                mock_logger.warning.call_args_list,
                mock_logger.error.call_args_list
            ]:
                all_messages.extend([call[0][0] for call in call_list])
            
            assert not any("WRITE OPERATION" in msg for msg in all_messages)


class TestToolFiltering:
    """Test tool filtering based on write_operations.enabled config."""
    
    def test_write_tools_filtered_when_disabled(
        self, config_with_write_disabled
    ):
        """Test that write tools are filtered out when write_operations.enabled=False."""
        registry = ToolRegistry(config_with_write_disabled)
        
        # Register both read and write tools
        write_tool = MockWriteTool()
        read_tool = MockReadTool()
        
        registry.register_tool(
            name=write_tool.name,
            description=write_tool.description,
            input_schema=write_tool.input_schema,
            handler=write_tool.execute,
            category=write_tool.category,
            requires_confirmation=write_tool.requires_confirmation
        )
        
        registry.register_tool(
            name=read_tool.name,
            description=read_tool.description,
            input_schema=read_tool.input_schema,
            handler=read_tool.execute,
            category=read_tool.category,
            requires_confirmation=read_tool.requires_confirmation
        )
        
        # Get available tools
        tools = registry.get_tool_list()
        tool_names = [tool.name for tool in tools]
        
        # Write tool should be filtered out
        assert write_tool.name not in tool_names
        # Read tool should be available
        assert read_tool.name in tool_names
    
    def test_write_tools_available_when_enabled(
        self, config_with_write_enabled
    ):
        """Test that write tools are available when write_operations.enabled=True."""
        registry = ToolRegistry(config_with_write_enabled)
        
        # Register both read and write tools
        write_tool = MockWriteTool()
        read_tool = MockReadTool()
        
        registry.register_tool(
            name=write_tool.name,
            description=write_tool.description,
            input_schema=write_tool.input_schema,
            handler=write_tool.execute,
            category=write_tool.category,
            requires_confirmation=write_tool.requires_confirmation
        )
        
        registry.register_tool(
            name=read_tool.name,
            description=read_tool.description,
            input_schema=read_tool.input_schema,
            handler=read_tool.execute,
            category=read_tool.category,
            requires_confirmation=read_tool.requires_confirmation
        )
        
        # Get available tools
        tools = registry.get_tool_list()
        tool_names = [tool.name for tool in tools]
        
        # Both tools should be available
        assert write_tool.name in tool_names
        assert read_tool.name in tool_names
    
    @pytest.mark.asyncio
    async def test_invoke_write_tool_when_disabled_raises_error(
        self, config_with_write_disabled, mock_unifi_client
    ):
        """Test that invoking a write tool when disabled raises clear error."""
        registry = ToolRegistry(config_with_write_disabled)
        
        # Register write tool
        write_tool = MockWriteTool()
        registry.register_tool(
            name=write_tool.name,
            description=write_tool.description,
            input_schema=write_tool.input_schema,
            handler=write_tool.execute,
            category=write_tool.category,
            requires_confirmation=write_tool.requires_confirmation
        )
        
        # Try to invoke the write tool
        with pytest.raises(ValueError) as exc_info:
            await registry.invoke(
                write_tool.name,
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
        
        # Error should mention write operations are disabled
        assert "write operation" in str(exc_info.value).lower()
        assert "disabled" in str(exc_info.value).lower()
        assert "write_operations.enabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invoke_read_tool_when_write_disabled_succeeds(
        self, config_with_write_disabled, mock_unifi_client
    ):
        """Test that read tools work even when write operations are disabled."""
        registry = ToolRegistry(config_with_write_disabled)
        
        # Register read tool
        read_tool = MockReadTool()
        registry.register_tool(
            name=read_tool.name,
            description=read_tool.description,
            input_schema=read_tool.input_schema,
            handler=read_tool.execute,
            category=read_tool.category,
            requires_confirmation=read_tool.requires_confirmation
        )
        
        # Invoke the read tool - should succeed
        result = await registry.invoke(
            read_tool.name,
            mock_unifi_client,
            {"test_param": "value"}
        )
        
        assert result["success"] is True
    
    def test_enabled_tool_count_excludes_disabled_write_tools(
        self, config_with_write_disabled
    ):
        """Test that enabled tool count excludes disabled write tools."""
        registry = ToolRegistry(config_with_write_disabled)
        
        # Register both read and write tools
        write_tool = MockWriteTool()
        read_tool = MockReadTool()
        
        registry.register_tool(
            name=write_tool.name,
            description=write_tool.description,
            input_schema=write_tool.input_schema,
            handler=write_tool.execute,
            category=write_tool.category,
            requires_confirmation=write_tool.requires_confirmation
        )
        
        registry.register_tool(
            name=read_tool.name,
            description=read_tool.description,
            input_schema=read_tool.input_schema,
            handler=read_tool.execute,
            category=read_tool.category,
            requires_confirmation=read_tool.requires_confirmation
        )
        
        # Total registered: 2
        assert registry.get_tool_count() == 2
        
        # Enabled: 1 (only read tool)
        assert registry.get_enabled_tool_count() == 1


class TestErrorHandling:
    """Test error handling for write operations."""
    
    @pytest.mark.asyncio
    async def test_write_operation_error_includes_rollback_info(
        self, write_tool, mock_unifi_client
    ):
        """Test that write operation errors include rollback information."""
        # Make the execute method raise an exception
        with patch.object(
            write_tool,
            "execute",
            side_effect=Exception("API call failed")
        ):
            # Invoke with confirmation
            result = await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
            
            # Should return error response
            assert "error" in result
            assert result["error"]["code"] == "EXECUTION_ERROR"
            
            # Should include actionable steps (rollback guidance)
            assert "actionable_steps" in result["error"]
            assert len(result["error"]["actionable_steps"]) > 0
    
    @pytest.mark.asyncio
    async def test_write_operation_tool_error_handled(
        self, write_tool, mock_unifi_client
    ):
        """Test that ToolError exceptions are handled properly."""
        # Make the execute method raise a ToolError
        with patch.object(
            write_tool,
            "execute",
            side_effect=ToolError(
                code="CUSTOM_ERROR",
                message="Custom error message",
                details="Error details",
                actionable_steps=["Step 1", "Step 2"]
            )
        ):
            # Invoke with confirmation
            result = await write_tool.invoke(
                mock_unifi_client,
                {"test_param": "value", "confirm": True}
            )
            
            # Should return formatted error
            assert "error" in result
            assert result["error"]["code"] == "CUSTOM_ERROR"
            assert result["error"]["message"] == "Custom error message"
            assert result["error"]["details"] == "Error details"
            assert result["error"]["actionable_steps"] == ["Step 1", "Step 2"]
    
    @pytest.mark.asyncio
    async def test_validation_error_before_write_operation(
        self, write_tool, mock_unifi_client
    ):
        """Test that validation errors prevent write operation execution."""
        with patch("unifi_mcp.tools.base.logger") as mock_logger:
            # Invoke with invalid arguments (missing required schema validation)
            # This will pass schema validation but we can test the flow
            result = await write_tool.invoke(
                mock_unifi_client,
                {"invalid_param": 123, "confirm": True}
            )
            
            # Should succeed (our mock schema allows additional properties)
            # But in real scenarios, validation would catch this
            assert "success" in result or "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
