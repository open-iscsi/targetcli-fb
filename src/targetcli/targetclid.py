'''
targetclid

This file is part of targetcli-fb.
Copyright (c) 2019 by Red Hat, Inc.

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
import errno
import fcntl
import os
import signal
import socket
import stat
import struct
import sys
import tempfile
from os import getenv, getuid
from pathlib import Path
from threading import Thread

from configshell_fb import ConfigShell

from targetcli import __version__ as targetcli_version
from targetcli.ui_root import UIRoot

err = sys.stderr

class TargetCLI:
    def __init__(self):
        '''
        initializer
        '''
        # socket for unix communication
        self.socket_path = '/var/run/targetclid.sock'
        # pid file for defending on multiple daemon runs
        self.pid_file = '/var/run/targetclid.pid'

        self.NoSignal = True
        self.sock = None

        # shell console methods
        self.shell = ConfigShell(getenv("TARGETCLI_HOME", '~/.targetcli'))
        self.con = self.shell.con
        self.display = self.shell.con.display
        self.render = self.shell.con.render_text

        # Handle SIGINT SIGTERM SIGHUP gracefully
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)

        try:
            self.pfd = open(self.pid_file, 'w+')  # noqa: SIM115
        except OSError as e:
            self.display(
                self.render(f"opening pidfile failed: {e!s}", 'red'),
            )
            sys.exit(1)

        self.try_pidfile_lock()

        is_root = False
        if getuid() == 0:
            is_root = True

        try:
            root_node = UIRoot(self.shell, as_root=is_root)
            root_node.refresh()
        except Exception as error:
            self.display(self.render(str(error), 'red'))
            if not is_root:
                self.display(self.render("Retry as root.", 'red'))
            self.pfd.close()
            sys.exit(1)

        # Keep track, for later use
        self.con_stdout_ = self.con._stdout
        self.con_stderr_ = self.con._stderr


    def __del__(self):
        '''
        destructor
        '''
        if hasattr(self, 'pfd'):
            self.pfd.close()


    def signal_handler(self):
        '''
        signal handler
        '''
        self.NoSignal = False
        if self.sock:
            self.sock.close()


    def try_pidfile_lock(self):
        '''
        get lock on pidfile, which is to check if targetclid is running
        '''
        # check if targetclid is already running
        lock = struct.pack('hhllhh', fcntl.F_WRLCK, 0, 0, 0, 0, 0)
        try:
            fcntl.fcntl(self.pfd, fcntl.F_SETLK, lock)
        except Exception:
            self.display(self.render("targetclid is already running...", 'red'))
            self.pfd.close()
            sys.exit(1)


    def release_pidfile_lock(self):
        '''
        release lock on pidfile
        '''
        lock = struct.pack('hhllhh', fcntl.F_UNLCK, 0, 0, 0, 0, 0)
        try:
            fcntl.fcntl(self.pfd, fcntl.F_SETLK, lock)
        except Exception as e:
            self.display(
                self.render(f"fcntl(UNLCK) on pidfile failed: {e!s}", 'red'),
            )
            self.pfd.close()
            sys.exit(1)
        self.pfd.close()


    def client_thread(self, connection):
        '''
        Handle commands from client
        '''
        # load the prefs
        self.shell.prefs.load()

        still_listen = True
        # Receive the data in small chunks and retransmit it
        while still_listen:
            data = connection.recv(65535)
            if b'-END@OF@DATA-' in data:
                connection.close()
                still_listen = False
            else:
                self.con._stdout = self.con._stderr = f = tempfile.NamedTemporaryFile(mode='w', delete=False)
                try:
                    # extract multiple commands delimited with '%'
                    list_data = data.decode().split('%')
                    for cmd in list_data:
                        self.shell.run_cmdline(cmd)
                except Exception as e:
                    print(str(e), file=f)  # push error to stream

                # Restore
                self.con._stdout = self.con_stdout_
                self.con._stderr = self.con_stderr_
                f.close()

                with open(f.name) as f:
                    output = f.read()
                    var = struct.pack('i', len(output))
                    connection.sendall(var)  # length of string
                    if len(output):
                        connection.sendall(output.encode())  # actual string

                Path(f.name).unlink()


def usage():
    print(f"Usage: {sys.argv[0]} [--version|--help]", file=err)
    print("  --version\t\tPrint version", file=err)
    print("  --help\t\tPrint this information", file=err)
    sys.exit(0)


def version():
    print(f"{sys.argv[0]} version {targetcli_version}", file=err)
    sys.exit(0)


def usage_version(cmd):
    if cmd in {"help", "--help", "-h"}:
        usage()

    if cmd in {"version", "--version", "-v"}:
        version()


def main():
    '''
    start targetclid
    '''
    if len(sys.argv) > 1:
        usage_version(sys.argv[1])
        print(f"unrecognized option: {sys.argv[1]}")
        sys.exit(-1)

    to = TargetCLI()

    if getenv('LISTEN_PID'):
        # the systemd-activation path, using next available FD
        fn = sys.stderr.fileno() + 1
        try:
            sock = socket.fromfd(fn, socket.AF_UNIX, socket.SOCK_STREAM)
        except OSError as err:
            to.display(to.render(err.strerror, 'red'))
            sys.exit(1)

        # save socket so a signal can clea it up
        to.sock = sock
    else:
        # Make sure file doesn't exist already
        with contextlib.suppress(FileNotFoundError):
            Path(to.socket_path).unlink()

        # Create a TCP/IP socket
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        except OSError as err:
            to.display(to.render(err.strerror, 'red'))
            sys.exit(1)

        # save socket so a signal can clea it up
        to.sock = sock

        mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600
        umask = 0o777 ^ mode  # Prevents always downgrading umask to 0
        umask_original = os.umask(umask)
        # Bind the socket path
        try:
            sock.bind(to.socket_path)
        except OSError as err:
            to.display(to.render(err.strerror, 'red'))
            sys.exit(1)
        finally:
            os.umask(umask_original)

        # Listen for incoming connections
        try:
            sock.listen(1)
        except OSError as err:
            to.display(to.render(err.strerror, 'red'))
            sys.exit(1)

    while to.NoSignal:
        try:
            # Wait for a connection
            connection, _client_address = sock.accept()
        except OSError as err:
            if err.errno != errno.EBADF or to.NoSignal:
                to.display(to.render(err.strerror, 'red'))
            break

        thread = Thread(target=to.client_thread, args=(connection,))
        thread.start()
        try:
            thread.join()
        except Exception as error:
            to.display(to.render(str(error), 'red'))

    to.release_pidfile_lock()

    if not to.NoSignal:
        to.display(to.render("Signal received, quiting gracefully!", 'green'))
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
