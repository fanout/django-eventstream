from rest_framework import viewsets
from chat.models import ChatRoom
from chat.serializers import ChatRoomSerializer

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    lookup_field = 'euid'

    def get_queryset(self):
        return ChatRoom.objects.all()