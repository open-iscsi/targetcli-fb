'''
Implements the targetcli base UI node.

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

from configshell import ConfigNode, ExecutionError
from rtslib import RTSLibError, RTSRoot, Config
from subprocess import PIPE, Popen
from os.path import isfile
from os import getuid

STARTUP_CONFIG = "/etc/target/scsi_target.lio"

def exec3(cmd):
    '''
    Executes a shell command **cmd** and returns
    **(retcode, stdout, stderr)**.
    '''
    process = Popen(cmd, shell=True, bufsize=1024*1024,
                    stdin=PIPE,
                    stdout=PIPE, stderr=PIPE,
                    close_fds=True)
    (out, err) = process.communicate()
    retcode = process.returncode
    return (retcode, out, err)

class UINode(ConfigNode):
    '''
    Our targetcli basic UI node.
    '''
    def __init__(self, name, parent=None, shell=None):
        ConfigNode.__init__(self, name, parent, shell)
        self.cfs_cwd = RTSRoot.configfs_dir
        self.define_config_group_param(
            'global', 'auto_enable_tpg', 'bool',
            'If true, automatically enables TPGs upon creation.')
        self.define_config_group_param(
            'global', 'auto_add_mapped_luns', 'bool',
            'If true, automatically create node ACLs mapped LUNs '
            + 'after creating a new target LUN or a new node ACL')
        self.define_config_group_param(
            'global', 'legacy_hba_view', 'bool',
            'If true, use legacy HBA view, allowing to create more '
            + 'than one storage object per HBA.')
        self.define_config_group_param(
            'global', 'auto_cd_after_create', 'bool',
            'If true, changes current path to newly created objects.')

    def assert_root(self):
        '''
        For commands requiring root privileges, disable command if not the root
        node's as_root attribute is False.
        '''
        root_node = self.get_root()
        if hasattr(root_node, 'as_root') and not root_node.as_root:
            raise ExecutionError("This privileged command is disabled: "
                                 + "you are not root.")

    def new_node(self, new_node):
        '''
        Used to honor global 'auto_cd_after_create'.
        Either returns None if the global is False, or the new_node if the
        global is True. In both cases, set the @last bookmark to last_node.
        '''
        self.shell.prefs['bookmarks']['last'] = new_node.path
        self.shell.prefs.save()
        if self.shell.prefs['auto_cd_after_create']:
            self.shell.log.info("Entering new node %s" % new_node.path)
            # Piggy backs on cd instead of just returning new_node,
            # so we update navigation history.
            return self.ui_command_cd(new_node.path)
        else:
            return None

    def refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        for child in self.children:
            child.refresh()

    def execute_command(self, command, pparams=[], kparams={}):
        '''
        We overload this one in order to handle our own exceptions cleanly,
        and not just configshell's ExecutionError.
        '''
        try:
            result = ConfigNode.execute_command(self, command,
                                                pparams, kparams)
        except RTSLibError, msg:
            self.shell.log.error(str(msg))
        else:
            self.shell.log.debug("Command %s succeeded." % command)
            return result

    def ui_command_exit(self):
        '''
        Exits the command line interface.
        '''
        if getuid() == 0:
            config = Config()
            if isfile(STARTUP_CONFIG):
                config.load(STARTUP_CONFIG, allow_new_attrs=True)
            saved_config = config.dump()
            config.load_live()
            live_config = config.dump()
            if saved_config != live_config:
                self.shell.con.display("There are unsaved configuration changes.\n"
                                       "If you exit now, configuration will not "
                                       "be updated and changes will be lost upon "
                                       "reboot.")
                try:
                    input = raw_input("Type 'exit' if you want to exit anyway: ")
                except EOFError:
                    input = None
                    self.shell.con.display('')
                if input == "exit":
                    return 'EXIT'
                else:
                    self.shell.log.warning("Aborted exit, use 'saveconfig' to "
                                           "save the current configuration.")
            else:
                return 'EXIT'
        else:
            return 'EXIT'

    def ui_command_refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        self.refresh()

    def ui_command_status(self):
        '''
        Displays the current node's status summary.

        SEE ALSO
        ========
        B{ls}
        '''
        description, is_healthy = self.summary()
        self.shell.log.info("Status for %s: %s" % (self.path, description))

    def ui_setgroup_global(self, parameter, value):
        ConfigNode.ui_setgroup_global(self, parameter, value)
        self.get_root().refresh()


class UIRTSLibNode(UINode):
    '''
    A subclass of UINode for nodes with an underlying RTSLib object.
    '''
    def __init__(self, name, rtslib_object, parent):
        '''
        Call from the class that inherits this, with the rtslib object that
        should be checked upon.
        '''
        UINode.__init__(self, name, parent)
        self.rtsnode = rtslib_object

        # If the rtsnode has parameters, use them
        parameters = self.rtsnode.list_parameters()
        parameters_ro = self.rtsnode.list_parameters(writable=False)
        for parameter in parameters:
            writable = parameter not in parameters_ro
            description = "The %s parameter." % parameter
            self.define_config_group_param(
                'parameter', parameter, 'string', description, writable)

        # If the rtsnode has attributes, enable them
        attributes = self.rtsnode.list_attributes()
        attributes_ro = self.rtsnode.list_attributes(writable=False)
        for attribute in attributes:
            writable = attribute not in attributes_ro
            description = "The %s attribute." % attribute
            self.define_config_group_param(
                'attribute', attribute, 'string', description, writable)

        # If the rtsnode has auth_attrs, use them
        auth_attrs = self.rtsnode.list_auth_attrs()
        auth_attrs_ro = self.rtsnode.list_auth_attrs(writable=False)
        for auth_attr in auth_attrs:
            writable = auth_attr not in auth_attrs_ro
            description = "The %s auth_attr." % auth_attr
            self.define_config_group_param(
                'auth', auth_attr, 'string', description, writable)

    def execute_command(self, command, pparams=[], kparams={}):
        '''
        Overrides the parent's execute_command() to check if the underlying
        RTSLib object still exists before returning.
        '''
        try:
            self.rtsnode._check_self()
        except RTSLibError:
            self.shell.log.error("The underlying rtslib object for "
                                 + "%s does not exist." % self.path)
            root = self.get_root()
            root.refresh()
            return root

        return UINode.execute_command(self, command, pparams, kparams)

    def ui_getgroup_attribute(self, attribute):
        '''
        This is the backend method for getting attributes.
        @param attribute: The attribute to get the value of.
        @type attribute: str
        @return: The attribute's value
        @rtype: arbitrary
        '''
        return self.rtsnode.get_attribute(attribute)

    def ui_setgroup_attribute(self, attribute, value):
        '''
        This is the backend method for setting attributes.
        @param attribute: The attribute to set the value of.
        @type attribute: str
        @param value: The attribute's value
        @type value: arbitrary
        '''
        self.assert_root()
        self.rtsnode.set_attribute(attribute, value)

    def ui_getgroup_parameter(self, parameter):
        '''
        This is the backend method for getting parameters.
        @param parameter: The parameter to get the value of.
        @type parameter: str
        @return: The parameter's value
        @rtype: arbitrary
        '''
        return self.rtsnode.get_parameter(parameter)

    def ui_setgroup_parameter(self, parameter, value):
        '''
        This is the backend method for setting parameters.
        @param parameter: The parameter to set the value of.
        @type parameter: str
        @param value: The parameter's value
        @type value: arbitrary
        '''
        self.assert_root()
        self.rtsnode.set_parameter(parameter, value)

    def ui_getgroup_auth(self, auth_attr):
        '''
        This is the backend method for getting auth_attrs.
        @param auth_attr: The auth_attr to get the value of.
        @type auth_attr: str
        @return: The auth_attr's value
        @rtype: arbitrary
        '''
        return self.rtsnode.get_auth_attr(auth_attr)

    def ui_setgroup_auth(self, auth_attr, value):
        '''
        This is the backend method for setting auth_attrs.
        @param auth_attr: The auth_attr to set the value of.
        @type auth_attr: str
        @param value: The auth_attr's value
        @type value: arbitrary
        '''
        self.assert_root()
        self.rtsnode.set_auth_attr(auth_attr, value)


