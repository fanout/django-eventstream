class ChannelManagerBase(object):
	def get_channels_for_request(self, request, view_kwargs):
		raise NotImplementedError()

	# user=None for anonymous
	def can_read_channel(self, user, channel):
		raise NotImplementedError()

	# this only has meaning if storage is enabled
	def is_channel_reliable(self, channel):
		raise NotImplementedError()

class DefaultChannelManager(ChannelManagerBase):
	def get_channels_for_request(self, request, view_kwargs):
		# by default, use view keywords, else query params
		if 'format-channels' in view_kwargs:
			out = set()
			for format_channel in view_kwargs['format-channels']:
				out.add(format_channel.format(**view_kwargs))
			return out
		elif 'channels' in view_kwargs:
			return set(view_kwargs['channels'])
		elif 'channel' in view_kwargs:
			return set([view_kwargs['channel']])
		else:
			return set(request.GET.getlist('channel'))

	def can_read_channel(self, user, channel):
		return True

	def is_channel_reliable(self, channel):
		return True
