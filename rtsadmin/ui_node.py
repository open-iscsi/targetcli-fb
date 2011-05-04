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
from configshell import ConfigNode
from rtslib import RTSLibError, RTSRoot

class UINode(ConfigNode):
    '''
    Our rtsadmin basic UI node.
    '''
    def __init__(self):
        ConfigNode.__init__(self)
        self.cfs_cwd = RTSRoot.configfs_dir
        self._configuration_groups['global']['auto_enable_tpgt'] = \
                 [self.ui_type_onoff,
                  'If on, automatically enables TPGTs upon creation.']

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
        self.con.display("WARNING: Saving the current configuration to disk "
                         + "will overwrite your boot settings.")
        self.con.display("The current target configuration will become the "
                         + "default boot config.")
        system('PYTHONPATH="" python /usr/sbin/tcm_dump --o')

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

    def ui_command_status(self):
        '''
        Displays the current node's status summary.

        SEE ALSO
        ========
        B{ls}
        '''
        description, is_healthy = self.summary()
        self.log.info("Status for %s: %s" % (self.path, description))

class UIParameters(object):
    '''
    A completely virtual class to implement UI methods for setting/getting
    rtslib object parameters. Requires a set cfs_object parameter and calling
    __init__(self, cfs_object, ).
    '''
    def __init__(self, rtslib_object):
        '''
        Call from the class that inherits this, with the rtslib object that
        should be queried for parameters.
        '''
        self._rtslib_object = rtslib_object
        self._configuration_groups['parameter'] = {}
        for parameter in self._rtslib_object.list_parameters():
            self._configuration_groups['parameter'][parameter] = \
                    [self.ui_type_string, "The %s parameter." % parameter]

    def ui_getgroup_parameter(self, parameter):
        '''
        This is the backend method for getting parameters.
        @param parameter: The parameter to get the value of.
        @type parameter: str
        @return: The parameter's value
        @rtype: arbitrary
        '''
        return self._rtslib_object.get_parameter(parameter)

    def ui_setgroup_parameter(self, parameter, value):
        '''
        This is the backend method for setting parameters.
        @param parameter: The parameter to set the value of.
        @type parameter: str
        @param value: The parameter's value
        @type value: arbitrary
        '''
        self._rtslib_object.set_parameter(parameter, value)

class UIAttributes(object):
    '''
    A completely virtual class to implement UI methods for setting/getting
    rtslib object attributes. Requires a set cfs_object attribute and calling
    __init__(self, cfs_object, ).
    '''
    def __init__(self, rtslib_object):
        '''
        Call from the class that inherits this, with the rtslib object that
        should be queried for attributes.
        '''
        self._rtslib_object = rtslib_object
        self._configuration_groups['attribute'] = {}
        for attribute in self._rtslib_object.list_attributes():
            self._configuration_groups['attribute'][attribute] = \
                    [self.ui_type_string, "The %s attribute." % attribute]

    def ui_getgroup_attribute(self, attribute):
        '''
        This is the backend method for getting attributes.
        @param attribute: The attribute to get the value of.
        @type attribute: str
        @return: The attribute's value
        @rtype: arbitrary
        '''
        return self._rtslib_object.get_attribute(attribute)

    def ui_setgroup_attribute(self, attribute, value):
        '''
        This is the backend method for setting attributes.
        @param attribute: The attribute to set the value of.
        @type attribute: str
        @param value: The attribute's value
        @type value: arbitrary
        '''
        self._rtslib_object.set_attribute(attribute, value)
