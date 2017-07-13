import copy
import json
from .eventresponse import EventResponse
from .utils import make_id, publish_event, publish_kick, trim_event_log, get_authorizer

class EventPermissionError(Exception):
	def __init__(self, message, channels=[]):
		super(Exception, self).__init__(message)
		self.channels = copy.deepcopy(channels)

def append_event(channel, event_type, data):
	from .models import Event
	e = Event(channel=channel, type=event_type, data=json.dumps(data))
	e.save()
	trim_event_log()
	return e

# TODO: skip_user_ids option
def send_event(channel, event_type, data):
	e = append_event(channel, event_type, data)
	publish_event(channel, event_type, data, str(e.eid), str(e.eid - 1))

def get_events(request, limit=100, user=None):
	from .models import EventCounter, Event

	resp = EventResponse()
	resp.is_recover = request.is_recover
	resp.user = user

	if len(request.channels) == 0:
		return resp

	limit_per_type = limit / len(request.channels)
	if limit_per_type < 1:
		limit_per_type = 1

	authorizer = get_authorizer()

	inaccessible_channels = []
	for channel in request.channels:
		if not authorizer.can_read_channel(user, channel):
			inaccessible_channels.append(channel)

	if len(inaccessible_channels) > 0:
		msg = 'Permission denied to channels: %s' % (
			', '.join(inaccessible_channels))
		raise EventPermissionError(msg, channels=inaccessible_channels)

	for channel, last_id in request.channel_last_ids.iteritems():
		try:
			ec = EventCounter.objects.get(name=channel)
			cur_id = ec.value
		except EventCounter.DoesNotExist:
			cur_id = 0

		reset = False

		if last_id is not None and int(last_id) != cur_id:
			try:
				Event.objects.get(channel=channel, eid=int(last_id))
				ok = True
			except Event.DoesNotExist:
				ok = False

			if ok:
				events = Event.objects.filter(
					channel=channel,
					eid__gte=int(last_id)
				).order_by('eid')[:limit_per_type]

				if len(events) > 0 and events[0].eid == int(last_id):
					events = events[1:]
				else:
					ok = False

			if not ok:
				# flag reset, and read events going forward
				reset = True
				events = []
				last_id = str(cur_id)
		else:
			# read events going forward
			events = []
			last_id = str(cur_id)

		items = []
		for e in events:
			item = EventResponse.Item()
			item.channel = channel
			item.type = e.type
			item.id = str(e.eid)
			item.data = json.loads(e.data)
			items.append(item)
		resp.channel_items[channel] = items
		resp.channel_last_ids[channel] = last_id
		if reset:
			resp.channel_reset.add(channel)
	return resp

def get_current_event_id(channels):
	from .models import EventCounter

	cur_ids = {}
	for channel in channels:
		try:
			ec = EventCounter.objects.get(name=channel)
			cur_id = ec.value
		except EventCounter.DoesNotExist:
			cur_id = 0

		cur_ids[channel] = str(cur_id)

	return make_id(cur_ids)

# TODO: set pub meta: require_sub=channel
def channel_permission_changed(user, channel):
	authorizer = get_authorizer()
	if not authorizer.can_read_channel(user, channel):
		user_id = self.user.id if self.user else 'anonymous'
		publish_kick(user_id)
