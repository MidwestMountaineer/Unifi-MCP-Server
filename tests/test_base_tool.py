"""Unit tests for BaseTool class.

Tests cover:
- Tool initialization and validation
- Input validation against JSON schema
- Output formatting helpers
- Error response formatting
- Data transformation helpers
- Validation helpers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.base import BaseTool, ToolError
from unifi_mcp.unifi_client import UniFiClient


# Test tool implementations

class ValidTool(BaseTool):
    """Valid tool implementation for testing."""
    name = "test_valid_tool"
    description = "A valid test tool"
    input_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    }
    
    async def execute(self, unifi_client, **kwargs):
        return self.format_success({"result": "success"})


class WriteOperationTool(BaseTool):
    """Tool that requires confirmation."""
    name = "test_write_tool"
    description = "A write operation tool"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "confirm": {"type": "boolean"}
        },
        "required": ["action"]
    }
    requires_confirmation = True
    
    async def execute(self, unifi_client, **kwargs):
        return self.format_success({"action": kwargs["action"]})


class TestToolInitialization:
    """Test tool initialization and validation."""
    
    def test_valid_tool_initialization(self):
        """Test that a valid tool can be initialized."""
        tool = ValidTool()
        assert tool.name == "test_valid_tool"
        assert tool.description == "A valid test tool"
        assert tool.input_schema is not None
    
    def test_missing_name_raises_error(self):
        """Test that missing name raises NotImplementedError."""
        class InvalidTool(BaseTool):
            description = "Test"
            input_schema = {}
            async def execute(self, unifi_client, **kwargs):
                pass
        
        with pytest.raises(NotImplementedError, match="must define 'name'"):
            InvalidTool()
    
    def test_missing_description_raises_error(self):
        """Test that missing description raises NotImplementedError."""
        class InvalidTool(BaseTool):
            name = "test"
            input_schema = {}
            async def execute(self, unifi_client, **kwargs):
                pass
        
        with pytest.raises(NotImplementedError, match="must define 'description'"):
            InvalidTool()
    
    def test_missing_input_schema_raises_error(self):
        """Test that missing input_schema raises NotImplementedError."""
        class InvalidTool(BaseTool):
            name = "test"
            description = "Test"
            async def execute(self, unifi_client, **kwargs):
                pass
        
        with pytest.raises(NotImplementedError, match="must define 'input_schema'"):
            InvalidTool()
    
    def test_missing_execute_raises_error(self):
        """Test that missing execute method raises TypeError."""
        class InvalidTool(BaseTool):
            name = "test"
            description = "Test"
            input_schema = {}
        
        # Python's ABC raises TypeError when trying to instantiate
        # an abstract class without implementing abstract methods
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            InvalidTool()


class TestInputValidation:
    """Test input validation against JSON schema."""
    
    def test_valid_input_passes_validation(self):
        """Test that valid input passes validation."""
        tool = ValidTool()
        arguments = {"param1": "value1", "param2": 42}
        
        # Should not raise any exception
        tool.validate_input(arguments)
    
    def test_missing_required_field_raises_error(self):
        """Test that missing required field raises ToolError."""
        tool = ValidTool()
        arguments = {"param2": 42}  # Missing required param1
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_input(arguments)
        
        error = exc_info.value
        assert error.code == "VALIDATION_ERROR"
        assert "param1" in error.details or "required" in error.details.lower()
    
    def test_wrong_type_raises_error(self):
        """Test that wrong type raises ToolError."""
        tool = ValidTool()
        arguments = {"param1": "value1", "param2": "not_an_integer"}
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_input(arguments)
        
        error = exc_info.value
        assert error.code == "VALIDATION_ERROR"
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed by default."""
        tool = ValidTool()
        arguments = {
            "param1": "value1",
            "param2": 42,
            "extra_field": "extra_value"
        }
        
        # Should not raise any exception
        tool.validate_input(arguments)


