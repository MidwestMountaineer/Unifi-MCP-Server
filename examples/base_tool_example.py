"""Example demonstrating BaseTool usage.

This example shows how to create a simple tool using the BaseTool class.
"""

import asyncio
from unittest.mock import AsyncMock

from unifi_mcp.tools.base import BaseTool


class ExampleTool(BaseTool):
    """Example tool that demonstrates BaseTool features."""
    
    name = "example_tool"
    description = "An example tool demonstrating BaseTool usage"
    category = "examples"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "A message to echo back"
            },
            "count": {
                "type": "integer",
                "description": "Number of times to repeat the message",
                "minimum": 1,
                "maximum": 10
            }
        },
        "required": ["message"]
    }
    
    async def execute(self, unifi_client, **kwargs):
        """Execute the example tool.
        
        Args:
            unifi_client: UniFi API client (not used in this example)
            **kwargs: Tool arguments
        
        Returns:
            Formatted success response
        """
        message = kwargs["message"]
        count = kwargs.get("count", 1)
        
        # Validate count is in range
        self.validate_range(count, min_value=1, max_value=10, field_name="count")
        
        # Create result
        result = {
            "message": message,
            "count": count,
            "repeated": [message] * count
        }
        
        return self.format_success(
            result,
            message=f"Successfully repeated message {count} times"
        )


async def main():
    """Run example tool demonstrations."""
    
    # Create tool instance
    tool = ExampleTool()
    
    # Create mock UniFi client (not used in this example)
    mock_client = AsyncMock()
    
    print("=" * 60)
    print("BaseTool Example Demonstration")
    print("=" * 60)
    print()
    
    # Example 1: Valid invocation
    print("Example 1: Valid invocation")
    print("-" * 60)
    arguments = {"message": "Hello, World!", "count": 3}
    print(f"Arguments: {arguments}")
    result = await tool.invoke(mock_client, arguments)
    print(f"Result: {result}")
    print()
    
    # Example 2: Missing required field
    print("Example 2: Missing required field")
    print("-" * 60)
    arguments = {"count": 2}  # Missing 'message'
    print(f"Arguments: {arguments}")
    result = await tool.invoke(mock_client, arguments)
    print(f"Result: {result}")
    print()
    
    # Example 3: Invalid type
    print("Example 3: Invalid type")
    print("-" * 60)
    arguments = {"message": "Test", "count": "not_a_number"}
    print(f"Arguments: {arguments}")
    result = await tool.invoke(mock_client, arguments)
    print(f"Result: {result}")
    print()
    
    # Example 4: Value out of range
    print("Example 4: Value out of range")
    print("-" * 60)
    arguments = {"message": "Test", "count": 100}
    print(f"Arguments: {arguments}")
    result = await tool.invoke(mock_client, arguments)
    print(f"Result: {result}")
    print()
    
    # Example 5: Using helper methods directly
    print("Example 5: Using helper methods")
    print("-" * 60)
    
    # Extract fields
    data = {"id": 1, "name": "Test", "extra": "value", "more": "data"}
    extracted = tool.extract_fields(data, ["id", "name"])
    print(f"Extract fields: {extracted}")
    
    # Filter items
    items = [
        {"id": 1, "active": True},
        {"id": 2, "active": False},
        {"id": 3, "active": True}
    ]
    filtered = tool.filter_items(items, lambda x: x["active"])
    print(f"Filter items: {filtered}")
    
    # Paginate
    items = list(range(25))
    page_items, total = tool.paginate(items, page=2, page_size=10)
    print(f"Paginate (page 2): {page_items} (total: {total})")
    
    # Sort items
    items = [
        {"id": 3, "name": "C"},
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"}
    ]
    sorted_items = tool.sort_items(items, key="id")
    print(f"Sort items: {sorted_items}")
    print()
    
    print("=" * 60)
    print("Example demonstration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
