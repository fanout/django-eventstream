from .sseclient import SSEClient
from .basesseclient import BaseSSEClient


import importlib

if importlib.util.find_spec("rest_framework") is not None:
    from .sseapiclient import SSEAPIClient
else:
    from django_eventstream.utils import raise_not_found_module_error

    SSEAPIClient = raise_not_found_module_error
