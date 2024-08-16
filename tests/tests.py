import os
import asyncio
from django import setup
from django.conf import settings
from time import sleep

if settings.configured is False:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    setup()

import requests
import threading
import time
import uuid
import sseclient
import json
from queue import Queue
from django.test import LiveServerTestCase, override_settings
from rest_framework.test import APITestCase, APIClient

from django.urls import reverse
from collections import defaultdict
from django_eventstream import send_event
from django_eventstream.tests import SSEAPIClient
from django.test.client import AsyncClient, AsyncRequestFactory


import re
import codecs
import six
import time
import asyncio

end_of_field = re.compile(r"\r\n\r\n|\r\r|\n\n")


class SSEClient:
    def __init__(self, response, chunk_size=1024):
        self.response = response
        self.chunk_size = chunk_size
        self.buf = ""
        self.retry = 3000
        self.resp_iterator = self.iter_content()

        encoding = getattr(self.response, "encoding", None) or "utf-8"
        self.decoder = codecs.getincrementaldecoder(encoding)(errors="replace")

    async def iter_content(self):
        async for chunk in self.response.streaming_content:
            yield chunk

    def _event_complete(self):
        return re.search(end_of_field, self.buf) is not None

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:  # loop until event emitted
            while not self._event_complete():
                try:
                    next_chunk = await self.resp_iterator.__anext__()
                    if not next_chunk:
                        raise EOFError()
                    self.buf += self.decoder.decode(next_chunk)
                except (StopIteration, EOFError) as e:
                    await asyncio.sleep(self.retry / 1000.0)
                    raise StopIteration

            (event_string, self.buf) = re.split(end_of_field, self.buf, maxsplit=1)
            msg = Event.parse(event_string)

            if msg.retry:
                self.retry = msg.retry

            if msg.data != "":
                return msg

    if six.PY2:
        next = __anext__


class Event(object):
    sse_line_pattern = re.compile("(?P<name>[^:]*):?( ?(?P<value>.*))?")

    def __init__(self, data="", event="message", id=None, retry=None):
        assert isinstance(data, six.string_types), "Data must be text"
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    @classmethod
    def parse(cls, raw):
        msg = cls()
        for line in raw.splitlines():
            m = cls.sse_line_pattern.match(line)
            if m is None:
                continue

            name = m.group("name")
            if name == "":
                continue
            value = m.group("value")

            if name == "data":
                if msg.data:
                    msg.data = "%s\n%s" % (msg.data, value)
                else:
                    msg.data = value
            elif name == "event":
                msg.event = value
            elif name == "id":
                msg.id = value
            elif name == "retry":
                msg.retry = int(value)

        return msg

    def __str__(self):
        return self.data


@override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
class StressTestBase(LiveServerTestCase):
    EVENT_STREAM_URL = "events"
    EVENT_WATCHER_URL = "health"

    WATCH_INTERVAL = 1
    NUM_CLIENTS = 2
    TEST_DURATION = 15

    EVENT_SENDER_URL = "send-event"
    EVENT_SENDER_INTERVAL = 1

    @override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.responses = defaultdict(list)
        self.expected_events = set()
        self.response_times = []
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        self.sse_url = reverse(self.EVENT_STREAM_URL)
        self.watcher_url = reverse(self.EVENT_WATCHER_URL)
        self.event_sender_url = reverse(self.EVENT_SENDER_URL)

    def generate_event_id(self):
        return str(uuid.uuid4())

    def sse_client(self, url, client_id):
        print(f"Client {client_id} starting.")
        try:
            for message in sseclient.SSEClient(self.live_server_url + self.sse_url):
                print("message: ", message)
        # for message in async_to_sync_iterator(client):
        #     print("message: ", message)
        #     if message.data:
        #         event_id = json.loads(message.data)
        #         with self.lock:
        #             self.responses[client_id].append(event_id)
        #     if self.stop_event.is_set():
        #         break
        except Exception as e:
            print(f"Client {client_id} encountered an error: {e}")
        print(f"Client {client_id} stopping.")

    def url_watcher(self, url, interval):
        print("Watcher starting.")
        watcher_responses = []
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                response = requests.get(f"{self.live_server_url}{self.watcher_url}")
                response_time = time.time() - start_time
                with self.lock:
                    self.response_times.append(response_time)
                    watcher_responses.append(
                        {
                            "status_code": response.status_code,
                            "response_time": response_time,
                        }
                    )
                print(
                    f"Watcher check {url}: {response.status_code}, Response time: {response_time:.2f} seconds"
                )
            except requests.RequestException as e:
                print(f"Watcher encountered an error: {e}")
            time.sleep(interval)
        print("Watcher stopping.")
        return watcher_responses

    def stress_test(
        self,
        num_clients,
        test_duration,
        sse_test_url,
        watcher_url,
        watch_interval,
        event_sender_method,
        event_sender_args,
    ):
        self.responses = defaultdict(list)
        self.expected_events = set()
        self.response_times = []
        self.stop_event.clear()

        threads = []
        result_queue = Queue()

        # Start the watcher thread
        watcher_thread = threading.Thread(
            target=lambda q: q.put(self.url_watcher(watcher_url, watch_interval)),
            args=(result_queue,),
        )
        watcher_thread.start()
        threads.append(watcher_thread)

        # Start the SSE client threads
        for client_id in range(num_clients):
            thread = threading.Thread(
                target=self.sse_client, args=(sse_test_url, client_id)
            )
            thread.start()
            threads.append(thread)

        # Start the event sender thread
        event_sender_thread = threading.Thread(
            target=lambda q: q.put(event_sender_method(*event_sender_args)),
            args=(result_queue,),
        )
        event_sender_thread.start()
        threads.append(event_sender_thread)

        # Let the threads run for the specified duration
        print("We are waiting for the test to complete...")
        time.sleep(test_duration)
        print("Test duration completed.")

        # Signal the event sender thread to stop
        self.stop_event.set()
        event_sender_thread.join()

        # Signal the watcher and client threads to stop
        print("Stopping watcher and client threads...")
        for thread in threads:
            if thread != event_sender_thread:
                thread.join()
        print("All threads stopped.")

        # Collect results from queue
        watcher_responses = result_queue.get()
        events_sent = result_queue.get()

        # Summarize results
        total_responses = sum(len(events) for events in self.responses.values())
        clients_with_responses = len(self.responses)

        print("\n--- Stress Test Summary ---")
        print(f"Total clients: {num_clients}")
        print(f"Clients with responses: {clients_with_responses}")
        print(f"Total responses received: {total_responses}")
        print(f"Total events sent: {len(self.expected_events)}")
        print("\nResponses per client:")

        # Sort the responses by client_id
        for client_id in sorted(self.responses.keys()):
            print(f"Client {client_id}: {len(self.responses[client_id])} responses")

        # Prepare the result to return
        result = {
            "responses": dict(self.responses),
            "watcher_responses": watcher_responses,
            "events_sent": events_sent,
        }

        return result

    @staticmethod
    def calculate_success_percentage(results, total_events_sent):
        total_events = len(results)
        successful_events = sum(1 for received in results.values() if received)
        return (successful_events / total_events_sent) * 100

    @staticmethod
    def calculate_response_time_stats(response_times):
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        min_response_time = min(response_times, default=0)
        max_response_time = max(response_times, default=0)
        return avg_response_time, min_response_time, max_response_time


