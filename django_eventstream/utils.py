import json
import threading
import importlib
import six
from django.conf import settings
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from gripcontrol import HttpStreamFormat

try:
	from urllib import quote
except ImportError:
	from urllib.parse import quote

tlocal = threading.local()

def have_channels():
	try:
		from channels.generic.http import AsyncHttpConsumer
		return True
	except ImportError:
		return False

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
	for channel, id in six.iteritems(ids):
		enc_channel = quote(channel)
		id_parts.append('%s:%s' % (enc_channel, id))
	return ','.join(id_parts)

def build_id_escape(s):
	out = ''
	for c in s:
		if c == '%':
			out += '%%'
		else:
			out += c
	return out

def sse_encode_event(event_type, data, event_id=None, escape=False):
	data_str = json.dumps(data, cls=DjangoJSONEncoder)
	if escape:
		event_type = build_id_escape(event_type)
		data_str = build_id_escape(data_str)
	out = 'event: %s\n' % event_type
	if event_id:
		out += 'id: %s\n' % event_id
	out += 'data: %s\n\n' % data_str
	return out

def sse_error_response(condition, text, extra={}):
	data = {'condition': condition, 'text': text}
	for k, v in six.iteritems(extra):
		data[k] = v
	body = sse_encode_event('stream-error', data, event_id='error')
	return HttpResponse(body, content_type='text/event-stream')

def publish_event(channel, event_type, data, pub_id, pub_prev_id,
		skip_user_ids=[]):
	from django_grip import publish

	content_filters = []
	if pub_id:
		event_id = '%I'
		content_filters.append('build-id')
	else:
		event_id = None
	content = sse_encode_event(event_type, data, event_id=event_id, escape=bool(pub_id))
	meta = {}
	if skip_user_ids:
		meta['skip_users'] = ','.join(skip_user_ids)
	publish(
		'events-%s' % quote(channel),
		HttpStreamFormat(content, content_filters=content_filters),
		id=pub_id,
		prev_id=pub_prev_id,
		meta=meta)

def publish_kick(user_id, channel):
	from django_grip import publish

	msg = 'Permission denied to channels: %s' % channel
	data = {'condition': 'forbidden', 'text': msg, 'channels': [channel]}
	content = sse_encode_event('stream-error', data, event_id='error')
	meta = {'require_sub': 'events-%s' % channel}
	publish(
		'user-%s' % user_id,
		HttpStreamFormat(content),
		id='kick-1',
		meta=meta)
	publish(
		'user-%s' % user_id,
		HttpStreamFormat(close=True),
		id='kick-2',
		prev_id='kick-1',
		meta=meta)

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
		return None

def get_storage():
	return get_class_from_setting('EVENTSTREAM_STORAGE_CLASS')

def get_channelmanager():
	return get_class_from_setting(
		'EVENTSTREAM_CHANNELMANAGER_CLASS',
		'django_eventstream.channelmanager.DefaultChannelManager')

def augment_cors_headers(headers):
	cors_origin = ''
	if hasattr(settings, 'EVENTSTREAM_ALLOW_ORIGIN'):
		cors_origin = settings.EVENTSTREAM_ALLOW_ORIGIN

	if cors_origin:
		headers['Access-Control-Allow-Origin'] = cors_origin

	allow_credentials = False
	if hasattr(settings, 'EVENTSTREAM_ALLOW_CREDENTIALS'):
		allow_credentials = settings.EVENTSTREAM_ALLOW_CREDENTIALS

	if allow_credentials:
		headers['Access-Control-Allow-Credentials'] = 'true'

