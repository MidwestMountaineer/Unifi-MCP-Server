# Retry Logic and Error Handling

This document describes the retry logic and error handling mechanisms implemented in the UniFi MCP Server.

## Overview

The server implements robust retry logic with exponential backoff to handle transient errors gracefully. This ensures reliable operation even when facing network issues, temporary service unavailability, or rate limiting.

## Key Features

- **Exponential Backoff**: Progressively longer delays between retries to avoid overwhelming services
- **Smart Error Classification**: Distinguishes between retryable and non-retryable errors
- **Automatic Re-authentication**: Handles session expiry transparently
- **Rate Limiting**: Respects API rate limits with appropriate backoff
- **Structured Logging**: Detailed logging of retry attempts for debugging

## Retry Configuration

### Default Configuration

```python
RetryConfig(
    max_attempts=3,        # Maximum number of attempts (including initial)
    backoff_factor=2.0,    # Exponential multiplier
    max_backoff=30,        # Maximum backoff time in seconds
    initial_backoff=1.0    # Initial backoff time in seconds
)
```

### Backoff Calculation

The backoff time is calculated using exponential backoff:

```
backoff = initial_backoff * (backoff_factor ^ attempt)
```

Capped at `max_backoff` to prevent excessive delays.

**Example progression** (initial=1.0, factor=2.0, max=30):
- Attempt 1: 1.0s
- Attempt 2: 2.0s
- Attempt 3: 4.0s
- Attempt 4: 8.0s
- Attempt 5: 16.0s
- Attempt 6+: 30.0s (capped)

## Error Classification

### Retryable Errors

These errors trigger automatic retry:

- `asyncio.TimeoutError` - Request timeout
- `ConnectionError` - Network connection issues
- `ConnectionResetError` - Connection reset by peer
- `ConnectionRefusedError` - Connection refused
- `SessionExpiredError` - Session expired (401)
- `RateLimitError` - Rate limit exceeded (429)
- `RetryableError` - Base class for custom retryable errors

### Non-Retryable Errors

These errors fail immediately without retry:

- `ValueError` - Invalid input parameters
- `TypeError` - Type mismatch
- `KeyError` - Missing required key
- `AttributeError` - Missing attribute
- `AuthenticationError` - Invalid credentials
- `NonRetryableError` - Base class for custom non-retryable errors

### HTTP Status Code Handling

- **401 Unauthorized**: Session expired → Mark as unauthenticated, retry with re-auth
- **429 Too Many Requests**: Rate limit → Retry with backoff
- **5xx Server Errors**: Temporary server issue → Retry
- **4xx Client Errors** (except 401, 429): Invalid request → No retry

## Usage Examples

### Basic Usage with retry_async

```python
from unifi_mcp.utils.retry import retry_async, RetryConfig

async def fetch_data():
    # May raise ConnectionError or TimeoutError
    return await api.get("/data")

# Retry with default configuration
result = await retry_async(fetch_data)

# Retry with custom configuration
config = RetryConfig(max_attempts=5, initial_backoff=2.0)
result = await retry_async(fetch_data, config=config)
```

### Using the @with_retry Decorator

```python
from unifi_mcp.utils.retry import with_retry, RetryConfig

@with_retry(config=RetryConfig(max_attempts=3))
async def fetch_user_data(user_id: int):
    return await api.get(f"/users/{user_id}")

# Automatically retries on transient errors
user = await fetch_user_data(123)
```

### Custom Error Classification

```python
from unifi_mcp.utils.retry import retry_async, RetryableError

class CustomAPIError(RetryableError):
    """Custom retryable error."""
    pass

async def api_call():
    if service_unavailable:
        raise CustomAPIError("Service temporarily unavailable")
    return data

# CustomAPIError will trigger retry
result = await retry_async(api_call)
```

## UniFi Client Integration

The UniFi client automatically uses retry logic for all API requests:

```python
from unifi_mcp.unifi_client import UniFiClient

async with UniFiClient(config) as client:
    # Automatically retries on transient errors
    devices = await client.get("/api/s/default/stat/device")
    
    # Handles session expiry with re-authentication
    clients = await client.get("/api/s/default/stat/sta")
```

### Session Expiry Handling

When a 401 Unauthorized response is received:

1. Client marks session as unauthenticated
2. Retry logic triggers another attempt
3. `_ensure_authenticated()` detects unauthenticated state
4. Client re-authenticates automatically
5. Request is retried with new session

```python
async def _ensure_authenticated(self) -> None:
    """Ensure the client is authenticated, re-authenticating if necessary."""
    if self.use_api_key:
        return  # API key auth doesn't expire
    
    if not self.authenticated:
        logger.info("Session expired, re-authenticating...")
        await self._authenticate()
```

### Rate Limiting

When a 429 Too Many Requests response is received:

