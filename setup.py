import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
	readme = f.read()

setup(
name='django-eventstream',
version='0.2.1',
description='Django EventStream library',
long_description=readme,
author='Justin Karneges',
author_email='justin@karneges.com',
url='https://github.com/fanout/django-eventstream',
license='MIT',
zip_safe=False,
packages=['django_eventstream', 'django_eventstream.migrations'],
package_data={'django_eventstream': ['static/django_eventstream/*']},
install_requires=['django_grip>=1.7,<3', 'Werkzeug>=0.12,<1'],
classifiers=[
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License'
]
)
