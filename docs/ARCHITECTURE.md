# Architecture Documentation

## Overview

The UniFi MCP Server is a Python-based Model Context Protocol (MCP) server that provides AI agents with secure, structured access to UniFi Network Controller capabilities. This document describes the system architecture, component interactions, design patterns, and technical decisions.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                            │
│                    (Kiro, Claude Desktop)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ stdio (JSON-RPC)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   UniFi MCP Server                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MCP Protocol Layer                       │   │
│  │  - Tool Registration                                  │   │
│  │  - Request/Response Handling                          │   │
│  │  - Error Formatting                                   │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │              Tool Handler Layer                       │   │
│  │  - Input Validation                                   │   │
│  │  - Authorization Checks                               │   │
│  │  - Result Formatting                                  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │           UniFi API Client Layer                      │   │
│  │  - Authentication                                     │   │
│  │  - Session Management                                 │   │
│  │  - HTTP Request/Response                              │   │
│  │  - Rate Limiting                                      │   │
│  │  - Caching                                            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │         Configuration & Logging Layer                 │   │
│  │  - Config Loading (YAML + env vars)                   │   │
│  │  - Credential Management                              │   │
│  │  - Structured Logging                                 │   │
│  │  - Diagnostics                                        │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              UniFi Network Controller                        │
│              (192.168.1.1 or 192.168.40.1)                   │
└──────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      src/unifi_mcp/                          │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  __main__.py │──│  server.py   │──│tool_registry │      │
│  │  (entry)     │  │  (MCP core)  │  │    .py       │      │
│  └──────────────┘  └──────┬───────┘  └──────┬───────┘      │
│                            │                  │              │
│                            │                  │              │
│  ┌─────────────────────────▼──────────────────▼──────────┐  │
│  │                    tools/                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │  │
│  │  │   base.py    │  │  network_    │  │  security.  │ │  │
│  │  │  (abstract)  │  │  discovery.  │  │     py      │ │  │
│  │  └──────────────┘  │     py       │  └─────────────┘ │  │
│  │                    └──────────────┘                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │  │
│  │  │ statistics.  │  │  migration.  │  │   write_    │ │  │
│  │  │     py       │  │     py       │  │ operations. │ │  │
│  │  └──────────────┘  └──────────────┘  │     py      │ │  │
│  │                                       └─────────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                  │
│  ┌─────────────────────────▼──────────────────────────────┐  │
│  │              unifi_client.py                            │  │
│  │  - Authentication & Session Management                  │  │
│  │  - HTTP Client (aiohttp)                                │  │
│  │  - Caching (TTLCache)                                   │  │
│  │  - Retry Logic                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            │                                  │
│  ┌─────────────────────────▼──────────────────────────────┐  │
│  │                    config/                              │  │
│  │  ┌──────────────┐  ┌──────────────┐                    │  │
│  │  │  loader.py   │  │ config.yaml  │                    │  │
│  │  │  (loading)   │  │  (defaults)  │                    │  │
│  │  └──────────────┘  └──────────────┘                    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            │                                  │
│  ┌─────────────────────────▼──────────────────────────────┐  │
│  │                    utils/                               │  │
│  │  ┌──────────────┐  ┌──────────────┐                    │  │
│  │  │  logging.py  │  │   retry.py   │                    │  │
│  │  │  (redaction) │  │  (backoff)   │                    │  │
│  │  └──────────────┘  └──────────────┘                    │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Protocol Layer

**File**: `src/unifi_mcp/server.py`

**Responsibilities**:
- Implements MCP protocol using official Python SDK
- Handles stdio transport (JSON-RPC over stdin/stdout)
- Registers tools and provides tool discovery
- Routes tool invocations to handlers
- Formats responses according to MCP specification

**Key Classes**:
- `UniFiMCPServer`: Main server class that orchestrates all components

**Design Patterns**:
- **Facade Pattern**: Provides simplified interface to complex subsystems
- **Decorator Pattern**: Uses SDK decorators for handler registration

**Key Methods**:
```python
async def run() -> None
    """Start MCP server with stdio transport"""

@server.list_tools()
async def list_tools() -> List[Tool]
    """Handle tools/list requests"""

@server.call_tool()
async def call_tool(name: str, arguments: Dict) -> List[TextContent]
    """Handle tools/call requests"""
```

### 2. Tool Registry

**File**: `src/unifi_mcp/tool_registry.py`

**Responsibilities**:
- Maintains registry of available tools
- Filters tools based on configuration (enabled/disabled)
- Routes tool invocations to appropriate handlers
- Provides tool metadata for discovery