@override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
class StressTestInternal(StressTestBase):

    def event_sender_internal(self, interval):
        print("Event sender starting.")
        events_sent = []
        time.sleep(8)  # Wait for clients to connect
        while not self.stop_event.is_set():
            try:
                event_id = self.generate_event_id()
                with self.lock:
                    self.expected_events.add(event_id)
                    events_sent.append(event_id)
                response = requests.get(
                    f"{self.live_server_url}{self.event_sender_url}",
                    params={"event_data": event_id},
                )
                if response.status_code == 200:
                    print(f"Event sent: {event_id}")
                else:
                    print(f"Failed to send event: {response.status_code}")
            except requests.RequestException as e:
                print(f"Event sender encountered an error: {e}")
            if self.stop_event.is_set():
                break
            time.sleep(interval)
        print("Event sender stopping.")
        return events_sent

    def test_sse_events_internal(self):
        EVENT_SENDER_ARGS = (self.EVENT_SENDER_INTERVAL,)
        print(
            f"Starting stress test with {self.NUM_CLIENTS} clients for {self.TEST_DURATION} seconds..."
        )
        results = self.stress_test(
            self.NUM_CLIENTS,
            self.TEST_DURATION,
            self.sse_url,
            self.watcher_url,
            self.WATCH_INTERVAL,
            self.event_sender_internal,
            EVENT_SENDER_ARGS,
        )
        print(f"results: {results}")

        total_events_sent = len(self.expected_events)
        success_percentage = self.calculate_success_percentage(
            results["responses"], total_events_sent
        )
        avg_response_time, min_response_time, max_response_time = (
            self.calculate_response_time_stats(self.response_times)
        )

        print(f"Success Percentage: {success_percentage:.2f}%")
        print(f"Average response time: {avg_response_time:.2f} seconds")
        print(f"Minimum response time: {min_response_time:.2f} seconds")
        print(f"Maximum response time: {max_response_time:.2f} seconds")

        # Assert that at least 100% of the events were successfully received by all clients
        self.assertGreaterEqual(
            success_percentage,
            100,
            f"Success percentage was {success_percentage:.2f}%, which is below the acceptable threshold.",
        )


