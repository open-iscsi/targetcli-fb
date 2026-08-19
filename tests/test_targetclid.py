import signal
import unittest
from unittest.mock import Mock

from targetcli.targetclid import TargetCLI


class SignalHandlerTest(unittest.TestCase):
    def test_signal_handler_stops_listener_and_closes_socket(self):
        targetcli = TargetCLI.__new__(TargetCLI)
        targetcli.NoSignal = True
        targetcli.sock = Mock()

        targetcli.signal_handler(signal.SIGTERM, None)

        self.assertFalse(targetcli.NoSignal)
        targetcli.sock.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
