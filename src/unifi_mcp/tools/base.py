"""Base tool class for MCP tools.

This module provides the base class for all MCP tools, including:
- Abstract tool interface definition
- Input validation against JSON schema
- Output formatting helpers
- Error response formatting
- Common tool patterns and utilities

All tools should inherit from BaseTool and implement the execute method.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from jsonschema import validate, ValidationError as JsonSchemaValidationError

from ..unifi_client import UniFiClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ToolError(Exception):
    """Structured error response for tool execution failures.
    
    This exception is raised when tool validation or execution fails.
    It provides structured error information that can be formatted
    for AI agent consumption.
    
    Attributes:
        code: Error code (e.g., "VALIDATION_ERROR", "API_ERROR")
        message: Human-readable error message
        details: Additional error details
        actionable_steps: List of steps to resolve the error
    """
    code: str
    message: str
    details: Optional[str] = None
    actionable_steps: Optional[List[str]] = None
    
    def __str__(self) -> str:
        """String representation of the error.
        
        Returns:
            Error message with code
        """
        return f"[{self.code}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format.
        
        Returns:
            Dictionary representation of the error
        """
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        
        if self.details:
            result["error"]["details"] = self.details
        
        if self.actionable_steps:
            result["error"]["actionable_steps"] = self.actionable_steps
        
        return result
    
    def to_json(self) -> str:
        """Convert error to JSON string.
        
        Returns:
            JSON string representation of the error
        """
        return json.dumps(self.to_dict(), indent=2)


