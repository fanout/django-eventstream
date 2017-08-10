# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class ChatMessage(models.Model):
	user = models.CharField(max_length=63)
	date = models.DateTimeField(auto_now=True, db_index=True)
	text = models.TextField()

	def to_data(self):
		out = {}
		out['id'] = self.id
		out['from'] = self.user
		out['date'] = self.date.isoformat()
		out['text'] = self.text
		return out
