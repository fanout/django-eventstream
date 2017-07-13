class DefaultAuthorizer(object):
	# user=None for anonymous
	def can_read_channel(user, channel):
		return True
