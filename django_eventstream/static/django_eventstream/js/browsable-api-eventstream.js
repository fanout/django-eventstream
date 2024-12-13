function restoreKeepAliveStatus() {
    var savedStatus = localStorage.getItem('keepAliveStatus');

    if (savedStatus !== null) {
        var keepAliveCheckbox = document.querySelector('input[name="keepAliveCheckbox"]');
        keepAliveCheckbox.checked = (savedStatus === 'true');
        keepAliveDisplay();
    }
}

restoreKeepAliveStatus();

function startStream() {
    var uri = window.location.href;
    var baseUri = uri.split('?')[0];
    var queryString = uri.split('?')[1] || '';
    var channel = new URLSearchParams(queryString).get('channels');
    var cleanUri = channel ? `${baseUri}?channels=${channel}` : baseUri;
    var es = new ReconnectingEventSource(cleanUri);
    var element = document.getElementById('sse-stream');
    var clearButton = document.getElementById('clearMessages');

    element.style.fontFamily = 'Arial, sans-serif';
    element.style.overflowY = 'auto';
    element.style.border = '1px solid #d3d3d3';
    element.style.borderRadius = '5px';
    element.style.padding = '10px';

    clearButton.addEventListener('click', function() {
        element.innerHTML = '';
    });

    es.onopen = function () {
        if (element) {
            addMessage(element, 'Connected to the SSE Stream', '#228B22', '#E8F5E9');
        }
    };

    es.onerror = function () {
        if (element) {
            addMessage(element, 'Connection lost, reconnecting...', '#a30000', '#FFEBEE');
        }
    };

    function handleEvent(message_type, eventData) {
        var data = JSON.parse(eventData);
        data = JSON.stringify(data, null, 2);
        var numberOfLines = (data.match(/\n/g) || []).length;
        if (numberOfLines > 0) {
            data = `\n${data}`;
        }
        addMessage(element, `<strong>Event - ${message_type} :</strong> ${data}`, '#2C2C2C', '#ECEFF1');
    }

    if (messages_types) {
        messages_types = messages_types.replace(' ', '').split(',');
        messages_types.forEach(message_type => {
            es.addEventListener(message_type, function (e) {
                handleEvent(message_type, e.data);
            }, false);
        });
    } else {
        es.addEventListener('message', function (e) {
            handleEvent('message', e.data);
        }, false);
    }


    es.addEventListener('keep-alive', function (e) {
        addMessage(element, 'Keep alive event received', '#337ab7', '#E3F2FD', true);
    }, false);

    es.addEventListener('stream-error', function (e) {
        var data = JSON.parse(e.data);
        addMessage(element, `<strong>Error </strong>- ${data.text}`, '#a30000', '#FFEBEE');
    }, false);
}

function keepAliveDisplay() {
    var keepAliveCheckbox = document.querySelector('input[name="keepAliveCheckbox"]');
    var keepAliveMessages = document.querySelectorAll('.keep-alive-message');
    if (keepAliveCheckbox.checked) {
        keepAliveMessages.forEach(function(message) {
            message.classList.remove('fade-out');
            message.classList.add('fade-in');
            message.style.display = '';
            setTimeout(() => message.style.opacity = 1, 600);
        });
        return true;
    } else {
        keepAliveMessages.forEach(function(message) {
            message.classList.remove('fade-in');
            message.classList.add('fade-out');
            setTimeout(() => {
                message.style.display = 'none';
                message.style.opacity = 0;
            }, 600);
        });
        return false;
    }
}

function addMessage(container, text, textColor, backgroundColor, isKeepAlive) {
    var now = new Date();
    var timestamp = now.getHours() + ':' + now.getMinutes().toString().padStart(2, '0') + ':' + now.getSeconds().toString().padStart(2, '0');

    var msg = document.createElement('div');
    msg.innerHTML = `<span style="font-size: 0.8em; color: #555;">${timestamp}</span> | ${text}`;
    msg.style.color = textColor;
    msg.style.background = backgroundColor;
    msg.style.borderLeft = `5px solid ${textColor}`;
    msg.style.padding = '10px';
    msg.style.margin = '10px 0';
    msg.style.borderRadius = '5px';

    to_scroll = true

    if (isKeepAlive) {
        msg.classList.add('keep-alive-message');
    }

    to_scroll = keepAliveDisplay();
    container.appendChild(msg);
    if (to_scroll) {
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
    keepAliveDisplay();
}

document.querySelector('input[name="keepAliveCheckbox"]').addEventListener('change', function() {
    keepAliveDisplay();
    localStorage.setItem('keepAliveStatus', this.checked.toString());
});

startStream();
