import copy
import threading
import asyncio
from django.http import HttpResponseBadRequest
from django.conf import settings
from channels.generic.http import AsyncHttpConsumer
from channels.http import AsgiRequest
from channels.db import database_sync_to_async

MAX_PENDING = 10

class Listener(object):
	def __init__(self):
		self.aevent = asyncio.Event()
		self.user_id = ''
		self.channels = set()
		self.channel_items = {}
		self.overflow = False
		self.error = ''

class ListenerManager(object):
	def __init__(self):
		self.lock = threading.Lock()
		self.listeners_by_channel = {}

	def add_listener(self, listener):
		self.lock.acquire()
		try:
			for channel in listener.channels:
				clisteners = self.listeners_by_channel.get(channel)
				if clisteners is None:
					clisteners = set()
					self.listeners_by_channel[channel] = clisteners
				clisteners.add(listener)
		finally:
			self.lock.release()

	def remove_listener(self, listener):
		self.lock.acquire()
		try:
			for channel in listener.channels:
				clisteners = self.listeners_by_channel.get(channel)
				clisteners.remove(listener)
				if len(clisteners) == 0:
					del self.listeners_by_channel[channel]
		finally:
			self.lock.release()

	def add_to_queues(self, channel, event):
		self.lock.acquire()
		try:
			wake = []
			listeners = self.listeners_by_channel.get(channel, set())
			for l in listeners:
				items = l.channel_items.get(channel)
				if items is None:
					items = []
					l.channel_items[channel] = items
				if len(items) < MAX_PENDING:
					items.append(event)
					wake.append(l)
				else:
					l.overflow = True
			for l in wake:
				l.aevent.set()
		finally:
			self.lock.release()

	def kick(self, user_id, channel):
		self.lock.acquire()
		try:
			wake = []
			listeners = self.listeners_by_channel.get(channel, set())
			for l in listeners:
				if l.user_id == user_id:
					msg = 'Permission denied to channels: %s' % channel
					l.error = {'condition': 'forbidden', 'text': msg, 'channels': [channel]}
					wake.append(l)
			for l in wake:
				l.aevent.set()
		finally:
			self.lock.release()

listener_manager = ListenerManager()

def get_listener_manager():
	return listener_manager

