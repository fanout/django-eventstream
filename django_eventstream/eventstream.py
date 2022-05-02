import copy
import json
from django.core.serializers.json import DjangoJSONEncoder
from .storage import EventDoesNotExist
from .eventresponse import EventResponse
from .utils import make_id, publish_event, publish_kick, \
	get_storage, get_channelmanager, have_channels

class EventPermissionError(Exception):
	def __init__(self, message, channels=None):
		super(Exception, self).__init__(message)
		if channels is None:
			channels = []
		self.channels = copy.deepcopy(channels)

def send_event(channel, event_type, data, skip_user_ids=None, async_publish=True, json_encode=True):
	from .event import Event

	if json_encode:
		data = json.dumps(data, cls=DjangoJSONEncoder)

	if skip_user_ids is None:
		skip_user_ids = []

	storage = get_storage()
	channelmanager = get_channelmanager()

	if channelmanager.is_channel_reliable(channel) and storage:
		e = storage.append_event(channel, event_type, data)
		pub_id = str(e.id)
		pub_prev_id = str(e.id - 1)
	else:
		e = Event(channel, event_type, data)
		pub_id = None
		pub_prev_id = None

	if have_channels():
		from .consumers import get_listener_manager
		# send to local listeners
		get_listener_manager().add_to_queues(channel, e)

	# publish through grip proxy
	publish_event(
		channel,
		event_type,
		data,
		pub_id,
		pub_prev_id,
		skip_user_ids=skip_user_ids,
		blocking=(not async_publish))

def get_events(request, limit=100, user=None):
	if user is None:
		user = request.user

	resp = EventResponse()
	resp.is_next = request.is_next
	resp.is_recover = request.is_recover
	resp.user = user

	if len(request.channels) == 0:
		return resp

	limit_per_type = int(limit / len(request.channels))
	if limit_per_type < 1:
		limit_per_type = 1

	storage = get_storage()
	channelmanager = get_channelmanager()

	inaccessible_channels = []
	for channel in request.channels:
		if not channelmanager.can_read_channel(user, channel):
			inaccessible_channels.append(channel)

	if len(inaccessible_channels) > 0:
		msg = 'Permission denied to channels: %s' % (
			', '.join(inaccessible_channels))
		raise EventPermissionError(msg, channels=inaccessible_channels)

	for channel in request.channels:
		reset = False

		last_id = request.channel_last_ids.get(channel)
		more = False

		if channelmanager.is_channel_reliable(channel) and storage:
			if last_id is not None:
				try:
					events = storage.get_events(
						channel,
						int(last_id),
						limit=limit_per_type + 1)
					if len(events) >= limit_per_type + 1:
						events = events[:limit_per_type]
						more = True
				except EventDoesNotExist as e:
					reset = True
					events = []
					last_id = str(e.current_id)
			else:
				events = []
				last_id = str(storage.get_current_id(channel))
		else:
			events = []
			last_id = None

		resp.channel_items[channel] = events
		if last_id is not None:
			resp.channel_last_ids[channel] = last_id
		if reset:
			resp.channel_reset.add(channel)
		if more:
			last_id_before_limit = events[-1].id
			request.channel_last_ids[channel] = last_id_before_limit
			resp.channel_more.add(channel)
	return resp

def get_current_event_id(channels):
	storage = get_storage()

	if not storage:
		raise ValueError('get_current_event_id requires storage to be enabled')

	cur_ids = {}
	for channel in channels:
		cur_ids[channel] = str(storage.get_current_id(channel))

	return make_id(cur_ids)

def channel_permission_changed(user, channel):
	channelmanager = get_channelmanager()
	if not channelmanager.can_read_channel(user, channel):
		user_id = user.id if user else 'anonymous'

		if have_channels():
			from .consumers import get_listener_manager
			# kick local listeners
			get_listener_manager().kick(user_id, channel)

		# kick users connected to grip proxy
		publish_kick(user_id, channel)
