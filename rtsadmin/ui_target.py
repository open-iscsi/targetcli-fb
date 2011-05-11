'''
Implements the rtsadmin target related UI.

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
from rtslib import RTSLibError, RTSLibBrokenLink, utils
from rtslib import NodeACL, NetworkPortal, MappedLUN
from rtslib import RTSRoot, Target, TPG, LUN

class UIFabricModule(UINode):
    '''
    A fabric module UI.
    '''
    def __init__(self, fabric_module):
        UINode.__init__(self)
        self.name = fabric_module.name
        self.fabric_module = fabric_module
        self.cfs_cwd = fabric_module.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for target in self.fabric_module.targets:
            self.log.debug("Found target %s under fabric module %s."
                           % (target.wwn, target.fabric_module))
            if target.has_feature('tpgts'):
                self.add_child(UIMultiTPGTarget(target))
            else:
                self.add_child(UITarget(target))

    def summary(self):
        no_targets = len(self._children)
        if no_targets > 1:
            msg = "%d Targets" % no_targets
        else:
            msg = "%d Target" % no_targets
        return (msg, None)

    def ui_command_create(self, wwn=None):
        '''
        Creates a new target. The I{wwn} format depends on the transport(s)
        supported by the fabric module. If the I{wwn} is ommited, then a 
        target will be created using either a randomly generated WWN of the
        proper type, or the first unused WWN in the list of possible WWNs if
        one is available. If WWNs are constrained to a list (i.e. for hardware
        targets addresses) and all WWNs are in use, the target creation will
        fail. Use the B{info} command to get more information abour WWN type
        and possible values.

        SEE ALSO
        ========
        B{info}
        '''
        target = Target(self.fabric_module, wwn, mode='create')
        wwn = target.wwn
        self.add_child(UITarget(target))
        self.log.info("Created target %s." % wwn)

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
        spec = self.fabric_module.spec
        if current_param == 'wwn' and spec['wwn_list'] is not None:
            existing_wwns = [child.wwn for child in self.fabric_module.targets]
            completions = [wwn for wwn in spec['wwn_list']
                           if wwn.startswith(text)
                           if wwn not in existing_wwns]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_delete(self, wwn):
        '''
        Recursively deletes the target with the specified I{wwn}, and all
        objects hanging under it.

        SEE ALSO
        ========
        B{create}
        '''
        target = Target(self.fabric_module, wwn, mode='lookup')
        target.delete()
        self.log.info("Deleted Target %s." % wwn)
        self.refresh()

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
        if current_param == 'wwn':
            wwns = [child.name for child in self.children]
            completions = [wwn for wwn in wwns if wwn.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_info(self):
        '''
        Displays information about the fabric module, notably the supported
        transports(s) and accepted B{wwn} format(s), as long as supported
        features.
        '''
        spec = self.fabric_module.spec
        self.log.info("Fabric module name: %s"
                      % self.name)
        self.log.info("ConfigFS path: %s"
                      % self.fabric_module.path)
        if spec['wwn_list'] is not None:
            self.log.info("Allowed WWNs list (%s type): %s"
                          % (spec['wwn_type'], ', '.join(spec['wwn_list'])))
        else:
            self.log.info("Supported WWN type: %s"
                          % spec['wwn_type'])
        self.log.info("Fabric module specfile: %s"
                      % self.fabric_module.spec_file)
        self.log.info("Fabric module features: %s" 
                      % ', '.join(spec['features']))
        self.log.info("Corresponding kernel module: %s"
                      % spec['kernel_module'])

    def ui_command_version(self):
        '''
        Displays the target fabric module version.
        '''
        version = "Target fabric module %s: %s" \
                % (self.fabric_module.name, self.fabric_module.version)
        self.con.display(version.strip())

class UIMultiTPGTarget(UINode):
    '''
    A generic target UI that has multiple TPGs.
    '''
    def __init__(self, target):
        UINode.__init__(self)
        self.target = target
        self.name = target.wwn
        self.cfs_cwd = target.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for tpg in self.target.tpgs:
            self.add_child(UITPG(tpg))

    def summary(self):
        if not self.target.fabric_module.is_valid_wwn(self.target.wwn):
            description = "INVALID WWN"
            is_healthy = False
        else:
            is_healthy = None
            no_tpgs = len(self._children)
            if no_tpgs > 1:
                description = "%d TPGs" % no_tpgs
            else:
                description = "%d TPG" % no_tpgs

        return (description, is_healthy)

    def ui_command_create(self, tag=None):
        '''
        Creates a new Target Portal Group within the target. The I{tag} must be
        a strictly positive integer value. If omitted, the next available
        Target Portal Group Tag (TPGT) will be used.

        SEE ALSO
        ========
        B{delete}
        '''
        if tag is None:
            tags = [tpg.tag for tpg in self.target.tpgs]
            for index in range(1048576):
                if index not in tags and index > 0:
                    tag = index
                    break
            if tag is None:
                self.log.error("Cannot find an available TPG Tag.")
                return
            else:
                self.log.info("Selected TPG Tag %d." % tag)
        else:
            try:
                tag = int(tag)
            except ValueError:
                self.log.error("The TPG Tag must be an integer value.")
                return
            else:
                if tag < 1:
                    self.log.error("The TPG Tag must be >0.")
                    return

        tpg = TPG(self.target, tag, mode='create')
        if self.prefs['auto_enable_tpgt']:
            tpg.enable = True
        self.log.info("Successfully created TPG %s." % tpg.tag)
        self.add_child(UITPG(tpg))

    def ui_command_delete(self, tag):
        '''
        Deletes the Target Portal Group with TPGT I{tag} from the target. The
        I{tag} must be a positive integer matching an existing TPGT.

        SEE ALSO
        ========
        B{create}
        '''
        tpg = TPG(self.target, tag, mode='lookup')
        tpg.delete()
        self.log.info("Deleted TPGT %s." % tag)
        self.refresh()

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
        if current_param == 'tag':
            tags = [child.name[4:] for child in self.children]
            completions = [tag for tag in tags if tag.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UITPG(UINode, UIAttributes, UIParameters):
    '''
    A generic TPG UI.
    '''
    def __init__(self, tpg):
        UINode.__init__(self)
        UIAttributes.__init__(self, tpg)
        UIParameters.__init__(self, tpg)
        self.tpg = tpg
        self.name = "tpgt%d" % tpg.tag
        self.cfs_cwd = tpg.path
        self.refresh()

        self.add_child(UILUNs(tpg))

        if tpg.has_feature('acls'):
            self.add_child(UINodeACLs(self.tpg))
        if tpg.has_feature('nps'):
            self.add_child(UIPortals(self.tpg))

    def summary(self):
        if self.tpg.has_feature('nexus'):
            description = "%s" % self.tpg.nexus
        elif self.tpg.enable:
            description = "enabled"
        else:
            description = "disabled"
        return (description, True)

    def ui_command_enable(self):
        '''
        Enables the TPG.

        SEE ALSO
        ========
        B{disable status}
        '''
        if self.tpg.enable:
            self.log.info("The TPGT is already enabled.")
        else:
            self.tpg.enable = True
            self.log.info("The TPGT has been enabled.")

    def ui_command_disable(self):
        '''
        Disables the TPG.

        SEE ALSO
        ========
        B{enable status}
        '''
        if self.tpg.enable:
            self.tpg.enable = False
            self.log.info("The TPGT has been disabled.")
        else:
            self.log.info("The TPGT is already disabled.")

class UITarget(UITPG):
    '''
    A generic target UI merged with its only TPG.
    '''
    # FIXME: This is a workaround for rtslib/kernel-side LIO enforcing at least
    # one TPG layer even for non-iSCSI fabric modules, for legacy reasons.
    def __init__(self, target):
        UITPG.__init__(self, TPG(target, 1))
        self.target = target
        self.tpg.enable = True
        self.name = target.wwn

    def summary(self):
        if not self.target.fabric_module.is_valid_wwn(self.target.wwn):
            return ("INVALID WWN", False)
        else:
            return UITPG.summary(self)


class UINodeACLs(UINode):
    '''
    A generic UI for node ACLs.
    '''
    def __init__(self, tpg):
        UINode.__init__(self)
        self.name = "acls"
        self.tpg = tpg
        self.cfs_cwd = "%s/acls" % tpg.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for node_acl in self.tpg.node_acls:
            self.add_child(UINodeACL(node_acl))

    def summary(self):
        no_acls = len(self._children)
        if no_acls > 1:
            msg = "%d ACLs" % no_acls
        else:
            msg = "%d ACL" % no_acls
        return (msg, None)

    def ui_command_create(self, wwn):
        '''
        Creates a Node ACL for the initiator node with the specified I{wwn}.
        The node's I{wwn} must match the expected WWN Type of the target's
        fabric module.

        SEE ALSO
        ========
        B{delete}
        '''
        spec = self.tpg.parent_target.fabric_module.spec
        if not utils.is_valid_wwn(spec['wwn_type'], wwn):
            self.log.error("'%s' is not a valid %s WWN."
                           % (wwn, spec['wwn_type']))
            return
        try:
            node_acl = NodeACL(self.tpg, wwn, mode="create")
        except RTSLibError, msg:
            self.log.error(msg)
            return
        else:
            self.log.info("Successfully created Node ACL for %s" 
                          % node_acl.node_wwn)
            self.add_child(UINodeACL(node_acl))

    def ui_command_delete(self, wwn):
        '''
        Deletes the Node ACL with the specified I{wwn}.

        SEE ALSO
        ========
        B{create}
        '''
        node_acl = NodeACL(self.tpg, wwn, mode='lookup')
        node_acl.delete()
        self.log.info("Successfully deleted Node ACL %s." % wwn)
        self.refresh()

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
        if current_param == 'wwn':
            wwns = [acl.node_wwn for acl in self.tpg.node_acls]
            completions = [wwn for wwn in wwns if wwn.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UINodeACL(UINode, UIAttributes, UIParameters):
    '''
    A generic UI for a node ACL.
    '''
    def __init__(self, node_acl):
        UINode.__init__(self)
        UIAttributes.__init__(self, node_acl)
        UIParameters.__init__(self, node_acl)
        self.name = node_acl.node_wwn
        self.node_acl = node_acl
        self.cfs_cwd = node_acl.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for mlun in self.node_acl.mapped_luns:
            self.add_child(UIMappedLUN(mlun))

    def summary(self):
        no_mluns = len(self._children)
        if no_mluns > 1:
            msg = "%d Mapped LUNs" % no_mluns
        else:
            msg = "%d Mapped LUN" % no_mluns
        return (msg, None)

    def ui_command_create(self, mapped_lun, tpg_lun, write_protect=None):
        '''
        Creates a mapping to one of the TPG LUNs for the initiator referenced
        by the ACL. The provided I{tpg_lun} will appear to that initiator as
        LUN I{mapped_lun}. If the I{write_protect} flag is set to B{1}, the
        initiator will not have write access to the Mapped LUN.

        SEE ALSO
        ========
        B{delete}
        '''
        try:
            tpg_lun = int(tpg_lun)
            mapped_lun = int(mapped_lun)
        except ValueError:
            self.log.error("Incorrect LUN value.")
            return

        mlun = MappedLUN(self.node_acl, mapped_lun, tpg_lun, write_protect)
        self.add_child(UIMappedLUN(mlun))
        self.log.info("Created Mapped LUN %s." % mlun.mapped_lun)

    def ui_command_delete(self, mapped_lun):
        '''
        Deletes the specified I{mapped_lun}.

        SEE ALSO
        ========
        B{create}
        '''
        mlun = MappedLUN(self.node_acl, mapped_lun)
        mlun.delete()
        self.log.info("Deleted Mapped LUN %s." % mapped_lun)
        self.refresh()

class UIMappedLUN(UINode):
    '''
    A generic UI for MappedLUN objects.
    '''
    def __init__(self, mapped_lun):
        UINode.__init__(self)
        self.mapped_lun = mapped_lun
        self.name = "mapped_lun%d" % mapped_lun.mapped_lun
        self.cfs_cwd = mapped_lun.path
        self.refresh()

    def summary(self):
        mapped_lun = self.mapped_lun
        is_healthy = True
        try:
            tpg_lun = mapped_lun.tpg_lun
        except RTSLibBrokenLink:
            description = "BROKEN LUN LINK"
            is_healthy = False
        else:
            if mapped_lun.write_protect:
                access_mode = 'ro'
            else:
                access_mode = 'rw'
            description = "lun%d (%s)" % (tpg_lun.lun, access_mode)

        return (description, is_healthy)

class UILUNs(UINode):
    '''
    A generic UI for TPG LUNs.
    '''
    def __init__(self, tpg):
        UINode.__init__(self)
        self.name = "luns"
        self.cfs_cwd = "%s/lun" % tpg.path
        self.tpg = tpg
        self.refresh()

    def refresh(self):
        self._children = set([])
        for lun in self.tpg.luns:
            self.add_child(UILUN(lun))

    def summary(self):
        no_luns = len(self._children)
        if no_luns > 1:
            msg = "%d LUNs" % no_luns
        else:
            msg = "%d LUN" % no_luns
        return (msg, None)

    def ui_command_create(self, storage_object, lun=None):
        '''
        Creates a new LUN in the Target Portal Group, attached to a storage
        object. If the I{lun} parameter is omitted, the first available LUN in
        the TPG will be used. The I{storage_object} must be the path of an
        existing storage object, i.e. B{/backstore/pscsi0/mydisk} to reference
        the B{mydisk} storage object of the virtual HBA B{pscsi0}.

        SEE ALSO
        ========
        B{delete}
        '''
        if lun is None:
            luns = [lun.lun for lun in self.tpg.luns]
            for index in range(1048576):
                if index not in luns:
                    lun = index
                    break
            if lun is None:
                self.log.error("Cannot find an available LUN.")
                return
            else:
                self.log.info("Selected LUN %d." % lun)
        else:
            try:
                lun = int(lun)
            except ValueError:
                self.log.error("The LUN must be an integer value.")
                return
            else:
                if lun < 0:
                    self.log.error("The LUN cannot be negative.")
                    return

        try:
            storage_object = self.get_node(storage_object).storage_object
        except AttributeError:
            self.log.error("Wrong storage object path.")

        lun_object = LUN(self.tpg, lun, storage_object)
        self.log.info("Successfully created LUN %s." % lun_object.lun)
        self.add_child(UILUN(lun_object))

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
        if current_param == 'storage_object':
            storage_objects = []
            for backstore in self.get_node('/backstores').children:
                for storage_object in backstore.children:
                    storage_objects.append(storage_object.path)
            completions = [so for so in storage_objects if so.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_delete(self, lun):
        '''
        Deletes the supplied LUN from the Target Portal Group. The I{lun} must
        be a positive number matching an existing LUN.

        SEE ALSO
        ========
        B{create}
        '''
        lun_object = LUN(self.tpg, lun)
        lun_object.delete()
        self.log.info("Successfully deleted LUN %s." % lun)
        # Refresh the TPG as we need to also refresh acls MappedLUNs
        self.parent.refresh()

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
        if current_param == 'lun':
            luns = [str(lun.lun) for lun in self.tpg.luns]
            completions = [lun for lun in luns if lun.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UILUN(UINode):
    '''
    A generic UI for LUN objects.
    '''
    def __init__(self, lun):
        UINode.__init__(self)
        self.lun = lun
        self.name = "lun%d" % lun.lun
        self.cfs_cwd = lun.path
        self.refresh()

    def summary(self):
        lun = self.lun
        is_healthy = True
        try:
            storage_object = lun.storage_object
        except RTSLibBrokenLink:
            description = "BROKEN STORAGE LINK"
            is_healthy = False
        else:
            backstore = storage_object.backstore
            if backstore.plugin.startswith("rd"):
                path = "ramdisk"
            else:
                path = storage_object.udev_path
            description = "%s%s/%s (%s)" % (backstore.plugin, backstore.index,
                                            storage_object.name, path)

        return (description, is_healthy)

class UIPortals(UINode):
    '''
    A generic UI for TPG network portals.
    '''
    def __init__(self, tpg):
        UINode.__init__(self)
        self.tpg = tpg
        self.name = "portals"
        self.cfs_cwd = "%s/np" % tpg.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for portal in self.tpg.network_portals:
            self.add_child(UIPortal(portal))

    def summary(self):
        no_portals = len(self._children)
        if no_portals > 1:
            msg = "%d Portals" % no_portals
        else:
            msg = "%d Portal" % no_portals
        return (msg, None)

    def ui_command_create(self, ip_address=None, ip_port=None):
        '''
        Creates a Network Portal with specified I{ip_address} and I{ip_port}.
        If I{ip_port} is omitted, the default port for the target fabric will
        be used. If I{ip_address} is omitted, the first IP address found
        matching the local hostname will be used.

        SEE ALSO
        ========
        B{delete}
        '''
        if ip_port is None:
            # FIXME: Add a specfile parameter to determine that
            ip_port = 3260
            self.log.info("Using default IP port %d" % ip_port)
        if ip_address is None:
            if not ip_address:
                ip_address = utils.get_main_ip()
                if ip_address:
                    self.log.info("Automatically selected IP address %s."
                                  % ip_address)
                else:
                    self.log.error("Cannot find a usable IP address to "
                                   + "create the Network Portal, aborting.")
                    return
        elif ip_address not in utils.list_eth_ips():
            self.log.error("Provided IP address %s does not exist, aborting."
                           % ip_address)
            return

        try:
            ip_port = int(ip_port)
        except ValueError:
            self.log.error("The ip_port must be an integer value.")
            return

        portal = NetworkPortal(self.tpg, ip_address,
                               ip_port, mode='create')
        self.log.info("Successfully created network portal %s:%d."
                      % (ip_address, ip_port))
        self.add_child(UIPortal(portal))

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
        if current_param == 'ip_address':
            completions = [addr for addr in utils.list_eth_ips()
                           if addr.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_delete(self, ip_address, ip_port):
        '''
        Deletes the Network Portal with specified I{ip_address} and I{ip_port}.

        SEE ALSO
        ========
        B{create}
        '''
        portal = NetworkPortal(self.tpg, ip_address, ip_port, mode='lookup')
        portal.delete()
        self.log.info("Deleted network portal %s:%s" % (ip_address, ip_port))
        self.refresh()

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
        completions = []
        # TODO: Check if a dict comprehension is acceptable here with supported
        #  XXX: python versions.
        portals = {}
        all_ports = set([])
        for portal in self.tpg.network_portals:
            all_ports.add(str(portal.port))
            if not portal.ip_address in portals:
                portals[portal.ip_address] = []
            portals[portal.ip_address].append(str(portal.port))

        if current_param == 'ip_address':
            if 'ip_port' in parameters:
                port = parameters['ip_port']
                completions = [addr for addr in portals
                               if port in portals[addr]
                               if addr.startswith(text)]
            else:
                completions = [addr for addr in portals
                               if addr.startswith(text)]
        elif current_param == 'ip_port':
            if 'ip_address' in parameters:
                addr = parameters['ip_address']
                if addr in portals:
                    completions = [port for port in portals[addr]
                                   if port.startswith(text)]
            else:
                completions = [port for port in all_ports
                               if port.startswith(text)]

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

class UIPortal(UINode):
    '''
    A generic UI for a network portal.
    '''
    def __init__(self, portal):
        UINode.__init__(self)
        self.portal = portal
        self.name = "%s:%s" % (portal.ip_address, portal.port)
        self.cfs_cwd = portal.path
        self.refresh()

    def summary(self):
        return ('', True)

