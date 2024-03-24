from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django_eventstream.views.eventstreamerview import events
from django_eventstream.renderers import SSEEventRenderer, BrowsableAPIEventStreamRenderer

class EventsViewSet(ViewSet):
    """
    A viewset to stream events to the client. Here you will be able to see the events in real time.

    By default, this viewset will not stream any events, beacause you must configure the channels you want to see the events from.
    To configure the channels, you can do it in three ways:
        - By setting the channels attribute in the class definition.
        - By setting the channels query parameter in the request.
        - By setting the channel in the URL.
    Those three ways are mutually exclusive, so you can only use one of them.

    If you want to see a specific type of messages and not the default "message" type, you can set the messages_types attribute in the class definition. 
    That the only way provide to set the messages types.
    """
    
    http_method_names = ['get']
    renderer_classes = (BrowsableAPIEventStreamRenderer, SSEEventRenderer)

    def __init__(self, channels: list = None, messages_types: list = None, *args, **kwargs):
        super().__init__()
        self.channels = channels if channels is not None else []
        self.messages_types = messages_types if messages_types is not None else None
    
    def list(self, request):
        if len(self.channels) > 0 and request.query_params.get('channels'):
            return Response({"error": "Conflicting channel specifications in ViewSet configuration and query parameters."}, status=status.HTTP_400_BAD_REQUEST)
        
        if self.messages_types :
            if len(self.messages_types) > 0 and request.query_params.get('messages_types'):
                return Response({"error": "Conflicting messages types specifications in ViewSet configuration and query parameters."}, status=status.HTTP_400_BAD_REQUEST)
        
        self.messages_types = request.query_params.get('messages_types', '').split(',') if request.query_params.get('messages_types') else self.messages_types

        if len(self.channels) == 0 :
            self.channels = request.query_params.get('channels', '').split(',') if request.query_params.get('channels') else []

        return self._stream_or_respond(self.channels, request)

    @action(detail=False, methods=['get'], url_path='(?P<channel>[^/.]+)')
    def channel(self, request, channel=None):
        if len(self.channels) > 0:
            return Response({"error": "Conflicting channel specifications in URL and ViewSet configuration."}, status=status.HTTP_400_BAD_REQUEST)
        return self._stream_or_respond([channel], request._request)
    
    def _stream_or_respond(self, channels, django_request):
        django_request = django_request._request
        kwargs = {'channels': channels}
        if 'text/event-stream' in django_request.META.get('HTTP_ACCEPT', '') or 'text/event-stream' in django_request.GET.get('format', ''):
            return events(django_request, **kwargs)
        elif 'text/html' in django_request.META.get('HTTP_ACCEPT', '') or 'text/html' in django_request.GET.get('format', ''):
            data = {'channels': ', '.join(channels)} if channels else {}
            data['messages_types'] = ', '.join(self.messages_types) if self.messages_types else "message"
            print("data['messages_types']")
            print(data['messages_types'])

            return Response(data, status=status.HTTP_200_OK)
        
        return Response({"error": "This endpoint only supports text/event-stream and text/html accept types."}, status=status.HTTP_400_BAD_REQUEST)

def configure_events_view_set(channels=None, messages_types=None):
    """
    Configure la classe EventsViewSet avec des canaux et des types de messages spécifiques.
    """
    class ConfiguredEventsViewSet(EventsViewSet):
        def __init__(self, *args, **kwargs):
            super().__init__(channels=channels, messages_types=messages_types, *args, **kwargs)
    return ConfiguredEventsViewSet
