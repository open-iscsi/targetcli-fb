'''
Implements the targetcli backstores related UI.

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

from ui_node import UINode, UIRTSLibNode
from rtslib import RTSRoot
from rtslib import FileIOStorageObject, BlockStorageObject
from rtslib import PSCSIStorageObject, RDMCPStorageObject
from rtslib.utils import (get_block_type, is_disk_partition)
from configshell import ExecutionError
import os
import re

def human_to_bytes(hsize, kilo=1024):
    '''
    This function converts human-readable amounts of bytes to bytes.
    It understands the following units :
        - I{B} or no unit present for Bytes
        - I{k}, I{K}, I{kB}, I{KB} for kB (kilobytes)
        - I{m}, I{M}, I{mB}, I{MB} for MB (megabytes)
        - I{g}, I{G}, I{gB}, I{GB} for GB (gigabytes)
        - I{t}, I{T}, I{tB}, I{TB} for TB (terabytes)

    Note: The definition of I{kilo} defaults to 1kB = 1024Bytes.
    Strictly speaking, those should not be called I{kB} but I{kiB}.
    You can override that with the optional kilo parameter.

    @param hsize: The human-readable version of the Bytes amount to convert
    @type hsize: string or int
    @param kilo: Optional base for the kilo prefix
    @type kilo: int
    @return: An int representing the human-readable string converted to bytes
    '''
    size = str(hsize).replace("g","G").replace("K","k")
    size = size.replace("m","M").replace("t","T")
    if not re.match("^[0-9]+[T|G|M|k]?[B]?$", size):
        raise RTSLibError("Cannot interpret size, wrong format: %s" % hsize)

    size = size.rstrip('B')

    units = ['k', 'M', 'G', 'T']
    try:
        power = units.index(size[-1]) + 1
    except ValueError:
        power = 0
        size = int(size)
    else:
        size = int(size[:-1])

    return size * (int(kilo) ** power)

def bytes_to_human(size, kilo=1024.0):
    if not size:
        return ""
    for x in ['bytes','K','M','G','T']:
        if size < kilo:
            return "(%3.1f%s) " % (size, x)
        size /= kilo


class UIBackstores(UINode):
    '''
    The backstores container UI.
    '''
    def __init__(self, parent):
        UINode.__init__(self, 'backstores', parent)
        self.cfs_cwd = "%s/core" % self.cfs_cwd
        self.refresh()

    def refresh(self):
        self._children = set([])
        UIPSCSIBackstore(self)
        UIRDMCPBackstore(self)
        UIFileIOBackstore(self)
        UIBlockBackstore(self)


class UIBackstore(UINode):
    '''
    A backstore UI.
    '''
    def __init__(self, plugin, parent):
        UINode.__init__(self, plugin, parent)
        self.cfs_cwd = "%s/core" % self.cfs_cwd
        self.refresh()

    def refresh(self):
        self._children = set([])
        for so in RTSRoot().storage_objects:
            if so.backstore.plugin == self.name:
                ui_so = UIStorageObject(so, self)
                ui_so.name = so.name

    def summary(self):
        no_storage_objects = len(self._children)
        if no_storage_objects > 1:
            msg = "%d Storage Objects" % no_storage_objects
        else:
            msg = "%d Storage Object" % no_storage_objects
        return (msg, None)

    def prm_buffered(self, buffered):
        buffered = \
                self.ui_eval_param(buffered, 'bool', True)
        if buffered:
            self.shell.log.info("Using buffered mode.")
        else:
            self.shell.log.info("Not using buffered mode.")
        return buffered

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
        try:
            child = self.get_child(name)
        except ValueError:
            self.shell.log.error("No storage object named %s." % name)
        else:
            hba = child.rtsnode.backstore
            child.rtsnode.delete()
            if not list(hba.storage_objects):
                hba.delete()
            self.remove_child(child)
            self.shell.log.info("Deleted storage object %s." % name)
            self.parent.parent.refresh()

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
    def __init__(self, parent):
        UIBackstore.__init__(self, 'pscsi', parent)

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

        if get_block_type(dev) is not None or is_disk_partition(dev):
            self.shell.log.info("Note: block backstore recommended for "
                                "SCSI block devices")

        so = PSCSIStorageObject(name, dev)
        ui_so = UIStorageObject(so, self)
        self.shell.log.info("Created pscsi storage object %s using %s"
                            % (name, dev))
        return self.new_node(ui_so)


class UIRDMCPBackstore(UIBackstore):
    '''
    RDMCP backstore UI.
    '''
    def __init__(self, parent):
        UIBackstore.__init__(self, 'ramdisk', parent)

    def ui_command_create(self, name, size):
        '''
        Creates an RDMCP storage object. I{size} is the size of the ramdisk.

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

        so = RDMCPStorageObject(name, human_to_bytes(size))
        ui_so = UIStorageObject(so, self)
        self.shell.log.info("Created ramdisk %s with size %s."
                            % (name, size))
        return self.new_node(ui_so)


