from django.http import HttpResponse
from django.urls import path
from .apiview import SendEventAPIView
from django_eventstream.views import configure_events_api_view
from django_eventstream.views import events


def health(request):
    return HttpResponse("ok")


urlpatterns = [
    path(
        "view-events-unconfigured-channels/",
        events,
        name="view-events-unconfigured-channels",
    ),
    path(
        "view-events/",
        events,
        {"channels": ["test"]},
        name="view-events",
    ),
    path(
        "apiview-events/",
        configure_events_api_view(
            channels=["enzo"],
            messages_types=["message", "enzo"],
            docstring="A viewset for events",
            class_name="Eventsss",
        ).as_view(),
        name="apiview-events",
    ),
    path(
        "no-configured-events/",
        configure_events_api_view().as_view(),
        name="no-configured-events",
    ),
    path("send-event/", SendEventAPIView.as_view(), name="send-event"),
    path("health/", health, name="health"),
]
