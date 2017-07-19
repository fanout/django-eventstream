class Event(object):
	def __init__(self, channel, type, data, id=None):
		self.channel = channel
		self.type = type
		self.data = data
		self.id = id