1. Client raises `RateLimitError`
2. Retry logic applies exponential backoff
3. Request is retried after delay
4. Respects `Retry-After` header if present

## Logging

All retry attempts are logged with structured information:

```
2025-10-08 22:17:41 [WARNING] unifi_mcp.utils.retry: Retryable error occurred, retrying in 1.0s: ConnectionError: Network unreachable
  function: fetch_data
  attempt: 1
  attempts_remaining: 2
  backoff_seconds: 1.0
  error_type: ConnectionError
```

Successful retries are logged at INFO level:

```
2025-10-08 22:17:42 [INFO] unifi_mcp.utils.retry: Operation succeeded after 3 attempts
  function: fetch_data
  attempt: 3
```

## Best Practices

### 1. Use Appropriate Retry Configuration

- **Read operations**: Default config (3 attempts, 1s initial backoff)
- **Write operations**: Fewer attempts (2-3) to avoid duplicate writes
- **Rate-limited APIs**: Longer initial backoff (2-5s)

### 2. Classify Errors Correctly

- Use `RetryableError` for transient issues
- Use `NonRetryableError` for permanent failures
- Inherit from appropriate base classes

### 3. Handle Idempotency

For write operations, ensure they are idempotent or use additional safeguards:

```python
@with_retry(config=RetryConfig(max_attempts=2))
async def update_firewall_rule(rule_id: str, data: dict):
    # Include idempotency key or check current state
    current = await client.get(f"/api/firewall/rule/{rule_id}")
    if current == data:
        return current  # Already updated
    
    return await client.post(f"/api/firewall/rule/{rule_id}", json=data)
```

### 4. Monitor Retry Metrics

Track retry attempts in production:

```python
# Log retry metrics for monitoring
logger.info(
    "Retry metrics",
    extra={
        "total_attempts": attempt_count,
        "success": success,
        "error_type": error_type,
        "endpoint": endpoint
    }
)
```

## Testing

### Unit Tests

Test retry behavior with mocked functions:

```python
@pytest.mark.asyncio
async def test_retry_on_transient_error():
    mock_func = AsyncMock(
        side_effect=[
            ConnectionError("first failure"),
            ConnectionError("second failure"),
            "success"
        ]
    )
    
    config = RetryConfig(max_attempts=3, initial_backoff=0.01)
    result = await retry_async(mock_func, config=config)
    
    assert result == "success"
    assert mock_func.call_count == 3
```

### Integration Tests

Test with real API calls:

```python
@pytest.mark.asyncio
async def test_session_expiry_handling():
    # Simulate session expiry
    client = UniFiClient(config)
    await client.connect()
    
    # Force session expiry
    client.authenticated = False
    
    # Should re-authenticate automatically
    result = await client.get("/api/s/default/stat/device")
    
    assert client.authenticated is True
    assert result is not None
```

## Troubleshooting

### Issue: Too Many Retries

**Symptom**: Requests take too long due to excessive retries

**Solution**: Reduce `max_attempts` or increase `initial_backoff`

```python
config = RetryConfig(max_attempts=2, initial_backoff=2.0)
```

### Issue: Not Retrying When Expected

**Symptom**: Errors that should retry are failing immediately

**Solution**: Ensure error inherits from `RetryableError` or is in the retryable set

```python
class MyError(RetryableError):  # Inherit from RetryableError
    pass
```

### Issue: Retrying Non-Idempotent Operations

**Symptom**: Write operations being executed multiple times

**Solution**: Reduce retries for write operations or implement idempotency

```python
# Option 1: Fewer retries
config = RetryConfig(max_attempts=1)  # No retries

# Option 2: Idempotency check
async def safe_write():
    if not already_written():
        await write_operation()
```

## Performance Considerations

### Memory Usage

Retry logic has minimal memory overhead:
- No persistent state between retries
- Async/await prevents thread blocking
- Backoff uses `asyncio.sleep()` (non-blocking)

### Latency

Retry adds latency only on failures:
- **Success on first attempt**: No additional latency
- **Success after retries**: Sum of backoff delays
- **Example**: 3 attempts with 1s, 2s backoff = ~3s additional latency

### Throughput

Retry logic doesn't limit throughput:
- Concurrent requests are independent
- Each request has its own retry state
- No global rate limiting (unless explicitly added)

## Related Documentation

- [UniFi Client Documentation](UNIFI-CLIENT.md)
- [Logging Documentation](LOGGING.md)
- [Error Handling Best Practices](../README.md#error-handling)

## Examples

See `examples/retry_demo.py` for comprehensive demonstrations of:
- Exponential backoff calculation
- Successful retry after transient failures
- Exhausted retries
- Non-retryable errors
- Decorator usage
- Session expiry handling
- Rate limiting

Run the demo:

```bash
python examples/retry_demo.py
```