**Key Classes**:
- `ToolRegistry`: Central registry for all tools

**Design Patterns**:
- **Registry Pattern**: Central repository for tool definitions
- **Strategy Pattern**: Different tool implementations with common interface

**Key Methods**:
```python
def register_tool(name, description, input_schema, handler, ...)
    """Register a tool with the registry"""

def get_tool_list() -> List[Tool]
    """Get list of enabled tools"""

async def invoke(name, unifi_client, arguments) -> Any
    """Invoke a tool by name"""
```

### 3. Tool Handler Layer

**File**: `src/unifi_mcp/tools/base.py`

**Responsibilities**:
- Defines abstract base class for all tools
- Validates input parameters against JSON schema
- Enforces confirmation requirements for write operations
- Formats output for AI consumption
- Provides error handling and formatting

**Key Classes**:
- `BaseTool`: Abstract base class for all tools
- `ToolError`: Structured error response

**Design Patterns**:
- **Template Method Pattern**: Base class defines algorithm structure
- **Factory Method Pattern**: Subclasses implement specific tool logic

**Key Methods**:
```python
async def execute(unifi_client, **kwargs) -> Any
    """Execute tool logic (implemented by subclasses)"""

def validate_input(arguments) -> None
    """Validate input against JSON schema"""

async def invoke(unifi_client, arguments) -> Any
    """Full invocation lifecycle with validation"""
```

### 4. Tool Implementations

**Files**: `src/unifi_mcp/tools/*.py`

**Categories**:
1. **Network Discovery** (`network_discovery.py`): 8 tools
   - List/get devices, clients, networks, WLANs
   
2. **Security** (`security.py`): 7 tools
   - List/get firewall rules, routes, port forwards, IPS status
   
3. **Statistics** (`statistics.py`): 7 tools
   - Network stats, client/device stats, top clients, DPI, alerts
   
4. **Migration** (`migration.py`): 3 tools
   - DHCP status, VLAN connectivity, configuration export
   
5. **Write Operations** (`write_operations.py`): 3 tools
   - Toggle/create/update firewall rules (requires confirmation)

**Design Patterns**:
- **Command Pattern**: Each tool encapsulates a request as an object
- **Chain of Responsibility**: Validation → Authorization → Execution

### 5. UniFi API Client

**File**: `src/unifi_mcp/unifi_client.py`

**Responsibilities**:
- Manages authentication and session cookies
- Makes HTTP/HTTPS requests to UniFi controller
- Handles SSL certificate validation
- Implements retry logic with exponential backoff
- Caches frequently accessed data
- Rate limits requests

**Key Classes**:
- `UniFiClient`: HTTP client for UniFi controller API

**Design Patterns**:
- **Singleton Pattern**: Single client instance per server
- **Proxy Pattern**: Wraps UniFi API with caching and retry logic
- **Decorator Pattern**: Adds caching and retry to HTTP requests

**Key Methods**:
```python
async def connect() -> None
    """Authenticate and establish session"""

async def get(endpoint, params=None) -> Dict
    """Make GET request with caching"""

async def post(endpoint, data) -> Dict
    """Make POST request with retry"""
```

**Caching Strategy**:
- TTL-based cache (default 30 seconds)
- Cache key: `endpoint + params`
- Invalidation on write operations
- Configurable TTL per endpoint type

**Retry Strategy**:
- Exponential backoff (factor: 2.0)
- Max attempts: 3
- Max backoff: 30 seconds
- Retryable errors: timeout, rate limit, temporary server errors
- Non-retryable: authentication, validation, not found

### 6. Configuration System

**Files**: 
- `src/unifi_mcp/config/loader.py`
- `src/unifi_mcp/config/config.yaml`

**Responsibilities**:
- Loads configuration from YAML and environment variables
- Validates required fields (fail-fast)
- Converts types (strings to booleans, integers, floats)
- Provides structured configuration object

**Key Classes**:
- `Config`: Structured configuration object
- `ConfigurationError`: Configuration validation errors

**Design Patterns**:
- **Builder Pattern**: Constructs complex configuration object
- **Strategy Pattern**: Multiple configuration sources (YAML, env vars)

**Configuration Hierarchy**:
```
1. YAML defaults (config.yaml)
2. Environment variable overrides (${VAR_NAME})
3. Runtime validation
4. Structured Config object
```

### 7. Logging System

**File**: `src/unifi_mcp/utils/logging.py`

