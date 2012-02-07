'''
Implements the targetcli root UI.

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

from rtslib import RTSRoot
from ui_node import UINode
from socket import gethostname
from ui_target import UIFabricModule
from ui_backstore import UIBackstores
import json
import shutil
import os
import stat

default_save_file = "/etc/target/saveconfig.json"

class UIRoot(UINode):
    '''
    The targetcli hierarchy root node.
    '''
    def __init__(self, shell, as_root=False):
        UINode.__init__(self, '/', shell=shell)
        self.as_root = as_root

    def refresh(self):
        '''
        Refreshes the tree of target fabric modules.
        '''
        self._children = set([])

        UIBackstores(self)

        for fabric_module in RTSRoot().fabric_modules:
            UIFabricModule(fabric_module, self)

    def ui_command_saveconfig(self, savefile=default_save_file):
        '''
        Saves the current configuration to a file so that it can be restored
        on next boot.
        '''
        self.assert_root()

        savefile = os.path.expanduser(savefile)

        backupfile = savefile + ".backup"
        try:
            shutil.move(savefile, backupfile)
            self.shell.log.info("Existing file %s backed up to %s" % \
                                    (savefile, backupfile))
        except IOError:
            pass

        with open(savefile, "w+") as f:
            os.fchmod(f.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            f.write(json.dumps(RTSRoot().dump(), sort_keys=True, indent=2))
            f.write("\n")

        self.shell.log.info("Configuration saved to %s" % savefile)

    def ui_command_restoreconfig(self, savefile=default_save_file, clear_existing=False):
        '''
        Restores configuration from a file.
        '''
        self.assert_root()

        savefile = os.path.expanduser(savefile)

        if not os.path.isfile(savefile):
            self.shell.log.info("Restore file %s not found" % savefile)
            return

        with open(savefile, "r") as f:
            try:
                errors = RTSRoot().restore(json.loads(f.read()), clear_existing)
            except ValueError:
                self.shell.log.error("Error parsing savefile: %s" % savefile)
                return

        if errors:
            self.shell.log.error("Configuration restored, %s recoverable errors" % errors)
        else:
            self.shell.log.info("Configuration restored from %s" % savefile)

        self.refresh()

    def ui_command_clearconfig(self, confirm=None):
        '''
        Removes entire configuration of backstores and targets
        '''
        self.assert_root()

        confirm = self.ui_eval_param(confirm, 'bool', False)

        RTSRoot().clear_existing(confirm=confirm)

        self.shell.log.info("All configuration cleared")

        self.refresh()

    def ui_command_version(self):
        '''
        Displays the targetcli and support libraries versions.
        '''
        from targetcli import __version__ as targetcli_version
        self.shell.log.info("targetcli version %s" % targetcli_version)

