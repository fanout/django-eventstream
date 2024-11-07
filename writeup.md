# Events, as received by an HTTP client, lack the "id" attribute when we're using redis.

## Here's how to see the problem.

### It's fine without redis

* check out the master branch of django-eventstream (I'm using 93b3f4fa3b6d26028b0654a9721303fe0cb6d153).
* cd to `examples/time`
* `rm -vf db.sqlite3 ; python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt && ./.venv/bin/python manage.py migrate && ./.venv/bin/python manage.py runserver`
* in another window, do `curl http://localhost:8000/events/`

You will see output like this:

```
event: message
id: time:22
data: "2024-11-07T20:42:35.515320"

event: message
id: time:24
data: "2024-11-07T20:42:36.526287"
```

This is good: each event includes an "id".

### Now use redis:

* edit `examples/time/requirements.txt` by adding a line `redis==5.2.0`
* edit `examples/time/server/settings.py` by adding `EVENTSTREAM_REDIS = {'host': 'localhost', 'port': 6379, 'db': 0,}`
* ensure you actually have a redis server listening on 6379 :-)

* Restart the server from scratch: `rm -vf db.sqlite3 ; python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt && ./.venv/bin/python manage.py migrate && ./.venv/bin/python manage.py runserver`
* Restart the `curl` in the other window.

You'll see this:

```

event: message
data: "2024-11-07T20:46:26.419070"

event: message
data: "2024-11-07T20:46:26.684600"
```

There are two things wrong here:
* the `id:` lines are gone
* *two* events are showing up every second, as opposed to just one previously

I'm only addressing the first of those two problems.

## Now apply my fix

In prose:

* add `"pub_id": pub_id,` to `redis_message` in `eventstream.send_event`
* retreive it in `views.RedisListener.listen` by assigning `pub_id = event_data["pub_id"]` and then passing that to the `Event` constructor a few lines down: `e = Event(channel, event_type, data, id=pub_id)`

Restart the server and curl, and now you'll see e.g.

```
event: message
id: time:15
data: "2024-11-07T20:53:32.465675"

event: message
id: time:16
data: "2024-11-07T20:53:32.742764"

```

i.e., we're still getting two events per second, but at least they have `id:` lines.
