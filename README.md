# Django EventStream

EventStream provides API endpoints for your Django application that can push data to connected clients. Data is sent using the Server-Sent Events protocol (SSE), in which data is streamed over a never-ending HTTP response.

For example, you could create an endpoint, `/events/`, that a client could connect to with a GET request:

```http
GET /events/ HTTP/1.1
Host: api.example.com
Accept: text/event-stream
```

The client would receive a streaming HTTP response with content looking like this:

```http
HTTP/1.1 200 OK
Transfer-Encoding: chunked
Connection: Transfer-Encoding
Content-Type: text/event-stream

event: message
data: {"foo": "bar"}

event: message
data: {"bar": "baz"}

...
```

Features:

* Easy to consume from browsers or native applications.
* Reliable delivery. Events can be persisted to your database, so clients can recover if they get disconnected.
* Per-user channel permissions.

## Requirements

* Django 5.0

## Setup

First, install this module and the daphne module:

```sh
pip install django-eventstream daphne
```

Add the `daphne` and `django_eventstream` apps to `settings.py`:

```py
INSTALLED_APPS = [
    ...
    "daphne",
    "django_eventstream",
]
```

Add an endpoint in `urls.py`:

```py
from django.urls import path, include
import django_eventstream

urlpatterns = [
    ...
    path("events/", include(django_eventstream.urls), {"channels": ["test"]}),
]
```

That's it! If you run `python manage.py runserver`, clients will be able to connect to the `/events/` endpoint and get a stream.

To send data to clients, call `send_event`:

```py
from django_eventstream import send_event

send_event("test", "message", {"text": "hello world"})
```

The first argument is the channel to send on, the second is the event type, and the third is the event data. The data will be JSON-encoded using `DjangoJSONEncoder`.

Note: in a basic setup, `send_event` must be called from within the server process (e.g. called from a view). It won't work if called from a separate process, such as from the shell or a management command.

### Deploying

After following the instructions in the previous section, you'll be able to develop and run locally using `runserver`. However, you should not use `runserver` when deploying, and instead launch an ASGI server such as Daphne, e.g.:

```sh
daphne your_project.asgi:application
```

See [How to deploy with ASGI](https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/).

WSGI mode can work too, but only in combination with a GRIP proxy. See [Multiple instances and scaling](#multiple-instances-and-scaling).

### Multiple instances and scaling

If you need to run multiple instances of your Django app for high availability or scalability, or need to send events from management commands, then you can introduce a GRIP proxy such as [Pushpin](https://pushpin.org) or [Fastly Fanout](https://developer.fastly.com/learning/concepts/real-time-messaging/fanout/) into your architecture. Otherwise, events originating from an instance will only be delivered to clients connected to that instance.

For example, to use Pushpin with your app, you need to do three things:

1. In your `settings.py`, add the `GripMiddleware` and set `GRIP_URL` to reference Pushpin's private control port:

```py
MIDDLEWARE = [
    "django_grip.GripMiddleware",
    ...
]
```

```py
GRIP_URL = 'http://localhost:5561'
```

The middleware is part of [django-grip](https://github.com/fanout/django-grip), which should have been pulled in automatically as a dependency of this module.

2. Configure Pushpin to route requests to your app, by adding something like this to Pushpin's `routes` file (usually `/etc/pushpin/routes`):

```
* localhost:8000 # Replace `localhost:8000` with your app's URL and port
```

3. Configure your consuming clients to connect to the Pushpin port (by default this is port 7999). Pushpin will forward requests to your app and handle streaming connections on its behalf.

If you would normally use a load balancer in front of your app, it should be configured to forward requests to Pushpin instead of your app. For example, if you are using Nginx you could have configuration similar to:

```
location /api/ {
    proxy_pass http://localhost:7999
}
```

The `location` block above will pass all requests coming on `/api/` to Pushpin.

## Event storage

By default, events aren't persisted anywhere, so if clients get disconnected or if your server fails to send data, then clients can miss messages. For reliable delivery, you'll want to enable event storage.

First, set up the database tables:

```sh
python manage.py migrate
```

Then, set a storage class in `settings.py`:

```py
EVENTSTREAM_STORAGE_CLASS = 'django_eventstream.storage.DjangoModelStorage'
```

That's all you need to do. When storage is enabled, events are written to the database before they are published, and they persist for 24 hours. If clients get disconnected, intermediate proxies go down, or your own server goes down or crashes at any time, even mid-publish, the stream will automatically be repaired.

To enable storage selectively by channel, implement a channel manager and override `is_channel_reliable`.

## Receiving in the browser

Include client libraries on the frontend:

```html
<script src="{% static 'django_eventstream/eventsource.min.js' %}"></script>
<script src="{% static 'django_eventstream/reconnecting-eventsource.js' %}"></script>
```

Listen for data:

```js
var es = new ReconnectingEventSource('/events/');

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

Note: OAuth may not work with the `AuthMiddlewareStack` from Django Channels. See [this token middleware](https://gist.github.com/rluts/22e05ed8f53f97bdd02eafdf38f3d60a).

## Routes and channel selection

The channels the client listens to are specified using Django view keyword arguments on the routes. Alternatively, if no keyword arguments are specified, then the client can select the channels on its own by providing one or more `channel` query parameters in the HTTP request.

Examples:

```py
# specify fixed list of channels
path('foo/events/', include(django_eventstream.urls), {'channels': ['foo']})

# specify a list of dynamic channels using formatting based on view keywords
path('objects/<obj_id>/events/', include(django_eventstream.urls),
    {'format-channels': ['object-{obj_id}']})

# client selects a single channel using a path component
path('events/<channel>/', include(django_eventstream.urls))

# client selects one or more channels using query parameters
path('events/', include(django_eventstream.urls))
```

Note that if view keywords or a channel path component are used, the client cannot use query parameters to select channels.

If even more advanced channel mapping is needed, implement a channel manager and override `get_channels_for_request`.

## Cross-Origin Resource Sharing (CORS) Headers

There are settings available to set response headers `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`, and `Access-Control-Allow-Headers`, which are `EVENTSTREAM_ALLOW_ORIGINS`, `EVENTSTREAM_ALLOW_CREDENTIALS`, and `EVENTSTREAM_ALLOW_HEADERS`, respectively.

Examples:

```py
EVENTSTREAM_ALLOW_ORIGINS = ['http://example.com', 'https://example.com']
EVENTSTREAM_ALLOW_CREDENTIALS = True
EVENTSTREAM_ALLOW_HEADERS = 'Authorization'
```

Note that `EVENTSTREAM_ALLOW_HEADERS` only takes a single string value and does not process a list.

If more advanced CORS capabilities are needed, see [django-cors-headers](https://github.com/adamchainz/django-cors-headers).
