#! /usr/bin/env python
'''
This file is part of targetcli.
Copyright (c) 2011-2013 by Datera, Inc

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
'''

from setuptools import setup

__version__ = ''
exec(open('targetcli/version.py').read())

setup(
    name = 'targetcli-fb',
    version = __version__,
    description = 'An administration shell for RTS storage targets.',
    license = 'Apache 2.0',
    maintainer = 'Andy Grover',
    maintainer_email = 'agrover@redhat.com',
    url = 'http://github.com/open-iscsi/targetcli-fb',
    packages = ['targetcli'],
    scripts = [
               'scripts/targetcli',
               'daemon/targetclid'
              ],
    data_files = [('/lib/systemd/system', ['systemd/targetclid.socket', 'systemd/targetclid.service'])],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
    )
