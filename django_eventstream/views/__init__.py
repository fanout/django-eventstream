from .eventstreamerview import events, get_listener_manager
try :
    from .sseview import EventsViewSet, configure_events_view_set
except  ImportError :
    pass


