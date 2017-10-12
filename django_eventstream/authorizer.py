class AuthorizorBase(object):
	def can_read_channel(self, user, channel):
		raise NotImplementedError()

class DefaultAuthorizer(AuthorizorBase):
	# user=None for anonymous
	def can_read_channel(self, user, channel):
		return True
