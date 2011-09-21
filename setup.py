#! /usr/bin/env python
'''
This file is part of targetcli.
Copyright (c) 2011 by RisingTide Systems LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, version 3 (AGPLv3).

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re
from distutils.core import setup
import targetcli

PKG = targetcli
VERSION = str(PKG.__version__)
(AUTHOR, EMAIL) = re.match('^(.*?)\s*<(.*)>$', PKG.__author__).groups()
URL = PKG.__url__
LICENSE = PKG.__license__
SCRIPTS = ["scripts/targetcli"]
DESCRIPTION = PKG.__description__

setup(name=PKG.__name__,
      description=DESCRIPTION,
      version=VERSION,
      author=AUTHOR,
      author_email=EMAIL,
      license=LICENSE,
      url=URL,
      scripts=SCRIPTS,
      packages=[PKG.__name__],
      package_data = {'':[]})
