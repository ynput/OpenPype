import os

from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.hosts.blender import utility_scripts
from openpype.settings.lib import get_project_settings


class AddMakePathsAbsoluteToLaunchArgs(PreLaunchHook):
    """Run `file.make_paths_absolute` operator before open."""

    # Append after file argument
    order = 11
    app_groups = [
        "blender",
    ]

    def execute(self):
        # Check enabled in settings
        project_name = self.data["project_name"]
        project_settings = get_project_settings(project_name)
        host_name = self.application.host_name
        host_settings = project_settings.get(host_name)
        if not host_settings:
            self.log.info('Host "{}" doesn\'t have settings'.format(host_name))
            return None

        if not host_settings.get("general", {}).get("use_paths_management"):
            return

        self.log.info(
            "Opening blend file with all paths converted to absolute"
        )
        # Add path to workfile to arguments
        self.launch_context.launch_args.extend(
            [
                "-P",
                Path(utility_scripts.__file__).parent.joinpath(
                    "make_paths_absolute.py"
                ),
            ]
        )
