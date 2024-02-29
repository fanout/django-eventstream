# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import asyncio
import copy
import threading
from asgiref.sync import sync_to_async
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from .utils import add_default_headers

MAX_PENDING = 10


class Listener(object):
    def __init__(self):
        self.loop = None
        self.aevent = asyncio.Event()
        self.user_id = ""
        self.channels = set()
        self.channel_items = {}
        self.overflow = False
        self.error = ""

    def assign_loop(self):
        self.loop = asyncio.get_event_loop()

    def wake_threadsafe(self):
        self.loop.call_soon_threadsafe(self.aevent.set)


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
            for listener in listeners:
                items = listener.channel_items.get(channel)
                if items is None:
                    items = []
                    listener.channel_items[channel] = items
                if len(items) < MAX_PENDING:
                    items.append(event)
                    wake.append(listener)
                else:
                    listener.overflow = True
            for listener in wake:
                listener.wake_threadsafe()
        finally:
            self.lock.release()

    def kick(self, user_id, channel):
        self.lock.acquire()
        try:
            wake = []
            listeners = self.listeners_by_channel.get(channel, set())
            for listener in listeners:
                if listener.user_id == user_id:
                    msg = "Permission denied to channels: %s" % channel
                    listener.error = {
                        "condition": "forbidden",
                        "text": msg,
                        "extra": {"channels": [channel]},
                    }
                    wake.append(listener)
            for listener in wake:
                listener.wake_threadsafe()
        finally:
            self.lock.release()


listener_manager = ListenerManager()


def get_listener_manager():
    return listener_manager


async def stream(event_request, listener):
    from .eventstream import get_events, EventPermissionError
    from .utils import sse_encode_event, sse_encode_error, make_id

    get_events = sync_to_async(get_events)

    listener.assign_loop()

    lm = get_listener_manager()
    lm.add_listener(listener)

    try:
        first_result = True

        while True:
            try:
                event_response = await get_events(event_request)
            except EventPermissionError as e:
                body = sse_encode_error(
                    "forbidden", str(e), extra={"channels": e.channels}
                )
                yield body
                break

            last_ids = copy.deepcopy(event_response.channel_last_ids)
            event_id = make_id(last_ids)

            body = ""

            if first_result:
                first_result = False

                # include padding on the first result
                body += ":" + (" " * 2048) + "\n\n"
                body += "event: stream-open\ndata:\n\n"

            if len(event_response.channel_reset) > 0:
                body += sse_encode_event(
                    "stream-reset",
                    {"channels": list(event_response.channel_reset)},
                    event_id=event_id,
                    json_encode=True,
                )

            for channel, items in event_response.channel_items.items():
                for item in items:
                    last_ids[channel] = item.id
                    event_id = make_id(last_ids)
                    body += sse_encode_event(item.type, item.data, event_id=event_id)

            yield body

            if len(event_response.channel_more) > 0:
                # read again immediately
                continue

            # FIXME: reconcile without re-reading from db

            lm.lock.acquire()
            conflict = False
            if len(listener.channel_items) > 0:
                # items were queued while reading from the db. toss them and
                #   read from db again
                listener.aevent.clear()
                listener.channel_items = {}
                conflict = True
            lm.lock.release()

            if conflict:
                continue

            # if we get here then the client is caught up. time to wait

            while True:
                f = asyncio.ensure_future(listener.aevent.wait())
                while True:
                    done, _ = await asyncio.wait([f], timeout=20)
                    if f in done:
                        break
                    body = "event: keep-alive\ndata:\n\n"
                    yield body

                lm.lock.acquire()

                channel_items = listener.channel_items
                overflow = listener.overflow
                error_data = listener.error

                listener.aevent.clear()
                listener.channel_items = {}
                listener.overflow = False

                lm.lock.release()

                body = ""
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
                            item.type, item.data, event_id=event_id
                        )

                more = True

                if error_data:
                    condition = error_data["condition"]
                    text = error_data["text"]
                    extra = error_data.get("extra")
                    body += sse_encode_error(condition, text, extra=extra)
                    more = False

                if body or not more:
                    yield body

                if not more:
                    break

                if overflow:
                    # check db
                    break

            event_request.channel_last_ids = last_ids
    finally:
        listener.aevent.set()
        lm.remove_listener(listener)


def events(request, **kwargs):
    from .eventrequest import EventRequest
    from .eventstream import EventPermissionError, get_events
    from .utils import sse_error_response

    try:
        event_request = EventRequest(request, view_kwargs=kwargs)
        response = None
    except EventRequest.ResumeNotAllowedError as e:
        response = HttpResponseBadRequest("Invalid request: %s.\n" % str(e))
    except EventRequest.GripError as e:
        if request.grip.proxied:
            response = sse_error_response("internal-error", "Invalid internal request.")
        else:
            response = sse_error_response(
                "bad-request", "Invalid request: %s." % str(e)
            )
    except EventRequest.Error as e:
        response = sse_error_response("bad-request", "Invalid request: %s." % str(e))
    except EventPermissionError as e:
        response = sse_error_response("forbidden", str(e), {"channels": e.channels})

    # for grip requests, prepare immediate response
    if not response and hasattr(request, "grip") and request.grip.proxied:
        try:
            event_response = get_events(event_request)
            response = event_response.to_grip_response(request)
        except EventPermissionError as e:
            response = sse_error_response("forbidden", str(e), {"channels": e.channels})

    # if this was a grip request or we encountered an error, respond now
    if response:
        add_default_headers(response, request=request)
        return response

    # if we got here then the request was not a grip request, and there
    #   were no errors, so we can begin a local stream response

    listener = Listener()
    listener.user_id = event_request.user.pk if event_request.user else "anonymous"
    listener.channels = event_request.channels

    response = StreamingHttpResponse(
        stream(event_request, listener), content_type="text/event-stream"
    )
    add_default_headers(response, request=request)

    return response
