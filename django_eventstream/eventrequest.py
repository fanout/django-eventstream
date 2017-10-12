import six
from .utils import parse_grip_last, parse_last_event_id, get_channelmanager

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

	def __init__(self, http_request=None, channel_limit=10, view_kwargs={}):
		self.channels = set()
		self.channel_last_ids = {}
		self.is_recover = False

		if http_request:
			self.apply_http_request(http_request,
				channel_limit=channel_limit,
				view_kwargs=view_kwargs)

	def apply_http_request(self, http_request, channel_limit, view_kwargs):
		is_next = False
		is_recover = False

		channelmanager = get_channelmanager()
		channels = channelmanager.get_channels_for_request(http_request, view_kwargs)

		if len(channels) < 1:
			raise EventRequest.Error('No channels specified')

		if len(channels) > channel_limit:
			raise EventRequest.Error('Channel limit exceeded')

		if http_request.GET.get('link') == 'next':
			is_next = True

		grip_last = None
		if http_request.GET.get('recover') == 'true':
			grip_last = http_request.META.get('HTTP_GRIP_LAST')

			if grip_last:
				try:
					grip_last = parse_grip_last(grip_last)
				except:
					raise EventRequest.GripError(
						'Failed to parse Grip-Last header')
			else:
				grip_last = {}

			channel_last_ids = {}
			is_recover = True
			for grip_channel, last_id in six.iteritems(grip_last):
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
