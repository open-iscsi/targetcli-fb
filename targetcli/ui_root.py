'''
Implements the targetcli root UI.

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

from rtslib import RTSRoot
from rtslib.utils import ignored
from configshell import ExecutionError
from ui_node import UINode
from socket import gethostname
from ui_target import UIFabricModule
from ui_backstore import UIBackstores
import json
import shutil
import os
import stat
from glob import glob
from datetime import datetime

default_save_file = "/etc/target/saveconfig.json"
kept_backups = 10

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

        # only show fabrics present in the system
        for fm in RTSRoot().fabric_modules:
            if fm.wwns == None or list(fm.wwns) != []:
                UIFabricModule(fm, self)

    def ui_command_saveconfig(self, savefile=default_save_file):
        '''
        Saves the current configuration to a file so that it can be restored
        on next boot.
        '''
        self.assert_root()

        savefile = os.path.expanduser(savefile)

        with open(savefile+".temp", "w+") as f:
            os.fchmod(f.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            f.write(json.dumps(RTSRoot().dump(), sort_keys=True, indent=2))
            f.write("\n")
            os.fsync(f.fileno())

        # Only save backups if saving to default location
        if savefile == default_save_file:
            backup_dir = os.path.dirname(savefile) + "/backup"
            backup_name = "saveconfig-" + \
                datetime.now().strftime("%Y%m%d-%H:%M:%S") + ".json"
            backupfile = backup_dir + "/" + backup_name
            with ignored(IOError):
                shutil.move(savefile, backupfile)

            # Kill excess backups
            backups = sorted(glob(os.path.dirname(savefile) + "/backup/*.json"))
            files_to_unlink = list(reversed(backups))[kept_backups:]
            for f in files_to_unlink:
                os.unlink(f)

            self.shell.log.info("Last %d configs saved in %s." % \
                                    (kept_backups, backup_dir))

        os.rename(savefile+".temp", savefile)
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
            self.shell.log.error("Configuration restored, %d recoverable errors:" % len(errors))
            for error in errors:
                self.shell.log.error(error)
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

    def ui_command_sessions(self, action="list", sid=None):
        '''
        Displays a detailed list of all open sessions.

        PARAMETERS
        ==========

        I{action}
        ---------
        The I{action} is one of:
            - B{list} gives a short session list
            - B{detail} gives a detailed list

        I{sid}
        ------
        You can specify an I{sid} to only list this one,
        with or without details.

        SEE ALSO
        ========
        status
        '''

        indent_step = 4
        base_steps = 0
        action_list = ("list", "detail")
        root = RTSRoot()

        if action not in action_list:
            raise ExecutionError("action must be one of: %s" %
                                                    ", ".join(action_list))
        if sid is not None:
            try:
                int(sid)
            except ValueError:
                raise ExecutionError("sid must be a number, '%s' given" % sid)

        def indent_print(text, steps):
            console = self.shell.con
            console.display(console.indent(text, indent_step * steps),
                            no_lf=True)

        def print_session(session):
            acl = session['parent_nodeacl']
            indent_print("alias: %(alias)s\tsid: %(id)i type: " \
                             "%(type)s session-state: %(state)s" % session,
                         base_steps)

            if action == 'detail':
                if self.as_root:
                    if acl.authenticate_target:
                        auth = " (authenticated)"
                    else:
                        auth = " (NOT AUTHENTICATED)"
                else:
                    auth = ""

                indent_print("name: %s%s" % (acl.node_wwn, auth),
                                 base_steps + 1)

                for mlun in acl.mapped_luns:
                    plugin = mlun.tpg_lun.storage_object.backstore.plugin
                    name = mlun.tpg_lun.storage_object.name
                    if mlun.write_protect:
                        mode = "r"
                    else:
                        mode = "rw"
                    indent_print("mapped-lun: %d backstore: %s/%s mode: %s" %
                                 (mlun.mapped_lun, plugin, name, mode),
                                 base_steps + 1)

                for connection in session['connections']:
                    indent_print("address: %(address)s (%(transport)s)  cid: " \
                                     "%(cid)i connection-state: %(cstate)s" % \
                                     connection, base_steps + 1)

        if sid:
            printed_sessions = filter(lambda x: x['id'] == int(sid), root.sessions)
        else:
            printed_sessions = list(root.sessions)

        if len(printed_sessions):
            for session in printed_sessions:
                print_session(session)
        else:
            if sid is None:
                indent_print("(no open sessions)", base_steps)
            else:
                raise ExecutionError("no session found with sid %i" % int(sid))

