'''
Implements the rtsadmin root UI.

This file is part of RTSAdmin Community Edition.
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

from os import system
from rtslib import RTSRoot
from ui_node import UINode
from socket import gethostname
from ui_target import UIFabricModule
from tcm_dump import tcm_full_backup
from ui_backstore import UIBackstores
from ui_backstore_legacy import UIBackstoresLegacy

class UIRoot(UINode):
    '''
    The rtsadmin hierarchy root node.
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
        if self.shell.prefs['legacy_hba_view']:
            UIBackstoresLegacy(self)
        else:
            UIBackstores(self)
        if not self.loaded:
            self.shell.log.debug("Refreshing in non-loaded mode.")
            for fabric_module in RTSRoot().fabric_modules:
                if fabric_module:
                    self.shell.log.info("Using %s fabric module." \
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
                        self.shell.log.warning("Can't load fabric module %s."
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

    def ui_command_saveconfig(self):
        '''
        Saves the whole configuration tree to disk so that it will be restored
        on next boot. Unless you do that, changes are lost accross reboots.
        '''
        self.assert_root()
        self.shell.con.display("WARNING: Saving %s current configuration to "
                               % gethostname()
                               + "disk will overwrite your boot settings.")
        self.shell.con.display("The current target configuration will become "
                               + "the default boot config.")
        input = raw_input("Are you sure? Type 'yes': ")
        if input == "yes":
            tcm_full_backup(None, None, '1', None)
        else:
            self.shell.log.warning("Aborted, configuration left untouched.")

    def ui_command_version(self):
        '''
        Displays the rtsadmin and support libraries versions.
        '''
        from rtslib import __version__ as rtslib_version
        from rtsadmin import __version__ as rtsadmin_version
        from configshell import __version__ as configshell_version
        for package, version in dict(rtsadmin=rtsadmin_version,
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

