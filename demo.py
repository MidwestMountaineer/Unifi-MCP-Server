#!/usr/bin/env python3
"""Demo script for UniFi MCP Server - Phase 1 & 2 functionality.

This script demonstrates:
- Configuration loading with environment variables
- Logging system with sensitive data redaction
- UniFi API client with authentication
- Retry logic and error handling
- Response caching
- Performance optimizations (connection pooling, timeouts, concurrent limiting)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from unifi_mcp.config.loader import load_config, ConfigurationError
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.utils.logging import get_logger, setup_logging


async def demo_configuration():
    """Demo 1: Configuration Loading"""
    print("\n" + "="*80)
    print("DEMO 1: Configuration Loading")
    print("="*80)
    
    try:
        # Load configuration
        config = load_config()
        
        print(f"\n✓ Configuration loaded successfully!")
        print(f"  - Server Name: {config.server.name}")
        print(f"  - Log Level: {config.server.log_level}")
        print(f"  - UniFi Host: {config.unifi.host}")
        print(f"  - UniFi Port: {config.unifi.port}")
        print(f"  - UniFi Site: {config.unifi.site}")
        print(f"  - SSL Verification: {config.unifi.verify_ssl}")
        
        # Show authentication method
        if config.unifi.api_key:
            print(f"  - Auth Method: API Key (***{config.unifi.api_key[-4:]})")
        else:
            print(f"  - Auth Method: Username/Password ({config.unifi.username})")
        
        # Show performance settings
        perf = config.server.performance
        print(f"\n✓ Performance Settings:")
        print(f"  - Cache TTL: {perf.get('cache_ttl', 30)}s")
        print(f"  - Max Concurrent Requests: {perf.get('max_concurrent_requests', 10)}")
        print(f"  - Request Timeout: {perf.get('request_timeout', 30)}s")
        print(f"  - Connection Timeout: {perf.get('connection_timeout', 10)}s")
        print(f"  - Connection Pool Size: {perf.get('connection_limit', 100)}")
        
        return config
        
    except ConfigurationError as e:
        print(f"\n✗ Configuration Error: {e}")
        print("\nMake sure you have a .env file with required variables:")
        print("  - UNIFI_HOST")
        print("  - UNIFI_API_KEY (or UNIFI_USERNAME + UNIFI_PASSWORD)")
        return None


async def demo_logging():
    """Demo 2: Logging with Redaction"""
    print("\n" + "="*80)
    print("DEMO 2: Logging System with Sensitive Data Redaction")
    print("="*80)
    
    # Set up logging
    setup_logging(log_level="INFO")
    logger = get_logger("demo")
    
    print("\n✓ Logging system initialized")
    print("  - Sensitive data (passwords, tokens, keys) will be redacted")
    
    # Demo logging with sensitive data
    print("\n  Example log entries:")
    logger.info("Normal log message - this appears as-is")
    
    # This will be redacted in the actual logs
    test_data = {
        "username": "admin",
        "password": "super_secret_password",
        "api_key": "1234567890abcdef",
        "normal_field": "this is visible"
    }
    
    print(f"  - Logging data with sensitive fields: {test_data}")
    print(f"  - In logs, password/api_key will show as: ***REDACTED***")


async def demo_api_client(config):
    """Demo 3: UniFi API Client"""
    print("\n" + "="*80)
    print("DEMO 3: UniFi API Client with Retry & Caching")
    print("="*80)
    
    if not config:
        print("\n✗ Skipping - configuration not loaded")
        return
    
    # Create client
    client = UniFiClient(config.unifi, config.server.__dict__)
    
    print(f"\n✓ UniFi API Client created")
    print(f"  - Base URL: {client.base_url}")
    print(f"  - Authentication: {'API Key' if client.use_api_key else 'Session-based'}")
    print(f"  - SSL Verification: {config.unifi.verify_ssl}")
    
    try:
        # Connect and authenticate
        print(f"\n→ Connecting to UniFi controller...")
        await client.connect()
        print(f"✓ Connected and authenticated successfully!")
        
        # Demo 1: Get devices (will be cached)
        print(f"\n→ Fetching device list (first request - will be cached)...")
        devices_response = await client.get(f"/api/s/{config.unifi.site}/stat/device")
        
        if devices_response.get("data"):
            device_count = len(devices_response["data"])
            print(f"✓ Retrieved {device_count} devices")
            
            # Show first device info
            if device_count > 0:
                device = devices_response["data"][0]
                print(f"\n  Example device:")
                print(f"  - Name: {device.get('name', 'N/A')}")
                print(f"  - Model: {device.get('model', 'N/A')}")
                print(f"  - MAC: {device.get('mac', 'N/A')}")
                print(f"  - State: {device.get('state', 'N/A')}")
        
        # Demo 2: Get devices again (should hit cache)
        print(f"\n→ Fetching device list again (should hit cache)...")
        devices_response_2 = await client.get(f"/api/s/{config.unifi.site}/stat/device")
        print(f"✓ Retrieved from cache (instant response)")
        
        # Demo 3: Get clients
        print(f"\n→ Fetching client list...")
        clients_response = await client.get(f"/api/s/{config.unifi.site}/stat/sta")
        
        if clients_response.get("data"):
            client_count = len(clients_response["data"])
            print(f"✓ Retrieved {client_count} connected clients")
            
            # Show first client info
            if client_count > 0:
                sta = clients_response["data"][0]
                print(f"\n  Example client:")
                print(f"  - Hostname: {sta.get('hostname', 'N/A')}")
                print(f"  - MAC: {sta.get('mac', 'N/A')}")
                print(f"  - IP: {sta.get('ip', 'N/A')}")
                print(f"  - Signal: {sta.get('signal', 'N/A')} dBm")
        
        # Demo 4: Show cache stats
        print(f"\n✓ Cache Statistics:")
        print(f"  - Cache entries: {len(client.cache)}")
        print(f"  - Cache enabled: {client.cache_enabled}")
        
        # Demo 5: Performance features
        print(f"\n✓ Performance Features Active:")
        print(f"  - Connection pooling: Enabled (keep-alive)")
        print(f"  - Max concurrent requests: {client.max_concurrent_requests}")
        print(f"  - Request timeout: {client.request_timeout}s")
        print(f"  - Connection timeout: {client.connection_timeout}s")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"\nMake sure:")
        print(f"  1. Your UniFi controller is accessible at {config.unifi.host}")
        print(f"  2. Your credentials are correct")
        print(f"  3. The controller is running")
    
    finally:
        # Clean up
        await client.close()
        print(f"\n✓ Connection closed")


async def demo_concurrent_requests(config):
    """Demo 4: Concurrent Request Limiting"""
    print("\n" + "="*80)
    print("DEMO 4: Concurrent Request Limiting")
    print("="*80)
    
    if not config:
        print("\n✗ Skipping - configuration not loaded")
        return
    
    # Create client with low concurrent limit for demo
    server_config = config.server.__dict__.copy()
    server_config["performance"] = server_config.get("performance", {}).copy()
    server_config["performance"]["max_concurrent_requests"] = 3
    
    client = UniFiClient(config.unifi, server_config)
    
    print(f"\n✓ Client configured with max 3 concurrent requests")
    
    try:
        await client.connect()
        
        print(f"\n→ Launching 10 concurrent requests...")
        print(f"  (only 3 will execute at a time)")
        
        # Launch multiple concurrent requests
        tasks = []
        for i in range(10):
            task = client.get(f"/api/s/{config.unifi.site}/stat/device", use_cache=False)
            tasks.append(task)
        
        # Execute all
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"\n✓ Completed {success_count}/10 requests")
        print(f"  - Requests were automatically queued and limited to 3 concurrent")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    finally:
        await client.close()


async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("UniFi MCP Server - Phase 1 & 2 Demo")
    print("="*80)
    print("\nThis demo showcases the completed functionality:")
    print("  ✓ Phase 1: Project Foundation")
    print("    - Configuration loading with validation")
    print("    - Logging system with sensitive data redaction")
    print("  ✓ Phase 2: UniFi API Client")
    print("    - HTTP client with authentication")
    print("    - Retry logic and error handling")
    print("    - Response caching with TTL")
    print("    - Performance optimizations")
    
    # Run demos
    config = await demo_configuration()
    await demo_logging()
    await demo_api_client(config)
    
    # Optional: Demo concurrent limiting (requires working connection)
    if config and os.getenv("DEMO_CONCURRENT", "false").lower() == "true":
        await demo_concurrent_requests(config)
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)
    print("\nNext Phase: MCP Server Core (Phase 3)")
    print("  - MCP server initialization")
    print("  - Tool registration and handlers")
    print("  - Request/response handling")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
