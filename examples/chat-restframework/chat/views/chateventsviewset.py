from django_eventstream.views.apiviews import EventsViewSet


class ChatEventsViewSet(EventsViewSet):

    def list(self, request, room_id=None):
        if room_id:
            self.channels = [f"room-{room_id}"]
        return super().list(request)
