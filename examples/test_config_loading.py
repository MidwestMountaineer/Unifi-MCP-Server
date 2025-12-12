#!/usr/bin/env python3
"""Example script to test configuration loading.

This script demonstrates how the configuration system works:
1. Loads .env file if present
2. Loads YAML configuration
3. Expands environment variables
4. Validates required fields
5. Returns structured Config object

Usage:
    python examples/test_config_loading.py
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config import load_config, ConfigurationError


def main():
    """Test configuration loading."""
    print("=" * 60)
    print("UniFi MCP Server - Configuration Loading Test")
    print("=" * 60)
    print()
    
    # Check if required environment variables are set
    required_vars = ["UNIFI_HOST", "UNIFI_USERNAME", "UNIFI_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("Please set these variables or create a .env file.")
        print("See .env.example for reference.")
        return 1
    
    try:
        print("Loading configuration...")
        config = load_config()
        print("✅ Configuration loaded successfully!")
        print()
        
        print("Server Configuration:")
        print(f"  Name: {config.server.name}")
        print(f"  Log Level: {config.server.log_level}")
        print(f"  Diagnostics Enabled: {config.server.diagnostics.get('enabled', False)}")
        print()
        
        print("UniFi Configuration:")
        print(f"  Host: {config.unifi.host}")
        print(f"  Port: {config.unifi.port}")
        print(f"  Username: {config.unifi.username}")
        print(f"  Password: {'*' * len(config.unifi.password)} (redacted)")
        print(f"  Site: {config.unifi.site}")
        print(f"  Verify SSL: {config.unifi.verify_ssl}")
        print()
        
        print("Retry Configuration:")
        print(f"  Max Attempts: {config.unifi.retry.get('max_attempts', 3)}")
        print(f"  Backoff Factor: {config.unifi.retry.get('backoff_factor', 2)}")
        print(f"  Max Backoff: {config.unifi.retry.get('max_backoff', 30)}")
        print()
        
        print("Tools Configuration:")
        print(f"  Network Discovery: {'enabled' if config.tools.network_discovery.get('enabled') else 'disabled'}")
        print(f"  Security: {'enabled' if config.tools.security.get('enabled') else 'disabled'}")
        print(f"  Statistics: {'enabled' if config.tools.statistics.get('enabled') else 'disabled'}")
        print(f"  Migration: {'enabled' if config.tools.migration.get('enabled') else 'disabled'}")
        print(f"  Write Operations: {'enabled' if config.tools.write_operations.get('enabled') else 'disabled'}")
        print()
        
        print("=" * 60)
        print("✅ All configuration validation passed!")
        print("=" * 60)
        return 0
        
    except ConfigurationError as e:
        print(f"❌ Configuration Error:")
        print(f"   {e}")
        print()
        return 1
    except Exception as e:
        print(f"❌ Unexpected Error:")
        print(f"   {e}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
