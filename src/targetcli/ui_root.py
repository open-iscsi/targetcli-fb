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

import gzip
import os
import re
import shutil
import stat
from datetime import datetime
from glob import glob
from pathlib import Path, PurePosixPath

from configshell_fb import ExecutionError
from rtslib_fb import RTSRoot
from rtslib_fb.utils import ignored

from targetcli import __version__

from .ui_backstore import UIBackstores, complete_path
from .ui_node import UINode
from .ui_target import UIFabricModule

default_target_dir = "/etc/target"
default_save_file = os.path.join(default_target_dir, "saveconfig.json")
universal_prefs_file = os.path.join(default_target_dir, "targetcli.conf")

class UIRoot(UINode):
    '''
    The targetcli hierarchy root node.
    '''
    def __init__(self, shell, as_root=False):
        UINode.__init__(self, '/', shell=shell)
        self.as_root = as_root
        self.rtsroot = RTSRoot()

    def refresh(self):
        '''
        Refreshes the tree of target fabric modules.
        '''
        self._children = set()

        # Invalidate any rtslib caches
        if 'invalidate_caches' in dir(RTSRoot):
            self.rtsroot.invalidate_caches()

        UIBackstores(self)

        # only show fabrics present in the system
        for fm in self.rtsroot.fabric_modules:
            if fm.wwns is None or any(fm.wwns):
                UIFabricModule(fm, self)

    def _compare_files(self, backupfile, savefile):
        '''
        Compare backfile and saveconfig file
        '''
        backupfilepath = Path(backupfile)
        if PurePosixPath(backupfile).suffix == '.gz':
            try:
                with gzip.open(backupfilepath, 'rb') as fbkp:
                    fdata_bkp = fbkp.read()
            except OSError as e:
                self.shell.log.warning(f"Could not gzip open backupfile {backupfile}: {e.strerror}")

        else:
            try:
                fdata_bkp = backupfilepath.read_bytes()
            except OSError as e:
                self.shell.log.warning(f"Could not open backupfile {backupfile}: {e.strerror}")

        try:
            fdata = Path(savefile).read_bytes()
        except OSError as e:
            self.shell.log.warning(f"Could not open saveconfig file {savefile}: {e.strerror}")

        return fdata_bkp == fdata

    def _create_dir(self, dirname):
        '''
        create directory with permissions 0o600 set
        if directory already exists, set right perms
        '''
        mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600
        dir_path = Path(dirname)
        if not dir_path.exists():
            umask = 0o777 ^ mode  # Prevents always downgrading umask to 0
            umask_original = os.umask(umask)
            try:
                dir_path.mkdir(mode=mode)
            except OSError as exe:
                raise ExecutionError(f"Cannot create directory [{dirname}] {exe.strerror}.")
            finally:
                os.umask(umask_original)
        elif dirname == default_target_dir and (os.stat(dirname).st_mode & 0o777) != mode:
            os.chmod(dirname, mode)

    def _save_backups(self, savefile):
        '''
        Take backup of config-file if needed.
        '''
        # Only save backups if saving to default location
        if savefile != default_save_file:
            return

        backup_dir = os.path.dirname(savefile) + "/backup/"
        backup_name = "saveconfig-" + \
                      datetime.now().strftime("%Y%m%d-%H:%M:%S") + "-json.gz"
        backupfile = backup_dir + backup_name
        backup_error = None

        self._create_dir(backup_dir)

        # Only save backups if savefile exits
        if not Path(savefile).exists():
            return

        backed_files_list = sorted(glob(os.path.dirname(savefile) + \
                                   "/backup/saveconfig-*json*"))

        # Save backup if backup dir is empty, or savefile is differnt from recent backup copy
        if not backed_files_list or not self._compare_files(backed_files_list[-1], savefile):
            mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600
            umask = 0o777 ^ mode  # Prevents always downgrading umask to 0
            umask_original = os.umask(umask)
            try:
                with open(savefile, 'rb') as f_in, gzip.open(backupfile, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    f_out.flush()
            except OSError as ioe:
                backup_error = ioe.strerror or "Unknown error"
            finally:
                os.umask(umask_original)

            if backup_error is None:
                # remove excess backups
                max_backup_files = int(self.shell.prefs['max_backup_files'])

                try:
                    prefs = Path(universal_prefs_file).read_text()
                    backups = [line for line in prefs.splitlines() if re.match(
                        r'^max_backup_files\s*=', line)]
                    if max_backup_files < int(backups[0].split('=')[1].strip()):
                        max_backup_files = int(backups[0].split('=')[1].strip())
                except:
                    self.shell.log.debug(f"No universal prefs file '{universal_prefs_file}'.")

                files_to_unlink = list(reversed(backed_files_list))[max_backup_files - 1:]
                for f in files_to_unlink:
                    with ignored(IOError):
                        Path(f).unlink()

                self.shell.log.info("Last %d configs saved in %s."
                                    % (max_backup_files, backup_dir))
            else:
                self.shell.log.warning(f"Could not create backup file {backupfile}: {backup_error}.")

    def ui_command_saveconfig(self, savefile=default_save_file):
        '''
        Saves the current configuration to a file so that it can be restored
        on next boot.
        '''
        self.assert_root()

        if not savefile:
            savefile = default_save_file

        savefile = os.path.expanduser(savefile)

        save_dir = os.path.dirname(savefile)
        self._create_dir(save_dir)
        self._save_backups(savefile)

        self.rtsroot.save_to_file(savefile)

        self.shell.log.info(f"Configuration saved to {savefile}")

    def ui_command_restoreconfig(self, savefile=default_save_file, clear_existing=False,
                                 target=None, storage_object=None):
        '''
        Restores configuration from a file.
        '''
        self.assert_root()

        savefile = os.path.expanduser(savefile)

        if not os.path.isfile(savefile):
            self.shell.log.info(f"Restore file {savefile} not found")
            return

        target = self.ui_eval_param(target, 'string', None)
        storage_object = self.ui_eval_param(storage_object, 'string', None)
        errors = self.rtsroot.restore_from_file(savefile, clear_existing,
                                                target, storage_object)

        self.refresh()

        if errors:
            raise ExecutionError("Configuration restored, %d recoverable errors:\n%s" % \
                                     (len(errors), "\n".join(errors)))

        self.shell.log.info(f"Configuration restored from {savefile}")

    def ui_complete_saveconfig(self, parameters, text, current_param):
        '''
        Auto-completes the file name
        '''
        if current_param != 'savefile':
            return []
        completions = complete_path(text, stat.S_ISREG)
        if len(completions) == 1 and not completions[0].endswith('/'):
            completions = [completions[0] + ' ']
        return completions

    ui_complete_restoreconfig = ui_complete_saveconfig

    def ui_command_clearconfig(self, confirm=None):
        '''
        Removes entire configuration of backstores and targets
        '''
        self.assert_root()

        confirm = self.ui_eval_param(confirm, 'bool', False)

        self.rtsroot.clear_existing(confirm=confirm)

        self.shell.log.info("All configuration cleared")

        self.refresh()

    def ui_command_version(self):
        '''
        Displays the targetcli and support libraries versions.
        '''
        self.shell.log.info(f"targetcli version {__version__}")

    def ui_command_sessions(self, action="list", sid=None):
        '''
        Displays a detailed list of all open sessions.

        PARAMETERS
        ==========

        action
        ------
        The action is one of:
            - `list`` gives a short session list
            - `detail` gives a detailed list

        sid
        ---
        You can specify an "sid" to only list this one,
        with or without details.

        SEE ALSO
        ========
        status
        '''

        indent_step = 4
        base_steps = 0
        action_list = ("list", "detail")

        if action not in action_list:
            raise ExecutionError(f"action must be one of: {', '.join(action_list)}")
        if sid is not None:
            try:
                int(sid)
            except ValueError:
                raise ExecutionError(f"sid must be a number, '{sid}' given")

        def indent_print(text, steps):
            console = self.shell.con
            console.display(console.indent(text, indent_step * steps),
                            no_lf=True)

        def print_session(session):
            acl = session['parent_nodeacl']
            indent_print("alias: %(alias)s\tsid: %(id)i type: %(type)s session-state: %(state)s" % session,
                         base_steps)

            if action == 'detail':
                if self.as_root:
                    auth = " (authenticated)" if acl.authenticate_target else " (NOT AUTHENTICATED)"
                else:
                    auth = ""

                indent_print(f"name: {acl.node_wwn}{auth}",
                                 base_steps + 1)

                for mlun in acl.mapped_luns:
                    plugin = mlun.tpg_lun.storage_object.plugin
                    name = mlun.tpg_lun.storage_object.name
                    mode = "r" if mlun.write_protect else "rw"
                    indent_print("mapped-lun: %d backstore: %s/%s mode: %s" %
                                 (mlun.mapped_lun, plugin, name, mode),
                                 base_steps + 1)

                for connection in session['connections']:
                    indent_print("address: %(address)s (%(transport)s)  cid: %(cid)i connection-state: %(cstate)s"
                                 % connection, base_steps + 1)

        if sid:
            printed_sessions = [x for x in self.rtsroot.sessions if x['id'] == int(sid)]
        else:
            printed_sessions = list(self.rtsroot.sessions)

        if len(printed_sessions):
            for session in printed_sessions:
                print_session(session)
        elif sid is None:
            indent_print("(no open sessions)", base_steps)
        else:
            raise ExecutionError("no session found with sid %i" % int(sid))
