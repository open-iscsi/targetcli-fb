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

from rtslib import RTSRoot
from ui_node import UINode
from ui_target import UIFabricModule
from ui_backstore import UIBackstores

class UIRoot(UINode):
    '''
    The rtsadmin hierarchy root node.
    '''
    def __init__(self):
        self.loaded = False
        UINode.__init__(self)
        self.name = '/'

    def refresh(self):
        '''
        Refreshes the tree of target fabric modules.
        '''
        self._children = set([])
        self.add_child(UIBackstores())
        if not self.loaded:
            self.log.debug("Refreshing in non-loaded mode.")
            for fabric_module in RTSRoot().fabric_modules:
                if fabric_module:
                    self.log.info("Using %s fabric module." \
                                  % fabric_module.name)
                    self.add_child(UIFabricModule(fabric_module))
                else:
                    try:
                        for step in fabric_module.load(yield_steps=True):
                            (action, taken, desc) = step
                            if taken:
                                self.log.info(desc)
                        self.log.info("Done loading %s fabric module." \
                                      % fabric_module.name)
                    except Exception, msg:
                        self.log.warning("Can't load fabric module %s."
                                         % fabric_module.name)
                        self.log.debug(msg)
                    else:
                        self.add_child(UIFabricModule(fabric_module))
            self.loaded = True
        else:
            self.log.debug("Refreshing in loaded mode.")
            for fabric_module in RTSRoot().loaded_fabric_modules:
                    self.log.debug("Loading %s." % fabric_module.name)
                    self.add_child(UIFabricModule(fabric_module))

    def ui_command_version(self):
        '''
        Displays the rtsadmin and support libraries versions.
        '''
        from rtslib import __version__ as rtslib_version
        from rtsadmin import __version__ as rtsadmin_version
        from configshell import __version__ as configshell_version
        self.log.info("Running rtsadmin version %s" % rtsadmin_version)
        self.log.info("Using rtslib version %s" % rtslib_version)
        self.log.info("Using configshell version %s" % configshell_version)

