import unittest
from unittest.mock import patch, Mock
from django.core.management import CommandError
from io import StringIO
from django_eventstream.management.commands.runserver_ngrok import Command


class TestRunserverNgrokCommand(unittest.TestCase):

    # @patch("requests.get")
    # @patch("django_grip.get_pubcontrol")
    # def test_setup_with_http_tunnel(self, mock_get_pubcontrol, mock_requests_get):
    #     # Mock the response from the ngrok API
    #     mock_response = Mock()
    #     mock_response.json.return_value = {
    #         "tunnels": [{"public_url": "http://abc123.ngrok.io", "proto": "http"}]
    #     }
    #     mock_requests_get.return_value = mock_response

    #     # Mock the pubcontrol client
    #     mock_pubcontrol = Mock()
    #     mock_pubcontrol.clients = ["dummy_client"]
    #     mock_get_pubcontrol.return_value = mock_pubcontrol

    #     command = Command(stdout=StringIO(), stderr=StringIO())
    #     command.setup()

    #     print("STDOUT:", command.stdout.getvalue())  # Debugging print
    #     print("STDERR:", command.stderr.getvalue())  # Debugging print

    #     self.assertIn(
    #         "Setting ngrok tunnel abc123.ngrok.io as GRIP origin",
    #         command.stdout.getvalue(),
    #     )

    # @patch("requests.get")
    # @patch("django_grip.get_pubcontrol")
    # def test_setup_with_https_tunnel(self, mock_get_pubcontrol, mock_requests_get):
    #     # Mock the response from the ngrok API
    #     mock_response = Mock()
    #     mock_response.json.return_value = {
    #         "tunnels": [{"public_url": "https://abc123.ngrok.io", "proto": "https"}]
    #     }
    #     mock_requests_get.return_value = mock_response

    #     # Mock the pubcontrol client
    #     mock_pubcontrol = Mock()
    #     mock_pubcontrol.clients = ["dummy_client"]
    #     mock_get_pubcontrol.return_value = mock_pubcontrol

    #     command = Command(stdout=StringIO(), stderr=StringIO())
    #     command.setup()

    #     self.assertIn(
    #         "Setting ngrok tunnel abc123.ngrok.io as GRIP origin",
    #         command.stdout.getvalue(),
    #     )

    #     mock_pubcontrol.set_origin.assert_called_once_with(
    #         host=None,
    #         port=None,
    #         ssl_host="abc123.ngrok.io",
    #         ssl_port=443,
    #         rewrite_host=True,
    #     )

    @patch("requests.get")
    @patch("django_grip.get_pubcontrol")
    def test_no_tunnels_found(self, mock_get_pubcontrol, mock_requests_get):
        # Mock the response from the ngrok API with no tunnels
        mock_response = Mock()
        mock_response.json.return_value = {"tunnels": []}
        mock_requests_get.return_value = mock_response

        # Mock the pubcontrol client
        mock_pubcontrol = Mock()
        mock_pubcontrol.clients = ["dummy_client"]
        mock_get_pubcontrol.return_value = mock_pubcontrol

        command = Command(stdout=StringIO(), stderr=StringIO())
        command.setup()

        self.assertIn("Error: no ngrok tunnels found", command.stderr.getvalue())

    @patch("requests.get")
    @patch("django_grip.get_pubcontrol")
    def test_no_grip_proxy_configured(self, mock_get_pubcontrol, mock_requests_get):
        # Mock the response from the ngrok API with a tunnel
        mock_response = Mock()
        mock_response.json.return_value = {
            "tunnels": [{"public_url": "http://abc123.ngrok.io", "proto": "http"}]
        }
        mock_requests_get.return_value = mock_response

        # Mock the pubcontrol client with no clients
        mock_pubcontrol = Mock()
        mock_pubcontrol.clients = []
        mock_get_pubcontrol.return_value = mock_pubcontrol

        command = Command(stdout=StringIO(), stderr=StringIO())
        command.setup()

        self.assertIn("Error: no GRIP proxy configured", command.stderr.getvalue())
