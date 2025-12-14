"""Property-based tests for MCP best practices compliance.

This module contains property-based tests that verify the UniFi MCP server
follows MCP best practices for tool design, including:
- Tool namespacing (unifi_ prefix)
- Pagination defaults
- Parameter naming conventions

These tests validate Requirements 9.1, 9.4, and 10.4 from the specification.
"""

import pytest
from hypothesis import given, settings, strategies as st, Phase
from typing import Dict, Any, List, Type
import importlib
import inspect

from unifi_mcp.tools.base import BaseTool


# Configure hypothesis for minimum 100 iterations
settings.register_profile(
    "unifi_mcp",
    max_examples=100,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink]
)
settings.load_profile("unifi_mcp")


def get_all_tool_classes() -> List[Type[BaseTool]]:
    """Discover all tool classes from the tools modules.
    
    Returns:
        List of all BaseTool subclasses
    """
    tool_classes = []
    
    # Import all tool modules
    tool_modules = [
        "unifi_mcp.tools.network_discovery",
        "unifi_mcp.tools.security",
        "unifi_mcp.tools.statistics",
        "unifi_mcp.tools.migration",
        "unifi_mcp.tools.write_operations",
    ]
    
    for module_name in tool_modules:
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    tool_classes.append(obj)
        except ImportError as e:
            pytest.skip(f"Could not import {module_name}: {e}")
    
    return tool_classes


# Get all tool classes once at module load time
ALL_TOOL_CLASSES = get_all_tool_classes()


