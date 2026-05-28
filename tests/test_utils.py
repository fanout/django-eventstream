# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django_eventstream import utils


class UtilsTest(TestCase):
    def test_sse_encode_event(self):
        self.assertEqual(utils.sse_encode_event("message", "hello"), "event: message\ndata: hello\n\n")

        # Check sanitization
        self.assertEqual(utils.sse_encode_event("message\nevent: foo", "hello\rworld", event_id="1\nevent_id: 2"), "event: messageevent: foo\nid: 1event_id: 2\ndata: hello\ndata: world\n\n")
