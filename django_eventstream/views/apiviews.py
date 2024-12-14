from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.metadata import SimpleMetadata
from rest_framework.settings import api_settings
from .views import events
from django_eventstream.renderers import (
    BrowsableAPIEventStreamRenderer,
    SSEEventRenderer,
)

try:
    from adrf.views import APIView
except ImportError:
    from rest_framework.views import APIView

import logging

logger = logging.getLogger(__name__)


class EventsMetadata(SimpleMetadata):
    """
    A metadata class to provide information about the EventsAPIView class.
    It's only purpose is to provide correct information about the actions that can be performed in the events view.
    """

    def determine_metadata(self, request, view):
        metadata = {
            "name": view.get_view_name(),
            "description": view.get_view_description(),
            "renders": [renderer.media_type for renderer in view.sse_renderer_classes],
            "listen_channels": view.channels,
            "listen_messages_types": view.messages_types,
        }
        if hasattr(view, "get_serializer"):
            actions = self.determine_actions(request, view)
            if actions:
                metadata["actions"] = actions
        return metadata


class EventsAPIView(APIView):
    """
    A view to stream events to the client. Here you will be able to see the events in real time.

    By default, this view will not stream any events, because you must configure the channels you want to see the events from.
    To configure the channels, you can do it in three ways:
        - By setting the channels attribute in the class definition.
        - By setting the channel in the URL.
    Those two ways are mutually exclusive, so you can only use one of them.

    If you want to see a specific type of messages and not the default "message" type, you can also set the messages_types attribute in the class definition.
    That's the only way provided to set the messages types.
    """

    http_method_names = ["get", "options", "head"]
    parser_classes = []
    metadata_class = EventsMetadata

    def __init__(
        self, channels: list = None, messages_types: list = None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.channels = channels if channels is not None else []
        self.messages_types = messages_types if messages_types is not None else []

    @property
    def sse_renderer_classes(self):
        if hasattr(settings, "EVENTSTREAM_RENDERER"):
            sse_renderer_classes = [
                import_string(renderer) for renderer in settings.EVENTSTREAM_RENDERER
            ]
        else:
            sse_renderer_classes = [SSEEventRenderer, BrowsableAPIEventStreamRenderer]
        return sse_renderer_classes

    @property
    def renderer_classes(self):
        if self.request.method == "OPTIONS":
            return api_settings.DEFAULT_RENDERER_CLASSES
        return self.sse_renderer_classes

    @property
    def _api_sse(self):
        for renderer in self.renderer_classes:
            if renderer.format == "api_sse":
                return True

    def get(self, request, *args, **kwargs):
        if len(self.channels) > 0 and request.query_params.get("channels"):
            return Response(
                {
                    "error": "Conflicting channel specifications in APIView configuration and query parameters."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.query_params.get("messages_types"):
            if len(self.messages_types) > 0:
                return Response(
                    {
                        "error": "Conflicting messages types specifications in APIView configuration and query parameters."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self.messages_types = request.query_params.get("messages_types", "").split(
                ","
            )

        if len(self.channels) == 0:
            self.channels = (
                request.query_params.get("channels", "").split(",")
                if request.query_params.get("channels")
                else []
            )

        return self._stream_or_respond(self.channels, request)

    def _accepted_format(self, request, format_list):
        accept_header = request.META.get("HTTP_ACCEPT", "")
        query_format = request.GET.get("format", "")
        return any(fmt in accept_header or fmt in query_format for fmt in format_list)

    def _stream_or_respond(self, channels, django_request):
        request = django_request._request
        messages_types = self.messages_types if self.messages_types else ["message"]
        data = {
            "channels": ", ".join(channels),
            "messages_types": ", ".join(messages_types),
        }

        if (
            self._accepted_format(request, ["text/html"])
            and self._api_sse
            and "text/event-stream" not in request.GET.get("format", "")
        ):
            return Response(data, status=status.HTTP_200_OK)
        elif self._accepted_format(request, ["text/event-stream", "*/*"]):
            kwargs = {"channels": channels}
            return events(request, **kwargs)

        return Response(
            {
                "error": "This endpoint only supports text/event-stream and text/html accept types."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


def configure_events_api_view(
    channels=None, messages_types=None, docstring=None, class_name=None
):
    """
    Configure the EventsAPIView class with specific channels and message types.
    """

    class ConfiguredEventsAPIView(EventsAPIView):
        __doc__ = (
            docstring
            or """
        A subclass of the EventsAPIView class with the channels and messages types configured.
        """
        )

        def __init__(self, *args, **kwargs):
            super().__init__(
                channels=channels, messages_types=messages_types, *args, **kwargs
            )
            self.__doc__ = """coucou"""

    if class_name:
        ConfiguredEventsAPIView.__name__ = class_name

    return ConfiguredEventsAPIView
