import json
import threading
import importlib
import six
from django.conf import settings
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from gripcontrol import HttpStreamFormat

try:
    from urllib import quote
    from urlparse import urlparse
except ImportError:
    from urllib.parse import quote, urlparse

tlocal = threading.local()


# return dict of (channel, last-id)
def parse_last_event_id(s):
    out = {}
    parts = s.split(",")
    for part in parts:
        channel, last_id = part.split(":")
        out[channel] = last_id
    return out


def make_id(ids):
    id_parts = []
    for channel, id in six.iteritems(ids):
        enc_channel = quote(channel)
        id_parts.append("%s:%s" % (enc_channel, id))
    return ",".join(id_parts)


def build_id_escape(s):
    out = ""
    for c in s:
        if c == "%":
            out += "%%"
        else:
            out += c
    return out


def sse_encode_event(event_type, data, event_id=None, escape=False, json_encode=False):
    if json_encode:
        data = json.dumps(data, cls=DjangoJSONEncoder)
    if escape:
        event_type = build_id_escape(event_type)
        data = build_id_escape(data)
    out = "event: %s\n" % event_type
    if event_id:
        out += "id: %s\n" % event_id
    if "\n" in data:
        # Handle multi-line data
        for line in data.split("\n"):
            out += "data: %s\n" % line
        out += "\n"  # At the end pop an additional new line to cap off the data.
    else:
        out += "data: %s\n\n" % data
    return out


def sse_encode_error(condition, text, extra=None):
    if extra is None:
        extra = {}
    data = {"condition": condition, "text": text}
    for k, v in six.iteritems(extra):
        data[k] = v
    return sse_encode_event("stream-error", data, event_id="error", json_encode=True)


def sse_error_response(condition, text, extra=None):
    return HttpResponse(
        sse_encode_error(condition, text, extra=extra), content_type="text/event-stream"
    )


def publish_event(
    channel, event_type, data, pub_id, pub_prev_id, skip_user_ids=None, **publish_kwargs
):
    from django_grip import publish

    if skip_user_ids is None:
        skip_user_ids = []

    content_filters = []
    if pub_id:
        event_id = "%I"
        content_filters.append("build-id")
    else:
        event_id = None
    content = sse_encode_event(event_type, data, event_id=event_id, escape=bool(pub_id))
    meta = {}
    if skip_user_ids:
        meta["skip_users"] = ",".join(skip_user_ids)
    publish(
        "events-%s" % quote(channel),
        HttpStreamFormat(content, content_filters=content_filters),
        id=pub_id,
        prev_id=pub_prev_id,
        meta=meta,
        **publish_kwargs,
    )


def publish_kick(user_id, channel):
    from django_grip import publish

    msg = "Permission denied to channels: %s" % channel
    data = {"condition": "forbidden", "text": msg, "channels": [channel]}
    content = sse_encode_event("stream-error", data, event_id="error")
    meta = {"require_sub": "events-%s" % channel}
    publish("user-%s" % user_id, HttpStreamFormat(content), id="kick-1", meta=meta)
    publish(
        "user-%s" % user_id,
        HttpStreamFormat(close=True),
        id="kick-2",
        prev_id="kick-1",
        meta=meta,
    )


def load_class(name):
    at = name.rfind(".")
    if at == -1:
        raise ValueError("class name contains no '.'")
    module_name = name[0:at]
    class_name = name[at + 1 :]
    return getattr(importlib.import_module(module_name), class_name)()


# load and keep in thread local storage
def get_class(name):
    if not hasattr(tlocal, "loaded"):
        tlocal.loaded = {}
    c = tlocal.loaded.get(name)
    if c is None:
        c = load_class(name)
        tlocal.loaded[name] = c
    return c


def get_class_from_setting(setting_name, default=None):
    if hasattr(settings, setting_name):
        return get_class(getattr(settings, setting_name))
    elif default:
        return get_class(default)
    else:
        return None


def get_storage():
    return get_class_from_setting("EVENTSTREAM_STORAGE_CLASS")


def get_channelmanager():
    return get_class_from_setting(
        "EVENTSTREAM_CHANNELMANAGER_CLASS",
        "django_eventstream.channelmanager.DefaultChannelManager",
    )


def add_default_headers(headers, request):
    headers["Cache-Control"] = "no-cache"
    headers["X-Accel-Buffering"] = "no"
    augment_cors_headers(headers, request)


def find_related_origin(request, cors_origins: list):
    """
    Find a related origin from a list of CORS (Cross-Origin Resource Sharing) origins
    based on the request's absolute URI.

    Args:
        request (HttpRequest): The HTTP request object.
        cors_origins (list): A list of CORS origins.

    Returns:
        str: The related origin if found, otherwise an empty string.

    Example:
        Consider a request with the absolute URI 'https://example.com/some-path/' and
        CORS origins ['http://example.com', 'https://example.com', 'https://sub.example.com'].
        Calling find_related_origin(request, cors_origins) will return 'https://example.com'
        as it matches the scheme and netloc of the request's URI.

    """
    origins = [urlparse(o) for o in cors_origins]
    url = urlparse(request.build_absolute_uri())
    for origin in origins:
        if origin.scheme == url.scheme and origin.netloc == url.netloc:
            return f"{origin.scheme}://{origin.netloc}"
    return ""


def augment_cors_headers(headers, request):
    cors_origin = getattr(settings, "EVENTSTREAM_ALLOW_ORIGIN", None)
    if not cors_origin:
        cors_origin = getattr(settings, "EVENTSTREAM_ALLOW_ORIGINS", "")

    if cors_origin:
        if isinstance(cors_origin, str):
            headers["Access-Control-Allow-Origin"] = cors_origin
        elif isinstance(cors_origin, list):
            origin = find_related_origin(request=request, cors_origins=cors_origin)
            if origin:
                headers["Access-Control-Allow-Origin"] = origin
        else:
            raise TypeError("settings.EVENTSTREAM_ALLOW_ORIGIN should be str or list")

    allow_credentials = getattr(settings, "EVENTSTREAM_ALLOW_CREDENTIALS", False)

    if allow_credentials:
        headers["Access-Control-Allow-Credentials"] = "true"

    allow_headers = getattr(settings, "EVENTSTREAM_ALLOW_HEADERS", "")

    if allow_headers:
        headers["Access-Control-Allow-Headers"] = allow_headers
