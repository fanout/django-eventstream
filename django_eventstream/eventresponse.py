import copy
import urllib
from django.http import HttpResponse
from .utils import sse_encode_event, make_id

class EventResponse(object):
	class Item(object):
		def __init__(self):
			self.channel = None
			self.type = None
			self.id = None
			self.data = None

	def __init__(self):
		self.channel_items = {}
		self.channel_last_ids = {}
		self.channel_reset = set()
		self.is_recover = False
		self.user = None

	# FIXME: use django-grip instead of manually building headers
	def to_http_response(self, http_request):
		last_ids = copy.deepcopy(self.channel_last_ids)

		body = ''

		if not self.is_recover:
			body += ':' + (' ' * 2048) + '\n'
			body += 'event: stream-open\ndata:\n\n'

		if len(self.channel_reset) > 0:
			body += sse_encode_event(
				'stream-reset',
				{'channels': list(self.channel_reset)},
				event_id=make_id(last_ids))

		for channel, items in self.channel_items.iteritems():
			for item in items:
				last_ids[channel] = item.id
				body += sse_encode_event(
					item.type,
					item.data,
					event_id=make_id(last_ids))

		resp = HttpResponse(body, content_type='text/event-stream')

		params = http_request.GET.copy()
		if 'link' not in params:
			params['link'] = 'true'
		uri = http_request.path + '?' + params.urlencode()
		resp['Grip-Link'] = '<%s>; rel=next' % uri

		resp['Grip-Hold'] = 'stream'

		user_id = self.user.id if self.user else 'anonymous'

		channel_header = ''
		for channel, last_id in last_ids.iteritems():
			if len(channel_header) > 0:
				channel_header += ', '
			enc_channel = urllib.quote(channel)
			channel_header += 'events-%s' % enc_channel
			channel_header += '; prev-id=%s; filter=build-id; filter=skip-users' % last_id
		channel_header += ', user-%s; filter=require-sub' % user_id
		resp['Grip-Channel'] = channel_header

		id_parts = []
		for channel in last_ids.iterkeys():
			enc_channel = urllib.quote(channel)
			id_parts.append('%s:%%(events-%s)s' % (enc_channel, enc_channel))
		id_format = ','.join(id_parts)

		resp['Grip-Set-Meta'] = 'id_format="%s"' % id_format

		keep_alive_header = 'event: keep-alive\\ndata:\\n\\n'
		keep_alive_header += '; format=cstring; timeout=20'
		resp['Grip-Keep-Alive'] = keep_alive_header

		return resp
