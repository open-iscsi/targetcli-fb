'''
Provides various utility functions.

This file is part of RTSLib.
Copyright (c) 2011-2013 by Datera, Inc
Copyright (c) 2011-2018 by Red Hat, Inc.

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

import os

from rtslib_fb import RTSLibError
from .ui_node import UIRTSLibNode

def command_enable(ui_rtsnode):
    '''
    Enables the storage object.

    SEE ALSO
    ========
    B{disable status}
    '''
    ui_rtsnode.assert_root()
    rtsnode = ui_rtsnode.rtsnode
    if rtsnode.enable:
        ui_rtsnode.shell.log.info("%s is already enabled." % rtsnode.name)
    else:
        try:
            ui_rtsnode.rtsnode.enable = True
            ui_rtsnode.shell.log.info("%s has been enabled." % rtsnode.name)
        except RTSLibError:
            raise ExecutionError("The %s could not be enabled." % rtsnode.name)

def command_disable(ui_rtsnode):
    '''
    Disables the storage obect

    SEE ALSO
    ========
    B{enable status}
    '''
    ui_rtsnode.assert_root()
    rtsnode = ui_rtsnode.rtsnode
    if rtsnode.enable:
        rtsnode.enable = False
        ui_rtsnode.shell.log.info("The %s has been disabled." % rtsnode.name)
    else:
        ui_rtsnode.shell.log.info("The %s is already disabled." % rtsnode.name)
