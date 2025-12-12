# Security Documentation

## Overview

Security is a first-class concern for the UniFi MCP Server. This document outlines the security architecture, threat model, security controls, best practices, and incident response procedures.

## Security Philosophy

### Core Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimal permissions and access
3. **Fail Secure**: Errors default to secure state
4. **Explicit Authorization**: Write operations require confirmation
5. **Audit Trail**: All operations logged
6. **Secure by Default**: Safe defaults, opt-in for risky features

### Security-First Design

- Credentials never logged or exposed
- Write operations disabled by default
- Input validation on all parameters
- SSL/TLS for network communication
- Sensitive data redaction throughout
- Clear error messages without credential leakage

## Threat Model

### Assets

1. **UniFi Controller Credentials**
   - Username and password
   - Session cookies
   - API tokens (if used)

2. **Network Configuration**
   - Firewall rules
   - VLAN settings
   - Port forwards
   - Routing rules

3. **Network Data**
   - Device information
   - Client information
   - Network topology
   - Traffic statistics

### Threat Actors

1. **Malicious AI Agent**
   - Compromised or malicious LLM
   - Attempts unauthorized changes
   - Tries to extract credentials

2. **Compromised MCP Client**
   - Kiro or Claude Desktop compromised
   - Attempts to bypass security controls
   - Tries to escalate privileges

3. **Local Attacker**
   - Access to machine running server
   - Attempts to read credentials from memory/disk
   - Tries to intercept network traffic

4. **Network Attacker**
   - Man-in-the-middle attacks
   - Attempts to intercept UniFi API traffic
   - Tries to replay captured requests

### Threats

1. **Credential Exposure**
   - Credentials logged to files
   - Credentials in error messages
   - Credentials in tool responses
   - Credentials in version control

2. **Unauthorized Configuration Changes**
   - AI agent makes changes without confirmation
   - Malicious firewall rule creation
   - Accidental network disruption

3. **Information Disclosure**
   - Sensitive network topology exposed
   - Client information leaked
   - Security configuration revealed

4. **Denial of Service**
   - Excessive API requests overwhelm controller
   - Resource exhaustion on server
   - Network disruption through config changes

5. **Session Hijacking**
   - Session cookies intercepted
   - Session cookies stolen from memory
   - Replay attacks

## Security Controls

### 1. Credential Management

#### Storage

**Environment Variables**:
- Credentials stored in environment variables
- Never in configuration files
- Never in version control
- `.env` file in `.gitignore`

**Example**:
```bash
# .env (never commit this file)
UNIFI_HOST=192.168.1.1
UNIFI_USERNAME=admin
UNIFI_PASSWORD=secure-password-here
```

#### Validation

**Fail-Fast Behavior**:
- Server refuses to start without required credentials
- Clear error messages guide user to fix
- No partial operation with missing credentials

**Example Error**:
```
ConfigurationError: Missing required configuration fields:
  - unifi.password (set via UNIFI_PASSWORD environment variable)

Please ensure all required environment variables are set.
```

#### Redaction

**Automatic Redaction**:
- All logging automatically redacts sensitive fields
- Redacted fields: password, token, api_key, secret, authorization, cookie, session
- Redaction applies to logs, errors, and diagnostics

**Implementation**:
```python
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd',
    'token', 'api_key', 'secret',
    'authorization', 'x-auth-token',
    'cookie', 'session'
}

def redact_sensitive_data(data):
    """Recursively redact sensitive fields"""
    # Replace sensitive values with '***REDACTED***'
```

#### Session Management

**Session Cookies**:
- Stored in memory only (never persisted)
- Cleared on server shutdown
- Automatic re-authentication on expiry
- One retry on 401 errors

### 2. Write Operation Safety

#### Confirmation Requirement

**Explicit Confirmation**:
- All write operations require `confirm=true` parameter
- Missing confirmation returns clear error
- No default confirmation
- Forces intentional action

**Example**:
```python
# This will fail
await toggle_firewall_rule(rule_id="abc123")

# This will succeed
await toggle_firewall_rule(rule_id="abc123", confirm=True)
```

