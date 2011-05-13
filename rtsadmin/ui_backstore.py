'''
Implements the rtsadmin backstores related UI.

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

from ui_node import UINode, UIAttributes, UIParameters
from rtslib import RTSRoot
from rtslib import FileIOBackstore, IBlockBackstore
from rtslib import PSCSIBackstore, RDDRBackstore, RDMCPBackstore
from rtslib import FileIOStorageObject, IBlockStorageObject
from rtslib import PSCSIStorageObject, RDDRStorageObject, RDMCPStorageObject
from rtslib.utils import get_block_type, is_disk_partition

class UIBackstores(UINode):
    '''
    The backstores container UI.
    '''
    def __init__(self):
        UINode.__init__(self)
        self.name = 'backstores'
        self.cfs_cwd = "%s/core" % self.cfs_cwd
        self.refresh()

    def refresh(self):
        self._children = set([])
        for backstore in RTSRoot().backstores:
            backstore_plugin = backstore.plugin
            if backstore_plugin == 'pscsi':
                self.add_child(UIPSCSIBackstore(backstore))
            elif backstore_plugin == 'rd_dr':
                self.add_child(UIRDDRBackstore(backstore))
            elif backstore_plugin == 'rd_mcp':
                self.add_child(UIRDMCPBackstore(backstore))
            elif backstore_plugin == 'fileio':
                self.add_child(UIFileIOBackstore(backstore))
            elif backstore_plugin == 'iblock':
                self.add_child(UIIBlockBackstore(backstore))

    def summary(self):
        no_backstores = len(self._children)
        if no_backstores > 1:
            msg = "%d Backstores" % no_backstores
        else:
            msg = "%d Backstore" % no_backstores
        return (msg, None)

    def ui_command_create(self, backstore_plugin):
        '''
        Creates a new backstore, using the chosen I{backstore_plugin}. More
        than one backstores using the same I{backstore_plugin} can co-exist.
        They will be identified by incremental index numbers, starting from 0.

        AVAILABLE BACKSTORE PLUGINS
        ===========================

        B{iblock}
        ---------
        This I{backstore_plugin} provides I{SPC-4}, along with I{ALUA} and
        I{Persistent Reservations} emulation on top of Linux BLOCK devices:
        B{any block device} that appears in /sys/block.

        B{pscsi}
        --------
        Provides pass-through for Linux physical SCSI devices. It can be used
        with any storage object that does B{direct pass-through} of SCSI
        commands without SCSI emulation. This assumes an underlying SCSI
        device that appears with lsscsi in /proc/scsi/scsi, such as a SAS hard
        drive, such as any SCSI device. The Linux kernel code for device SCSI
        drivers resides in linux/drivers/scsi. SCSI-3 and higher is supported
        with this subsystem, but only for control CDBs capable by the device
        firmware.

        B{fileio}
        ---------
        This I{backstore_plugin} provides I{SPC-4}, along with I{ALUA} and
        I{Persistent Reservations} emulation on top of Linux VFS devices:
        B{any file on a mounted filesystem}. It may be backed by a file or an
        underlying real block device. FILEIO is using struct file to serve
        block I/O with various methods (synchronous or asynchronous) and
        (buffered or direct).

        B{rd_dr}
        -------
        This I{backstore_plugin} provides the same level of SCSI emulation than
        the I{fileio} and I{iblock} backstores, but uses a B{ramdisk}, based on
        direct memory mapping. It is the fastest of all backstores, and is
        typically used for bandwidth testing.

        B{rd_mcp}
        --------
        This I{backstore_plugin} is a bit slower than B{rd_dr}, but more robust
        with multiple initiators, with a separate memory mapping using memory
        copy. Also typically used for bandwidth testing.

        EXAMPLE
        =======

        B{create iblock}
        ----------------
        Creates a new backstore, using the B{iblock} I{backstore_plugin}.
        '''
        self.assert_root()
        self.log.debug("%r" % [(backstore.plugin, backstore.index)
                              for backstore in RTSRoot().backstores])
        indexes = [backstore.index for backstore in RTSRoot().backstores
                   if backstore.plugin == backstore_plugin]
        self.log.debug("Existing %s backstore indexes: %r"
                      % (backstore_plugin, indexes))
        for index in range(1048576):
            if index not in indexes:
                backstore_index = index
                break

        if backstore_index is None:
            self.log.error("Cannot find an available backstore index.")
            return
        else:
            self.log.info("First available %s backstore index is %d."
                          % (backstore_plugin, backstore_index))

        if backstore_plugin == 'pscsi':
            backstore = PSCSIBackstore(backstore_index, mode='create')
            self.add_child(UIPSCSIBackstore(backstore))
        elif backstore_plugin == 'rd_dr':
            backstore = RDDRBackstore(backstore_index, mode='create')
            self.add_child(UIRDDRBackstore(backstore))
        elif backstore_plugin == 'rd_mcp':
            backstore = RDMCPBackstore(backstore_index, mode='create')
            self.add_child(UIRDMCPBackstore(backstore))
        elif backstore_plugin == 'fileio':
            backstore = FileIOBackstore(backstore_index, mode='create')
            self.add_child(UIFileIOBackstore(backstore))
        elif backstore_plugin == 'iblock':
            backstore = IBlockBackstore(backstore_index, mode='create')
            self.add_child(UIIBlockBackstore(backstore))
        else:
            self.log.error("Invalid backstore plugin %s" % backstore_plugin)
            return

        self.log.info("Created new backstore %s" % backstore.name)

    def ui_complete_create(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command create.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'backstore_plugin':
            plugins = ['pscsi', 'rd_dr', 'rd_mcp', 'fileio', 'iblock']
            completions = [plugin for plugin in plugins
                           if plugin.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_delete(self, backstore):
        '''
        Deletes a I{backstore}, and recursively all defined storage objects
        hanging under it. If there are existing LUNs making use of those
        storage objects, they will be deleted too.

        EXAMPLE
        =======
        B{delete iblock2}
        -----------------
        That would recursively delete the B{iblock} backstore with index 2.
        '''
        self.assert_root()
        for child in self.children:
            if child.name == backstore:
                child.backstore.delete()
                self.del_child(child)
                self.log.info("Deleted backstore %s." % backstore)
                self.parent.refresh()
                break
        else:
            self.log.error("Cannot find backstore to delete: %s."
                           % backstore)

    def ui_complete_delete(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command delete.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'backstore':
            backstores = [child.name for child in self.children]
            completions = [backstore for backstore in backstores
                           if backstore.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UIBackstore(UINode):
    '''
    A backstore UI.
    '''
    def __init__(self, backstore):
        UINode.__init__(self)
        self.backstore = backstore
        self.name = backstore.name
        self.cfs_cwd = backstore.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for storage_object in self.backstore.storage_objects:
            self.add_child(UIStorageObject(storage_object))

    def summary(self):
        no_storage_objects = len(self._children)
        if no_storage_objects > 1:
            msg = "%d Storage Objects" % no_storage_objects
        else:
            msg = "%d Storage Object" % no_storage_objects
        return (msg, None)

    def prm_gen_wwn(self, generate_wwn):
        generate_wwn = \
                self.ui_eval_param(generate_wwn, self.ui_type_bool, True)
        if generate_wwn:
            self.log.info("Generating a wwn serial.")
        else:
            self.log.info("Not generating a wwn serial.")
        return generate_wwn

    def prm_buffered(self, buffered):
        generate_wwn = \
                self.ui_eval_param(buffered, self.ui_type_bool, True)
        if buffered:
            self.log.info("Using buffered mode.")
        else:
            self.log.info("Not using buffered mode.")
        return buffered

    def ui_command_version(self):
        '''
        Displays the version of the current backstore's plugin.
        '''
        self.con.display("Backstore plugin %s %s"
                         % (self.backstore.plugin, self.backstore.version))

    def ui_command_delete(self, name):
        '''
        Recursively deletes the storage object having the specified I{name}. If
        there are LUNs using this storage object, they will be deleted too.

        EXAMPLE
        =======
        B{delete mystorage}
        -------------------
        Deletes the storage object named mystorage, and all associated LUNs.
        '''
        self.assert_root()
        for child in self.children:
            if child.name == name:
                child.storage_object.delete()
                self.del_child(child)
                self.log.info("Deleted storage object %s." % name)
                self.parent.parent.refresh()
                break
        else:
            self.log.error("Could not find storage object to delete: %s."
                           % name)

    def ui_complete_delete(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command delete.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'name':
            names = [child.name for child in self.children]
            completions = [name for name in names
                           if name.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UIPSCSIBackstore(UIBackstore):
    '''
    PSCSI backstore UI.
    '''
    def ui_command_create(self, name, dev):
        '''
        Creates a PSCSI storage object, with supplied name and SCSI device. The
        SCSI device I{dev} can either be a path name to the device, in which
        case it is recommended to use the /dev/disk/by-id hierarchy to have
        consistent naming should your physical SCSI system be modified, or an
        SCSI device ID in the H:C:T:L format, which is not recommended as SCSI
        IDs may vary in time.
        '''
        self.assert_root()
        so = PSCSIStorageObject(self.backstore, name, dev)
        self.add_child(UIStorageObject(so))
        self.log.info("Created pscsi storage object %s using %s"
                      % (name, dev))

class UIRDDRBackstore(UIBackstore):
    '''
    RDDR backstore UI.
    '''
    def ui_command_create(self, name, size, generate_wwn=None):
        '''
        Creates an RDDR storage object. I{size} is the size of the ramdisk, and
        the optional I{generate_wwn} parameter is a boolean specifying whether
        or not we should generate a T10 wwn serial for the unit (by default,
        yes).

        SIZE SYNTAX
        ===========
        - If size is an int, it represents a number of bytes.
        - If size is a string, the following units can be used:
            - B{B} or no unit present for bytes
            - B{k}, B{K}, B{kB}, B{KB} for kB (kilobytes)
            - B{m}, B{M}, B{mB}, B{MB} for MB (megabytes)
            - B{g}, B{G}, B{gB}, B{GB} for GB (gigabytes)
            - B{t}, B{T}, B{tB}, B{TB} for TB (terabytes)
        '''
        self.assert_root()
        so = RDDRStorageObject(self.backstore, name, size,
                               self.prm_gen_wwn(generate_wwn))
        self.add_child(UIStorageObject(so))
        self.log.info("Created rd_dr ramdisk storage object %s with size %s."
                      % (name, size))

class UIRDMCPBackstore(UIBackstore):
    '''
    RDMCP backstore UI.
    '''
    def ui_command_create(self, name, size, generate_wwn=None):
        '''
        Creates an RDMCP storage object. I{size} is the size of the ramdisk,
        and the optional I{generate_wwn} parameter is a boolean specifying
        whether or not we should generate a T10 wwn Serial for the unit (by
        default, yes).

        SIZE SYNTAX
        ===========
        - If size is an int, it represents a number of bytes.
        - If size is a string, the following units can be used:
            - B{B} or no unit present for bytes
            - B{k}, B{K}, B{kB}, B{KB} for kB (kilobytes)
            - B{m}, B{M}, B{mB}, B{MB} for MB (megabytes)
            - B{g}, B{G}, B{gB}, B{GB} for GB (gigabytes)
            - B{t}, B{T}, B{tB}, B{TB} for TB (terabytes)
        '''
        self.assert_root()
        so = RDMCPStorageObject(self.backstore, name, size,
                                self.prm_gen_wwn(generate_wwn))
        self.add_child(UIStorageObject(so))
        self.log.info("Created rd_mcp ramdisk storage object %s with size %s."
                      % (name, size))

class UIFileIOBackstore(UIBackstore):
    '''
    FileIO backstore UI.
    '''
    def ui_command_create(self, name, file_or_dev, size=None,
                          generate_wwn=None, buffered=None):
        '''
        Creates a FileIO storage object. If I{file_or_dev} is a path to a
        regular file to be used as backend, then the I{size} parameter is
        mandatory. Else, if I{file_or_dev} is a path to a block device, the
        size parameter B{must} be ommited. If present, I{size} is the size of
        the file to be used, I{file} the path to the file or I{dev} the path to
        a block device.  The optional I{generate_wwn} parameter is a boolean
        specifying whether or not we should generate a T10 wwn Serial for the
        unit (by default, yes).  The I{buffered} parameter is a boolean stating
        whether or not to enable buffered mode. It is disabled by default
        (synchronous mode).

        SIZE SYNTAX
        ===========
        - If size is an int, it represents a number of bytes.
        - If size is a string, the following units can be used:
            - B{B} or no unit present for bytes
            - B{k}, B{K}, B{kB}, B{KB} for kB (kilobytes)
            - B{m}, B{M}, B{mB}, B{MB} for MB (megabytes)
            - B{g}, B{G}, B{gB}, B{GB} for GB (gigabytes)
            - B{t}, B{T}, B{tB}, B{TB} for TB (terabytes)
        '''
        self.assert_root()
        self.log.debug('Using params: size=%s generate_wwn=%s buffered=%s'
                       % (size, generate_wwn, buffered))
        is_dev = get_block_type(file_or_dev) is not None \
                or is_disk_partition(file_or_dev)

        if size is None and is_dev:
            so = FileIOStorageObject(self.backstore, name, file_or_dev,
                                     gen_wwn=self.prm_gen_wwn(generate_wwn),
                                     buffered_mode=self.prm_buffered(buffered))
            self.log.info("Created fileio storage object %s with size %s."
                          % (name, size))
            self.add_child(UIStorageObject(so))
        elif size is not None and not is_dev:
            so = FileIOStorageObject(self.backstore, name, file_or_dev, size,
                                     gen_wwn=self.prm_gen_wwn(generate_wwn),
                                     buffered_mode=self.prm_buffered(buffered))
            self.log.info("Created fileio storage object %s." % name)
            self.add_child(UIStorageObject(so))
        else:
            self.log.error("For fileio, you must either specify both a file "
                           + "and a size, or just a device path.")

class UIIBlockBackstore(UIBackstore):
    '''
    IBlock backstore UI.
    '''
    def ui_command_create(self, name, dev, generate_wwn=None):
        '''
        Creates an IBlock Storage object. I{dev} is the path to the TYPE_DISK
        block device to use and the optional I{generate_wwn} parameter is a
        boolean specifying whether or not we should generate a T10 wwn Serial
        for the unit (by default, yes).
        '''
        self.assert_root()
        so = IBlockStorageObject(self.backstore, name, dev,
                                 self.prm_wwn(generate_wwn))
        self.add_child(UIStorageObject(so))
        self.log.info("Created iblock storage object %s using %s."
                      % (name, dev))

class UIStorageObject(UINode, UIAttributes):
    '''
    A storage object UI.
    '''
    def __init__(self, storage_object):
        UINode.__init__(self)
        UIAttributes.__init__(self, storage_object)
        self.storage_object = storage_object
        self.name = storage_object.name
        self.cfs_cwd = storage_object.path
        self.refresh()

    def summary(self):
        so = self.storage_object
        if so.backstore.plugin.startswith("rd"):
            path = "ramdisk"
        else:
            path = so.udev_path
        if not path:
            return ("BROKEN STORAGE LINK", False)
        else:
            return ("%s %s" % (path, so.status), True)

