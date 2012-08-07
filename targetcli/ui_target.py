'''
Implements the targetcli target related UI.

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
from rtslib import RTSLibError, RTSLibBrokenLink, utils
from rtslib import NodeACL, NetworkPortal, MappedLUN
from rtslib import Target, TPG, LUN
from configshell import ExecutionError

class UIFabricModule(UIRTSLibNode):
    '''
    A fabric module UI.
    '''
    def __init__(self, fabric_module, parent):
        super(UIFabricModule, self).__init__(fabric_module.name,
                                             fabric_module, parent,
                                             late_params=True)
        self.cfs_cwd = fabric_module.path
        self.refresh()
        if self.rtsnode.has_feature('discovery_auth'):
            for param in ['userid', 'password',
                          'mutual_userid', 'mutual_password',
                          'enable']:
                self.define_config_group_param('discovery_auth',
                                               param, 'string')
        self.refresh()

    # Support late params
    #
    # By default the base class will call list_parameters and list_attributes
    # in init. This stops us from being able to lazy-load fabric modules.
    # We declare we support "late_params" to stop this, and then
    # this code overrides the base class methods that involve enumerating
    # this stuff, so we don't need to call list_parameters/attrs (which
    # would cause the module to load) until the ui is actually asking for
    # them from us.
    # Currently fabricmodules don't have these anyways, this is all a CYA thing.
    def list_config_groups(self):
        groups = super(UIFabricModule, self).list_config_groups()
        if len(self.rtsnode.list_parameters()):
            groups.append('parameter')
        if len(self.rtsnode.list_attributes()):
            groups.append('attribute')
        return groups

    # Support late params (see above)
    def list_group_params(self, group, writable=None):
        if group not in ("parameter", "attribute"):
            return super(UIFabricModule, self).list_group_params(group,
                                                                 writable)

        params_func = getattr(self.rtsnode, "list_%ss" % group)
        params = params_func()
        params_ro = params_func(writable=False)

        ret_list = []
        for param in params:
            p_writable = param not in params_ro
            if writable is not None and p_writable != writable:
                continue
            ret_list.append(param)

        ret_list.sort()
        return ret_list

    # Support late params (see above)
    def get_group_param(self, group, param):
        if group not in ("parameter", "attribute"):
            return super(UIFabricModule, self).get_group_param(group, param)

        if param not in self.list_group_params(group):
            raise ValueError("Not such parameter %s in configuration group %s"
                             % (param, group))

        description = "The %s %s." % (param, group)
        writable = param in self.list_group_params(group, writable=True)

        return dict(name=param, group=group, type="string",
                    description=description, writable=writable)

    def ui_getgroup_discovery_auth(self, auth_attr):
        '''
        This is the backend method for getting discovery_auth attributes.
        @param auth_attr: The auth attribute to get the value of.
        @type auth_attr: str
        @return: The auth attribute's value
        @rtype: str
        '''
        value = None
        if auth_attr == 'password':
            value = self.rtsnode.discovery_password
        elif auth_attr == 'userid':
            value = self.rtsnode.discovery_userid
        elif auth_attr == 'mutual_password':
            value = self.rtsnode.discovery_mutual_password
        elif auth_attr == 'mutual_userid':
            value = self.rtsnode.discovery_mutual_userid
        elif auth_attr == 'enable':
            value = self.rtsnode.discovery_enable_auth
        return value

    def ui_setgroup_discovery_auth(self, auth_attr, value):
        '''
        This is the backend method for setting discovery auth attributes.
        @param auth_attr: The auth attribute to set the value of.
        @type auth_attr: str
        @param value: The auth's value
        @type value: str
        '''
        self.assert_root()
        if value is None:
            value = ''
        if auth_attr == 'password':
            self.rtsnode.discovery_password = value
        elif auth_attr == 'userid':
            self.rtsnode.discovery_userid = value
        elif auth_attr == 'mutual_password':
            self.rtsnode.discovery_mutual_password = value
        elif auth_attr == 'mutual_userid':
            self.rtsnode.discovery_mutual_userid = value
        elif auth_attr == 'enable':
            self.rtsnode.discovery_enable_auth = value

    def refresh(self):
        self._children = set([])
        for target in self.rtsnode.targets:
            self.shell.log.debug("Found target %s under fabric module %s."
                                 % (target.wwn, target.fabric_module))
            if target.has_feature('tpgts'):
                UIMultiTPGTarget(target, self)
            else:
                UITarget(target, self)

    def summary(self):
        no_targets = len(self._children)
        status = None
        msg = "%d Targets" % no_targets

        fm = self.rtsnode
        if fm.has_feature('discovery_auth') and fm.discovery_enable_auth:
            if not (fm.discovery_password and fm.discovery_userid):
                status = False

            if fm.discovery_mutual_password and fm.discovery_mutual_userid:
                msg += ", mutual disc auth"
            else:
                msg += ", disc auth"

        return (msg, status)

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
        self.assert_root()
        target = Target(self.rtsnode, wwn, mode='create')
        wwn = target.wwn
        if target.has_feature('tpgts'):
            ui_target = UIMultiTPGTarget(target, self)
            self.shell.log.info("Created target %s." % wwn)
            return ui_target.ui_command_create()
        else:
            ui_target = UITarget(target, self)
            self.shell.log.info("Created target %s." % wwn)
            return self.new_node(ui_target)

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
        spec = self.rtsnode.spec
        if current_param == 'wwn' and spec['wwn_list'] is not None:
            existing_wwns = [child.wwn for child in self.rtsnode.targets]
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
        self.assert_root()
        target = Target(self.rtsnode, wwn, mode='lookup')
        target.delete()
        self.shell.log.info("Deleted Target %s." % wwn)
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
        spec = self.rtsnode.spec
        self.shell.log.info("Fabric module name: %s" % self.name)
        self.shell.log.info("ConfigFS path: %s" % self.rtsnode.path)
        if spec['wwn_list'] is not None:
            self.shell.log.info("Allowed WWNs list (%s type): %s"
                                % (spec['wwn_type'],
                                   ', '.join(spec['wwn_list'])))
        else:
            self.shell.log.info("Supported WWN type: %s" % spec['wwn_type'])

        self.shell.log.info("Fabric module specfile: %s"
                            % self.rtsnode.spec_file)
        self.shell.log.info("Fabric module features: %s"
                            % ', '.join(spec['features']))
        self.shell.log.info("Corresponding kernel module: %s"
                            % spec['kernel_module'])

    def ui_command_version(self):
        '''
        Displays the target fabric module version.
        '''
        version = "Target fabric module %s: %s" \
                % (self.rtsnode.name, self.rtsnode.version)
        self.shell.con.display(version.strip())


class UIMultiTPGTarget(UIRTSLibNode):
    '''
    A generic target UI that has multiple TPGs.
    '''
    def __init__(self, target, parent):
        UIRTSLibNode.__init__(self, target.wwn, target, parent)
        self.cfs_cwd = target.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for tpg in self.rtsnode.tpgs:
            UITPG(tpg, self)

    def summary(self):
        if not self.rtsnode.fabric_module.is_valid_wwn(self.rtsnode.wwn):
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
        self.assert_root()

        tpg = TPG(self.rtsnode, tag, mode='create')
        if self.shell.prefs['auto_enable_tpgt']:
            tpg.enable = True
        self.shell.log.info("Created TPG %s." % tpg.tag)
        ui_tpg = UITPG(tpg, self)
        return self.new_node(ui_tpg)

    def ui_command_delete(self, tag):
        '''
        Deletes the Target Portal Group with TPGT I{tag} from the target. The
        I{tag} must be a positive integer matching an existing TPGT.

        SEE ALSO
        ========
        B{create}
        '''
        self.assert_root()
        if tag.startswith("tpg"):
            tag = tag[3:]
        tpg = TPG(self.rtsnode, int(tag), mode='lookup')
        tpg.delete()
        self.shell.log.info("Deleted TPGT %s." % tag)
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


class UITPG(UIRTSLibNode):
    '''
    A generic TPG UI.
    '''
    def __init__(self, tpg, parent):
        name = "tpg%d" % tpg.tag
        UIRTSLibNode.__init__(self, name, tpg, parent)
        self.cfs_cwd = tpg.path
        self.refresh()

        UILUNs(tpg, self)

        if tpg.has_feature('acls'):
            UINodeACLs(self.rtsnode, self)
        if tpg.has_feature('nps'):
            UIPortals(self.rtsnode, self)

    def summary(self):
        status = None
        if self.rtsnode.has_feature('nexus'):
            description = str(self.rtsnode.nexus)
        elif self.rtsnode.enable:
            description = "enabled"
        else:
            description, status = ("disabled", False)

        if self.rtsnode.has_feature("acls_auth") and \
                int(self.rtsnode.get_attribute("authentication")):
            description += ", auth"
        return (description, status)

    def ui_command_enable(self):
        '''
        Enables the TPG.

        SEE ALSO
        ========
        B{disable status}
        '''
        self.assert_root()
        if self.rtsnode.enable:
            self.shell.log.info("The TPGT is already enabled.")
        else:
            try:
                self.rtsnode.enable = True
                self.shell.log.info("The TPGT has been enabled.")
            except:
                self.shell.log.error("The TPGT could not be enabled.")

    def ui_command_disable(self):
        '''
        Disables the TPG.

        SEE ALSO
        ========
        B{enable status}
        '''
        self.assert_root()
        if self.rtsnode.enable:
            self.rtsnode.enable = False
            self.shell.log.info("The TPGT has been disabled.")
        else:
            self.shell.log.info("The TPGT is already disabled.")


class UITarget(UITPG):
    '''
    A generic target UI merged with its only TPG.
    '''
    def __init__(self, target, parent):
        UITPG.__init__(self, TPG(target, 1), parent)
        self._name = target.wwn
        self.target = target
        if self.parent.name != "sbp":
            self.rtsnode.enable = True

    def summary(self):
        if not self.target.fabric_module.is_valid_wwn(self.target.wwn):
            return ("INVALID WWN", False)
        else:
            return UITPG.summary(self)


class UINodeACLs(UINode):
    '''
    A generic UI for node ACLs.
    '''
    def __init__(self, tpg, parent):
        UINode.__init__(self, "acls", parent)
        self.tpg = tpg
        self.cfs_cwd = "%s/acls" % tpg.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for node_acl in self.tpg.node_acls:
            UINodeACL(node_acl, self)

    def summary(self):
        no_acls = len(self._children)
        if no_acls > 1:
            msg = "%d ACLs" % no_acls
        else:
            msg = "%d ACL" % no_acls
        return (msg, None)

    def ui_command_create(self, wwn, add_mapped_luns=None):
        '''
        Creates a Node ACL for the initiator node with the specified I{wwn}.
        The node's I{wwn} must match the expected WWN Type of the target's
        fabric module.

        If I{add_mapped_luns} is omitted, the global parameter
        B{auto_add_mapped_luns} will be used, else B{true} or B{false} are
        accepted. If B{true}, then after creating the ACL, mapped LUNs will be
        automatically created for all existing LUNs.

        SEE ALSO
        ========
        B{delete}
        '''
        self.assert_root()
        spec = self.tpg.parent_target.fabric_module.spec
        if not utils.is_valid_wwn(spec['wwn_type'], wwn):
            self.shell.log.error("'%s' is not a valid %s WWN."
                                 % (wwn, spec['wwn_type']))
            return

        add_mapped_luns = \
                self.ui_eval_param(add_mapped_luns, 'bool',
                                   self.shell.prefs['auto_add_mapped_luns'])

        try:
            node_acl = NodeACL(self.tpg, wwn, mode="create")
        except RTSLibError, msg:
            self.shell.log.error(str(msg))
            return
        else:
            self.shell.log.info("Created Node ACL for %s"
                                % node_acl.node_wwn)
            ui_node_acl = UINodeACL(node_acl, self)

        if add_mapped_luns:
            for lun in self.tpg.luns:
                MappedLUN(node_acl, lun.lun, lun.lun, write_protect=False)
                self.shell.log.info("Created mapped LUN %d." % lun.lun)
            self.refresh()

        return self.new_node(ui_node_acl)

    def ui_command_delete(self, wwn):
        '''
        Deletes the Node ACL with the specified I{wwn}.

        SEE ALSO
        ========
        B{create}
        '''
        self.assert_root()
        node_acl = NodeACL(self.tpg, wwn, mode='lookup')
        node_acl.delete()
        self.shell.log.info("Deleted Node ACL %s." % wwn)
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


class UINodeACL(UIRTSLibNode):
    '''
    A generic UI for a node ACL.
    '''
    def __init__(self, node_acl, parent):
        UIRTSLibNode.__init__(self, node_acl.node_wwn, node_acl, parent)
        self.cfs_cwd = node_acl.path

        if self.rtsnode.has_feature('acls_auth'):
            for parameter in ['userid', 'password',
                              'mutual_userid', 'mutual_password']:
                self.define_config_group_param('auth', parameter, 'string')
        self.refresh()

    def ui_getgroup_auth(self, auth_attr):
        '''
        This is the backend method for getting auths attributes.
        @param auth_attr: The auth attribute to get the value of.
        @type auth_attr: str
        @return: The auth attribute's value
        @rtype: str
        '''
        value = None
        if auth_attr == 'password':
            value = self.rtsnode.chap_password
        elif auth_attr == 'userid':
            value = self.rtsnode.chap_userid
        elif auth_attr == 'mutual_password':
            value = self.rtsnode.chap_mutual_password
        elif auth_attr == 'mutual_userid':
            value = self.rtsnode.chap_mutual_userid
        return value

    def ui_setgroup_auth(self, auth_attr, value):
        '''
        This is the backend method for setting auths attributes.
        @param auth_attr: The auth attribute to set the value of.
        @type auth_attr: str
        @param value: The auth's value
        @type value: str
        '''
        self.assert_root()
        if value is None:
            value = ''
        if auth_attr == 'password':
            self.rtsnode.chap_password = value
        elif auth_attr == 'userid':
            self.rtsnode.chap_userid = value
        elif auth_attr == 'mutual_password':
            self.rtsnode.chap_mutual_password = value
        elif auth_attr == 'mutual_userid':
            self.rtsnode.chap_mutual_userid = value

    def refresh(self):
        self._children = set([])
        for mlun in self.rtsnode.mapped_luns:
            UIMappedLUN(mlun, self)

    def summary(self):
        no_mluns = len(self._children)
        if no_mluns > 1:
            msg = "%d Mapped LUNs" % no_mluns
        else:
            msg = "%d Mapped LUN" % no_mluns

        status = None
        na = self.rtsnode
        if self.rtsnode.has_feature("acls_auth") and \
                int(self.parent.parent.rtsnode.get_attribute("authentication")):
            if not (na.chap_password and na.chap_userid):
                status = False

            if na.chap_mutual_password and na.chap_mutual_userid:
                msg += ", mutual auth"
            else:
                msg += ", auth"

        return (msg, status)

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
        self.assert_root()
        try:
            tpg_lun = int(tpg_lun)
            mapped_lun = int(mapped_lun)
        except ValueError:
            self.shell.log.error("Incorrect LUN value.")
            return

        if tpg_lun in (ml.tpg_lun.lun for ml in self.rtsnode.mapped_luns):
            self.shell.log.warning(
                "Warning: TPG LUN %d already mapped to this NodeACL" % tpg_lun)

        mlun = MappedLUN(self.rtsnode, mapped_lun, tpg_lun, write_protect)
        ui_mlun = UIMappedLUN(mlun, self)
        self.shell.log.info("Created Mapped LUN %s." % mlun.mapped_lun)
        return self.new_node(ui_mlun)

    def ui_command_delete(self, mapped_lun):
        '''
        Deletes the specified I{mapped_lun}.

        SEE ALSO
        ========
        B{create}
        '''
        self.assert_root()
        mlun = MappedLUN(self.rtsnode, mapped_lun)
        mlun.delete()
        self.shell.log.info("Deleted Mapped LUN %s." % mapped_lun)
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
        if current_param == 'mapped_lun':
            mluns = [str(mlun.mapped_lun) for mlun in self.rtsnode.mapped_luns]
            completions = [mlun for mlun in mluns if mlun.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions


class UIMappedLUN(UIRTSLibNode):
    '''
    A generic UI for MappedLUN objects.
    '''
    def __init__(self, mapped_lun, parent):
        name = "mapped_lun%d" % mapped_lun.mapped_lun
        UIRTSLibNode.__init__(self, name, mapped_lun, parent)
        self.cfs_cwd = mapped_lun.path
        self.refresh()

    def summary(self):
        mapped_lun = self.rtsnode
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
            description = "lun%d %s/%s (%s)" \
            % (tpg_lun.lun, tpg_lun.storage_object.plugin,
               tpg_lun.storage_object.name, access_mode)

        return (description, is_healthy)


class UILUNs(UINode):
    '''
    A generic UI for TPG LUNs.
    '''
    def __init__(self, tpg, parent):
        UINode.__init__(self, "luns", parent)
        self.cfs_cwd = "%s/lun" % tpg.path
        self.tpg = tpg
        self.refresh()

    def refresh(self):
        self._children = set([])
        for lun in self.tpg.luns:
            UILUN(lun, self)

    def summary(self):
        no_luns = len(self._children)
        if no_luns > 1:
            msg = "%d LUNs" % no_luns
        else:
            msg = "%d LUN" % no_luns
        return (msg, None)

    def ui_command_create(self, storage_object, lun=None,
                          add_mapped_luns=None):
        '''
        Creates a new LUN in the Target Portal Group, attached to a storage
        object. If the I{lun} parameter is omitted, the first available LUN in
        the TPG will be used. If present, it must be a number greater than 0.
        Alternatively, the syntax I{lunX} where I{X} is a positive number is
        also accepted.

        The I{storage_object} must be the path of an existing storage object,
        i.e. B{/backstore/pscsi0/mydisk} to reference the B{mydisk} storage
        object of the virtual HBA B{pscsi0}.

        If I{add_mapped_luns} is omitted, the global parameter
        B{auto_add_mapped_luns} will be used, else B{true} or B{false} are
        accepted. If B{true}, then after creating the LUN, mapped LUNs will be
        automatically created for all existing node ACLs, mapping the new LUN.

        SEE ALSO
        ========
        B{delete}
        '''
        self.assert_root()

        add_mapped_luns = \
                self.ui_eval_param(add_mapped_luns, 'bool',
                                   self.shell.prefs['auto_add_mapped_luns'])

        try:
            storage_object = self.get_node(storage_object).rtsnode
        except ValueError:
            self.shell.log.error("Invalid storage object %s." % storage_object)
            return

        if lun and lun.lower().startswith('lun'):
            lun = lun[3:]
        lun_object = LUN(self.tpg, lun, storage_object)
        self.shell.log.info("Created LUN %s." % lun_object.lun)
        ui_lun = UILUN(lun_object, self)

        if add_mapped_luns:
            for acl in self.tpg.node_acls:
                if lun:
                    mapped_lun = lun
                else:
                    mapped_lun = 0
                existing_mluns = [mlun.mapped_lun for mlun in acl.mapped_luns]
                if mapped_lun in existing_mluns:
                    mapped_lun = None
                    for possible_mlun in xrange(LUN.MAX_LUN):
                        if possible_mlun not in existing_mluns:
                            mapped_lun = possible_mlun
                            break

                if mapped_lun == None:
                    self.shell.log.warning(
                        "Cannot map new lun %s into ACL %s"
                        % (lun_object.lun, acl.node_wwn))
                else:
                    mlun = MappedLUN(acl, mapped_lun, lun_object, write_protect=False)
                    self.shell.log.info("Created LUN %d->%d mapping in node ACL %s"
                                        % (mlun.tpg_lun.lun, mlun.mapped_lun, acl.node_wwn))
            self.parent.refresh()

        return self.new_node(ui_lun)

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

        Alternatively, the syntax I{lunX} where I{X} is a positive number is
        also accepted.

        SEE ALSO
        ========
        B{create}
        '''
        self.assert_root()
        if lun.lower().startswith("lun"):
            lun = lun[3:]
        try:
            lun_object = LUN(self.tpg, lun)
        except:
            raise RTSLibError("Invalid LUN")
        lun_object.delete()
        self.shell.log.info("Deleted LUN %s." % lun)
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


