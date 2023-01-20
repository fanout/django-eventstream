import copy
import time
import jwt
import six
from gripcontrol import Channel
from django.conf import settings
from django.http import HttpResponse
from .utils import sse_encode_event, make_id, build_id_escape

try:
	from urllib import quote
except ImportError:
	from urllib.parse import quote

class EventResponse(object):
	def __init__(self):
		self.channel_items = {}
		self.channel_last_ids = {}
		self.channel_reset = set()
		self.channel_more = set()
		self.is_next = False
		self.is_recover = False
		self.user = None

	def to_http_response(self, http_request):
		last_ids = copy.deepcopy(self.channel_last_ids)
		event_id = make_id(last_ids)

		body = ''

		if not self.is_next:
			body += ':' + (' ' * 2048) + '\n\n'
			body += 'event: stream-open\ndata:\n\n'

		if len(self.channel_reset) > 0:
			body += sse_encode_event(
				'stream-reset',
				{'channels': list(self.channel_reset)},
				event_id=event_id,
				json_encode=True)

		for channel, items in six.iteritems(self.channel_items):
			for item in items:
				last_ids[channel] = item.id
				event_id = make_id(last_ids)
				body += sse_encode_event(
					item.type,
					item.data,
					event_id=event_id,
					escape=True)

		resp = HttpResponse(body, content_type='text/event-stream')

		more = (len(self.channel_more) > 0)

		user_id = str(self.user.id) if self.user else 'anonymous'

		params = http_request.GET.copy()
		params['link'] = 'next'
		if more:
			params['lastEventId'] = event_id
			if 'recover' in params:
				del params['recover']
		else:
			params['recover'] = 'true'
			if 'lastEventId' in params:
				del params['lastEventId']
		es_meta = {
			'iss': 'es',
			'exp': int(time.time()) + 3600,
			'channels': list(self.channel_items.keys()),
			'user': user_id
		}
		params['es-meta'] = six.ensure_text(jwt.encode(es_meta,
				settings.SECRET_KEY.encode('utf-8')))
		next_uri = http_request.path + '?' + params.urlencode()

		instruct = http_request.grip.start_instruct()

		instruct.set_next_link(next_uri)

		for channel in six.iterkeys(self.channel_items):
			enc_channel = quote(channel)
			last_id = last_ids.get(channel)
			gc = Channel('events-%s' % enc_channel, prev_id=last_id)
			if last_id:
				gc.filters.append('build-id')
			gc.filters.append('skip-users')
			instruct.add_channel(gc)

		gc = Channel('user-%s' % user_id)
		gc.filters.append('require-sub')
		instruct.add_channel(gc)

		if not more:
			instruct.set_hold_stream()

		if len(last_ids) > 0:
			id_parts = []
			for channel in six.iterkeys(last_ids):
				enc_channel = quote(channel)
				id_parts.append('%s:%%(events-%s)s' % (build_id_escape(
						enc_channel), enc_channel))
			id_format = ','.join(id_parts)
			instruct.meta['id_format'] = id_format

		instruct.meta['user'] = user_id

		instruct.set_keep_alive('event: keep-alive\ndata:\n\n', 20)

		return resp
