import os
from six.moves.urllib_parse import urlparse
import requests
from django_grip import get_pubcontrol
from django.apps import apps
if apps.is_installed('django.contrib.staticfiles'):
	from django.contrib.staticfiles.management.commands import runserver
else:
	from django.core.management.commands import runserver


class Command(runserver.Command):
	help = 'Set ngrok tunnel as origin for GRIP service, then invoke runserver'

	def setup(self):
		host = None
		port = None
		ssl_host = None
		ssl_port = None

		resp = requests.get('http://localhost:4040/api/tunnels')
		tunnels = resp.json()['tunnels']
		for tunnel in tunnels:
			if tunnel['proto'] in ('http', 'https'):
				parsed = urlparse(tunnel['public_url'])
				if tunnel['proto'] == 'http':
					host = parsed.hostname
					port = parsed.port if parsed.port is not None else 80
				elif tunnel['proto'] == 'https':
					ssl_host = parsed.hostname
					ssl_port = parsed.port if parsed.port is not None else 443

		if host is None and ssl_host is None:
			self.stderr.write('Error: no ngrok tunnels found')
			return

		pub = get_pubcontrol()
		if len(pub.clients) == 0:
			self.stderr.write('Error: no GRIP proxy configured')
			return

		pub.set_origin(
			host=host,
			port=port,
			ssl_host=ssl_host,
			ssl_port=ssl_port,
			rewrite_host=True)

		self.stdout.write(
			'Setting ngrok tunnel %s as GRIP origin' % (host or ssl_host))

	def run(self, **options):
		# be sure to execute setup() only once, even if autoreload is used
		use_reloader = options['use_reloader']
		if not use_reloader or os.environ.get('RUN_MAIN') != 'true':
			self.setup()

		super(Command, self).run(**options)
