# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

import jwt
from django.conf import settings
from django.test import RequestFactory, TestCase

from django_eventstream.eventrequest import EventRequest


class EventRequestEsMetaTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self, ticket):
        return self.factory.get("/events/", {"es-meta": ticket})

    def _encode(self, payload):
        return jwt.encode(payload, settings.SECRET_KEY.encode("utf-8"), algorithm="HS256")

    def test_expired_es_meta_ticket_raises_event_request_error(self):
        expired_ticket = self._encode(
            {"user": "anonymous", "channels": ["test"], "exp": int(time.time()) - 60}
        )
        request = self._make_request(expired_ticket)

        with self.assertRaises(EventRequest.Error):
            EventRequest(request, view_kwargs={})

    def test_malformed_es_meta_ticket_raises_event_request_error(self):
        request = self._make_request("not-a-real-jwt")

        with self.assertRaises(EventRequest.Error):
            EventRequest(request, view_kwargs={})

    def test_valid_es_meta_ticket_is_accepted(self):
        valid_ticket = self._encode(
            {"user": "anonymous", "channels": ["test"], "exp": int(time.time()) + 60}
        )
        request = self._make_request(valid_ticket)

        event_request = EventRequest(request, view_kwargs={})

        self.assertEqual(event_request.channels, ["test"])
