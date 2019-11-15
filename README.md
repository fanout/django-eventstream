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
* Highly reliable. Events can be persisted to your database, so clients can recover if they get disconnected.
* Set per-user channel permissions.
* Clean API contract that could be exposed to third parties if desired.

## Requirements

This library requires one or both of:

* [Django Channels 2](https://channels.readthedocs.io/en/latest/) (for asynchronous connection handling, needs Python 3.5+).
* A GRIP-compatible proxy such as [Pushpin](https://pushpin.org) or [Fanout Cloud](https://fanout.io) (will work with any Python version including 2.x).

## Setup

If you're using Python 3.5 or later, we recommend setting up your project with Channels as this will give you the most flexibility, including being able to run standalone or with `runserver`. You can always [add Pushpin/Fanout](#multiple-instances-and-scaling) afterwards for high availability or scale.

For Python versions earlier than 3.5, see [Setup without Channels](#setup-without-channels).

### Setup with Channels

First, install this module:

```sh
pip install django-eventstream
```

Add the `channels` and `django_eventstream` apps to your `settings.py`:

```py
INSTALLED_APPS = [
    ...
    'channels',
    'django_eventstream',
]
```

Add the `GripMiddleware`:

```py
MIDDLEWARE = [
    'django_grip.GripMiddleware',
    ...
]
```

Channels introduces an entirely separate routing system for handling async connections. Routes are declared in `routing.py` files instead of `urls.py` files, and you declare an [ASGI](https://channels.readthedocs.io/en/latest/asgi.html) application instead of (or in addition to) a WSGI application.

Create a `routing.py` file in one of your Django app dirs, with an endpoint declared:

```py
from django.conf.urls import url
from channels.routing import URLRouter
from channels.http import AsgiHandler
from channels.auth import AuthMiddlewareStack
import django_eventstream

urlpatterns = [
    url(r'^events/', AuthMiddlewareStack(
        URLRouter(django_eventstream.routing.urlpatterns)
    ), {'channels': ['test']}),
    url(r'', AsgiHandler),
]
```

Then, ensure you have a master `routing.py` file in your project dir (next to `settings.py`) that routes to the app's `routing` module from the previous step:

```py
from channels.routing import ProtocolTypeRouter, URLRouter
import your_app.routing

application = ProtocolTypeRouter({
    'http': URLRouter(your_app.routing.urlpatterns),
})
```

Set `ASGI_APPLICATION` in your `settings.py` file to your project's `routing` module:

```py
ASGI_APPLICATION = 'your_project.routing.application'
```

Finally, create an `asgi.py` file in your project dir. It's similar to your `wsgi.py`:

```py
"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")
django.setup()
application = get_default_application()
```

For more information about setting up Channels in general, see the [Channels Documentation](http://channels.readthedocs.io/en/latest/tutorial/part_1.html#integrate-the-channels-library).

That's it! If you run `python manage.py runserver`, clients will be able to connect to the `/events/` endpoint and get a stream.

To send data to clients, call `send_event`:

```py
from django_eventstream import send_event

send_event('test', 'message', {'text': 'hello world'})
```

The first argument is the channel to send on, the second is the event type, and the third is the event data. The data will be JSON-encoded using `DjangoJSONEncoder`.

### Deploying with Channels

After following the instructions in the previous section, you'll be able to develop and run locally using `runserver`. However, you should not use `runserver` when deploying, and instead launch an ASGI server such as Daphne, e.g.:

```sh
daphne your_project.asgi:application
```

See the [Channels Documentation](https://channels.readthedocs.io/en/latest/deploying.html) for information about deployment.

### Multiple instances and scaling

If you need to run multiple instances of your Django project for high availability, or need to push data from management commands, or need to be able to scale to a large number of connections, you can introduce a GRIP proxy layer (such as [Pushpin](https://pushpin.org) or [Fanout Cloud](https://fanout.io)) into your architecture.

In your `settings.py`, set `GRIP_URL` with your proxy settings:

```py
GRIP_URL = 'http://api.fanout.io/realm/your-realm?iss=your-realm&key=base64:your-realm-key'
```

Then configure the proxy to forward traffic to your project. E.g. with Fanout Cloud, set the `host:port` of your deployed project as your realm's Origin Server, and have clients connect to your realm's domain.

### Setup without Channels

It is possible to use this library with a GRIP proxy only, without setting up Channels. This can be useful if your Python version doesn't support Channels.

First, install this module:

```sh
pip install django-eventstream
```

A few changes need to be made to `settings.py`.

Add the `django_eventstream` app:

```py
INSTALLED_APPS = [
    ...
    'django_eventstream',
]
```

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

Add an endpoint in `urls.py`:

```py
from django.conf.urls import url, include
import django_eventstream

urlpatterns = [
    ...
    url(r'^events/', include(django_eventstream.urls), {'channels': ['test']}),
]
```

That's it! Clients can now connect to the `/events/` endpoint through the proxy and get a stream.

To send data to clients, call `send_event`:

```py
from django_eventstream import send_event

send_event('test', 'message', {'text': 'hello world'})
```

The first argument is the channel to send on, the second is the event type, and the third is the event data. The data will be JSON-encoded using `DjangoJSONEncoder`.

## Local development without Channels

If you're developing locally without Channels and want to test with Fanout Cloud, we recommend using [ngrok](https://ngrok.com/) to register a public host that routes to your local instance.

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

Now if you make client requests to your realm's domain (e.g. `{realm-id}.fanoutcdn.com`) they will be routed to your local instance.

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
url(r'^foo/events/', include(django_eventstream.urls), {'channels': ['foo']})

# specify a list of dynamic channels using formatting based on view keywords
url(r'^objects/(?P<obj_id>\w+)/events/', include(django_eventstream.urls),
    {'format-channels': ['object-{obj_id}']})

# client selects a single channel using a path component
url(r'^events/(?P<channel>\w+)/', include(django_eventstream.urls))

# client selects one or more channels using query parameters
url(r'^events/', include(django_eventstream.urls))
```

Note that if view keywords or a channel path component are used, the client cannot use query parameters to select channels.

If even more advanced channel mapping is needed, implement a channel manager and override `get_channels_for_request`.

## Cross-Origin Resource Sharing (CORS) Headers

There are two setting properties available to set `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials` which are `EVENTSTREAM_ALLOW_ORIGIN` and `EVENTSTREAM_ALLOW_CREDENTIALS`, respectively.

Examples:

```py
EVENTSTREAM_ALLOW_ORIGIN = 'your-website.com'
EVENTSTREAM_ALLOW_CREDENTIALS = True
```

Note that `EVENTSTREAM_ALLOW_ORIGIN` only takes a single string value and does not process a list.
