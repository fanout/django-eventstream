Install dependencies:

```sh
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```

Note: The `django_eventstream` library doesn't get installed and instead is loaded from within this repository by relative path.

GRIP configuration:

```sh
cat "GRIP_URL=http://api.fanout.io/realm/your-realm?iss=your-realm&key=base64:your-realm-key" > .env
```

Run ngrok:

```sh
ngrok http 8000
```

Run the server:

```sh
python manage.py runserver_ngrok
```
