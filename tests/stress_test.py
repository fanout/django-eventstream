#!/usr/bin/env python
"""
Stress test for django-eventstream to verify fixes under load.

This test simulates high-load scenarios to ensure:
1. No asyncio task leaks under rapid connect/disconnect
2. No lock deadlocks under concurrent access
3. Proper cleanup on stream cancellation

Run this manually to verify the fixes work under stress.
"""

import os
import sys
import asyncio
import time
import statistics

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
import django
django.setup()

from unittest.mock import patch
from asgiref.sync import sync_to_async
from django_eventstream.views import Listener, stream
from django_eventstream.eventrequest import EventRequest
from django_eventstream.storage import DjangoModelStorage


async def stress_test_rapid_cancellations(num_iterations=50):
    """
    Stress test: rapid connection/cancellation cycles.
    
    This simulates what happens in production when clients
    rapidly connect and disconnect.
    """
    print(f"\nStress Test: {num_iterations} rapid connect/disconnect cycles")
    print("-" * 70)
    
    storage = DjangoModelStorage()
    get_current_id = sync_to_async(storage.get_current_id)
    
    with patch("django_eventstream.eventstream.get_storage", return_value=storage):
        try:
            current_id = await get_current_id("stress_test_channel")
        except:
            # Channel doesn't exist yet, that's OK
            current_id = "0"
        
        initial_tasks = len([t for t in asyncio.all_tasks() 
                           if not t.done() and t != asyncio.current_task()])
        
        start_time = time.time()
        
        for i in range(num_iterations):
            listener = Listener()
            request = EventRequest()
            request.is_next = False
            request.is_recover = False
            request.channels = ["stress_test_channel"]
            request.channel_last_ids = {"stress_test_channel": str(current_id)}
            
            # Start stream
            task = asyncio.create_task(collect_stream(stream(request, listener)))
            
            # Brief wait before cancel
            await asyncio.sleep(0.01)
            
            # Cancel
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Print progress
            if (i + 1) % 10 == 0:
                print(f"  Completed {i + 1}/{num_iterations} cycles...")
        
        elapsed = time.time() - start_time
        
        # Give time for cleanup
        await asyncio.sleep(0.5)
        
        final_tasks = len([t for t in asyncio.all_tasks() 
                          if not t.done() and t != asyncio.current_task()])
        
        print(f"\nResults:")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"  Cycles/second: {num_iterations/elapsed:.1f}")
        print(f"  Initial tasks: {initial_tasks}")
        print(f"  Final tasks: {final_tasks}")
        print(f"  Task leak: {final_tasks - initial_tasks}")
        
        if final_tasks - initial_tasks <= 0:
            print("  ✓ PASS: No task leaks detected")
            return True
        else:
            print(f"  ✗ FAIL: {final_tasks - initial_tasks} tasks leaked")
            return False


async def stress_test_concurrent_streams(num_concurrent=20):
    """
    Stress test: multiple concurrent streams.
    
    This simulates multiple clients connected simultaneously,
    then all disconnecting at once.
    """
    print(f"\nStress Test: {num_concurrent} concurrent streams")
    print("-" * 70)
    
    storage = DjangoModelStorage()
    get_current_id = sync_to_async(storage.get_current_id)
    
    with patch("django_eventstream.eventstream.get_storage", return_value=storage):
        try:
            current_id = await get_current_id("stress_test_channel")
        except:
            current_id = "0"
        
        tasks = []
        
        print(f"  Starting {num_concurrent} concurrent streams...")
        
        # Start all streams
        for i in range(num_concurrent):
            listener = Listener()
            request = EventRequest()
            request.is_next = False
            request.is_recover = False
            request.channels = ["stress_test_channel"]
            request.channel_last_ids = {"stress_test_channel": str(current_id)}
            
            task = asyncio.create_task(collect_stream(stream(request, listener)))
            tasks.append(task)
        
        # Let them all run
        await asyncio.sleep(1.0)
        
        print(f"  Cancelling all {num_concurrent} streams...")
        
        # Cancel all at once
        for task in tasks:
            task.cancel()
        
        # Wait for all cancellations
        cancelled = 0
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                cancelled += 1
        
        # Give time for cleanup
        await asyncio.sleep(0.5)
        
        remaining_tasks = len([t for t in asyncio.all_tasks() 
                              if not t.done() and t != asyncio.current_task()])
        
        print(f"\nResults:")
        print(f"  Streams started: {len(tasks)}")
        print(f"  Streams cancelled: {cancelled}")
        print(f"  Remaining tasks: {remaining_tasks}")
        
        if cancelled == len(tasks):
            print("  ✓ PASS: All streams cancelled successfully")
            return True
        else:
            print(f"  ✗ FAIL: Only {cancelled}/{len(tasks)} cancelled")
            return False


async def collect_stream(stream_iter):
    """Helper to collect stream output."""
    response = ""
    async for chunk in stream_iter:
        response += chunk
    return response


async def main():
    """Run all stress tests."""
    print("=" * 70)
    print("Django EventStream Stress Tests")
    print("=" * 70)
    print("\nThese tests verify the fixes work correctly under load.")
    
    results = []
    
    try:
        # Test 1: Rapid cancellations
        results.append(await stress_test_rapid_cancellations(50))
        
        # Test 2: Concurrent streams
        results.append(await stress_test_concurrent_streams(20))
        
        # Summary
        print("\n" + "=" * 70)
        print("STRESS TEST SUMMARY")
        print("=" * 70)
        print(f"Tests run: {len(results)}")
        print(f"Tests passed: {sum(results)}")
        print(f"Tests failed: {len(results) - sum(results)}")
        
        if all(results):
            print("\n✓ All stress tests passed!")
            return 0
        else:
            print("\n✗ Some stress tests failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during stress testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
