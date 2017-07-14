# Django EventStream

Django EventStream provides an API endpoint for your Django application that can push data instantly to clients. It relies on Pushpin or Fanout Cloud as a proxy for managing the client connections. Data is sent using the Server-Sent Events protocol, which is an HTTP-based protocol where data is streamed out using a never-ending HTTP response.

For example, you could set up an endpoint on path `/events/` that a client could connect to with a GET request:

```http
GET /events/?channel=test HTTP/1.1
Host: api.example.com
Accept: text/event-stream
```

The client would receive a streaming HTTP response looking like this:

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
* Highly reliable. Events are persisted to your database, so clients can recover if they get disconnected.
* Reasonably clean API endpoint contract that can be exposed to third parties.

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

Set `GRIP_PROXES` with your Pushpin or Fanout Cloud settings:

```py
GRIP_PROXIES = [{
    'key': b64decode('your-realm-key'),
    'control_uri': 'http://api.fanout.io/realm/your-realm',
    'control_iss': 'your-realm'
}]
```

Add the `django_eventstream` app:

```py
INSTALLED_APPS = [
    ...
    'django_eventstream',
]
```

Set up the database tables:

```sh
python manage.py migrate
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

Include client libraries on the frontend:

```html
<script src="{% static 'django_eventstream/eventsource.min.js' %}"></script>
<script src="{% static 'django_eventstream/reconnecting-eventsource.js' %}"></script>
```

## Usage

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

Send data:

```py
from django_eventstream import send_event

send_event('test', 'message', {'text': 'hello world'})
```

## Authorization

Declare authorizer class with your authorization logic:

```py
class MyAuthorizer(object):
    def can_read_channel(self, user, channel):
        # require auth for prefixed channels
        if channel.startswith('_') and user is None:
            return False
        return True
```

Configure settings.py to use it:

```py
EVENTSTREAM_AUTHORIZER_CLASS = 'myapp.authorizer.MyAuthorizer'
```

Whenever permissions change, call `channel_permission_changed`. This will cause clients to be disconnected if they lost permission to the channel.

```py
from django_eventstream import channel_permission_changed

channel_permission_changed(user, '_mychannel')
