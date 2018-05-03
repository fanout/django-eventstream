import sys
import json
import datetime
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from .event import Event

is_python3 = sys.version_info >= (3,)

# minutes before purging an event from the database
EVENT_TIMEOUT = 60 * 24

# attempt to trim this many events per pass
EVENT_TRIM_BATCH = 50

class EventDoesNotExist(Exception):
	def __init__(self, message, current_id):
		super(Exception, self).__init__(message)
		self.current_id = current_id

class StorageBase(object):
	def append_event(self, channel, event_type, data):
		raise NotImplementedError()

	def get_events(self, channel, last_id, limit=100):
		raise NotImplementedError()

	def get_current_id(self, channel):
		raise NotImplementedError()

class DjangoModelStorage(StorageBase):
	def append_event(self, channel, event_type, data):
		from . import models

		db_event = models.Event(
			channel=channel,
			type=event_type,
			data=json.dumps(data, cls=DjangoJSONEncoder))
		db_event.save()

		self.trim_event_log()

		e = Event(
			db_event.channel,
			db_event.type,
			data,
			id=db_event.eid)

		return e

	def get_events(self, channel, last_id, limit=100):
		from . import models

		if is_python3:
			assert(isinstance(last_id, int))
		else:
			assert(isinstance(last_id, (int, long)))

		try:
			ec = models.EventCounter.objects.get(name=channel)
			cur_id = ec.value
		except models.EventCounter.DoesNotExist:
			cur_id = 0

		if last_id == cur_id:
			return []

		# look up the referenced event first, to avoid a range query when
		#   the referenced event doesn't exist
		try:
			models.Event.objects.get(
				channel=channel,
				eid=last_id)
		except models.Event.DoesNotExist:
			raise EventDoesNotExist(
				'No such event %d' % last_id,
				cur_id)

		# increase limit by 1 since we'll exclude the first result
		db_events = models.Event.objects.filter(
			channel=channel,
			eid__gte=last_id
		).order_by('eid')[:limit + 1]

		# ensure the first result matches the referenced event
		if len(db_events) == 0 or db_events[0].eid != last_id:
			raise EventDoesNotExist(
				'No such event %d' % last_id,
				cur_id)

		# exclude the first result
		db_events = db_events[1:]

		out = []
		for db_event in db_events:
			e = Event(
				db_event.channel,
				db_event.type,
				json.loads(db_event.data),
				id=db_event.eid)
			out.append(e)

		return out

	def get_current_id(self, channel):
		from . import models

		try:
			ec = models.EventCounter.objects.get(name=channel)
			return ec.value
		except models.EventCounter.DoesNotExist:
			return 0

	def trim_event_log(self):
		from . import models

		now = timezone.now()
		cutoff = now - datetime.timedelta(minutes=EVENT_TIMEOUT)
		while True:
			events = models.Event.objects.filter(
				created__lt=cutoff
			)[:EVENT_TRIM_BATCH]
			if len(events) < 1:
				break
			for e in events:
				try:
					e.delete()
				except models.Event.DoesNotExist:
					# someone else deleted. that's fine
					pass
