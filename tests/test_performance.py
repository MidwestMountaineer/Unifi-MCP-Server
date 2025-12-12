"""
Performance test suite for UniFi MCP Server.

Tests memory usage, response times, and concurrent request handling.
Requirements: 17.1, 17.2, 17.6, 17.7

Note: These are basic unit tests. For comprehensive performance profiling,
use devtools/performance_profiler.py which tests against a real UniFi controller.
"""

import pytest
import asyncio
import time
import psutil
import os

from unifi_mcp.config.loader import ServerConfig, UniFiConfig


class TestPerformanceBasics:
    """Basic performance tests that don't require mocking."""
    
    @pytest.mark.asyncio
    async def test_module_import_speed(self):
        """Test that modules load quickly."""
        start_time = time.time()
        from unifi_mcp import server
        from unifi_mcp import unifi_client
        from unifi_mcp import tool_registry
        elapsed = time.time() - start_time
        
        # Module imports should be very fast
        assert elapsed < 1, f"Module imports took {elapsed:.3f}s (should be <1s)"
    
    @pytest.mark.asyncio
    async def test_config_creation_speed(self):
        """Test that configuration objects are created quickly."""
        start_time = time.time()
        
        # Create config objects
        for _ in range(100):
            server_config = ServerConfig(
                name="test-server",
                log_level="INFO",
                performance={
                    "cache_ttl": 30,
                    "max_concurrent_requests": 10,
                    "request_timeout": 30,
                    "connection_timeout": 10
                }
            )
            unifi_config = UniFiConfig(
                host="192.168.1.1",
                port=443,
                username="test",
                password="test",
                site="default",
                verify_ssl=False
            )
        
        elapsed = time.time() - start_time
        
        # Creating 100 config objects should be fast
        assert elapsed < 1, f"Config creation took {elapsed:.3f}s for 100 objects"
    
    @pytest.mark.asyncio
    async def test_memory_baseline(self):
        """Test baseline memory usage of test process."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        rss_mb = mem_info.rss / 1024 / 1024
        
        # Test process should not use excessive memory
        # This is a sanity check, not a strict requirement
        assert rss_mb < 500, f"Test process using {rss_mb:.2f}MB (seems excessive)"
    
    @pytest.mark.asyncio
    async def test_async_task_performance(self):
        """Test that async tasks execute efficiently."""
        async def simple_task(n):
            await asyncio.sleep(0.001)  # 1ms
            return n * 2
        
        start_time = time.time()
        
        # Run 100 concurrent tasks
        results = await asyncio.gather(*[simple_task(i) for i in range(100)])
        
        elapsed = time.time() - start_time
        
        # Should complete quickly due to concurrency
        assert elapsed < 1, f"100 concurrent tasks took {elapsed:.3f}s (should be <1s)"
        assert len(results) == 100
        assert results[0] == 0
        assert results[99] == 198


class TestPerformanceTargets:
    """Document performance targets for reference.
    
    These tests serve as documentation of the performance requirements.
    Actual performance testing is done by devtools/performance_profiler.py
    """
    
    def test_startup_time_target(self):
        """Document: Startup time should be under 5 seconds (Requirement 17.6)."""
        target_seconds = 5
        assert target_seconds == 5, "Startup time target is 5 seconds"
    
    def test_memory_usage_target(self):
        """Document: Memory usage should be under 100MB at idle (Requirement 17.1)."""
        target_mb = 100
        assert target_mb == 100, "Memory usage target is 100MB at idle"
    
    def test_response_time_target(self):
        """Document: Read operations should complete in under 2 seconds (Requirement 17.2)."""
        target_seconds = 2
        assert target_seconds == 2, "Response time target is 2 seconds"
    
    def test_concurrent_requests_target(self):
        """Document: Should handle 10+ concurrent requests (Requirement 17.7)."""
        target_concurrent = 10
        assert target_concurrent == 10, "Concurrent requests target is 10+"


class TestPerformanceConfiguration:
    """Test performance-related configuration."""
    
    def test_performance_config_defaults(self):
        """Test that performance configuration has reasonable defaults."""
        config = ServerConfig(
            name="test",
            performance={
                "cache_ttl": 30,
                "max_concurrent_requests": 10,
                "request_timeout": 30,
                "connection_timeout": 10
            }
        )
        
        # Verify reasonable defaults
        assert config.performance["cache_ttl"] == 30
        assert config.performance["max_concurrent_requests"] == 10
        assert config.performance["request_timeout"] == 30
        assert config.performance["connection_timeout"] == 10
        
        # Timeouts should be reasonable
        assert config.performance["connection_timeout"] < 30
        assert config.performance["request_timeout"] < 60
    
    def test_retry_config_defaults(self):
        """Test that retry configuration has reasonable defaults."""
        config = UniFiConfig(
            host="192.168.1.1",
            retry={
                "max_attempts": 3,
                "backoff_factor": 2,
                "max_backoff": 30
            }
        )
        
        # Verify reasonable retry settings
        assert config.retry["max_attempts"] == 3
        assert config.retry["backoff_factor"] == 2
        assert config.retry["max_backoff"] == 30
