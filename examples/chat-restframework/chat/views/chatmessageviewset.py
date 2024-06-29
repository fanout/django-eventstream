from rest_framework import viewsets
from chat.models import ChatMessage, ChatRoom
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError, transaction
from chat.serializers import ChatMessageSerializer
from django_eventstream import send_event


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        """Filtrer les messages par 'room_id' passé dans l'URL."""
        room_id = self.kwargs["room_id"]

        return self.queryset.filter(room_id=room_id)

    def create(self, request, *args, **kwargs):
        room_id = self.kwargs["room_id"]
        try:
            room = ChatRoom.objects.get(eid=room_id)
        except ChatRoom.DoesNotExist:
            try:
                room = ChatRoom(eid=room_id)
                room.save()
            except IntegrityError:
                room = ChatRoom.objects.get(eid=room_id)

        mfrom = request.data.get("user")
        text = request.data.get("text")

        with transaction.atomic():
            msg = ChatMessage(room=room, user=mfrom, text=text)
            msg.save()
            send_event("room-{}".format(room_id), "message", msg.to_data())

        serialized_msg = ChatMessageSerializer(msg).data
        return Response(serialized_msg, status=status.HTTP_201_CREATED)
