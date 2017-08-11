# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import HttpResponse, HttpResponseNotAllowed
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django_eventstream import send_event, get_current_event_id
from .models import ChatRoom, ChatMessage

def home(request, room_id=None):
	user = request.GET.get('user')
	if user:
		if not room_id:
			room_id = 'default'

		try:
			room = ChatRoom.objects.get(eid=room_id)
			cmsgs = ChatMessage.objects.filter(
				room=room).order_by('-date')[:50]
			msgs = []
			for msg in reversed(cmsgs):
				msgs.append(msg.to_data())
		except ChatRoom.DoesNotExist:
			msgs = []

		context = {}
		context['room_id'] = room_id
		context['last_id'] = get_current_event_id(['room-%s' % room_id])
		context['messages'] = msgs
		context['user'] = user
		return render(request, 'chat/chat.html', context)
	else:
		context = {}
		if room_id:
			context['room_id'] = room_id
		else:
			context['room_id'] = ''
		return render(request, 'chat/join.html', context)

def messages(request, room_id):
	if request.method == 'POST':
		try:
			room = ChatRoom.objects.get(eid=room_id)
		except ChatRoom.DoesNotExist:
			try:
				room = ChatRoom(eid=room_id)
				room.save()
			except IntegrityError:
				# someone else made the room. no problem
				room = ChatRoom.objects.get(eid=room_id)

		mfrom = request.POST['from']
		text = request.POST['text']
		with transaction.atomic():
			msg = ChatMessage(room=room, user=mfrom, text=text)
			msg.save()
			send_event('room-%s' % room_id, 'message', msg.to_data())
		body = json.dumps(msg.to_data())
		return HttpResponse(body, content_type='application/json')
	else:
		return HttpResponseNotAllowed(['POST'])
