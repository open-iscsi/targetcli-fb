'''
Implements the targetcli base UI node.

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

from configshell import ConfigNode, ExecutionError
from rtslib import RTSLibError, RTSRoot

class UINode(ConfigNode):
    '''
    Our targetcli basic UI node.
    '''
    def __init__(self, name, parent=None, shell=None):
        ConfigNode.__init__(self, name, parent, shell)
        self.cfs_cwd = RTSRoot.configfs_dir
        self.define_config_group_param(
            'global', 'auto_enable_tpgt', 'bool',
            'If true, automatically enables TPGTs upon creation.')
        self.define_config_group_param(
            'global', 'auto_add_mapped_luns', 'bool',
            'If true, automatically create node ACLs mapped LUNs '
            + 'after creating a new target LUN or a new node ACL')
        self.define_config_group_param(
            'global', 'auto_cd_after_create', 'bool',
            'If true, changes current path to newly created objects.')
        self.define_config_group_param(
            'global', 'auto_save_on_exit', 'bool',
            'If true, saves configuration on exit.')

    def assert_root(self):
        '''
        For commands requiring root privileges, disable command if not the root
        node's as_root attribute is False.
        '''
        root_node = self.get_root()
        if hasattr(root_node, 'as_root') and not self.get_root().as_root:
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
    def __init__(self, name, rtslib_object, parent, late_params=False):
        '''
        Call from the class that inherits this, with the rtslib object that
        should be checked upon.
        '''
        UINode.__init__(self, name, parent)
        self.rtsnode = rtslib_object

        if late_params:
            return

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


