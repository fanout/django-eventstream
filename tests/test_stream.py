# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import asyncio

from django.test import TestCase
from django_eventstream.consumers import EventsConsumer, Listener
from django_eventstream.eventrequest import EventRequest
from unittest import IsolatedAsyncioTestCase

from django_eventstream.storage import DjangoModelStorage
from unittest.mock import patch
from channels.db import database_sync_to_async


EVENTS_LIMIT = 100
EVENTS_OVER_LIMIT = 2
INITIAL_EVENT = 0
CHANNEL_NAME = 'testchannel'


class DjangoStreamTest(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = DjangoModelStorage()
        pass

    @patch('django_eventstream.eventstream.get_storage')
    async def test_stream_with_last_event_id_does_not_loop_forever(self, mock_get_storage):
        events_consumer, request = await self.__initialise_test(mock_get_storage)

        with patch.object(self.storage, 'get_events', wraps=self.storage.get_events) as wrapped_storage:

            promise = asyncio.create_task(events_consumer.stream(request))
            await asyncio.sleep(2)
            events_consumer.is_streaming = False
            await promise

            # print(self.storage.get_events.call_args_list)
            self.__assert_all_events_are_retrieved_only_once()
            

    def __assert_all_events_are_retrieved_only_once(self):
        self.storage.get_events.assert_any_call(CHANNEL_NAME, INITIAL_EVENT, limit=EVENTS_LIMIT + 1)
        self.storage.get_events.assert_any_call(CHANNEL_NAME, EVENTS_LIMIT, limit=EVENTS_LIMIT + 1)

    async def __initialise_test(self, mock_get_storage):
        mock_get_storage.return_value = self.storage

        events_consumer = self.__create_events_consumer()
        request = self.__create_event_request()
        await self.__populate_db_with_events()
        return events_consumer, request

    def __create_events_consumer(self):
        mock_listener = Listener()
        mock_listener.aevent.wait = mock_wait


        events_consumer = EventsConsumer()
        events_consumer.listener = mock_listener
        events_consumer.is_streaming = True
        events_consumer.base_send = mock_send
        return events_consumer

    def __create_event_request(self):
        request = EventRequest()
        request.is_next = False
        request.is_recover = False
        request.channels = [CHANNEL_NAME]
        request.channel_last_ids = {CHANNEL_NAME: INITIAL_EVENT}
        return request

    @database_sync_to_async
    def __populate_db_with_events(self):
        for i in range(EVENTS_LIMIT + EVENTS_OVER_LIMIT):
            self.storage.append_event(CHANNEL_NAME, 'message', 'dummy')

async def mock_send(*args, **kwargs):
    pass

async def mock_wait(*args, **kwargs):
    pass