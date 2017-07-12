#!/usr/bin/env python

from setuptools import setup

setup(
name="django-eventstream",
version="0.1.0",
description="Django EventStream library",
author="Justin Karneges",
author_email="justin@karneges.com",
url="https://github.com/fanout/django-eventstream",
license="MIT",
package_dir={'django_eventstream': 'src'},
packages=['django_eventstream'],
install_requires=["django_grip>=1.7,<3", "Werkzeug>=0.12,<1"],
classifiers=[
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License"
]
)
