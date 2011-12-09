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

default_save_file = "/etc/target/saveconfig.json"

class UIRoot(UINode):
    '''
    The targetcli hierarchy root node.
    '''
    def __init__(self, shell, as_root=False):
        self.loaded = False
        UINode.__init__(self, '/', shell=shell)
        self.as_root = as_root

    def refresh(self):
        '''
        Refreshes the tree of target fabric modules.
        '''
        self._children = set([])

        UIBackstores(self)

        if not self.loaded:
            self.shell.log.debug("Refreshing in non-loaded mode.")
            for fabric_module in RTSRoot().fabric_modules:
                if fabric_module:
                    self.shell.log.debug("Using %s fabric module." \
                                        % fabric_module.name)
                    UIFabricModule(fabric_module, self)
                elif self.as_root:
                    try:
                        for step in fabric_module.load(yield_steps=True):
                            (action, taken, desc) = step
                            if taken:
                                self.shell.log.info(desc)
                        self.shell.log.info("Done loading %s fabric module." \
                                            % fabric_module.name)
                    except Exception, msg:
                        self.shell.log.debug("Can't load fabric module %s."
                                               % fabric_module.name)
                        self.shell.log.debug(msg)
                    else:
                        UIFabricModule(fabric_module, self)
            self.loaded = True
        else:
            self.shell.log.debug("Refreshing in loaded mode.")
            for fabric_module in RTSRoot().loaded_fabric_modules:
                self.shell.log.debug("Loading %s." % fabric_module.name)
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
            RTSRoot().restore(json.loads(f.read()), clear_existing)

        self.shell.log.info("Configuration restored from %s" % savefile)

        self.refresh()

    def ui_command_clearconfig(self, confirm=False):
        '''
        Attempts to remove entire configuration of backstores and targets
        '''
        self.assert_root()

        RTSRoot().clear_existing(confirm=confirm)

        self.shell.log.info("All configuration cleared")

        self.refresh()

    def ui_command_version(self):
        '''
        Displays the targetcli and support libraries versions.
        '''
        from rtslib import __version__ as rtslib_version
        from targetcli import __version__ as targetcli_version
        from configshell import __version__ as configshell_version
        for package, version in dict(targetcli=targetcli_version,
                                     rtslib=rtslib_version,
                                     configshell=configshell_version).items():
            if version == 'GIT_VERSION':
                self.shell.log.error("Cannot find %s version. The %s package "
                                     % (package, package)
                                     + "has probably not been built properly "
                                     + "from either the git repository or a "
                                     + "public tarball.")
            else:
                self.shell.log.info("Using %s version %s" % (package, version))

