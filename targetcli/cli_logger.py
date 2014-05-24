'''
This file is part of LIO(tm).

Copyright (c) 2012-2014 by Datera, Inc.
More information on www.datera.io.

Original author: Jerome Martin <jxm@netiant.com>

Datera and LIO are trademarks of Datera, Inc., which may be registered in some
jurisdictions.

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
import sys, logging

class LogFormatter(logging.Formatter):

    default_format = "LOG%(levelno)s: %(msg)s"
    formats = {10: "DEBUG:%(module)s:%(lineno)s: %(msg)s",
               20: "%(msg)s",
               30: "\n### %(msg)s\n",
               40: "*** %(msg)s",
               50: "CRITICAL: %(msg)s"}

    def __init__(self):
        logging.Formatter.__init__(self)

    def format(self, record):
        self._fmt = self.formats.get(record.levelno, self.default_format)
        return logging.Formatter.format(self, record) 

logger = logging.getLogger("LioCli")
logger.setLevel(logging.INFO)

log_fmt = LogFormatter()
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_fmt)
logging.root.addHandler(log_handler)
