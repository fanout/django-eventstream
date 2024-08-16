import re
import codecs
from django_eventstream.event import Event


class BaseSSEClient:
    end_of_field = re.compile(r"\r\n\r\n|\r\r|\n\n")

    def __init__(self, response=None):
        self.response = response

    def set_response(self, response):
        self.response = response

    async def sse_stream(self):
        if not self.response:
            raise ValueError("You must set a response before calling `sse_stream`")
        if not getattr(self.response, "streaming", False):
            raise ValueError("The response is not streaming")

        # Utilisation de l'encodage par défaut si non disponible
        encoding = getattr(self.response, "encoding", None) or "utf-8"
        decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
        buf = ""

        async for chunk in self.response.streaming_content:
            buf += decoder.decode(chunk)
            while re.search(self.end_of_field, buf):
                (event_string, buf) = re.split(self.end_of_field, buf, maxsplit=1)
                event = Event.parse(event_string)
                yield event
