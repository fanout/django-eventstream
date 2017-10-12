# Django EventStream

Django EventStream provides an API endpoint for your Django application that can push data to connected clients. It relies on Pushpin or Fanout Cloud to manage the connections. Data is sent using the Server-Sent Events protocol (SSE), in which data is streamed over a never-ending HTTP response.

For example, you could create an endpoint, `/events/`, that a client could connect to with a GET request:

```http
GET /events/?channel=test HTTP/1.1
Host: api.example.com
Accept: text/event-stream
```

The client would receive a streaming HTTP response with content looking like this:

```http
HTTP/1.1 200 OK
Transfer-Encoding: chunked
Connection: Transfer-Encoding
Content-Type: text/event-stream

event: stream-open
data:

event: message
id: test:1
data: {"foo": "bar"}

event: message
id: test:2
data: {"bar": "baz"}
```

Features:

* Easy to consume from browsers or native applications.
* Highly reliable. Events can be persisted to your database, so clients can recover if they get disconnected.
* Set per-user channel permissions.
* Clean API contract that could be exposed to third parties if desired.

## Setup

Install this module:

```sh
pip install django-eventstream
```

Then a few changes need to be made to `settings.py`.

Add the `GripMiddleware`:

```py
MIDDLEWARE = [
    'django_grip.GripMiddleware',
    ...
]
```

Set `GRIP_URL` with your Pushpin or Fanout Cloud settings:

```py
# pushpin
GRIP_URL = 'http://localhost:5561'
```

```py
# fanout cloud
GRIP_URL = 'http://api.fanout.io/realm/your-realm?iss=your-realm&key=base64:your-realm-key'
```

Add the `django_eventstream` app:

```py
INSTALLED_APPS = [
    ...
    'django_eventstream',
]
```

Add an endpoint in `urls.py`:

```py
from django.conf.urls import url, include
import django_eventstream

urlpatterns = [
    ...
    url(r'^events/', include(django_eventstream.urls)),
]
```

That's it! Clients can now connect to the `/events/` endpoint and get a stream.

To send data to clients, call `send_event`:

```py
from django_eventstream import send_event

send_event('test', 'message', {'text': 'hello world'})
```

The first argument is the channel to send on, the second is the event type, and the third is the event data. The data will be JSON-encoded using `DjangoJSONEncoder`.

## Local development

If you're developing locally and want to test with Fanout Cloud, we recommend using [ngrok](https://ngrok.com/) to register a public host that routes to your local instance.

As a convenience, this module comes with a Django command `runserver_ngrok` that acts like `runserver` except it additionally configures your Fanout Cloud realm to use a detected tunnel as the origin server.

From a separate shell, run `ngrok`:

```sh
ngrok http 8000
```

Then run the `runserver_ngrok` command:

```sh
python manage.py runserver_ngrok
```

You should see output like this:

```
Setting ngrok tunnel 4f91f84e.ngrok.io as GRIP origin
...
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Note that it may take a minute or so for the changes to take effect.

## Event storage

By default, events aren't persisted anywhere, so if clients get disconnected or if your server fails to publish data to Pushpin or Fanout Cloud, then clients can miss messages. For reliable delivery, you'll want to enable event storage.

First, set up the database tables:

```sh
python manage.py migrate
```

Then, set a storage class in `settings.py`:

```py
EVENTSTREAM_STORAGE_CLASS = 'django_eventstream.storage.DjangoModelStorage'
```

That's all you need to do. When storage is enabled, events are written to the database before they are published, and they persist for 24 hours. If clients get disconnected, Pushpin or Fanout Cloud goes down, or your own server goes down or crashes at any time, even mid-publish, the stream will automatically be repaired.

To enable storage selectively by channel, implement a channel manager and override `is_channel_reliable`.

## Receiving in the browser

Include client libraries on the frontend:

```html
<script src="{% static 'django_eventstream/eventsource.min.js' %}"></script>
<script src="{% static 'django_eventstream/reconnecting-eventsource.js' %}"></script>
```

Listen for data:

```js
var es = new ReconnectingEventSource('/events/?channel=test');

es.addEventListener('message', function (e) {
    console.log(e.data);
}, false);

es.addEventListener('stream-reset', function (e) {
    // ... client fell behind, reinitialize ...
}, false);
```

## Authorization

Declare a channel manager class with your authorization logic:

```py
from django_eventstream.channelmanager import DefaultChannelManager

class MyChannelManager(DefaultChannelManager):
    def can_read_channel(self, user, channel):
        # require auth for prefixed channels
        if channel.startswith('_') and user is None:
            return False
        return True
```

Configure `settings.py` to use it:

```py
EVENTSTREAM_CHANNELMANAGER_CLASS = 'myapp.channelmanager.MyChannelManager'
```

Whenever permissions change, call `channel_permission_changed`. This will cause clients to be disconnected if they lost permission to the channel.

```py
from django_eventstream import channel_permission_changed

channel_permission_changed(user, '_mychannel')
```

## Selecting channels

By default, the client selects the channels to listen to by providing one or more `channel` query parameters in the HTTP request. Alternatively, it is possible to use Django view keyword arguments to select the channels. Examples:

```py
# client selects the channels using query parameters:
url(r'^events/', include(django_eventstream.urls))

# client selects a single channel using a path component
url(r'^events/(?P<channel>\w+)/', include(django_eventstream.urls))

# server selects the channels
url(r'^foo/events/', include(django_eventstream.urls), {'channels':['foo']})

# server selects the channels using formatting based on the view keywords
url(r'^objects/(?P<obj_id>\w+)/events/', include(django_eventstream.urls),
    {'format-channels':['object-{obj_id}']})
```

Note that if view keywords are used, the client cannot use query parameters to select channels.

If even more advanced channel mapping is needed, implement a channel manager and override `get_channels_for_request`.
