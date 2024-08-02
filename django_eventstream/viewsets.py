from django.conf import settings
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.settings import APISettings
from django_eventstream.views import events
from django_eventstream.renderers import (
    SSEEventRenderer,
    BrowsableAPIEventStreamRenderer,
)


class EventsViewSet(ViewSet):
    """
    A viewset to stream events to the client. Here you will be able to see the events in real time.

    By default, this viewset will not stream any events, because you must configure the channels you want to see the events from.
    To configure the channels, you can do it in three ways:
        - By setting the channels attribute in the class definition.
        - By setting the channels query parameter in the request.
        - By setting the channel in the URL.
    Those three ways are mutually exclusive, so you can only use one of them.

    If you want to see a specific type of messages and not the default "message" type, you can set the messages_types attribute in the class definition.
    That's the only way provided to set the messages types.
    """

    http_method_names = ["get"]
    renderer_classes = (BrowsableAPIEventStreamRenderer, SSEEventRenderer)

    no_api_sse_renderer = False

    def __init__(
        self, channels: list = None, messages_types: list = None, *args, **kwargs
    ):
        super().__init__()
        self.channels = channels if channels is not None else []
        self.messages_types = messages_types if messages_types is not None else []
        self._api_sse = False

    def get_renderers(self):
        if hasattr(settings, "REST_FRAMEWORK"):
            api_settings = APISettings(
                user_settings=settings.REST_FRAMEWORK,
                defaults=None,
                import_strings=None,
            )
            default_renderers = list(api_settings.DEFAULT_RENDERER_CLASSES)

            sse_renderers = []
            api_sse_renderers = []

            for renderer_class in default_renderers:
                renderer_instance = renderer_class()
                if renderer_instance.format == "api_sse":
                    api_sse_renderers.append(renderer_class)
                    self._api_sse = True
                if renderer_instance.format == "text/event-stream":
                    sse_renderers.append(renderer_class)

            if len(api_sse_renderers) == 0:
                self.no_api_sse_renderer = True
            else:
                self.no_api_sse_renderer = False

            self.renderer_classes = api_sse_renderers + sse_renderers

        return super().get_renderers()

    def list(self, request):
        if len(self.channels) > 0 and request.query_params.get("channels"):
            return Response(
                {
                    "error": "Conflicting channel specifications in ViewSet configuration and query parameters."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.query_params.get("messages_types"):
            if len(self.messages_types) > 0:
                return Response(
                    {
                        "error": "Conflicting messages types specifications in ViewSet configuration and query parameters."
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

    @action(detail=False, methods=["get"], url_path="(?P<channel>[^/.]+)")
    def channel(self, request, channel=None):
        if len(self.channels) > 0:
            return Response(
                {
                    "error": "Conflicting channel specifications in URL and ViewSet configuration."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._stream_or_respond([channel], request._request)

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


def configure_events_view_set(channels=None, messages_types=None):
    """
    Configure the EventsViewSet class with specific channels and message types.
    """

    class ConfiguredEventsViewSet(EventsViewSet):
        def __init__(self, *args, **kwargs):
            super().__init__(
                channels=channels, messages_types=messages_types, *args, **kwargs
            )

    return ConfiguredEventsViewSet
