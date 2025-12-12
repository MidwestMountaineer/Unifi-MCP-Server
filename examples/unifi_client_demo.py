"""Demo script for UniFi API client.

This script demonstrates how to use the UniFi client to connect to a
UniFi Network Controller and make API requests.

Usage:
    python examples/unifi_client_demo.py

Requirements:
    - Set environment variables: UNIFI_HOST, UNIFI_USERNAME, UNIFI_PASSWORD
    - Or create a .env file with these variables
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config.loader import load_config
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.utils.logging import setup_logging


async def main():
    """Main demo function."""
    # Set up logging
    setup_logging(log_level="INFO", include_correlation_id=True)
    
    print("=" * 60)
    print("UniFi API Client Demo")
    print("=" * 60)
    print()
    
    try:
        # Load configuration
        print("Loading configuration...")
        config = load_config()
        print(f"✓ Configuration loaded")
        print(f"  Host: {config.unifi.host}:{config.unifi.port}")
        print(f"  Site: {config.unifi.site}")
        print(f"  SSL Verification: {config.unifi.verify_ssl}")
        print()
        
        # Create UniFi client
        print("Creating UniFi client...")
        client = UniFiClient(config.unifi)
        print("✓ Client created")
        print()
        
        # Connect and authenticate
        print("Connecting to UniFi controller...")
        await client.connect()
        print("✓ Connected and authenticated")
        print()
        
        # Make a test API request - list UniFi devices
        print("Fetching UniFi device list...")
        try:
            devices_response = await client.get("/api/s/{site}/stat/device")
            
            if "data" in devices_response:
                devices = devices_response["data"]
                print(f"✓ Found {len(devices)} UniFi device(s)")
                print()
                
                # Display device summary
                if devices:
                    print("UniFi Devices (Managed Hardware):")
                    print("-" * 60)
                    for device in devices:
                        name = device.get("name", "Unknown")
                        model = device.get("model", "Unknown")
                        device_type = device.get("type", "Unknown")
                        state = device.get("state", 0)
                        status = "Online" if state == 1 else "Offline"
                        
                        print(f"  • {name}")
                        print(f"    Model: {model} ({device_type})")
                        print(f"    Status: {status}")
                        print()
            else:
                print("⚠ No device data in response")
        
        except Exception as e:
            print(f"✗ Failed to fetch devices: {e}")
        
        # Fetch connected clients (all devices on network)
        print("Fetching connected clients...")
        try:
            clients_response = await client.get("/api/s/{site}/stat/sta")
            
            if "data" in clients_response:
                clients = clients_response["data"]
                print(f"✓ Found {len(clients)} connected client(s)")
                print()
                
                # Display client summary (limit to first 10 for brevity)
                if clients:
                    print("Connected Clients (Sample - showing first 10):")
                    print("-" * 60)
                    for network_client in clients[:10]:
                        hostname = network_client.get("hostname", network_client.get("name", "Unknown"))
                        ip = network_client.get("ip", "No IP")
                        mac = network_client.get("mac", "Unknown")
                        
                        print(f"  • {hostname}")
                        print(f"    IP: {ip}")
                        print(f"    MAC: {mac}")
                        print()
                    
                    if len(clients) > 10:
                        print(f"  ... and {len(clients) - 10} more clients")
                        print()
            else:
                print("⚠ No client data in response")
        
        except Exception as e:
            print(f"✗ Failed to fetch clients: {e}")
        
        # Close connection
        print("Closing connection...")
        await client.close()
        print("✓ Connection closed")
        print()
        
        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
    
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        print("Make sure you have set the following environment variables:")
        print("  - UNIFI_HOST (e.g., 192.168.1.1)")
        print("  - UNIFI_USERNAME (e.g., admin)")
        print("  - UNIFI_PASSWORD")
        print()
        print("You can also create a .env file with these variables.")
        sys.exit(1)


async def demo_context_manager():
    """Demo using the client as a context manager."""
    print()
    print("=" * 60)
    print("Context Manager Demo")
    print("=" * 60)
    print()
    
    config = load_config()
    
    # Using async context manager
    print("Using client as context manager...")
    async with UniFiClient(config.unifi) as client:
        print("✓ Connected (context manager handles connect/close)")
        
        # Make a request
        response = await client.get("/api/s/{site}/stat/device")
        device_count = len(response.get("data", []))
        print(f"✓ Found {device_count} device(s)")
    
    print("✓ Connection automatically closed")
    print()


if __name__ == "__main__":
    # Run main demo
    asyncio.run(main())
    
    # Uncomment to run context manager demo
    # asyncio.run(demo_context_manager())
