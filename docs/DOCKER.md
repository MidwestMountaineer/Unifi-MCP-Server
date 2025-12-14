# Docker Deployment

Deploy the UniFi MCP Server using Docker.

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Edit with your credentials
nano .env

# Build and run
docker-compose up -d

# Verify
docker logs unifi-mcp-server
```

## Environment File (.env)

```bash
UNIFI_HOST=192.168.1.1
UNIFI_PORT=443
UNIFI_API_KEY=your-api-key-here
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
LOG_LEVEL=INFO
```

## Docker Commands

```bash
# Build image
docker build -t unifi-mcp-server .

# Run container
docker run -d --name unifi-mcp-server --env-file .env unifi-mcp-server

# View logs
docker logs -f unifi-mcp-server

# Stop
docker-compose down
```

## Docker Compose

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f
```

## MCP Client Integration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "--env-file", "/path/to/.env", "unifi-mcp-server"]
    }
  }
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check `UNIFI_HOST`, use `--network host` if needed |
| Auth failed | Verify API key or credentials |
| Container won't start | Check `docker logs unifi-mcp-server` |
