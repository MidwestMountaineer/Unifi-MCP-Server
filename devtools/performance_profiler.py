#!/usr/bin/env python3
"""
Performance profiling tool for UniFi MCP Server.

This script profiles:
- Memory usage (idle and under load)
- Startup time
- Response times for read operations
- Concurrent request handling

Requirements: 17.1, 17.2, 17.6, 17.7
"""

import asyncio
import time
import psutil
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.config.loader import load_config
from unifi_mcp.unifi_client import UniFiClient
from unifi_mcp.server import UniFiMCPServer


class PerformanceProfiler:
    """Profile performance metrics for the UniFi MCP Server."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.results = {
            "memory": {},
            "startup": {},
            "response_times": {},
            "concurrent": {}
        }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in MB."""
        mem_info = self.process.memory_info()
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        }
    
    async def profile_startup_time(self) -> float:
        """Profile server startup time."""
        print("\n=== Profiling Startup Time ===")
        
        start_time = time.time()
        
        # Load configuration
        config = load_config()
        
        # Initialize server (which creates and connects the client)
        server = UniFiMCPServer(config)
        
        # Connect to UniFi controller
        await server.unifi_client.connect()
        
        startup_time = time.time() - start_time
        
        print(f"✓ Startup time: {startup_time:.3f}s")
        print(f"  Target: <5 seconds")
        print(f"  Status: {'✓ PASS' if startup_time < 5 else '✗ FAIL'}")
        
        self.results["startup"]["time_seconds"] = startup_time
        self.results["startup"]["target_seconds"] = 5
        self.results["startup"]["pass"] = startup_time < 5
        
        return startup_time
    
    async def profile_memory_idle(self) -> Dict[str, float]:
        """Profile memory usage at idle."""
        print("\n=== Profiling Memory Usage (Idle) ===")
        
        # Load configuration
        config = load_config()
        server = UniFiMCPServer(config)
        await server.unifi_client.connect()
        
        # Wait a moment for everything to settle
        await asyncio.sleep(2)
        
        mem_usage = self.get_memory_usage()
        
        print(f"✓ RSS Memory: {mem_usage['rss_mb']:.2f} MB")
        print(f"✓ VMS Memory: {mem_usage['vms_mb']:.2f} MB")
        print(f"  Target: <100 MB RSS")
        print(f"  Status: {'✓ PASS' if mem_usage['rss_mb'] < 100 else '✗ FAIL'}")
        
        self.results["memory"]["idle_rss_mb"] = mem_usage['rss_mb']
        self.results["memory"]["idle_vms_mb"] = mem_usage['vms_mb']
        self.results["memory"]["target_mb"] = 100
        self.results["memory"]["idle_pass"] = mem_usage['rss_mb'] < 100
        
        return mem_usage
    
    async def profile_response_times(self, client: UniFiClient) -> Dict[str, List[float]]:
        """Profile response times for common read operations."""
        print("\n=== Profiling Response Times ===")
        
        operations = [
            ("list_devices", lambda: client.get("/api/s/default/stat/device")),
            ("list_clients", lambda: client.get("/api/s/default/stat/sta")),
            ("list_networks", lambda: client.get("/api/s/default/rest/networkconf")),
            ("list_wlans", lambda: client.get("/api/s/default/rest/wlanconf")),
            ("get_health", lambda: client.get("/api/s/default/stat/health")),
        ]
        
        response_times = {}
        
        for op_name, op_func in operations:
            times = []
            
            # Run each operation 5 times
            for i in range(5):
                start_time = time.time()
                try:
                    await op_func()
                    elapsed = time.time() - start_time
                    times.append(elapsed)
                except Exception as e:
                    print(f"  ✗ {op_name} failed: {e}")
                    continue
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                
                print(f"✓ {op_name}:")
                print(f"    Avg: {avg_time:.3f}s | Min: {min_time:.3f}s | Max: {max_time:.3f}s | P95: {p95_time:.3f}s")
                print(f"    Status: {'✓ PASS' if avg_time < 2 else '✗ FAIL'} (target: <2s)")
                
                response_times[op_name] = {
                    "times": times,
                    "avg": avg_time,
                    "min": min_time,
                    "max": max_time,
                    "p95": p95_time,
                    "pass": avg_time < 2
                }
        
        self.results["response_times"] = response_times
        return response_times
    
    async def profile_concurrent_requests(self, client: UniFiClient, num_concurrent: int = 10) -> Dict:
        """Profile concurrent request handling."""
        print(f"\n=== Profiling Concurrent Requests ({num_concurrent} simultaneous) ===")
        
        # Create multiple concurrent requests
        async def make_request(request_id: int):
            start_time = time.time()
            try:
                await client.get("/api/s/default/stat/device")
                elapsed = time.time() - start_time
                return {"id": request_id, "success": True, "time": elapsed}
            except Exception as e:
                elapsed = time.time() - start_time
                return {"id": request_id, "success": False, "time": elapsed, "error": str(e)}
        
        # Execute concurrent requests
        start_time = time.time()
        results = await asyncio.gather(*[make_request(i) for i in range(num_concurrent)])
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        if successful:
            times = [r["time"] for r in successful]
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            print(f"✓ Completed: {len(successful)}/{num_concurrent} requests")
            print(f"✓ Total time: {total_time:.3f}s")
            print(f"✓ Avg response time: {avg_time:.3f}s")
            print(f"✓ Max response time: {max_time:.3f}s")
            print(f"  Status: {'✓ PASS' if len(successful) >= num_concurrent else '✗ FAIL'}")
        
        if failed:
            print(f"✗ Failed: {len(failed)} requests")
            for r in failed[:3]:  # Show first 3 failures
                print(f"    Request {r['id']}: {r.get('error', 'Unknown error')}")
        
        self.results["concurrent"] = {
            "num_requests": num_concurrent,
            "successful": len(successful),
            "failed": len(failed),
            "total_time": total_time,
            "avg_response_time": avg_time if successful else None,
            "max_response_time": max_time if successful else None,
            "pass": len(successful) >= num_concurrent
        }
        
        return self.results["concurrent"]
    
    async def profile_memory_under_load(self, client: UniFiClient) -> Dict[str, float]:
        """Profile memory usage under load."""
        print("\n=== Profiling Memory Usage (Under Load) ===")
        
        # Make several requests to simulate load
        tasks = []
        for _ in range(20):
            tasks.append(client.get("/api/s/default/stat/device"))
            tasks.append(client.get("/api/s/default/stat/sta"))
        
        await asyncio.gather(*tasks)
        
        # Wait a moment for memory to stabilize
        await asyncio.sleep(1)
        
        mem_usage = self.get_memory_usage()
        
        print(f"✓ RSS Memory: {mem_usage['rss_mb']:.2f} MB")
        print(f"✓ VMS Memory: {mem_usage['vms_mb']:.2f} MB")
        print(f"  Increase from idle: {mem_usage['rss_mb'] - self.results['memory']['idle_rss_mb']:.2f} MB")
        
        self.results["memory"]["load_rss_mb"] = mem_usage['rss_mb']
        self.results["memory"]["load_vms_mb"] = mem_usage['vms_mb']
        self.results["memory"]["load_pass"] = mem_usage['rss_mb'] < 150  # Allow some increase under load
        
        return mem_usage
    
    def print_summary(self):
        """Print summary of all profiling results."""
        print("\n" + "=" * 60)
        print("PERFORMANCE PROFILING SUMMARY")
        print("=" * 60)
        
        # Startup
        print("\n📊 Startup Time:")
        startup = self.results["startup"]
        print(f"  Time: {startup['time_seconds']:.3f}s (target: <{startup['target_seconds']}s)")
        print(f"  Status: {'✓ PASS' if startup['pass'] else '✗ FAIL'}")
        
        # Memory
        print("\n💾 Memory Usage:")
        memory = self.results["memory"]
        print(f"  Idle RSS: {memory['idle_rss_mb']:.2f} MB (target: <{memory['target_mb']} MB)")
        print(f"  Idle Status: {'✓ PASS' if memory['idle_pass'] else '✗ FAIL'}")
        if "load_rss_mb" in memory:
            print(f"  Load RSS: {memory['load_rss_mb']:.2f} MB")
            print(f"  Load Status: {'✓ PASS' if memory['load_pass'] else '✗ FAIL'}")
        
        # Response Times
        print("\n⚡ Response Times:")
        response_times = self.results["response_times"]
        all_pass = True
        for op_name, data in response_times.items():
            status = '✓ PASS' if data['pass'] else '✗ FAIL'
            print(f"  {op_name}: {data['avg']:.3f}s avg ({status})")
            all_pass = all_pass and data['pass']
        print(f"  Overall: {'✓ ALL PASS' if all_pass else '✗ SOME FAIL'}")
        
        # Concurrent
        print("\n🔄 Concurrent Requests:")
        concurrent = self.results["concurrent"]
        print(f"  Requests: {concurrent['successful']}/{concurrent['num_requests']} successful")
        print(f"  Total time: {concurrent['total_time']:.3f}s")
        if concurrent['avg_response_time']:
            print(f"  Avg response: {concurrent['avg_response_time']:.3f}s")
        print(f"  Status: {'✓ PASS' if concurrent['pass'] else '✗ FAIL'}")
        
        # Overall
        print("\n" + "=" * 60)
        overall_pass = (
            startup['pass'] and
            memory['idle_pass'] and
            all_pass and
            concurrent['pass']
        )
        print(f"OVERALL: {'✓ ALL TESTS PASSED' if overall_pass else '✗ SOME TESTS FAILED'}")
        print("=" * 60)
    
    async def run_full_profile(self):
        """Run complete performance profiling suite."""
        print("=" * 60)
        print("UniFi MCP Server - Performance Profiling")
        print("=" * 60)
        
        client = None
        try:
            # Profile startup time
            await self.profile_startup_time()
            
            # Profile memory at idle
            await self.profile_memory_idle()
            
            # Create client for remaining tests
            config = load_config()
            client = UniFiClient(config.unifi, config.server.performance)
            await client.connect()
            
            # Profile response times
            await self.profile_response_times(client)
            
            # Profile concurrent requests
            await self.profile_concurrent_requests(client, num_concurrent=10)
            
            # Profile memory under load
            await self.profile_memory_under_load(client)
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"\n✗ Profiling failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up client session
            if client and client.session:
                await client.session.close()


async def main():
    """Main entry point."""
    profiler = PerformanceProfiler()
    await profiler.run_full_profile()


if __name__ == "__main__":
    asyncio.run(main())
