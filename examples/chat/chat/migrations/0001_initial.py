# Generated by Django 2.1.7 on 2019-02-16 22:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user", models.CharField(max_length=64)),
                ("date", models.DateTimeField(auto_now=True, db_index=True)),
                ("text", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("eid", models.CharField(max_length=64, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="room",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="chat.ChatRoom"
            ),
        ),
    ]
