# Docker Deployment Guide

This guide covers deploying the UniFi MCP Server using Docker and Docker Compose.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Building the Image](#building-the-image)
- [Running with Docker](#running-with-docker)
- [Running with Docker Compose](#running-with-docker-compose)
- [Environment Variables](#environment-variables)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The UniFi MCP Server Docker image provides:

- **Multi-stage build** for minimal image size (~150MB)
- **Non-root user** for enhanced security
- **Health checks** for container monitoring
- **Resource limits** to prevent resource exhaustion
- **Environment-based configuration** for flexibility

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher (optional)
- **Network Access**: Connectivity to your UniFi controller
- **Credentials**: UniFi admin account or API key

### Install Docker

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

**Windows/macOS:**
Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Quick Start

### 1. Clone or Navigate to Project

```bash
cd projects/unifi-mcp-server
```

### 2. Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### 3. Build and Run

**Using Docker Compose (Recommended):**
```bash
docker-compose up -d
```

**Using Docker directly:**
```bash
docker build -t unifi-mcp-server .
docker run -d --env-file .env unifi-mcp-server
```

### 4. Verify

```bash
# Check container status
docker ps

# View logs
docker logs unifi-mcp-server

# Check health
docker inspect --format='{{.State.Health.Status}}' unifi-mcp-server
```

## Configuration

### Environment File (.env)

Create a `.env` file in the project root:

```bash
# UniFi Controller Connection
UNIFI_HOST=192.168.1.1
UNIFI_PORT=443
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false

# Authentication Method 1: API Key (Recommended)
UNIFI_API_KEY=your-api-key-here

# Authentication Method 2: Username/Password
# UNIFI_USERNAME=admin
# UNIFI_PASSWORD=your-password

# Logging
LOG_LEVEL=INFO
```

**Important**: Never commit `.env` to version control!

## Building the Image

### Standard Build

```bash
docker build -t unifi-mcp-server:latest .
```

### Build with Custom Tag

```bash
docker build -t unifi-mcp-server:v0.1.0 .
```

### Build with Build Arguments

```bash
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  -t unifi-mcp-server:latest \
  .
```

### Multi-platform Build

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t unifi-mcp-server:latest \
  .
```

## Running with Docker

### Basic Run

```bash
docker run -d \
  --name unifi-mcp-server \
  --env-file .env \
  unifi-mcp-server:latest
```

### Run with Environment Variables

```bash
docker run -d \
  --name unifi-mcp-server \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_API_KEY=your-api-key \
  -e LOG_LEVEL=DEBUG \
  unifi-mcp-server:latest
```

### Run with Volume for Logs

```bash
docker run -d \
  --name unifi-mcp-server \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  unifi-mcp-server:latest
```

### Run with Host Network

```bash
docker run -d \
  --name unifi-mcp-server \
  --network host \
  --env-file .env \
  unifi-mcp-server:latest
```

### Interactive Run (for testing)

```bash
docker run -it --rm \
  --env-file .env \
  unifi-mcp-server:latest
```

## Running with Docker Compose

### Start Services

```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up unifi-mcp-server
```

### Stop Services

```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove with volumes
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs

# Follow logs
docker-compose logs -f

# Specific service
docker-compose logs unifi-mcp-server

# Last 100 lines
docker-compose logs --tail=100
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart unifi-mcp-server
```

### Scale Services

```bash
# Run multiple instances (if needed)
docker-compose up -d --scale unifi-mcp-server=3
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `UNIFI_HOST` | UniFi controller hostname/IP | `192.168.1.1` |
| `UNIFI_API_KEY` or `UNIFI_USERNAME`/`UNIFI_PASSWORD` | Authentication credentials | See below |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UNIFI_PORT` | Controller HTTPS port | `443` |
| `UNIFI_SITE` | UniFi site name | `default` |
| `UNIFI_VERIFY_SSL` | Verify SSL certificates | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Authentication Methods

**Method 1: API Key (Recommended)**
```bash
UNIFI_API_KEY=your-api-key-here
```

**Method 2: Username/Password**
```bash
UNIFI_USERNAME=admin
UNIFI_PASSWORD=your-password
```

## Security Considerations

### Container Security

1. **Non-root User**: Container runs as user `unifi` (UID 1000)
2. **Read-only Filesystem**: Most of the filesystem is read-only
3. **No New Privileges**: Security option prevents privilege escalation
4. **Resource Limits**: CPU and memory limits prevent resource exhaustion

### Network Security

1. **No Exposed Ports**: MCP uses stdio, no network ports needed
2. **SSL/TLS**: Supports secure HTTPS connections to UniFi controller
3. **Credential Protection**: Environment variables never logged

### Best Practices

1. **Use API Keys**: Prefer API keys over username/password
2. **Rotate Credentials**: Regularly rotate API keys and passwords
3. **Limit Permissions**: Use least-privilege UniFi accounts
4. **Monitor Logs**: Review container logs for suspicious activity
5. **Update Regularly**: Keep Docker image updated

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs unifi-mcp-server
```

**Common issues:**
- Missing environment variables
- Invalid credentials
- Network connectivity to controller

### Connection Refused

**Verify network:**
```bash
# Test from container
docker exec unifi-mcp-server ping -c 3 192.168.1.1

# Test HTTPS
docker exec unifi-mcp-server curl -k https://192.168.1.1
```

**Solutions:**
- Use `--network host` if controller is on same host
- Check firewall rules
- Verify `UNIFI_HOST` is correct

### Authentication Failed

**Check credentials:**
```bash
# View environment (redacted)
docker exec unifi-mcp-server env | grep UNIFI
```

**Solutions:**
- Verify API key is valid
- Check username/password
- Ensure account has admin privileges

### High Memory Usage

**Check resource usage:**
```bash
docker stats unifi-mcp-server
```

**Solutions:**
- Adjust memory limits in `docker-compose.yml`
- Check for memory leaks in logs
- Restart container

### Health Check Failing

**Check health status:**
```bash
docker inspect --format='{{json .State.Health}}' unifi-mcp-server | jq
```

**Solutions:**
- Verify Python can import package
- Check for startup errors in logs
- Increase health check timeout

## Advanced Usage

### Custom Dockerfile

Create a custom Dockerfile extending the base image:

```dockerfile
FROM unifi-mcp-server:latest

# Add custom tools or configuration
COPY custom_tools/ /app/custom_tools/

# Install additional dependencies
USER root
RUN pip install --no-cache-dir custom-package
USER unifi
```

### Docker Secrets

Use Docker secrets for sensitive data:

```yaml
# docker-compose.yml
services:
  unifi-mcp-server:
    secrets:
      - unifi_api_key
    environment:
      - UNIFI_API_KEY_FILE=/run/secrets/unifi_api_key

secrets:
  unifi_api_key:
    file: ./secrets/api_key.txt
```

### Persistent Logs

Mount a volume for persistent logs:

```yaml
# docker-compose.yml
services:
  unifi-mcp-server:
    volumes:
      - ./logs:/app/logs:rw
```

### Custom Network

Create a custom Docker network:

```bash
# Create network
docker network create unifi-network

# Run container on network
docker run -d \
  --name unifi-mcp-server \
  --network unifi-network \
  --env-file .env \
  unifi-mcp-server:latest
```

### Health Check Customization

Modify health check in Dockerfile:

```dockerfile
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=5 \
    CMD python -c "import unifi_mcp; print('OK')" || exit 1
```

### Resource Limits

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 128M
```

## Integration with MCP Clients

### Kiro Integration

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file",
        "/path/to/projects/unifi-mcp-server/.env",
        "unifi-mcp-server:latest"
      ],
      "disabled": false
    }
  }
}
```

### Claude Desktop Integration

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file",
        "/path/to/.env",
        "unifi-mcp-server:latest"
      ]
    }
  }
}
```

## Maintenance

### Update Image

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build

# Restart with new image
docker-compose up -d
```

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove all unused resources
docker system prune -a
```

### Backup Configuration

```bash
# Backup environment file
cp .env .env.backup

# Backup docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup
```

## Performance Tuning

### Optimize Build Cache

```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t unifi-mcp-server .
```

### Reduce Image Size

The multi-stage build already optimizes size, but you can:

1. Use `python:3.11-alpine` for even smaller images (may require additional build deps)
2. Remove unnecessary dependencies from `pyproject.toml`
3. Use `.dockerignore` to exclude files

### Improve Startup Time

1. Pre-build and cache the image
2. Use volume mounts for development
3. Optimize Python imports

## Support

For issues or questions:

1. Check logs: `docker logs unifi-mcp-server`
2. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. Open an issue on GitHub
4. Check [MCP documentation](https://modelcontextprotocol.io/)

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)
