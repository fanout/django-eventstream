# Chat

Simple web chat app.

Server is a Django app (using Django-EventStream). Updates are sent over Fanout Cloud or Pushpin.

There is a public instance available here: [http://chat.fanoutapp.com](http://chat.fanoutapp.com).

There are [iOS](https://github.com/fanout/chat-demo-ios) and [Android](https://github.com/fanout/chat-demo-android) demo clients.

## Usage

Install dependencies and setup database:

```sh
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

The `django_eventstream` library doesn't get installed and instead is loaded from within this repository by relative path.

Note: default storage is sqlite.

### Running with Fanout Cloud

Create a `.env` file containing `GRIP_URL`:

```sh
GRIP_URL=https://api.fanout.io/realm/{realm-id}?iss={realm-id}&key=base64:{realm-key}
```

Be sure to replace `{realm-id}` and `{realm-key}` with the values from the Fanout control panel.

In a separate shell, run ngrok for local tunneling:

```sh
ngrok http 8000
```

Run a local instance of the project:

```sh
python manage.py runserver_ngrok
```

The `runserver_ngrok` command automatically sets the ngrok tunnel as your Fanout Cloud domain's Origin Server.

Then open up two browser windows to your Fanout Cloud domain (e.g. https://{realm-id}.fanoutcdn.com/). Requests made to Fanout Cloud should be routed through ngrok to the local instance.

### Running with Pushpin

Create a `.env` file containing `GRIP_URL`:

```sh
GRIP_URL=http://localhost:5561
```

Run Pushpin:

```sh
pushpin --route="* localhost:8000"
```

Run the server:

```sh
python manage.py runserver
```

Then open up two browser windows to [http://localhost:7999/](http://localhost:7999/).

## API

### Get past messages:

```http
GET /rooms/{room-id}/messages/
```

Params: (None)

Returns: JSON object, with fields:

* `messages`: list of the most recent messages, in time descending order
* `last-event-id`: last event ID (use this when listening for events)

### Send message:

```http
POST /rooms/{room-id}/messages/
```

Params:

* `from={string}`: the name of the user sending the message
* `text={string}`: the content of the message

Returns: JSON object of message

### Get events:

```http
GET /events/
```

Params:

* `channel`: events channel to listen to, using the form `room-{room-id}`. can be specified more than once to listen to events of multiple rooms
* `lastEventId`: event ID to start reading from (optional)

Returns: SSE stream
