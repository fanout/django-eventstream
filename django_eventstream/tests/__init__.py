from .sseclient import SSEClient
from .basesseclient import BaseSSEClient


import importlib

if importlib.util.find_spec("rest_framework") is None:
    from django_eventstream.utils import raise_not_found_module_error

    SSEAPIClient = raise_not_found_module_error

else:
    from .sseapiclient import SSEAPIClient
