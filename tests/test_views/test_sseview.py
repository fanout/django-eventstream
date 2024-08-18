from django.urls import reverse
from django.test import TestCase
from django_eventstream.tests import SSEAPIClient, SSEClient
from .test_basesseview import BaseTestSSEViewStream


class BaseTestSSEView(TestCase):
    def test_unconfigured_channels(self):
        client = self.client_class()
        response = client.get(
            reverse("view-events-unconfigured-channels"),
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 OK but got {response.status_code}"

        assert not response.streaming, (
            "Expected a streaming response, instead we got: %s" % response.content
        )
        excepted_event = 'event: stream-error\nid: error\ndata: {"condition": "bad-request", "text": "Invalid request: No channels specified."}\n\n'

        assert excepted_event == response.content.decode(), "Expected event not found"


class TestSSEViewStreamWithSSEAPIClient(BaseTestSSEViewStream):
    __test__ = True

    def setUp(self):
        self.client_class = SSEAPIClient
        self.url = reverse("view-events")


class TestSSEViewStreamWithAPIClient(BaseTestSSEViewStream):
    __test__ = True

    def setUp(self):
        self.client_class = SSEClient
        self.url = reverse("view-events")
