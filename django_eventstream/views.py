# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.http import HttpResponseBadRequest
from .utils import augment_cors_headers

def events(request, **kwargs):
	from .eventrequest import EventRequest
	from .eventstream import EventPermissionError, get_events
	from .utils import sse_error_response

	try:
		event_request = EventRequest(request, view_kwargs=kwargs)
		event_response = get_events(event_request)
		response = event_response.to_http_response(request)
	except EventRequest.ResumeNotAllowedError as e:
		response = HttpResponseBadRequest(
			'Invalid request: %s.\n' % str(e))
	except EventRequest.GripError as e:
		if request.grip.proxied:
			response = sse_error_response(
				'internal-error',
				'Invalid internal request.')
		else:
			response = sse_error_response(
				'bad-request',
				'Invalid request: %s.' % str(e))
	except EventRequest.Error as e:
		response = sse_error_response(
			'bad-request',
			'Invalid request: %s.' % str(e))
	except EventPermissionError as e:
		response = sse_error_response(
			'forbidden',
			str(e),
			{'channels': e.channels})

	response['Cache-Control'] = 'no-cache'

	augment_cors_headers(response)

	return response
