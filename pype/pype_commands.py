# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import subprocess
import sys


class PypeCommands:
    """Class implementing commands used by Pype.

    Most of its methods are called by :mod:`cli` module.
    """
    @staticmethod
    def launch_tray(debug=False):
        from pype.tools import tray

        tray.main()

    @staticmethod
    def launch_settings_gui(dev):
        from pype.lib import execute

        args = [sys.executable, "-m", "pype.tools.settings"]
        if dev:
            args.append("--develop")
        return_code = execute(args)
        return return_code

    def launch_eventservercli(self, args):
        from pype.modules import ftrack
        from pype.lib import execute

        fname = os.path.join(
            os.path.dirname(os.path.abspath(ftrack.__file__)),
            "ftrack_server",
            "event_server_cli.py"
        )

        return execute([
            sys.executable, "-u", fname
        ])

    def publish(self, gui, paths):
        pass

    def texture_copy(self, project, asset, path):
        pass

    def run_pype_tests(self, keyword, id):
        pass

    def make_docs(self):
        pass

    def pype_setup_coverage(self):
        pass

    def run_application(self, app, project, asset, task, tools, arguments):
        pass

    def validate_jsons(self):
        pass
