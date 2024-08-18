import sys
import importlib
from unittest import TestCase
from unittest.mock import patch


class TestDRFImports(TestCase):

    @patch("django_eventstream.views.importlib.util.find_spec", return_value=None)
    def test_no_drf_apiviews(self, mock_find_spec):
        if "rest_framework" in sys.modules:
            del sys.modules["rest_framework"]

        importlib.reload(sys.modules["django_eventstream.views"])

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.views import EventsAPIView

            EventsAPIView()

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.views import configure_events_api_view

            configure_events_api_view()

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.views import EventsMetadata

            EventsMetadata()

    @patch("django_eventstream.renderers.importlib.util.find_spec", return_value=None)
    def test_no_drf_renderers(self, mock_find_spec):
        if "rest_framework" in sys.modules:
            del sys.modules["rest_framework"]

        importlib.reload(sys.modules["django_eventstream.renderers"])

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.renderers import BrowsableAPIEventStreamRenderer

            BrowsableAPIEventStreamRenderer()

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.renderers import SSEEventRenderer

            SSEEventRenderer()

    @patch("django_eventstream.tests.importlib.util.find_spec", return_value=None)
    def test_no_drf_apitestclients(self, mock_find_spec):
        if "rest_framework" in sys.modules:
            del sys.modules["rest_framework"]

        importlib.reload(sys.modules["django_eventstream.tests"])

        with self.assertRaises(ModuleNotFoundError):
            from django_eventstream.tests import SSEAPIClient

            SSEAPIClient()

    def test_drf_apiviews(self):
        from django_eventstream.views import (
            EventsAPIView,
            configure_events_api_view,
            EventsMetadata,
        )
        from django_eventstream.views.apiviews import (
            EventsAPIView as AbsolutEventsAPIView,
            EventsMetadata as AbsolutEventsMetadata,
            configure_events_api_view as absolut_configure_events_api_view,
        )

        self.assertEqual(EventsAPIView, AbsolutEventsAPIView)
        self.assertEqual(EventsMetadata, AbsolutEventsMetadata)
        self.assertEqual(configure_events_api_view, absolut_configure_events_api_view)

    def test_drf_renderers(self):
        from django_eventstream.renderers import (
            BrowsableAPIEventStreamRenderer,
            SSEEventRenderer,
        )
        from django_eventstream.renderers.browsableapieventstreamrenderer import (
            BrowsableAPIEventStreamRenderer as AbsolutBrowsableAPIEventStreamRenderer,
        )
        from django_eventstream.renderers.sserenderer import (
            SSEEventRenderer as AbsolutEventStreamRenderer,
        )

        self.assertEqual(
            BrowsableAPIEventStreamRenderer, AbsolutBrowsableAPIEventStreamRenderer
        )
        self.assertEqual(SSEEventRenderer, AbsolutEventStreamRenderer)

    def test_drf_apitestclients(self):
        from django_eventstream.tests import SSEAPIClient
        from django_eventstream.tests.sseapiclient import (
            SSEAPIClient as AbsolutSSEAPIClient,
        )

        self.assertEqual(SSEAPIClient, AbsolutSSEAPIClient)
