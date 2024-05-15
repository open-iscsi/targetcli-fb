'''
Starts the targetcli CLI shell.

This file is part of targetcli.
Copyright (c) 2011-2013 by Datera, Inc

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


import contextlib
import fcntl
import readline
import socket
import struct
import sys
from os import getenv, getuid

from configshell_fb import ConfigShell, ExecutionError
from rtslib_fb import RTSLibError

from targetcli import __version__ as targetcli_version
from targetcli.ui_root import UIRoot

err = sys.stderr
# lockfile for serializing multiple targetcli requests
lock_file = '/var/run/targetcli.lock'
socket_path = '/var/run/targetclid.sock'
hints = ['/', 'backstores/', 'iscsi/', 'loopback/', 'vhost/', 'xen-pvscsi/',
         'cd', 'pwd', 'ls', 'set', 'get', 'help', 'refresh', 'status',
         'clearconfig', 'restoreconfig', 'saveconfig', 'exit']

class TargetCLI(ConfigShell):
    default_prefs = {'color_path': 'magenta',
                     'color_command': 'cyan',
                     'color_parameter': 'magenta',
                     'color_keyword': 'cyan',
                     'completions_in_columns': True,
                     'logfile': None,
                     'loglevel_console': 'info',
                     'loglevel_file': 'debug9',
                     'color_mode': True,
                     'prompt_length': 30,
                     'tree_max_depth': 0,
                     'tree_status_mode': True,
                     'tree_round_nodes': True,
                     'tree_show_root': True,
                     'export_backstore_name_as_model': True,
                     'auto_enable_tpgt': True,
                     'auto_add_mapped_luns': True,
                     'auto_cd_after_create': False,
                     'auto_save_on_exit': True,
                     'max_backup_files': '10',
                     'auto_add_default_portal': True,
                     'auto_use_daemon': False,
                     'daemon_use_batch_mode': False,
                    }

def usage():
    print(f"Usage: {sys.argv[0]} [--version|--help|CMD|--disable-daemon]", file=err)
    print("  --version\t\tPrint version", file=err)
    print("  --help\t\tPrint this information", file=err)
    print("  CMD\t\t\tRun targetcli shell command and exit", file=err)
    print("  <nothing>\t\tEnter configuration shell", file=err)
    print("  --disable-daemon\tTurn-off the global auto use daemon flag", file=err)
    print("See man page for more information.", file=err)
    sys.exit(-1)

def version():
    print(f"{sys.argv[0]} version {targetcli_version}", file=err)
    sys.exit(0)

def usage_version(cmd):
    if cmd in {"help", "--help", "-h"}:
        usage()

    if cmd in {"version", "--version", "-v"}:
        version()

def try_op_lock(shell, lkfd):
    '''
    acquire a blocking lock on lockfile, to serialize multiple requests
    '''
    try:
        fcntl.flock(lkfd, fcntl.LOCK_EX)  # wait here until ongoing request is finished
    except Exception as e:
        shell.con.display(
            shell.con.render_text(
                f"taking lock on lockfile failed: {e!s}",
                'red'))
        sys.exit(1)

def release_op_lock(shell, lkfd):
    '''
    release blocking lock on lockfile, which can allow other requests process
    '''
    try:
        fcntl.flock(lkfd, fcntl.LOCK_UN)  # allow other requests now
    except Exception as e:
        shell.con.display(
            shell.con.render_text(
                f"unlock on lockfile failed: {e!s}",
                'red'))
        sys.exit(1)
    lkfd.close()

def completer(text, state):
    options = [x for x in hints if x.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

def call_daemon(shell, req, interactive):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    except OSError as err:
        shell.con.display(shell.con.render_text(err, 'red'))
        sys.exit(1)

    try:
        sock.connect(socket_path)
    except OSError as err:
        shell.con.display(shell.con.render_text(err, 'red'))
        shell.con.display(
            shell.con.render_text("Currently auto_use_daemon is true, "
                "hence please make sure targetclid daemon is running ...\n"
                "(or)\nIncase if you wish to turn auto_use_daemon to false "
                "then run '#targetcli --disable-daemon'", 'red'))
        sys.exit(1)

    # Two cases where we want to get pwd:
    # 1. Before starting shell in interactive mode, needed for setting terminal
    # 2. And only in Interactive mode, having command 'cd'
    get_pwd = False
    if interactive:
        if not req:
            req = "pwd"
            get_pwd = True
        elif "cd " in req:
            req += "%pwd"
            get_pwd = True
    else:
        req = "cd /%" + req  # Non-interactive modes always consider start at '/'

    try:
        # send request
        sock.sendall(req.encode())
    except OSError as err:
        shell.con.display(shell.con.render_text(err, 'red'))
        sys.exit(1)

    var = sock.recv(4)  # get length of data
    sending = struct.unpack('i', var)
    amount_expected = sending[0]
    amount_received = 0

    # get the actual data in chunks
    output = ""
    path = ""
    while amount_received < amount_expected:
        data = sock.recv(1024)
        data = data.decode()
        amount_received += len(data)
        output += data

    if get_pwd:
        output_split = output.splitlines()
        lines = len(output_split)
        for i in range(lines):
            if i == lines - 1:
                path = str(output_split[i])
            else:
                print(str(output_split[i]), end="\n")
    else:
        print(output, end="")

    sock.send(b'-END@OF@DATA-')
    sock.close()

    return path

def switch_to_daemon(shell, interactive):
    readline.set_completer(completer)
    readline.set_completer_delims('')

    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        call_daemon(shell, command, False)
        sys.exit(0)

    if interactive:
        shell.con.display(f"targetcli shell version {targetcli_version}\n"
                          "Entering targetcli interactive mode for daemonized approach.\n"
                          "Type 'exit' to quit.\n")
    else:
        shell.con.display(f"targetcli shell version {targetcli_version}\n"
                          "Entering targetcli batch mode for daemonized approach.\n"
                          "Enter multiple commands separated by newline and "
                          "type 'exit' to run them all in one go.\n")

    prompt_path = "/"
    if interactive:
        prompt_path = call_daemon(shell, None, interactive)  # get the initial path

    inputs = []
    real_exit = False
    while True:
        command = input(f"{prompt_path}> ")
        if command.lower() == "exit":
            real_exit = True
        elif not command:
            continue
        if not interactive:
            inputs.append(command)
            if real_exit:
                command = '%'.join(inputs)  # delimit multiple commands with '%'
                call_daemon(shell, command, interactive)
                break
        else:
            if real_exit:
                break
            path = call_daemon(shell, command, interactive)
            if path:
                if path[0] == "/":
                    prompt_path = path
                else:
                    print(path)  # Error No Path ...

    sys.exit(0)

def main():
    '''
    Start the targetcli shell.
    '''
    shell = TargetCLI(getenv("TARGETCLI_HOME", '~/.targetcli'))

    is_root = False
    if getuid() == 0:
        is_root = True

    try:
        lkfd = open(lock_file, 'w+')  # noqa: SIM115
    except OSError as e:
        shell.con.display(
                shell.con.render_text(f"opening lockfile failed: {e!s}",
                    'red'))
        sys.exit(1)

    try_op_lock(shell, lkfd)

    use_daemon = False
    if shell.prefs['auto_use_daemon']:
        use_daemon = True

    disable_daemon = False
    if len(sys.argv) > 1:
        usage_version(sys.argv[1])
        if sys.argv[1] in {"disable-daemon", "--disable-daemon"}:
            disable_daemon = True

    interactive_mode = True
    if shell.prefs['daemon_use_batch_mode']:
        interactive_mode = False

    if use_daemon and not disable_daemon:
        switch_to_daemon(shell, interactive_mode)
        # does not return

    try:
        root_node = UIRoot(shell, as_root=is_root)
        root_node.refresh()
    except Exception as error:
        shell.con.display(shell.con.render_text(str(error), 'red'))
        if not is_root:
            shell.con.display(shell.con.render_text("Retry as root.", 'red'))
        sys.exit(-1)

    if len(sys.argv) > 1:
        try:
            if disable_daemon:
                shell.run_cmdline('set global auto_use_daemon=false')
            else:
                shell.run_cmdline(" ".join(sys.argv[1:]))
        except Exception as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    shell.con.display(f"targetcli shell version {targetcli_version}\n"
                      "Copyright 2011-2013 by Datera, Inc and others.\n"
                      "For help on commands, type 'help'.\n")
    if not is_root:
        shell.con.display("You are not root, disabling privileged commands.\n")

    while not shell._exit:
        try:
            shell.run_interactive()
        except (RTSLibError, ExecutionError) as msg:  # noqa: PERF203 - would otherwise exit shell
            shell.log.error(str(msg))

    if shell.prefs['auto_save_on_exit'] and is_root:
        shell.log.info("Global pref auto_save_on_exit=true")
        root_node.ui_command_saveconfig()

    release_op_lock(shell, lkfd)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        main()
