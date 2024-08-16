from django.http import HttpResponse
from django.urls import path
from .apiview import SendEventAPIView
from django_eventstream.views import configure_events_api_view


def health(request):
    return HttpResponse("ok")


urlpatterns = [
    path(
        "events/",
        configure_events_api_view(
            channels=["enzo"],
            messages_types=["message", "enzo"],
            docstring="A viewset for events",
            class_name="Eventsss",
        ).as_view(),
        name="events",
    ),
    path("send-event/", SendEventAPIView.as_view(), name="send-event"),
    path("health/", health, name="health"),
]
