'''
Implements the targetcli base UI node.

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


from configshell_fb import ConfigNode, ExecutionError


class UINode(ConfigNode):
    '''
    Our targetcli basic UI node.
    '''
    def __init__(self, name, parent=None, shell=None):
        ConfigNode.__init__(self, name, parent, shell)
        self.define_config_group_param(
            'global', 'export_backstore_name_as_model', 'bool',
            'If true, the backstore name is used for the scsi inquiry model name.')
        self.define_config_group_param(
            'global', 'auto_enable_tpgt', 'bool',
            'If true, automatically enables TPGTs upon creation.')
        self.define_config_group_param(
            'global', 'auto_add_mapped_luns', 'bool',
            'If true, automatically create node ACLs mapped LUNs after creating a new target LUN or a new node ACL')
        self.define_config_group_param(
            'global', 'auto_cd_after_create', 'bool',
            'If true, changes current path to newly created objects.')
        self.define_config_group_param(
            'global', 'auto_save_on_exit', 'bool',
            'If true, saves configuration on exit.')
        self.define_config_group_param(
            'global', 'auto_add_default_portal', 'bool',
            'If true, adds a portal listening on all IPs to new targets.')
        self.define_config_group_param(
            'global', 'max_backup_files', 'string',
            'Max no. of configurations to be backed up in /etc/target/backup/ directory.')
        self.define_config_group_param(
            'global', 'auto_use_daemon', 'bool',
            'If true, commands will be sent to targetclid.')
        self.define_config_group_param(
            'global', 'daemon_use_batch_mode', 'bool',
            'If true, use batch mode for daemonized approach.')

    def assert_root(self):
        '''
        For commands requiring root privileges, disable command if not the root
        node's as_root attribute is False.
        '''
        root_node = self.get_root()
        if hasattr(root_node, 'as_root') and not self.get_root().as_root:
            raise ExecutionError("This privileged command is disabled: you are not root.")

    def new_node(self, new_node):
        '''
        Used to honor global 'auto_cd_after_create'.
        Either returns None if the global is False, or the new_node if the
        global is True. In both cases, set the @last bookmark to last_node.
        '''
        self.shell.prefs['bookmarks']['last'] = new_node.path
        self.shell.prefs.save()
        if self.shell.prefs['auto_cd_after_create']:
            self.shell.log.info(f"Entering new node {new_node.path}")
            # Piggy backs on cd instead of just returning new_node,
            # so we update navigation history.
            return self.ui_command_cd(new_node.path)
        return None

    def refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        for child in self.children:
            child.refresh()

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
        ls
        '''
        description, _is_healthy = self.summary()
        self.shell.log.info(f"Status for {self.path}: {description}")

    def ui_setgroup_global(self, parameter, value):
        ConfigNode.ui_setgroup_global(self, parameter, value)
        self.get_root().refresh()

    def ui_type_yesno(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for "Yes" and "No" boolean values.
        "Yes" and "No" are used for boolean iSCSI session parameters.
        '''
        if reverse:
            if value is not None:
                return value
            return 'n/a'
        type_enum = ('Yes', 'No')
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            return syntax
        if value in type_enum:
            return value
        raise ValueError(f"Syntax error, '{value}' is not {syntax}.")


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
            param_type, desc = getattr(self.__class__, 'ui_desc_parameters', {}).get(parameter, ('string', ''))
            self.define_config_group_param(
                'parameter', parameter, param_type, desc, writable)

        # If the rtsnode has attributes, enable them
        attributes = self.rtsnode.list_attributes()
        attributes_ro = self.rtsnode.list_attributes(writable=False)
        for attribute in attributes:
            writable = attribute not in attributes_ro
            param_type, desc = getattr(self.__class__, 'ui_desc_attributes', {}).get(attribute, ('string', ''))
            self.define_config_group_param(
                'attribute', attribute, param_type, desc, writable)

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

    def ui_command_info(self):
        info = self.rtsnode.dump()
        for item in ('attributes', 'parameters'):
            if item in info:
                del info[item]
        for name, value in sorted(info.items()):
            if not isinstance(value, (dict, list)):
                self.shell.log.info(f"{name}: {value}")
