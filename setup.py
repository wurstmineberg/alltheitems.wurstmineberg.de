#!/usr/bin/env python

from setuptools import setup

setup(name='alltheitems.wurstmineberg.de',
      description='a searchable web frontend for items.json',
      author='Wurstmineberg',
      author_email='mail@wurstmineberg.de',
      packages=["alltheitems"],
      use_scm_version = {
            "write_to": "alltheitems/version.py",
          },
      setup_requires=["setuptools_scm"],
      package_data={"alltheitems": ["assets/*.json"]}
     )


