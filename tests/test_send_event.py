from django.test import Client
from django.urls import reverse
from django_eventstream import send_event


def send_event_internal(event_data):
    """This method is sending event by calling a view that sends an event. Because the view is in the main Django
    process it sends (internally) the event."""

    client = Client()
    # Préparez les données à envoyer
    event_data = event_data or "test-event"
    data = {"event_data": event_data}

    # Envoie la requête GET avec les données en tant que paramètres de requête
    response = client.get(reverse("send-event"), data=data)

    assert response.status_code == 200

    return response


def send_event_external(event_data):
    """ """
    event_data = event_data or "test-event"
    send_event("test", "message", event_data)
