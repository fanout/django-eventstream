import django_eventstream

from chat.views import ChatMessageViewSet, ChatRoomViewSet, ChatEventsViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r"rooms", ChatRoomViewSet, basename="rooms")
router.register(
    r"rooms/(?P<room_id>.+)/messages", ChatMessageViewSet, basename="messages"
)
router.register(
    r"rooms/(?P<room_id>.+)/events", ChatEventsViewSet, basename="message_events"
)


urlpatterns = [
    path("", include(router.urls)),
    path("test", views.home),
]
