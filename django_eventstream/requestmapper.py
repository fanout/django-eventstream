class RequestMapperBase(object):
	def get_channels_for_request(self, request, view_kwargs):
		raise NotImplementedError()

class DefaultRequestMapper(RequestMapperBase):
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
