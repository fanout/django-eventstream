# Time example

Sends the current time over a stream.

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

At a shell, run `curl http://localhost:8000/events/`
