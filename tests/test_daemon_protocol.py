import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

from configshell.console import Console

from targetcli import targetcli_shell
from targetcli.daemon_protocol import (
    END,
    MAGIC,
    STDERR,
    STDOUT,
    ProtocolError,
    StreamRecorder,
    encode_reply,
    read_reply,
)
from targetcli.targetclid import TargetCLI


class FakeSocket:
    '''Serves a fixed byte string in small pieces to exercise reassembly.'''

    def __init__(self, data, piece=3, connect_error=None):
        self._data = data
        self._piece = piece
        self._connect_error = connect_error
        self.sent = []
        self.closed = False

    def recv(self, size):
        chunk = self._data[:min(size, self._piece)]
        self._data = self._data[len(chunk):]
        return chunk

    def send(self, data):
        self.sent.append(data)

    def sendall(self, data):
        self.sent.append(data)

    def connect(self, path):
        if self._connect_error:
            raise self._connect_error

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ProtocolTest(unittest.TestCase):
    def test_round_trip_keeps_order_and_markers_in_payload(self):
        records = [(STDOUT, "STDERR: not a marker\nSTDOUT: neither\n"),
                   (STDERR, "boom\n"),
                   (STDOUT, "  indented\n\n")]
        self.assertEqual(read_reply(FakeSocket(encode_reply(records))), records)

    def test_multibyte_text_split_across_recv_calls(self):
        records = [(STDOUT, "äöü€" * 50)]
        self.assertEqual(read_reply(FakeSocket(encode_reply(records), piece=1)), records)

    def test_empty_reply(self):
        self.assertEqual(read_reply(FakeSocket(MAGIC + END)), [])

    def test_old_daemon_reply_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_reply(FakeSocket(b'\x05\x00\x00\x00hello'))

    def test_unknown_tag_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_reply(FakeSocket(MAGIC + b'X' + END))

    def test_invalid_utf8_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_reply(FakeSocket(MAGIC + STDOUT + b'\x00\x00\x00\x02\xff\xfe' + END))

    def test_truncated_reply_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_reply(FakeSocket(encode_reply([(STDOUT, "hello")])[:-3]))

    def test_consecutive_writes_to_a_stream_are_merged(self):
        records = []
        out = StreamRecorder(STDOUT, records)
        err = StreamRecorder(STDERR, records)
        out.write("a")
        out.write("b")
        err.write("c")
        out.write("")
        out.write("d")
        self.assertEqual(read_reply(FakeSocket(encode_reply(records))),
                         [(STDOUT, "ab"), (STDERR, "c"), (STDOUT, "d")])
        with self.assertRaises(OSError):
            out.fileno()  # configshell's get_width() relies on this


class ClientThreadTest(unittest.TestCase):
    def run_daemon(self, request, run_cmdline):
        targetcli, connection = self.start_daemon([request, b'-END@OF@DATA-'], run_cmdline)
        targetcli.client_thread(connection)

        (reply,), _ = connection.sendall.call_args
        connection.close.assert_called_once_with()
        return read_reply(FakeSocket(reply, piece=4096))

    def start_daemon(self, requests, run_cmdline):
        targetcli = TargetCLI.__new__(TargetCLI)
        orig_out, orig_err = io.StringIO(), io.StringIO()
        targetcli.con = SimpleNamespace(_stdout=orig_out, _stderr=orig_err)
        targetcli.shell = Mock()
        targetcli.shell.run_cmdline.side_effect = lambda cmd: run_cmdline(targetcli.con, cmd)
        connection = Mock()
        connection.recv.side_effect = requests
        self.addCleanup(self.assertIs, targetcli.con._stdout, orig_out)
        self.addCleanup(self.assertIs, targetcli.con._stderr, orig_err)
        return targetcli, connection

    def test_client_disconnect_ends_the_session(self):
        targetcli, connection = self.start_daemon([b''], None)
        targetcli.client_thread(connection)
        connection.sendall.assert_not_called()
        targetcli.shell.run_cmdline.assert_not_called()
        connection.close.assert_called_once_with()

    def test_streams_are_recorded_in_order(self):
        def run(con, cmd):
            con._stdout.write(f"out {cmd}\n")
            con._stderr.write(f"err {cmd}\n")

        self.assertEqual(self.run_daemon(b'a%b', run),
                         [(STDOUT, "out a\n"), (STDERR, "err a\n"),
                          (STDOUT, "out b\n"), (STDERR, "err b\n")])

    def test_exception_goes_to_stderr_and_streams_are_restored(self):
        def run(con, _cmd):
            con._stdout.write("partial\n")
            raise RuntimeError("bad command")

        self.assertEqual(self.run_daemon(b'x', run),
                         [(STDOUT, "partial\n"), (STDERR, "bad command\n")])


