# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseBadRequest

def events(request):
	from .eventrequest import EventRequest
	from .eventstream import EventPermissionError, get_events
	from .utils import sse_error_response

	user = None
	if request.user.is_authenticated:
		user = request.user

	try:
		event_request = EventRequest(request)
		event_response = get_events(event_request, user=user)
		response = event_response.to_http_response(request)
	except EventRequest.ResumeNotAllowedError as e:
		response = HttpResponseBadRequest('Invalid request: %s.\n' % e.message)
	except EventRequest.GripError:
		response = sse_error_response(
			'internal-error',
			'Invalid internal request.')
	except EventRequest.Error as e:
		response = sse_error_response(
			'bad-request',
			'Invalid request: %s.' % e.message)
	except EventPermissionError as e:
		response = sse_error_response(
			'forbidden',
			e.message,
			{'channels': e.channels})

	response['Cache-Control'] = 'no-cache'
	response['Access-Control-Allow-Origin'] = request.META.get('HTTP_HOST')
	return response