@pytest.mark.asyncio
class TestToolInvocation:
    """Test tool invocation with validation."""
    
    async def test_successful_invocation(self):
        """Test successful tool invocation."""
        tool = ValidTool()
        unifi_client = MagicMock(spec=UniFiClient)
        arguments = {"param1": "value1"}
        
        result = await tool.invoke(unifi_client, arguments)
        
        assert result["success"] is True
        assert "data" in result
    
    async def test_invocation_with_invalid_input(self):
        """Test invocation with invalid input returns error."""
        tool = ValidTool()
        unifi_client = MagicMock(spec=UniFiClient)
        arguments = {}  # Missing required param1
        
        result = await tool.invoke(unifi_client, arguments)
        
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    async def test_write_operation_without_confirmation(self):
        """Test write operation without confirmation returns error."""
        tool = WriteOperationTool()
        unifi_client = MagicMock(spec=UniFiClient)
        arguments = {"action": "delete"}
        
        result = await tool.invoke(unifi_client, arguments)
        
        assert "error" in result
        assert result["error"]["code"] == "CONFIRMATION_REQUIRED"
    
    async def test_write_operation_with_confirmation(self):
        """Test write operation with confirmation succeeds."""
        tool = WriteOperationTool()
        unifi_client = MagicMock(spec=UniFiClient)
        arguments = {"action": "delete", "confirm": True}
        
        result = await tool.invoke(unifi_client, arguments)
        
        assert result["success"] is True
        assert result["data"]["action"] == "delete"
    
    async def test_invocation_with_execution_error(self):
        """Test invocation with execution error returns formatted error."""
        class ErrorTool(BaseTool):
            name = "test_error_tool"
            description = "Tool that raises error"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                raise Exception("Test error")
        
        tool = ErrorTool()
        unifi_client = MagicMock(spec=UniFiClient)
        arguments = {}
        
        result = await tool.invoke(unifi_client, arguments)
        
        assert "error" in result
        assert result["error"]["code"] == "EXECUTION_ERROR"
        assert "Test error" in result["error"]["details"]


class TestOutputFormatting:
    """Test output formatting helpers."""
    
    def test_format_success(self):
        """Test format_success helper."""
        tool = ValidTool()
        data = {"key": "value"}
        
        result = tool.format_success(data)
        
        assert result["success"] is True
        assert result["data"] == data
    
    def test_format_success_with_message(self):
        """Test format_success with message."""
        tool = ValidTool()
        data = {"key": "value"}
        message = "Operation completed"
        
        result = tool.format_success(data, message)
        
        assert result["success"] is True
        assert result["data"] == data
        assert result["message"] == message
    
    def test_format_list(self):
        """Test format_list helper."""
        tool = ValidTool()
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        result = tool.format_list(items)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["count"] == 3
    
    def test_format_list_with_pagination(self):
        """Test format_list with pagination info."""
        tool = ValidTool()
        items = [{"id": 1}, {"id": 2}]
        
        result = tool.format_list(items, total=10, page=1, page_size=2)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 2
    
    def test_format_detail(self):
        """Test format_detail helper."""
        tool = ValidTool()
        item = {"id": 1, "name": "Test"}
        
        result = tool.format_detail(item)
        
        assert result["success"] is True
        assert result["data"] == item
    
    def test_format_detail_with_type(self):
        """Test format_detail with type."""
        tool = ValidTool()
        item = {"id": 1, "name": "Test"}
        
        result = tool.format_detail(item, item_type="device")
        
        assert result["success"] is True
        assert result["data"] == item
        assert result["type"] == "device"
    
    def test_format_error(self):
        """Test format_error helper."""
        tool = ValidTool()
        
        result = tool.format_error(
            code="TEST_ERROR",
            message="Test error message",
            details="Error details",
            actionable_steps=["Step 1", "Step 2"]
        )
        
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test error message"
        assert result["error"]["details"] == "Error details"
        assert result["error"]["actionable_steps"] == ["Step 1", "Step 2"]


class TestDataTransformationHelpers:
    """Test data transformation helpers."""
    
    def test_extract_fields(self):
        """Test extract_fields helper."""
        tool = ValidTool()
        data = {"id": 1, "name": "Test", "extra": "value"}
        fields = ["id", "name"]
        
        result = tool.extract_fields(data, fields)
        
        assert result == {"id": 1, "name": "Test"}
        assert "extra" not in result
    
    def test_extract_fields_with_rename(self):
        """Test extract_fields with rename mapping."""
        tool = ValidTool()
        data = {"id": 1, "name": "Test"}
        fields = ["id", "name"]
        rename = {"id": "device_id", "name": "device_name"}
        
        result = tool.extract_fields(data, fields, rename)
        
        assert result == {"device_id": 1, "device_name": "Test"}
    
    def test_filter_items(self):
        """Test filter_items helper."""
        tool = ValidTool()
        items = [
            {"id": 1, "active": True},
            {"id": 2, "active": False},
            {"id": 3, "active": True}
        ]
        
        result = tool.filter_items(items, lambda x: x["active"])
        
        assert len(result) == 2
        assert all(item["active"] for item in result)
    
    def test_paginate(self):
        """Test paginate helper."""
        tool = ValidTool()
        items = list(range(100))
        
        page_items, total = tool.paginate(items, page=2, page_size=10)
        
        assert len(page_items) == 10
        assert page_items[0] == 10
        assert page_items[-1] == 19
        assert total == 100
    
    def test_paginate_last_page(self):
        """Test paginate on last page with partial results."""
        tool = ValidTool()
        items = list(range(25))
        
        page_items, total = tool.paginate(items, page=3, page_size=10)
        
        assert len(page_items) == 5
        assert total == 25
    
    def test_sort_items(self):
        """Test sort_items helper."""
        tool = ValidTool()
        items = [
            {"id": 3, "name": "C"},
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"}
        ]
        
        result = tool.sort_items(items, key="id")
        
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[2]["id"] == 3
    
    def test_sort_items_reverse(self):
        """Test sort_items in reverse order."""
        tool = ValidTool()
        items = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
            {"id": 3, "name": "C"}
        ]
        
        result = tool.sort_items(items, key="id", reverse=True)
        
        assert result[0]["id"] == 3
        assert result[1]["id"] == 2
        assert result[2]["id"] == 1


