# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import asyncio

from asgiref.sync import sync_to_async
from django.test import TestCase
from django_eventstream.views import Listener, stream
from django_eventstream.eventrequest import EventRequest
from unittest import IsolatedAsyncioTestCase

from django_eventstream.storage import DjangoModelStorage
from unittest.mock import patch


EVENTS_LIMIT = 100
EVENTS_OVER_LIMIT = 2
INITIAL_EVENT = 0
CHANNEL_NAME = "testchannel"


class DjangoStreamTest(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = DjangoModelStorage()
        pass

    @patch("django_eventstream.eventstream.get_storage")
    async def test_stream_with_last_event_id_does_not_loop_forever(
        self, mock_get_storage
    ):
        request, listener = await self.__initialise_test(mock_get_storage)

        with patch.object(
            self.storage, "get_events", wraps=self.storage.get_events
        ) as wrapped_storage:

            promise = asyncio.create_task(
                self.__collect_response(stream(request, listener))
            )
            await asyncio.sleep(2)
            promise.cancel()

            try:
                await promise
                raise ValueError("stream completed unexpectedly")
            except asyncio.CancelledError:
                pass

            # print(self.storage.get_events.call_args_list)
            self.__assert_all_events_are_retrieved_only_once()

    def __assert_all_events_are_retrieved_only_once(self):
        self.storage.get_events.assert_any_call(
            CHANNEL_NAME, INITIAL_EVENT, limit=EVENTS_LIMIT + 1
        )
        self.storage.get_events.assert_any_call(
            CHANNEL_NAME, EVENTS_LIMIT, limit=EVENTS_LIMIT + 1
        )

    async def __initialise_test(self, mock_get_storage):
        mock_get_storage.return_value = self.storage

        mock_listener = Listener()
        mock_listener.aevent.wait = mock_wait

        request = self.__create_event_request()
        await self.__populate_db_with_events()
        return request, mock_listener

    async def __collect_response(self, stream_iter):
        response = ""
        async for chunk in stream_iter:
            response += chunk
        return response

    def __create_event_request(self):
        request = EventRequest()
        request.is_next = False
        request.is_recover = False
        request.channels = [CHANNEL_NAME]
        request.channel_last_ids = {CHANNEL_NAME: INITIAL_EVENT}
        return request

    @sync_to_async
    def __populate_db_with_events(self):
        for i in range(EVENTS_LIMIT + EVENTS_OVER_LIMIT):
            self.storage.append_event(CHANNEL_NAME, "message", "dummy")


async def mock_send(*args, **kwargs):
    pass


async def mock_wait(*args, **kwargs):
    pass
