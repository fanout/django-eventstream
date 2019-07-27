import time
import jwt
import six
from django.contrib.auth import get_user_model
from django.conf import settings
from .utils import parse_last_event_id, get_channelmanager

try:
	from urllib import unquote
except ImportError:
	from urllib.parse import unquote

class EventRequest(object):
	class Error(ValueError):
		pass

	class GripError(Error):
		pass

	class ResumeNotAllowedError(Error):
		pass

	def __init__(self, http_request=None, channel_limit=10, view_kwargs=None):
		if view_kwargs is None:
			view_kwargs = {}

		self.channels = set()
		self.channel_last_ids = {}
		self.is_recover = False
		self.user = None

		if http_request:
			self.apply_http_request(http_request,
				channel_limit=channel_limit,
				view_kwargs=view_kwargs)

	def apply_http_request(self, http_request, channel_limit, view_kwargs):
		is_next = False
		is_recover = False
		user = None

		es_meta = {}
		if http_request.GET.get('es-meta'):
			es_meta = jwt.decode(http_request.GET['es-meta'], settings.SECRET_KEY.encode('utf-8'))
			if int(time.time()) >= es_meta['exp']:
				raise ValueError('es-meta signature is expired')

		if 'user' in es_meta:
			if es_meta['user'] != 'anonymous':
				user = get_user_model().objects.get(pk=es_meta['user'])
		else:
			if hasattr(http_request, 'user') and http_request.user.is_authenticated:
				user = http_request.user

		if 'channels' in es_meta:
			channels = es_meta['channels']
		else:
			channelmanager = get_channelmanager()
			channels = channelmanager.get_channels_for_request(http_request, view_kwargs)

		if len(channels) < 1:
			raise EventRequest.Error('No channels specified')

		if len(channels) > channel_limit:
			raise EventRequest.Error('Channel limit exceeded')

		if http_request.GET.get('link') == 'next':
			is_next = True

		if http_request.GET.get('recover') == 'true':
			channel_last_ids = {}
			is_recover = True
			for grip_channel, last_id in six.iteritems(http_request.grip.last):
				if not grip_channel.startswith('events-'):
					continue
				channel = unquote(grip_channel[7:])
				if channel in channels:
					channel_last_ids[channel] = last_id
		else:
			last_event_id = http_request.META.get('HTTP_LAST_EVENT_ID')
			if not last_event_id:
				# take the first non-empty param, from the end
				for val in reversed(http_request.GET.getlist('lastEventId')):
					if val:
						last_event_id = val
						break

			if last_event_id:
				if last_event_id == 'error':
					raise EventRequest.ResumeNotAllowedError(
						'Can\'t resume session after stream-error')

				try:
					parsed = parse_last_event_id(last_event_id)

					channel_last_ids = {}
					for channel, last_id in six.iteritems(parsed):
						channel = unquote(channel)
						if channel in channels:
							channel_last_ids[channel] = last_id
				except:
					raise EventRequest.Error(
						'Failed to parse Last-Event-ID or lastEventId')
			else:
				channel_last_ids = {}

		self.channels = channels
		self.channel_last_ids = channel_last_ids
		self.is_next = is_next
		self.is_recover = is_recover
		self.user = user