class TestValidationHelpers:
    """Test validation helpers."""
    
    def test_validate_required_fields_success(self):
        """Test validate_required_fields with all fields present."""
        tool = ValidTool()
        data = {"field1": "value1", "field2": "value2"}
        required_fields = ["field1", "field2"]
        
        # Should not raise any exception
        tool.validate_required_fields(data, required_fields)
    
    def test_validate_required_fields_missing(self):
        """Test validate_required_fields with missing fields."""
        tool = ValidTool()
        data = {"field1": "value1"}
        required_fields = ["field1", "field2", "field3"]
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_required_fields(data, required_fields)
        
        error = exc_info.value
        assert error.code == "MISSING_FIELDS"
        assert "field2" in error.details
        assert "field3" in error.details
    
    def test_validate_enum_success(self):
        """Test validate_enum with valid value."""
        tool = ValidTool()
        
        # Should not raise any exception
        tool.validate_enum("option1", ["option1", "option2"], "test_field")
    
    def test_validate_enum_invalid(self):
        """Test validate_enum with invalid value."""
        tool = ValidTool()
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_enum("invalid", ["option1", "option2"], "test_field")
        
        error = exc_info.value
        assert error.code == "INVALID_VALUE"
        assert "test_field" in error.message
    
    def test_validate_range_success(self):
        """Test validate_range with value in range."""
        tool = ValidTool()
        
        # Should not raise any exception
        tool.validate_range(50, min_value=0, max_value=100, field_name="test")
    
    def test_validate_range_too_small(self):
        """Test validate_range with value too small."""
        tool = ValidTool()
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_range(-5, min_value=0, max_value=100, field_name="test")
        
        error = exc_info.value
        assert error.code == "VALUE_OUT_OF_RANGE"
        assert "too small" in error.message
    
    def test_validate_range_too_large(self):
        """Test validate_range with value too large."""
        tool = ValidTool()
        
        with pytest.raises(ToolError) as exc_info:
            tool.validate_range(150, min_value=0, max_value=100, field_name="test")
        
        error = exc_info.value
        assert error.code == "VALUE_OUT_OF_RANGE"
        assert "too large" in error.message
    
    def test_validate_range_min_only(self):
        """Test validate_range with only minimum value."""
        tool = ValidTool()
        
        # Should not raise any exception
        tool.validate_range(50, min_value=0, field_name="test")
    
    def test_validate_range_max_only(self):
        """Test validate_range with only maximum value."""
        tool = ValidTool()
        
        # Should not raise any exception
        tool.validate_range(50, max_value=100, field_name="test")


class TestToolError:
    """Test ToolError class."""
    
    def test_tool_error_to_dict(self):
        """Test ToolError to_dict method."""
        error = ToolError(
            code="TEST_ERROR",
            message="Test message",
            details="Test details",
            actionable_steps=["Step 1", "Step 2"]
        )
        
        result = error.to_dict()
        
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test message"
        assert result["error"]["details"] == "Test details"
        assert result["error"]["actionable_steps"] == ["Step 1", "Step 2"]
    
    def test_tool_error_to_dict_minimal(self):
        """Test ToolError to_dict with minimal fields."""
        error = ToolError(
            code="TEST_ERROR",
            message="Test message"
        )
        
        result = error.to_dict()
        
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test message"
        assert "details" not in result["error"]
        assert "actionable_steps" not in result["error"]
    
    def test_tool_error_to_json(self):
        """Test ToolError to_json method."""
        error = ToolError(
            code="TEST_ERROR",
            message="Test message"
        )
        
        result = error.to_json()
        
        assert isinstance(result, str)
        assert "TEST_ERROR" in result
        assert "Test message" in result
