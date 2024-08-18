from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django_eventstream.tests import SSEAPIClient, SSEClient
from django_eventstream import Event

from .test_basesseview import BaseTestSSEViewStream


class TestSSEAPIViewStreamWithSSEAPIClient(BaseTestSSEViewStream):
    __test__ = True

    def setUp(self):
        self.client_class = SSEAPIClient
        self.url = reverse("apiview-events")


class TestSSEAPIViewStreamWithAPIClient(BaseTestSSEViewStream):
    __test__ = True

    def setUp(self):
        self.client_class = SSEClient
        self.url = reverse("apiview-events")


class BasetestSSEAPIView(TestCase):
    def test_browsableapiview(self):
        client = APIClient()
        response = client.get(
            reverse("apiview-events"),
            headers={
                "Accept": "text/html",
                "Content-Type": "text/html",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert not response.streaming, "Expected a non-streaming response"

    def test_head_request(self):
        client = APIClient()
        response = client.head(
            reverse("apiview-events"),
            headers={
                "Accept": "text/html",
                "Content-Type": "text/html",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert not response.streaming, "Expected a non-streaming response"

    def options_request(self, url):
        client = APIClient()
        response = client.options(
            url,
            headers={
                "Accept": "text/html",
                "Content-Type": "text/html",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert not response.streaming, "Expected a non-streaming response"

        return response

    def test_options_request_configured_view(self):
        response = self.options_request(reverse("apiview-events"))

        excepted_response = {
            "name": "Eventsss",
            "description": "A viewset for events",
            "renders": ["text/event-stream", "text/html"],
            "listen_channels": ["enzo"],
            "listen_messages_types": ["message", "enzo"],
        }

        assert (
            response.data == excepted_response
        ), f"Expected {excepted_response} but got {response.data}"

    def test_options_request_no_configured_events(self):
        response = self.options_request(reverse("no-configured-events"))

        excepted_response = {
            "name": "Configured Events Api",
            "description": "A subclass of the EventsAPIView class with the channels and messages types configured.",
            "renders": ["text/event-stream", "text/html"],
            "listen_channels": [],
            "listen_messages_types": [],
        }

        assert (
            response.data == excepted_response
        ), f"Expected {excepted_response} but got {response.data}"
