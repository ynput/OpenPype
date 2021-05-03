# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
import json
from pathlib import Path

from openpype.lib import PypeLogger
from openpype.api import get_app_environments_for_context


class PypeCommands:
    """Class implementing commands used by Pype.

    Most of its methods are called by :mod:`cli` module.
    """
    @staticmethod
    def launch_tray(debug=False):
        PypeLogger.set_process_name("Tray")

        from openpype.tools import tray

        tray.main()

    @staticmethod
    def launch_settings_gui(dev):
        from openpype.tools import settings

        # TODO change argument options to allow enum of user roles
        user_role = "developer"
        settings.main(user_role)

    @staticmethod
    def launch_eventservercli(*args):
        from openpype.modules.ftrack.ftrack_server.event_server_cli import (
            run_event_server
        )
        return run_event_server(*args)

    @staticmethod
    def launch_standalone_publisher():
        from openpype.tools import standalonepublish
        standalonepublish.main()

    @staticmethod
    def publish(paths):
        """Start headless publishing.

        Publish use json from passed paths argument.

        Args:
            paths (list): Paths to jsons.

        Raises:
            RuntimeError: When there is no pathto process.
        """
        if not any(paths):
            raise RuntimeError("No publish paths specified")

        from openpype import install, uninstall
        from openpype.api import Logger

        # Register target and host
        import pyblish.api
        import pyblish.util

        env = get_app_environments_for_context(
            os.environ["AVALON_PROJECT"],
            os.environ["AVALON_ASSET"],
            os.environ["AVALON_TASK"],
            os.environ["AVALON_APP_NAME"]
        )
        os.environ.update(env)

        log = Logger.get_logger()

        install()

        pyblish.api.register_target("filesequence")
        pyblish.api.register_host("shell")

        os.environ["OPENPYPE_PUBLISH_DATA"] = os.pathsep.join(paths)

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

    def extractenvironments(output_json_path, project, asset, task, app):
        env = os.environ.copy()
        if all((project, asset, task, app)):
            from openpype.api import get_app_environments_for_context
            env = get_app_environments_for_context(
                project, asset, task, app, env
            )

        output_dir = os.path.dirname(output_json_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_json_path, "w") as file_stream:
            json.dump(env, file_stream, indent=4)

    def texture_copy(self, project, asset, path):
        pass

    def run_application(self, app, project, asset, task, tools, arguments):
        pass

    def validate_jsons(self):
        pass

