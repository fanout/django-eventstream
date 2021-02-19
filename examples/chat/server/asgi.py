"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import sys

filepath = os.path.abspath(__file__)

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(filepath)))))

import dotenv
dotenv.read_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(filepath)), '.env'))

import django
from django.core.asgi import get_asgi_application
from django.conf.urls import url
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import django_eventstream

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

application = ProtocolTypeRouter({
    'http': URLRouter([
        url(r'^rooms/(?P<room_id>[^/]+)/events/', AuthMiddlewareStack(
            URLRouter(django_eventstream.routing.urlpatterns)
        ), { 'format-channels': ['room-{room_id}'] }),

        # older endpoint allowing client to select channel. not recommended
        url(r'^events/', AuthMiddlewareStack(URLRouter(
            django_eventstream.routing.urlpatterns
        ))),

        url(r'', get_asgi_application()),
    ]),
})
