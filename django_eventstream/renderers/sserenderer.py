from rest_framework.renderers import BaseRenderer
from django.conf import settings
from django_eventstream.utils import get_cors_from_settings

class SSEEventRenderer(BaseRenderer):
    """
    A renderer to stream events to the client in text/event-stream format and add the right CORS headers.
    """
    media_type = 'text/event-stream'
    Access_Control_Allow_Origin = get_cors_from_settings()
    Cache_Control = "no-cache"
    X_Accel_Buffering = "no"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Ensure data is a byte string
        if isinstance(data, str):
            data = data.encode(self.charset)
        return data