from django.conf.urls import include, url
import django_eventstream
from . import views

urlpatterns = [
	url(r'^$', views.home),
	url(r'^messages/$', views.messages),
	url(r'^events/', include(django_eventstream.urls)),
]
