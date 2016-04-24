#!/usr/bin/env python

from distutils.core import setup

setup(name='alltheitems.wurstmineberg.de',
      version='1.0',
      description='a searchable web frontend for items.json',
      author='Wurstmineberg',
      author_email='mail@wurstmineberg.de',
      packages=["alltheitems"],
      package_data={"alltheitems": ["assets/*.json"]}
     )


