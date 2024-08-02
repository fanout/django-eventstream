import importlib

if importlib.util.find_spec("rest_framework") is not None:
    from .browsableapieventstreamrenderer import BrowsableAPIEventStreamRenderer
    from .sserenderer import SSEEventRenderer
else:
    from ..utils import raise_not_found_module_error
    BrowsableAPIEventStreamRenderer = raise_not_found_module_error
    SSEEventRenderer = raise_not_found_module_error