"""Demo script for retry logic and error handling.

This script demonstrates:
1. Exponential backoff calculation
2. Retry on transient errors
3. No retry on permanent errors
4. Re-authentication on session expiry
5. Rate limiting handling
6. Connection error handling

Run this script to see retry logic in action.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.utils.retry import (
    RetryConfig,
    retry_async,
    with_retry,
    RetryableError,
    NonRetryableError,
)
from unifi_mcp.utils.logging import setup_logging, get_logger


# Set up logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)


async def demo_exponential_backoff():
    """Demonstrate exponential backoff calculation."""
    print("\n" + "="*70)
    print("DEMO 1: Exponential Backoff Calculation")
    print("="*70)
    
    config = RetryConfig(
        initial_backoff=1.0,
        backoff_factor=2.0,
        max_backoff=30
    )
    
    print(f"\nConfiguration:")
    print(f"  Initial backoff: {config.initial_backoff}s")
    print(f"  Backoff factor: {config.backoff_factor}x")
    print(f"  Max backoff: {config.max_backoff}s")
    
    print(f"\nBackoff progression:")
    for attempt in range(10):
        backoff = config.calculate_backoff(attempt)
        print(f"  Attempt {attempt + 1}: {backoff:.1f}s")


async def demo_successful_retry():
    """Demonstrate successful retry after transient failures."""
    print("\n" + "="*70)
    print("DEMO 2: Successful Retry After Transient Failures")
    print("="*70)
    
    call_count = 0
    
    async def flaky_api_call():
        """Simulates an API call that fails twice then succeeds."""
        nonlocal call_count
        call_count += 1
        
        print(f"\n  Attempt {call_count}...")
        
        if call_count == 1:
            print("  ❌ Connection timeout!")
            raise asyncio.TimeoutError("Connection timed out")
        elif call_count == 2:
            print("  ❌ Connection error!")
            raise ConnectionError("Network unreachable")
        else:
            print("  ✅ Success!")
            return {"status": "ok", "data": "Important data"}
    
    config = RetryConfig(max_attempts=3, initial_backoff=0.5)
    
    print("\nCalling flaky API with retry logic...")
    result = await retry_async(flaky_api_call, config=config)
    
    print(f"\n✅ Final result: {result}")
    print(f"Total attempts: {call_count}")


async def demo_exhausted_retries():
    """Demonstrate failure after exhausting all retries."""
    print("\n" + "="*70)
    print("DEMO 3: Exhausted Retries (Persistent Failure)")
    print("="*70)
    
    call_count = 0
    
    async def always_fails():
        """Simulates an API call that always fails."""
        nonlocal call_count
        call_count += 1
        print(f"\n  Attempt {call_count}...")
        print("  ❌ Connection error!")
        raise ConnectionError("Service unavailable")
    
    config = RetryConfig(max_attempts=3, initial_backoff=0.5)
    
    print("\nCalling API that always fails...")
    try:
        await retry_async(always_fails, config=config)
    except ConnectionError as e:
        print(f"\n❌ All retries exhausted: {e}")
        print(f"Total attempts: {call_count}")


async def demo_non_retryable_error():
    """Demonstrate no retry on permanent errors."""
    print("\n" + "="*70)
    print("DEMO 4: Non-Retryable Error (No Retry)")
    print("="*70)
    
    call_count = 0
    
    async def invalid_input():
        """Simulates an API call with invalid input."""
        nonlocal call_count
        call_count += 1
        print(f"\n  Attempt {call_count}...")
        print("  ❌ Invalid input!")
        raise ValueError("Invalid parameter: user_id must be positive")
    
    config = RetryConfig(max_attempts=3, initial_backoff=0.5)
    
    print("\nCalling API with invalid input...")
    try:
        await retry_async(invalid_input, config=config)
    except ValueError as e:
        print(f"\n❌ Non-retryable error (no retry): {e}")
        print(f"Total attempts: {call_count} (should be 1)")


async def demo_decorator():
    """Demonstrate using the @with_retry decorator."""
    print("\n" + "="*70)
    print("DEMO 5: Using @with_retry Decorator")
    print("="*70)
    
    call_count = 0
    
    @with_retry(config=RetryConfig(max_attempts=3, initial_backoff=0.5))
    async def fetch_user_data(user_id: int):
        """Fetch user data with automatic retry."""
        nonlocal call_count
        call_count += 1
        
        print(f"\n  Fetching user {user_id}, attempt {call_count}...")
        
        if call_count < 2:
            print("  ❌ Timeout!")
            raise asyncio.TimeoutError()
        
        print("  ✅ Success!")
        return {"id": user_id, "name": "John Doe", "email": "john@example.com"}
    
    print("\nCalling decorated function...")
    result = await fetch_user_data(123)
    
    print(f"\n✅ Result: {result}")
    print(f"Total attempts: {call_count}")


async def demo_session_expiry():
    """Demonstrate handling session expiry with re-authentication."""
    print("\n" + "="*70)
    print("DEMO 6: Session Expiry and Re-authentication")
    print("="*70)
    
    call_count = 0
    authenticated = True
    
    async def api_call_with_session():
        """Simulates an API call that may have expired session."""
        nonlocal call_count, authenticated
        call_count += 1
        
        print(f"\n  Attempt {call_count}...")
        
        if call_count == 1:
            # First call: session expired
            authenticated = False
            print("  ❌ Session expired (401)!")
            
            # In real implementation, this would trigger re-authentication
            class SessionExpiredError(RetryableError):
                pass
            
            raise SessionExpiredError("Session expired, re-authentication required")
        else:
            # After retry, session is re-authenticated
            if not authenticated:
                print("  🔄 Re-authenticating...")
                await asyncio.sleep(0.1)
                authenticated = True
                print("  ✅ Re-authenticated!")
            
            print("  ✅ API call successful!")
            return {"data": "Protected resource"}
    
    config = RetryConfig(max_attempts=3, initial_backoff=0.5)
    
    print("\nCalling API with expired session...")
    result = await retry_async(api_call_with_session, config=config)
    
    print(f"\n✅ Result: {result}")
    print(f"Total attempts: {call_count}")


async def demo_rate_limiting():
    """Demonstrate handling rate limiting."""
    print("\n" + "="*70)
    print("DEMO 7: Rate Limiting Handling")
    print("="*70)
    
    call_count = 0
    
    async def rate_limited_api():
        """Simulates an API with rate limiting."""
        nonlocal call_count
        call_count += 1
        
        print(f"\n  Attempt {call_count}...")
        
        if call_count == 1:
            print("  ❌ Rate limit exceeded (429)!")
            print("  ⏳ Retry after: 2 seconds")
            
            class RateLimitError(RetryableError):
                pass
            
            raise RateLimitError("Rate limit exceeded. Retry after: 2")
        else:
            print("  ✅ Success!")
            return {"data": "Rate limit cleared"}
    
    config = RetryConfig(max_attempts=3, initial_backoff=2.0)
    
    print("\nCalling rate-limited API...")
    result = await retry_async(rate_limited_api, config=config)
    
    print(f"\n✅ Result: {result}")
    print(f"Total attempts: {call_count}")


async def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("RETRY LOGIC AND ERROR HANDLING DEMO")
    print("="*70)
    print("\nThis demo showcases the retry logic with exponential backoff")
    print("and various error handling scenarios.")
    
    try:
        await demo_exponential_backoff()
        await demo_successful_retry()
        await demo_exhausted_retries()
        await demo_non_retryable_error()
        await demo_decorator()
        await demo_session_expiry()
        await demo_rate_limiting()
        
        print("\n" + "="*70)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nKey Takeaways:")
        print("  ✅ Exponential backoff prevents overwhelming services")
        print("  ✅ Transient errors are automatically retried")
        print("  ✅ Permanent errors fail fast without retry")
        print("  ✅ Session expiry triggers re-authentication")
        print("  ✅ Rate limiting is handled gracefully")
        print("  ✅ Clear error messages help with debugging")
        print()
    
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
