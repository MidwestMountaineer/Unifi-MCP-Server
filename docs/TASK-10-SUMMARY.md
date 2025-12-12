# Task 10: Base Tool Class and Validation - Implementation Summary

## Overview

Implemented the base tool class (`BaseTool`) that provides the foundation for all MCP tools in the UniFi MCP Server. This abstract base class defines the standard interface, validation, and helper methods that all tools will inherit.

## Files Created

### 1. `src/unifi_mcp/tools/base.py`
**Purpose**: Core base tool class and error handling

**Key Components**:

#### `ToolError` Exception Class
- Inherits from `Exception` for proper Python exception handling
- Structured error response with:
  - `code`: Error code (e.g., "VALIDATION_ERROR", "API_ERROR")
  - `message`: Human-readable error message
  - `details`: Additional error details
  - `actionable_steps`: List of steps to resolve the error
- Methods:
  - `to_dict()`: Convert to dictionary format for JSON responses
  - `to_json()`: Convert to JSON string
  - `__str__()`: String representation for logging

#### `BaseTool` Abstract Base Class
- Abstract base class that all tools must inherit from
- Enforces implementation of required attributes and methods
- Provides comprehensive validation and formatting utilities

**Required Attributes** (must be defined by subclasses):
- `name`: Tool name (should be prefixed with "unifi_")
- `description`: Tool description for AI agents (<200 chars)
- `input_schema`: JSON schema for parameter validation
- `requires_confirmation`: Boolean for write operations (default: False)
- `category`: Tool category (default: "general")

**Required Methods** (must be implemented by subclasses):
- `execute(unifi_client, **kwargs)`: Tool execution logic

**Provided Methods**:

1. **Input Validation**:
   - `validate_input(arguments)`: Validates arguments against JSON schema
   - Raises `ToolError` with detailed error messages on validation failure

2. **Tool Invocation**:
   - `invoke(unifi_client, arguments)`: Full invocation lifecycle
     - Validates input
     - Checks confirmation requirement for write operations
     - Executes the tool
     - Handles errors and formats responses

3. **Output Formatting Helpers**:
   - `format_success(data, message)`: Format successful results
   - `format_list(items, total, page, page_size)`: Format list results with pagination
   - `format_detail(item, item_type)`: Format single item details
   - `format_error(code, message, details, actionable_steps)`: Format error responses

4. **Data Transformation Helpers**:
   - `extract_fields(data, fields, rename)`: Extract specific fields from data
   - `filter_items(items, filter_fn)`: Filter list of items
   - `paginate(items, page, page_size)`: Paginate results
   - `sort_items(items, key, reverse)`: Sort items by key

5. **Validation Helpers**:
   - `validate_required_fields(data, required_fields)`: Check required fields
   - `validate_enum(value, allowed_values, field_name)`: Validate enum values
   - `validate_range(value, min_value, max_value, field_name)`: Validate numeric ranges

### 2. `src/unifi_mcp/tools/__init__.py`
**Purpose**: Package initialization for tools module

**Exports**:
- `BaseTool`: Base class for all tools
- `ToolError`: Exception class for tool errors

### 3. `tests/test_base_tool.py`
**Purpose**: Comprehensive unit tests for BaseTool

**Test Coverage** (40 tests, all passing):

1. **Tool Initialization** (5 tests):
   - Valid tool initialization
   - Missing name raises error
   - Missing description raises error
   - Missing input_schema raises error
   - Missing execute method raises error

2. **Input Validation** (4 tests):
   - Valid input passes validation
   - Missing required field raises error
   - Wrong type raises error
   - Extra fields are allowed

3. **Tool Invocation** (4 tests):
   - Successful invocation
   - Invalid input returns error
   - Write operation without confirmation returns error
   - Write operation with confirmation succeeds

4. **Output Formatting** (7 tests):
   - format_success basic and with message
   - format_list basic and with pagination
   - format_detail basic and with type
   - format_error

5. **Data Transformation** (7 tests):
   - extract_fields basic and with rename
   - filter_items
   - paginate basic and last page
   - sort_items basic and reverse

6. **Validation Helpers** (10 tests):
   - validate_required_fields success and missing
   - validate_enum success and invalid
   - validate_range success, too small, too large, min only, max only

7. **ToolError Class** (3 tests):
   - to_dict with all fields
   - to_dict with minimal fields
   - to_json

## Design Decisions

### 1. ToolError as Exception
**Decision**: Made `ToolError` inherit from `Exception`

**Rationale**:
- Allows proper Python exception handling with try/except
- Can be raised and caught like standard exceptions
- Provides structured error information for AI agents
- Maintains compatibility with pytest and other testing frameworks

### 2. Abstract Base Class Pattern
**Decision**: Used Python's ABC (Abstract Base Class) for BaseTool

**Rationale**:
- Enforces implementation of required methods at instantiation time
- Provides clear interface contract for tool developers
- Prevents accidental instantiation of incomplete tools
- IDE support for abstract method detection

### 3. Comprehensive Helper Methods
**Decision**: Included extensive helper methods in BaseTool

