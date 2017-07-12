# Django EventStream

Reliable, multi-channel Server-Sent Events for Django, using Pushpin or Fanout Cloud.

## Setup

Add the app to settings.py:

```py
INSTALLED_APPS = [
    ...
    'django_eventstream',
]
```

Set up the database:

```sh
python manage.py migrate
```

Set up an endpoint in urls.py:

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

Declare authorizer class:

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
