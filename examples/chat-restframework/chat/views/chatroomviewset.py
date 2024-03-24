from rest_framework import viewsets
from chat.models import ChatRoom
from chat.serializers import ChatRoomSerializer
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from django.http import HttpResponseRedirect

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    lookup_field = 'euid'

    def get_queryset(self):
        return ChatRoom.objects.all()