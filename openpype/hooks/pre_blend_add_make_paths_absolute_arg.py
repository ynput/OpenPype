import os

from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.hosts.blender import utility_scripts


class AddMakePathsAbsoluteToLaunchArgs(PreLaunchHook):
    """Run `file.make_paths_absolute` operator before open."""

    # Append after file argument
    order = 11
    app_groups = [
        "blender",
    ]

    def execute(self):
        # TODO Setting

        self.log.info(
            "Opening blend file with all paths converted to absolute."
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
