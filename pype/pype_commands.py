# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
from pathlib import Path

from pype.lib import PypeLogger


class PypeCommands:
    """Class implementing commands used by Pype.

    Most of its methods are called by :mod:`cli` module.
    """
    @staticmethod
    def launch_tray(debug=False):
        PypeLogger.set_process_name("Tray")

        from pype.tools import tray

        tray.main()

    @staticmethod
    def launch_settings_gui(dev):
        from pype.tools import settings

        # TODO change argument options to allow enum of user roles
        user_role = "developer"
        settings.main(user_role)

    @staticmethod
    def launch_eventservercli(*args):
        from pype.modules.ftrack.ftrack_server.event_server_cli import (
            run_event_server
        )
        return run_event_server(*args)

    @staticmethod
    def launch_standalone_publisher():
        from pype.tools import standalonepublish
        standalonepublish.main()

    @staticmethod
    def publish(paths):
        """Start headless publishing.

        Publish collects json from current working directory
        or supplied paths argument.

        Args:
            paths (list): Paths to jsons.

        Raises:
            RuntimeError: When there is no pathto process.
        """
        if not any(paths):
            raise RuntimeError("No publish paths specified")

        from pype import install, uninstall
        from pype.api import Logger

        # Register target and host
        import pyblish.api
        import pyblish.util

        log = Logger.get_logger()

        install()

        pyblish.api.register_target("filesequence")
        pyblish.api.register_host("shell")

        os.environ["PYPE_PUBLISH_DATA"] = os.pathsep.join(paths)

        log.info("Running publish ...")

        # Error exit as soon as any error occurs.
        error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

        for result in pyblish.util.publish_iter():
            if result["error"]:
                log.error(error_format.format(**result))
                uninstall()
                sys.exit(1)

        log.info("Publish finished.")
        uninstall()

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

    @staticmethod
    def generate_zip(out_path: str):
        """Generate zip file from current sources.

        Args:
            out_path (str): Path to generated zip file.

        """
        from igniter import bootstrap_repos

        # create zip file
        bs = bootstrap_repos.BootstrapRepos()
        if out_path:
            out_path = Path(out_path)
            bs.data_dir = out_path.parent

        print(f">>> Creating zip in {bs.data_dir} ...")
        repo_file = bs.install_live_repos()
        if not repo_file:
            print("!!! Error while creating zip file.")
            exit(1)

        print(f">>> Created {repo_file}")
