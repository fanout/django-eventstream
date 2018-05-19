from django.conf.urls import url, include
import django_eventstream
from . import views

urlpatterns = [
	url(r'^$', views.home),
	url(r'^(?P<room_id>[^/]+)$', views.home),
	url(r'^rooms/(?P<room_id>[^/]+)/messages/$', views.messages),
	url(r'^events/', include(django_eventstream.urls)),
]
