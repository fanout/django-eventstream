import time
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django_eventstream.tests import SSEAPIClient
from django_eventstream import Event


class TestSSEApiView(TestCase):
    async def test_stream(self):
        client = SSEAPIClient()
        response = client.get(
            reverse("events"),
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "text/event-stream",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert response.streaming, "Expected a streaming response"

        received_events = []
        events_time = []
        expected_event_count = 4
        expected_total_duration = 40  # seconds
        expected_interval_between_events = 20  # seconds

        start_time = time.time()
        async for event in client.sse_stream():
            received_events.append(event)
            events_time.append(time.time())
            if len(received_events) >= expected_event_count:
                break
        end_time = time.time()

        total_duration = end_time - start_time

        assert (
            len(received_events) == expected_event_count
        ), f"Expected {expected_event_count} events but got {len(received_events)}"

        # The total duration should be within 1 second of the expected total duration.
        assert (
            abs(total_duration - expected_total_duration) < 1
        ), f"Expected total duration of {expected_total_duration} seconds but got {total_duration} seconds"

        expected_events = [
            Event(channel="", type="message", data={}, id=None, retry=None),
            Event(
                channel="", type="stream-open", data={"data": ""}, id=None, retry=None
            ),
            Event(
                channel="", type="keep-alive", data={"data": ""}, id=None, retry=None
            ),
            Event(
                channel="", type="keep-alive", data={"data": ""}, id=None, retry=None
            ),
        ]

        assert (
            received_events == expected_events
        ), "Received events do not match the expected events"

        # Verify that the time between each event is approximately the expected interval
        # Skipping the first interval (from start to the first event)
        for i in range(1, len(events_time)):
            interval_duration = events_time[i] - events_time[i - 1]
            if i == 1:
                continue
            assert (
                abs(interval_duration - expected_interval_between_events) < 1
            ), f"Expected interval of {expected_interval_between_events} seconds but got {interval_duration} seconds"

    def test_stream_html(self):
        client = APIClient()
        response = client.get(
            reverse("events"),
            headers={
                "Accept": "text/html",
                "Content-Type": "text/html",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert not response.streaming, "Expected a non-streaming response"

        assert (
            response.content == b"channels: , messages_types: message"
        ), "Expected response content to match"
