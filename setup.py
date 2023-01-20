import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
	readme = f.read()

install_requires = []

install_requires.extend(['PyJWT>=1.5,<3', 'gripcontrol>=4.0,<5', 'django_grip>=3.0,<4', 'six>=1.10,<2'])

setup(
name='django-eventstream',
version='4.5.1',
description='Server-Sent Events for Django',
long_description=readme,
long_description_content_type='text/markdown',
author='Justin Karneges',
author_email='justin@fanout.io',
url='https://github.com/fanout/django-eventstream',
license='MIT',
zip_safe=False,
packages=['django_eventstream', 'django_eventstream.migrations', 'django_eventstream.management', 'django_eventstream.management.commands'],
package_data={'django_eventstream': ['static/django_eventstream/*']},
install_requires=install_requires,
tests_require=['Django>=2.0'],
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
