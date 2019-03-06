from django.conf.urls import url
from channels.routing import URLRouter
from channels.http import AsgiHandler
from channels.auth import AuthMiddlewareStack
import django_eventstream

urlpatterns = [
	url(r'^rooms/(?P<room_id>[^/]+)/events/', AuthMiddlewareStack(
		URLRouter(django_eventstream.routing.urlpatterns)
	), {'format-channels': ['room-{room_id}']}),
	url(r'', AsgiHandler),
]
