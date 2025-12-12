# Performance Profiler - Quick Reference Guide

## Overview

The performance profiler (`performance_profiler.py`) is a comprehensive tool for measuring and validating the performance characteristics of the UniFi MCP Server.

## Quick Start

```bash
# From project root
cd projects/unifi-mcp-server

# Run the profiler
python devtools/performance_profiler.py
```

## What It Tests

### 1. Startup Time ⏱️
- Measures time to initialize server and connect to UniFi controller
- **Target**: <5 seconds
- **Current**: ~0.095s

### 2. Memory Usage 💾
- **Idle**: Memory usage with server running but no requests
- **Under Load**: Memory usage during high request volume
- **Target**: <100 MB RSS at idle
- **Current**: ~68 MB idle, ~71 MB under load

### 3. Response Times ⚡
Tests common read operations:
- `list_devices` - Get all network devices
- `list_clients` - Get all connected clients
- `list_networks` - Get network configurations
- `list_wlans` - Get wireless networks
- `get_health` - Get system health

**Target**: <2 seconds per operation  
**Current**: <0.02s average

### 4. Concurrent Requests 🔄
- Tests handling of multiple simultaneous requests
- **Target**: 10+ concurrent requests
- **Current**: 10/10 successful

## Sample Output

```
============================================================
UniFi MCP Server - Performance Profiling
============================================================

=== Profiling Startup Time ===
✓ Startup time: 0.095s
  Target: <5 seconds
  Status: ✓ PASS

=== Profiling Memory Usage (Idle) ===
✓ RSS Memory: 68.03 MB
✓ VMS Memory: 50.48 MB
  Target: <100 MB RSS
  Status: ✓ PASS

=== Profiling Response Times ===
✓ list_devices:
    Avg: 0.019s | Min: 0.000s | Max: 0.095s | P95: 0.095s
    Status: ✓ PASS (target: <2s)
...

============================================================
OVERALL: ✓ ALL TESTS PASSED
============================================================
```

## Requirements

### Python Packages
- `psutil>=5.9.0` - For memory profiling
- `aiohttp>=3.9.0` - For async HTTP
- All standard project dependencies

### Configuration
- Valid `.env` file with UniFi credentials
- Access to UniFi controller
- Network connectivity

## Understanding Results

### Startup Time
- **Good**: <1 second
- **Acceptable**: 1-5 seconds
- **Needs Optimization**: >5 seconds

### Memory Usage
- **Excellent**: <70 MB
- **Good**: 70-100 MB
- **Acceptable**: 100-150 MB
- **Needs Optimization**: >150 MB

### Response Times
- **Excellent**: <0.1s
- **Good**: 0.1-1s
- **Acceptable**: 1-2s
- **Needs Optimization**: >2s

### Concurrent Requests
- **Excellent**: 100% success rate
- **Good**: >90% success rate
- **Acceptable**: >80% success rate
- **Needs Optimization**: <80% success rate

## Troubleshooting

### Connection Errors
```
✗ Profiling failed: Connection refused
```
**Solution**: Check UniFi controller is running and accessible

### Authentication Errors
```
✗ Profiling failed: Authentication failed
```
**Solution**: Verify credentials in `.env` file

### Timeout Errors
```
✗ Profiling failed: Request timeout
```
**Solution**: Check network connectivity and controller responsiveness

### Memory Errors
```
Memory usage 150.00 MB exceeds target
```
**Solution**: This may indicate a memory leak or inefficient code

## When to Run

### Regular Testing
- Before releases
- After major code changes
- When adding new features
- Weekly/monthly monitoring

### Performance Issues
- User reports slow responses
- Memory usage concerns
- Startup time complaints
- Concurrent request failures

### Benchmarking
- Comparing different implementations
- Testing optimization changes
- Validating performance improvements
- Regression testing

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Performance Tests
  run: |
    python devtools/performance_profiler.py
  env:
    UNIFI_HOST: ${{ secrets.UNIFI_HOST }}
    UNIFI_USERNAME: ${{ secrets.UNIFI_USERNAME }}
    UNIFI_PASSWORD: ${{ secrets.UNIFI_PASSWORD }}
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-push

echo "Running performance profiler..."
python devtools/performance_profiler.py

if [ $? -ne 0 ]; then
    echo "Performance tests failed!"
    exit 1
fi
```

## Advanced Usage

### Custom Test Runs

Modify `performance_profiler.py` to:
- Test specific operations
- Adjust concurrent request count
- Change test iterations
- Add custom metrics

### Example Modifications

```python
# Test with more concurrent requests
await self.profile_concurrent_requests(client, num_concurrent=50)

# Test specific operation multiple times
for i in range(10):
    await self.profile_response_times(client)
```

## Related Tools

### Unit Tests
```bash
# Run performance unit tests
pytest tests/test_performance.py -v
```

### Coverage Analysis
```bash
# Run with coverage
pytest tests/test_performance.py --cov=unifi_mcp
```

### Memory Profiling
```bash
# Detailed memory profiling
python -m memory_profiler devtools/performance_profiler.py
```

## Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Startup Time | <5s | 0.095s | ✅ |
| Memory (Idle) | <100MB | 68MB | ✅ |
| Response Time | <2s | <0.02s | ✅ |
| Concurrent | 10+ | 10/10 | ✅ |

## Best Practices

1. **Run in Production-like Environment**: Test with realistic network conditions
2. **Multiple Runs**: Run several times to account for variance
3. **Monitor Trends**: Track performance over time
4. **Document Changes**: Note any performance regressions
5. **Baseline Comparison**: Compare against previous results

## Support

For issues or questions:
1. Check `docs/TASK-30-SUMMARY.md` for detailed results
2. Review `tests/test_performance.py` for unit tests
3. Consult `docs/ARCHITECTURE.md` for system design
4. Open an issue with profiler output

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Status**: Production Ready
