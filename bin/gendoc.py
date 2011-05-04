#!/usr/bin/python

# This file is part of RTSAdmin Community Edition.
# Copyright (c) 2011 by RisingTide Systems LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 (AGPLv3).
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys
import inspect
import textwrap
import datetime
sys.path.insert(0, os.path.realpath("."))
import rtsadmin

def doctitle(txt):
    return "%s\n%s\n%s\n\n" \
            % ("".ljust(len(txt), "="), txt, "".ljust(len(txt), "="))

def docsubtitle(txt):
    return "%s\n%s\n%s\n\n" \
            % ("".ljust(len(txt), "-"), txt, "".ljust(len(txt), "-"))

def title(txt):
    return "%s\n%s\n\n" % (txt, "".ljust(len(txt), "="))

def subtitle(txt):
    return "%s\n%s\n\n" % (txt, "".ljust(len(txt), "-"))

def gen_context_reference():
    string = ""
    string += "Documentation extract not implemented yet"
    return string

def gen_help_misc():
    string = ""
    string += "Documentation extract not implemented yet"
    return string

def gen_help_cmd():
    string = title("Globally Available Commands")
    string += "Documentation extract not implemented yet"
    return string

def gen_title():
    string = ""
    string += doctitle("The rtsadmin Reference Guide")
    string += docsubtitle(rtsadmin.__description__)
    string += ":Date: version %s built on %s\n" \
            % (str(rtsadmin.__version__), 
               str(datetime.datetime.now().date()))
    license_fields = rtsadmin.__license__.split(".")
    string += ":Author: %s. %s.\n" % (license_fields[0], license_fields[1])
    string += "\n"
    return string

def gen_toc():
    return ".. contents:: **Table of Contents**\n\n"

def gen_options():
    return ".. sectnum::\n\n.. header:: .. image:: rtslogo.png\n\n"

if __name__ == "__main__":
    print gen_title()
    print gen_options()
    print gen_toc()
    print gen_help_misc()
    print gen_help_cmd()
    print gen_context_reference()
