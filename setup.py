import os
import sys
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
	readme = f.read()

install_requires = []

if sys.version_info >= (3,5):
	install_requires.append('channels>=2.1.2')

install_requires.extend(['PyJWT>=1.5,<2', 'gripcontrol>=3.1.0,<4', 'django_grip>=2.0.0,<3', 'Werkzeug>=0.12,<1', 'six>=1.10,<2'])

setup(
name='django-eventstream',
version='2.4.0',
description='Server-Sent Events for Django',
long_description=readme,
author='Justin Karneges',
author_email='justin@fanout.io',
url='https://github.com/fanout/django-eventstream',
license='MIT',
zip_safe=False,
packages=['django_eventstream', 'django_eventstream.migrations', 'django_eventstream.management', 'django_eventstream.management.commands'],
package_data={'django_eventstream': ['static/django_eventstream/*']},
install_requires=install_requires,
tests_require=['Django'],
test_suite='tests.runtests.runtests',
classifiers=[
	'Development Status :: 4 - Beta',
	'Topic :: Utilities',
	'License :: OSI Approved :: MIT License',
	'Programming Language :: Python',
	'Programming Language :: Python :: 2',
	'Programming Language :: Python :: 3',
	'Framework :: Django',
]
)
