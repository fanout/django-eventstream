import time
import threading
import datetime
from django.shortcuts import render
from django_eventstream import get_current_event_id, send_event
from django_eventstream.channelmanager import DefaultChannelManager

class MyChannelManager(DefaultChannelManager):
	def can_read_channel(self, user, channel):
		if channel.startswith('_'):
			return False
		return True

	def is_channel_reliable(self, channel):
		if channel.startswith('~'):
			return False
		return True

def _send_worker():
	while True:
		data = datetime.datetime.utcnow().isoformat()
		for channel in ['test', '~test']:
			send_event(channel, 'message', data)
		time.sleep(1)

def home(request):
	context = {}
	context['url'] = '/events/?channel=test'
	context['last_id'] = get_current_event_id(['test'])
	return render(request, 'basic/home.html', context)

send_thread = threading.Thread(target=_send_worker)
send_thread.daemon = True
send_thread.start()
