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

Note: The `django_eventstream` library doesn't get installed and instead is loaded from within this repository by relative path.

Run:

```sh
python manage.py runserver
```

Open browser to http://localhost:8000/

### Running with Fanout Cloud

Set `GRIP_URL` in your `.env`:

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

Open browser to your Fanout Cloud domain (e.g. `https://{realm-id}.fanoutcdn.com/`). Requests made to Fanout Cloud should be routed through ngrok to the local instance.

### Running with Pushpin

Set `GRIP_URL` in your `.env`:

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

Open browser to http://localhost:7999/

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
GET /rooms/{room-id}/events/
```

Params:

* `lastEventId`: event ID to start reading from (optional)

Returns: SSE stream
