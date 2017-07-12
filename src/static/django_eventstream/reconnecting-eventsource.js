// MIT License:
//
// Copyright (C) 2017 Fanout, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to
// deal in the Software without restriction, including without limitation the
// rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
// sell copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
// IN THE SOFTWARE.

var ReconnectingEventSource = function (url, configuration) {
	this._eventSource = null;
	this._lastEventId = null;
	this._timer = null;
	this._listeners = {};

	this.url = url;
	this.readyState = 0;
	this.retry_time = 3000;

	if (configuration != undefined && configuration.lastEventId) {
		this._lastEventId = configuration.lastEventId;
		delete configuration['lastEventId'];
	}

	this._configuration = configuration;

	var self = this;
	this._onevent_wrapped = function (event) { self._onevent(event); };

	this._start();
};

ReconnectingEventSource.prototype._start = function () {
	var url = this.url;

	if (this._lastEventId) {
		if (url.indexOf('?') === -1) {
			url += '?';
		} else {
			url += '&';
		}
		url += 'lastEventId=' + encodeURIComponent(this._lastEventId);
	}

	this._eventSource = new EventSource(url, this._configuration);

	var self = this;

	this._eventSource.onopen = function (event) { self._onopen(event); };
	this._eventSource.onerror = function (event) { self._onerror(event); };

	// apply listen types
	for (var type in this._listeners) {
		this._eventSource.addEventListener(type, this._onevent_wrapped);
	}
};

ReconnectingEventSource.prototype._onopen = function (event) {
	if (this.readyState == 0) {
		this.readyState = 1;
		this.onopen(event);
	}
};

ReconnectingEventSource.prototype._onerror = function (event) {
	if (this.readyState == 1) {
		this.readyState = 0;
		this.onerror(event);
	}

	if (this._eventSource) {
		if(this._eventSource.readyState == 2) {
			// reconnect with new object
			this._eventSource.close();
			this._eventSource = null;

			var self = this;
			this._timer = setTimeout(function () {
				self._start();
			}, this.retry_time);
		}
	}
};

ReconnectingEventSource.prototype._onevent = function (event) {
	if (event.lastEventId) {
		this._lastEventId = event.lastEventId;
	}

	var l = this._listeners[event.type];
	if (l != undefined) {
		// operate on a copy
		l = l.slice();
		for (var n = 0; n < l.length; n++) {
			l[n](event);
		}
	}

	if (event.type == 'message') {
		this.onmessage(event);
	}
};

ReconnectingEventSource.prototype.onopen = function (event) {
	// user may override
};

ReconnectingEventSource.prototype.onerror = function (event) {
	// user may override
};

ReconnectingEventSource.prototype.onmessage = function (event) {
	// user may override
};

ReconnectingEventSource.prototype.close = function () {
	if (this._timer) {
		clearTimeout(this._timer);
		this._timer = null;
	}

	if (this._eventSource) {
		this._eventSource.close();
		this._eventSource = null;
	}

	this.readyState = 2;
};

ReconnectingEventSource.prototype.addEventListener = function (type, callback) {
	var type = type.toString();
	var l = this._listeners[type];
	if (l == undefined) {
		l = [];
		this._listeners[type] = l;
		if (this._eventSource) {
			this._eventSource.addEventListener(type, this._onevent_wrapped);
		}
	}
	for (var n = 0; n < l.length; n++) {
		if (l[n] === callback) {
			return;
		}
	}
	l.push(callback);
};

ReconnectingEventSource.prototype.removeEventListener = function (type, callback) {
	var type = type.toString();
	var l = this._listeners[type];
	if (l == undefined) {
		return;
	}
	for (var n = 0; n < l.length; n++) {
		if (l[n] === callback) {
			l.splice(n, 1);
			break;
		}
	}
	if (l.length == 0) {
		delete this._listeners[type];
		if (this._eventSource) {
			this._eventSource.removeEventListener(type, this._onevent_wrapped);
		}
	}
};
