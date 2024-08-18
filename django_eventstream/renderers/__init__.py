import importlib

if importlib.util.find_spec("rest_framework") is None:
    from django_eventstream.utils import raise_not_found_module_error

    BrowsableAPIEventStreamRenderer = raise_not_found_module_error
    SSEEventRenderer = raise_not_found_module_error
else:
    from .browsableapieventstreamrenderer import BrowsableAPIEventStreamRenderer
    from .sserenderer import SSEEventRenderer
