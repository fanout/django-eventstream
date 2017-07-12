import datetime
import json
import urllib
import threading
import importlib
from werkzeug.http import parse_options_header
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from gripcontrol import HttpStreamFormat
from django_grip import publish

# minutes before purging an event from the database
EVENT_TIMEOUT = 60 * 24

# attempt to trim this many events per pass
EVENT_TRIM_BATCH = 50

tlocal = threading.local()

# return dict of (channel, last-id)
def parse_grip_last(s):
	parsed = parse_options_header(s, multiple=True)

	out = {}
	for n in range(0, len(parsed), 2):
		channel = parsed[n]
		params = parsed[n + 1]
		last_id = params.get('last-id')
		if last_id is None:
			raise ValueError('channel "%s" has no last-id param' % channel)
		out[channel] = last_id
	return out

# return dict of (channel, last-id)
def parse_last_event_id(s):
	out = {}
	parts = s.split(',')
	for part in parts:
		channel, last_id = part.split(':')
		out[channel] = last_id
	return out

def make_id(ids):
	id_parts = []
	for channel, id in ids.iteritems():
		enc_channel = urllib.quote(channel)
		id_parts.append('%s:%s' % (enc_channel, id))
	return ','.join(id_parts)

def sse_encode_event(event_type, data, event_id=None):
	out = 'event: %s\n' % event_type
	if event_id:
		out += 'id: %s\n' % event_id
	out += 'data: %s\n\n' % json.dumps(data)
	return out

def sse_error_response(condition, text, extra={}):
	data = {'condition': condition, 'text': text}
	for k, v in extra.iteritems():
		data[k] = v
	body = sse_encode_event('stream-error', data, event_id='error')
	return HttpResponse(body, content_type='text/event-stream')

def publish_event(channel, event_type, data, pub_id, pub_prev_id):
	content = sse_encode_event(event_type, data, event_id='%I')
	publish(
		'events-%s' % channel,
		HttpStreamFormat(content),
		id=pub_id,
		prev_id=pub_prev_id)

def publish_kick(user_id, channel):
	msg = 'Permission denied to channels: %s' % channel
	data = {'condition': 'forbidden', 'text': msg, 'channels': [channel]}
	content = sse_encode_event('stream-error', data, event_id='error')
	publish(
		'user-%s' % user_id,
		HttpStreamFormat(content),
		id='kick-1')
	publish(
		'user-%s' % user_id,
		HttpStreamFormat(close=True),
		id='kick-2',
		prev_id='kick-1')

def trim_event_log():
	from .models import Event
	now = timezone.now()
	cutoff = now - datetime.timedelta(minutes=EVENT_TIMEOUT)
	while True:
		events = Event.objects.filter(created__lt=cutoff)[:EVENT_TRIM_BATCH]
		if len(events) < 1:
			break
		for e in events:
			try:
				e.delete()
			except Event.DoesNotExist:
				# someone else deleted. that's fine
				pass

def load_class(name):
	at = name.rfind('.')
	if at == -1:
		raise ValueError('class name contains no \'.\'')
	module_name = name[0:at]
	class_name = name[at + 1:]
	return getattr(importlib.import_module(module_name), class_name)()

# load and keep in thread local storage
def get_class(name):
	if not hasattr(tlocal, 'loaded'):
		tlocal.loaded = {}
	c = tlocal.loaded.get(name)
	if c is None:
		c = load_class(name)
		tlocal.loaded[name] = c
	return c

def get_class_from_setting(setting_name, default=None):
	if hasattr(settings, setting_name):
		return get_class(getattr(settings, setting_name))
	elif default:
		return get_class(default)
	else:
		raise ValueError('%s not specified' % setting_name)

def get_authorizer():
	return get_class_from_setting(
		'EVENTSTREAM_AUTHORIZER_CLASS',
		'django_eventstream.authorizer.DefaultAuthorizer')
