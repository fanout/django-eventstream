import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
	readme = f.read()

setup(
name='django-eventstream',
version='1.1.0',
description='Django EventStream library',
long_description=readme,
author='Justin Karneges',
author_email='justin@fanout.io',
url='https://github.com/fanout/django-eventstream',
license='MIT',
zip_safe=False,
packages=['django_eventstream', 'django_eventstream.migrations', 'django_eventstream.management', 'django_eventstream.management.commands'],
package_data={'django_eventstream': ['static/django_eventstream/*']},
install_requires=['django_grip>=1.7,<3', 'Werkzeug>=0.12,<1', 'six>=1.10,<2'],
classifiers=[
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License'
]
)
