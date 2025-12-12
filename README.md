# UniFi MCP Server

A Model Context Protocol (MCP) server for UniFi Network Controller, enabling AI agents to interact with UniFi network infrastructure through natural language.

**Status**: ✅ **Production Ready** - 25 Tools Available

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What is This?

The UniFi MCP Server bridges your UniFi Network Controller with AI assistants like **Kiro** and **Claude Desktop**, allowing you to manage and monitor your network using natural language.

**Ask questions like:**
- "List all devices on my network"
- "Show me firewall rules blocking IoT traffic"
- "Which clients are using the most bandwidth?"
- "What's the IPS status and recent alerts?"
- "Export my network configuration for backup"

**Get instant answers** without logging into the UniFi web interface!

---

## ✨ Features

### 🔍 Network Discovery (8 tools)
- List and inspect devices (switches, APs, gateways)
- Monitor connected clients (wired/wireless)
- View network and VLAN configurations
- Manage wireless networks (WLANs)

### 🔒 Security Management (7 tools)
- Review firewall rules and policies
- Check traffic routing rules
- Inspect port forwarding configuration
- Monitor IPS/IDS status and alerts

### 📊 Statistics & Monitoring (7 tools)
- Network and system health metrics
- Client and device statistics
- Top bandwidth consumers
- Deep packet inspection (DPI) data
- System alerts and events

### 🔧 Migration Support (3 tools)
- DHCP status and lease information
- VLAN connectivity verification
- Configuration export for backup

**Total: 25 production-ready tools** | All read-only and safe for AI agents

---

## 🚀 Quick Start

### System Requirements

- **Python**: 3.11 or higher
- **UniFi Controller**: UniFi OS (Dream Machine, Cloud Gateway) or traditional controller
- **Network Access**: Connectivity to your UniFi controller
- **Credentials**: Admin account or API key

### Installation

#### Option 1: Using pip (Recommended)

```bash
# Navigate to project directory
cd projects/unifi-mcp-server

# Install in editable mode
pip install -e .

# Verify installation
unifi-mcp-server --version
```

#### Option 2: Using uv (Faster)

```bash
# Install with uv
uv pip install -e .

# Or run directly with uvx
uvx --from . unifi-mcp-server
```

#### Option 3: Docker

```bash
# Using Docker Compose (Recommended)
docker-compose up -d

# Or using Docker directly
docker build -t unifi-mcp-server .
docker run -d --env-file .env unifi-mcp-server

# View logs
docker logs unifi-mcp-server
```

**See [Docker Deployment Guide](docs/DOCKER-DEPLOYMENT.md) for detailed instructions.**

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# UniFi Controller Connection
UNIFI_HOST=192.168.1.1          # Your controller IP address
UNIFI_PORT=443                   # HTTPS port (default: 443)
UNIFI_SITE=default              # Site name (usually "default")
UNIFI_VERIFY_SSL=false          # Set to false for self-signed certs

# Authentication Method 1: API Key (Recommended for UniFi OS)
UNIFI_API_KEY=your_api_key_here

# Authentication Method 2: Username/Password (Legacy)
UNIFI_USERNAME=your_username
UNIFI_PASSWORD=your_password

# Optional: Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

**Security Note**: Never commit `.env` to version control! It's already in `.gitignore`.

### Authentication Methods

#### API Key (Recommended for UniFi OS)

For UniFi OS devices (Dream Machine, Cloud Gateway, uNAS Pro):

1. Log into your UniFi OS web interface
2. Go to **Settings** → **System** → **Advanced**
3. Scroll to **API** section
4. Click **Create New API Key**
5. Name it (e.g., "Kiro MCP Server")
6. Copy the key and add to `.env` as `UNIFI_API_KEY`

**Benefits**: More secure, no password exposure, easier to revoke

#### Username/Password (Legacy Controllers)

For traditional UniFi Controllers (not UniFi OS):

1. Use your admin account credentials
2. Add to `.env` as `UNIFI_USERNAME` and `UNIFI_PASSWORD`

**Note**: API key authentication is preferred when available.

---

## 🔌 Integration with Kiro

### Setup Steps

1. **Install the package** (see Installation above)

2. **Configure authentication** (see Configuration above)

3. **Add to Kiro MCP configuration**

#### Workspace-Level Config (Recommended)

Edit `.kiro/settings/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_PORT": "443",
        "UNIFI_API_KEY": "your_api_key_here",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false",
        "LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "unifi_list_*",
        "unifi_get_*"
      ]
    }
  }
}
```

