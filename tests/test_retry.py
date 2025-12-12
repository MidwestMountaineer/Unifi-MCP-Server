"""Tests for retry logic with exponential backoff.

This module tests the retry utilities including:
- Exponential backoff calculation
- Retry on transient errors
- No retry on permanent errors
- Maximum attempts enforcement
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.utils.retry import (
    RetryConfig,
    retry_async,
    with_retry,
    is_retryable_error,
    RetryableError,
    NonRetryableError,
)


class TestRetryConfig:
    """Tests for RetryConfig class."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.backoff_factor == 2.0
        assert config.max_backoff == 30
        assert config.initial_backoff == 1.0
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            backoff_factor=3.0,
            max_backoff=60,
            initial_backoff=2.0
        )
        
        assert config.max_attempts == 5
        assert config.backoff_factor == 3.0
        assert config.max_backoff == 60
        assert config.initial_backoff == 2.0
    
    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(
            initial_backoff=1.0,
            backoff_factor=2.0,
            max_backoff=30
        )
        
        # First retry: 1.0 * 2^0 = 1.0
        assert config.calculate_backoff(0) == 1.0
        
        # Second retry: 1.0 * 2^1 = 2.0
        assert config.calculate_backoff(1) == 2.0
        
        # Third retry: 1.0 * 2^2 = 4.0
        assert config.calculate_backoff(2) == 4.0
        
        # Fourth retry: 1.0 * 2^3 = 8.0
        assert config.calculate_backoff(3) == 8.0
    
    def test_backoff_max_cap(self):
        """Test that backoff is capped at max_backoff."""
        config = RetryConfig(
            initial_backoff=1.0,
            backoff_factor=2.0,
            max_backoff=10
        )
        
        # 1.0 * 2^10 = 1024, but should be capped at 10
        assert config.calculate_backoff(10) == 10
        
        # 1.0 * 2^20 = 1048576, but should be capped at 10
        assert config.calculate_backoff(20) == 10


class TestIsRetryableError:
    """Tests for error classification."""
    
    def test_retryable_errors(self):
        """Test that retryable errors are identified correctly."""
        assert is_retryable_error(asyncio.TimeoutError()) is True
        assert is_retryable_error(ConnectionError("test")) is True
        assert is_retryable_error(ConnectionResetError()) is True
        assert is_retryable_error(ConnectionRefusedError()) is True
        assert is_retryable_error(RetryableError()) is True
    
    def test_non_retryable_errors(self):
        """Test that non-retryable errors are identified correctly."""
        assert is_retryable_error(ValueError("test")) is False
        assert is_retryable_error(TypeError("test")) is False
        assert is_retryable_error(KeyError("test")) is False
        assert is_retryable_error(AttributeError("test")) is False
        assert is_retryable_error(NonRetryableError()) is False
    
    def test_unknown_errors_not_retried(self):
        """Test that unknown errors are not retried by default."""
        class CustomError(Exception):
            pass
        
        assert is_retryable_error(CustomError()) is False
    
    def test_custom_retryable_errors(self):
        """Test custom retryable error sets."""
        class CustomError(Exception):
            pass
        
        retryable = {CustomError}
        assert is_retryable_error(CustomError(), retryable_errors=retryable) is True
    
    def test_non_retryable_takes_precedence(self):
        """Test that non-retryable errors take precedence over retryable."""
        class AmbiguousError(Exception):
            pass
        
        retryable = {AmbiguousError}
        non_retryable = {AmbiguousError}
        
        # Should NOT retry because non-retryable takes precedence
        assert is_retryable_error(
            AmbiguousError(),
            retryable_errors=retryable,
            non_retryable_errors=non_retryable
        ) is False


class TestRetryAsync:
    """Tests for retry_async function."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test that successful calls don't retry."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_async(mock_func, config=RetryConfig(max_attempts=3))
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test that function succeeds after transient failures."""
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
    
    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test that function fails after exhausting retries."""
        mock_func = AsyncMock(side_effect=ConnectionError("persistent failure"))
        
        config = RetryConfig(max_attempts=3, initial_backoff=0.01)
        
        with pytest.raises(ConnectionError, match="persistent failure"):
            await retry_async(mock_func, config=config)
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors don't trigger retries."""
        mock_func = AsyncMock(side_effect=ValueError("invalid input"))
        
        config = RetryConfig(max_attempts=3, initial_backoff=0.01)
        
        with pytest.raises(ValueError, match="invalid input"):
            await retry_async(mock_func, config=config)
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """Test that backoff delays are applied."""
        mock_func = AsyncMock(
            side_effect=[
                ConnectionError("first"),
                ConnectionError("second"),
                "success"
            ]
        )
        
        config = RetryConfig(
            max_attempts=3,
            initial_backoff=0.1,
            backoff_factor=2.0
        )
        
        import time
        start = time.time()
        result = await retry_async(mock_func, config=config)
        elapsed = time.time() - start
        
        assert result == "success"
        # Should have waited at least 0.1 + 0.2 = 0.3 seconds
        assert elapsed >= 0.3
    
    @pytest.mark.asyncio
    async def test_with_arguments(self):
        """Test retry with function arguments."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_async(
            mock_func,
            "arg1",
            "arg2",
            kwarg1="value1",
            config=RetryConfig(max_attempts=3)
        )
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test decorator on successful function."""
        @with_retry(config=RetryConfig(max_attempts=3))
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_with_retries(self):
        """Test decorator with retries."""
        call_count = 0
        
        @with_retry(config=RetryConfig(max_attempts=3, initial_backoff=0.01))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_decorator_with_arguments(self):
        """Test decorator preserves function arguments."""
        @with_retry(config=RetryConfig(max_attempts=3))
        async def test_func(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = await test_func("x", "y", c="z")
        assert result == "x-y-z"
    
    @pytest.mark.asyncio
    async def test_decorator_exhausted_retries(self):
        """Test decorator fails after exhausting retries."""
        @with_retry(config=RetryConfig(max_attempts=3, initial_backoff=0.01))
        async def test_func():
            raise ConnectionError("persistent")
        
        with pytest.raises(ConnectionError, match="persistent"):
            await test_func()


class TestRetryIntegration:
    """Integration tests for retry logic."""
    
    @pytest.mark.asyncio
    async def test_realistic_api_scenario(self):
        """Test realistic API call scenario with transient failures."""
        call_count = 0
        
        async def api_call():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call: timeout
                raise asyncio.TimeoutError()
            elif call_count == 2:
                # Second call: connection error
                raise ConnectionError("network issue")
            else:
                # Third call: success
                return {"data": "success"}
        
        config = RetryConfig(max_attempts=3, initial_backoff=0.01)
        result = await retry_async(api_call, config=config)
        
        assert result == {"data": "success"}
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_mixed_error_types(self):
        """Test handling of mixed error types."""
        call_count = 0
        
        async def api_call():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Retryable error
                raise ConnectionError("transient")
            elif call_count == 2:
                # Non-retryable error
                raise ValueError("invalid input")
            else:
                return "success"
        
        config = RetryConfig(max_attempts=3, initial_backoff=0.01)
        
        # Should fail on the ValueError without further retries
        with pytest.raises(ValueError, match="invalid input"):
            await retry_async(api_call, config=config)
        
        assert call_count == 2