#### Write Operation Logging

**Audit Trail**:
- All write operations logged at WARNING level
- Logs include: tool name, arguments, timestamp, result
- Separate log entries for: initiation, completion, failure
- Correlation IDs track operations

**Log Format**:
```json
{
  "timestamp": "2025-10-09T10:30:00Z",
  "level": "WARNING",
  "message": "WRITE OPERATION INITIATED: unifi_toggle_firewall_rule",
  "tool_name": "unifi_toggle_firewall_rule",
  "category": "write_operations",
  "operation_type": "write",
  "confirmed": true,
  "arguments": {
    "rule_id": "abc123",
    "confirm": true
  }
}
```

#### Disabled by Default

**Configuration**:
```yaml
tools:
  write_operations:
    enabled: false  # Must explicitly enable
    require_confirmation: true  # Cannot disable
```

**Rationale**: Prevents accidental enablement of write operations

### 3. Input Validation

#### JSON Schema Validation

**All Inputs Validated**:
- Every tool has JSON schema for parameters
- Validation before execution
- Type checking (string, integer, boolean, enum)
- Range checking (min/max values)
- Required field checking

**Example Schema**:
```python
input_schema = {
    "type": "object",
    "properties": {
        "rule_id": {
            "type": "string",
            "description": "Firewall rule ID",
            "minLength": 1,
            "maxLength": 100
        },
        "enabled": {
            "type": "boolean",
            "description": "Enable or disable rule"
        }
    },
    "required": ["rule_id"]
}
```

#### Sanitization

**Input Sanitization**:
- String length limits (max 1000 chars for text fields)
- IP address format validation
- MAC address format validation
- VLAN ID range validation (1-4094)
- No SQL injection (no SQL used)
- No command injection (no shell commands)
- No path traversal (no file operations with user input)

### 4. Network Security

#### SSL/TLS

**HTTPS Communication**:
- All UniFi API communication over HTTPS
- SSL certificate verification configurable
- Self-signed certificates supported (with warning)
- No HTTP fallback

**Configuration**:
```yaml
unifi:
  verify_ssl: true  # Recommended for production
  # Set to false only for development with self-signed certs
```

**Warning for Self-Signed**:
```
WARNING: SSL certificate verification disabled. 
This should only be used in development environments.
```

#### Connection Security

**Timeouts**:
- Connection timeout: 10 seconds
- Read timeout: 30 seconds
- Prevents hanging connections
- Limits exposure window

**Connection Pooling**:
- Reuses connections (keep-alive)
- Limits concurrent connections (max 10)
- Prevents connection exhaustion

### 5. Error Handling

#### Secure Error Messages

**No Credential Exposure**:
- Errors never include credentials
- Errors never include session cookies
- Errors never include API tokens
- Stack traces redacted in production

**Example Secure Error**:
```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Failed to authenticate with UniFi controller",
    "details": "Invalid credentials",
    "actionable_steps": [
      "Verify UNIFI_USERNAME environment variable",
      "Verify UNIFI_PASSWORD environment variable",
      "Check UniFi controller is accessible"
    ]
  }
}
```

**What NOT to include**:
- ❌ "Authentication failed with username 'admin' and password 'secret123'"
- ❌ "Session cookie: unifises=abc123..."
- ❌ Full stack traces with environment variables

#### Error Logging

**Structured Error Logging**:
- Errors logged with context
- Correlation IDs for tracing
- Sensitive data redacted
- Stack traces in DEBUG mode only

### 6. Rate Limiting

#### API Rate Limiting

**Request Throttling**:
- Max 10 concurrent requests (configurable)
- Prevents overwhelming UniFi controller
- Protects against DoS
- Respects controller rate limits

**Retry Logic**:
- Exponential backoff on rate limit errors
- Max 3 retry attempts
- Max 30 second backoff
- Prevents retry storms

### 7. Caching Security

#### Cache Isolation

**Memory-Only Cache**:
- Cache stored in memory only
- Never persisted to disk
- Cleared on server shutdown
- No cache poisoning risk

