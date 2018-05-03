# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import IntegrityError, models, transaction

class EventCounter(models.Model):
	name = models.CharField(max_length=255, unique=True)
	value = models.BigIntegerField(default=0)
	updated = models.DateTimeField(db_index=True, auto_now=True)

	@classmethod
	def get_or_create(cls, name):
		try:
			en = cls.objects.get(name=name)
		except cls.DoesNotExist:
			try:
				en = cls(name=name)
				en.save()
			except IntegrityError:
				en = cls.objects.get(name=name)
		return en

class Event(models.Model):
	channel = models.CharField(max_length=255, db_index=True)
	type = models.CharField(max_length=255, db_index=True)
	data = models.TextField()
	eid = models.BigIntegerField(default=0, db_index=True)
	created = models.DateTimeField(db_index=True, auto_now_add=True)

	class Meta:
		unique_together = ('channel', 'eid')

	def save(self, *args, **kwargs):
		if not self.eid:
			counter = EventCounter.get_or_create(self.channel)

			with transaction.atomic():
				counter = EventCounter.objects.select_for_update(
					).get(id=counter.id)

				if counter.value == 0:
					# insert placeholder to enable querying from ID 0
					zero_event = Event(channel=self.channel)
					super(Event, zero_event).save()

				self.eid = counter.value + 1

				try:
					super(Event, self).save(*args, **kwargs)
				except Exception:
					self.eid = 0
					raise

				counter.value = self.eid
				counter.save()
		else:
			super(Event, self).save(*args, **kwargs)