@override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
class StressTestExternal(StressTestBase):

    def event_sender_external(self, interval):
        print("Event sender starting.")
        events_sent = []
        time.sleep(8)  # Wait for clients to connect
        while not self.stop_event.is_set():
            event_id = self.generate_event_id()
            send_event(channel="enzo", data=event_id, event_type="message")
            print(f"Event sent: {event_id}")
            with self.lock:
                self.expected_events.add(event_id)
                events_sent.append(event_id)
            if self.stop_event.is_set():
                break
            time.sleep(interval)
        print("Event sender stopping.")
        return events_sent

    @override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
    def test_sse_events_external(self):
        EVENT_SENDER_INTERVAL = (self.EVENT_SENDER_INTERVAL,)
        print(
            f"Starting stress test with {self.NUM_CLIENTS} clients for {self.TEST_DURATION} seconds..."
        )

        results = self.stress_test(
            self.NUM_CLIENTS,
            self.TEST_DURATION,
            self.EVENT_STREAM_URL,
            self.EVENT_WATCHER_URL,
            self.WATCH_INTERVAL,
            self.event_sender_external,
            EVENT_SENDER_INTERVAL,
        )

        print(f"results: {results}")

        total_events_sent = len(self.expected_events)
        success_percentage = self.calculate_success_percentage(
            results["responses"], total_events_sent
        )
        avg_response_time, min_response_time, max_response_time = (
            self.calculate_response_time_stats(self.response_times)
        )

        print(f"Success Percentage: {success_percentage:.2f}%")
        print(f"Average response time: {avg_response_time:.2f} seconds")
        print(f"Minimum response time: {min_response_time:.2f} seconds")
        print(f"Maximum response time: {max_response_time:.2f} seconds")

        # Assert that at least 100% of the events were successfully received by all clients
        self.assertGreaterEqual(
            success_percentage,
            100,
            f"Success percentage was {success_percentage:.2f}%, which is below the acceptable threshold.",
        )


from django.test import TestCase, override_settings
from django.urls import get_resolver


@override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
class URLListTest(TestCase):

    def test_list_urls(self):
        url_patterns = get_resolver().url_patterns

        def list_urls(urls, depth=0):
            for entry in urls:
                url_pattern = entry.pattern
                url_name = entry.name if entry.name else "No name"
                print("  " * depth + f"{url_pattern} [name='{url_name}']")
                if hasattr(entry, "url_patterns"):
                    list_urls(entry.url_patterns, depth + 1)

        list_urls(url_patterns)

        url = reverse("events")
        print(f"URL for 'events' name: {url}")


from asgiref.sync import async_to_sync
import threading
from django_eventstream import send_event

from channels.testing import ChannelsLiveServerTestCase


# class TestSSEAPIClient(LiveServerTestCase):


from django.test.client import AsyncClient


@override_settings(
    ROOT_URLCONF="bench.urls",
)
class MyAsyncTestCase(TestCase):
    async def test_something_async(self):
        client = AsyncClient()
        response = await client.get(path="/events/")
        print("response: ", response)
        print("response.content: ", response.content)
        print("response.streaming: ", response.streaming)

        self.assertEqual(response.status_code, 200)
        for message in response:
            print("message: ", message)


from django_eventstream.views import configure_events_api_view
from adrf.test import AsyncAPIClient
from django.core.asgi import get_asgi_application


# @override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
# class TestSSEAPIClient(ChannelsLiveServerTestCase):
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


class TestSSEAPIClient(APITestCase):

    # @override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
    def send_events(self):
        sleep(5)
        while True:
            send_event(channel="enzo", data="Hello, world!", event_type="message")
            # requests.get(self.live_server_url + "/send-event/")s
            APIClient().get(reverse("send-event"))
            print("Event sent.")
            time.sleep(1)

    @override_settings(ROOT_URLCONF="bench.urls", ALLOWED_HOSTS=["*"])
    async def test_sse_client(self):
        # send_event_thread = threading.Thread(target=self.send_events)
        # send_event_thread.start()

        # Test synchrone pour recevoir les événements
        # response = requests.get(self.live_server_url + "/events/", stream=True)
        # print("response: ", response)
        # for line in response.iter_lines():
        #     if line:
        #         print(line.decode("utf-8"))
        #         break

        # Test asynchrone pour recevoir les événements
        # url = self.live_server_url + reverse("events")
        url = reverse("events")
        print("url: ", url)
        # health_url = self.live_server_url + reverse("health")
        health_url = reverse("health")
        print("health_url: ", health_url)

        client = SSEAPIClient()
        # test the health url

        # reponse = await client.get(health_url)
        reponse = client.get(health_url)
        print("reponse: ", reponse)

        print("url: ", url)
        # response = await client.get(
        response = client.get(
            url,
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "text/event-stream",
            },
        )
        print("response: ", response)

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert response.streaming, "Expected a streaming response"

        # async for chunk in response.streaming_content:
        #     print("chunk: ", chunk.decode("utf-8"))
        #     break
        async for event in client.sse_stream():
            print(event)
        # sse_client = sseclient.SSEClient(url)

        # ----------------------------

        # rf = AsyncRequestFactory()
        # get_request = rf.get(reverse("events"), content_type="text/event-stream")

        # view = configure_events_api_view(
        #     channels=["enzo"],
        #     messages_types=["message", "enzo"],
        #     docstring="A viewset for events",
        #     class_name="Eventsss",
        # ).as_view()

        # response = view(get_request)
        # from django.http.response import StreamingHttpResponse

        # if isinstance(response, StreamingHttpResponse):
        #     print("responseee: ", response)

        # print("response: ", response)
        # print("response.streaming: ", response.streaming)


# sse = sseclient.SSEClient(self.live_server_url + "/events/")
# for message in sse:
#     print("message: ", message)
