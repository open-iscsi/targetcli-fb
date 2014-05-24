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
import pyparsing as pp
import sys, tty, cmd, termios, readline, traceback

import rtslib.config, rtslib.config_tree
from targetcli.cli_logger import logger as log
from rtslib.config import ConfigError

# TODO Implement | filters: top N, last N, page, grep
# TODO Redo help summary, using 2 columns: cmd, short description

class CliError(Exception):
    pass

class Cli(cmd.Cmd):
    '''
    Our base Cli class, common to both CliLive and CliConfig
    '''
    intro = ''
    log_levels = {'debug': 10, 'info': 20, 'warning': 30,
                  'error': 40, 'critical': 50}

    def __init__(self, interactive, history_path):
        '''
        Initializes a new Cli object.

        interactive is a boolean to run either interactively or in batch mode
        history_path is the path to the command-line history file
        '''
        cmd.Cmd.__init__(self)
        self.debug_level = 'off'
        self.last_traceback = None
        self.interactive = interactive
        self.do_save_history = self.interactive
        if self.interactive:
            self.load_history()
        readline.set_completer_delims(' \t\n`~!@#$%^&*()=+[{]}\\|;\'",<>/?')

    def do_EOF(self, options):
        sys.stdout.write("exit\n")
        return self.do_exit(options)

    def _complete_options(self, text, line, begidx, endidx, options):
        '''
        Helper to autocomplete one or more options out of options, without any
        ordering considerations.
        '''
        # TODO Add middle-of-line completion
        prev_options = line.split()[1:]
        if text:
            prev_options = prev_options[:-1]
        return ["%s " % name for name in options
                if name.startswith(text)
                if name.strip() not in prev_options]

    def _complete_one_option(self, text, line, begidx, endidx, options):
        '''
        Helper to autocomplete a single option out of options.
        '''
        # TODO Add middle-of-line completion
        prev_options = line.split()[1:]
        if text:
            prev_options = prev_options[:-1]
        return ["%s " % name for name in options
                if name.startswith(text)
                if not prev_options]

    def _complete_path(self, text, line, begidx, endidx, prefix=None):
        '''
        Helper to autocomplete a configuration path.
        '''
        # TODO Add middle-of-line completion
        pattern = line.partition(' ')[2]
        if prefix is None:
            prefix = ''

        # Are we completing an attr/obj value/id or a group?
        nodes_last_key = self.config.search(("%s %s.*"
                                             % (prefix, pattern)).strip())
        # Or an attr/obj name/class ?
        nodes_first_key = [node for node
                           in self.config.search(("%s %s.* .*"
                                                 % (prefix, pattern)).strip())
                           if node.data['type'] != 'group']
        completions = []
        completions.extend(node.key[-1] for node in nodes_last_key)
        completions.extend(node.key[0] for node in nodes_first_key)
        return ["%s " % c for c in completions if c.startswith(text)]

    def _complete_filepath(self, text, line, begidx, endidx):
        '''
        Helper to autocomplete file paths.
        '''
        # TODO Implement this
        return []

    def save_history(self):
        '''
        Saves the command history.
        '''
        if not self.do_save_history:
            return
        try:
            readline.write_history_file(self.history_path)
        except Exception, e:
            raise CliError("Failed to save command history, disabling: %s", e)
            self.do_save_history = False

    def load_history(self):
        '''
        Loads the command history.
        '''
        try:
            readline.read_history_file(self.history_path)
        except IOError, e:
            log.debug("Error while reading history: %s" % e)

    def clear_history(self):
        '''
        Clears the command history.
        '''
        readline.clear_history()

    def emptyline(self):
        '''
        Just go on with a new prompt line if the user enters an empty line.
        '''
        pass

    def cmdloop(self):
        '''
        The main REPL loop.
        '''
        intro = self.intro
        while True:
            try:
                cmd.Cmd.cmdloop(self, intro=intro)
            except KeyboardInterrupt:
                sys.stdout.write("^C\n")
                intro = ''
            else:
                break

    def onecmd(self, line):
        '''
        Executes a command line.
        '''
        try:
            result = cmd.Cmd.onecmd(self, line)
        except pp.ParseException, e:
            log.error("Unknown syntax: %s at char %d" % (e.msg, e.loc))
            return None
        except ConfigError, e:
            self.last_traceback = traceback.format_exc()
            log.error(str(e))
        except CliError, e:
            self.last_traceback = traceback.format_exc()
            log.error(str(e))
        except Exception, e:
            self.last_traceback = traceback.format_exc()
            log.error("%s: %s\n" % (e.__class__.__name__, e))
            return None
        else:
            self.save_history()
            return result

    def completenames(self, text, *ignored):
        return ["%s " % name[3:] for name in self.get_names()
                if name.startswith("do_%s" % text)
                if not name in ['do_EOF']]

    def getchar(self):
        '''
        Returns the first character read from stdin, without waiting for the
        user to hit enter.
        '''
        fd = sys.stdin.fileno()
        tcattr_backup = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, tcattr_backup)
            return char

    def yes_no(self, question, default=None):
        '''
        Asks a yes/no question to be answered by typing a single 'y' or 'n'
        character. If we do not run in interactive mode, returns None. Else
        returns True for yes and False for not.

        default can either be True (yes is the default), False (no is the
        default) or None (no default).
        '''
        keys = {'\x03': '^C', '\x04': '^D'}
        if not self.interactive:
            result = None
        else:
            if default is None:
                choices = "y/n"
            elif default is True:
                choices = "Y/n"
                dfl_key = 'y'
            elif default is False:
                choices = "y/N"
                dfl_key = 'n'
            key = None
            replies = ['y', 'n', 'Y', 'N']
            if default is not None:
                replies.append('\r')
            while key not in replies:
                log.debug("Got key %r" % key)
                sys.stdout.write("%s [%s] " % (question, choices))
                key = self.getchar()
                key = keys.get(key, key)
                if key == '\r' and default is not None:
                    sys.stdout.write("%s\n" % dfl_key)
                else:
                    sys.stdout.write("%s\n" % key)
                if key in ['^C', '^D']:
                    raise CliError("Aborted")
            if key == '\r':
                result = default
            elif key.lower() == 'y':
                result = True
            else:
                result = False

        log.debug("yes_no(%s) -> %r" % (question, result))
        return result

    def parse(self, line, header, grammar):
        '''
        Parses line using a pyparsing grammar.
        Returns the parse tree as a list.
        '''
        if not grammar:
            grammar = pp.Empty()
        grammar = pp.Literal(header) + grammar
        line = "%s %s" % (header, line)
        log.debug("Parsing line '%s'" % line)
        tokens = grammar.parseString(line, parseAll=True).asList()
        log.debug("Got parse tree %s" % tokens)
        return tokens

    def do_trace(self, options):
        '''
        trace

        Displays the last exception trace for the current mode.

        This is useful only for debugging the application. Your lio support
        team might ask you to run this command to help understanding an issue
        you're experimenting.
        '''
        options = self.parse(options, 'trace', '')[1:]
        if self.last_traceback is not None:
            log.error(self.last_traceback)
        else:
            log.error("No previous exception traceback.")

    def do_debug(self, options):
        '''
        debug [off|cli|api|all]

        Controls the debug messages level:

            off disables all debug message
            cli enables only cli debug messages
            api also enables Config API messages
            all adds even more details to api debug

        With no option, displays the current debug level.
        '''
        syntax = pp.Optional(pp.oneOf(["off", "cli", "api", "all"]))
        options = self.parse(options, 'debug', syntax)[1:]

        if not options:
            log.info("Current debug level: %s" % self.debug_level)
        else:
            self.debug_level = options[0]
            if self.debug_level == 'off':
                log.setLevel(self.log_levels['info'])
                rtslib.config.log.setLevel(self.log_levels['info'])
                rtslib.config_tree.log.setLevel(self.log_levels['info'])
            elif self.debug_level == 'cli':
                log.setLevel(self.log_levels['debug'])
                rtslib.config.log.setLevel(self.log_levels['info'])
                rtslib.config_tree.log.setLevel(self.log_levels['info'])
            elif self.debug_level == 'api':
                log.setLevel(self.log_levels['debug'])
                rtslib.config.log.setLevel(self.log_levels['debug'])
                rtslib.config_tree.log.setLevel(self.log_levels['info'])
            elif self.debug_level == 'all':
                log.setLevel(self.log_levels['debug'])
                rtslib.config.log.setLevel(self.log_levels['debug'])
                rtslib.config_tree.log.setLevel(self.log_levels['debug'])

            log.info("Debug level is now: %s" % self.debug_level)

    def complete_debug(self, text, line, begidx, endidx):
        return self._complete_one_option(text, line, begidx, endidx,
                                         ["off", "cli", "api", "all"])
