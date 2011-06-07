'''
Implements the rtsadmin base UI node.

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
from configshell import ConfigNode, ExecutionError
from rtslib import RTSLibError, RTSRoot

class UINode(ConfigNode):
    '''
    Our rtsadmin basic UI node.
    '''
    def __init__(self):
        ConfigNode.__init__(self)
        self.cfs_cwd = RTSRoot.configfs_dir
        self._configuration_groups['global']['auto_enable_tpgt'] = \
                 ['bool',
                  'If true, automatically enables TPGTs upon creation.',
                   True]
        self._configuration_groups['global']['auto_add_mapped_luns'] = \
                 ['bool',
                  'If true, automatically create node ACLs mapped LUNs '
                  + 'after creating a new target LUN or a new node ACL',
                  True]
        self._configuration_groups['global']['legacy_hba_view'] = \
                 ['bool',
                  'If true, use legacy HBA view, allowing to create more '
                  + 'than one storage object per HBA.',
                  True]
        self._configuration_groups['global']['auto_cd_after_create'] = \
                 ['bool',
                  'If true, changes current path to newly created objects.',
                  True]

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
        self.prefs['bookmarks']['last'] = new_node.path
        self.prefs.save()
        if self.prefs['auto_cd_after_create']:
            self.log.info("Entering new node %s" % new_node.path)
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
        if command == '_cfs':
            self.log.info(self.cfs_cwd)
            return
        elif command == '_sh':
            self.log.info("Opening a shell in %s." % self.cfs_cwd)
            self.con.display("Type [CTRL-D] or exit to come back.")
            system("(cd %s; bash)" % self.cfs_cwd )
            return
        try:
            result = ConfigNode.execute_command(self, command,
                                                pparams, kparams)
        except RTSLibError, msg:
            self.log.error(msg)
        else:
            self.log.debug("Command %s succeeded." % command)
            return result


    def ui_command_refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        self.refresh()

    def ui_command_saveconfig(self):
        '''
        Saves the whole configuration tree to disk so that it will be restored
        on next boot. Unless you do that, changes are lost accross reboots.
        '''
        self.assert_root()
        self.con.display("WARNING: Saving the current configuration to disk "
                         + "will overwrite your boot settings.")
        self.con.display("The current target configuration will become the "
                         + "default boot config.")
        system('PYTHONPATH="" python /usr/sbin/tcm_dump --o')

    def ui_command_status(self):
        '''
        Displays the current node's status summary.

        SEE ALSO
        ========
        B{ls}
        '''
        description, is_healthy = self.summary()
        self.log.info("Status for %s: %s" % (self.path, description))

    def ui_setgroup_global(self, parameter, value):
        ConfigNode.ui_setgroup_global(self, parameter, value)
        self.get_root().refresh()

class UIRTSLibNode(UINode):
    '''
    A subclass of UINode for nodes with an underlying RTSLib object.
    '''
    def __init__(self, rtslib_object):
        '''
        Call from the class that inherits this, with the rtslib object that
        should be checked upon.
        '''
        UINode.__init__(self)
        self.rtsnode = rtslib_object

        # If the rtsnode has parameters, use them
        parameters = self.rtsnode.list_parameters()
        parameters_ro = self.rtsnode.list_parameters(writable=False)
        if parameters:
            self._configuration_groups['parameter'] = {}
            for parameter in parameters:
                if parameter in parameters_ro:
                    writable = False
                else:
                    writable = True
                self._configuration_groups['parameter'][parameter] = \
                        ['string', "The %s parameter." % parameter,
                        writable]

        # If the rtsnode has attributes, enable them
        attributes = self.rtsnode.list_attributes()
        attributes_ro = self.rtsnode.list_attributes(writable=False)
        if attributes:
            self._configuration_groups['attribute'] = {}
            for attribute in attributes:
                if attribute in attributes_ro:
                    writable = False
                else:
                    writable = True
                self._configuration_groups['attribute'][attribute] = \
                        ['string', "The %s attribute." % attribute,
                        writable]

    def execute_command(self, command, pparams=[], kparams={}):
        '''
        Overrides the parent's execute_command() to check if the underlying
        RTSLib object still exists before returning.
        '''
        if not self.rtsnode.exists:
            self.log.error("The underlying rtslib object for "
                           + "%s does not exist." % self.path)
            root = self.get_root()
            root.refresh()
            return root
        else:
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


