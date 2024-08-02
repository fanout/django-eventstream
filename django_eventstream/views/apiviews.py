from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer  
from rest_framework import status
from .views import events
from ..renderers import SSEEventRenderer, BrowsableAPIEventStreamRenderer

import logging
logger = logging.getLogger(__name__)

class EventsAPIView(APIView):
    """
    A view to stream events to the client. Here you will be able to see the events in real time.

    By default, this view will not stream any events, because you must configure the channels you want to see the events from.
    To configure the channels, you can do it in three ways:
        - By setting the channels attribute in the class definition.
        - By setting the channels query parameter in the request.
        - By setting the channel in the URL.
    Those three ways are mutually exclusive, so you can only use one of them.

    If you want to see a specific type of messages and not the default "message" type, you can set the messages_types attribute in the class definition.
    That's the only way provided to set the messages types.
    """

    http_method_names = ["get", "options", "head"]
    parser_classes = []

    def __init__(self, channels: list = None, messages_types: list = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channels = channels if channels is not None else []
        self.messages_types = messages_types if messages_types is not None else []

    @property
    def renderer_classes(self):
        if self.request.method == "OPTIONS":
            return [BrowsableAPIRenderer, JSONRenderer]
        if hasattr(settings, "EVENTSTREAM_RENDERER"):
            renderer_classes = [import_string(renderer) for renderer in settings.EVENTSTREAM_RENDERER]
        else:
            renderer_classes = [SSEEventRenderer, BrowsableAPIEventStreamRenderer]
        return renderer_classes

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
            self.messages_types = request.query_params.get("messages_types", "").split(",")

        if len(self.channels) == 0:
            self.channels = (
                request.query_params.get("channels", "").split(",")
                if request.query_params.get("channels")
                else []
            )

        return self._stream_or_respond(self.channels, request)
    
    def options(self, request, *args, **kwargs):
        if self.metadata_class is None:
            return self.http_method_not_allowed(request, *args, **kwargs)
        data = self.metadata_class().determine_metadata(request, self)
        logger.error(f"OPTIONS {data}")

        default_renderer_classes = [BrowsableAPIRenderer]
        response = Response(data, status=status.HTTP_200_OK)
        response.accepted_renderer = default_renderer_classes[0]()
        logger.error(f"OPTIONS {response.accepted_renderer}")
        response.accepted_media_type = response.accepted_renderer.media_type
        response.renderer_context = self.get_renderer_context()
        logger.error(f"OPTIONS {response.renderer_context}")
        
        logger.error(f"OPTIONS {response}")
        return response

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

        if self._accepted_format(request, ["text/html"]) and self._api_sse and 'text/event-stream' not in request.GET.get('format', ''):
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

def configure_events_api_view(channels=None, messages_types=None):
    """
    Configure the EventsAPIView class with specific channels and message types.
    """

    class ConfiguredEventsAPIView(EventsAPIView):
        def __init__(self, *args, **kwargs):
            super().__init__(channels=channels, messages_types=messages_types, *args, **kwargs)

    return ConfiguredEventsAPIView