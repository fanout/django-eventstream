import re
import codecs
import asyncio
from django_eventstream.event import Event


class BaseSSEClient:
    """
    This class provides a way to properly consume Server-Sent Events (SSE) in a synchronous way.
    It also provide a default headers to be used in the request to ensure that the response will be in the correct format.
    """

    end_of_field = re.compile(r"\r\n\r\n|\r\r|\n\n")

    def __init__(self):
        self.response = None
        self.default_headers = {
            "Accept": "text/event-stream",
            "Content-Type": "text/event-stream",
        }

    def sse_stream(self, response=None):
        if self.response is None:
            raise ValueError("You must set a response before calling `sse_stream_sync`")
        if not getattr(self.response, "streaming", False):
            raise ValueError("The response is not streaming")

        encoding = getattr(self.response, "encoding", None) or "utf-8"
        decoder = codecs.getincrementaldecoder(encoding)(errors="replace")

        async def async_event_generator():
            buf = ""
            async for chunk in self.response.streaming_content:
                buf += decoder.decode(chunk)
                while re.search(self.end_of_field, buf):
                    event_string, buf = re.split(self.end_of_field, buf, maxsplit=1)
                    event = Event.parse(event_string)
                    yield event

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        generator = async_event_generator()
        try:
            while True:
                event = loop.run_until_complete(generator.__anext__())
                yield event
        except StopAsyncIteration:
            pass
        finally:
            loop.close()
