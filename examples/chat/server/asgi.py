"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import sys

filepath = os.path.abspath(__file__)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(filepath))))
)

import dotenv

dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(filepath)), ".env"))

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

application = get_asgi_application()
