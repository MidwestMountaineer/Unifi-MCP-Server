# Extension Guide

## Overview

The UniFi MCP Server is designed to be easily extensible. This guide shows you how to add new tools, create custom tool categories, extend the UniFi client, and integrate with other systems.

## Table of Contents

1. [Adding New Tools](#adding-new-tools)
2. [Creating Tool Categories](#creating-tool-categories)
3. [Extending the UniFi Client](#extending-the-unifi-client)
4. [Custom Output Formatters](#custom-output-formatters)
5. [Adding Configuration Options](#adding-configuration-options)
6. [Custom Logging](#custom-logging)
7. [Integration with Other Systems](#integration-with-other-systems)
8. [Testing Your Extensions](#testing-your-extensions)

## Adding New Tools

### Step 1: Create Tool Class

Create a new tool by inheriting from `BaseTool`:

```python
# src/unifi_mcp/tools/my_tools.py

from typing import Any, Dict
from .base import BaseTool
from ..unifi_client import UniFiClient


class MyCustomTool(BaseTool):
    """Description of what your tool does."""
    
    # Tool metadata
    name = "unifi_my_custom_tool"
    description = "Brief description for AI agents (under 200 chars)"
    category = "custom"
    requires_confirmation = False  # Set to True for write operations
    
    # JSON schema for input parameters
    input_schema = {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of parameter 1"
            },
            "param2": {
                "type": "integer",
                "description": "Description of parameter 2",
                "default": 10
            }
        },
        "required": ["param1"]
    }

    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute the tool logic.
        
        Args:
            unifi_client: UniFi API client instance
            **kwargs: Validated tool parameters
        
        Returns:
            Tool result (will be formatted as JSON)
        """
        # Extract parameters
        param1 = kwargs.get("param1")
        param2 = kwargs.get("param2", 10)
        
        # Make API call
        response = await unifi_client.get(
            f"/api/s/{unifi_client.site}/stat/device"
        )
        
        # Process data
        data = response.get("data", [])
        
        # Filter or transform as needed
        filtered_data = [
            item for item in data
            if item.get("name") == param1
        ]
        
        # Return formatted result
        return self.format_success(
            data=filtered_data,
            message=f"Found {len(filtered_data)} items"
        )
```

### Step 2: Register Tool

Add your tool to the server registration in `src/unifi_mcp/server.py`:

```python
def _register_tools(self) -> None:
    """Register all available tools with the registry."""
    # ... existing imports ...
    
    # Import your new tool
    from .tools.my_tools import MyCustomTool
    
    # ... existing tool registrations ...
    
    # Add your tool to the list
    tools_to_register = [
        # ... existing tools ...
        MyCustomTool(),
    ]
    
    # Registration happens automatically
```

### Step 3: Add Configuration (Optional)

Add configuration for your tool category in `src/unifi_mcp/config/config.yaml`:

```yaml
tools:
  # ... existing categories ...
  
  custom:
    enabled: true
    tools:
      - my_custom_tool
```

### Step 4: Test Your Tool

Create a test file `tests/test_my_tools.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from unifi_mcp.tools.my_tools import MyCustomTool


@pytest.mark.asyncio
async def test_my_custom_tool():
    """Test MyCustomTool execution."""
    # Create tool instance
    tool = MyCustomTool()
    
    # Mock UniFi client
    mock_client = AsyncMock()
    mock_client.site = "default"
    mock_client.get.return_value = {
        "data": [
            {"name": "test-device", "type": "switch"},
            {"name": "other-device", "type": "ap"}
        ]
    }
    
    # Execute tool
    result = await tool.execute(
        mock_client,
        param1="test-device",
        param2=10
    )
    
    # Verify result
    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "test-device"
```

Run tests:

```bash
pytest tests/test_my_tools.py -v
```

## Creating Tool Categories

### Step 1: Create Category File

Create a new file for your category:

```python
# src/unifi_mcp/tools/monitoring.py

from typing import Any, Dict, List
from .base import BaseTool
from ..unifi_client import UniFiClient


class GetUptimeTool(BaseTool):
    """Get uptime for all devices."""
    
    name = "unifi_get_uptime"
    description = "Get uptime statistics for all network devices"
    category = "monitoring"
    
    input_schema = {
        "type": "object",
        "properties": {
            "sort_by": {
                "type": "string",
                "enum": ["uptime", "name"],
                "default": "uptime"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Get device uptime."""
        sort_by = kwargs.get("sort_by", "uptime")
        
        # Get devices
        response = await unifi_client.get(
            f"/api/s/{unifi_client.site}/stat/device"
        )
        
        devices = response.get("data", [])
        
        # Extract uptime info
        uptime_data = [
            {
                "name": device.get("name", "Unknown"),
                "type": device.get("type", "Unknown"),
                "uptime": device.get("uptime", 0),
                "uptime_hours": device.get("uptime", 0) / 3600
            }
            for device in devices
        ]
        
        # Sort
        if sort_by == "uptime":
            uptime_data.sort(key=lambda x: x["uptime"])
        else:
            uptime_data.sort(key=lambda x: x["name"])
        
        return self.format_list(uptime_data)


class GetBandwidthTool(BaseTool):
    """Get bandwidth usage for all devices."""
    
    name = "unifi_get_bandwidth"
    description = "Get bandwidth usage statistics"
    category = "monitoring"
    
    input_schema = {
        "type": "object",
        "properties": {
            "time_range": {
                "type": "string",
                "enum": ["1h", "24h", "7d"],
                "default": "1h"
            }
        }
    }
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Get bandwidth usage."""
        time_range = kwargs.get("time_range", "1h")
        
        # Implementation here
        # ...
        
        return self.format_success(data={})
```

### Step 2: Register Category

Update `server.py` to register all tools in the category:

```python
from .tools.monitoring import (
    GetUptimeTool,
    GetBandwidthTool,
)

tools_to_register = [
    # ... existing tools ...
    GetUptimeTool(),
    GetBandwidthTool(),
]
```

### Step 3: Add Category Configuration

Update `config.yaml`:

```yaml
tools:
  monitoring:
    enabled: true
    tools:
      - get_uptime
      - get_bandwidth
```

## Extending the UniFi Client

### Adding New API Methods

Extend the UniFi client with new methods:

```python
# src/unifi_mcp/unifi_client.py

class UniFiClient:
    # ... existing methods ...
    
    async def get_port_profiles(self) -> List[Dict[str, Any]]:
        """Get all port profiles.
        
        Returns:
            List of port profile configurations
        """
        response = await self.get(
            f"/api/s/{self.site}/rest/portconf"
        )
        return response.get("data", [])
    
    async def get_network_settings(self) -> Dict[str, Any]:
        """Get network settings.
        
        Returns:
            Network configuration
        """
        response = await self.get(
            f"/api/s/{self.site}/rest/setting/network"
        )
        return response.get("data", {})
    
    async def update_device_name(
        self,
        device_id: str,
        new_name: str
    ) -> Dict[str, Any]:
        """Update device name.
        
        Args:
            device_id: Device ID
            new_name: New device name
        
        Returns:
            Updated device data
        """
        response = await self.post(
            f"/api/s/{self.site}/rest/device/{device_id}",
            data={"name": new_name}
        )
        return response.get("data", {})
```

### Custom Caching Strategy

Implement custom caching for specific endpoints:

```python
async def get_with_custom_cache(
    self,
    endpoint: str,
    ttl: int = 60
) -> Dict[str, Any]:
    """Get with custom TTL.
    
    Args:
        endpoint: API endpoint
        ttl: Cache TTL in seconds
    
    Returns:
        API response data
    """
    cache_key = f"{endpoint}"
    
    # Check cache
    if cache_key in self.cache:
        return self.cache[cache_key]
    
    # Make request
    response = await self.get(endpoint)
    
    # Cache with custom TTL
    self.cache[cache_key] = response
    
    # Schedule cache invalidation
    asyncio.create_task(self._invalidate_after(cache_key, ttl))
    
    return response

async def _invalidate_after(self, key: str, ttl: int):
    """Invalidate cache key after TTL."""
    await asyncio.sleep(ttl)
    if key in self.cache:
        del self.cache[key]
```

## Custom Output Formatters

### Creating Formatters

Create custom formatters for specific data types:

```python
# src/unifi_mcp/tools/formatters.py

from typing import Any, Dict, List


def format_device_summary(device: Dict[str, Any]) -> Dict[str, Any]:
    """Format device data for summary view.
    
    Args:
        device: Raw device data from UniFi API
    
    Returns:
        Formatted device summary
    """
    return {
        "id": device.get("_id"),
        "name": device.get("name", "Unknown"),
        "model": device.get("model", "Unknown"),
        "type": device.get("type", "Unknown"),
        "ip": device.get("ip", "Unknown"),
        "mac": device.get("mac", "Unknown"),
        "status": "online" if device.get("state") == 1 else "offline",
        "uptime_hours": round(device.get("uptime", 0) / 3600, 2),
        "version": device.get("version", "Unknown")
    }


def format_client_summary(client: Dict[str, Any]) -> Dict[str, Any]:
    """Format client data for summary view."""
    return {
        "mac": client.get("mac"),
        "name": client.get("name") or client.get("hostname", "Unknown"),
        "ip": client.get("ip", "Unknown"),
        "network": client.get("network", "Unknown"),
        "connection": "wireless" if client.get("is_wired") == False else "wired",
        "signal": client.get("signal"),
        "uptime_hours": round(client.get("uptime", 0) / 3600, 2)
    }


def format_bandwidth(bytes_value: int) -> str:
    """Format bytes as human-readable bandwidth.
    
    Args:
        bytes_value: Bytes value
    
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(bytes_value)
    unit_index = 0
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    return f"{value:.2f} {units[unit_index]}"
```

### Using Formatters in Tools

```python
from .formatters import format_device_summary, format_bandwidth


class ListDevicesWithFormatterTool(BaseTool):
    """List devices with custom formatting."""
    
    name = "unifi_list_devices_formatted"
    description = "List devices with enhanced formatting"
    category = "network_discovery"
    
    input_schema = {"type": "object", "properties": {}}
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute with custom formatting."""
        response = await unifi_client.get(
            f"/api/s/{unifi_client.site}/stat/device"
        )
        
        devices = response.get("data", [])
        
        # Apply custom formatter
        formatted_devices = [
            format_device_summary(device)
            for device in devices
        ]
        
        return self.format_list(formatted_devices)
```

## Adding Configuration Options

### Step 1: Update Config Schema

Add new configuration options to `config.yaml`:

```yaml
server:
  # ... existing config ...
  
  custom_features:
    enable_advanced_monitoring: false
    monitoring_interval: 60
    alert_thresholds:
      cpu_percent: 80
      memory_percent: 90
      disk_percent: 85
```

### Step 2: Update Config Loader

Update `config/loader.py` to handle new config:

```python
@dataclass
class CustomFeaturesConfig:
    """Custom features configuration."""
    enable_advanced_monitoring: bool
    monitoring_interval: int
    alert_thresholds: Dict[str, int]


@dataclass
class ServerConfig:
    """Server configuration."""
    # ... existing fields ...
    custom_features: CustomFeaturesConfig


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration."""
    # ... existing loading logic ...
    
    # Parse custom features
    custom_features_data = server_data.get("custom_features", {})
    custom_features = CustomFeaturesConfig(
        enable_advanced_monitoring=custom_features_data.get(
            "enable_advanced_monitoring", False
        ),
        monitoring_interval=custom_features_data.get(
            "monitoring_interval", 60
        ),
        alert_thresholds=custom_features_data.get(
            "alert_thresholds", {}
        )
    )
    
    server_config.custom_features = custom_features
    
    return config
```

### Step 3: Use Configuration

Access configuration in your tools:

```python
class AdvancedMonitoringTool(BaseTool):
    """Advanced monitoring tool."""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute with config."""
        if not self.config.server.custom_features.enable_advanced_monitoring:
            return self.format_error(
                code="FEATURE_DISABLED",
                message="Advanced monitoring is disabled",
                actionable_steps=[
                    "Enable in config.yaml: custom_features.enable_advanced_monitoring = true"
                ]
            )
        
        interval = self.config.server.custom_features.monitoring_interval
        thresholds = self.config.server.custom_features.alert_thresholds
        
        # Use configuration
        # ...
        
        return self.format_success(data={})
```

## Custom Logging

### Adding Custom Log Fields

Extend logging with custom fields:

```python
# src/unifi_mcp/utils/logging.py

def log_tool_performance(
    tool_name: str,
    duration_ms: float,
    cache_hit: bool = False
):
    """Log tool performance metrics.
    
    Args:
        tool_name: Name of the tool
        duration_ms: Execution duration in milliseconds
        cache_hit: Whether result was from cache
    """
    logger = get_logger(__name__)
    logger.info(
        f"Tool performance: {tool_name}",
        extra={
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "cache_hit": cache_hit,
            "metric_type": "performance"
        }
    )
```

### Using Custom Logging

```python
import time
from ..utils.logging import log_tool_performance


class PerformanceTrackedTool(BaseTool):
    """Tool with performance tracking."""
    
    async def execute(
        self,
        unifi_client: UniFiClient,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute with performance tracking."""
        start_time = time.time()
        
        # Execute tool logic
        result = await self._do_work(unifi_client, **kwargs)
        
        # Log performance
        duration_ms = (time.time() - start_time) * 1000
        log_tool_performance(
            tool_name=self.name,
            duration_ms=duration_ms,
            cache_hit=False
        )
        
        return result
```

## Integration with Other Systems

### Prometheus Metrics (Future)

Add Prometheus metrics export:

```python
# src/unifi_mcp/metrics.py

from prometheus_client import Counter, Histogram, Gauge


# Define metrics
tool_invocations = Counter(
    'unifi_mcp_tool_invocations_total',
    'Total tool invocations',
    ['tool_name', 'status']
)

tool_duration = Histogram(
    'unifi_mcp_tool_duration_seconds',
    'Tool execution duration',
    ['tool_name']
)

cache_hits = Counter(
    'unifi_mcp_cache_hits_total',
    'Cache hits',
    ['endpoint']
)

active_sessions = Gauge(
    'unifi_mcp_active_sessions',
    'Number of active UniFi sessions'
)


def record_tool_invocation(tool_name: str, status: str, duration: float):
    """Record tool invocation metrics."""
    tool_invocations.labels(tool_name=tool_name, status=status).inc()
    tool_duration.labels(tool_name=tool_name).observe(duration)
```

### Webhook Notifications

Add webhook support for events:

```python
# src/unifi_mcp/webhooks.py

import aiohttp
from typing import Dict, Any


async def send_webhook(
    url: str,
    event_type: str,
    data: Dict[str, Any]
):
    """Send webhook notification.
    
    Args:
        url: Webhook URL
        event_type: Type of event
        data: Event data
    """
    payload = {
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                logger.warning(
                    f"Webhook failed: {response.status}",
                    extra={"url": url, "status": response.status}
                )
```

## Testing Your Extensions

### Unit Testing

```python
# tests/test_my_extension.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unifi_mcp.tools.my_tools import MyCustomTool


@pytest.fixture
def mock_unifi_client():
    """Create mock UniFi client."""
    client = AsyncMock()
    client.site = "default"
    return client


@pytest.mark.asyncio
async def test_custom_tool_success(mock_unifi_client):
    """Test successful tool execution."""
    # Setup
    tool = MyCustomTool()
    mock_unifi_client.get.return_value = {
        "data": [{"name": "test"}]
    }
    
    # Execute
    result = await tool.execute(
        mock_unifi_client,
        param1="test"
    )
    
    # Verify
    assert result["success"] is True
    mock_unifi_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_custom_tool_validation_error(mock_unifi_client):
    """Test validation error handling."""
    tool = MyCustomTool()
    
    # Execute with invalid params
    result = await tool.invoke(
        mock_unifi_client,
        {}  # Missing required param1
    )
    
    # Verify error
    assert "error" in result
    assert result["error"]["code"] == "VALIDATION_ERROR"
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_custom_tool_integration():
    """Test tool against real UniFi controller."""
    # Load config
    config = load_config()
    
    # Create client
    client = UniFiClient(config.unifi, {})
    await client.connect()
    
    try:
        # Create tool
        tool = MyCustomTool()
        
        # Execute
        result = await tool.execute(
            client,
            param1="test-device"
        )
        
        # Verify
        assert result["success"] is True
        assert "data" in result
    
    finally:
        await client.disconnect()
```

### Manual Testing with Dev Console

```python
# examples/test_my_tool.py

import asyncio
from unifi_mcp.config import load_config
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.tools.my_tools import MyCustomTool


async def main():
    """Test custom tool manually."""
    # Load config
    config = load_config()
    
    # Create client
    client = UniFiClient(config.unifi, {})
    await client.connect()
    
    try:
        # Create and execute tool
        tool = MyCustomTool()
        result = await tool.execute(
            client,
            param1="test-device",
            param2=10
        )
        
        # Print result
        print(json.dumps(result, indent=2))
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
python examples/test_my_tool.py
```

## Best Practices

### Tool Design

1. **Keep Tools Focused**: One tool, one purpose
2. **Clear Descriptions**: Under 200 characters, describe what not how
3. **Simple Schemas**: Flat structures, avoid deep nesting
4. **Sensible Defaults**: Provide defaults for optional parameters
5. **Consistent Naming**: Use `unifi_` prefix, descriptive names

### Error Handling

1. **Use ToolError**: Structured error responses
2. **Actionable Messages**: Tell users how to fix
3. **No Credential Exposure**: Never include credentials in errors
4. **Log Errors**: Use structured logging

### Performance

1. **Use Caching**: Cache frequently accessed data
2. **Paginate Results**: Don't return huge datasets
3. **Async All The Way**: Use async/await throughout
4. **Limit Concurrent Requests**: Respect controller limits

### Security

1. **Validate Inputs**: Always validate against schema
2. **Require Confirmation**: For write operations
3. **Log Write Operations**: Audit trail for changes
4. **Redact Sensitive Data**: In logs and responses

### Testing

1. **Unit Test Everything**: Mock external dependencies
2. **Integration Test Critical Paths**: Test against real controller
3. **Test Error Cases**: Not just happy path
4. **Use Fixtures**: Reusable test data and mocks

## Examples

### Complete Tool Example

See `src/unifi_mcp/tools/network_discovery.py` for complete examples of:
- List tools with filtering
- Detail tools with ID lookup
- Pagination support
- Error handling

### Complete Category Example

See `src/unifi_mcp/tools/security.py` for complete category with:
- Multiple related tools
- Consistent formatting
- Comprehensive error handling

### Write Operation Example

See `src/unifi_mcp/tools/write_operations.py` for:
- Confirmation requirement
- Write operation logging
- Rollback information

## Getting Help

### Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Security Documentation](SECURITY.md)
- [Configuration Guide](CONFIGURATION.md)
- [Tool Reference](ALL-TOOLS-REFERENCE.md)

### Community

- GitHub Issues: Report bugs, request features
- GitHub Discussions: Ask questions, share extensions
- Pull Requests: Contribute your extensions

## Changelog

### Version 1.0.0 (October 2025)

- Initial extension guide
- Tool creation examples
- Testing guidelines
- Best practices

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Status**: Production Ready