**Rationale**:
- Reduces code duplication across tool implementations
- Ensures consistent output formatting
- Simplifies common operations (pagination, filtering, sorting)
- Makes tool development faster and more consistent

### 4. JSON Schema Validation
**Decision**: Used jsonschema library for input validation

**Rationale**:
- Industry-standard validation approach
- Provides detailed error messages
- Supports complex validation rules
- Compatible with MCP tool schema definitions

### 5. Confirmation Requirement for Write Operations
**Decision**: Built-in confirmation check for write operations

**Rationale**:
- Safety-first approach prevents accidental changes
- Explicit confirmation required via `confirm=true` parameter
- Clear error messages guide users to add confirmation
- Aligns with security requirements (Req 10.1, 10.2)

## Requirements Satisfied

✅ **Requirement 1.6**: Tool error handling and response formatting
- Implemented `ToolError` exception class
- Comprehensive error response formatting
- Clear error messages with actionable steps

✅ **Requirement 7.1**: Clear, descriptive tool names
- Enforced via `name` attribute requirement
- Convention documented for "unifi_" prefix

✅ **Requirement 7.2**: Concise tool descriptions
- Enforced via `description` attribute requirement
- Documentation recommends <200 characters

✅ **Requirement 7.3**: Simple, flat input schemas
- Supported via `input_schema` attribute
- JSON schema validation ensures compliance

✅ **Requirement 7.4**: Clear parameter descriptions
- Supported via JSON schema structure
- Validation provides detailed error messages

✅ **Requirement 7.5**: Optional parameter marking
- Supported via JSON schema "required" field
- Validation enforces required parameters

✅ **Requirement 11.4**: Validation errors with specific details
- `validate_input()` provides detailed validation errors
- Field-level error messages with paths
- Actionable steps for resolution

## Integration Points

### With Tool Registry
- Tools register themselves using `ToolDefinition` from tool_registry
- BaseTool provides the handler interface expected by registry
- Category and confirmation requirements integrated

### With MCP Server
- Tool invocation through `invoke()` method
- Error responses formatted for MCP protocol
- Success responses formatted for AI consumption

### With UniFi Client
- Tools receive `unifi_client` parameter in `execute()`
- Client used for all UniFi API interactions
- Error handling for API failures

## Usage Example

```python
from unifi_mcp.tools.base import BaseTool

class ListDevicesTool(BaseTool):
    """Example tool implementation."""
    
    name = "unifi_list_devices"
    description = "List all UniFi devices (switches, APs, gateways)"
    category = "network_discovery"
    input_schema = {
        "type": "object",
        "properties": {
            "device_type": {
                "type": "string",
                "enum": ["all", "switch", "ap", "gateway"],
                "description": "Filter by device type"
            }
        }
    }
    
    async def execute(self, unifi_client, **kwargs):
        device_type = kwargs.get("device_type", "all")
        
        # Get devices from UniFi API
        devices = await unifi_client.get("/api/s/default/stat/device")
        
        # Filter if needed
        if device_type != "all":
            devices = self.filter_items(
                devices,
                lambda d: d.get("type") == device_type
            )
        
        # Extract relevant fields
        summary_devices = [
            self.extract_fields(
                device,
                ["_id", "name", "type", "model", "ip", "state"],
                rename={"_id": "id", "ip": "ip_address"}
            )
            for device in devices
        ]
        
        return self.format_list(summary_devices)
```

## Testing Results

All 40 unit tests pass successfully:
- ✅ Tool initialization validation
- ✅ Input validation against JSON schema
- ✅ Tool invocation lifecycle
- ✅ Output formatting helpers
- ✅ Data transformation helpers
- ✅ Validation helpers
- ✅ ToolError functionality

## Next Steps

With the base tool class complete, the next tasks can proceed:

1. **Task 11**: Implement network discovery tools
   - ListDevicesTool
   - GetDeviceDetailsTool
   - ListClientsTool
   - GetClientDetailsTool
   - ListNetworksTool
   - GetNetworkDetailsTool
   - ListWLANsTool
   - GetWLANDetailsTool

2. **Task 14**: Implement security tools
   - ListFirewallRulesTool
   - GetFirewallRuleDetailsTool
   - etc.

All future tools will inherit from `BaseTool` and benefit from:
- Automatic input validation
- Consistent error handling
- Standard output formatting
- Common data transformation utilities
- Built-in confirmation checks for write operations

## Files Modified

None - this task only created new files.

## Dependencies

- `jsonschema`: For JSON schema validation
- `unifi_mcp.unifi_client`: For UniFi API client interface
- `unifi_mcp.utils.logging`: For structured logging

## Performance Considerations

- Input validation is fast (JSON schema validation is optimized)
- Helper methods are lightweight (no heavy processing)
- Pagination support prevents memory issues with large datasets
- Caching handled at UniFi client level, not in BaseTool

## Security Considerations

- Confirmation requirement enforced for write operations
- Sensitive data redaction handled by logging layer
- Input validation prevents injection attacks
- Error messages don't expose sensitive information

---

**Task Status**: ✅ Complete
**Tests**: 40/40 passing
**Requirements**: All satisfied (1.6, 7.1-7.5, 11.4)