**Responsibilities**:
- Structured logging with JSON format
- Sensitive data redaction (passwords, tokens, API keys)
- Correlation ID generation and tracking
- Configurable log levels
- Optional file logging

**Key Functions**:
- `get_logger(name)`: Get logger instance
- `redact_sensitive_data(data)`: Redact sensitive fields
- `setup_logging(config)`: Configure logging system

**Design Patterns**:
- **Decorator Pattern**: Wraps standard logging with redaction
- **Singleton Pattern**: Single logging configuration

**Redacted Fields**:
- `password`, `passwd`, `pwd`
- `token`, `api_key`, `secret`
- `authorization`, `x-auth-token`
- `cookie`, `session`

### 8. Retry Logic

**File**: `src/unifi_mcp/utils/retry.py`

**Responsibilities**:
- Exponential backoff calculation
- Retry decision logic
- Timeout handling

**Key Functions**:
- `calculate_backoff(attempt, factor, max_backoff)`: Calculate delay
- `should_retry(error, attempt, max_attempts)`: Retry decision

**Design Patterns**:
- **Strategy Pattern**: Different retry strategies for different errors

## Data Flow

### Tool Invocation Flow

```
1. MCP Client sends tools/call request
   ↓
2. Server.call_tool() receives request
   ↓
3. ToolRegistry.invoke() routes to handler
   ↓
4. BaseTool.invoke() validates input
   ↓
5. BaseTool.execute() performs operation
   ↓
6. UniFiClient makes API request
   ↓
7. Response cached (if applicable)
   ↓
8. Result formatted for AI consumption
   ↓
9. Response returned to MCP client
```

### Authentication Flow

```
1. Server starts
   ↓
2. UniFiClient.connect() called
   ↓
3. POST /api/login with credentials
   ↓
4. Session cookie stored
   ↓
5. Cookie included in subsequent requests
   ↓
6. On 401 error: re-authenticate once
   ↓
7. On success: continue with new session
```

### Caching Flow

```
1. Tool requests data via UniFiClient.get()
   ↓
2. Generate cache key (endpoint + params)
   ↓
3. Check cache for key
   ↓
4. If hit: return cached data
   ↓
5. If miss: make API request
   ↓
6. Store result in cache with TTL
   ↓
7. Return data to tool
```

## Design Decisions

### 1. Why Python?

**Decision**: Use Python 3.10+ for implementation

**Rationale**:
- Official MCP SDK available for Python
- Rich ecosystem for HTTP clients (aiohttp)
- Excellent async/await support
- Easy to read and maintain
- Good for learning and iteration

**Trade-offs**:
- Slower than compiled languages
- Higher memory usage than Go/Rust
- Acceptable for homelab use case

### 2. Why stdio Transport?

**Decision**: Use stdio (stdin/stdout) for MCP communication

**Rationale**:
- Standard MCP transport mechanism
- Works with all MCP clients (Kiro, Claude Desktop)
- Simple process model (no network ports)
- Easy to debug with MCP Inspector

**Trade-offs**:
- Single client per server instance
- No network-based access
- Acceptable for local AI assistant use case

### 3. Why Hybrid Configuration?

**Decision**: YAML for structure, environment variables for secrets

**Rationale**:
- YAML provides readable structure
- Environment variables keep secrets out of version control
- Follows 12-factor app principles
- Easy to deploy in different environments

**Trade-offs**:
- More complex than single source
- Requires documentation
- Worth it for security

### 4. Why TTL-based Caching?

**Decision**: Use TTL cache with 30-second default

**Rationale**:
- Reduces load on UniFi controller
- Improves response time for repeated queries
- Simple to implement and understand
- 30 seconds balances freshness vs performance

**Trade-offs**:
- Stale data possible (up to TTL)
- Memory usage for cache
- Acceptable for homelab monitoring

### 5. Why Confirmation for Write Operations?

**Decision**: Require explicit `confirm=true` for write operations

**Rationale**:
- Prevents accidental network changes by AI
- Provides clear audit trail
- Forces intentional action
- Aligns with security-first approach

**Trade-offs**:
- Extra step for legitimate changes
- Worth it for safety

### 6. Why Separate Tool Files?

**Decision**: Organize tools by category in separate files

**Rationale**:
- Easier to navigate and maintain
- Clear separation of concerns
- Supports selective tool loading
- Follows single responsibility principle

**Trade-offs**:
- More files to manage
- Worth it for organization

## Performance Characteristics

### Memory Usage

- **Idle**: ~50-70MB (Python runtime + dependencies)
- **Active**: ~80-100MB (with cache and active requests)
- **Target**: <100MB idle