class TestToolNamespacingCompliance:
    """Property-based tests for tool namespacing compliance.
    
    These tests verify that all tools use the unifi_ prefix as required
    by Requirement 9.1.
    """

    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_name_has_unifi_prefix(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the tool name SHALL start with the `unifi_` prefix.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        # Use modulo to handle edge cases where hypothesis generates out of range
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        assert tool.name.startswith("unifi_"), (
            f"Tool '{tool.name}' does not start with 'unifi_' prefix. "
            f"All tools must use the 'unifi_' namespace prefix for MCP compliance."
        )
    
    def test_all_tools_have_unifi_prefix(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        Verify all discovered tools have the unifi_ prefix.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        non_compliant_tools = []
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            if not tool.name.startswith("unifi_"):
                non_compliant_tools.append(tool.name)
        
        assert len(non_compliant_tools) == 0, (
            f"The following tools do not have 'unifi_' prefix: {non_compliant_tools}"
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_name_is_lowercase(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the tool name SHALL be lowercase with underscores.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        assert tool.name == tool.name.lower(), (
            f"Tool name '{tool.name}' is not lowercase. "
            f"Tool names should be lowercase with underscores."
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_name_uses_underscores(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the tool name SHALL use underscores as separators.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        # Check that name doesn't contain hyphens or spaces
        assert "-" not in tool.name, (
            f"Tool name '{tool.name}' contains hyphens. Use underscores instead."
        )
        assert " " not in tool.name, (
            f"Tool name '{tool.name}' contains spaces. Use underscores instead."
        )


class TestPaginationDefaultsCompliance:
    """Property-based tests for pagination defaults compliance.
    
    These tests verify that tools with pagination use sensible defaults
    as required by Requirement 9.4.
    """
    
    def _get_paginated_tools(self) -> List[Type[BaseTool]]:
        """Get all tools that support pagination."""
        paginated_tools = []
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            if "page_size" in properties or "page" in properties:
                paginated_tools.append(tool_class)
        return paginated_tools
    
    def test_paginated_tools_have_page_size_default(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 9: Pagination Default Application**
        **Validates: Requirements 9.4**
        
        For any tool with pagination, page_size SHALL have a sensible default.
        """
        paginated_tools = self._get_paginated_tools()
        
        if not paginated_tools:
            pytest.skip("No paginated tools found")
        
        for tool_class in paginated_tools:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            
            if "page_size" in properties:
                page_size_schema = properties["page_size"]
                assert "default" in page_size_schema, (
                    f"Tool '{tool.name}' has page_size but no default value"
                )
                default = page_size_schema["default"]
                assert default > 0, (
                    f"Tool '{tool.name}' has invalid page_size default: {default}"
                )
                assert default <= 100, (
                    f"Tool '{tool.name}' has page_size default > 100: {default}. "
                    f"Consider a smaller default for context efficiency."
                )

    def test_paginated_tools_have_page_default(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 9: Pagination Default Application**
        **Validates: Requirements 9.4**
        
        For any tool with pagination, page SHALL default to 1.
        """
        paginated_tools = self._get_paginated_tools()
        
        if not paginated_tools:
            pytest.skip("No paginated tools found")
        
        for tool_class in paginated_tools:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            
            if "page" in properties:
                page_schema = properties["page"]
                assert "default" in page_schema, (
                    f"Tool '{tool.name}' has page but no default value"
                )
                default = page_schema["default"]
                assert default == 1, (
                    f"Tool '{tool.name}' has page default != 1: {default}. "
                    f"Page should default to 1 (first page)."
                )
    
    def test_paginated_tools_have_maximum_page_size(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 9: Pagination Default Application**
        **Validates: Requirements 9.4**
        
        For any tool with pagination, page_size SHALL have a maximum limit.
        """
        paginated_tools = self._get_paginated_tools()
        
        if not paginated_tools:
            pytest.skip("No paginated tools found")
        
        for tool_class in paginated_tools:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            
            if "page_size" in properties:
                page_size_schema = properties["page_size"]
                assert "maximum" in page_size_schema, (
                    f"Tool '{tool.name}' has page_size but no maximum limit. "
                    f"Add a maximum to prevent excessive context consumption."
                )
                maximum = page_size_schema["maximum"]
                assert maximum <= 500, (
                    f"Tool '{tool.name}' has page_size maximum > 500: {maximum}. "
                    f"Consider a lower maximum for context efficiency."
                )
    
    def test_paginated_tools_have_minimum_page_size(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 9: Pagination Default Application**
        **Validates: Requirements 9.4**
        
        For any tool with pagination, page_size SHALL have a minimum of 1.
        """
        paginated_tools = self._get_paginated_tools()
        
        if not paginated_tools:
            pytest.skip("No paginated tools found")
        
        for tool_class in paginated_tools:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            
            if "page_size" in properties:
                page_size_schema = properties["page_size"]
                assert "minimum" in page_size_schema, (
                    f"Tool '{tool.name}' has page_size but no minimum limit"
                )
                minimum = page_size_schema["minimum"]
                assert minimum >= 1, (
                    f"Tool '{tool.name}' has page_size minimum < 1: {minimum}"
                )


class TestParameterNamingCompliance:
    """Property-based tests for parameter naming compliance.
    
    These tests verify that tools use unambiguous parameter names
    as required by Requirement 10.4.
    """
    
    # Parameters that should include entity type prefix
    IDENTIFIER_PARAMS = ["id", "mac", "address"]
    
    # Acceptable prefixed parameter names
    ACCEPTABLE_ID_PARAMS = [
        "device_id", "client_id", "rule_id", "route_id", "forward_id",
        "network_id", "wlan_id", "site_id", "user_id", "group_id",
        "mac_address", "ip_address", "src_address", "dst_address",
        "source_address", "destination_address"
    ]
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_no_ambiguous_id_parameter(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 11: Parameter Naming Convention**
        **Validates: Requirements 10.4**
        
        For any tool parameter that accepts an identifier, the parameter name
        SHALL include the entity type (e.g., `device_id`, `rule_id`, not just `id`).
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        schema = tool.input_schema
        properties = schema.get("properties", {})
        
        # Check for ambiguous parameter names
        ambiguous_params = []
        for param_name in properties.keys():
            # Check if parameter is just "id" without prefix
            if param_name == "id":
                ambiguous_params.append(param_name)
            # Check if parameter is just "mac" without suffix
            elif param_name == "mac":
                ambiguous_params.append(param_name)
        
        assert len(ambiguous_params) == 0, (
            f"Tool '{tool.name}' has ambiguous parameter names: {ambiguous_params}. "
            f"Use prefixed names like 'device_id', 'mac_address' instead."
        )

    def test_all_tools_use_prefixed_identifiers(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 11: Parameter Naming Convention**
        **Validates: Requirements 10.4**
        
        Verify all tools use properly prefixed identifier parameters.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        violations = []
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            
            for param_name in properties.keys():
                # Check for bare "id" parameter
                if param_name == "id":
                    violations.append(f"{tool.name}: 'id' should be prefixed (e.g., 'device_id')")
                # Check for bare "mac" parameter
                elif param_name == "mac":
                    violations.append(f"{tool.name}: 'mac' should be 'mac_address'")
        
        assert len(violations) == 0, (
            f"Parameter naming violations found:\n" + "\n".join(violations)
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_parameter_names_are_descriptive(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 11: Parameter Naming Convention**
        **Validates: Requirements 10.4**
        
        For any tool parameter, the name SHALL be descriptive and unambiguous.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        schema = tool.input_schema
        properties = schema.get("properties", {})
        
        # Check that all parameters have descriptions
        for param_name, param_schema in properties.items():
            assert "description" in param_schema, (
                f"Tool '{tool.name}' parameter '{param_name}' lacks a description. "
                f"All parameters should have descriptions for clarity."
            )
            
            # Description should not be empty
            description = param_schema.get("description", "")
            assert len(description) > 0, (
                f"Tool '{tool.name}' parameter '{param_name}' has empty description."
            )
    
    def test_required_parameters_are_marked(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 11: Parameter Naming Convention**
        **Validates: Requirements 10.4**
        
        For any tool with required parameters, they SHALL be marked in the schema.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # If there are required parameters, verify they exist in properties
            for req_param in required:
                assert req_param in properties, (
                    f"Tool '{tool.name}' marks '{req_param}' as required "
                    f"but it's not in properties"
                )


class TestToolDescriptionCompliance:
    """Tests for tool description compliance.
    
    These tests verify that tools have concise, unambiguous descriptions
    as required by Requirement 9.2.
    """
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_has_description(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the tool SHALL have a non-empty description.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        assert tool.description, (
            f"Tool '{tool.name}' has no description"
        )
        assert len(tool.description) > 0, (
            f"Tool '{tool.name}' has empty description"
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_description_is_concise(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the description SHALL be concise (<200 chars).
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        # Description should be concise for AI consumption
        assert len(tool.description) < 200, (
            f"Tool '{tool.name}' description is too long ({len(tool.description)} chars). "
            f"Keep descriptions under 200 characters for context efficiency."
        )


class TestToolCategoryCompliance:
    """Tests for tool category compliance."""
    
    VALID_CATEGORIES = [
        "network_discovery",
        "security",
        "statistics",
        "migration",
        "write_operations",
        "general"
    ]
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_has_valid_category(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 8: Tool Namespacing Consistency**
        **Validates: Requirements 9.1**
        
        For any registered tool, the category SHALL be one of the valid categories.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        assert tool.category in self.VALID_CATEGORIES, (
            f"Tool '{tool.name}' has invalid category '{tool.category}'. "
            f"Valid categories: {self.VALID_CATEGORIES}"
        )



class TestResponseFormatCompliance:
    """Property-based tests for response format compliance.
    
    These tests verify that tools properly support response_format parameter
    as required by Requirement 10.3.
    """
    
    def _get_tools_with_response_format(self) -> List[Type[BaseTool]]:
        """Get all tools that support response_format parameter."""
        tools_with_format = []
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            if "response_format" in properties:
                tools_with_format.append(tool_class)
        return tools_with_format
    
    def test_response_format_tools_have_valid_enum(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 10: Response Format Support**
        **Validates: Requirements 10.3**
        
        For any tool that supports response_format, the parameter SHALL have
        valid enum values of "detailed" and "concise".
        """
        tools_with_format = self._get_tools_with_response_format()
        
        if not tools_with_format:
            pytest.skip("No tools with response_format found")
        
        for tool_class in tools_with_format:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            response_format_schema = properties.get("response_format", {})
            
            assert "enum" in response_format_schema, (
                f"Tool '{tool.name}' response_format lacks enum values"
            )
            
            enum_values = response_format_schema.get("enum", [])
            assert "detailed" in enum_values, (
                f"Tool '{tool.name}' response_format missing 'detailed' option"
            )
            assert "concise" in enum_values, (
                f"Tool '{tool.name}' response_format missing 'concise' option"
            )
    
    def test_response_format_defaults_to_detailed(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 10: Response Format Support**
        **Validates: Requirements 10.3**
        
        For any tool that supports response_format, the default SHALL be "detailed"
        for backward compatibility.
        """
        tools_with_format = self._get_tools_with_response_format()
        
        if not tools_with_format:
            pytest.skip("No tools with response_format found")
        
        for tool_class in tools_with_format:
            tool = tool_class()
            schema = tool.input_schema
            properties = schema.get("properties", {})
            response_format_schema = properties.get("response_format", {})
            
            assert "default" in response_format_schema, (
                f"Tool '{tool.name}' response_format lacks default value"
            )
            
            default = response_format_schema.get("default")
            assert default == "detailed", (
                f"Tool '{tool.name}' response_format default is '{default}', "
                f"expected 'detailed' for backward compatibility"
            )
    
    @given(tool_index=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_response_format_has_description(self, tool_index):
        """
        **Feature: unifi-mcp-v2-api-support, Property 10: Response Format Support**
        **Validates: Requirements 10.3**
        
        For any tool that supports response_format, the parameter SHALL have
        a description explaining the format options.
        """
        tools_with_format = self._get_tools_with_response_format()
        
        if not tools_with_format:
            pytest.skip("No tools with response_format found")
        
        tool_class = tools_with_format[tool_index % len(tools_with_format)]
        tool = tool_class()
        schema = tool.input_schema
        properties = schema.get("properties", {})
        response_format_schema = properties.get("response_format", {})
        
        assert "description" in response_format_schema, (
            f"Tool '{tool.name}' response_format lacks description"
        )
        
        description = response_format_schema.get("description", "")
        assert len(description) > 0, (
            f"Tool '{tool.name}' response_format has empty description"
        )
    
    def test_tools_with_response_format_have_concise_fields(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 10: Response Format Support**
        **Validates: Requirements 10.3**
        
        For any tool that supports response_format, the tool class SHALL define
        CONCISE_FIELDS to specify which fields to include in concise format.
        """
        tools_with_format = self._get_tools_with_response_format()
        
        if not tools_with_format:
            pytest.skip("No tools with response_format found")
        
        for tool_class in tools_with_format:
            tool = tool_class()
            
            assert hasattr(tool_class, 'CONCISE_FIELDS'), (
                f"Tool '{tool.name}' supports response_format but lacks CONCISE_FIELDS"
            )
            
            concise_fields = getattr(tool_class, 'CONCISE_FIELDS', [])
            assert len(concise_fields) > 0, (
                f"Tool '{tool.name}' has empty CONCISE_FIELDS"
            )


class TestLargeDatasetTruncation:
    """Property-based tests for large dataset truncation.
    
    These tests verify that tools properly truncate large datasets
    as required by Requirement 10.6.
    """
    
    def test_base_tool_has_truncation_method(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 12: Large Dataset Truncation**
        **Validates: Requirements 10.6**
        
        The BaseTool class SHALL provide truncation functionality.
        """
        assert hasattr(BaseTool, 'truncate_response'), (
            "BaseTool lacks truncate_response method"
        )
        assert hasattr(BaseTool, 'format_list_with_truncation'), (
            "BaseTool lacks format_list_with_truncation method"
        )
        assert hasattr(BaseTool, 'DEFAULT_MAX_RESPONSE_SIZE'), (
            "BaseTool lacks DEFAULT_MAX_RESPONSE_SIZE constant"
        )
    
    def test_default_max_response_size_is_reasonable(self):
        """
        **Feature: unifi-mcp-v2-api-support, Property 12: Large Dataset Truncation**
        **Validates: Requirements 10.6**
        
        The default max response size SHALL be reasonable (between 50 and 500).
        """
        max_size = BaseTool.DEFAULT_MAX_RESPONSE_SIZE
        
        assert max_size >= 50, (
            f"DEFAULT_MAX_RESPONSE_SIZE ({max_size}) is too small, should be >= 50"
        )
        assert max_size <= 500, (
            f"DEFAULT_MAX_RESPONSE_SIZE ({max_size}) is too large, should be <= 500"
        )
    
    @given(
        items_count=st.integers(min_value=0, max_value=500),
        max_size=st.integers(min_value=10, max_value=200)
    )
    @settings(max_examples=100)
    def test_truncation_respects_max_size(self, items_count, max_size):
        """
        **Feature: unifi-mcp-v2-api-support, Property 12: Large Dataset Truncation**
        **Validates: Requirements 10.6**
        
        For any list of items exceeding max_size, the truncated result SHALL
        contain at most max_size items.
        """
        # Create a concrete tool instance for testing
        class TestTool(BaseTool):
            name = "unifi_test_tool"
            description = "Test tool"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                return {}
        
        tool = TestTool()
        items = [{"id": i, "name": f"item_{i}"} for i in range(items_count)]
        
        truncated, was_truncated, guidance = tool.truncate_response(items, max_size)
        
        assert len(truncated) <= max_size, (
            f"Truncated result has {len(truncated)} items, expected <= {max_size}"
        )
        
        if items_count > max_size:
            assert was_truncated, (
                f"Expected truncation for {items_count} items with max_size {max_size}"
            )
            assert guidance is not None, (
                "Expected guidance message when truncated"
            )
        else:
            assert not was_truncated, (
                f"Unexpected truncation for {items_count} items with max_size {max_size}"
            )
    
    @given(items_count=st.integers(min_value=101, max_value=500))
    @settings(max_examples=100)
    def test_truncation_includes_guidance_message(self, items_count):
        """
        **Feature: unifi-mcp-v2-api-support, Property 12: Large Dataset Truncation**
        **Validates: Requirements 10.6**
        
        When truncation occurs, the response SHALL include guidance for more
        targeted queries.
        """
        class TestTool(BaseTool):
            name = "unifi_test_tool"
            description = "Test tool"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                return {}
        
        tool = TestTool()
        items = [{"id": i} for i in range(items_count)]
        
        truncated, was_truncated, guidance = tool.truncate_response(items)
        
        assert was_truncated, "Expected truncation for large dataset"
        assert guidance is not None, "Expected guidance message"
        assert "pagination" in guidance.lower() or "page" in guidance.lower(), (
            "Guidance should mention pagination"
        )
    
    @given(
        items_count=st.integers(min_value=0, max_value=200),
        response_format=st.sampled_from(["detailed", "concise"])
    )
    @settings(max_examples=100)
    def test_format_list_with_truncation_includes_metadata(self, items_count, response_format):
        """
        **Feature: unifi-mcp-v2-api-support, Property 12: Large Dataset Truncation**
        **Validates: Requirements 10.6**
        
        The format_list_with_truncation method SHALL include truncation metadata
        when truncation occurs.
        """
        class TestTool(BaseTool):
            name = "unifi_test_tool"
            description = "Test tool"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                return {}
        
        tool = TestTool()
        items = [{"id": i, "name": f"item_{i}", "extra": "data"} for i in range(items_count)]
        concise_fields = ["id", "name"]
        
        result = tool.format_list_with_truncation(
            items=items,
            response_format=response_format,
            concise_fields=concise_fields,
            max_size=50
        )
        
        assert "success" in result
        assert "data" in result
        assert "count" in result
        assert "response_format" in result
        assert result["response_format"] == response_format
        
        if items_count > 50:
            assert result.get("truncated") is True, (
                "Expected truncated=True for large dataset"
            )
            assert "truncated_from" in result, (
                "Expected truncated_from in result"
            )
            assert "guidance" in result, (
                "Expected guidance in truncated result"
            )
    
    @given(
        items_count=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_concise_format_has_fewer_fields(self, items_count):
        """
        **Feature: unifi-mcp-v2-api-support, Property 10: Response Format Support**
        **Validates: Requirements 10.3**
        
        When response_format="concise" is specified, the response SHALL contain
        fewer fields than when response_format="detailed" is specified.
        """
        class TestTool(BaseTool):
            name = "unifi_test_tool"
            description = "Test tool"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                return {}
        
        tool = TestTool()
        items = [
            {"id": i, "name": f"item_{i}", "extra1": "data1", "extra2": "data2", "extra3": "data3"}
            for i in range(items_count)
        ]
        concise_fields = ["id", "name"]
        
        detailed_result = tool.format_list_with_truncation(
            items=items,
            response_format="detailed",
            concise_fields=concise_fields
        )
        
        concise_result = tool.format_list_with_truncation(
            items=items,
            response_format="concise",
            concise_fields=concise_fields
        )
        
        # Both should have same count
        assert detailed_result["count"] == concise_result["count"]
        
        # Concise items should have fewer fields
        if items_count > 0:
            detailed_item = detailed_result["data"][0]
            concise_item = concise_result["data"][0]
            
            assert len(concise_item) <= len(detailed_item), (
                f"Concise item has {len(concise_item)} fields, "
                f"detailed has {len(detailed_item)} fields"
            )
            
            # Concise should only have the specified fields
            for field in concise_item.keys():
                assert field in concise_fields, (
                    f"Concise item has unexpected field '{field}'"
                )


class TestToolDescriptionConciseness:
    """Property-based tests for tool description conciseness.
    
    These tests verify that all tool descriptions are concise to minimize
    baseline context consumption when tools are listed.
    
    **Feature: unifi-power-optimization, Property 1: Tool Description Conciseness**
    **Validates: Requirements 2.3**
    """
    
    # Maximum allowed description length (from design doc)
    MAX_DESCRIPTION_LENGTH = 100
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_description_under_max_length(self, tool_index):
        """
        **Feature: unifi-power-optimization, Property 1: Tool Description Conciseness**
        **Validates: Requirements 2.3**
        
        For any MCP tool in the UniFi server, the tool description SHALL be
        under 100 characters to minimize baseline context consumption when
        tools are listed.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        description_length = len(tool.description)
        
        assert description_length <= self.MAX_DESCRIPTION_LENGTH, (
            f"Tool '{tool.name}' has description of {description_length} characters, "
            f"which exceeds the maximum of {self.MAX_DESCRIPTION_LENGTH}. "
            f"Description: '{tool.description}'"
        )
    
    def test_all_tools_have_concise_descriptions(self):
        """
        **Feature: unifi-power-optimization, Property 1: Tool Description Conciseness**
        **Validates: Requirements 2.3**
        
        Verify all discovered tools have descriptions under the maximum length.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        verbose_tools = []
        for tool_class in ALL_TOOL_CLASSES:
            tool = tool_class()
            if len(tool.description) > self.MAX_DESCRIPTION_LENGTH:
                verbose_tools.append({
                    "name": tool.name,
                    "length": len(tool.description),
                    "description": tool.description
                })
        
        assert len(verbose_tools) == 0, (
            f"The following tools have descriptions exceeding {self.MAX_DESCRIPTION_LENGTH} chars: "
            f"{[t['name'] + ' (' + str(t['length']) + ' chars)' for t in verbose_tools]}"
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_description_not_empty(self, tool_index):
        """
        **Feature: unifi-power-optimization, Property 1: Tool Description Conciseness**
        **Validates: Requirements 2.3**
        
        For any MCP tool, the description SHALL not be empty.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        assert tool.description and len(tool.description.strip()) > 0, (
            f"Tool '{tool.name}' has an empty description"
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_description_no_verbose_phrases(self, tool_index):
        """
        **Feature: unifi-power-optimization, Property 1: Tool Description Conciseness**
        **Validates: Requirements 2.3**
        
        For any MCP tool, the description SHALL NOT contain verbose phrases
        like "Use this to..." that waste context tokens.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        verbose_phrases = [
            "Use this to",
            "This tool is used to",
            "This tool allows you to",
            "You can use this to",
        ]
        
        description_lower = tool.description.lower()
        for phrase in verbose_phrases:
            assert phrase.lower() not in description_lower, (
                f"Tool '{tool.name}' description contains verbose phrase '{phrase}'. "
                f"Description should focus on WHAT the tool does, not HOW to use it."
            )


class TestErrorResponseActionability:
    """Property-based tests for error response actionability.
    
    These tests verify that all error responses include actionable steps
    as required by Requirement 7.2 from the unifi-power-optimization spec.
    
    **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
    **Validates: Requirements 7.2**
    """
    
    def test_tool_error_has_actionable_steps_field(self):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        The ToolError class SHALL have an actionable_steps field.
        """
        from unifi_mcp.tools.base import ToolError
        
        # Create a ToolError with actionable steps
        error = ToolError(
            code="TEST_ERROR",
            message="Test error message",
            details="Test details",
            actionable_steps=["Step 1", "Step 2"]
        )
        
        assert hasattr(error, 'actionable_steps'), (
            "ToolError class must have actionable_steps attribute"
        )
        assert error.actionable_steps is not None, (
            "ToolError actionable_steps should not be None when provided"
        )
        assert len(error.actionable_steps) >= 1, (
            "ToolError should have at least one actionable step"
        )
    
    def test_tool_error_to_dict_includes_actionable_steps(self):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        When ToolError is converted to dict, it SHALL include actionable_steps.
        """
        from unifi_mcp.tools.base import ToolError
        
        error = ToolError(
            code="TEST_ERROR",
            message="Test error message",
            details="Test details",
            actionable_steps=["Check connectivity", "Verify credentials"]
        )
        
        error_dict = error.to_dict()
        
        assert "error" in error_dict, "Error dict should have 'error' key"
        assert "actionable_steps" in error_dict["error"], (
            "Error dict should include actionable_steps"
        )
        assert len(error_dict["error"]["actionable_steps"]) >= 1, (
            "Error dict should have at least one actionable step"
        )
    
    @given(
        code=st.sampled_from([
            "VALIDATION_ERROR", "API_ERROR", "DEVICE_NOT_FOUND", 
            "CLIENT_NOT_FOUND", "NETWORK_NOT_FOUND", "RULE_NOT_FOUND",
            "ROUTE_NOT_FOUND", "WLAN_NOT_FOUND", "FORWARD_NOT_FOUND",
            "MISSING_FIELDS", "INVALID_VALUE", "VALUE_OUT_OF_RANGE",
            "EXECUTION_ERROR", "CONFIRMATION_REQUIRED", "BOTH_ENDPOINTS_FAILED"
        ]),
        message=st.text(min_size=5, max_size=100),
        num_steps=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_tool_error_actionable_steps_property(self, code, message, num_steps):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        For any error response from the MCP server, the response SHALL include
        an actionable_steps field with at least one specific step the user can
        take to resolve the issue.
        """
        from unifi_mcp.tools.base import ToolError
        
        # Generate actionable steps
        steps = [f"Step {i+1}: Take action {i+1}" for i in range(num_steps)]
        
        error = ToolError(
            code=code,
            message=message,
            actionable_steps=steps
        )
        
        error_dict = error.to_dict()
        
        # Property: actionable_steps must be present and non-empty
        assert "error" in error_dict, "Error response must have 'error' key"
        assert "actionable_steps" in error_dict["error"], (
            f"Error response for code '{code}' must include actionable_steps"
        )
        assert isinstance(error_dict["error"]["actionable_steps"], list), (
            "actionable_steps must be a list"
        )
        assert len(error_dict["error"]["actionable_steps"]) >= 1, (
            f"Error response for code '{code}' must have at least one actionable step"
        )
    
    def test_base_tool_format_error_includes_actionable_steps(self):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        The BaseTool.format_error method SHALL include actionable_steps in output.
        """
        from unifi_mcp.tools.base import BaseTool
        
        # Create a concrete tool for testing
        class TestTool(BaseTool):
            name = "unifi_test_tool"
            description = "Test tool for error formatting"
            input_schema = {"type": "object", "properties": {}}
            
            async def execute(self, unifi_client, **kwargs):
                return {}
        
        tool = TestTool()
        
        error_response = tool.format_error(
            code="TEST_ERROR",
            message="Test error",
            details="Test details",
            actionable_steps=["Check configuration", "Verify access"]
        )
        
        assert "error" in error_response, "format_error should return error dict"
        assert "actionable_steps" in error_response["error"], (
            "format_error output should include actionable_steps"
        )
        assert len(error_response["error"]["actionable_steps"]) >= 1, (
            "format_error should include at least one actionable step"
        )
    
    def test_endpoint_error_has_actionable_steps(self):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        The EndpointError class SHALL provide actionable steps via get_actionable_steps().
        """
        from unifi_mcp.api.endpoint_router import EndpointError
        
        # Test single endpoint failure
        error = EndpointError(
            feature="firewall_rules",
            primary_endpoint="/api/v2/firewall/rules",
            primary_error="Connection refused",
            message="Failed to retrieve firewall rules"
        )
        
        steps = error.get_actionable_steps()
        
        assert isinstance(steps, list), "get_actionable_steps should return a list"
        assert len(steps) >= 1, (
            "EndpointError should provide at least one actionable step"
        )
    
    def test_endpoint_error_both_endpoints_failed_has_actionable_steps(self):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        When both v2 and v1 endpoints fail, EndpointError SHALL provide actionable steps.
        """
        from unifi_mcp.api.endpoint_router import EndpointError
        
        # Test both endpoints failed
        error = EndpointError(
            feature="firewall_rules",
            primary_endpoint="/api/v2/firewall/rules",
            primary_error="Connection refused",
            fallback_endpoint="/api/s/default/rest/firewallrule",
            fallback_error="Timeout",
            message="Both endpoints failed"
        )
        
        steps = error.get_actionable_steps()
        
        assert isinstance(steps, list), "get_actionable_steps should return a list"
        assert len(steps) >= 1, (
            "EndpointError with both failures should provide actionable steps"
        )
        # Should mention both endpoints failed
        steps_text = " ".join(steps).lower()
        assert "both" in steps_text or "v2" in steps_text or "v1" in steps_text, (
            "Actionable steps should reference the dual endpoint failure"
        )
    
    @given(tool_index=st.integers(min_value=0, max_value=max(0, len(ALL_TOOL_CLASSES) - 1)))
    @settings(max_examples=100)
    def test_tool_validation_errors_have_actionable_steps(self, tool_index):
        """
        **Feature: unifi-power-optimization, Property 2: Error Response Actionability**
        **Validates: Requirements 7.2**
        
        For any tool, validation errors SHALL include actionable steps.
        """
        if not ALL_TOOL_CLASSES:
            pytest.skip("No tool classes found")
        
        from unifi_mcp.tools.base import ToolError
        
        tool_class = ALL_TOOL_CLASSES[tool_index % len(ALL_TOOL_CLASSES)]
        tool = tool_class()
        
        # Try to trigger a validation error with invalid input
        try:
            # Pass invalid type for a required field if any
            tool.validate_input({"invalid_field_xyz": "invalid_value"})
        except ToolError as e:
            # Validation error should have actionable steps
            assert e.actionable_steps is not None, (
                f"Tool '{tool.name}' validation error should have actionable_steps"
            )
            assert len(e.actionable_steps) >= 1, (
                f"Tool '{tool.name}' validation error should have at least one actionable step"
            )
        except Exception:
            # If no validation error, that's fine - schema may allow empty input
            pass
