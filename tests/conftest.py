import django
from django.core.management.commands.makemigrations import Command as MakeMigrations
from django.core.management.commands.migrate import Command as Migrate
from django.core.management.commands.flush import Command as Flush


def pytest_configure(config):
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": "db.sqlite3",
                "TEST": {
                    "NAME": "db_test.sqlite3",
                },
            },
        },
        # EVENTSTREAM_REDIS = {
        #     "host": "localhost",
        #     "port": 6379,
        #     "db": 0,
        # },
        SITE_ID=1,
        SECRET_KEY="not very secret in tests",
        USE_I18N=True,
        STATIC_URL="/static/",
        ROOT_URLCONF="tests.urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {
                    "debug": True,  # We want template errors to raise,
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            },
        ],
        MIDDLEWARE=(
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ),
        INSTALLED_APPS=[
            "daphne",
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "rest_framework",
            "django_eventstream",
        ],
        ALLOWED_HOSTS=["testserver"],
        WSGI_APPLICATION="tests.wsgi.application",
        ASGI_APPLICATION="tests.asgi.application",
        PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",),
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
    )

    django.setup()
    Flush().run_from_argv(["python", "manage.py", "--noinput"])
    MakeMigrations().run_from_argv(["python", "manage.py"])
    Migrate().run_from_argv(["python", "manage.py"])
