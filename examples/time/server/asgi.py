"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import sys

filepath = os.path.abspath(__file__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(filepath)))))

import dotenv
dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(filepath)), '.env'))

import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
django.setup()
application = get_default_application()