**Cache Invalidation**:
- Write operations invalidate cache
- TTL-based expiration (30 seconds default)
- No stale security-critical data

## Security Best Practices

### Deployment

#### Production Deployment

1. **Use Strong Credentials**:
   ```bash
   # Generate strong password
   openssl rand -base64 32
   ```

2. **Enable SSL Verification**:
   ```bash
   export UNIFI_VERIFY_SSL=true
   ```

3. **Use Dedicated Service Account**:
   - Create UniFi user with minimal permissions
   - Read-only for monitoring tools
   - Limited write permissions if needed

4. **Restrict File Permissions**:
   ```bash
   chmod 600 .env  # Only owner can read
   ```

5. **Run as Non-Root User**:
   ```bash
   # Create dedicated user
   useradd -r -s /bin/false unifi-mcp
   
   # Run as that user
   sudo -u unifi-mcp python -m unifi_mcp
   ```

6. **Enable Audit Logging**:
   ```yaml
   server:
     log_level: "INFO"
     logging:
       log_to_file: true
       log_file_path: "/var/log/unifi-mcp-server.log"
   ```

#### Development

1. **Use Test Controller**:
   - Never test against production controller
   - Use isolated test environment
   - Separate credentials

2. **Enable Debug Logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   ```

3. **Review Logs Regularly**:
   - Check for suspicious activity
   - Monitor write operations
   - Review authentication failures

### Credential Rotation

#### Regular Rotation

1. **Change UniFi Password**:
   - Rotate every 90 days
   - Use strong, unique passwords
   - Update environment variables

2. **Update Environment Variables**:
   ```bash
   # Update .env file
   vim .env
   
   # Restart server
   systemctl restart unifi-mcp-server
   ```

3. **Audit Access**:
   - Review UniFi user permissions
   - Remove unused accounts
   - Check login history

### Monitoring

#### Security Monitoring

1. **Monitor Write Operations**:
   ```bash
   # Filter logs for write operations
   grep "WRITE OPERATION" /var/log/unifi-mcp-server.log
   ```

2. **Monitor Authentication Failures**:
   ```bash
   # Filter logs for auth failures
   grep "AUTHENTICATION_FAILED" /var/log/unifi-mcp-server.log
   ```

3. **Monitor Unusual Activity**:
   - Excessive API calls
   - Failed tool invocations
   - Unexpected write operations

#### Alerting (Future)

- Alert on write operations
- Alert on authentication failures
- Alert on rate limit exceeded
- Alert on unusual patterns

## Vulnerability Management

### Reporting Vulnerabilities

**Contact**: Create issue in GitHub repository (or email if sensitive)

**Information to Include**:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response Timeline**:
- Acknowledgment: 48 hours
- Initial assessment: 1 week
- Fix timeline: Depends on severity

### Severity Levels

1. **Critical**: Credential exposure, remote code execution
2. **High**: Unauthorized write operations, privilege escalation
3. **Medium**: Information disclosure, DoS
4. **Low**: Minor information leakage, non-security bugs

### Disclosure Policy

- Coordinated disclosure preferred
- 90-day disclosure timeline
- Credit to reporter (if desired)
- Security advisory published

## Incident Response

### Suspected Compromise

#### Immediate Actions

1. **Stop the Server**:
   ```bash
   systemctl stop unifi-mcp-server
   # or
   kill <pid>
   ```

2. **Rotate Credentials**:
   - Change UniFi controller password
   - Update environment variables
   - Revoke any API tokens

3. **Review Logs**:
   ```bash
   # Check for suspicious activity
   grep -E "WRITE OPERATION|AUTHENTICATION_FAILED" /var/log/unifi-mcp-server.log
   ```

4. **Check UniFi Controller**:
   - Review recent configuration changes
   - Check for unauthorized firewall rules
   - Review login history

#### Investigation

1. **Collect Evidence**:
   - Save log files
   - Document timeline
   - Identify affected systems

2. **Analyze Logs**:
   - Identify unauthorized operations
   - Trace back to source
   - Determine scope of compromise

3. **Assess Impact**:
   - What data was accessed?
   - What changes were made?
   - What systems were affected?

#### Recovery

1. **Restore Configuration**:
   - Revert unauthorized changes
   - Restore from backup if needed
   - Verify network functionality

2. **Update Security Controls**:
   - Patch vulnerabilities
   - Strengthen authentication
   - Add monitoring

3. **Resume Operations**:
   - Restart server with new credentials
   - Monitor closely for recurrence
   - Document lessons learned

### Post-Incident

1. **Root Cause Analysis**:
   - What happened?
   - How did it happen?
   - Why did controls fail?

2. **Remediation**:
   - Fix vulnerabilities
   - Improve controls
   - Update procedures

3. **Documentation**:
   - Incident report
   - Timeline
   - Lessons learned

## Security Checklist

### Pre-Deployment

- [ ] Strong, unique credentials configured
- [ ] SSL verification enabled (production)
- [ ] Write operations disabled (unless needed)
- [ ] File permissions restricted (600 for .env)
- [ ] Running as non-root user
- [ ] Audit logging enabled
- [ ] Log file permissions restricted
- [ ] Firewall rules configured (if applicable)

### Post-Deployment

- [ ] Verify server starts successfully
- [ ] Test authentication
- [ ] Verify write operations blocked (if disabled)
- [ ] Check logs for errors
- [ ] Monitor for unusual activity
- [ ] Document deployment

### Regular Maintenance

- [ ] Review logs weekly
- [ ] Rotate credentials quarterly
- [ ] Update dependencies monthly
- [ ] Review security advisories
- [ ] Test backup/restore procedures
- [ ] Audit user permissions

## Security Roadmap

### Current (v1.0.0)

- ✅ Credential management (environment variables)
- ✅ Sensitive data redaction
- ✅ Write operation confirmation
- ✅ Input validation
- ✅ SSL/TLS support
- ✅ Audit logging

### Near-Term (v1.1.0)

- [ ] API key authentication (alternative to password)
- [ ] Role-based access control (RBAC)
- [ ] Rate limiting per client
- [ ] Security headers
- [ ] Content Security Policy

### Medium-Term (v1.2.0)

- [ ] OAuth2 authentication
- [ ] Multi-factor authentication (MFA)
- [ ] Encrypted configuration files
- [ ] Security scanning (SAST/DAST)
- [ ] Penetration testing

### Long-Term (v2.0.0)

- [ ] Zero Trust architecture
- [ ] Hardware security module (HSM) support
- [ ] Secrets management integration (Vault, AWS Secrets Manager)
- [ ] Security Information and Event Management (SIEM) integration
- [ ] Compliance certifications (SOC 2, ISO 27001)

## Compliance

### Data Protection

**GDPR Considerations**:
- Client MAC addresses are personal data
- Client names may be personal data
- No data stored persistently (memory-only cache)
- No data shared with third parties
- User can request data deletion (clear cache)

**Data Minimization**:
- Only collect necessary data
- Cache only for performance
- No long-term storage
- No analytics or tracking

### Audit Requirements

**Audit Trail**:
- All write operations logged
- Authentication events logged
- Correlation IDs for tracing
- Logs retained per policy

**Log Retention**:
- Configurable retention period
- Secure log storage
- Log rotation
- Log backup

## References

### Internal Documentation

- [Architecture Documentation](ARCHITECTURE.md)
- [Configuration Guide](CONFIGURATION.md)
- [Extension Guide](EXTENDING.md)

### External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [UniFi Security Best Practices](https://help.ui.com/hc/en-us/articles/360006893234)

### Security Tools

- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - Protocol testing
- [Bandit](https://github.com/PyCQA/bandit) - Python security linter
- [Safety](https://github.com/pyupio/safety) - Dependency vulnerability scanner
- [OWASP ZAP](https://www.zaproxy.org/) - Security testing

## Changelog

### Version 1.0.0 (October 2025)

- Initial security implementation
- Credential management
- Write operation safety
- Input validation
- Audit logging
- SSL/TLS support

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Security Contact**: Create GitHub issue for security concerns  
**Status**: Production Ready
