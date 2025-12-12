# Dev Console Quick Start Guide

## What is the Dev Console?

The dev console is an interactive command-line tool for testing UniFi MCP Server tools without needing a full MCP client like Kiro or Claude Desktop.

## Quick Start

### 1. Setup

Make sure you have a `.env` file with your credentials:

```bash
UNIFI_HOST=192.168.1.1
UNIFI_API_KEY=your_api_key_here
```

### 2. Start the Console

```bash
python -m devtools.dev_console
```

### 3. Try Some Commands

```
# List all available tools
> list

# List tools in a category
> list network_discovery

# Show all categories
> categories

# Invoke a simple tool
> invoke unifi_list_devices

# Invoke with arguments
> invoke unifi_list_devices {"device_type": "switch"}

# Get help
> help

# Exit
> exit
```

## Common Use Cases

### Explore Available Tools

```
> list
> categories
> list security
```

### Test Network Discovery

```
# List all devices
> invoke unifi_list_devices

# List only switches
> invoke unifi_list_devices {"device_type": "switch"}

# Get device details
> invoke unifi_get_device_details {"device_id": "abc123"}

# List wireless clients
> invoke unifi_list_clients {"connection_type": "wireless"}
```

### Check Network Statistics

```
# Overall network stats
> invoke unifi_get_network_stats

# System health
> invoke unifi_get_system_health

# Top bandwidth users
> invoke unifi_get_top_clients {"limit": 5}
```

### View Security Configuration

```
# List firewall rules
> invoke unifi_list_firewall_rules

# List only enabled rules
> invoke unifi_list_firewall_rules {"enabled_only": true}

# Get rule details
> invoke unifi_get_firewall_rule_details {"rule_id": "abc123"}
```

### Test Write Operations

**Note**: Write operations require `confirm: true` and must be enabled in config.

```
# Toggle a firewall rule (requires confirmation)
> invoke unifi_toggle_firewall_rule {"rule_id": "abc123", "enabled": false, "confirm": true}
```

## Tips

1. **Copy/Paste Tool Names**: Use `list` to see tool names, then copy/paste them into `invoke` commands

2. **JSON Format**: Arguments must be valid JSON with double quotes:
   - ✅ Good: `{"device_type": "switch"}`
   - ❌ Bad: `{device_type: 'switch'}`

3. **Start Simple**: Begin with tools that don't require arguments like `unifi_list_devices`

4. **Check Categories**: Use `categories` to see what types of tools are available

5. **Read Descriptions**: The `list` command shows descriptions for each tool

## Troubleshooting

### Can't Connect

```
✗ Failed to connect to UniFi controller
```

**Fix**: Check your `.env` file has correct `UNIFI_HOST` and credentials

### Tool Not Found

```
Unknown tool: unifi_list_device
```

**Fix**: Use `list` to see exact tool names (e.g., `unifi_list_devices` with an 's')

### Invalid JSON

```
Invalid JSON arguments: Expecting property name enclosed in double quotes
```

**Fix**: Use double quotes for keys and string values: `{"key": "value"}`

### Write Operation Disabled

```
Write operation tool 'unifi_toggle_firewall_rule' is disabled
```

**Fix**: Enable write operations in `config.yaml`:
```yaml
tools:
  write_operations:
    enabled: true
```

## Next Steps

- See `devtools/README.md` for complete documentation
- Check `examples/dev_console_demo.py` for programmatic usage
- Read `docs/TASK-23-SUMMARY.md` for implementation details

## Need Help?

- Type `help` in the console for command reference
- Check the full documentation in `devtools/README.md`
- Look at example scripts in `examples/` directory
