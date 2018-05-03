SECRET_KEY = 'django_tests_secret_key'

DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django_eventstream',
    'tests',
]
