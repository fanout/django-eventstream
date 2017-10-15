import copy
import six
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

	# FIXME: use django-grip instead of manually building headers
	def to_http_response(self, http_request):
		last_ids = copy.deepcopy(self.channel_last_ids)
		event_id = make_id(last_ids)

		body = ''

		if not self.is_next:
			body += ':' + (' ' * 2048) + '\n'
			body += 'event: stream-open\ndata:\n\n'

		if len(self.channel_reset) > 0:
			body += sse_encode_event(
				'stream-reset',
				{'channels': list(self.channel_reset)},
				event_id=event_id)

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
		uri = http_request.path + '?' + params.urlencode()
		resp['Grip-Link'] = '<%s>; rel=next' % uri

		if not more:
			resp['Grip-Hold'] = 'stream'

		user_id = self.user.id if self.user else 'anonymous'

		channel_header = ''
		for channel in six.iterkeys(self.channel_items):
			if len(channel_header) > 0:
				channel_header += ', '
			enc_channel = quote(channel)
			last_id = last_ids.get(channel)
			channel_header += 'events-%s' % enc_channel
			if last_id:
				channel_header += '; prev-id=%s; filter=build-id' % last_id
			channel_header += '; filter=skip-users'
		channel_header += ', user-%s; filter=require-sub' % user_id
		resp['Grip-Channel'] = channel_header

		set_meta_header = ''

		if len(last_ids) > 0:
			id_parts = []
			for channel in six.iterkeys(last_ids):
				enc_channel = quote(channel)
				id_parts.append('%s:%%(events-%s)s' % (build_id_escape(enc_channel), enc_channel))
			id_format = ','.join(id_parts)
			set_meta_header += 'id_format="%s"' % id_format

		if len(set_meta_header) > 0:
			set_meta_header += ', '
		set_meta_header += 'user="%s"' % user_id
		resp['Grip-Set-Meta'] = set_meta_header

		keep_alive_header = 'event: keep-alive\\ndata:\\n\\n'
		keep_alive_header += '; format=cstring; timeout=20'
		resp['Grip-Keep-Alive'] = keep_alive_header

		return resp
