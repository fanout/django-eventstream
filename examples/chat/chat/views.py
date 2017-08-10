# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import HttpResponse, HttpResponseNotAllowed
from django.db import transaction
from django.shortcuts import render
from django_eventstream import send_event, get_current_event_id
from .models import ChatMessage

def home(request):
	context = {}
	context['last_id'] = get_current_event_id(['chat'])
	msgs = []
	for msg in reversed(ChatMessage.objects.all().order_by('-date')[:50]):
		msgs.append(msg.to_data())
	context['messages'] = msgs
	return render(request, 'chat/home.html', context)

def messages(request):
	if request.method == 'POST':
		mfrom = request.POST['from']
		text = request.POST['text']
		with transaction.atomic():
			msg = ChatMessage(user=mfrom, text=text)
			msg.save()
			send_event('chat', 'message', msg.to_data())
		body = json.dumps(msg.to_data())
		return HttpResponse(body, content_type='application/json')
	else:
		return HttpResponseNotAllowed(['POST'])
