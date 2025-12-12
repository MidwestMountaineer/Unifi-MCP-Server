"""Retry logic with exponential backoff for API requests.

This module provides utilities for retrying failed operations with exponential
backoff. It's designed to handle transient errors like network timeouts and
rate limiting while avoiding retries for permanent errors like authentication
failures.

Key Features:
- Exponential backoff with configurable parameters
- Distinction between retryable and non-retryable errors
- Structured logging of retry attempts
- Configurable maximum attempts and backoff limits
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Set, Type, TypeVar
from functools import wraps

from unifi_mcp.utils.logging import get_logger


# Type variable for generic return type
T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of retry attempts (including initial attempt)
        backoff_factor: Multiplier for exponential backoff (e.g., 2.0 = double each time)
        max_backoff: Maximum backoff time in seconds
        initial_backoff: Initial backoff time in seconds
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        max_backoff: int = 30,
        initial_backoff: float = 1.0
    ):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of attempts (default: 3)
            backoff_factor: Exponential backoff multiplier (default: 2.0)
            max_backoff: Maximum backoff time in seconds (default: 30)
            initial_backoff: Initial backoff time in seconds (default: 1.0)
        """
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.initial_backoff = initial_backoff
        self.logger = get_logger(__name__)
    
    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff time for a given attempt number.
        
        Uses exponential backoff: initial_backoff * (backoff_factor ^ attempt)
        Capped at max_backoff.
        
        Args:
            attempt: Attempt number (0-indexed)
        
        Returns:
            Backoff time in seconds
        
        Example:
            >>> config = RetryConfig(initial_backoff=1.0, backoff_factor=2.0, max_backoff=30)
            >>> config.calculate_backoff(0)  # First retry
            1.0
            >>> config.calculate_backoff(1)  # Second retry
            2.0
            >>> config.calculate_backoff(2)  # Third retry
            4.0
            >>> config.calculate_backoff(10)  # Would be 1024, but capped
            30.0
        """
        backoff = self.initial_backoff * (self.backoff_factor ** attempt)
        return min(backoff, self.max_backoff)


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger a retry."""
    pass


# Default retryable error types
DEFAULT_RETRYABLE_ERRORS: Set[Type[Exception]] = {
    asyncio.TimeoutError,
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
    RetryableError,
}

# Default non-retryable error types
DEFAULT_NON_RETRYABLE_ERRORS: Set[Type[Exception]] = {
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    NonRetryableError,
}


def is_retryable_error(
    error: Exception,
    retryable_errors: Optional[Set[Type[Exception]]] = None,
    non_retryable_errors: Optional[Set[Type[Exception]]] = None
) -> bool:
    """Determine if an error should trigger a retry.
    
    Args:
        error: The exception that occurred
        retryable_errors: Set of exception types that should be retried
        non_retryable_errors: Set of exception types that should NOT be retried
    
    Returns:
        True if the error should trigger a retry, False otherwise
    
    Note:
        Non-retryable errors take precedence over retryable errors.
        If an error matches both sets, it will NOT be retried.
    """
    if retryable_errors is None:
        retryable_errors = DEFAULT_RETRYABLE_ERRORS
    
    if non_retryable_errors is None:
        non_retryable_errors = DEFAULT_NON_RETRYABLE_ERRORS
    
    # Check if error is explicitly non-retryable
    if any(isinstance(error, err_type) for err_type in non_retryable_errors):
        return False
    
    # Check if error is retryable
    if any(isinstance(error, err_type) for err_type in retryable_errors):
        return True
    
    # Default: don't retry unknown errors
    return False


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    retryable_errors: Optional[Set[Type[Exception]]] = None,
    non_retryable_errors: Optional[Set[Type[Exception]]] = None,
    **kwargs
) -> T:
    """Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        retryable_errors: Set of exception types that should be retried
        non_retryable_errors: Set of exception types that should NOT be retried
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of successful function call
    
    Raises:
        Exception: The last exception if all retries fail
    
    Example:
        >>> async def fetch_data():
        ...     # May raise ConnectionError
        ...     return await api.get("/data")
        >>> 
        >>> result = await retry_async(fetch_data, config=RetryConfig(max_attempts=3))
    """
    if config is None:
        config = RetryConfig()
    
    logger = get_logger(__name__)
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            # Attempt the function call
            result = await func(*args, **kwargs)
            
            # Success!
            if attempt > 0:
                logger.info(
                    f"Operation succeeded after {attempt + 1} attempts",
                    extra={"function": func.__name__, "attempt": attempt + 1}
                )
            
            return result
        
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            should_retry = is_retryable_error(e, retryable_errors, non_retryable_errors)
            
            # Check if we have attempts remaining
            attempts_remaining = config.max_attempts - attempt - 1
            
            if not should_retry:
                logger.warning(
                    f"Non-retryable error occurred: {type(e).__name__}: {e}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__
                    }
                )
                raise
            
            if attempts_remaining == 0:
                logger.error(
                    f"All retry attempts exhausted: {type(e).__name__}: {e}",
                    extra={
                        "function": func.__name__,
                        "total_attempts": config.max_attempts,
                        "error_type": type(e).__name__
                    }
                )
                raise
            
            # Calculate backoff and wait
            backoff = config.calculate_backoff(attempt)
            
            logger.warning(
                f"Retryable error occurred, retrying in {backoff:.1f}s: {type(e).__name__}: {e}",
                extra={
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "attempts_remaining": attempts_remaining,
                    "backoff_seconds": backoff,
                    "error_type": type(e).__name__
                }
            )
            
            await asyncio.sleep(backoff)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry logic failed without exception")


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_errors: Optional[Set[Type[Exception]]] = None,
    non_retryable_errors: Optional[Set[Type[Exception]]] = None
):
    """Decorator to add retry logic to an async function.
    
    Args:
        config: Retry configuration (uses defaults if None)
        retryable_errors: Set of exception types that should be retried
        non_retryable_errors: Set of exception types that should NOT be retried
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @with_retry(config=RetryConfig(max_attempts=3))
        ... async def fetch_data():
        ...     return await api.get("/data")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func,
                *args,
                config=config,
                retryable_errors=retryable_errors,
                non_retryable_errors=non_retryable_errors,
                **kwargs
            )
        return wrapper
    return decorator
