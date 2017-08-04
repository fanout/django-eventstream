from django.shortcuts import render
from django_eventstream import get_current_event_id

class MyAuthorizer(object):
	def can_read_channel(self, user, channel):
		if channel.startswith('_'):
			return False
		return True

def home(request):
	context = {}
	context['url'] = '/events/?channel=test'
	context['last_id'] = get_current_event_id(['test'])
	return render(request, 'demo/home.html', context)