class BaseTool(ABC):
    """Base class for all MCP tools.
    
    This abstract class defines the interface that all tools must implement.
    It provides common functionality for:
    - Input validation against JSON schema
    - Output formatting for AI consumption
    - Error response formatting
    - Tool metadata (name, description, schema)
    
    Subclasses must implement:
    - name: Tool name (class attribute)
    - description: Tool description (class attribute)
    - input_schema: JSON schema for parameters (class attribute)
    - execute: Tool execution logic (method)
    
    Example:
        >>> class ListDevicesTool(BaseTool):
        ...     name = "unifi_list_devices"
        ...     description = "List all UniFi devices"
        ...     input_schema = {
        ...         "type": "object",
        ...         "properties": {
        ...             "device_type": {
        ...                 "type": "string",
        ...                 "enum": ["all", "switch", "ap", "gateway"]
        ...             }
        ...         }
        ...     }
        ...     
        ...     async def execute(self, unifi_client, **kwargs):
        ...         device_type = kwargs.get("device_type", "all")
        ...         devices = await unifi_client.get("/api/s/default/stat/device")
        ...         return self.format_success(devices)
    """
    
    # Tool metadata (must be defined by subclasses)
    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    requires_confirmation: bool = False
    category: str = "general"
    
    def __init__(self):
        """Initialize the tool.
        
        Validates that required class attributes are defined.
        
        Raises:
            NotImplementedError: If required attributes are not defined
        """
        if not self.name:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'name' attribute"
            )
        
        if not self.description:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'description' attribute"
            )
        
        if not self.input_schema:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'input_schema' attribute"
            )
    
    @abstractmethod
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Union[Dict[str, Any], List[Any], str]:
        """Execute the tool logic.
        
        This method must be implemented by subclasses to provide the actual
        tool functionality. It receives the UniFi client and validated parameters.
        
        Args:
            unifi_client: UniFi API client instance
            **kwargs: Tool parameters (already validated)
        
        Returns:
            Tool execution result (dict, list, or string)
        
        Raises:
            Exception: Any errors during tool execution
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute() method"
        )
    
    def validate_input(self, arguments: Dict[str, Any]) -> None:
        """Validate input arguments against the tool's JSON schema.
        
        Args:
            arguments: Input arguments to validate
        
        Raises:
            ToolError: If validation fails
        """
        try:
            validate(instance=arguments, schema=self.input_schema)
            logger.debug(
                f"Input validation successful for {self.name}",
                extra={"tool_name": self.name}
            )
        
        except JsonSchemaValidationError as e:
            logger.warning(
                f"Input validation failed for {self.name}: {e.message}",
                extra={
                    "tool_name": self.name,
                    "error": e.message,
                    "path": list(e.path) if e.path else None
                }
            )
            
            # Extract field path for better error messages
            field_path = ".".join(str(p) for p in e.path) if e.path else "root"
            
            raise ToolError(
                code="VALIDATION_ERROR",
                message=f"Invalid input for tool '{self.name}'",
                details=f"Validation error at '{field_path}': {e.message}",
                actionable_steps=[
                    f"Check the input schema for '{self.name}'",
                    "Ensure all required fields are provided",
                    "Verify field types match the schema"
                ]
            )
    
    async def invoke(
        self,
        unifi_client: UniFiClient,
        arguments: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """Invoke the tool with validation.
        
        This method handles the full tool invocation lifecycle:
        1. Validate input arguments
        2. Check confirmation requirement (for write operations)
        3. Execute the tool
        4. Log write operations with full details
        5. Format and return the result
        
        Args:
            unifi_client: UniFi API client instance
            arguments: Tool arguments
        
        Returns:
            Tool execution result or error response
        """
        try:
            # Validate input
            self.validate_input(arguments)
            
            # Check confirmation requirement for write operations
            if self.requires_confirmation:
                confirm = arguments.get("confirm", False)
                if not confirm:
                    error = ToolError(
                        code="CONFIRMATION_REQUIRED",
                        message=f"Tool '{self.name}' requires explicit confirmation",
                        details="This is a write operation that modifies network configuration",
                        actionable_steps=[
                            "Add 'confirm': true to the arguments",
                            "Review the operation details before confirming",
                            "Ensure you understand the impact of this change"
                        ]
                    )
                    logger.warning(
                        f"Write operation blocked - confirmation required: {self.name}",
                        extra={
                            "tool_name": self.name,
                            "category": self.category,
                            "requires_confirmation": True,
                            "confirmed": False
                        }
                    )
                    return error.to_dict()
                
                # Log write operation attempt with full details
                from ..utils.logging import redact_sensitive_data
                redacted_args = redact_sensitive_data(arguments)
                logger.warning(
                    f"WRITE OPERATION INITIATED: {self.name}",
                    extra={
                        "tool_name": self.name,
                        "category": self.category,
                        "operation_type": "write",
                        "confirmed": True,
                        "arguments": redacted_args
                    }
                )
            
            # Execute the tool
            logger.info(
                f"Executing tool: {self.name}",
                extra={"tool_name": self.name, "category": self.category}
            )
            
            result = await self.execute(unifi_client, **arguments)
            
            # Log successful write operation completion
            if self.requires_confirmation:
                logger.warning(
                    f"WRITE OPERATION COMPLETED: {self.name}",
                    extra={
                        "tool_name": self.name,
                        "category": self.category,
                        "operation_type": "write",
                        "status": "success"
                    }
                )
            
            logger.info(
                f"Tool execution successful: {self.name}",
                extra={"tool_name": self.name}
            )
            
            return result
        
        except ToolError as e:
            # Tool-specific error (already formatted)
            # Log write operation failure with details
            if self.requires_confirmation:
                logger.error(
                    f"WRITE OPERATION FAILED: {self.name}",
                    extra={
                        "tool_name": self.name,
                        "category": self.category,
                        "operation_type": "write",
                        "status": "failed",
                        "error_code": e.code,
                        "error_message": e.message
                    }
                )
            
            logger.warning(
                f"Tool error: {self.name}",
                extra={
                    "tool_name": self.name,
                    "error_code": e.code,
                    "error_message": e.message
                }
            )
            return e.to_dict()
        
        except Exception as e:
            # Unexpected error
            # Log write operation failure with details
            if self.requires_confirmation:
                logger.error(
                    f"WRITE OPERATION FAILED: {self.name}",
                    extra={
                        "tool_name": self.name,
                        "category": self.category,
                        "operation_type": "write",
                        "status": "failed",
                        "error": str(e)
                    },
                    exc_info=True
                )
            
            logger.error(
                f"Tool execution failed: {self.name}",
                extra={
                    "tool_name": self.name,
                    "error": str(e)
                },
                exc_info=True
            )
            
            error = ToolError(
                code="EXECUTION_ERROR",
                message=f"Tool execution failed: {self.name}",
                details=str(e),
                actionable_steps=[
                    "Check the UniFi controller is accessible",
                    "Verify your credentials are correct",
                    "Check the server logs for more details"
                ]
            )
            return error.to_dict()
    
    # Response format constants
    RESPONSE_FORMAT_DETAILED = "detailed"
    RESPONSE_FORMAT_CONCISE = "concise"
    
    # Default maximum response size (number of items before truncation)
    DEFAULT_MAX_RESPONSE_SIZE = 100
    
    # Output formatting helpers
    
    def format_success(
        self,
        data: Any,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format a successful tool result.
        
        Args:
            data: Result data
            message: Optional success message
        
        Returns:
            Formatted success response
        """
        result = {"success": True, "data": data}
        
        if message:
            result["message"] = message
        
        return result
    
    def format_list(
        self,
        items: List[Any],
        total: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Format a list result with optional pagination info.
        
        Args:
            items: List of items
            total: Total number of items (if paginated)
            page: Current page number (if paginated)
            page_size: Items per page (if paginated)
        
        Returns:
            Formatted list response
        """
        result = {
            "success": True,
            "data": items,
            "count": len(items)
        }
        
        if total is not None:
            result["total"] = total
        
        if page is not None:
            result["page"] = page
        
        if page_size is not None:
            result["page_size"] = page_size
        
        return result
    
    def format_detail(
        self,
        item: Dict[str, Any],
        item_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format a detail result for a single item.
        
        Args:
            item: Item details
            item_type: Optional type description (e.g., "device", "client")
        
        Returns:
            Formatted detail response
        """
        result = {
            "success": True,
            "data": item
        }
        
        if item_type:
            result["type"] = item_type
        
        return result
    
    def format_error(
        self,
        code: str,
        message: str,
        details: Optional[str] = None,
        actionable_steps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Format an error response.
        
        Args:
            code: Error code
            message: Error message
            details: Optional error details
            actionable_steps: Optional list of steps to resolve
        
        Returns:
            Formatted error response
        """
        error = ToolError(
            code=code,
            message=message,
            details=details,
            actionable_steps=actionable_steps
        )
        return error.to_dict()
    
    # Data transformation helpers
    
    def extract_fields(
        self,
        data: Dict[str, Any],
        fields: List[str],
        rename: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract specific fields from a data dictionary.
        
        Useful for creating summary views with only relevant fields.
        
        Args:
            data: Source data dictionary
            fields: List of field names to extract
            rename: Optional mapping of old names to new names
        
        Returns:
            Dictionary with only the specified fields
        """
        result = {}
        rename = rename or {}
        
        for field in fields:
            if field in data:
                new_name = rename.get(field, field)
                result[new_name] = data[field]
        
        return result
    
    def filter_items(
        self,
        items: List[Dict[str, Any]],
        filter_fn: Any
    ) -> List[Dict[str, Any]]:
        """Filter a list of items using a filter function.
        
        Args:
            items: List of items to filter
            filter_fn: Function that returns True for items to keep
        
        Returns:
            Filtered list of items
        """
        return [item for item in items if filter_fn(item)]
    
    def paginate(
        self,
        items: List[Any],
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Any], int]:
        """Paginate a list of items.
        
        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page
        
        Returns:
            Tuple of (paginated items, total count)
        """
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return items[start:end], total
    
    def sort_items(
        self,
        items: List[Dict[str, Any]],
        key: str,
        reverse: bool = False
    ) -> List[Dict[str, Any]]:
        """Sort a list of items by a specific key.
        
        Args:
            items: List of items to sort
            key: Dictionary key to sort by
            reverse: Sort in descending order if True
        
        Returns:
            Sorted list of items
        """
        return sorted(
            items,
            key=lambda x: x.get(key, ""),
            reverse=reverse
        )
    
    # Validation helpers
    
    def validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: List[str]
    ) -> None:
        """Validate that required fields are present in data.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
        
        Raises:
            ToolError: If any required fields are missing
        """
        missing_fields = [
            field for field in required_fields
            if field not in data or data[field] is None
        ]
        
        if missing_fields:
            raise ToolError(
                code="MISSING_FIELDS",
                message="Required fields are missing",
                details=f"Missing fields: {', '.join(missing_fields)}",
                actionable_steps=[
                    f"Provide values for: {', '.join(missing_fields)}",
                    "Check the tool documentation for required parameters"
                ]
            )
    
    def validate_enum(
        self,
        value: str,
        allowed_values: List[str],
        field_name: str
    ) -> None:
        """Validate that a value is in the allowed set.
        
        Args:
            value: Value to validate
            allowed_values: List of allowed values
            field_name: Name of the field (for error messages)
        
        Raises:
            ToolError: If value is not in allowed values
        """
        if value not in allowed_values:
            raise ToolError(
                code="INVALID_VALUE",
                message=f"Invalid value for '{field_name}'",
                details=f"Value '{value}' is not allowed",
                actionable_steps=[
                    f"Use one of: {', '.join(allowed_values)}",
                    f"Check the tool documentation for valid {field_name} values"
                ]
            )
    
    def validate_range(
        self,
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        field_name: str = "value"
    ) -> None:
        """Validate that a numeric value is within a range.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            field_name: Name of the field (for error messages)
        
        Raises:
            ToolError: If value is out of range
        """
        if min_value is not None and value < min_value:
            raise ToolError(
                code="VALUE_OUT_OF_RANGE",
                message=f"Value for '{field_name}' is too small",
                details=f"Value {value} is less than minimum {min_value}",
                actionable_steps=[
                    f"Use a value >= {min_value}",
                    f"Check the tool documentation for valid {field_name} range"
                ]
            )
        
        if max_value is not None and value > max_value:
            raise ToolError(
                code="VALUE_OUT_OF_RANGE",
                message=f"Value for '{field_name}' is too large",
                details=f"Value {value} is greater than maximum {max_value}",
                actionable_steps=[
                    f"Use a value <= {max_value}",
                    f"Check the tool documentation for valid {field_name} range"
                ]
            )
    
    # Response format helpers
    
    def apply_response_format(
        self,
        items: List[Dict[str, Any]],
        response_format: str = "detailed",
        concise_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Apply response format to a list of items.
        
        When response_format is "concise", only the specified fields are included.
        When response_format is "detailed", all fields are included.
        
        Args:
            items: List of item dictionaries
            response_format: "detailed" or "concise"
            concise_fields: Fields to include in concise format
        
        Returns:
            Formatted list of items
        """
        if response_format == self.RESPONSE_FORMAT_CONCISE and concise_fields:
            return [
                {k: v for k, v in item.items() if k in concise_fields}
                for item in items
            ]
        return items
    
    def truncate_response(
        self,
        items: List[Any],
        max_size: Optional[int] = None,
        include_guidance: bool = True
    ) -> tuple[List[Any], bool, Optional[str]]:
        """Truncate a list of items if it exceeds the maximum size.
        
        Args:
            items: List of items to potentially truncate
            max_size: Maximum number of items (defaults to DEFAULT_MAX_RESPONSE_SIZE)
            include_guidance: Whether to include guidance message when truncated
        
        Returns:
            Tuple of (truncated items, was_truncated, guidance_message)
        """
        max_size = max_size or self.DEFAULT_MAX_RESPONSE_SIZE
        
        if len(items) <= max_size:
            return items, False, None
        
        truncated_items = items[:max_size]
        guidance = None
        
        if include_guidance:
            guidance = (
                f"Response truncated to {max_size} items (total: {len(items)}). "
                f"Use pagination (page, page_size) or filtering parameters "
                f"for more targeted queries."
            )
        
        return truncated_items, True, guidance
    
    def format_list_with_truncation(
        self,
        items: List[Any],
        total: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        max_size: Optional[int] = None,
        response_format: str = "detailed",
        concise_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Format a list result with optional truncation and response format.
        
        This method combines pagination info, truncation, and response format
        into a single formatted response.
        
        Args:
            items: List of items
            total: Total number of items (if paginated)
            page: Current page number (if paginated)
            page_size: Items per page (if paginated)
            max_size: Maximum items before truncation
            response_format: "detailed" or "concise"
            concise_fields: Fields to include in concise format
        
        Returns:
            Formatted list response with truncation info if applicable
        """
        # Apply response format first
        formatted_items = self.apply_response_format(
            items, response_format, concise_fields
        )
        
        # Apply truncation
        truncated_items, was_truncated, guidance = self.truncate_response(
            formatted_items, max_size
        )
        
        result = {
            "success": True,
            "data": truncated_items,
            "count": len(truncated_items),
            "response_format": response_format
        }
        
        if total is not None:
            result["total"] = total
        
        if page is not None:
            result["page"] = page
        
        if page_size is not None:
            result["page_size"] = page_size
        
        if was_truncated:
            result["truncated"] = True
            result["truncated_from"] = len(items)
            if guidance:
                result["guidance"] = guidance
        
        return result
