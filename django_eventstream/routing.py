from django.urls import path
from . import consumers

urlpatterns = [
    path('', consumers.EventsConsumer.as_asgi()),
]
