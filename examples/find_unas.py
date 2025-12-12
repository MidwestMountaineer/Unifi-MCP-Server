"""Quick script to find the uNAS Pro in connected clients."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config.loader import load_config
from unifi_mcp.unifi_client import UniFiClient


async def main():
    """Find uNAS Pro."""
    config = load_config()
    
    async with UniFiClient(config.unifi) as client:
        # Fetch all clients
        clients_response = await client.get("/api/s/{site}/stat/sta")
        
        if "data" in clients_response:
            clients = clients_response["data"]
            print(f"Searching {len(clients)} connected clients for uNAS Pro (192.168.10.40)...")
            print()
            
            # Look for uNAS Pro by IP
            for network_client in clients:
                ip = network_client.get("ip", "")
                if ip == "192.168.10.40":
                    hostname = network_client.get("hostname", network_client.get("name", "Unknown"))
                    mac = network_client.get("mac", "Unknown")
                    
                    print("✓ Found uNAS Pro!")
                    print(f"  Hostname: {hostname}")
                    print(f"  IP: {ip}")
                    print(f"  MAC: {mac}")
                    return
            
            print("✗ uNAS Pro (192.168.10.40) not found in connected clients")
            print()
            print("This could mean:")
            print("  - The uNAS Pro is offline")
            print("  - It's not currently connected to the network")
            print("  - It hasn't been seen recently by the controller")
            print()
            print("All connected IPs:")
            for network_client in clients:
                ip = network_client.get("ip", "No IP")
                hostname = network_client.get("hostname", network_client.get("name", "Unknown"))
                print(f"  - {ip:15} {hostname}")


if __name__ == "__main__":
    asyncio.run(main())
