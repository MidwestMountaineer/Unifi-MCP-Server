# UniFi API Key Setup Guide

## Quick Start

For UniFi OS devices (Dream Machine, Cloud Gateway, uNAS Pro), API key authentication is the recommended method.

## Step-by-Step Instructions

### 1. Access UniFi OS Settings

1. Open your browser and navigate to your Dream Machine:
   - URL: `https://192.168.1.1` (or your Dream Machine IP)
   - Login with your admin credentials

2. Navigate to **Settings** (gear icon in bottom left)

### 2. Generate API Key

1. In Settings, go to **System** section
2. Click on **Advanced** tab
3. Scroll down to the **API** section
4. Click **Create New API Key**

### 3. Configure API Key

1. **Name**: Give it a descriptive name
   - Example: "Kiro MCP Server"
   - Example: "Homelab Automation"

2. **Permissions**: Select appropriate permissions
   - For read-only access: Select "View Only"
   - For full access: Select "Full Management"
   - **Recommendation**: Start with "View Only" for testing

3. Click **Create**

### 4. Copy the API Key

⚠️ **IMPORTANT**: The API key will only be shown once!

1. Copy the generated API key immediately
2. Store it securely (password manager recommended)
3. You won't be able to see it again after closing the dialog

Example API key format:
```
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Test the API Key

You can test the API key using curl:

```bash
# Test API key authentication
curl -k -H "X-API-KEY: your_api_key_here" \
  https://192.168.1.1/proxy/network/api/s/default/stat/device
```

If successful, you'll see JSON data about your devices.

## Using the API Key with UniFi MCP Server

### Environment Variable

Set the API key as an environment variable:

```bash
export UNIFI_API_KEY="your_api_key_here"
export UNIFI_HOST="192.168.1.1"
export UNIFI_VERIFY_SSL="false"
```

### Kiro MCP Configuration

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "python",
      "args": ["-m", "unifi_mcp"],
      "cwd": "U:/KiroWorkspace/projects/unifi-mcp-server",
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_API_KEY": "your_api_key_here",
        "UNIFI_SITE": "default",
        "UNIFI_VERIFY_SSL": "false"
      },
      "disabled": false
    }
  }
}
```

### .env File

Or create a `.env` file in the project root:

```bash
UNIFI_HOST=192.168.1.1
UNIFI_API_KEY=your_api_key_here
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
LOG_LEVEL=INFO
```

## API Key vs Username/Password

### API Key (Recommended)

**Pros:**
- ✅ More secure (can be revoked without changing password)
- ✅ Granular permissions (read-only vs full access)
- ✅ Better for automation and integrations
- ✅ No session management needed
- ✅ Works with UniFi OS devices

**Cons:**
- ❌ Only available on UniFi OS devices
- ❌ Requires manual generation via web UI

### Username/Password (Legacy)

**Pros:**
- ✅ Works with traditional UniFi Controllers
- ✅ No additional setup required

**Cons:**
- ❌ Less secure (exposes credentials)
- ❌ Requires session management
- ❌ No granular permissions
- ❌ Password changes break automation

## Security Best Practices

### API Key Management

1. **Use Read-Only Keys for Monitoring**
   - Create separate keys for read-only vs write operations
   - Use read-only keys for dashboards and monitoring

2. **Rotate Keys Regularly**
   - Generate new keys periodically (quarterly recommended)
   - Revoke old keys after rotation

3. **Store Keys Securely**
   - Use environment variables (not hardcoded)
   - Use password managers or secrets management tools
   - Never commit keys to version control

4. **Monitor Key Usage**
   - Review API key activity in UniFi OS logs
   - Revoke unused or suspicious keys immediately

5. **Limit Key Scope**
   - Create separate keys for different applications
   - Revoke keys when no longer needed

### Revoking API Keys

If a key is compromised:

1. Go to **Settings** → **System** → **Advanced** → **API**
2. Find the compromised key in the list
3. Click **Revoke** or **Delete**
4. Generate a new key if needed

## Troubleshooting

### "Invalid API Key" Error

**Possible causes:**
1. API key was copied incorrectly (check for extra spaces)
2. API key was revoked in UniFi OS
3. API key doesn't have required permissions

**Solutions:**
1. Verify the API key is correct (copy/paste again)
2. Check if key still exists in UniFi OS settings
3. Generate a new API key with appropriate permissions

### "Connection Refused" Error

**Possible causes:**
1. Wrong host IP address
2. Wrong port (should be 443 for HTTPS)
3. UniFi OS is not running

**Solutions:**
1. Verify Dream Machine IP: `ping 192.168.1.1`
2. Check UniFi OS is accessible: `https://192.168.1.1`
3. Verify port 443 is open

### "SSL Certificate Verification Failed"

**Possible causes:**
1. Self-signed certificate on Dream Machine
2. `UNIFI_VERIFY_SSL` not set to `false`

**Solutions:**
1. Set `UNIFI_VERIFY_SSL=false` in environment
2. Or install the Dream Machine's certificate in your trust store

### "Unauthorized" Error

**Possible causes:**
1. API key doesn't have required permissions
2. API key is for wrong site

**Solutions:**
1. Regenerate API key with "Full Management" permissions
2. Verify `UNIFI_SITE` matches your site name (usually "default")

## API Key Permissions

### View Only (Read-Only)

**Can access:**
- Device information
- Client information
- Network configuration (read)
- Statistics and metrics
- Firewall rules (read)
- System information

**Cannot access:**
- Configuration changes
- Device adoption/provisioning
- Firmware updates
- User management

**Recommended for:**
- Monitoring dashboards
- Read-only integrations
- Testing and development

### Full Management

**Can access:**
- Everything in View Only
- Configuration changes
- Device management
- Firmware updates
- User management

**Recommended for:**
- Automation scripts
- Configuration management
- Full-featured integrations

**Use with caution!**

## Example: Testing Your Setup

Once configured, test with Python:

```python
import os
import asyncio
import aiohttp

async def test_api_key():
    api_key = os.getenv("UNIFI_API_KEY")
    host = os.getenv("UNIFI_HOST", "192.168.1.1")
    
    url = f"https://{host}/proxy/network/api/s/default/stat/device"
    headers = {"X-API-KEY": api_key}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, ssl=False) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Success! Found {len(data.get('data', []))} devices")
            else:
                print(f"❌ Error: {response.status}")
                print(await response.text())

asyncio.run(test_api_key())
```

## Additional Resources

- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)
- [UniFi OS Release Notes](https://community.ui.com/releases)
- [UniFi Community Forums](https://community.ui.com/)

---

**Need Help?** Check the main setup guide at `docs/KIRO-SETUP-GUIDE.md` or the troubleshooting section above.
