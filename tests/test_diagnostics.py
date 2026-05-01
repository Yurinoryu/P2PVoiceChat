import unittest

from common.diagnostics import format_runtime_diagnostics, get_runtime_diagnostics


class DiagnosticsTests(unittest.TestCase):
    def test_runtime_diagnostics_shape(self):
        info = get_runtime_diagnostics()

        self.assertIn("voice_ready", info)
        self.assertIn("voice_message", info)
        self.assertIn("tcp_port", info)
        self.assertIn("udp_port", info)
        self.assertIn("opus_dll_path", info)

    def test_runtime_diagnostics_format(self):
        text = format_runtime_diagnostics()

        self.assertIn("App:", text)
        self.assertIn("Voice ready:", text)
        self.assertIn("TCP", text)
        self.assertIn("UDP", text)


if __name__ == "__main__":
    unittest.main()
