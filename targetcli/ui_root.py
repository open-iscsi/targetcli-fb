'''
Implements the targetcli root UI.

This file is part of targetcli.
Copyright (c) 2011-2014 by Datera, Inc

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
from os import system
import readline, tempfile
from rtslib import RTSRoot, Config
from ui_node import UINode, STARTUP_CONFIG
from socket import gethostname
from cli_config import CliConfig
from ui_target import UIFabricModule
from ui_backstore import UIBackstores
from ui_backstore_legacy import UIBackstoresLegacy

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
        if self.shell.prefs['legacy_hba_view']:
            UIBackstoresLegacy(self)
        else:
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
                        self.shell.log.debug("Done loading %s fabric module." \
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
        try:
            input = raw_input("Are you sure? Type 'yes': ")
        except EOFError:
            input = None
            self.shell.con.display('')
        if input == "yes":
            config = Config()
            config.load_live()
            with open(STARTUP_CONFIG, "w") as fd:
                fd.write(config.dump())
        else:
            self.shell.log.warning("Aborted, configuration left untouched.")

    def ui_command_configure(self):
        '''
        Enters the config mode.

        This mode allows editing a candidate configuration without
        impacting the running system. This candidate configuration can
        then either be commited or discarded at will. If commited, it
        will be applied to the running system and saved as the new
        startup configuration.

        Other features include loading a configuration from file, undo
        support, rollback support, configuration backups and more.

        This mode is a functionnal but early preview version of the next-
        generation targetcli environment.
        '''
        self.assert_root()
        self.shell.log.warning("Entering configure mode")
        self.shell.log.warning("This mode is a functionnal but early "
                               "preview version of the next-generation "
                               "targetcli")
        system("targetcli-ng configure")
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

