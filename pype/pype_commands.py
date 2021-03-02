# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
import json
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
    def extractenvironments(output_json_path, project, asset, task, app):
        env = os.environ.copy()
        if all((project, asset, task, app)):
            from pype.api import get_app_environments_for_context
            env = get_app_environments_for_context(
                project, asset, task, app, env
            )

        output_dir = os.path.dirname(output_json_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_json_path, "w") as file_stream:
            json.dump(env, file_stream, indent=4)

    def publish(self, gui, paths):
        pass

    def texture_copy(self, project, asset, path):
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
        repo_file = bs.create_version_from_live_code()
        if not repo_file:
            print("!!! Error while creating zip file.")
            exit(1)

        print(f">>> Created {repo_file}")
