from .views import Listener, RedisListener, ListenerManager, get_listener_manager, stream, events

# Verify that DRF is installed
import importlib

if importlib.util.find_spec("rest_framework") is not None:
    from .apiviews import EventsAPIView, configure_events_api_view
else:
    from ..utils import raise_not_found_module_error
    EventsAPIView = raise_not_found_module_error
    configure_events_api_view = raise_not_found_module_error