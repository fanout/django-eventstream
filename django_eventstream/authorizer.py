class DefaultAuthorizer(object):
	# user=None for anonymous
	def can_read_channel(self, user, channel):
		return True
