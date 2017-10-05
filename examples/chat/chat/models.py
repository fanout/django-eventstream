# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class ChatRoom(models.Model):
	eid = models.CharField(max_length=64, unique=True)

class ChatMessage(models.Model):
	room = models.ForeignKey(ChatRoom)
	user = models.CharField(max_length=64)
	date = models.DateTimeField(auto_now=True, db_index=True)
	text = models.TextField()

	def to_data(self):
		out = {}
		out['id'] = self.id
		out['from'] = self.user
		out['date'] = self.date
		out['text'] = self.text
		return out
