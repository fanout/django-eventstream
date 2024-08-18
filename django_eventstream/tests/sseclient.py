from django.test import Client
from .basesseclient import BaseSSEClient


class SSEClient(Client, BaseSSEClient):
    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        BaseSSEClient.__init__(self)

    def get(self, *args, **kwargs):
        if "headers" in kwargs:
            headers = {**self.default_headers, **kwargs["headers"]}
        else:
            headers = self.default_headers

        kwargs["headers"] = headers

        self.response = super().get(*args, **kwargs)
        return self.response
