# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-06 20:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("channel", models.CharField(db_index=True, max_length=255)),
                ("type", models.CharField(db_index=True, max_length=255)),
                ("data", models.TextField()),
                ("eid", models.BigIntegerField(db_index=True, default=0)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name="EventCounter",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("value", models.BigIntegerField(default=0)),
                ("updated", models.DateTimeField(auto_now=True, db_index=True)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="event",
            unique_together=set([("channel", "eid")]),
        ),
    ]
