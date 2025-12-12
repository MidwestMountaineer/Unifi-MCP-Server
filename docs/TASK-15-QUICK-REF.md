# Task 15 Quick Reference: Routing and Port Forward Tools

## New Tools Added

### Traffic Routes

```python
# List all routes
unifi_list_traffic_routes()

# List only enabled routes
unifi_list_traffic_routes(enabled_only=True)

# Get route details
unifi_get_route_details(route_id="abc123")
```

### Port Forwards

```python
# List all port forwards
unifi_list_port_forwards()

# List only enabled forwards
unifi_list_port_forwards(enabled_only=True)

# Get port forward details
unifi_get_port_forward_details(forward_id="xyz789")
```

## Example Outputs

### Route Summary
```json
{
  "id": "route1",
  "name": "VPN Route",
  "enabled": true,
  "type": "static",
  "destination_network": "10.0.0.0/24",
  "next_hop": "192.168.1.254",
  "distance": 1,
  "interface": "eth0"
}
```

### Port Forward Summary
```json
{
  "id": "forward1",
  "name": "Web Server",
  "enabled": true,
  "protocol": "TCP",
  "source": "any",
  "destination_ip": "192.168.10.100",
  "destination_port": "8080",
  "external_port": "80",
  "log": false
}
```

## Testing

Run unit tests:
```bash
python -m pytest tests/test_routing_tools.py -v
```

Run demo:
```bash
python examples/routing_demo.py
```

## API Endpoints

- Routes: `/api/s/{site}/rest/routing`
- Port Forwards: `/api/s/{site}/rest/portforward`

## Requirements Met

✅ 5.3 - List traffic routing rules  
✅ 5.4 - Get route details  
✅ 5.5 - List port forwarding rules  
✅ 5.6 - Get port forward details  
✅ 12.1 - Unit tests for core functionality  
✅ 12.3 - Validate tool schemas and responses
