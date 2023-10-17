"""
3dequalizer plugin tests

These test need to be run in 3dequalizer.

"""
import unittest
from openpype.hosts.equalizer.api import EqualizerHost
import tde4  # noqa: F401


class TestEqualizer(unittest.TestCase):

    def test_context_data(self):
        # ensure empty project notest

        host = EqualizerHost.get_host()
        tde4.setProjectNotes("")

        data = host.get_context_data()
        assert data == "", "context data are not empty"