class UILUN(UIRTSLibNode):
    '''
    A generic UI for LUN objects.
    '''
    def __init__(self, lun, parent):
        name = "lun%d" % lun.lun
        UIRTSLibNode.__init__(self, name, lun, parent)
        self.cfs_cwd = lun.path
        self.refresh()

    def summary(self):
        lun = self.rtsnode
        is_healthy = True
        try:
            storage_object = lun.storage_object
        except RTSLibBrokenLink:
            description = "BROKEN STORAGE LINK"
            is_healthy = False
        else:
            if storage_object.plugin == "ramdisk":
                description = "%s/%s" % (storage_object.plugin, storage_object.name,)
            else:
                description = "%s/%s (%s)" % (storage_object.plugin,
                                          storage_object.name,
                                          storage_object.udev_path)

        return (description, is_healthy)


class UIPortals(UINode):
    '''
    A generic UI for TPG network portals.
    '''
    def __init__(self, tpg, parent):
        UINode.__init__(self, "portals", parent)
        self.tpg = tpg
        self.cfs_cwd = "%s/np" % tpg.path
        self.refresh()

    def refresh(self):
        self._children = set([])
        for portal in self.tpg.network_portals:
            UIPortal(portal, self)

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
        self.assert_root()

        # FIXME: Add a specfile parameter to determine default port
        ip_port = self.ui_eval_param(ip_port, 'number', 3260)
        ip_address = self.ui_eval_param(ip_address, 'string', "0.0.0.0")

        if ip_address not in utils.list_eth_ips() and ip_address != "0.0.0.0":
            raise ExecutionError("Cannot bind to address: %s" % ip_address)

        if ip_port == 3260:
            self.shell.log.info("Using default IP port %d" % ip_port)
        if ip_address == "0.0.0.0":
            self.shell.log.info("Binding to INADDR_ANY (0.0.0.0)")

        portal = NetworkPortal(self.tpg, ip_address, ip_port, mode='create')
        self.shell.log.info("Created network portal %s:%d."
                            % (ip_address, ip_port))
        ui_portal = UIPortal(portal, self)
        return self.new_node(ui_portal)

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
        self.assert_root()
        portal = NetworkPortal(self.tpg, ip_address, ip_port, mode='lookup')
        portal.delete()
        self.shell.log.info("Deleted network portal %s:%s"
                            % (ip_address, ip_port))
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


class UIPortal(UIRTSLibNode):
    '''
    A generic UI for a network portal.
    '''
    def __init__(self, portal, parent):
        name = "%s:%s" % (portal.ip_address, portal.port)
        UIRTSLibNode.__init__(self, name, portal, parent)
        self.cfs_cwd = portal.path
        self.refresh()

    def summary(self):
        return ('', True)

