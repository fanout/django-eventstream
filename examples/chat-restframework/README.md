# Chat

Simple web chat app using EventStream.

There is a public instance available here: [http://chat.fanoutapp.com](http://chat.fanoutapp.com).

There are [iOS](https://github.com/fanout/chat-demo-ios) and [Android](https://github.com/fanout/chat-demo-android) demo clients.

## Usage

Install dependencies, setup database, and create empty environment config:

```sh
virtualenv --python=python3 venv
. venv/bin/activate
pip install -r requirements.txt
touch .env
python manage.py migrate
```

Note: The `django_eventstream` library doesn't get installed and instead you need to install it with `pip install "../../[drf]"` to install the Django Rest Framework version of the library from local source.

Run the REST API server:

```sh
python manage.py runserver 0.0.0.0:8000
```

Next start into the chat-client directory and run the following commands:

```sh
python -m http.server 9000
```

This will start a simple web server for the chat client.

Open browser to http://localhost:9000/

Now let's try.

### Get past messages:

```http
GET /rooms/{room-id}/messages/
```

Params: (None)

Returns: JSON object, with a list of messages.

### Send message:

```http
POST /rooms/{room-id}/messages/
```

Params:

* `user={string}`: the name of the user sending the message
* `text={string}`: the content of the message
* `room={string}`: the room ID

Returns: JSON object of message

### Get events:

```http
GET /rooms/{room-id}/events/
```

Returns: SSE stream
