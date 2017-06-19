#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='alltheitems.wurstmineberg.de',
    description='a searchable web frontend for items.json',
    author='Wurstmineberg',
    author_email='mail@wurstmineberg.de',
    packages=['alltheitems'],
    use_scm_version = {
        'write_to': 'alltheitems/_version.py',
    },
    setup_requires=['setuptools_scm'],
    package_data={'alltheitems': ['assets/*.json']},
    install_requires=[
        'api',
        'bottle',
        'minecraft',
        'more-itertools',
        'wmb'
    ],
    dependency_links=[
        'git+https://github.com/wurstmineberg/api.wurstmineberg.de.git#egg=api',
        'git+https://github.com/wurstmineberg/systemd-minecraft.git#egg=minecraft',
        'git+https://github.com/wurstmineberg/wurstmineberg-common-python.git#egg=wmb'
    ]
)
