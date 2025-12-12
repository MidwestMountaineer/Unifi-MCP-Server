# UniFi MCP Server - Production Deployment

**Status**: ✅ Production Deployed  
**Location**: `tools/MCP/unifi-mcp-server/`  
**Deployed**: October 25, 2025  
**Version**: 1.0.0

---

## Deployment Information

### Location
- **Production**: `U:\KiroWorkspace\tools\MCP\unifi-mcp-server\`
- **Archive**: `U:\KiroWorkspace\archive\projects\2025-10-10-unifi-mcp-server\`
- **Spec**: `U:\KiroWorkspace\archive\specs\2025-10-10-unifi-mcp-server\`

### Configuration

**User-Level MCP Config**: `C:\Users\austi\.kiro\settings\mcp.json`

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "[REDACTED]",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false,
      "autoApprove": ["unifi_list_*", "unifi_get_*"]
    }
  }
}
```

**Working Directory**: The MCP server runs from wherever Python can import `unifi_mcp` module

**Environment File**: `tools/MCP/unifi-mcp-server/.env`

---

## Installation

The MCP server is installed as a Python package and can be run from anywhere:

```powershell
# Install in development mode (from tools/MCP/unifi-mcp-server/)
cd tools\MCP\unifi-mcp-server
pip install -e .

# Or install normally
pip install .
```

Once installed, the `unifi_mcp` module is available system-wide via `python -m unifi_mcp`.

---

## Usage

### Via Kiro IDE
The MCP server is automatically started by Kiro when configured in `mcp.json`. No manual startup required.

### Manual Testing
```powershell
# From any directory
python -m unifi_mcp

# Or use the dev console
cd tools\MCP\unifi-mcp-server
python -m devtools.dev_console
```

### Via MCP Inspector
```powershell
cd tools\MCP\unifi-mcp-server
.\devtools\mcp_inspector.ps1
```

---

## Tools Available

**Total**: 25 production-ready tools

### Categories
- **Network Discovery** (8 tools): Devices, clients, networks, WLANs
- **Security** (7 tools): Firewall, routing, port forwards, IPS
- **Statistics** (7 tools): Network stats, health, bandwidth, DPI
- **Migration Support** (3 tools): DHCP, VLAN connectivity, config export

See `docs/ALL-TOOLS-REFERENCE.md` for complete documentation.

---

## Maintenance

### Updating the MCP Server

1. **Make changes** in `tools/MCP/unifi-mcp-server/`
2. **Test changes** using dev console or MCP inspector
3. **Reinstall** if needed: `pip install -e .`
4. **Restart Kiro** to reload MCP server
5. **Document changes** in this file

### Creating New Features

If you want to add new features or make significant changes:

1. **Create new project** in `projects/unifi-mcp-enhancements/`
2. **Copy from deployed version** as starting point
3. **Develop and test** in project directory
4. **Deploy to tools/MCP/** when complete
5. **Archive project** when done

---

## Documentation

### Quick References
- **All Tools**: `docs/ALL-TOOLS-REFERENCE.md`
- **Kiro Setup**: `docs/KIRO-SETUP-GUIDE.md`
- **Quick Reference**: `docs/QUICK-REFERENCE.md`
- **Architecture**: `docs/ARCHITECTURE.md`

### Guides
- **API Key Setup**: `docs/API-KEY-SETUP.md`
- **Configuration**: `docs/CONFIGURATION.md`
- **Security**: `docs/SECURITY.md`
- **Logging**: `docs/LOGGING.md`
- **Extending**: `docs/EXTENDING.md`

### Development Tools
- **Dev Console**: `devtools/dev_console.py`
- **MCP Inspector**: `devtools/mcp_inspector.ps1`
- **Performance Profiler**: `devtools/performance_profiler.py`

---

## Project History

### Development Phase (Oct 8-10, 2025)
- **Location**: `projects/unifi-mcp-server/`
- **Status**: Active development
- **Outcome**: 25 tools implemented, all tests passing

### Completion (Oct 10, 2025)
- **Status**: PROJECT-COMPLETE.md created
- **Spec**: Archived to `archive/specs/2025-10-10-unifi-mcp-server/`
- **Project**: Remained in `projects/` (incorrect)

### Deployment (Oct 25, 2025)
- **Action**: Moved to production location
- **Deployed**: `tools/MCP/unifi-mcp-server/`
- **Archived**: `archive/projects/2025-10-10-unifi-mcp-server/`
- **Reason**: Better hygiene, proper separation of deployed vs. development

---

## Future Enhancements

If you want to add features, create a new project:

```
projects/unifi-mcp-enhancements/
├── README.md (describe enhancements)
├── src/ (copy from tools/MCP/unifi-mcp-server/)
├── tests/ (add new tests)
└── docs/ (document changes)
```

When complete:
1. Test thoroughly
2. Deploy to `tools/MCP/unifi-mcp-server/`
3. Archive project to `archive/projects/YYYY-MM-DD-unifi-mcp-enhancements/`
4. Update this DEPLOYMENT.md

---

## Troubleshooting

### MCP Server Not Starting
1. Check Python can import module: `python -c "import unifi_mcp"`
2. Check environment variables in `mcp.json`
3. Check `.env` file exists with credentials
4. Check Kiro MCP server status in IDE

### Tools Not Working
1. Verify UniFi controller accessible: `ping 192.168.1.1`
2. Check API key is valid
3. Check SSL verification setting
4. Enable debug logging: Set `LOG_LEVEL=DEBUG` in `mcp.json`

### Need to Reinstall
```powershell
cd tools\MCP\unifi-mcp-server
pip uninstall unifi-mcp
pip install -e .
```

---

**Deployed**: October 25, 2025  
**Deployed By**: Automated maintenance process  
**Status**: ✅ Production Ready  
**Next Review**: As needed for enhancements

