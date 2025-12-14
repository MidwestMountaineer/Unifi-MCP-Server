# UniFi MCP Server

MCP server for UniFi Network Controller - manage your network with AI assistants using natural language.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

**25 read-only tools** across 4 categories:

| Category | Tools | Examples |
|----------|-------|----------|
| Discovery | 8 | List devices, clients, networks, WLANs |
| Security | 7 | Firewall rules, IPS status, port forwards |
| Statistics | 7 | Network stats, top clients, DPI, alerts |
| Migration | 3 | DHCP status, VLAN connectivity, config export |

## Quick Start

### 1. Install

```bash
# Using uvx (recommended)
uvx --from git+https://github.com/MidwestMountaineer/Unifi-MCP-Server.git unifi-mcp-server

# Or pip
pip install git+https://github.com/MidwestMountaineer/Unifi-MCP-Server.git
```

### 2. Get API Key

1. Log into your Dream Machine
2. **Settings** → **System** → **Advanced** → **API**
3. Create new API key with **Read Only** permissions
4. Copy the key (shown only once)

### 3. Configure

Add to your MCP client config (e.g., `.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/MidwestMountaineer/Unifi-MCP-Server.git", "unifi-mcp-server"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your-api-key-here",
        "UNIFI_VERIFY_SSL": "false"
      }
    }
  }
}
```

### 4. Test

Ask your AI assistant: *"List all my UniFi devices"*

## Kiro Power

This repo is also a **Kiro Power** with guided workflows. Install via Kiro's "Add power from GitHub":

```
https://github.com/MidwestMountaineer/Unifi-MCP-Server
```

See [POWER.md](POWER.md) for workflow documentation.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `UNIFI_HOST` | Controller IP | (required) |
| `UNIFI_API_KEY` | API key | (required for UniFi OS) |
| `UNIFI_USERNAME` | Username | (for traditional controllers) |
| `UNIFI_PASSWORD` | Password | (for traditional controllers) |
| `UNIFI_PORT` | Controller port | `443` |
| `UNIFI_SITE` | Site name | `default` |
| `UNIFI_VERIFY_SSL` | Verify SSL | `false` |
| `LOG_LEVEL` | Log verbosity | `INFO` |

## Available Tools

### Discovery
- `unifi_list_devices` / `unifi_get_device_details`
- `unifi_list_clients` / `unifi_get_client_details`
- `unifi_list_networks` / `unifi_get_network_details`
- `unifi_list_wlans` / `unifi_get_wlan_details`

### Security
- `unifi_list_firewall_rules` / `unifi_get_firewall_rule_details`
- `unifi_list_traffic_routes` / `unifi_get_route_details`
- `unifi_list_port_forwards` / `unifi_get_port_forward_details`
- `unifi_get_ips_status`

### Statistics
- `unifi_get_network_stats` / `unifi_get_system_health`
- `unifi_get_client_stats` / `unifi_get_device_stats`
- `unifi_get_top_clients` / `unifi_get_dpi_stats`
- `unifi_get_alerts`

### Migration
- `unifi_get_dhcp_status`
- `unifi_verify_vlan_connectivity`
- `unifi_export_configuration`

## Docker

```bash
docker-compose up -d
```

See [docs/DOCKER.md](docs/DOCKER.md) for details.

## Development

```bash
# Clone and install
git clone https://github.com/MidwestMountaineer/Unifi-MCP-Server.git
cd Unifi-MCP-Server
pip install -e ".[dev]"

# Run tests
pytest

# Dev console
python devtools/dev_console.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check `UNIFI_HOST` and controller is reachable |
| 401 Unauthorized | Regenerate API key with correct permissions |
| SSL errors | Set `UNIFI_VERIFY_SSL=false` |
| Empty results | Check `UNIFI_SITE` name, upgrade API key to Full Management |

## License

MIT - See [LICENSE](LICENSE)
