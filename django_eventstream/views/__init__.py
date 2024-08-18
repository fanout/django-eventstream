from .views import (
    Listener,
    RedisListener,
    ListenerManager,
    get_listener_manager,
    stream,
    events,
)

import importlib

if importlib.util.find_spec("rest_framework") is None:
    from django_eventstream.utils import raise_not_found_module_error

    EventsAPIView = raise_not_found_module_error
    configure_events_api_view = raise_not_found_module_error
    EventsMetadata = raise_not_found_module_error
else:
    from .apiviews import EventsAPIView, configure_events_api_view, EventsMetadata