class EventsConsumer(AsyncHttpConsumer):
	@database_sync_to_async
	def parse_request(self, request):
		from .eventrequest import EventRequest

		kwargs = self.scope['url_route']['kwargs']

		return EventRequest(request, view_kwargs=kwargs)

	@database_sync_to_async
	def get_events(self, event_request, user):
		from .eventstream import get_events

		return get_events(event_request, user=user)

	async def handle(self, body):
		from .eventrequest import EventRequest
		from .eventstream import EventPermissionError
		from .utils import sse_encode_event, sse_error_response, make_id

		self.listener = None

		request = AsgiRequest(self.scope, body)

		# TODO use GripMiddleware
		request.grip_proxied = False
		for name, value in self.scope['headers']:
			if name == b'grip-sig':
				request.grip_proxied = True
				break

		if 'user' in self.scope:
			request.user = self.scope['user']

		try:
			event_request = await self.parse_request(request)
			response = None
		except EventRequest.ResumeNotAllowedError as e:
			response = HttpResponseBadRequest(
				'Invalid request: %s.\n' % str(e))
		except EventRequest.GripError as e:
			if request.grip_proxied:
				response = sse_error_response(
					'internal-error',
					'Invalid internal request.')
			else:
				response = sse_error_response(
					'bad-request',
					'Invalid request: %s.' % str(e))
		except EventRequest.Error as e:
			response = sse_error_response(
				'bad-request',
				'Invalid request: %s.' % str(e))

		user = None
		if hasattr(request, 'user') and request.user.is_authenticated:
			user = request.user

		# for grip requests, prepare immediate response
		if not response and request.grip_proxied:
			try:
				event_response = await self.get_events(event_request, user)
				response = event_response.to_http_response(request)
			except EventPermissionError as e:
				response = sse_error_response(
					'forbidden',
					str(e),
					{'channels': e.channels})

		extra_headers = {}
		extra_headers['Cache-Control'] = 'no-cache'

		if hasattr(settings, 'EVENTSTREAM_ALLOW_ORIGIN'):
			cors_origin = settings.EVENTSTREAM_ALLOW_ORIGIN
		else:
			cors_origin = settings.ALLOWED_HOSTS

		extra_headers['Access-Control-Allow-Origin'] = cors_origin

		# if this was a grip request or we encountered an error, respond now
		if response:
			headers = []
			for name, value in response.items():
				headers.append((name, value))

			for name, value in extra_headers.items():
				headers.append((name, value))

			await self.send_response(
				response.status_code,
				response.content,
				headers=headers
			)
			return

		# if we got here then the request was not a grip request, and there
		#   were no errors, so we can begin a local stream response

		headers = [('Content-Type', 'text/event-stream')]
		for name, value in extra_headers.items():
			headers.append((name, value))

		await self.send_headers(headers=headers)

		body = b':' + (b' ' * 2048) + b'\n\n'
		body += b'event: stream-open\ndata:\n\n'
		await self.send_body(body, more_body=True)

		self.listener = Listener()
		self.is_streaming = True

		asyncio.get_event_loop().create_task(self.stream(event_request, user))

	async def stream(self, event_request, user):
		from .eventstream import EventPermissionError
		from .utils import sse_encode_event, make_id

		self.listener.user_id = user.id if user else 'anonymous'
		self.listener.channels = event_request.channels

		lm = get_listener_manager()

		lm.add_listener(self.listener)

		while self.is_streaming:
			try:
				event_response = await self.get_events(event_request, user)
			except EventPermissionError as e:
				data = {
					'condition': 'forbidden',
					'text': str(e),
					'channels': e.channels,
				}
				body = sse_encode_event('stream-error', data, event_id='error')
				await self.send_body(body.encode('utf-8'))
				break

			last_ids = copy.deepcopy(event_response.channel_last_ids)
			event_id = make_id(last_ids)

			body = ''

			if len(event_response.channel_reset) > 0:
				body += sse_encode_event(
					'stream-reset',
					{'channels': list(event_response.channel_reset)},
					event_id=event_id)

			for channel, items in event_response.channel_items.items():
				for item in items:
					last_ids[channel] = item.id
					event_id = make_id(last_ids)
					body += sse_encode_event(
						item.type,
						item.data,
						event_id=event_id)

			await self.send_body(body.encode('utf-8'), more_body=True)

			if len(event_response.channel_more) > 0:
				# read again immediately
				continue

			# FIXME: reconcile without re-reading from db

			lm.lock.acquire()
			conflict = False
			if len(self.listener.channel_items) > 0:
				# items were queued while reading from the db. toss them and
				#   read from db again
				self.listener.aevent.clear()
				self.listener.channel_items = {}
				conflict = True
			lm.lock.release()

			if conflict:
				continue

			# if we get here then the client is caught up. time to wait

			while self.is_streaming:
				f = asyncio.ensure_future(self.listener.aevent.wait())
				while True:
					done, _ = await asyncio.wait([f], timeout=20)
					if f in done:
						break
					body = 'event: keep-alive\ndata:\n\n'
					await self.send_body(body.encode('utf-8'), more_body=True)

				if not self.is_streaming:
					break

				lm.lock.acquire()

				channel_items = self.listener.channel_items
				overflow = self.listener.overflow
				error_data = self.listener.error

				self.listener.aevent.clear()
				self.listener.channel_items = {}
				self.listener.overflow = False

				lm.lock.release()

				body = ''
				for channel, items in channel_items.items():
					for item in items:
						if channel in last_ids:
							if item.id is not None:
								last_ids[channel] = item.id
							else:
								del last_ids[channel]
						if last_ids:
							event_id = make_id(last_ids)
						else:
							event_id = None
						body += sse_encode_event(
							item.type,
							item.data,
							event_id=event_id)

				more = True

				if error_data:
					body += sse_encode_event('stream-error', error_data, event_id='error')
					more = False

				if body or not more:
					await self.send_body(body.encode('utf-8'), more_body=more)

				if not more:
					self.is_streaming = False
					break

				if overflow:
					# check db
					break

			event_request.channel_last_ids = last_ids

		lm.remove_listener(self.listener)

	async def disconnect(self):
		self.is_streaming = False
		if self.listener:
			self.listener.aevent.set()
