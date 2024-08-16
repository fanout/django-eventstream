from django.test import Client
from .basesseclient import BaseSSEClient


class SSEClient(Client, BaseSSEClient):
    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        BaseSSEClient.__init__(self)

    def get(self, *args, **kwargs):
        self.response = super().get(*args, **kwargs)
        return self.response