### Response Times

- **Cached requests**: <100ms
- **Uncached requests**: 200ms - 2s (depends on UniFi controller)
- **Target**: <2s for read operations

### Concurrency

- **Max concurrent requests**: 10 (configurable)
- **Connection pooling**: Yes (aiohttp)
- **Keep-alive**: Yes

### Caching

- **Cache size**: 100 entries (configurable)
- **Default TTL**: 30 seconds
- **Cache hit rate**: ~70-80% for typical usage

## Scalability Considerations

### Current Limitations

1. **Single UniFi Controller**: Only supports one controller per instance
2. **Single Client**: stdio transport supports one MCP client
3. **No Horizontal Scaling**: Single process model
4. **Memory-based Cache**: Lost on restart

### Future Enhancements

1. **Multiple Controllers**: Support multiple UniFi controllers
2. **Persistent Cache**: Redis or file-based cache
3. **HTTP Transport**: Support network-based MCP clients
4. **Metrics**: Prometheus metrics for monitoring
5. **Rate Limiting**: Per-client rate limiting

## Testing Architecture

### Test Structure

```
tests/
├── test_config.py              # Configuration loading
├── test_logging.py             # Logging and redaction
├── test_retry.py               # Retry logic
├── test_unifi_client.py        # API client
├── test_base_tool.py           # Base tool class
├── test_tool_registry.py       # Tool registry
├── test_server.py              # MCP server
├── test_network_discovery.py   # Network tools
├── test_security_tools.py      # Security tools
├── test_statistics_tools.py    # Statistics tools
├── test_migration_tools.py     # Migration tools
├── test_write_operations.py    # Write operations
└── test_integration.py         # End-to-end tests
```

### Test Patterns

1. **Unit Tests**: Mock UniFi API responses
2. **Integration Tests**: Test against real/mock controller
3. **Protocol Tests**: Validate MCP compliance with Inspector
4. **Performance Tests**: Measure response times and memory

### Test Coverage

- **Target**: 80%+ for core functionality
- **Current**: ~85% (as of October 2025)
- **Focus**: Critical paths and error handling

## Deployment Architecture

### Development

```
Developer Machine
├── Python 3.10+ environment
├── .env file with credentials
├── Direct execution: python -m unifi_mcp
└── MCP Inspector for testing
```

### Production (Kiro)

```
Kiro IDE
├── mcp.json configuration
├── uvx package runner
├── Environment variables from system
└── stdio communication
```

### Docker (Future)

```
Docker Container
├── Python runtime
├── Application code
├── Environment variables from host
└── Volume mount for logs
```

## Security Architecture

See [SECURITY.md](SECURITY.md) for detailed security documentation.

### Security Layers

1. **Credential Management**: Environment variables, never logged
2. **Input Validation**: JSON schema validation for all inputs
3. **Authorization**: Confirmation required for write operations
4. **Logging**: Sensitive data redaction
5. **Network**: HTTPS with optional SSL verification
6. **Error Handling**: No credential exposure in errors

## Monitoring and Observability

### Logging

- **Structured logging**: JSON format with context
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Track requests through system
- **Sensitive data redaction**: Automatic

### Metrics (Future)

- Tool invocation counts
- Response times (p50, p95, p99)
- Error rates
- Cache hit rates
- UniFi API call counts

### Tracing (Future)

- Distributed tracing with OpenTelemetry
- Request flow visualization
- Performance bottleneck identification

## Extension Points

See [EXTENDING.md](EXTENDING.md) for detailed extension guide.

### Adding New Tools

1. Create tool class inheriting from `BaseTool`
2. Define name, description, input_schema
3. Implement `execute()` method
4. Register in `server.py`

### Adding New Tool Categories

1. Create new file in `tools/` directory
2. Define tool classes
3. Add category to configuration
4. Register tools in server

### Custom Transports (Future)

1. Implement transport interface
2. Register with MCP server
3. Configure in server initialization

## References

### Internal Documentation

- [Configuration Guide](CONFIGURATION.md)
- [Security Documentation](SECURITY.md)
- [Extension Guide](EXTENDING.md)
- [Learning Journey](LEARNING.md)
- [Tool Reference](ALL-TOOLS-REFERENCE.md)

### External Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [UniFi Controller API](https://ubntwiki.com/products/software/unifi-controller/api)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

## Changelog

### Version 1.0.0 (October 2025)

- Initial architecture implementation
- 25 read-only tools
- 3 write operation tools
- MCP protocol compliance
- Comprehensive testing
- Production-ready release

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Status**: Production Ready
