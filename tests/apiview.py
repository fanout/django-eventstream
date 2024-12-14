from rest_framework.views import APIView
from django_eventstream.eventstream import send_event
from rest_framework.response import Response


class SendEventAPIView(APIView):
    def get(self, request):
        data = request.query_params.get("event_data", "Hello, world!!")
        send_event(channel="enzo", data=data, event_type="message")
        return Response(data)
