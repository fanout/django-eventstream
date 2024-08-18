from unittest import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django_eventstream.tests import SSEAPIClient, SSEClient


class TestBaseSSEClient(TestCase):
    __test__ = False

    def test_no_stream_before_get(self):
        with self.assertRaises(ValueError):
            stream = self.client.sse_stream()
            next(stream)

    def test_no_stream_without_streaming_response(self):
        self.client.get(reverse("health"))
        with self.assertRaises(ValueError):
            stream = self.client.sse_stream()
            next(stream)

    def test_stream_given_reponse(self):
        client = APIClient()

        self.client.sse_stream(response=self.client.get(reverse("health")))


class TestSSEAPIClient(TestBaseSSEClient):
    __test__ = True

    def setUp(self):
        self.client = SSEAPIClient()


class TestSSEClient(TestBaseSSEClient):
    __test__ = True

    def setUp(self):
        self.client = SSEClient()
