# -*- coding: utf-8 -*-
"""
Performance tests for concurrent event streaming.

These tests validate that the optimizations reduce lock contention
when many clients are connected to the event stream.
"""
from __future__ import unicode_literals
import asyncio
import time
import threading
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

from django_eventstream.views import ListenerManager, Listener, get_listener_manager
from django_eventstream.event import Event


class PerformanceTest(IsolatedAsyncioTestCase):
    """Test performance improvements for concurrent scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.listener_manager = ListenerManager()

    def test_concurrent_event_queuing_performance(self):
        """Test that queuing events to many listeners doesn't cause excessive lock contention."""
        num_listeners = 100
        num_events = 10  # Matches MAX_PENDING default
        channel = "test-channel"
        
        # Create many listeners
        listeners = []
        for i in range(num_listeners):
            listener = Listener()
            listener.assign_loop = Mock()  # Mock to avoid asyncio loop issues
            listener.loop = Mock()
            listener.loop.call_soon_threadsafe = Mock()
            listener.channels = {channel}
            listener.user_id = f"user-{i}"
            listeners.append(listener)
            self.listener_manager.add_listener(listener)
        
        # Measure time to queue events to all listeners
        start_time = time.time()
        
        for i in range(num_events):
            event = Event(channel, "message", f"Event {i}")
            self.listener_manager.add_to_queues(channel, event)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify all listeners received all events
        for listener in listeners:
            self.assertEqual(len(listener.channel_items.get(channel, [])), num_events)
        
        # Performance assertion: should complete in reasonable time
        # With 100 listeners and 10 events, this should take less than 1 second
        # on most systems even with lock contention
        self.assertLess(elapsed, 2.0, 
            f"Queuing {num_events} events to {num_listeners} listeners took {elapsed:.3f}s")
        
        # Clean up
        for listener in listeners:
            self.listener_manager.remove_listener(listener)

    def test_concurrent_add_remove_listeners(self):
        """Test that adding/removing listeners concurrently doesn't deadlock."""
        num_threads = 20
        operations_per_thread = 10
        channel = "test-channel"
        
        results = {'errors': []}
        
        def add_remove_listener():
            try:
                for _ in range(operations_per_thread):
                    listener = Listener()
                    listener.assign_loop = Mock()
                    listener.loop = Mock()
                    listener.loop.call_soon_threadsafe = Mock()
                    listener.channels = {channel}
                    listener.user_id = "test-user"
                    
                    self.listener_manager.add_listener(listener)
                    time.sleep(0.001)  # Small delay to increase contention
                    self.listener_manager.remove_listener(listener)
            except Exception as e:
                results['errors'].append(str(e))
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            thread = threading.Thread(target=add_remove_listener)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify no errors occurred
        self.assertEqual(len(results['errors']), 0, 
            f"Errors occurred during concurrent operations: {results['errors']}")
        
        # Performance assertion: should complete without timeout
        self.assertLess(elapsed, 5.0,
            f"Concurrent add/remove operations took {elapsed:.3f}s")
        
        # Verify all threads completed
        for thread in threads:
            self.assertFalse(thread.is_alive(), "Thread did not complete in time")

    def test_lock_not_held_during_wake_operations(self):
        """Test that the lock is released before waking listeners."""
        channel = "test-channel"
        
        # Create a listener with a slow wake operation
        slow_listener = Listener()
        slow_listener.assign_loop = Mock()
        slow_listener.loop = Mock()
        slow_listener.channels = {channel}
        slow_listener.user_id = "slow-user"
        
        wake_called = threading.Event()
        wake_completed = threading.Event()
        
        def slow_wake(fn):
            wake_called.set()
            time.sleep(0.1)  # Simulate slow wake
            wake_completed.set()
        
        slow_listener.loop.call_soon_threadsafe = slow_wake
        
        # Create another listener to test concurrent access
        fast_listener = Listener()
        fast_listener.assign_loop = Mock()
        fast_listener.loop = Mock()
        fast_listener.loop.call_soon_threadsafe = Mock()
        fast_listener.channels = {channel}
        fast_listener.user_id = "fast-user"
        
        # Add listeners
        self.listener_manager.add_listener(slow_listener)
        self.listener_manager.add_listener(fast_listener)
        
        # Queue event in a thread
        event = Event(channel, "message", "Test event")
        
        def queue_event():
            self.listener_manager.add_to_queues(channel, event)
        
        thread = threading.Thread(target=queue_event)
        thread.start()
        
        # Wait for wake to be called
        wake_called.wait(timeout=1.0)
        
        # Try to add another listener while wake is in progress
        # This should succeed quickly if lock is not held during wake
        another_listener = Listener()
        another_listener.assign_loop = Mock()
        another_listener.loop = Mock()
        another_listener.loop.call_soon_threadsafe = Mock()
        another_listener.channels = {channel}
        another_listener.user_id = "another-user"
        
        add_start = time.time()
        self.listener_manager.add_listener(another_listener)
        add_elapsed = time.time() - add_start
        
        # Adding listener should be fast even while wake is in progress
        self.assertLess(add_elapsed, 0.05,
            f"Adding listener took {add_elapsed:.3f}s, lock may be held during wake")
        
        # Clean up
        thread.join()
        self.listener_manager.remove_listener(slow_listener)
        self.listener_manager.remove_listener(fast_listener)
        self.listener_manager.remove_listener(another_listener)
