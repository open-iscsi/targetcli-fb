'''
This file is part of LIO(tm).

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
import os, sys
import pyparsing as pp

from rtslib.config_filters import *
from targetcli.cli import Cli, CliError
from targetcli.cli_config import CliConfig
from targetcli.cli_logger import logger as log
from rtslib.config import Config, ConfigError

# TODO Implement do_summary using tables + color
# TODO Implement sum for PR
# TODO Implement sum for initiator sessions
# TODO Implement sum for alua metadata
# TODO Implement sum + mgmt for fabric modules
# TODO Implement sum for network BW + portals
# TODO Implement sum for disk IO

class CliLive(Cli):
    '''
    The lio target configuration command-line for live mode.
    '''
    history_path = os.path.expanduser("~/.targetcli/history_live.txt")
    intro = ("\nWelcome to the lio target interactive shell.\n"
             "Copyright (c) 2012-2014 by Datera, Inc.\n"
             "Enter '?' to list available commands.\n")

    def __init__(self, interactive=False):
        Cli.__init__(self, interactive, self.history_path)
        self.prompt = "live> "
        self.do_resync()

    def do_exit(self, options):
        '''
        exit

        Exits the lio target configuration shell.
        '''
        options = self.parse(options, 'exit', '')
        return True

    def do_resync(self, options=''):
        '''
        resync

        Re-synchronizes the cli with the live running configuration. This
        could be useful in rare cases where manual changes have been made to
        the underlying configfs structure for debugging purposes.
        '''
        options = self.parse(options, 'resync', '')
        log.info("Syncing policy and configuration...")
        # FIXME Investigate bug in ConfigTree code: error if loading live twice
        # without recreating the Config object.
        self.config = Config()
        self.config.load_live()

    def do_configure(self, options):
        '''
        configure

        Switch to config mode. In this mode, you can safely edit a candidate
        configuration for the system, and commit it only when it is ready.
        '''
        options = self.parse(options, 'configure', '')
        if not self.interactive:
            raise CliError("Cannot switch to config mode when running "
                           "non-interactively.")
        else:
            self.save_history()
            self.clear_history()
            # FIXME Preserve CliConfig session state, notably undo history
            CliConfig(interactive=True).cmdloop()
            self.clear_history()
            self.load_history()
            self.do_resync()
            log.warning("[live] Back to live mode")

    def do_show(self, options):
        '''
        show [all] [PATH]

        Shows the running live configuration for PATH.

        Note that attributes with default values will be
        filrered out by default, unless the all option is used.
        '''
        if options and options.split()[0] == 'all':
            options = " ".join(options.split()[1:])
            node_filter = lambda x:x
        else:
            node_filter = filter_no_default

        config = self.config.dump(options, node_filter)
        if config is None:
            config = self.config.dump("%s .*" % options, node_filter)
        if config is not None:
            sys.stdout.write("%s\n" % config)
        else:
            log.error("No such path in current configuration: %s" % options)

    def complete_show(self, text, line, begidx, endidx):
        # TODO add all option
        return self._complete_path(text, line, begidx, endidx)

    def do_initialize_system(self, options):
        '''
        initialize_system

        Loads and commits the system startup configuration if it exists.
        '''
        self.config.load(CliConfig.config_path)
        do_it = self.yes_no("Load and commit the system startup configuration?"
                            , False)
        if do_it is not False:
            log.info("Initializing LIO target...")
            for msg in self.config.apply():
                log.info(msg)
        self.config.load_live()

