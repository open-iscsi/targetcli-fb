'''
Implements the targetcli backstores related UI.

Copyright (c) 2015 by Red Hat, Inc

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

from rtslib_fb import UserBackedStorageObject

# Note: Since this is exec'd at the end of ui_backstore.py, both
# UIUserBackstore and UIUserBackedStorageObject are already in scope.

class UIGlusterBackstore(UIUserBackstore):

    def __init__(self, parent):
        self.so_cls = UIUserBackedStorageObject
        super(self.__class__, self).__init__("gluster", parent)

    def ui_command_create(self, name, size, server, volume, path):
        '''
        Creates a Gluster-backed storage object.

        SIZE SYNTAX
        ===========
        - If size is an int, it represents a number of bytes.
        - If size is a string, the following units can be used:
            - B{B} or no unit present for bytes
            - B{k}, B{K}, B{kB}, B{KB} for kB (kilobytes)
            - B{m}, B{M}, B{mB}, B{MB} for MB (megabytes)
            - B{g}, B{G}, B{gB}, B{GB} for GB (gigabytes)
            - B{t}, B{T}, B{tB}, B{TB} for TB (terabytes)

        'server' is the name of the Gluster server.
        'volume' is the name of the Gluster volume.
        'path' is the name of the path in the volume.

        I{server}, I{volume}, and I{path} are also all required.
        '''
        self.assert_root()

        size = human_to_bytes(size)
        config = "gluster/%s@%s/%s" % (server, volume, path)
        so = UserBackedStorageObject(name, size=size, config=config, level=1)
        ui_so = UIUserBackedStorageObject(so, self)
        self.setup_model_alias(so)
        self.shell.log.info("Created Gluster storage object %s"
                            % (name,))
        return self.new_node(ui_so)


new_backstore(UIGlusterBackstore)
