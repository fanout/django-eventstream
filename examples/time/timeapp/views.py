import time
import threading
import datetime
from django.shortcuts import render
from django_eventstream import get_current_event_id, send_event
from django_eventstream.channelmanager import DefaultChannelManager

def home(request):
	context = {}
	context['url'] = '/events/'
	context['last_id'] = get_current_event_id(['time'])
	return render(request, 'timeapp/home.html', context)

def _send_worker():
	while True:
		data = datetime.datetime.utcnow().isoformat()
		send_event('time', 'message', data)
		time.sleep(1)

def _db_ready():
	from django.db import DatabaseError
	from django_eventstream.models import Event
	try:
		# see if db tables are present
		Event.objects.count()
		return True
	except DatabaseError:
		return False

if _db_ready():
	send_thread = threading.Thread(target=_send_worker)
	send_thread.daemon = True
	send_thread.start()
