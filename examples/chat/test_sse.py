import requests
import threading
import time
from collections import defaultdict
import uuid
import sseclient
import json
import pytest

# Global dictionaries to track responses
responses = defaultdict(set)
expected_events = set()
response_times = []

# Event to signal threads to stop
stop_event = threading.Event()

# URL to watch
watch_url = "http://127.0.0.1:8000/"
watch_interval = 1  # Intervalle en secondes pour vérifier l'URL

def generate_event_id():
    return str(uuid.uuid4())

def sse_client(url, client_id):
    try:
        messages = sseclient.SSEClient(url)
        for event in messages:
            if event.data:
                event_id = json.loads(event.data)  # Use json.loads to correctly parse the event data
                responses[client_id].add(event_id)
            if stop_event.is_set():
                break
    except requests.RequestException as e:
        print(f"Client {client_id} encountered an error: {e}")

def url_watcher(url, interval):
    while not stop_event.is_set():
        try:
            start_time = time.time()
            response = requests.get(url)
            response_time = time.time() - start_time
            response_times.append(response_time)
            print(f"Watcher check {url}: {response.status_code}, Response time: {response_time:.2f} seconds")
        except requests.RequestException as e:
            print(f"Watcher encountered an error: {e}")
        time.sleep(interval)

def event_sender(url, interval):
    time.sleep(8)
    while not stop_event.is_set():
        try:
            event_id = generate_event_id()
            expected_events.add(event_id)
            response = requests.get(url, params={'event_data': event_id})
            if response.status_code == 200:
                print(f"Event sent: {event_id}")
            else:
                print(f"Failed to send event: {response.status_code}")
        except requests.RequestException as e:
            print(f"Event sender encountered an error: {e}")
        time.sleep(interval)

def stress_test(url, num_clients, duration):
    global responses, expected_events, stop_event, response_times
    responses = defaultdict(set)
    expected_events = set()
    response_times = []
    stop_event = threading.Event()

    threads = []

    # Start the watcher thread
    for client_id in range(num_clients):
        thread = threading.Thread(target=sse_client, args=(url, client_id))
        thread.start()
        threads.append(thread)
        
    watcher_thread = threading.Thread(target=url_watcher, args=(watch_url, watch_interval))
    watcher_thread.start()
    threads.append(watcher_thread)
    
    # Start the event sender thread
    event_sender_thread = threading.Thread(target=event_sender, args=("http://127.0.0.1:8000/send-event/", 1))
    event_sender_thread.start()
    threads.append(event_sender_thread)
    
    # Let the threads run for the specified duration
    print("We are waiting for the test to complete...")
    time.sleep(duration)
    print("Test duration completed.")
    
    # Signal the event sender thread to stop
    stop_event.set()
    event_sender_thread.join()
    
    time.sleep(3)

    # Signal the watcher and client threads to stop
    for thread in threads:
        if thread != event_sender_thread:
            thread.join(timeout=1)

    # Summarize results
    total_responses = sum(len(events) for events in responses.values())
    clients_with_responses = len(responses)
    
    # Print all the responses received by each client
    # for client_id in responses:
    #     print(f"Client {client_id}: {responses[client_id]}")
    
    print("\n--- Stress Test Summary ---")
    print(f"Total clients: {num_clients}")
    print(f"Clients with responses: {clients_with_responses}")
    print(f"Total responses received: {total_responses}")
    print(f"Total events sent: {len(expected_events)}")
    print("\nResponses per client:")

    # Sort the responses by client_id
    for client_id in sorted(responses.keys()):
        print(f"Client {client_id}: {len(responses[client_id])} responses")

    # Check if all events were received by all clients
    results = {}
    for event_id in expected_events:
        received_by_all = all(event_id in responses[client_id] for client_id in responses)
        print(f"Event {event_id} received by all clients: {received_by_all}")
        results[event_id] = received_by_all

    return results

def calculate_success_percentage(results, total_events_sent):
    total_events = len(results)
    successful_events = sum(1 for received in results.values() if received)
    return (successful_events / total_events_sent) * 100

def calculate_response_time_stats(response_times):
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    min_response_time = min(response_times, default=0)
    max_response_time = max(response_times, default=0)
    return avg_response_time, min_response_time, max_response_time

def test_sse_events(num_clients=1000, test_duration=120):
    test_url = "http://localhost:8000/events/"
    
    print(f"Starting stress test with {num_clients} clients for {test_duration} seconds...")
    results = stress_test(test_url, num_clients, test_duration)
    
    total_events_sent = len(expected_events)
    success_percentage = calculate_success_percentage(results, total_events_sent)
    avg_response_time, min_response_time, max_response_time = calculate_response_time_stats(response_times)
    
    print(f"Success Percentage: {success_percentage:.2f}%")
    print(f"Average response time: {avg_response_time:.2f} seconds")
    print(f"Minimum response time: {min_response_time:.2f} seconds")
    print(f"Maximum response time: {max_response_time:.2f} seconds")
    
    # Assert that at least 90% of the events were successfully received by all clients
    assert success_percentage >= 90, f"Success percentage was {success_percentage:.2f}%, which is below the acceptable threshold."

if __name__ == "__main__":
    test_sse_events()