class CallDaemonTest(unittest.TestCase):
    def call(self, records, req, interactive, reply=None, connect_error=None):
        if reply is None:
            reply = encode_reply(records)
        sock = FakeSocket(reply, connect_error=connect_error)
        out, err, combined = io.StringIO(), io.StringIO(), io.StringIO()

        class Tee(io.StringIO):
            def __init__(self, own):
                super().__init__()
                self.own = own

            def write(self, text):
                combined.write(text)
                return self.own.write(text)

        stdout, stderr = Tee(out), Tee(err)
        # A real console without color, where render_text() returns its
        # argument unchanged, so non-str messages would crash display()
        con = Console(stdout=stdout, stderr=stderr)
        shell = SimpleNamespace(con=con)
        path, exit_code = "", None
        with patch.object(targetcli_shell.socket, 'socket', return_value=sock), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                path = targetcli_shell.call_daemon(shell, req, interactive)
            except SystemExit as e:
                exit_code = e.code
        self.assertTrue(sock.closed)
        return path, out.getvalue(), err.getvalue(), combined.getvalue(), exit_code

    def test_output_containing_markers_is_printed_verbatim(self):
        text = "o- / name=STDERR:x STDOUT: y\n  indented\n"
        path, out, err, _, code = self.call([(STDOUT, text)], "ls", False)
        self.assertEqual((path, out, err, code), ("", text, "", None))

    def test_error_exits_non_zero_and_keeps_order(self):
        records = [(STDOUT, "first\n"), (STDERR, "oops\n"), (STDOUT, "second\n")]
        _, out, err, combined, code = self.call(records, "a%b", False)
        self.assertEqual(code, 1)
        self.assertEqual((out, err), ("first\nsecond\n", "oops\n"))
        self.assertEqual(combined, "first\noops\nsecond\n")

    def test_error_does_not_exit_in_interactive_mode(self):
        _, _, err, _, code = self.call([(STDERR, "oops\n")], "ls", True)
        self.assertEqual((err, code), ("oops\n", None))

    def test_prompt_path_is_taken_from_last_stdout_line(self):
        records = [(STDOUT, "some output\n/iscsi\n")]
        path, out, _, _, _ = self.call(records, "cd /iscsi", True)
        self.assertEqual((path, out), ("/iscsi", "some output\n"))

    def test_failed_cd_yields_no_path_and_shows_error(self):
        path, out, err, _, code = self.call([(STDERR, "No such path /nope\n")], "cd /nope", True)
        self.assertEqual((path, out, err, code), ("", "", "No such path /nope\n", None))

    def test_stdout_held_for_prompt_is_flushed_before_errors(self):
        records = [(STDOUT, "warning\n"), (STDERR, "No such path /nope\n")]
        path, out, err, combined, code = self.call(records, "cd /nope", True)
        self.assertEqual((path, code), ("", None))
        self.assertEqual(combined, "warning\nNo such path /nope\n")
        self.assertEqual((out, err), ("warning\n", "No such path /nope\n"))

    def test_last_stdout_line_that_is_not_a_path_is_printed(self):
        path, out, _, _, _ = self.call([(STDOUT, "first\nnot a path\n")], "cd x", True)
        self.assertEqual((path, out), ("", "first\nnot a path\n"))

    def test_old_daemon_reply_reports_error_and_exits(self):
        _, out, err, _, code = self.call(None, "ls", False, reply=b'\x05\x00\x00\x00hello')
        self.assertEqual((out, code), ("", 1))
        self.assertIn("please restart targetclid", err)

    def test_connection_failure_reports_error_and_exits(self):
        _, out, err, _, code = self.call(None, "ls", False, reply=b'',
                                         connect_error=FileNotFoundError(2, "No such file or directory"))
        self.assertEqual((out, code), ("", 1))
        self.assertIn("No such file or directory", err)
        self.assertIn("targetclid daemon is running", err)


if __name__ == '__main__':
    unittest.main()
