from django.conf.urls import url
from . import consumers

urlpatterns = [
    url(r'^$', consumers.EventsConsumer.as_asgi()),
]