#### User-Level Config (Global)

Edit `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your_api_key_here",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false
    }
  }
}
```

4. **Restart or reconnect** the MCP server in Kiro

5. **Test it!** Try asking: "List all my UniFi devices"

### Using with uvx (Alternative)

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uvx",
      "args": ["--from", ".", "unifi-mcp-server"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

---

## 💬 Example Prompts

### Network Discovery
```
"List all devices on my network"
"Show me wireless clients"
"What's the status of my living room AP?"
"Which clients are connected to the IoT VLAN?"
"Show me all configured networks and VLANs"
"What wireless networks are configured?"
```

### Security Monitoring
```
"List all firewall rules"
"Show me firewall rules blocking IoT to Core traffic"
"What port forwards are configured?"
"What's the IPS status?"
"Show me recent IPS alerts"
"List all traffic routing rules"
```

### Performance Analysis
```
"Which clients are using the most bandwidth?"
"Show me network statistics"
"What's the system health status?"
"Get DPI statistics for application usage"
"Show me recent system alerts"
```

### Troubleshooting
```
"Why is device X offline?"
"What's the signal strength for my laptop?"
"Show me clients with poor signal"
"What's the uptime of my main switch?"
"Check DHCP status and leases"
```

### Configuration & Planning
```
"Export my network configuration for backup"
"Verify connectivity between IoT and Core VLANs"
"What security is used on the guest WiFi?"
"Show me all VLAN assignments"
"Get DHCP lease information"
```

---

## 🛠️ Available Tools

### Network Discovery (8 tools)

| Tool | Description |
|------|-------------|
| `unifi_list_devices` | List all UniFi devices with filtering |
| `unifi_get_device_details` | Get detailed device information |
| `unifi_list_clients` | List connected clients (wired/wireless) |
| `unifi_get_client_details` | Get detailed client information |
| `unifi_list_networks` | List all networks and VLANs |
| `unifi_get_network_details` | Get detailed network configuration |
| `unifi_list_wlans` | List wireless networks |
| `unifi_get_wlan_details` | Get detailed WLAN configuration |

### Security Tools (7 tools)

| Tool | Description |
|------|-------------|
| `unifi_list_firewall_rules` | List firewall rules with filtering |
| `unifi_get_firewall_rule_details` | Get detailed firewall rule info |
| `unifi_list_traffic_routes` | List traffic routing rules |
| `unifi_get_route_details` | Get detailed route information |
| `unifi_list_port_forwards` | List port forwarding rules |
| `unifi_get_port_forward_details` | Get detailed port forward info |
| `unifi_get_ips_status` | Get IPS/IDS status and alerts |

### Statistics Tools (7 tools)

| Tool | Description |
|------|-------------|
| `unifi_get_network_stats` | Get overall network statistics |
| `unifi_get_system_health` | Get system health metrics |
| `unifi_get_client_stats` | Get client bandwidth and performance |
| `unifi_get_device_stats` | Get device statistics |
| `unifi_get_top_clients` | List top bandwidth consumers |
| `unifi_get_dpi_stats` | Get deep packet inspection data |
| `unifi_get_alerts` | Get recent system alerts |

### Migration Tools (3 tools)

| Tool | Description |
|------|-------------|
| `unifi_get_dhcp_status` | Get DHCP server status and leases |
| `unifi_verify_vlan_connectivity` | Verify connectivity between VLANs |
| `unifi_export_configuration` | Export configuration for backup |

**See [docs/ALL-TOOLS-REFERENCE.md](docs/ALL-TOOLS-REFERENCE.md) for complete tool documentation.**

---

## 📁 Project Structure

```
projects/unifi-mcp-server/
├── src/
│   └── unifi_mcp/
│       ├── __init__.py
│       ├── __main__.py              # Entry point
│       ├── server.py                 # MCP server implementation
│       ├── unifi_client.py           # UniFi API client
│       ├── tool_registry.py          # Tool registration system
│       ├── config/
│       │   ├── config.yaml           # Default configuration
│       │   └── loader.py             # Config loading logic
│       ├── tools/
│       │   ├── base.py               # Base tool class
│       │   ├── network_discovery.py  # Device/client tools
│       │   ├── security.py           # Firewall/routing tools
│       │   ├── statistics.py         # Stats/monitoring tools
│       │   ├── migration.py          # Migration support tools
│       │   └── write_operations.py   # Write operation tools
│       └── utils/
│           ├── logging.py            # Logging with redaction
│           ├── validation.py         # Input validation
│           └── retry.py              # Retry logic
├── tests/                            # Comprehensive test suite
├── docs/                             # Documentation
├── examples/                         # Example scripts
├── devtools/                         # Development tools
├── .env.example                      # Example environment variables
├── .gitignore
├── pyproject.toml                    # Package configuration
├── LICENSE                           # MIT License
└── README.md                         # This file
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=unifi_mcp

# Run specific test file
pytest tests/test_network_discovery.py

# Run with verbose output
pytest -v
```

### Performance Profiling

```bash
# Run comprehensive performance profiler
python devtools/performance_profiler.py

# Run performance tests
pytest tests/test_performance.py -v
```

The profiler tests:
- ✅ Startup time (<5s target, actual: ~0.1s)
- ✅ Memory usage (<100MB target, actual: ~68MB)
- ✅ Response times (<2s target, actual: <0.02s)
- ✅ Concurrent requests (10+ target, actual: 10/10)

See `devtools/PERFORMANCE-PROFILER-GUIDE.md` for details.

### Manual Testing

#### Developer Console

```bash
# Interactive testing console
python devtools/dev_console.py

# List available tools
> list

# Invoke a tool
> invoke unifi_list_devices

# Get help
> help
```

#### MCP Inspector

```bash
# Validate MCP protocol compliance (PowerShell)
.\devtools\mcp_inspector.ps1

# Or bash
./devtools/mcp_inspector.sh
```

#### Example Scripts

```bash
# Run example demos
python examples/phase4_interactive_demo.py
python examples/security_demo.py
python examples/statistics_demo.py
```

---

## 🔒 Security

### Credential Protection
- ✅ Credentials stored in environment variables only
- ✅ All sensitive data redacted from logs
- ✅ API keys never exposed in responses
- ✅ `.env` file excluded from version control

### Read-Only Operations
- ✅ All 25 tools are read-only and safe
- ✅ No risk of accidental network changes
- ✅ Perfect for AI agent exploration

### Write Operations (Future)
- ⚠️ Write operations require explicit confirmation
- ⚠️ Safety framework with rollback support
- ⚠️ Comprehensive audit logging
- ⚠️ Disabled by default

### Network Security
- ✅ HTTPS by default
- ✅ SSL certificate validation (configurable)
- ✅ Support for self-signed certificates
- ✅ Connection and read timeouts

### Best Practices
- Use API key authentication when possible
- Create dedicated read-only accounts for production
- Enable audit logging for write operations
- Regularly rotate credentials
- Use proper SSL certificates in production

---

## 🐛 Troubleshooting

### Connection Issues

**Problem**: "Failed to connect to UniFi controller"

**Solutions**:
1. Verify `UNIFI_HOST` is correct
2. Check network connectivity: `ping 192.168.1.1`
3. Ensure controller is accessible on port 443
4. Set `UNIFI_VERIFY_SSL=false` for self-signed certs

### Authentication Issues

**Problem**: "Authentication failed"

**Solutions**:
1. Verify API key or username/password are correct
2. Check account has admin privileges
3. Test credentials in UniFi web UI
4. Ensure 2FA is not enabled (not supported yet)
5. Check if API key has expired

### Tool Not Found

**Problem**: "Tool 'unifi_xxx' not found"

**Solutions**:
1. Verify server is running in Kiro MCP Server view
2. Reconnect the MCP server
3. Check logs with `LOG_LEVEL=DEBUG`
4. Ensure package is installed: `pip list | grep unifi-mcp`

### No Data Returned

**Problem**: Tool returns empty results

**Solutions**:
1. Verify data exists in UniFi web UI
2. Check site name: `UNIFI_SITE=default`
3. Review logs for API errors
4. Test with dev console: `python devtools/dev_console.py`

### Performance Issues

**Problem**: Slow response times

**Solutions**:
1. Use list tools for overviews (faster)
2. Use detail tools only when needed
3. Enable caching (configured by default)
4. Check network latency to controller
5. Set `LOG_LEVEL=INFO` (not DEBUG)

---

## 📚 Documentation

### Core Documentation
- **[ALL-TOOLS-REFERENCE.md](docs/ALL-TOOLS-REFERENCE.md)** - Complete tool reference
- **[KIRO-SETUP-GUIDE.md](docs/KIRO-SETUP-GUIDE.md)** - Detailed Kiro integration guide
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** - Configuration options
- **[LEARNING.md](docs/LEARNING.md)** - Learning journey and insights

### Tool Guides
- **[QUICK-REFERENCE.md](docs/QUICK-REFERENCE.md)** - Quick reference for common tasks
- **[SECURITY-TOOLS-GUIDE.md](docs/SECURITY-TOOLS-GUIDE.md)** - Security tools usage
- **[STATISTICS-TOOLS-GUIDE.md](docs/STATISTICS-TOOLS-GUIDE.md)** - Statistics tools usage
- **[IPS-TOOL-GUIDE.md](docs/IPS-TOOL-GUIDE.md)** - IPS monitoring guide
- **[CLIENT-DEVICE-STATS-GUIDE.md](docs/CLIENT-DEVICE-STATS-GUIDE.md)** - Client/device stats
- **[DPI-ALERTS-GUIDE.md](docs/DPI-ALERTS-GUIDE.md)** - DPI and alerts guide

### Developer Documentation
- **[MCP-SERVER.md](docs/MCP-SERVER.md)** - MCP server architecture
- **[UNIFI-CLIENT.md](docs/UNIFI-CLIENT.md)** - UniFi API client details
- **[LOGGING.md](docs/LOGGING.md)** - Logging and diagnostics
- **[RETRY-LOGIC.md](docs/RETRY-LOGIC.md)** - Retry and error handling

### Testing Documentation
- **[MCP-INSPECTOR-GUIDE.md](docs/MCP-INSPECTOR-GUIDE.md)** - Protocol validation
- **[DEV-CONSOLE-QUICK-START.md](docs/DEV-CONSOLE-QUICK-START.md)** - Developer console

---

## 🗺️ Roadmap

### ✅ Phase 1-7: Core Functionality (Complete)
- [x] Project structure and configuration
- [x] MCP server implementation
- [x] UniFi API client with authentication
- [x] Retry logic and error handling
- [x] Caching layer
- [x] Network discovery tools (8 tools)
- [x] Security tools (7 tools)
- [x] Statistics tools (7 tools)
- [x] Migration support tools (3 tools)

### 🚧 Phase 8: Write Operations (In Progress)
- [x] Write operation safety framework
- [x] Confirmation requirements
- [x] Audit logging
- [ ] Additional write operation tools

### 📋 Phase 9-12: Production Ready (Planned)
- [ ] Comprehensive documentation
- [ ] Docker deployment
- [ ] Performance optimization
- [ ] PyPI publication
- [ ] Advanced monitoring features

### 🔮 Future Enhancements
- Real-time event streaming
- Automated remediation tools
- Advanced analytics and reporting
- Bulk operation tools
- Multi-site support
- Webhook integrations

---

## 🤝 Contributing

This is a personal learning project, but feedback and suggestions are welcome!

### How to Contribute
1. Report bugs or issues
2. Suggest new features or tools
3. Improve documentation
4. Share your use cases

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd projects/unifi-mcp-server

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **MCP Protocol**: [Model Context Protocol](https://modelcontextprotocol.io/)
- **UniFi API**: [Ubiquiti UniFi Controller API](https://ubntwiki.com/products/software/unifi-controller/api)
- **Reference Implementation**: [sirkirby/unifi-network-mcp](https://github.com/sirkirby/unifi-network-mcp)
- **Kiro IDE**: AI-powered development environment

---

## 📞 Support

### Documentation
- Check the [docs/](docs/) directory for detailed guides
- Review [examples/](examples/) for code samples
- See [LEARNING.md](docs/LEARNING.md) for insights and gotchas

### Troubleshooting
- Enable debug logging: `LOG_LEVEL=DEBUG`
- Test with dev console: `python devtools/dev_console.py`
- Validate with MCP Inspector: `.\devtools\mcp_inspector.ps1`

### Community
- UniFi Community Forums
- r/homelab on Reddit
- r/selfhosted on Reddit

---

## 🎓 Learning Resources

### MCP Development
- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io/)

### UniFi API
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)
- [UniFi Community](https://community.ui.com/)

### Project Documentation
- [LEARNING.md](docs/LEARNING.md) - Lessons learned building this MCP server
- [Design Document](.kiro/specs/unifi-mcp-server/design.md) - Architecture and design decisions
- [Requirements](.kiro/specs/unifi-mcp-server/requirements.md) - Project requirements

---

**Built with ❤️ for the homelab community**

**Status**: Production Ready | **Tools**: 25 | **Test Coverage**: 80%+ | **Python**: 3.11+

---

**Quick Links**:
- [Installation](#-quick-start)
- [Configuration](#️-configuration)
- [Kiro Integration](#-integration-with-kiro)
- [Example Prompts](#-example-prompts)
- [All Tools](#️-available-tools)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)
