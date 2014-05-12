'''
This file is part of the LIO SCSI Target.

Copyright (c) 2012-2014 by Datera, Inc.
More information on www.datera.io.

Original author: Jerome Martin <jxm@netiant.com>

Datera and LIO are trademarks of Datera, Inc., which may be registered in some
jurisdictions.

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
import pyparsing as pp
import prettytable as pt
import os, sys, datetime, shutil

from rtslib.config_filters import *
from targetcli.cli import Cli, CliError
from rtslib.config_live import dump_live
from targetcli.cli_logger import logger as log
from rtslib.config_parser import ConfigParser
from rtslib.config import Config, ConfigError

# TODO Add path vs pattern documentation
# TODO Implement 'configure locked' mode
# TODO Implement do_copy
# TODO Implement do_comment
# TODO Implement do_rollback
# TODO When live summary is done, use tables for info
# TODO Allow PATH=='top ... ...' to indicate top-level

class CliConfig(Cli):
    '''
    The lio target configuration command-line for edit mode.
    '''
    config_path = "/etc/target/scsi_target.lio"
    history_path = os.path.expanduser("~/.targetcli/history_configure.txt")

    def __init__(self, interactive=False):
        Cli.__init__(self, interactive, self.history_path)
        self.set_prompt()
        log.info("Syncing policy and configuration...")
        self.backup_dir = "/var/target"
        self.config = Config()
        self.config.load_live()
        self.edit_levels = ['']
        self.needs_save = False
        if interactive:
            log.warning("[edit] top-level")

    @property
    def needs_commit(self):
        if self.needs_save:
            return True
        keys = ('removed', 'major', 'major_obj',
                'minor', 'minor_obj', 'created')
        diff = self.config.diff_live()
        for key in keys:
            if diff[key]:
                return True
        return False

    @property
    def attrs_missing(self):
        for attr in self.config.current.walk(filter_only_missing):
            return True
        return False

    def add_edit_level(self, path):
        self.edit_levels.append(path)
        log.warning("[edit] %s" % self.edit_levels[-1])
        self.set_prompt(self.edit_levels[-1])

    def del_edit_level(self):
        if len(self.edit_levels) == 1:
            raise CliError("Already at top-level")
                          
        self.edit_levels.pop()
        if len(self.edit_levels) == 1:
            log.warning("[edit] top-level")
        else:
            log.warning("[edit] %s" % self.edit_levels[-1])
        self.set_prompt(self.edit_levels[-1])

    def set_prompt(self, string=''):
        '''
        Sets the prompt from string.
        '''
        if not string:
            prompt = "config# "
        else:
            max_len = 25
            if len(string) <= max_len:
                prompt = "%s# " % string
            else:
                prompt = "..%s# " % string[-max_len+3:]
        self.prompt =  prompt

    def fmt_data_src(self, src):

        # TODO Get rid of this one in favor of lst_data_src

        def ts2str(ts):
            date = datetime.datetime.fromtimestamp(int(ts))
            date = date.strftime('%Y-%m-%d %H:%M:%S')
            return date

        try:
            date = ts2str(src['timestamp'])
        except:
            date = "unknown date"

        if src['operation'] == 'set':
            fmt = ("(%s) set %s"
                   % (date, src['data'].strip()))
        elif src['operation'] == 'delete':
            fmt = ("(%s) delete %s"
                   % (date, src['pattern'].strip()))
        elif src['operation'] == 'load':
            mdate = ts2str(src['mtime'])
            fmt = ("(%s) load %s (modified %s)"
                   % (date, src['filepath'], mdate))
        elif src['operation'] == 'update':
            mdate = ts2str(src['mtime'])
            fmt = ("(%s) merge %s (modified %s)"
                   % (date, src['filepath'], mdate))
        elif src['operation'] == 'clear':
            fmt = ("(%s) cleared config"
                   % date)
        elif src['operation'] == 'resync':
            fmt = ("(%s) Synchronized configuration with live system"
                   % date)
        elif src['operation'] == 'init':
            fmt = ("(%s) created new configuration"
                   % date)
        else:
            fmt = ("(%s) unknown operation"
                   % date)
        return fmt

    def lst_data_src(self, src):

        def ts2str(ts):
            date = datetime.datetime.fromtimestamp(int(ts))
            date = date.strftime('%Y-%m-%d %H:%M:%S')
            return date

        try:
            date = ts2str(src['timestamp'])
        except:
            date = "unknown date"

        if src['operation'] == 'set':
            lst = [date, 'set', src['data'].strip()]
        elif src['operation'] == 'delete':
            lst = [date, 'delete', src['pattern'].strip()]
        elif src['operation'] == 'load':
            mdate = ts2str(src['mtime'])
            lst = [date, 'load',
                   "%s\nmodified %s" % (src['filepath'], mdate)]
        elif src['operation'] == 'update':
            mdate = ts2str(src['mtime'])
            lst = [date, 'merge',
                   "%s\nmodified %s" % (src['filepath'], mdate)]
        elif src['operation'] == 'clear':
            lst = [date, 'clear', 'n/a']
        elif src['operation'] == 'resync':
            lst = [date, 'resync', 'n/a']
        elif src['operation'] == 'init':
            lst = [date, 'init', 'n/a']
        else:
            lst = [date, 'unknown', 'n/a']
        return lst

    def do_exit(self, options):
        '''
        exit [now]

        Exits the current configuration edit level, and goes back to the
        previous edit level. If run on the top-level configuration, then exits
        config mode.

        If the now option is provided, no confirmation will be asked if there
        are uncommitted changes in the current candidate configuration when
        exiting the config mode.
        '''
        options = self.parse(options, 'exit', pp.Optional('now'))[1:]

        if self.edit_levels[-1]:
            self.del_edit_level()
            exit = False
        elif self.needs_commit:
            log.warning("[edit] All non-commited changes will be lost!")
            if 'now' in options:
                log.warning("[edit] exiting anyway, as requested")
                exit = True
            else:
                exit = self.yes_no("Exit config mode anyway?", False)
        else:
            exit = True
        return exit

    def complete_exit(self, text, line, begidx, endidx):
        return self._complete_options(text, line, begidx, endidx, ['now'])

    def do_commit(self, options):
        '''
        commit [check|interactive]

        Saves the current configuration to the system startup configuration
        file, after applying the changes to the running system.
      
        If the check option is provided, the current configuration will be
        checked but not saved or applied.

        If the interactive option is provided, the user will be able to confirm
        or skip every modification to the live system.
        '''
        # TODO Add [as DESCRIPTION] option
        # TODO Change to commit only current level unless 'all' option
        syntax = pp.Optional(pp.oneOf("check interactive"))
        options = self.parse(options, 'commit', syntax)[1:]

        if self.attrs_missing:
            self.do_missing('')
            raise CliError("Cannot validate configuration: "
                           "required attributes not set")

        if not self.needs_commit:
            raise CliError("No changes to commit!")

        log.info("Validating configuration")
        for msg in self.config.verify():
            log.info(msg)
        if 'check' in options:
            return        

        do_it = self.yes_no("Apply changes and overwrite system "
                            "configuration ?", False)
        if do_it is not False:
            log.info("Applying configuration")
            for msg in self.config.apply():
                if 'interactive' in options:
                    apply = self.yes_no("%s\nPlease confirm" % msg, True)
                    if apply is False:
                        log.warning("Aborted commit on user request: "
                                    "please verify system status")
                        return
                else:
                    log.info(msg)
                
            # TODO remove older backups
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            backup_path = "%s/backup-%s.lio" % (self.backup_dir, ts)
            log.info("Performing backup of startup configuration: %s"
                     % backup_path)
            shutil.copyfile(self.config_path, backup_path)
            log.info("Saving new startup configuration")
            # We reload the config from live before saving it, in
            # case this kernel has new attributes not yet in our
            # policy files
            self.config.load_live()
            self.config.save(self.config_path)
            self.needs_save = False
        else:
            log.info("Cancelled configuration commit")

    def complete_commit(self, text, line, begidx, endidx):
        return self._complete_options(text, line, begidx, endidx,
                                      ['check', 'interactive'])

    def do_rollback(self, options):
        '''
        rollback

        Return to the last committed configuration. Only the current
        configuration is affected. The commit command can then be used to apply
        the rolled-back configuration to the running system.
        '''
        # TODO Add more control to directly rollback the n-th version, view
        # backup infos before rollback, etc.
        backups = sorted(n for n in os.listdir(self.backup_dir)
                         if n.endswith(".lio"))
        if not backups:
            raise ConfigError("No backup found")
        else:
            backup_path = "%s/%s" % (self.backup_dir, backups[-1])
            self.config.load(backup_path)
            os.remove(backup_path)
            log.warning("Rolled-back to %s" % backup_path)

    def do_edit(self, options):
        '''
        edit PATH

        Changes the current configuration edit level to PATH, relative to the
        current configuration edit level. If PATH does not exist currently, it
        will be created.
        '''
        level = self.edit_levels[-1]
        nodes = self.config.search("%s %s" % (level, options))
        if not nodes:
            nodes_beyond = self.config.search("%s %s .*" % (level, options))
            if nodes_beyond:
                raise CliError("Incomplete path: [%s]" % options)
            else:
                statement = "%s %s" % (self.edit_levels[-1], options)
                log.debug("Setting statement '%s'" % statement)
                self.config.set(statement)
                self.needs_save = True
                node = self.config.search(statement)[0]
                log.info("Created configuration level: %s" % node.path_str)
                self.add_edit_level(node.path_str)
                self.do_missing('')
        elif len(nodes) > 1:
            raise CliError("Ambiguous path: [%s]" % options)
        else:
            self.add_edit_level(nodes[0].path_str)
            self.do_missing('')

    def complete_edit(self, text, line, begidx, endidx):
        # TODO Add tips for new path
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_live(self, options):
        '''
        live COMMAND

        Executes a single non-interactive command in live mode.
        '''
        # TODO Add completion
        from targetcli.cli_live import CliLive
        CliLive(interactive=False).onecmd(options)

    def do_set(self, options):
        '''
        set [PATH] OBJECT IDENTIFIER
        set [PATH] ATTRIBUTE VALUE

        Sets either an OBJECT IDENTIFIER (i.e. "disk mydisk") or an ATTRIBUTE
        VALUE (i.e. "enable yes").
        '''
        if not options:
            raise CliError("Missing required options")
        statement = "%s %s" % (self.edit_levels[-1], options)
        log.debug("Setting statement '%s'" % statement)
        created = self.config.set(statement)
        for node in created:
            log.info("[%s] has been set" % node.path_str)
        if not created:
            log.info("Ignored: Current configuration already match statement")
        else:
            self.needs_save = True

    def complete_set(self, text, line, begidx, endidx):
        # TODO Add tips for new path
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_delete(self, options):
        '''
        delete [PATH]

        Deletes either all LIO configuration objects at the current edit level,
        or only those under PATH relative to the current level.
        '''
        path = "%s %s" % (self.edit_levels[-1], options)
        if not path.strip():
            raise CliError("Cannot delete top-level configuration")

        nodes = self.config.search(path)
        if not nodes:
            # TODO Replace all "%s .*" forms with a try_hard arg to search
            nodes.extend(self.config.search("%s .*" % path))
        if not nodes:
            raise CliError("No configuration objects at path: %s"
                           % path.strip())

        # FIXME Use a real tree walk with filter
        obj_no = 0
        for node in nodes:
            if node.data['type'] == 'obj':
                obj_no +=1

        if obj_no == 0:
            raise CliError("Can't delete attributes, only objects: %s"
                           % path.strip())

        do_it = self.yes_no("Delete %d objects(s) from current configuration?"
                            % len(nodes), False)
        if do_it is not False:
            deleted = self.config.delete(path)
            if not deleted:
                deleted = self.config.delete("%s .*" % path)
            self.needs_save = True
            log.info("Deleted %d configuration object(s)" % obj_no)
        else:
            log.info("Cancelled: configuration not modified")

    def complete_delete(self, text, line, begidx, endidx):
        # TODO Filter for objects only, skip attributes
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_undo(self, options):
        '''
        undo

        Undo the last configuration change done during this config mode
        session. The lio cli has unlimited undo levels capabilities within a
        session.
        
        To restore a previously commited configuration, see the rollback
        command.
        '''
        options = self.parse(options, 'undo', '')[1:]
        data_src = self.config.current.data['source']
        self.config.undo()
        self.needs_save = True

        # TODO Implement info option to view all previous ops
        # TODO Implement last N option for multiple undo

        log.info("[undo] %s" % self.fmt_data_src(data_src))

    def do_info(self, options):
        '''
        info [PATH]

        Displays edit history information about the current configuration level
        or all configuration items matching PATH.
        '''
        # TODO Add node type information
        path = "%s %s" % (self.edit_levels[-1], options)
        if not path.strip():
            # This is just a test for tables
            table = pt.PrettyTable()
            table.hrules = pt.ALL
            table.field_names = ["change", "date", "type", "data"]
            table.align['data'] = 'l'
            changes = []
            nb_ver = len(self.config._configs)
            for idx, cfg in enumerate(reversed(self.config._configs)):
                lst_src = self.lst_data_src(cfg.data['source'])
                table.add_row(["%03d" % (idx + 1)] + lst_src)
            # FIXME Use term width to compute these
            table.max_width["date"] = 10
            table.max_width["data"] = 43
            sys.stdout.write("%s\n" % table.get_string())
        else:
            nodes = self.config.search(path)
            if not nodes:
                # TODO Replace all "%s .*" forms with a try_hard arg to search
                nodes.extend(self.config.search("%s .*" % path))
            if not nodes:
                raise CliError("Path does not exist: %s" % path.strip())
            infos = []
            for node in nodes:
                if node.data.get('required'):
                    req = "(required attribute) "
                else:
                    req = ""
                path = node.path_str
                infos.append("%s[%s]\nLast change: %s"
                             % (req, path,
                                self.fmt_data_src(node.data['source'])))
            log.info("\n\n".join(infos))

    def complete_info(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_clear(self, options):
        '''
        clear

        Clears the current configuration. This removes all current objects and
        attributes from the configuration.
        '''
        options = self.parse(options, 'clear', '')[1:]

        self.config.clear()
        log.info("Configuration cleared")

    def do_load(self, options):
        '''
        load live|FILE_PATH

        Replaces the current configuration with the contents of FILE_PATH.
        If any error happens while doing so, the current configuration will
        be fully rolled back.

        If live is used instead of FILE_PATH, the configuration from the live
        system will be used instead.
        '''
        # TODO Add completion for filepath
        # TODO Add a filepath type to policy and also a parser we can use here
        tok_string = (pp.QuotedString('"')
                      | pp.QuotedString("'")
                      | pp.Word(pp.printables, excludeChars="{}#'\";"))
        options = self.parse(options, 'load', tok_string)[1:]
        src = options[0]
        if src == 'live':
            if self.yes_no("Replace the current configuration with the "
                           "running configuration?", False) is not False:
                self.config.load_live()
            else:
                log.info("Cancelled: configuration not modified")
        else:
            if self.yes_no("Replace the current configuration with %s?"
                           % src, False) is not False:
                self.config.load(src)
            else:
                log.info("Cancelled: configuration not modified")

    def complete_load(self, text, line, begidx, endidx):
        # TODO Add filename support
        return self._complete_options(text, line, begidx, endidx, ['live'])

    def do_merge(self, options):
        '''
        merge live|FILE_PATH

        Merges the contents of FILE_PATH with the current configuration.
        In case of conflict, values from FILE_PATH will be used.
        If any error happens while doing so, the current configuration will
        be fully rolled back.

        If live is used instead of FILE_PATH, the configuration from the live
        system will be used instead.
        '''
        # TODO Add completion for filepath
        # TODO Add a filepath type to policy and also a parser we can use here
        tok_string = (pp.QuotedString('"')
                      | pp.QuotedString("'")
                      | pp.Word(pp.printables, excludeChars="{}#'\";"))
        options = self.parse(options, 'merge', tok_string)[1:]
        src = options[0]
        if src == 'live':
            if self.yes_no("Merge the running configuration with "
                           "the current configuration?", False) is not False:
                self.config.set(dump_live())
            else:
                log.info("Cancelled: configuration not modified")
        else:
            if self.yes_no("Merge %s with the current configuration?"
                           % src, False) is not False:
                self.config.update(src)
            else:
                log.info("Cancelled: configuration not modified")

    def complete_merge(self, text, line, begidx, endidx):
        # TODO Add filename support
        return self._complete_options(text, line, begidx, endidx, ['live'])

    def do_dump(self, options):
        '''
        dump FILE_PATH [PATH|all]

        Dumps a copy of either the current configuration level or the
        configuration at PATH to FILE_PATH. If PATH is 'all', then the
        top-level configuration will be dumped.
        '''
        options = options.split()
        if len(options) < 1:
            raise CliError("Syntax error: expected at least one option")
        filepath = options.pop(0)
        if not filepath.startswith('/'):
            raise CliError("Expected an absolute file path")
        path = " ".join(options)
        if path.strip() == 'all':
            path = ''
        else:
            path = ("%s %s" % (self.edit_levels[-1], path)).strip()

        self.config.save(filepath, path)
        if not path:
            path_desc = 'all'
        else:
            path_desc = path
        # FIXME Accept "half-node" path
        log.info("Dumped [%s] to %s" % (path_desc, filepath))

    def complete_dump(self, text, line, begidx, endidx):
        options = line.split()[1:]
        if len(options) < 1:
            return self._complete_filepath(text, options[0],
                                           begidx, endidx)
        else:
            # FIXME This is broken
            return self._complete_path(text, " ".join(options[1:]),
                                       begidx, endidx, self.edit_levels[-1])

    def do_show(self, options):
        '''
        show [all] [PATH]

        Shows the current candidate configuration for PATH, relative to the
        current edit level. 

        Note that attributes with default values will be
        filrered out by default, unless the all option is used.
        '''
        if options and options.split()[0] == 'all':
            options = " ".join(options.split()[1:])
            node_filter = lambda x:x
        else:
            node_filter = filter_no_default

        path = ("%s %s" % (self.edit_levels[-1], options)).strip()
        config = self.config.dump(path, node_filter)
        if config is None:
            config = self.config.dump("%s .*" % path, node_filter)
        if config is not None:
            sys.stdout.write("%s\n" % config)
        else:
            log.error("No such path in current configuration: %s" % path)

    def complete_show(self, text, line, begidx, endidx):
        # TODO add all option
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_missing(self, options):
        '''
        missing [PATH]

        Shows all missing required attribute values in the current candidate
        configuration for PATH, relative to the current edit level. 
        '''
        node_filter = filter_only_missing
        path = ("%s %s" % (self.edit_levels[-1], options)).strip()
        if not path:
            path = '.*'
        trees = self.config.search(path)
        if not trees:
            trees = self.config.search("%s .*" % path)
        if not trees:
            raise CliError("No such path: %s" % path)

        missing = []
        for tree in trees:
            for attr in tree.walk(node_filter):
                missing.append(attr)

        if not options:
            path = "current configuration"

        if not missing:
            log.warning("No missing attributes values under %s" % path)
        else:
            log.warning("Missing attributes values under %s:" % path)
            for attr in missing:
                log.info("    %s" % attr.path_str)
            sys.stdout.write("\n")

    def complete_missing(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx,
                                   self.edit_levels[-1])

    def do_diff(self, options):
        '''
        diff

        Shows all differences between the current configuration and the live
        running configuration.
        '''
        options = self.parse(options, 'diff', '')[1:]
        diff = self.config.diff_live()
        has_diffs = False
        if diff['removed']:
            has_diffs = True
            log.warning("Objects removed in the current configuration:")
            for node in diff['removed']:
                log.info("    %s" % node.path_str)
        if diff['created']:
            has_diffs = True
            log.warning("New objects in the current configuration:")
            for node in diff['created']:
                log.info("    %s" % node.path_str)
        if diff['major']:
            has_diffs = True
            log.warning("Major attribute changes in the current configuration:")
            for node in diff['major']:
                log.info("    %s" % node.path_str)
        if diff['minor']:
            has_diffs = True
            log.warning("Minor attribute changes in the current configuration:")
            for node in diff['minor']:
                log.info("    %s" % node.path_str)
        if not has_diffs:
            log.warning("Current configuration is in sync with live system")
        else:
            sys.stdout.write("\n")