class UIFileIOBackstore(UIBackstore):
    '''
    FileIO backstore UI.
    '''
    def __init__(self, parent):
        UIBackstore.__init__(self, 'fileio', parent)

    def _create_file(self, filename, size, sparse=True):
        f = open(filename, "w+")
        try:
            if sparse:
                f.seek(size-1)
                f.write("\0")
            else:
                self.shell.log.info("Writing %s bytes" % size)
                while size > 0:
                    write_size = min(size, 1024)
                    f.write("\0" * write_size)
                    size -= write_size
        except IOError:
            f.close()
            os.remove(filename)
            raise ExecutionError("Could not expand file to size")
        f.close()

    def ui_command_create(self, name, file_or_dev, size=None, buffered=None,
                          sparse=None):
        '''
        Creates a FileIO storage object. If I{file_or_dev} is a path to a
        regular file to be used as backend, then the I{size} parameter is
        mandatory. Else, if I{file_or_dev} is a path to a block device, the
        size parameter B{must} be ommited. If present, I{size} is the size of
        the file to be used, I{file} the path to the file or I{dev} the path to
        a block device. The I{buffered} parameter is a boolean stating
        whether or not to enable buffered mode. It is enabled by default
        (asynchronous mode). The I{sparse} parameter is only applicable when
        creating a new backing file. It is a boolean stating if the
        created file should be created as a sparse file (the default), or
        fully initialized.

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
        self.shell.log.debug("Using params size=%s buffered=%s sparse=%s"
                             % (size, buffered, sparse))

        sparse = self.ui_eval_param(sparse, 'bool', True)

        is_dev = get_block_type(file_or_dev) is not None \
                or is_disk_partition(file_or_dev)

        if is_dev:
            if size:
                self.shell.log.info("Block device, size parameter ignored")
                size = None
            self.shell.log.info("Note: block backstore preferred for best results")
        else:
            # use given file size only if backing file does not exist
            if os.path.isfile(file_or_dev):
                new_size = os.path.getsize(file_or_dev)
                if size:
                    self.shell.log.info("%s exists, using its size (%s bytes) instead" 
                                        % (file_or_dev, new_size))
                size = new_size
            else:
                # create file and extend to given file size
                if not size:
                    raise ExecutionError("Attempting to create file for new" +
                                         " fileio backstore, need a size")
                size = human_to_bytes(size)
                self._create_file(file_or_dev, size, sparse)

        so = FileIOStorageObject(
            name, file_or_dev,
            size,
            buffered_mode=self.prm_buffered(buffered))
        self.shell.log.info("Created fileio %s with size %s"
                            % (name, size))
        ui_so = UIStorageObject(so, self)

        return self.new_node(ui_so)


class UIBlockBackstore(UIBackstore):
    '''
    Block backstore UI.
    '''
    def __init__(self, parent):
        UIBackstore.__init__(self, 'block', parent)

    def ui_command_create(self, name, dev):
        '''
        Creates an Block Storage object. I{dev} is the path to the TYPE_DISK
        block device to use.
        '''
        self.assert_root()

        so = BlockStorageObject(name, dev)
        ui_so = UIStorageObject(so, self)
        self.shell.log.info("Created block storage object %s using %s."
                            % (name, dev))
        return self.new_node(ui_so)


class UIStorageObject(UIRTSLibNode):
    '''
    A storage object UI.
    '''
    def __init__(self, storage_object, parent):
        name = storage_object.name
        UIRTSLibNode.__init__(self, name, storage_object, parent)
        self.cfs_cwd = storage_object.path
        self.refresh()

    def ui_command_version(self):
        '''
        Displays the version of the current backstore's plugin.
        '''
        backstore = self.rtsnode.backstore
        self.shell.con.display("Backstore plugin %s %s"
                               % (backstore.plugin, backstore.version))

    def summary(self):
        so = self.rtsnode
        errors = []
        if so.backstore.plugin == "ramdisk":
            path = "ramdisk"
        else:
            path = so.udev_path

        if not path:
            errors.append("BROKEN STORAGE LINK")

        legacy = []
        if self.rtsnode.name != self.name:
            legacy.append("ADDED SUFFIX")
        if len(list(self.rtsnode.backstore.storage_objects)) > 1:
            legacy.append("SHARED HBA")

        if legacy:
            errors.append("LEGACY: " + ", ".join(legacy))

        size = bytes_to_human(getattr(so, "size", 0))

        if errors:
            msg = ", ".join(errors)
            if path:
                msg += " (%s %s)" % (path, so.status)
            return (msg, False)
        else:
            return ("%s %s%s" % (path, size, so.status), True)

